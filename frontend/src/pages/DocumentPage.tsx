/**
 * 文档管理页面。
 * 
 * 功能：
 * 1. 上传 PDF/MD/TXT 文档
 * 2. 查看已上传的文档列表
 * 3. 删除文档
 * 4. 自动索引并可用于问答
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, Trash2, Check, X, ArrowLeft, Loader } from 'lucide-react'
import { useAuth } from '../services/auth'

const API = '/api/v1'

function getToken() { return localStorage.getItem('token') }

async function api(url: string, options: RequestInit = {}) {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const isFormData = options.body instanceof FormData
  if (!isFormData) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${API}${url}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token'); window.location.href = '/login'
    throw new Error('登录已过期')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || '请求失败')
  }
  return res.json()
}

/** 文件大小格式化 */
function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

export default function DocumentPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [docs, setDocs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadDocs = async () => {
    try { setDocs(await api('/documents')) } catch (err: any) { setError(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    loadDocs()
  }, [user])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(''); setSuccess(''); setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const result = await api('/documents/upload', { method: 'POST', body: form })
      setSuccess(`「${result.filename}」上传成功，已索引 ${result.chunk_count} 个文本块`)
      loadDocs()
    } catch (err: any) { setError(err.message) }
    finally { setUploading(false) }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除？')) return
    setError('')
    try { await api(`/documents/${id}`, { method: 'DELETE' }); setSuccess('已删除'); loadDocs() }
    catch (err: any) { setError(err.message) }
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold text-indigo-600">DataArk</h1>
          <span className="text-sm text-gray-400">|</span>
          <span className="text-sm text-gray-500">文档管理</span>
        </div>
        <span className="text-sm text-gray-500">{user.username}</span>
      </header>

      <div className="max-w-4xl mx-auto p-6">
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

        {/* 上传区域 */}
        <label className={`flex items-center justify-center gap-2 px-6 py-8 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/30 mb-6 ${uploading ? 'opacity-50' : ''}`}>
          <input type="file" accept=".pdf,.md,.txt,.docx" onChange={handleUpload} className="hidden" disabled={uploading} />
          {uploading ? <Loader size={24} className="animate-spin text-indigo-600" /> : <Upload size={24} className="text-indigo-600" />}
          <div className="text-gray-500">
            <span className="text-indigo-600 font-medium">{uploading ? '上传中...' : '点击上传文档'}</span>
            <span className="text-sm ml-2">支持 PDF / Markdown / TXT / Word</span>
          </div>
        </label>

        {/* 文档列表 */}
        {loading ? (
          <div className="text-center text-gray-400 py-12">加载中...</div>
        ) : docs.length === 0 ? (
          <div className="text-center text-gray-400 py-12">
            <FileText size={48} className="mx-auto mb-3 opacity-50" />
            <p>还没有上传文档</p>
          </div>
        ) : (
          <div className="space-y-2">
            {docs.map(d => (
              <div key={d.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-indigo-500" />
                  <div>
                    <div className="font-medium">{d.filename}</div>
                    <div className="text-sm text-gray-500 flex gap-3">
                      <span>{fmtSize(d.file_size)}</span>
                      <span>{d.file_type.toUpperCase()}</span>
                      {d.is_indexed && <span className="text-green-600">✅ 已索引 ({d.chunk_count} 块)</span>}
                      {!d.is_indexed && <span className="text-red-500">❌ 索引失败</span>}
                    </div>
                  </div>
                </div>
                <button onClick={() => handleDelete(d.id)} className="p-2 text-gray-400 hover:text-red-600">
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
