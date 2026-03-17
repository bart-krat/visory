import { useState } from 'react'
import ChatView from './components/ChatView'

export default function App() {
  return (
    <div style={{ maxWidth: 600, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Visory</h1>
      <p>Plan your day with AI</p>
      <ChatView />
    </div>
  )
}
