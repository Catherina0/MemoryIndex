// #region 布局组件

import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

// #region 导航链接配置
const navLinks = [
  { path: '/', label: '首页' },
  { path: '/archives', label: '存档库' },
  { path: '/search', label: '搜索' },
  { path: '/dashboard', label: '统计' },
]
// #endregion

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 导航栏 */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2 group">
              <span className="text-lg font-bold text-gray-900 tracking-tight group-hover:text-blue-600 transition-colors">
                MemoryIndex
              </span>
            </Link>

            {/* 导航链接 */}
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map(({ path, label }) => (
                <Link
                  key={path}
                  to={path}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    isActive(path)
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>

            {/* GitHub */}
            <a
              href="https://github.com/Catherina0/MemoryIndex"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </nav>

      {/* 主内容区 */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-1">
        {children}
      </main>

      {/* 页脚 */}
      <footer className="border-t border-gray-200 bg-white py-6 mt-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500">
          <p>&copy; 2025 MemoryIndex. GPLv3+</p>
          <div className="flex items-center gap-4">
            <Link to="/archives" className="hover:text-gray-900 transition-colors">存档库</Link>
            <Link to="/search" className="hover:text-gray-900 transition-colors">搜索</Link>
            <Link to="/dashboard" className="hover:text-gray-900 transition-colors">统计</Link>
            <a
              href="https://github.com/Catherina0/MemoryIndex"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-gray-900 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

// #endregion
