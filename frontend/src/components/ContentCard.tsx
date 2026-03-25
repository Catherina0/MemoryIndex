// #region ContentCard - 搜索结果卡片

import type { SearchResult } from '@/api/client'

interface ContentCardProps {
  result: SearchResult
}

export default function ContentCard({ result }: ContentCardProps) {
  const isVideo = result.type === 'video'

  return (
    <div className="card-interactive px-4 py-3.5 animate-fade-in">
      <div className="flex items-start gap-3">
        {/* 类型指示条 */}
        <div className={`w-1 self-stretch rounded-full flex-shrink-0 ${
          isVideo ? 'bg-violet-400' : 'bg-teal-400'
        }`} />

        <div className="flex-1 min-w-0">
          {/* 元信息行 */}
          <div className="flex items-center gap-2 mb-1">
            <span className={isVideo ? 'badge-video' : 'badge-archive'}>
              {isVideo ? '视频' : '网页'}
            </span>
            <span className="text-[11px] text-slate-400 uppercase tracking-wide">
              {result.source_type}
            </span>
            <span className="text-xs text-slate-400 ml-auto tabular-nums">
              {new Date(result.created_at).toLocaleDateString('zh-CN')}
            </span>
          </div>

          {/* 标题 */}
          <h3 className="text-sm font-semibold text-slate-800 line-clamp-2 mb-1 group-hover:text-primary-600 transition-colors">
            {result.title}
          </h3>

          {/* 摘要 */}
          {result.summary && (
            <p className="text-xs text-slate-500 line-clamp-2 mb-2 leading-relaxed">
              {result.summary}
            </p>
          )}

          {/* 标签 */}
          {result.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.tags.slice(0, 4).map((tag) => (
                <span key={tag} className="text-[11px] text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded">
                  {tag}
                </span>
              ))}
              {result.tags.length > 4 && (
                <span className="text-[11px] text-slate-400">+{result.tags.length - 4}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// #endregion
