import { useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'

const AUTH_ERROR = /auth|token|jwt|expired|unauthor|forbidden/i

export default function Chat({ session, onLogout, onAuthError }) {
  const { user, token } = session
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const socketRef = useRef(null)
  const bottomRef = useRef(null)
  const seqRef = useRef(0)

  useEffect(() => {
    const socket = io({ auth: { token } })
    socketRef.current = socket

    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)
    const onConnectError = (err) => {
      setConnected(false)
      if (AUTH_ERROR.test(err?.message || '')) onAuthError()
    }
    const onMessage = (payload) => {
      seqRef.current += 1
      setMessages((current) => [
        ...current,
        { key: `m${seqRef.current}`, kind: 'message', payload },
      ])
    }
    const onSystem = (payload) => {
      seqRef.current += 1
      setMessages((current) => [
        ...current,
        { key: `s${seqRef.current}`, kind: 'system', payload },
      ])
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
