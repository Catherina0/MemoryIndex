import { useSearchStore } from '@/store'
import type { Tag } from '@/api/client'

// #region TagFilter - 搜索页标签过滤侧边栏
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
    <div className="bg-white border border-gray-200 rounded-lg p-4 h-fit sticky top-20">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">按标签过滤</h3>

      {tags.length === 0 ? (
        <p className="text-xs text-gray-400">暂无标签</p>
      ) : (
        <div className="space-y-1">
          {tags.slice(0, 15).map((tag) => (
            <label
              key={tag.id}
              className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedTags.includes(tag.name)}
                onChange={() => toggleTag(tag.name)}
                className="w-3.5 h-3.5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <span className="flex-1 text-sm text-gray-700">{tag.name}</span>
              <span className="text-xs text-gray-400">{tag.count}</span>
            </label>
          ))}
        </div>
      )}

      {selectedTags.length > 0 && (
        <button
          type="button"
          onClick={() => setSelectedTags([])}
          className="w-full mt-3 text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          清除筛选
        </button>
      )}
    </div>
  )
}
// #endregion
