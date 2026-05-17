/**
 * 登录/注册页面。
 * 
 * React 组件 = 返回 JSX 的函数。
 * useState 管理"状态"——数据变了页面自动更新。
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../services/api'
import { useAuth } from '../services/auth'

export default function LoginPage() {
  // useNavigate = 页面跳转
  const navigate = useNavigate()
  // useAuth = 获取全局认证状态
  const { setUser } = useAuth()

  // useState = 状态管理
  // [值, 设置值的函数]
  const [isRegister, setIsRegister] = useState(false)  // 登录还是注册？
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()  // 阻止表单默认提交行为
    setError('')
    setLoading(true)

    try {
      // 注册或登录
      if (isRegister) {
        await register(username, email, password)
      }
      // 登录获取 token
      const result = await login(username, password)
      localStorage.setItem('token', result.access_token)
      // 获取用户信息
      const me = await (await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${result.access_token}` },
      })).json()
      setUser(me)
      // 跳转到聊天页
      navigate('/chat')
    } catch (err: any) {
      setError(err.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-indigo-600">DataArk</h1>
          <p className="text-gray-500 mt-2">AI 数据智能平台</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              placeholder="请输入用户名"
              required
            />
          </div>

          {/* 注册时才显示邮箱 */}
          {isRegister && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                placeholder="请输入邮箱"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              placeholder="请输入密码"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {loading ? '处理中...' : isRegister ? '注册' : '登录'}
          </button>
        </form>

        {/* 切换登录/注册 */}
        <div className="mt-4 text-center text-sm text-gray-500">
          {isRegister ? '已有账号？' : '没有账号？'}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-indigo-600 hover:underline ml-1"
          >
            {isRegister ? '去登录' : '去注册'}
          </button>
        </div>
      </div>
    </div>
  )
}
