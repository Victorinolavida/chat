import { useCallback, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { authRequest } from './api'

const AUTH_ERROR = /auth|token|jwt|expired|unauthor|forbidden/i
const SOCKET_PATH = '/ws'

const parseTime = (value) => {
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? null : time
}

const sortItems = (items) =>
  items
    .map((item, index) => ({ item, index }))
    .sort((a, b) => {
      const diff = a.item.time - b.item.time
      return diff !== 0 ? diff : a.index - b.index
    })
    .map(({ item }) => item)

const isAuthError = (err) =>
  err?.status === 401 || AUTH_ERROR.test(err?.message || '')

const mergeHistory = (current, historyMessages, seqRef) => {
  const seen = new Set()
  for (const item of current) {
    if (item.kind === 'message' && item.payload?.id) {
      seen.add(item.payload.id)
    }
  }
  const additions = []
  for (const message of historyMessages) {
    if (!message) continue
    if (message.id && seen.has(message.id)) continue
    if (message.id) seen.add(message.id)
    seqRef.current += 1
    additions.push({
      key: message.id || `h${seqRef.current}`,
      kind: 'message',
      payload: message,
      time: parseTime(message.created_at) ?? 0,
    })
  }
  if (additions.length === 0) return current
  return sortItems([...current, ...additions])
}

import lockIcon from './icons/lock.svg'

const conversationLabel = (conversation, userId) => {
  if (!conversation) return ''
  const others = (conversation.members || []).filter(
    (member) => member.id !== userId,
  )
  if (others.length === 0) return 'Private'
  return `${others.map((member) => member.username).join(', ')}`
}

// Plays a short Web Audio chime for incoming messages. The AudioContext is
// created lazily on the first user gesture so browsers don't block it.
const useNotificationSound = () => {
  const contextRef = useRef(null)

  useEffect(() => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return undefined

    const unlock = () => {
      try {
        if (!contextRef.current) contextRef.current = new AudioCtx()
        const context = contextRef.current
        if (context.state === 'suspended') context.resume()
        // Play a silent buffer so the context is fully unlocked and can later
        // play in response to a socket event (outside a user gesture).
        const source = context.createBufferSource()
        source.buffer = context.createBuffer(1, 1, 22050)
        source.connect(context.destination)
        source.start(0)
      } catch {
        // Ignore: a blocked audio context must never break the app.
      }
    }

    window.addEventListener('pointerdown', unlock)
    window.addEventListener('keydown', unlock)
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      contextRef.current?.close?.()
      contextRef.current = null
    }
  }, [])

  return useCallback(() => {
    const context = contextRef.current
    if (!context) return
    try {
      if (context.state === 'suspended') context.resume()
      if (context.state !== 'running') return

      const now = context.currentTime
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(880, now)
      oscillator.frequency.exponentialRampToValueAtTime(1320, now + 0.12)
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.3)
      oscillator.connect(gain).connect(context.destination)
      oscillator.start(now)
      oscillator.stop(now + 0.32)
    } catch {
      // Ignore: sound is best-effort and must not affect messaging.
    }
  }, [])
}


export default function Chat({ session, onLogout, onAuthError }) {
  const { user, token } = session
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [conversations, setConversations] = useState([])
  const [onlineUsers, setOnlineUsers] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [unread, setUnread] = useState({ general: 0 })
  const socketRef = useRef(null)
  const bottomRef = useRef(null)
  const seqRef = useRef(0)
  const activeIdRef = useRef(activeId)
  const conversationsRef = useRef([])
  const playNotification = useNotificationSound()

  useEffect(() => {
    activeIdRef.current = activeId
  }, [activeId])

  useEffect(() => {
    conversationsRef.current = conversations
  }, [conversations])

  const refreshConversations = useCallback(
    async (signal) => {
      try {
        const data = await authRequest('/conversations', {
          method: 'GET',
          token,
          signal,
        })
        if (signal?.aborted) return
        setConversations(
          Array.isArray(data?.conversations) ? data.conversations : [],
        )
      } catch (err) {
        if (signal?.aborted) return
        if (isAuthError(err)) {
          onAuthError()
          return
        }
        setError('Could not load conversations.')
      }
    },
    [token, onAuthError],
  )

  // Keep online users in sync while the component is mounted.
  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    const { signal } = controller

    const refreshOnline = async () => {
      try {
        const data = await authRequest('/users/online', {
          method: 'GET',
          token,
          signal,
        })
        if (signal.aborted) return
        const users = Array.isArray(data?.users) ? data.users : []
        setOnlineUsers(users.filter((item) => item.id !== user.id))
      } catch (err) {
        if (!signal.aborted && isAuthError(err)) onAuthError()
      }
    }

    const loadConversations = async () => {
      await refreshConversations(signal)
    }

    refreshOnline()
    loadConversations()
    return () => controller.abort()
  }, [token, user.id, onAuthError, refreshConversations])

  // Fetch (and refetch) history whenever the active conversation changes.
  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    const { signal } = controller

    const loadMessages = async () => {
      try {
        const path = activeId
          ? `/messages?conversation_id=${encodeURIComponent(activeId)}`
          : '/messages'
        const data = await authRequest(path, { method: 'GET', token, signal })
        if (signal.aborted) return
        setHistoryError('')
        const historyMessages = Array.isArray(data?.messages) ? data.messages : []
        setMessages((current) => mergeHistory(current, historyMessages, seqRef))
      } catch (err) {
        if (signal.aborted) return
        if (isAuthError(err)) {
          onAuthError()
          return
        }
        if (err?.status === 403) {
          setMessages([])
          setActiveId(null)
          setHistoryError('Not authorized. Showing general chat.')
          return
        }
        setHistoryError('Could not load history.')
      } finally {
        if (!signal.aborted) setLoadingHistory(false)
      }
    }

    loadMessages()
    return () => controller.abort()
  }, [token, activeId, refreshKey, onAuthError])

  useEffect(() => {
    const socket = io({ path: SOCKET_PATH, auth: { token } })
    socketRef.current = socket

    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)
    const onConnectError = (err) => {
      setConnected(false)
      if (AUTH_ERROR.test(err?.message || '')) onAuthError()
    }
    const appendMessage = (payload) => {
      setMessages((current) => {
        const id = payload?.id
        if (
          id &&
          current.some(
            (item) => item.kind === 'message' && item.payload?.id === id,
          )
        ) {
          return current
        }
        seqRef.current += 1
        return sortItems([
          ...current,
          {
            key: id || `m${seqRef.current}`,
            kind: 'message',
            payload,
            time: parseTime(payload?.created_at) ?? Date.now(),
          },
        ])
      })
    }
    const onMessage = (payload) => {
      const conversationId = payload?.conversation_id ?? null
      const isOwn = payload?.from_user_id === user.id
      const isActive = conversationId === activeIdRef.current

      // Badge first so a failing notification can never swallow it.
      if (!isOwn && !isActive) {
        const key = conversationId || 'general'
        setUnread((current) => ({
          ...current,
          [key]: (current[key] || 0) + 1,
        }))
      }

      if (isOwn) {
        if (isActive) appendMessage(payload)
        return
      }

      playNotification()

      if (
        conversationId &&
        !conversationsRef.current.some((item) => item.id === conversationId)
      ) {
        refreshConversations()
      }

      if (isActive) appendMessage(payload)
    }
    const onSystem = (payload) => {
      if (activeIdRef.current) return
      seqRef.current += 1
      setMessages((current) =>
        sortItems([
          ...current,
          {
            key: `s${seqRef.current}`,
            kind: 'system',
            payload,
            time: Date.now(),
          },
        ]),
      )
    }
    const onPresence = async () => {
      try {
        const data = await authRequest('/users/online', {
          method: 'GET',
          token,
        })
        const users = Array.isArray(data?.users) ? data.users : []
        setOnlineUsers(users.filter((item) => item.id !== user.id))
      } catch (err) {
        if (isAuthError(err)) onAuthError()
      }
    }
    const onError = (payload) => {
      setError(payload?.message || payload?.error || 'Something went wrong')
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('connect_error', onConnectError)
    socket.on('chat:message', onMessage)
    socket.on('chat:system', onSystem)
    socket.on('chat:error', onError)
    socket.on('presence:update', onPresence)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('connect_error', onConnectError)
      socket.off('chat:message', onMessage)
      socket.off('chat:system', onSystem)
      socket.off('chat:error', onError)
      socket.off('presence:update', onPresence)
      socket.disconnect()
      socketRef.current = null
    }
  }, [token, user.id, onAuthError, refreshConversations, playNotification])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeId) || null
  const text = draft.trim()
  const canSend = text.length > 0 && connected

  const formatUnread = (count) => (count > 99 ? '99+' : count)

  const openConversation = (id) => {
    setActiveId(id)
    setMessages([])
    setHistoryError('')
    setLoadingHistory(true)
    const key = id || 'general'
    setUnread((current) =>
      current[key]
        ? {
            ...current,
            [key]: 0,
          }
        : current,
    )
  }

  const startConversation = async (otherUser) => {
    setError('')
    try {
      const conversation = await authRequest('/conversations', {
        method: 'POST',
        token,
        payload: { user_ids: [otherUser.id] },
      })
      if (!conversation?.id) throw new Error('Could not start conversation')
      setConversations((current) =>
        current.some((item) => item.id === conversation.id)
          ? current
          : [conversation, ...current],
      )
      openConversation(conversation.id)
    } catch (err) {
      if (isAuthError(err)) {
        onAuthError()
        return
      }
      setError(err?.message || 'Could not start conversation')
    }
  }

  const send = (event) => {
    event.preventDefault()
    if (!canSend || !socketRef.current) return
    setError('')
    const payload = { message: text }
    if (activeId) {
      payload.private = true
      payload.conversation_id = activeId
      const other = activeConversation?.members?.find(
        (member) => member.id !== user.id,
      )
      if (other) payload.to_user_id = other.id
    }
    socketRef.current.emit('chat:message', payload)
    setDraft('')
    if (activeId) setRefreshKey((key) => key + 1)
  }

  return (
    <div className="chat">
      <header>
        <span>
          Logged in as <strong>{user.username}</strong>{' '}
          <em className={connected ? 'online' : 'offline'}>
            {connected ? 'online' : 'offline'}
          </em>
        </span>
        <button type="button" className="link" onClick={onLogout}>
          Logout
        </button>
      </header>

      <div className="chat-body">
        <aside className="sidebar">
          <section>
            <h3>Conversations</h3>
            <button
              type="button"
              className={activeId === null ? 'channel active' : 'channel'}
              onClick={() => openConversation(null)}
            >
              <span className="channel-name">General</span>
              {unread.general > 0 && (
                <span className="badge">{formatUnread(unread.general)}</span>
              )}
            </button>
            {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={
                    activeId === conversation.id ? 'channel active' : 'channel'
                  }
                  onClick={() => openConversation(conversation.id)}
                >
                  <img src={lockIcon} alt="Private" className="lock" />
                  <span className="channel-name">
                    {conversationLabel(conversation, user.id)}
                  </span>
                  {unread[conversation.id] > 0 && (
                    <span className="badge">
                      {formatUnread(unread[conversation.id])}
                    </span>
                  )}
                </button>
            ))}
          </section>

          <section>
            <h3>Online</h3>
            {onlineUsers.length === 0 ? (
              <p className="muted">No one else online</p>
            ) : (
              onlineUsers.map((onlineUser) => (
                <div key={onlineUser.id} className="online-user">
                  <span className="dot" />
                  <span className="name">{onlineUser.username}</span>
                  <button
                    type="button"
                    className="link small"
                    onClick={() => startConversation(onlineUser)}
                  >
                    Message
                  </button>
                </div>
              ))
            )}
          </section>
        </aside>

        <div className="conversation">
          <div className="conversation-title">
              {activeId
                ? (
                  <span>
                    <img src={lockIcon} alt="Private" className="lock" />
                    {conversationLabel(activeConversation, user.id)}
                  </span>
                )
                : 'General'}
          </div>

          <div className={activeId ? 'messages private' : 'messages'}>
            {loadingHistory && <p className="loading">Loading messages…</p>}
            {messages.map((item) =>
              item.kind === 'system' ? (
                <p key={item.key} className="system">
                  {item.payload.message}
                </p>
              ) : (
                <MessageItem
                  key={item.key}
                  message={item.payload}
                  userId={user.id}
                />
              ),
            )}
            <div ref={bottomRef} />
          </div>

          {historyError && <p className="error">{historyError}</p>}
          {error && <p className="error">{error}</p>}

          <form onSubmit={send}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Type a message…"
              autoFocus
            />
            <button type="submit" disabled={!canSend}>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

function MessageItem({ message, userId }) {
  const mine = message.from_user_id === userId
  return (
    <div className={mine ? 'bubble mine' : 'bubble theirs'}>
      {!mine && <span className="meta">{message.from_username}</span>}
      <span className="body">{message.body}</span>
      <span className="time">
        {new Date(message.created_at).toLocaleTimeString()}
      </span>
    </div>
  )
}
