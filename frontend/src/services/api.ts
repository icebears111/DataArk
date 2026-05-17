/**
 * API 调用工具。
 * 
 * fetch 是浏览器内置的 HTTP 请求 API。
 * 这里封装了几个常用函数，方便调用后端接口。
 */

// 后端 API 的基础 URL
// 开发时 Vite 的代理会把 /api 转发到后端
const BASE_URL = '/api/v1'

/**
 * 从 localStorage 获取 token。
 * 
 * localStorage 是浏览器自带的"小数据库"，
 * 关闭页面后数据还在。
 * 登录成功后我们把 token 存这里。
 */
function getToken(): string | null {
  return localStorage.getItem('token')
}

/**
 * 通用的请求函数。
 * 
 * @param url - API 路径（如 /auth/login）
 * @param options - 请求选项（body, method 等）
 * @returns 解析后的 JSON 数据
 */
async function request(url: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  })

  // 先尝试解析错误信息
  const errorData = !response.ok ? await response.json().catch(() => null) : null

  // 只有登录后的接口返回 401 才是 token 过期
  if (response.status === 401 && !url.includes('/auth/login') && !url.includes('/auth/register')) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('登录已过期')
  }

  if (!response.ok) {
    throw new Error(errorData?.detail || '请求失败')
  }

  return response.json()
}

// ----- 导出给组件使用的函数 -----

/**
 * 登录。
 */
export async function login(username: string, password: string) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

/**
 * 注册。
 */
export async function register(username: string, email: string, password: string) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  })
}

/**
 * 获取当前用户信息。
 */
export async function getMe() {
  return request('/auth/me')
}

/**
 * 聊天（非流式）。
 */
export async function chat(message: string, sessionId?: string) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  })
}

/**
 * 聊天（流式）。
 * 
 * SSE = Server-Sent Events
 * 后端一个字一个字地返回，前端实时展示。
 * 用 ReadableStream 来读取。
 * 
 * @param onToken - 每收到一个字就调用一次
 * @param onDone - 完成后调用
 */
export async function chatStream(
  message: string,
  sessionId: string | null,
  onToken: (token: string) => void,
  onDone: () => void,
) {
  const token = getToken()

  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  })

  if (response.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('登录已过期')
  }
  if (!response.ok) {
    throw new Error('聊天请求失败')
  }

  // ReadableStream = 可读流
  // 后端发来的数据是一块一块的，我们一块一块读
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    // SSE 格式：data: {"token": "你"}
    // 每行以 "data: " 开头
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.token) {
            onToken(data.token)
          }
          if (data.done) {
            onDone()
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}
