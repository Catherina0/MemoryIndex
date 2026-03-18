import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listVideos, listArchives, listTags, type Tag, type ContentListItem } from '@/api/client'
import ContentCard from '@/components/ContentCard'
import Pagination from '@/components/Pagination'

export default function ArchiveListPage() {
  const [activeTab, setActiveTab] = useState<'all' | 'videos' | 'archives'>('all')
  const [sortBy, setSortBy] = useState<'recent' | 'oldest' | 'duration'>('recent')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  
  const [items, setItems] = useState<ContentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [tags, setTags] = useState<Tag[]>([])
  
  const itemsPerPage = 20

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

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      try {
        const offset = (currentPage - 1) * itemsPerPage
        
        let response
        if (activeTab === 'videos') {
          response = await listVideos(itemsPerPage, offset, sortBy)
        } else if (activeTab === 'archives') {
          response = await listArchives(itemsPerPage, offset, sortBy)
        } else {
          // 全部：先加载视频再加载网页
          const [videosRes, archivesRes] = await Promise.all([
            listVideos(itemsPerPage, offset, sortBy),
            listArchives(itemsPerPage, offset, sortBy)
          ])
          response = {
            items: [...videosRes.items, ...archivesRes.items],
            total: videosRes.total + archivesRes.total,
            limit: itemsPerPage,
            offset
          }
        }
        
        // 过滤标签
        let filtered = response.items
        if (selectedTags.length > 0) {
          filtered = filtered.filter(item =>
            selectedTags.some(tag => item.tags.includes(tag))
          )
        }
        
        setItems(filtered)
        setTotal(selectedTags.length > 0 ? filtered.length : response.total)
      } catch (err) {
        console.error('加载数据失败:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [activeTab, sortBy, currentPage, selectedTags])

  const handleTagToggle = (tagName: string) => {
    setSelectedTags(prev =>
      prev.includes(tagName)
        ? prev.filter(t => t !== tagName)
        : [...prev, tagName]
    )
    setCurrentPage(1) // 重置分页
  }

  const totalPages = Math.ceil(total / itemsPerPage)

  return (
    <div className="space-y-8">
      {/* 标题 */}
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">📚 全部存档</h1>
        <p className="text-gray-600">共 {total} 条内容</p>
      </div>

      {/* 标签过滤 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">🏷️ 按标签过滤</h2>
        <div className="flex flex-wrap gap-2">
          {tags.slice(0, 30).map(tag => (
            <button
              key={tag.id}
              onClick={() => handleTagToggle(tag.name)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                selectedTags.includes(tag.name)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
              }`}
            >
              {tag.name} ({tag.count})
            </button>
          ))}
        </div>
        {selectedTags.length > 0 && (
          <button
            onClick={() => setSelectedTags([])}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium text-sm"
          >
            清除筛选
          </button>
        )}
      </div>

      {/* 控制条 */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* 标签页 */}
        <div className="flex gap-2">
          <button
            onClick={() => { setActiveTab('all'); setCurrentPage(1) }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => { setActiveTab('videos'); setCurrentPage(1) }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'videos'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
            }`}
          >
            视频
          </button>
          <button
            onClick={() => { setActiveTab('archives'); setCurrentPage(1) }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'archives'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
            }`}
          >
            网页
          </button>
        </div>

        {/* 排序 */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">排序：</label>
          <select
            value={sortBy}
            onChange={(e) => { setSortBy(e.target.value as any); setCurrentPage(1) }}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="recent">最近添加</option>
            <option value="oldest">最早添加</option>
            <option value="duration">时长长短</option>
          </select>
        </div>
      </div>

      {/* 内容列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border border-primary border-t-transparent"></div>
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="space-y-4">
            {items.map((item) => (
              <Link
                key={`${item.type}-${item.id}`}
                to={`/content/${item.id}?type=${item.type}`}
                className="block hover:no-underline"
              >
                <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold px-2 py-1 rounded bg-blue-100 text-blue-800">
                          {item.type === 'video' ? '📹 视频' : '📄 网页'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {item.source_type}
                        </span>
                        {item.duration && (
                          <span className="text-xs text-gray-500">
                            ⏱️ {Math.floor(item.duration / 60)}分
                          </span>
                        )}
                      </div>
                      <h3 className="text-lg font-bold text-gray-900 mb-1 line-clamp-2">
                        {item.title}
                      </h3>
                      <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                        {item.summary || '暂无摘要'}
                      </p>
                      {item.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {item.tags.slice(0, 5).map(tag => (
                            <span
                              key={tag}
                              className="inline-block bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs"
                            >
                              #{tag}
                            </span>
                          ))}
                          {item.tags.length > 5 && (
                            <span className="inline-block text-gray-500 px-2 py-1 text-xs">
                              +{item.tags.length - 5}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-xs text-gray-500 ml-4 flex-shrink-0">
                      {new Date(item.created_at).toLocaleDateString('zh-CN')}
                    </div>
                  </div>
                </div>
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
      ) : (
        <div className="text-center py-12 text-gray-600">
          <p>暂无内容</p>
        </div>
      )}
    </div>
  )
}
