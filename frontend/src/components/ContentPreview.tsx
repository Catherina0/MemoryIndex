import { Link } from 'react-router-dom'
import type { ContentListItem } from '@/api/client'

// #region ContentPreview - 内容预览卡片（首页/统计页用）
interface ContentPreviewProps {
  content: ContentListItem
}

export default function ContentPreview({ content }: ContentPreviewProps) {
  return (
    <Link
      to={`/content/${content.id}?type=${content.type}`}
      className="bg-white border border-gray-200 rounded-lg p-4 block hover:border-gray-300 hover:shadow-sm transition-all group"
    >
      {/* 类型标签 */}
      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
        content.type === 'video'
          ? 'bg-purple-50 text-purple-700'
          : 'bg-emerald-50 text-emerald-700'
      }`}>
        {content.type === 'video' ? '视频' : '网页'}
      </span>

      {/* 标题 */}
      <h3 className="text-sm font-medium text-gray-900 line-clamp-2 mt-2 mb-1 group-hover:text-blue-700 transition-colors">
        {content.title}
      </h3>

      {/* 摘要 */}
      {content.summary && (
        <p className="text-xs text-gray-500 line-clamp-2 mb-2">{content.summary}</p>
      )}

      {/* 底部信息 */}
      <div className="flex items-center gap-2 mt-auto">
        <span className="text-xs text-gray-400">
          {new Date(content.created_at).toLocaleDateString('zh-CN')}
        </span>
        {content.tags.length > 0 && (
          <>
            <span className="text-xs text-gray-300">|</span>
            {content.tags.slice(0, 2).map((tag) => (
              <span key={tag} className="text-xs text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded">
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
