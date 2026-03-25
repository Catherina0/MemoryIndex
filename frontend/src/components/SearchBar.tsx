import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearchStore } from '@/store'

// #region SearchBar 组件
interface SearchBarProps {
  /** 如果提供 onSearch，则直接调用；否则跳转到 /search 页面 */
  onSearch?: (query: string, tags: string[]) => void
  placeholder?: string
  /** 外部设置的初始值（用于从 URL 参数初始化） */
  initialValue?: string
}

export default function SearchBar({ onSearch, placeholder = '搜索知识库...', initialValue }: SearchBarProps) {
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

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pr-20 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          type="submit"
          className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-blue-600 text-white px-4 py-1.5 rounded-md text-sm hover:bg-blue-700 transition-colors font-medium"
        >
          搜索
        </button>
      </div>
    </form>
  )
}
// #endregion
