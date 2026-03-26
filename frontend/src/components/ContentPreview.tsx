// #region ContentPreview - 内容预览卡片

import { Link } from 'react-router-dom'
import type { ContentListItem } from '@/api/client'

interface ContentPreviewProps {
  content: ContentListItem
}

export default function ContentPreview({ content }: ContentPreviewProps) {
  const isVideo = content.type === 'video'

  return (
    <Link
      to={`/content/${content.id}?type=${content.type}`}
      className="card-interactive p-4 flex flex-col gap-2.5 group animate-fade-in"
    >
      {/* 顶部：类型标签 + 日期 */}
      <div className="flex items-center justify-between">
        <span className={isVideo ? 'badge-video' : 'badge-archive'}>
          {isVideo ? '视频' : '网页'}
        </span>
        <span className="text-xs text-slate-400 tabular-nums">
          {new Date(content.created_at).toLocaleDateString('zh-CN')}
        </span>
      </div>

      {/* 标题 */}
      <h3 className="text-sm font-semibold text-slate-800 line-clamp-2 group-hover:text-primary-600 transition-colors leading-snug">
        {content.title}
      </h3>

      {/* 摘要 */}
      {content.summary && content.summary !== '暂无摘要' && (
        <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
          {content.summary}
        </p>
      )}

      {/* 底部：来源 + 标签 */}
      <div className="flex items-center gap-2 mt-auto pt-1">
        <span className="text-[11px] text-slate-400 uppercase tracking-wide">
          {content.source_type}
        </span>
        {content.duration && (
          <span className="text-[11px] text-slate-400">
            {Math.floor(content.duration / 60)}:{String(content.duration % 60).padStart(2, '0')}
          </span>
        )}
        {content.tags.length > 0 && (
          <>
            <span className="text-slate-200">|</span>
            {content.tags.slice(0, 2).map((tag) => (
              <span key={tag} className="text-[11px] text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded">
                {tag}
              </span>
            ))}
          </>
        )}
      </div>
    </Link>
  )
}

// #endregion
