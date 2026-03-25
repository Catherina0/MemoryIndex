// #region TagFilter - 标签过滤器

import { useSearchStore } from '@/store'
import type { Tag } from '@/api/client'

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

  if (tags.length === 0) return null

  return (
    <div className="card p-4 h-fit sticky top-20">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">标签筛选</h3>

      <div className="space-y-0.5">
        {tags.slice(0, 15).map((tag) => {
          const isSelected = selectedTags.includes(tag.name)
          return (
            <label
              key={tag.id}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-colors ${
                isSelected ? 'bg-primary-50' : 'hover:bg-slate-50'
              }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleTag(tag.name)}
                className="w-3.5 h-3.5 text-primary-600 rounded border-slate-300 focus:ring-primary-500 focus:ring-offset-0"
              />
              <span className={`flex-1 text-sm ${isSelected ? 'text-primary-700 font-medium' : 'text-slate-600'}`}>
                {tag.name}
              </span>
              <span className={`text-xs tabular-nums ${isSelected ? 'text-primary-400' : 'text-slate-400'}`}>
                {tag.count}
              </span>
            </label>
          )
        })}
      </div>

      {selectedTags.length > 0 && (
        <button
          type="button"
          onClick={() => setSelectedTags([])}
          className="w-full mt-3 pt-3 border-t border-slate-100 text-xs text-primary-600 hover:text-primary-700 font-medium transition-colors"
        >
          清除全部筛选
        </button>
      )}
    </div>
  )
}

// #endregion
