// #region ArchiveListPage - 资料库

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listVideos, listArchives, listTags, type Tag, type ContentListItem } from '@/api/client'
import ContentPreview from '@/components/ContentPreview'
import Pagination from '@/components/Pagination'

export default function ArchiveListPage() {
  const [activeTab, setActiveTab] = useState<'all' | 'videos' | 'archives'>('all')
  const [sortBy, setSortBy] = useState<'recent' | 'oldest'>('recent')
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  const [items, setItems] = useState<ContentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [tags, setTags] = useState<Tag[]>([])

  const itemsPerPage = 18

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
          const halfPage = Math.ceil(itemsPerPage / 2)
          const halfOffset = Math.floor(offset / 2)

          const [videosRes, archivesRes] = await Promise.all([
            listVideos(halfPage, halfOffset, sortBy as any),
            listArchives(halfPage, halfOffset, sortBy),
          ])

          allItems = [...videosRes.items, ...archivesRes.items]
          allItems.sort((a, b) => {
            const ta = new Date(a.created_at).getTime()
            const tb = new Date(b.created_at).getTime()
            return sortBy === 'oldest' ? ta - tb : tb - ta
          })
          allItems = allItems.slice(0, itemsPerPage)
          totalCount = videosRes.total + archivesRes.total
        }

        // 客户端标签过滤
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

  const tabs: { key: typeof activeTab; label: string; icon: string }[] = [
    { key: 'all', label: '全部', icon: '' },
    { key: 'videos', label: '视频', icon: '' },
    { key: 'archives', label: '网页', icon: '' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* #region 页头 */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">资料库</h1>
          <p className="text-sm text-slate-500 mt-1">
            共 <span className="font-semibold text-slate-700">{total}</span> 条内容
          </p>
        </div>
        <Link to="/" className="btn-primary text-xs px-3 py-1.5">
          <svg className="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          导入
        </Link>
      </div>
      {/* #endregion */}

      {/* #region 控制栏 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* 标签页切换 */}
        <div className="flex bg-slate-100 rounded-lg p-0.5">
          {tabs.map(({ key, label }) => (
            <button
              type="button"
              key={key}
              onClick={() => { setActiveTab(key); setCurrentPage(1) }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                activeTab === key
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 排序 */}
        <select
          aria-label="排序方式"
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value as 'recent' | 'oldest')
            setCurrentPage(1)
          }}
          className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm bg-white text-slate-600 focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 transition-all"
        >
          <option value="recent">最新优先</option>
          <option value="oldest">最早优先</option>
        </select>
      </div>
      {/* #endregion */}

      {/* #region 标签过滤 */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.slice(0, 20).map(tag => {
            const isSelected = selectedTags.includes(tag.name)
            return (
              <button
                type="button"
                key={tag.id}
                onClick={() => handleTagToggle(tag.name)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  isSelected
                    ? 'tag-pill-active'
                    : 'tag-pill'
                }`}
              >
                {tag.name}
                <span className={`ml-1 ${isSelected ? 'text-primary-400' : 'text-slate-400'}`}>
                  {tag.count}
                </span>
              </button>
            )
          })}
          {selectedTags.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTags([])}
              className="px-2.5 py-1 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
            >
              清除筛选
            </button>
          )}
        </div>
      )}
      {/* #endregion */}

      {/* #region 内容网格 */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="animate-spin rounded-full h-7 w-7 border-2 border-primary-600 border-t-transparent" />
          <span className="text-sm text-slate-400">加载中...</span>
        </div>
      ) : items.length > 0 ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {items.map((item) => (
              <ContentPreview key={`${item.type}-${item.id}`} content={item} />
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
        <div className="text-center py-20">
          <div className="text-slate-200 mb-3">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <p className="text-slate-400">暂无内容</p>
          <Link to="/" className="text-sm text-primary-600 hover:text-primary-700 mt-2 inline-block font-medium">
            去导入第一条内容 &rarr;
          </Link>
        </div>
      )}
      {/* #endregion */}
    </div>
  )
}

// #endregion
