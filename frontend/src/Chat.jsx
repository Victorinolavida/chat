import { useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'

export default function Chat({ user, onLogout }) {
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [connected, setConnected] = useState(false)
  const socketRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    const socket = io({ auth: { username: user.username } })
    socketRef.current = socket

    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))
    socket.on('message', (message) => setMessages((current) => [...current, message]))
    socket.on('system', (message) => setMessages((current) => [...current, message]))

    return () => socket.disconnect()
  }, [user.username])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = (event) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || !socketRef.current) return
    socketRef.current.emit('message', { username: user.username, message: text })
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
        {messages.map((message, index) => (
          <p key={index} className={message.username === user.username ? 'mine' : ''}>
            <span className="meta">
              {message.username} · {new Date(message.timestamp).toLocaleTimeString()}
            </span>
            {message.message}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Type a message…"
          autoFocus
        />
        <button type="submit">Send</button>
      </form>
    </div>
  )
}
