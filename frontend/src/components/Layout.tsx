// #region 布局组件

import { type ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

// #region SVG 图标
function IconHome({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? 'text-primary-600' : 'text-slate-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" />
    </svg>
  )
}

function IconLibrary({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? 'text-primary-600' : 'text-slate-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  )
}

function IconSearch({ active }: { active: boolean }) {
  return (
    <svg className={`w-4 h-4 ${active ? 'text-primary-600' : 'text-slate-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  )
}

function IconMenu() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  )
}

function IconClose() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}
// #endregion

// #region 导航链接配置
const navLinks = [
  { path: '/', label: '首页', Icon: IconHome },
  { path: '/archives', label: '资料库', Icon: IconLibrary },
  { path: '/search', label: '搜索', Icon: IconSearch },
]
// #endregion

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-surface-50 flex flex-col">
      {/* #region 导航栏 */}
      <nav className="glass-nav sticky top-0 z-50 shadow-nav">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-sm">
                <span className="text-white text-xs font-bold">M</span>
              </div>
              <span className="text-base font-semibold text-slate-900 tracking-tight">
                MemoryIndex
              </span>
            </Link>

            {/* 桌面导航 */}
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map(({ path, label, Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive(path)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100/80'
                  }`}
                >
                  <Icon active={isActive(path)} />
                  {label}
                </Link>
              ))}
            </div>

            {/* 移动端菜单按钮 */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100"
            >
              {mobileMenuOpen ? <IconClose /> : <IconMenu />}
            </button>
          </div>
        </div>

        {/* 移动端菜单 */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200/60 bg-white animate-fade-in">
            <div className="px-4 py-3 space-y-1">
              {navLinks.map(({ path, label, Icon }) => (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive(path)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon active={isActive(path)} />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>
      {/* #endregion */}

      {/* #region 主内容区 */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {children}
      </main>
      {/* #endregion */}

      {/* #region 页脚 */}
      <footer className="border-t border-slate-200/60 bg-white/50 py-5 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-slate-400">
          <span>&copy; 2025 MemoryIndex</span>
          <span>GPLv3+</span>
        </div>
      </footer>
      {/* #endregion */}
    </div>
  )
}

// #endregion
