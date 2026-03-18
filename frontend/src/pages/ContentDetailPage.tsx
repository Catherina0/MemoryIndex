import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
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
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript' | 'ocr' | 'report'>('summary')

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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border border-primary border-t-transparent"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded-lg">
        {error}
      </div>
    )
  }

  if (!content) {
    return <div className="text-center py-12 text-gray-600">内容不存在</div>
  }

  const tabs = [
    { id: 'summary', label: '摘要', content: content.summary || '暂无摘要' },
    { id: 'transcript', label: contentType === 'archive' ? '网页内容' : '转写文本', content: content.transcript },
    { id: 'ocr', label: 'OCR 文本', content: content.ocr_text },
    { id: 'report', label: '详细报告', content: content.report },
  ].filter((tab) => tab.content) as Array<{ id: 'summary' | 'transcript' | 'ocr' | 'report'; label: string; content: string }>

  return (
    <div className="max-w-4xl mx-auto">
      {/* 标题和基本信息 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{content.title}</h1>
            <p className="text-gray-600 mt-2">
              来源：<span className="font-semibold">{content.source_type}</span>
            </p>
          </div>
          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            {contentType === 'video' ? '📹 视频' : '📄 网页'}
          </span>
        </div>

        {content.source_url ? (
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-1">🔗 原始链接：</p>
            <a
              href={content.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 text-sm break-all hover:underline"
            >
              {content.source_url}
            </a>
          </div>
        ) : contentType === 'archive' ? (
          <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 px-3 py-2 rounded mb-4 text-sm">
            ⚠️ 原始链接未保存
          </div>
        ) : null}

        {content.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {content.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        <p className="text-sm text-gray-500 mt-4">
          创建时间：{new Date(content.created_at).toLocaleString('zh-CN')}
        </p>

        {contentType === 'video' && content.duration_seconds && (
          <p className="text-sm text-gray-500 mt-1">
            时长：{Math.floor(content.duration_seconds / 60)} 分钟
          </p>
        )}

        {content.file_path && (
          <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
            <p className="text-sm font-medium text-gray-700 mb-1">📁 本地文件路径</p>
            <code className="text-xs text-gray-600 break-all select-all block bg-white p-2 rounded border border-gray-100">{content.file_path}</code>
          </div>
        )}
      </div>

      {/* 内容标签页 */}
      {tabs.length > 0 && (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {/* 标签页头 */}
          <div className="flex border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 px-4 py-3 text-sm font-medium text-center transition-colors ${
                  activeTab === tab.id
                    ? 'border-b-2 border-primary text-primary bg-blue-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* 标签页内容 */}
          <div className="p-6">
            <div className="prose prose-sm md:prose-base lg:prose-lg max-w-none prose-img:rounded-xl prose-a:text-blue-600 hover:prose-a:text-blue-800 whitespace-pre-wrap text-gray-700 leading-relaxed overflow-x-auto">
              <ReactMarkdown
                rehypePlugins={[rehypeRaw]}
                remarkPlugins={[remarkGfm]}
              >
                {tabs.find((t) => t.id === activeTab)?.content || ''}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
