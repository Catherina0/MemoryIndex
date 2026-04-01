// #region 全局状态管理

import { create } from 'zustand'
import type { SearchResult } from '@/api/client'

// #region 搜索状态

interface SearchStore {
  query: string
  setQuery: (query: string) => void
  selectedTags: string[]
  setSelectedTags: (tags: string[]) => void
  results: SearchResult[]
  setResults: (results: SearchResult[]) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  total: number
  setTotal: (total: number) => void
  currentPage: number
  setCurrentPage: (page: number) => void
}

export const useSearchStore = create<SearchStore>((set) => ({
  query: '',
  setQuery: (query: string) => set({ query }),
  selectedTags: [],
  setSelectedTags: (selectedTags: string[]) => set({ selectedTags, currentPage: 1 }),
  results: [],
  setResults: (results: SearchResult[]) => set({ results }),
  isLoading: false,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
  total: 0,
  setTotal: (total: number) => set({ total }),
  currentPage: 1,
  setCurrentPage: (currentPage: number) => set({ currentPage }),
}))

// #endregion

// #endregion
