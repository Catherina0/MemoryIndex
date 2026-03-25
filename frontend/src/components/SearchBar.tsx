// #region SearchBar 组件

import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearchStore } from '@/store'

interface SearchBarProps {
  onSearch?: (query: string, tags: string[]) => void
  placeholder?: string
  initialValue?: string
  size?: 'normal' | 'large'
}

export default function SearchBar({
  onSearch,
  placeholder = '搜索知识库...',
  initialValue,
  size = 'normal',
}: SearchBarProps) {
  const navigate = useNavigate()
  const { setQuery, setSelectedTags, setCurrentPage } = useSearchStore()
  const [input, setInput] = useState(initialValue || '')

  useEffect(() => {
    if (initialValue !== undefined) {
      setInput(initialValue)
    }
  }, [initialValue])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    setQuery(input.trim())
    setSelectedTags([])
    setCurrentPage(1)

    if (onSearch) {
      onSearch(input.trim(), [])
    } else {
      navigate(`/search?q=${encodeURIComponent(input.trim())}`)
    }
  }

  const isLarge = size === 'large'

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative group">
        {/* 搜索图标 */}
        <svg
          className={`absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500 transition-colors ${
            isLarge ? 'w-5 h-5' : 'w-4 h-4'
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          className={`w-full bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400
            focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400
            transition-all duration-200 ${
              isLarge
                ? 'pl-11 pr-24 py-3.5 text-base rounded-2xl shadow-card'
                : 'pl-10 pr-20 py-2.5 text-sm rounded-xl'
            }`}
        />

        <button
          type="submit"
          className={`absolute right-1.5 top-1/2 -translate-y-1/2 btn-primary ${
            isLarge ? 'px-5 py-2 text-sm' : 'px-4 py-1.5 text-xs'
          }`}
        >
          搜索
        </button>
      </div>
    </form>
  )
}

// #endregion
