/**
 * 统计看板页面。
 * 
 * 展示数据源、文档、系统使用情况等概览数据。
 * 使用 SVG 实现简单的柱状图，不依赖第三方图表库。
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Database, FileText, Activity, Server, ArrowLeft } from 'lucide-react'
import { useAuth } from '../services/auth'

const API = '/api/v1'
function getToken() { return localStorage.getItem('token') }

async function api(url: string) {
  const res = await fetch(`${API}${url}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
  if (!res.ok) throw new Error('请求失败')
  return res.json()
}

/** 统计卡片组件 */
function StatCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode; label: string; value: number | string; sub?: string; color: string
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">{label}</span>
        <span className={`p-2 rounded-lg ${color}`}>{icon}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

/** 简单柱状图组件 */
function BarChart({ data, title }: { data: { label: string; value: number; color?: string }[]; title: string }) {
  const maxVal = Math.max(...data.map(d => d.value), 1)
  const colors = ['bg-indigo-500', 'bg-emerald-500', 'bg-amber-500', 'bg-rose-500', 'bg-cyan-500']

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h3 className="text-sm font-medium text-gray-700 mb-4">{title}</h3>
      <div className="space-y-3">
        {data.map((d, i) => (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{d.label}</span>
              <span className="text-gray-900 font-medium">{d.value}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2.5">
              <div
                className={`h-2.5 rounded-full transition-all duration-500 ${d.color || colors[i % colors.length]}`}
                style={{ width: `${(d.value / maxVal) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [summary, setSummary] = useState<any>(null)
  const [dsStats, setDsStats] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    Promise.all([
      api('/analytics/summary'),
      api('/analytics/datasources'),
    ]).then(([s, d]) => {
      setSummary(s)
      setDsStats(d)
    }).catch(console.error).finally(() => setLoading(false))
  }, [user])

  if (!user) return null

  const chartData = dsStats.map((d: any) => ({
    label: d.type.toUpperCase(),
    value: d.count,
  }))

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold text-indigo-600">DataArk</h1>
          <span className="text-sm text-gray-400">|</span>
          <span className="text-sm text-gray-500">统计看板</span>
        </div>
        <span className="text-sm text-gray-500">{user.username}</span>
      </header>

      <div className="max-w-5xl mx-auto p-6">
        {loading ? (
          <div className="text-center text-gray-400 py-20">加载中...</div>
        ) : (
          <>
            {/* 概览卡片 */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard
                icon={<Database size={18} className="text-indigo-600" />}
                label="数据源"
                value={summary?.datasource_count || 0}
                sub={`${summary?.datasource_connected || 0} 个在线`}
                color="bg-indigo-50"
              />
              <StatCard
                icon={<FileText size={18} className="text-emerald-600" />}
                label="文档"
                value={summary?.document_count || 0}
                sub={`${summary?.document_indexed || 0} 个已索引`}
                color="bg-emerald-50"
              />
              <StatCard
                icon={<Server size={18} className="text-amber-600" />}
                label="数据库类型"
                value={dsStats.length || 0}
                sub="种数据库"
                color="bg-amber-50"
              />
              <StatCard
                icon={<Activity size={18} className="text-rose-600" />}
                label="系统状态"
                value="运行中"
                sub="FastAPI + LangChain"
                color="bg-rose-50"
              />
            </div>

            {/* 图表区域 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {chartData.length > 0 && (
                <BarChart data={chartData} title="数据源类型分布" />
              )}
              {(summary?.document_count || 0) > 0 && (
                <BarChart
                  data={[
                    { label: '已索引', value: summary?.document_indexed || 0, color: 'bg-emerald-500' },
                    { label: '未索引', value: (summary?.document_count || 0) - (summary?.document_indexed || 0), color: 'bg-gray-400' },
                    { label: '总计', value: summary?.document_count || 0, color: 'bg-indigo-500' },
                  ]}
                  title="文档索引状态"
                />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
