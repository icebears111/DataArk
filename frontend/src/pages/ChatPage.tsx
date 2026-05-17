/**
 * 聊天页面。
 * 
 * 核心功能：
 * 1. 输入消息
 * 2. 发送给后端
 * 3. 流式显示回复
 * 4. 历史消息列表
 */

import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, LogOut, Database, FileText, BarChart3, Shield } from 'lucide-react'
import { useAuth } from '../services/auth'
import { chatStream } from '../services/api'
import ChatMessage from '../components/ChatMessage'

/**
 * 消息的类型。
 * 
 * TypeScript 中，用 interface 定义数据的"形状"。
 */
interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  // ---- 状态 ----
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentReply, setCurrentReply] = useState('')  // 当前正在接收的回复
  
  // ref = 引用，用来操作 DOM 元素
  // 和 state 的区别：ref 改变不会触发页面重新渲染
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  // 用 ref 跟踪实时回复内容，避免 onDone 读到旧值
  const replyRef = useRef('')

  // 自动滚到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentReply])

  // 如果没登录，跳回登录页
  useEffect(() => {
    if (!user && !localStorage.getItem('token')) {
      navigate('/login')
    }
  }, [user, navigate])

  // 自动聚焦输入框
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  /**
   * 发送消息。
   * 
   * async/await = 处理异步操作的关键字
   * async 函数返回 Promise，await 等待 Promise 完成
   */
  const handleSend = async () => {
    const message = input.trim()
    if (!message || loading) return

    setInput('')
    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setLoading(true)
    setCurrentReply('')

    try {
      // 重置 ref
      replyRef.current = ''

      // 调用流式 API
      // onToken：每收到一个字就追加
      // 同时更新 state（触发界面渲染）和 ref（供 onDone 读取）
      await chatStream(
        message,
        null,
        (token) => {
          replyRef.current += token
          setCurrentReply(replyRef.current)
        },
        () => {
          // 用 ref 拿完整的回复内容
          setMessages(prev => [...prev, { role: 'assistant', content: replyRef.current }])
          setCurrentReply('')
          setLoading(false)
        },
      )
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `错误：${err.message}` }])
      setLoading(false)
    }
  }

  /**
   * 按 Enter 发送。
   * 
   * 键盘事件：e.key === 'Enter' 表示按了回车键。
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /**
   * 退出登录。
   */
  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
    navigate('/login')
  }

  if (!user) return null

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* ---- 顶部导航栏 ---- */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-indigo-600">DataArk</h1>
          <span className="text-sm text-gray-400">|</span>
          <span className="text-sm text-gray-500">{user.username}</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/datasources')}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            <Database size={16} />
            数据源
          </button>
          <button onClick={() => navigate('/documents')}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            <FileText size={16} />
            文档
          </button>
          <button onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            <BarChart3 size={16} />
            看板
          </button>
          <button onClick={() => navigate('/admin')}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            <Shield size={16} />
            管理
          </button>
          <button onClick={handleLogout}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-500 transition-colors">
            <LogOut size={16} />
            退出
          </button>
        </div>
      </header>

      {/* ---- 消息列表 ---- */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {/* 空状态提示 */}
          {messages.length === 0 && !currentReply && (
            <div className="text-center text-gray-400 mt-20">
              <div className="text-6xl mb-4">🗄️</div>
              <p className="text-lg">欢迎使用 DataArk</p>
              <p className="text-sm mt-1">输入您的问题，AI 智能助手将为您解答</p>
            </div>
          )}

          {/* 消息列表 */}
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}

          {/* 当前正在接收的回复（流式效果） */}
          {loading && currentReply && (
            <ChatMessage message={{ role: 'assistant', content: currentReply }} />
          )}

          {/* 加载动画 */}
          {loading && !currentReply && (
            <div className="flex justify-start mb-4">
              <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}

          {/* 滚动锚点 */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ---- 输入框 ---- */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题..."
            disabled={loading}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}
