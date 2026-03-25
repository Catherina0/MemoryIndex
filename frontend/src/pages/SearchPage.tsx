import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { searchContent, listTags, type Tag } from '@/api/client'
import { useSearchStore } from '@/store'
import SearchBar from '@/components/SearchBar'
import ContentCard from '@/components/ContentCard'
import TagFilter from '@/components/TagFilter'
import Pagination from '@/components/Pagination'

// #region SearchPage
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

  // query / selectedTags / currentPage 变化时自动搜索
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
    <div className="space-y-6">
      <SearchBar onSearch={handleSearch} initialValue={query} />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧：标签过滤 */}
        <div className="lg:col-span-1">
          <TagFilter tags={tags} />
        </div>

        {/* 右侧：搜索结果 */}
        <div className="lg:col-span-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
            </div>
          ) : results.length > 0 ? (
            <>
              <p className="text-sm text-gray-500 mb-4">
                找到 <span className="font-medium text-gray-900">{total}</span> 个结果
              </p>

              <div className="space-y-3">
                {results.map((result) => (
                  <Link
                    key={`${result.type}-${result.id}`}
                    to={`/content/${result.id}?type=${result.type}`}
                    className="block"
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
            <div className="text-center py-16 text-gray-500">
              <p className="text-base">未找到匹配的内容</p>
              <p className="text-sm mt-1">尝试调整搜索关键词或筛选条件</p>
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400">
              <p>输入关键词开始搜索</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
// #endregion
