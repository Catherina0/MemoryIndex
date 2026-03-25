// #region SearchPage - 搜索页

import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { searchContent, listTags, type Tag } from '@/api/client'
import { useSearchStore } from '@/store'
import SearchBar from '@/components/SearchBar'
import ContentCard from '@/components/ContentCard'
import TagFilter from '@/components/TagFilter'
import Pagination from '@/components/Pagination'

export default function SearchPage() {
  const {
    query,
    setQuery,
    selectedTags,
    results,
    setResults,
    isLoading,
    setIsLoading,
    total,
    setTotal,
    currentPage,
    setCurrentPage,
  } = useSearchStore()

  const [searchParams] = useSearchParams()
  const [tags, setTags] = useState<Tag[]>([])
  const [error, setError] = useState<string>('')
  const [hasSearched, setHasSearched] = useState(false)

  const resultsPerPage = 20

  // #region 从 URL 读取搜索参数
  useEffect(() => {
    const urlQuery = searchParams.get('q')
    if (urlQuery && urlQuery.trim()) {
      setQuery(urlQuery.trim())
    }
  }, [searchParams, setQuery])
  // #endregion

  // #region 加载标签
  useEffect(() => {
    const loadTags = async () => {
      try {
        const tagsData = await listTags()
        setTags(tagsData)
      } catch (_err) {
        // 标签加载失败不阻塞搜索
      }
    }
    loadTags()
  }, [])
  // #endregion

  // #region 执行搜索
  const executeSearch = useCallback(async (q: string, tagList: string[], page: number) => {
    if (!q.trim()) return

    setIsLoading(true)
    setError('')
    setHasSearched(true)

    try {
      const offset = (page - 1) * resultsPerPage
      const response = await searchContent(
        q,
        tagList.length > 0 ? tagList : undefined,
        undefined,
        resultsPerPage,
        offset
      )
      setResults(response.results)
      setTotal(response.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || '搜索失败，请重试')
      setResults([])
      setTotal(0)
    } finally {
      setIsLoading(false)
    }
  }, [setIsLoading, setResults, setTotal])

  useEffect(() => {
    if (query) {
      executeSearch(query, selectedTags, currentPage)
    }
  }, [query, selectedTags, currentPage, executeSearch])
  // #endregion

  // #region 搜索栏提交
  const handleSearch = (q: string, _tags: string[]) => {
    setCurrentPage(1)
    setQuery(q)
  }
  // #endregion

  const totalPages = Math.ceil(total / resultsPerPage)

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 页头 */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 mb-1">搜索</h1>
        <p className="text-sm text-slate-500">在知识库中搜索视频、网页和笔记</p>
      </div>

      {/* 搜索栏 */}
      <SearchBar onSearch={handleSearch} initialValue={query} />

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200/60 text-red-700 px-4 py-3 rounded-xl text-sm animate-fade-in">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* 主体 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧：标签过滤 */}
        <div className="lg:col-span-1 order-2 lg:order-1">
          <TagFilter tags={tags} />
        </div>

        {/* 右侧：搜索结果 */}
        <div className="lg:col-span-3 order-1 lg:order-2">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="animate-spin rounded-full h-7 w-7 border-2 border-primary-600 border-t-transparent" />
              <span className="text-sm text-slate-400">搜索中...</span>
            </div>
          ) : results.length > 0 ? (
            <>
              <p className="text-sm text-slate-500 mb-4">
                找到 <span className="font-semibold text-slate-800">{total}</span> 个结果
              </p>

              <div className="space-y-2.5">
                {results.map((result) => (
                  <Link
                    key={`${result.type}-${result.id}`}
                    to={`/content/${result.id}?type=${result.type}`}
                    className="block group"
                  >
                    <ContentCard result={result} />
                  </Link>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="mt-8">
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={setCurrentPage}
                  />
                </div>
              )}
            </>
          ) : hasSearched ? (
            <div className="text-center py-20">
              <div className="text-slate-300 mb-3">
                <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <p className="text-base text-slate-500 font-medium">未找到匹配的内容</p>
              <p className="text-sm text-slate-400 mt-1">尝试调整关键词或清除标签筛选</p>
            </div>
          ) : (
            <div className="text-center py-20">
              <div className="text-slate-200 mb-3">
                <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <p className="text-slate-400">输入关键词开始搜索</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// #endregion
