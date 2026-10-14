import { useEffect, useRef, useState } from 'react'
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

export default function Chat({ session, onLogout, onAuthError }) {
  const { user, token } = session
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')
  const [loadingHistory, setLoadingHistory] = useState(false)
  const socketRef = useRef(null)
  const bottomRef = useRef(null)
  const seqRef = useRef(0)

  useEffect(() => {
    const socket = io({ path: SOCKET_PATH, auth: { token } })
    socketRef.current = socket

    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)
    const onConnectError = (err) => {
      setConnected(false)
      if (AUTH_ERROR.test(err?.message || '')) onAuthError()
    }
    const onMessage = (payload) => {
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
    const onSystem = (payload) => {
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
    const onError = (payload) => {
      setError(payload?.message || payload?.error || 'Something went wrong')
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('connect_error', onConnectError)
    socket.on('chat:message', onMessage)
    socket.on('chat:system', onSystem)
    socket.on('chat:error', onError)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('connect_error', onConnectError)
      socket.off('chat:message', onMessage)
      socket.off('chat:system', onSystem)
      socket.off('chat:error', onError)
      socket.disconnect()
      socketRef.current = null
    }
  }, [token, onAuthError])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!token) return undefined
    const controller = new AbortController()
    const { signal } = controller
    let cancelled = false

    const loadHistory = async () => {
      setHistoryError('')
      setLoadingHistory(true)
      try {
        const data = await authRequest('/messages', {
          method: 'GET',
          token,
          signal,
        })
        if (cancelled || signal.aborted) return
        const historyMessages = Array.isArray(data?.messages) ? data.messages : []
        if (historyMessages.length > 0) {
          setMessages((current) => {
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
          })
        }
      } catch (err) {
        if (cancelled || signal.aborted) return
        const msg = err?.message || ''
        if (err?.status === 401 || AUTH_ERROR.test(msg)) {
          onAuthError()
          return
        }
        setHistoryError('Could not load history.')
      } finally {
        if (!cancelled && !signal.aborted) {
          setLoadingHistory(false)
        }
      }
    }

    loadHistory()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [token, onAuthError])

  const text = draft.trim()
  const canSend = text.length > 0 && connected

  const send = (event) => {
    event.preventDefault()
    if (!canSend || !socketRef.current) return
    setError('')
    socketRef.current.emit('chat:message', { message: text })
    setDraft('')
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

      <div className="messages">
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
