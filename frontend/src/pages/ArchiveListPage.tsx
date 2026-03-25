import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listVideos, listArchives, listTags, type Tag, type ContentListItem } from '@/api/client'
import Pagination from '@/components/Pagination'

// #region ArchiveListPage
export default function ArchiveListPage() {
  const [activeTab, setActiveTab] = useState<'all' | 'videos' | 'archives'>('all')
  const [sortBy, setSortBy] = useState<'recent' | 'oldest'>('recent')
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  const [items, setItems] = useState<ContentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [tags, setTags] = useState<Tag[]>([])

  const itemsPerPage = 20

  // #region 加载标签
  useEffect(() => {
    const loadTags = async () => {
      try {
        const tagsData = await listTags()
        setTags(tagsData)
      } catch (_err) {
        // 静默处理
      }
    }
    loadTags()
  }, [])
  // #endregion

  // #region 加载数据
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      try {
        const offset = (currentPage - 1) * itemsPerPage

        let allItems: ContentListItem[] = []
        let totalCount = 0

        if (activeTab === 'videos') {
          const res = await listVideos(itemsPerPage, offset, sortBy as any)
          allItems = res.items
          totalCount = res.total
        } else if (activeTab === 'archives') {
          const res = await listArchives(itemsPerPage, offset, sortBy)
          allItems = res.items
          totalCount = res.total
        } else {
          // "全部"标签：分别拉取各自的半页数据，合并后按时间排序
          const halfPage = Math.ceil(itemsPerPage / 2)
          const halfOffset = Math.floor(offset / 2)

          const [videosRes, archivesRes] = await Promise.all([
            listVideos(halfPage, halfOffset, sortBy as any),
            listArchives(halfPage, halfOffset, sortBy),
          ])

          allItems = [...videosRes.items, ...archivesRes.items]
          // 按创建时间排序
          allItems.sort((a, b) => {
            const ta = new Date(a.created_at).getTime()
            const tb = new Date(b.created_at).getTime()
            return sortBy === 'oldest' ? ta - tb : tb - ta
          })
          allItems = allItems.slice(0, itemsPerPage)
          totalCount = videosRes.total + archivesRes.total
        }

        // 标签过滤（客户端）
        if (selectedTags.length > 0) {
          allItems = allItems.filter(item =>
            selectedTags.some(tag => item.tags.includes(tag))
          )
        }

        setItems(allItems)
        setTotal(selectedTags.length > 0 ? allItems.length : totalCount)
      } catch (_err) {
        // 静默处理
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [activeTab, sortBy, currentPage, selectedTags])
  // #endregion

  // #region 标签切换
  const handleTagToggle = (tagName: string) => {
    setSelectedTags(prev =>
      prev.includes(tagName)
        ? prev.filter(t => t !== tagName)
        : [...prev, tagName]
    )
    setCurrentPage(1)
  }
  // #endregion

  const totalPages = Math.ceil(total / itemsPerPage)

  const tabs: { key: typeof activeTab; label: string }[] = [
    { key: 'all', label: '全部' },
    { key: 'videos', label: '视频' },
    { key: 'archives', label: '网页' },
  ]

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">存档库</h1>
        <p className="text-sm text-gray-500 mt-1">共 {total} 条内容</p>
      </div>

      {/* 控制条：标签页 + 排序 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1">
          {tabs.map(({ key, label }) => (
            <button
              type="button"
              key={key}
              onClick={() => { setActiveTab(key); setCurrentPage(1) }}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === key
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <select
          aria-label="排序方式"
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value as 'recent' | 'oldest')
            setCurrentPage(1)
          }}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="recent">最近添加</option>
          <option value="oldest">最早添加</option>
        </select>
      </div>

      {/* 标签过滤 */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.slice(0, 20).map(tag => (
            <button
              type="button"
              key={tag.id}
              onClick={() => handleTagToggle(tag.name)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                selectedTags.includes(tag.name)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {tag.name}
              <span className={`ml-1 ${selectedTags.includes(tag.name) ? 'text-blue-200' : 'text-gray-400'}`}>
                {tag.count}
              </span>
            </button>
          ))}
          {selectedTags.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTags([])}
              className="px-2.5 py-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              清除筛选
            </button>
          )}
        </div>
      )}

      {/* 内容列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="space-y-2">
            {items.map((item) => (
              <Link
                key={`${item.type}-${item.id}`}
                to={`/content/${item.id}?type=${item.type}`}
                className="block"
              >
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-gray-300 hover:shadow-sm transition-all">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* 元信息行 */}
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                          item.type === 'video'
                            ? 'bg-purple-50 text-purple-700'
                            : 'bg-emerald-50 text-emerald-700'
                        }`}>
                          {item.type === 'video' ? '视频' : '网页'}
                        </span>
                        <span className="text-xs text-gray-400">{item.source_type}</span>
                        {item.duration && (
                          <span className="text-xs text-gray-400">
                            {Math.floor(item.duration / 60)}分{item.duration % 60}秒
                          </span>
                        )}
                      </div>

                      {/* 标题 */}
                      <h3 className="text-sm font-medium text-gray-900 line-clamp-1 mb-1">
                        {item.title}
                      </h3>

                      {/* 摘要 */}
                      {item.summary && (
                        <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                          {item.summary}
                        </p>
                      )}

                      {/* 标签 */}
                      {item.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {item.tags.slice(0, 4).map(tag => (
                            <span key={tag} className="text-xs text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
                              {tag}
                            </span>
                          ))}
                          {item.tags.length > 4 && (
                            <span className="text-xs text-gray-400">+{item.tags.length - 4}</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* 日期 */}
                    <div className="text-xs text-gray-400 flex-shrink-0 tabular-nums">
                      {new Date(item.created_at).toLocaleDateString('zh-CN')}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-6">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-16 text-gray-400 text-sm">
          暂无内容
        </div>
      )}
    </div>
  )
}
// #endregion
