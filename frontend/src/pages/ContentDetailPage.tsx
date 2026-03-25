// #region ContentDetailPage - 内容详情页

import { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'
import { getContentDetail, type ContentDetail } from '@/api/client'

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const contentType = (searchParams.get('type') || 'video') as 'video' | 'archive'

  const [content, setContent] = useState<ContentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [activeTab, setActiveTab] = useState<string>('summary')

  // #region 加载内容
  useEffect(() => {
    const loadContent = async () => {
      if (!id) return

      setLoading(true)
      setError('')

      try {
        const data = await getContentDetail(parseInt(id), contentType)
        setContent(data)
      } catch (err: any) {
        setError(err.response?.data?.detail || '加载内容失败')
      } finally {
        setLoading(false)
      }
    }

    loadContent()
  }, [id, contentType])
  // #endregion

  // #region Loading 状态
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <div className="animate-spin rounded-full h-7 w-7 border-2 border-primary-600 border-t-transparent" />
        <span className="text-sm text-slate-400">加载中...</span>
      </div>
    )
  }
  // #endregion

  // #region 错误状态
  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-2 bg-red-50 border border-red-200/60 text-red-700 px-4 py-3 rounded-xl text-sm">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      </div>
    )
  }
  // #endregion

  if (!content) {
    return (
      <div className="text-center py-20 text-slate-400">内容不存在</div>
    )
  }

  // #region 构建标签页
  const tabs = [
    { id: 'summary', label: '摘要', content: content.summary || '暂无摘要' },
  ]

  if (contentType === 'archive') {
    if (content.readme_text) {
      tabs.push({ id: 'readme', label: 'README', content: content.readme_text })
    }
    if (content.raw_archive) {
      tabs.push({ id: 'raw_archive', label: '网页原文', content: content.raw_archive })
    } else if (content.transcript) {
      tabs.push({ id: 'transcript', label: '网页原文', content: content.transcript })
    }
    if (content.ocr_text) {
      tabs.push({ id: 'ocr', label: 'OCR 内容', content: content.ocr_text })
    }
  } else {
    if (content.readme_text) {
      tabs.push({ id: 'readme', label: 'README', content: content.readme_text })
    }
    if (content.transcript) {
      tabs.push({ id: 'transcript', label: '转写文本', content: content.transcript })
    }
    if (content.ocr_text) {
      tabs.push({ id: 'ocr', label: 'OCR 文本', content: content.ocr_text })
    }
  }

  if (content.report) {
    tabs.push({ id: 'report', label: '详细报告', content: content.report })
  }
  // #endregion

  const currentTabContent = tabs.find((t) => t.id === activeTab)?.content || tabs[0]?.content || ''
  const isVideo = contentType === 'video'

  return (
    <div className="max-w-3xl mx-auto space-y-5 animate-fade-in">
      {/* #region 返回导航 */}
      <Link
        to="/archives"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 transition-colors group"
      >
        <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        返回资料库
      </Link>
      {/* #endregion */}

      {/* #region 视频播放器 */}
      {isVideo && content.file_path && (
        <div className="bg-slate-900 rounded-xl overflow-hidden shadow-lg">
          <video
            controls
            className="w-full max-h-[60vh] object-contain"
            src={`/api/content/${content.id}/media`}
          />
        </div>
      )}
      {/* #endregion */}

      {/* #region 标题和基本信息 */}
      <div className="card p-5 sm:p-6">
        {/* 类型和来源 */}
        <div className="flex items-center gap-2 mb-3">
          <span className={isVideo ? 'badge-video' : 'badge-archive'}>
            {isVideo ? '视频' : '网页'}
          </span>
          <span className="text-xs text-slate-400 uppercase tracking-wide">
            {content.source_type}
          </span>
          {isVideo && content.duration_seconds && (
            <>
              <span className="w-1 h-1 bg-slate-300 rounded-full" />
              <span className="text-xs text-slate-400">
                {Math.floor(content.duration_seconds / 60)} 分钟
              </span>
            </>
          )}
          <span className="w-1 h-1 bg-slate-300 rounded-full" />
          <span className="text-xs text-slate-400">
            {new Date(content.created_at).toLocaleString('zh-CN')}
          </span>
        </div>

        {/* 标题 */}
        <h1 className="text-xl font-bold text-slate-900 leading-tight mb-3">
          {content.title}
        </h1>

        {/* 原始链接 */}
        {content.source_url && (
          <a
            href={content.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 break-all transition-colors"
          >
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            {content.source_url}
          </a>
        )}

        {/* 标签 */}
        {content.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {content.tags.map((tag) => (
              <Link
                key={tag}
                to={`/search?tags=${tag}`}
                className="tag-pill"
              >
                {tag}
              </Link>
            ))}
          </div>
        )}

        {/* 本地文件路径 */}
        {content.file_path && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs text-slate-400 mb-1.5">本地路径</p>
            <code className="text-xs text-slate-600 break-all select-all block bg-slate-50 p-2.5 rounded-lg font-mono">
              {content.file_path}
            </code>
          </div>
        )}
      </div>
      {/* #endregion */}

      {/* #region 内容标签页 */}
      {tabs.length > 0 && (
        <div className="card overflow-hidden">
          {/* 标签页头 */}
          <div className="flex border-b border-slate-200/80 overflow-x-auto bg-slate-50/50">
            {tabs.map((tab) => (
              <button
                type="button"
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-all relative ${
                  activeTab === tab.id
                    ? 'text-primary-700 bg-white'
                    : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 rounded-t" />
                )}
              </button>
            ))}
          </div>

          {/* 标签页内容 */}
          <div className="p-5 sm:p-6">
            <div className={`prose-custom max-w-none leading-relaxed overflow-x-auto ${
              activeTab === 'report' || activeTab === 'content' ? '' : 'whitespace-pre-wrap'
            }`}>
              <ReactMarkdown
                rehypePlugins={[rehypeRaw]}
                remarkPlugins={[remarkGfm]}
              >
                {currentTabContent}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
      {/* #endregion */}
    </div>
  )
}

// #endregion
