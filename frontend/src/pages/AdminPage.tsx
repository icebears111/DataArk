/**
 * 管理后台页面。
 * 
 * 管理员专用，提供用户管理和审计日志查看功能。
 * 普通用户打开此页面会看到无权限提示。
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, ClipboardList, Shield, ArrowLeft, ShieldAlert } from 'lucide-react'
import { useAuth } from '../services/auth'

const API = '/api/v1'
function getToken() { return localStorage.getItem('token') }

async function api(url: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API}${url}`, { ...options, headers })
  if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
  if (res.status === 403) { throw new Error('需要管理员权限') }
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(err?.detail || '请求失败') }
  return res.json()
}

export default function AdminPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'users' | 'audit'>('users')
  const [users, setUsers] = useState<any[]>([])
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isAdmin, setIsAdmin] = useState(true)

  const loadUsers = async () => {
    try { setUsers(await api('/admin/users')) } catch (err: any) { setError(err.message); setIsAdmin(false) }
  }

  const loadAudit = async () => {
    try { const r = await api('/admin/audit-logs?limit=100'); setAuditLogs(r.logs) } catch (err: any) { setError(err.message) }
  }

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    Promise.all([loadUsers(), loadAudit()]).finally(() => setLoading(false))
  }, [user])

  const handleSetRole = async (userId: number, role: string) => {
    setError('')
    try {
      await api(`/admin/users/${userId}/role`, {
        method: 'PUT', body: JSON.stringify({ role }),
      })
      loadUsers()
    } catch (err: any) { setError(err.message) }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('确定删除这个用户？')) return
    setError('')
    try {
      await api(`/admin/users/${userId}`, { method: 'DELETE' })
      loadUsers()
    } catch (err: any) { setError(err.message) }
  }

  if (!user) return null
  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <ShieldAlert size={48} className="mx-auto mb-4 text-red-400" />
          <p className="text-lg text-gray-600">需要管理员权限</p>
          <button onClick={() => navigate('/chat')} className="mt-4 text-indigo-600 hover:underline">返回聊天</button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold text-indigo-600">DataArk</h1>
          <span className="text-sm text-gray-400">|</span>
          <span className="text-sm text-gray-500">管理后台</span>
        </div>
        <span className="text-sm text-gray-500">{user.username}</span>
      </header>

      <div className="max-w-5xl mx-auto p-6">
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4">{error}</div>
        )}

        {/* 标签切换 */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setTab('users')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg ${tab === 'users' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'}`}
          ><Users size={16} /> 用户管理</button>
          <button
            onClick={() => setTab('audit')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg ${tab === 'audit' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'}`}
          ><ClipboardList size={16} /> 审计日志</button>
        </div>

        {/* 用户管理 */}
        {tab === 'users' && (
          <div className="bg-white rounded-xl shadow-sm border">
            <table className="w-full">
              <thead>
                <tr className="border-b text-sm text-gray-500">
                  <th className="text-left p-4">ID</th>
                  <th className="text-left p-4">用户名</th>
                  <th className="text-left p-4">邮箱</th>
                  <th className="text-left p-4">角色</th>
                  <th className="text-left p-4">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-4 text-sm">{u.id}</td>
                    <td className="p-4 font-medium">{u.username}</td>
                    <td className="p-4 text-sm text-gray-500">{u.email}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs ${u.role === 'admin' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}`}>
                        {u.role === 'admin' ? '管理员' : '用户'}
                      </span>
                    </td>
                    <td className="p-4 flex gap-2">
                      {u.role !== 'admin' && (
                        <button onClick={() => handleSetRole(u.id, 'admin')}
                          className="text-xs px-2 py-1 border border-indigo-600 text-indigo-600 rounded hover:bg-indigo-50">
                          设为管理员
                        </button>
                      )}
                      {u.role === 'admin' && u.id !== user.id && (
                        <button onClick={() => handleSetRole(u.id, 'user')}
                          className="text-xs px-2 py-1 border border-gray-300 text-gray-500 rounded hover:bg-gray-50">
                          取消管理
                        </button>
                      )}
                      {u.id !== user.id && (
                        <button onClick={() => handleDeleteUser(u.id)}
                          className="text-xs px-2 py-1 border border-red-300 text-red-500 rounded hover:bg-red-50">
                          删除
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 审计日志 */}
        {tab === 'audit' && (
          <div className="bg-white rounded-xl shadow-sm border">
            {auditLogs.length === 0 ? (
              <div className="text-center text-gray-400 py-12">暂无审计日志</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b text-sm text-gray-500">
                    <th className="text-left p-4">时间</th>
                    <th className="text-left p-4">用户</th>
                    <th className="text-left p-4">操作</th>
                    <th className="text-left p-4">状态</th>
                    <th className="text-left p-4">详情</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log: any) => (
                    <tr key={log.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="p-4 text-sm text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="p-4 text-sm">{log.username}</td>
                      <td className="p-4 text-sm font-medium">{log.action}</td>
                      <td className="p-4">
                        <span className={`text-xs px-2 py-1 rounded ${log.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {log.success ? '成功' : '失败'}
                        </span>
                      </td>
                      <td className="p-4 text-xs text-gray-400 max-w-xs truncate">{log.detail || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
