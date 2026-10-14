import { useState } from 'react'
import AuthForm from './AuthForm'
import Chat from './Chat'
import './App.css'

function App() {
  const [session, setSession] = useState(null)

  return (
    <div className="app">
      {session ? (
        <Chat user={session.user} onLogout={() => setSession(null)} />
      ) : (
        <AuthForm onAuthenticated={setSession} />
      )}
    </div>
  )
}

export default App
