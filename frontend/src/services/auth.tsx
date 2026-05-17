/**
 * 认证上下文（Context）。
 * 
 * React Context 是一种"全局状态"机制。
 * 不用一层层传 props，所有子组件都能直接读到。
 * 
 * 这里用来管理用户登录状态，整个应用都能用。
 */

import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { getMe } from './api'

/**
 * 用户信息的类型定义。
 * TypeScript 用 interface 定义对象的结构。
 */
interface User {
  id: number
  username: string
  email: string
}

/**
 * AuthContext 的类型。
 * 
 * ? 表示可选（可能是 null）
 */
interface AuthContextType {
  user: User | null        // 当前用户
  loading: boolean          // 是否正在加载
  setUser: (user: User | null) => void  // 设置用户
}

// 创建 Context（默认值 = undefined）
const AuthContext = createContext<AuthContextType | undefined>(undefined)

/**
 * AuthProvider：包裹整个应用，提供认证状态。
 * 
 * 在 App.tsx 里：
 *   <AuthProvider>
 *     <Routes>...</Routes>
 *   </AuthProvider>
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // useEffect：组件加载时自动执行
  // 这里检查 localStorage 里有没有 token
  // 如果有，尝试获取用户信息（实现"自动登录"）
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * useAuth：获取认证状态的 Hook。
 * 
 * Hook 是 React 的一种函数，以 use 开头。
 * 在任意组件里调用 useAuth() 就能拿到 user 和 setUser。
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
