import React from 'react'
import { useSearchStore } from '@/store'
import type { Tag } from '@/api/client'
import clsx from 'clsx'

interface TagFilterProps {
  tags: Tag[]
}

export default function TagFilter({ tags }: TagFilterProps) {
  const { selectedTags, setSelectedTags } = useSearchStore()

  const toggleTag = (tagName: string) => {
    setSelectedTags(
      selectedTags.includes(tagName)
        ? selectedTags.filter((t) => t !== tagName)
        : [...selectedTags, tagName]
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4 h-fit sticky top-20">
      <h3 className="font-bold text-gray-900 mb-4">🏷️ 按标签过滤</h3>

      {tags.length === 0 ? (
        <p className="text-sm text-gray-500">暂无标签</p>
      ) : (
        <div className="space-y-2">
          {tags.slice(0, 15).map((tag) => (
            <label
              key={tag.id}
              className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedTags.includes(tag.name)}
                onChange={() => toggleTag(tag.name)}
                className="w-4 h-4 text-primary rounded focus:ring-primary"
              />
              <span className="flex-1 text-sm text-gray-700">{tag.name}</span>
              <span className="text-xs text-gray-500">({tag.count})</span>
            </label>
          ))}
        </div>
      )}

      {selectedTags.length > 0 && (
        <button
          onClick={() => setSelectedTags([])}
          className="w-full mt-4 text-sm text-primary hover:text-blue-700 font-medium"
        >
          清除筛选
        </button>
      )}
    </div>
  )
}
