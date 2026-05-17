/**
 * 单条聊天消息组件。
 * 
 * 根据是谁发的（用户 or AI），显示不同的样式。
 */

import React from 'react'

/**
 * Message 的类型定义。
 */
interface Message {
  role: 'user' | 'assistant'  // 谁发的
  content: string              // 内容
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`
          max-w-[80%] px-4 py-3 rounded-2xl
          ${isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100'}
        `}
      >
        {/* AI 消息显示角色标签 */}
        {!isUser && (
          <div className="text-xs text-indigo-500 font-medium mb-1">DataArk</div>
        )}
        {/* 消息内容 */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    </div>
  )
}
