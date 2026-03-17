// #region 布局组件

import React from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 导航栏 */}
      <nav className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <span className="text-2xl">📚</span>
              <span className="text-xl font-bold text-gray-900">MemoryIndex</span>
            </Link>

            {/* 导航链接 */}
            <div className="hidden md:flex items-center gap-8">
              <Link
                to="/"
                className={`font-medium transition-colors ${
                  isActive('/')
                    ? 'text-primary border-b-2 border-primary pb-2'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                首页
              </Link>
              <Link
                to="/search"
                className={`font-medium transition-colors ${
                  isActive('/search')
                    ? 'text-primary border-b-2 border-primary pb-2'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                搜索
              </Link>
              <Link
                to="/dashboard"
                className={`font-medium transition-colors ${
                  isActive('/dashboard')
                    ? 'text-primary border-b-2 border-primary pb-2'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                统计
              </Link>
            </div>

            {/* 功能按钮 */}
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/Catherina0/MemoryIndex"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                💻 GitHub
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* 页脚 */}
      <footer className="bg-gray-900 text-gray-300 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
            <div>
              <h3 className="text-white font-bold mb-4">MemoryIndex</h3>
              <p className="text-sm">
                基于 AI 代理的个人知识管理系统。将互联网内容转化为结构化知识库。
              </p>
            </div>
            <div>
              <h4 className="text-white font-bold mb-4">功能</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    📹 视频处理
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    🕸️ 网页归档
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    🔍 全文搜索
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-bold mb-4">社区</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a
                    href="https://github.com/Catherina0/MemoryIndex"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    GitHub 仓库
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    文档
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-white transition-colors">
                    反馈
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-700 pt-8 text-center text-sm">
            <p>&copy; 2025 MemoryIndex. 基于 GPLv3+ 开源。</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

// #endregion
