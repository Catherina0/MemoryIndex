import type { SearchResult } from '@/api/client'

interface ContentCardProps {
  result: SearchResult
}

export default function ContentCard({ result }: ContentCardProps) {
  const sourceIcon: Record<string, string> = {
    youtube: '🎥',
    bilibili: 'B',
    twitter: '𝕏',
    zhihu: '知',
    reddit: '🔴',
    xiaohongshu: '小',
    local: '💾',
  }

  const icon = sourceIcon[result.source_type] || '📄'

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-4 border border-gray-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{icon}</span>
            <span className="text-xs font-medium text-gray-500 px-2 py-1 bg-gray-100 rounded">
              {result.type === 'video' ? '📹 视频' : '📄 网页'}
            </span>
          </div>

          <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2 hover:text-primary transition-colors">
            {result.title}
          </h3>

          {result.summary && (
            <p className="text-gray-600 text-sm whitespace-pre-wrap break-words mb-3">{result.summary}</p>
          )}

          {result.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {result.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs"
                >
                  #{tag}
                </span>
              ))}
              {result.tags.length > 3 && (
                <span className="text-xs text-gray-500">+{result.tags.length - 3}</span>
              )}
            </div>
          )}

          <p className="text-xs text-gray-500">
            {new Date(result.created_at).toLocaleDateString('zh-CN')}
          </p>
        </div>
      </div>
    </div>
  )
}
