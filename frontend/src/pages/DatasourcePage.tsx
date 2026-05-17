/**
 * 数据源管理页面。
 * 
 * 功能：
 * 1. 添加数据库连接（MySQL/PostgreSQL/SQLite）
 * 2. 测试连接
 * 3. 查看数据源列表
 * 4. 同步表结构
 * 5. 删除数据源
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Database, Trash2, RefreshCw, Check, X, ArrowLeft } from 'lucide-react'
import { useAuth } from '../services/auth'

// API 基础路径（通过 Vite 代理转发）
const API = '/api/v1'

function getToken() {
  return localStorage.getItem('token')
}

async function api(url: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${API}${url}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('登录已过期')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || '请求失败')
  }
  return res.json()
}

/** 数据库类型选项 */
const DB_TYPES = [
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'sqlite', label: 'SQLite' },
]

/** 新数据源表单的默认值 */
const EMPTY_FORM = {
  name: '',
  db_type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: 'root',
  password: '',
}

export default function DatasourcePage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  // 数据源列表
  const [datasources, setDatasources] = useState<any[]>([])
  // 加载状态
  const [loading, setLoading] = useState(true)
  // 是否显示添加表单
  const [showForm, setShowForm] = useState(false)
  // 表单数据
  const [form, setForm] = useState(EMPTY_FORM)
  // 错误消息
  const [error, setError] = useState('')
  // 成功消息
  const [success, setSuccess] = useState('')
  // 正在同步的数据源 ID
  const [syncing, setSyncing] = useState<number | null>(null)

  // 加载数据源列表
  const loadDatasources = async () => {
    try {
      const data = await api('/datasources')
      setDatasources(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    loadDatasources()
  }, [user])

  // 切换数据库类型时自动更新默认端口
  const handleDbTypeChange = (dbType: string) => {
    const portMap: Record<string, number> = {
      mysql: 3306,
      postgresql: 5432,
      sqlite: 0,
    }
    setForm({ ...form, db_type: dbType, port: portMap[dbType] || 3306 })
  }

  // 添加数据源
  const handleAdd = async () => {
    setError('')
    setSuccess('')
    try {
      await api('/datasources', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setSuccess('数据源添加成功')
      setShowForm(false)
      setForm(EMPTY_FORM)
      loadDatasources()
    } catch (err: any) {
      setError(err.message)
    }
  }

  // 测试连接
  const handleTest = async () => {
    setError('')
    setSuccess('')
    try {
      await api('/datasources/test', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setSuccess('连接成功！')
    } catch (err: any) {
      setError(err.message)
    }
  }

  // 同步表结构
  const handleSync = async (id: number) => {
    setError('')
    setSyncing(id)
    try {
      await api(`/datasources/${id}/sync`, { method: 'POST' })
      setSuccess('表结构同步完成')
      loadDatasources()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSyncing(null)
    }
  }

  // 删除数据源
  const handleDelete = async (id: number) => {
    if (!confirm('确定删除这个数据源？')) return
    setError('')
    try {
      await api(`/datasources/${id}`, { method: 'DELETE' })
      setSuccess('已删除')
      loadDatasources()
    } catch (err: any) {
      setError(err.message)
    }
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 导航栏 */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold text-indigo-600">DataArk</h1>
          <span className="text-sm text-gray-400">|</span>
          <span className="text-sm text-gray-500">数据源管理</span>
        </div>
        <span className="text-sm text-gray-500">{user.username}</span>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {/* 提示消息 */}
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 flex items-center gap-2">
            <X size={16} /> {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 text-green-600 p-3 rounded-lg mb-4 flex items-center gap-2">
            <Check size={16} /> {success}
          </div>
        )}

        {/* 添加按钮 */}
        <button
          onClick={() => { setShowForm(!showForm); setError(''); setSuccess('') }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 mb-6"
        >
          <Plus size={18} /> 添加数据源
        </button>

        {/* 添加表单 */}
        {showForm && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">添加数据库连接</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">名称</label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg" placeholder="例如: 生产数据库" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">数据库类型</label>
                <select value={form.db_type} onChange={e => handleDbTypeChange(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg">
                  {DB_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">主机地址</label>
                <input value={form.host} onChange={e => setForm({...form, host: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg" placeholder="localhost" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">端口</label>
                <input type="number" value={form.port} onChange={e => setForm({...form, port: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">数据库名</label>
                <input value={form.database} onChange={e => setForm({...form, database: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">用户名</label>
                <input value={form.username} onChange={e => setForm({...form, username: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">密码</label>
                <input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg" />
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={handleTest} className="px-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50">
                测试连接
              </button>
              <button onClick={handleAdd} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                保存
              </button>
            </div>
          </div>
        )}

        {/* 数据源列表 */}
        {loading ? (
          <div className="text-center text-gray-400 py-12">加载中...</div>
        ) : datasources.length === 0 ? (
          <div className="text-center text-gray-400 py-12">
            <Database size={48} className="mx-auto mb-3 opacity-50" />
            <p>还没有数据源</p>
            <p className="text-sm mt-1">点击上方按钮添加数据库连接</p>
          </div>
        ) : (
          <div className="space-y-3">
            {datasources.map(ds => (
              <div key={ds.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${ds.is_connected ? 'bg-green-500' : 'bg-red-500'}`} />
                  <div>
                    <div className="font-medium">{ds.name}</div>
                    <div className="text-sm text-gray-500">
                      {ds.db_type} · {ds.host}:{ds.port}/{ds.database}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleSync(ds.id)} disabled={syncing === ds.id}
                    className="p-2 text-gray-400 hover:text-indigo-600 disabled:opacity-50">
                    <RefreshCw size={18} className={syncing === ds.id ? 'animate-spin' : ''} />
                  </button>
                  <button onClick={() => handleDelete(ds.id)}
                    className="p-2 text-gray-400 hover:text-red-600">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
