import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// React 18 的新写法：createRoot 替代 ReactDOM.render
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/*
      BrowserRouter 提供路由功能
      让页面可以根据 URL 切换而不刷新
    */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
