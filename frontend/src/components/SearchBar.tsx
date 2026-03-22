import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearchStore } from '@/store'

interface SearchBarProps {
  onSearch?: (query: string, tags: string[]) => void
  placeholder?: string
}

export default function SearchBar({ onSearch, placeholder = '搜索内容...' }: SearchBarProps) {
  const navigate = useNavigate()
  const { setQuery, setSelectedTags, setCurrentPage } = useSearchStore()
  const [input, setInput] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()

    if (!input.trim()) {
      return
    }

    setQuery(input)
    setSelectedTags([])
    setCurrentPage(1)

    if (onSearch) {
      onSearch(input, [])
    } else {
      navigate(`/search?q=${encodeURIComponent(input)}`)
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
          className="w-full px-4 py-3 pl-12 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent shadow-md"
        />
        <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
          🔍
        </span>
        <button
          type="submit"
          className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-primary text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors font-medium"
        >
          搜索
        </button>
      </div>
    </form>
  )
}
