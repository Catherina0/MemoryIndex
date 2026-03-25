import type { SearchResult } from '@/api/client'

// #region ContentCard - 搜索结果卡片
interface ContentCardProps {
  result: SearchResult
}

export default function ContentCard({ result }: ContentCardProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-gray-300 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* 元信息 */}
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
              result.type === 'video'
                ? 'bg-purple-50 text-purple-700'
                : 'bg-emerald-50 text-emerald-700'
            }`}>
              {result.type === 'video' ? '视频' : '网页'}
            </span>
            <span className="text-xs text-gray-400">{result.source_type}</span>
          </div>

          {/* 标题 */}
          <h3 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1 hover:text-blue-700 transition-colors">
            {result.title}
          </h3>

          {/* 摘要 */}
          {result.summary && (
            <p className="text-xs text-gray-500 line-clamp-2 mb-2">{result.summary}</p>
          )}

          {/* 标签 + 日期 */}
          <div className="flex items-center gap-2 flex-wrap">
            {result.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="text-xs text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
                {tag}
              </span>
            ))}
            {result.tags.length > 3 && (
              <span className="text-xs text-gray-400">+{result.tags.length - 3}</span>
            )}
            <span className="text-xs text-gray-400 ml-auto">
              {new Date(result.created_at).toLocaleDateString('zh-CN')}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
// #endregion
