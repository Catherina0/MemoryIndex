import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { searchContent, listTags, type Tag } from '@/api/client'
import { useSearchStore } from '@/store'
import SearchBar from '@/components/SearchBar'
import ContentCard from '@/components/ContentCard'
import TagFilter from '@/components/TagFilter'
import Pagination from '@/components/Pagination'

export default function SearchPage() {
  const {
    query,
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

  const [tags, setTags] = useState<Tag[]>([])
  const [error, setError] = useState<string>('')

  const resultsPerPage = 20

  // 加载标签
  useEffect(() => {
    const loadTags = async () => {
      try {
        const tagsData = await listTags()
        setTags(tagsData)
      } catch (err) {
        console.error('加载标签失败:', err)
      }
    }
    loadTags()
  }, [])

  // 执行搜索
  const handleSearch = async (q: string, tags: string[]) => {
    if (!q.trim()) {
      setError('请输入搜索关键词')
      return
    }

    setIsLoading(true)
    setError('')
    setCurrentPage(1)

    try {
      const offset = 0
      const response = await searchContent(q, tags.length > 0 ? tags : undefined, undefined, resultsPerPage, offset)
      setResults(response.results)
      setTotal(response.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || '搜索失败，请重试')
      setResults([])
      setTotal(0)
    } finally {
      setIsLoading(false)
    }
  }

  // 分页处理
  useEffect(() => {
    if (!query) return

    const offset = (currentPage - 1) * resultsPerPage
    const loadPage = async () => {
      setIsLoading(true)
      try {
        const response = await searchContent(query, selectedTags.length > 0 ? selectedTags : undefined, undefined, resultsPerPage, offset)
        setResults(response.results)
        setTotal(response.total)
      } catch (err) {
        console.error('搜索失败:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadPage()
  }, [currentPage, query, selectedTags])

  const totalPages = Math.ceil(total / resultsPerPage)

  return (
    <div className="space-y-8">
      <SearchBar onSearch={handleSearch} />

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded-lg">
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
              <div className="animate-spin rounded-full h-8 w-8 border border-primary border-t-transparent"></div>
            </div>
          ) : results.length > 0 ? (
            <>
              <div className="text-sm text-gray-600 mb-4">
                找到 <span className="font-semibold text-gray-900">{total}</span> 个结果
              </div>

              <div className="space-y-4">
                {results.map((result) => (
                  <Link
                    key={`${result.type}-${result.id}`}
                    to={`/content/${result.id}?type=${result.type}`}
                    className="block hover:no-underline"
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
          ) : query ? (
            <div className="text-center py-12 text-gray-600">
              <p>未找到匹配的内容</p>
              <p className="text-sm mt-2">尝试调整搜索关键词或筛选条件</p>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-600">
              <p>输入关键词开始搜索</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
