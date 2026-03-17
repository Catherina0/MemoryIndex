import React from 'react'
import { Link } from 'react-router-dom'
import type { ContentListItem } from '@/api/client'

interface ContentPreviewProps {
  content: ContentListItem
}

export default function ContentPreview({ content }: ContentPreviewProps) {
  return (
    <Link
      to={`/content/${content.id}?type=${content.type}`}
      className="bg-white rounded-lg shadow-md hover:shadow-lg transition-all hover:scale-105 p-4 block group"
    >
      <div className="text-4xl mb-3 group-hover:scale-110 transition-transform">
        {content.type === 'video' ? '📹' : '📄'}
      </div>
      <h3 className="font-bold text-gray-900 line-clamp-2 group-hover:text-primary transition-colors mb-2">
        {content.title}
      </h3>
      {content.summary && (
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{content.summary}</p>
      )}
      <div className="text-xs text-gray-500">
        {new Date(content.created_at).toLocaleDateString('zh-CN')}
      </div>
      {content.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {content.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
              #{tag}
            </span>
          ))}
        </div>
      )}
    </Link>
  )
}
