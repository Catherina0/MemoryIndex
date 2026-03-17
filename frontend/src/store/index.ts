// #region 全局状态管理

import { create } from 'zustand'
import type { SearchResult, Tag, Stats } from '@/api/client'

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
  setSelectedTags: (selectedTags: string[]) => set({ selectedTags }),
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

// #region 统计状态

interface StatsStore {
  stats: Stats | null
  setStats: (stats: Stats | null) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export const useStatsStore = create<StatsStore>((set) => ({
  stats: null,
  setStats: (stats: Stats | null) => set({ stats }),
  isLoading: false,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
}))

// #endregion

// #region 标签状态

interface TagStore {
  tags: Tag[]
  setTags: (tags: Tag[]) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export const useTagStore = create<TagStore>((set) => ({
  tags: [],
  setTags: (tags: Tag[]) => set({ tags }),
  isLoading: false,
  setIsLoading: (isLoading: boolean) => set({ isLoading }),
}))

// #endregion

// #endregion
