import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import DatasourcePage from './pages/DatasourcePage'
import DocumentPage from './pages/DocumentPage'
import DashboardPage from './pages/DashboardPage'
import AdminPage from './pages/AdminPage'
import { AuthProvider, useAuth } from './services/auth'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/datasources" element={<DatasourcePage />} />
        <Route path="/documents" element={<DocumentPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </AuthProvider>
  )
}

function HomePage() {
  const { user } = useAuth()

  if (user) {
    return <Navigate to="/chat" replace />
  }
  return <Navigate to="/login" replace />
}

export default App
