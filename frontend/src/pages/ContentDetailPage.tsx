import { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'
import { getContentDetail, type ContentDetail } from '@/api/client'

// #region ContentDetailPage
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="text-center py-16 text-gray-400">
        内容不存在
      </div>
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

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* 返回链接 */}
      <Link to="/archives" className="text-sm text-gray-500 hover:text-gray-700 transition-colors">
        &larr; 返回存档库
      </Link>

      {/* 视频播放器 */}
      {contentType === 'video' && content.file_path && (
        <div className="bg-black rounded-lg overflow-hidden">
          <video
            controls
            className="w-full max-h-[60vh] object-contain"
            src={`/api/content/${content.id}/media`}
          />
        </div>
      )}

      {/* 标题和基本信息 */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h1 className="text-xl font-bold text-gray-900 leading-tight">{content.title}</h1>
          <span className={`text-xs font-medium px-2 py-1 rounded flex-shrink-0 ${
            contentType === 'video'
              ? 'bg-purple-50 text-purple-700'
              : 'bg-emerald-50 text-emerald-700'
          }`}>
            {contentType === 'video' ? '视频' : '网页'}
          </span>
        </div>

        {/* 来源信息 */}
        <div className="flex items-center gap-3 text-sm text-gray-500 mb-3">
          <span>{content.source_type}</span>
          {contentType === 'video' && content.duration_seconds && (
            <span>{Math.floor(content.duration_seconds / 60)} 分钟</span>
          )}
          <span>{new Date(content.created_at).toLocaleString('zh-CN')}</span>
        </div>

        {/* 原始链接 */}
        {content.source_url && (
          <a
            href={content.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 break-all hover:underline"
          >
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
                className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded hover:bg-gray-200 transition-colors"
              >
                {tag}
              </Link>
            ))}
          </div>
        )}

        {/* 本地文件路径 */}
        {content.file_path && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-400 mb-1">本地文件</p>
            <code className="text-xs text-gray-600 break-all select-all block bg-gray-50 p-2 rounded">
              {content.file_path}
            </code>
          </div>
        )}
      </div>

      {/* 内容标签页 */}
      {tabs.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {/* 标签页头 */}
          <div className="flex border-b border-gray-200 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                type="button"
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'border-b-2 border-blue-600 text-blue-700 bg-blue-50/50'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 标签页内容 */}
          <div className="p-5">
            <div className={`prose prose-sm max-w-none prose-a:text-blue-600 hover:prose-a:text-blue-800 prose-table:border prose-th:bg-gray-50 prose-th:p-2 prose-th:border prose-td:p-2 prose-td:border text-gray-700 leading-relaxed overflow-x-auto ${
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
    </div>
  )
}
// #endregion
