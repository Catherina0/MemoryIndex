import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getStats, listVideos, listArchives, type ContentListItem } from '@/api/client'
import { useStatsStore } from '@/store'
import ContentPreview from '@/components/ContentPreview'

// #region DashboardPage
export default function DashboardPage() {
  const { stats, setStats, isLoading, setIsLoading } = useStatsStore()
  const [recentVideos, setRecentVideos] = useState<ContentListItem[]>([])
  const [recentArchives, setRecentArchives] = useState<ContentListItem[]>([])
  const [loadingContent, setLoadingContent] = useState(true)

  // #region 加载统计
  useEffect(() => {
    const loadStats = async () => {
      setIsLoading(true)
      try {
        const statsData = await getStats()
        setStats(statsData)
      } catch (_err) {
        // 静默处理
      } finally {
        setIsLoading(false)
      }
    }
    loadStats()
  }, [])
  // #endregion

  // #region 加载最近内容
  useEffect(() => {
    const loadRecentContent = async () => {
      setLoadingContent(true)
      try {
        const [videosRes, archivesRes] = await Promise.all([
          listVideos(6, 0, 'recent'),
          listArchives(6, 0, 'recent'),
        ])
        setRecentVideos(videosRes.items)
        setRecentArchives(archivesRes.items)
      } catch (_err) {
        // 静默处理
      } finally {
        setLoadingContent(false)
      }
    }
    loadRecentContent()
  }, [])
  // #endregion

  return (
    <div className="space-y-8">
      {/* 页头 */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">统计</h1>
        <p className="text-sm text-gray-500 mt-1">知识库概览</p>
      </div>

      {/* 统计卡片 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
        </div>
      ) : stats ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <DashboardStat label="视频" value={stats.total_videos} color="purple" />
            <DashboardStat label="网页归档" value={stats.total_archives} color="emerald" />
            <DashboardStat label="标签" value={stats.total_tags} color="blue" />
            <DashboardStat
              label="平均视频时长"
              value={stats.average_video_duration
                ? `${Math.round(stats.average_video_duration / 60)} 分钟`
                : '-'}
              color="amber"
            />
          </div>

          {/* 热门标签 */}
          {stats.top_tags.length > 0 && (
            <div>
              <h2 className="text-base font-semibold text-gray-900 mb-3">热门标签</h2>
              <div className="flex flex-wrap gap-2">
                {stats.top_tags.slice(0, 15).map((tag) => (
                  <Link
                    key={tag.id}
                    to={`/search?tags=${tag.name}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
                  >
                    {tag.name}
                    <span className="text-xs text-gray-400">{tag.count}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>
      ) : null}

      {/* 最近的内容 */}
      {loadingContent ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
        </div>
      ) : (
        <>
          {recentVideos.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-gray-900">最近的视频</h2>
                <Link to="/archives?tab=videos" className="text-sm text-blue-600 hover:text-blue-800">查看全部</Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {recentVideos.map((video) => (
                  <ContentPreview key={`video-${video.id}`} content={video} />
                ))}
              </div>
            </div>
          )}

          {recentArchives.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-gray-900">最近的网页</h2>
                <Link to="/archives?tab=archives" className="text-sm text-blue-600 hover:text-blue-800">查看全部</Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {recentArchives.map((archive) => (
                  <ContentPreview key={`archive-${archive.id}`} content={archive} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
// #endregion

// #region 统计卡片组件
const colorMap: Record<string, string> = {
  purple: 'border-l-purple-400',
  emerald: 'border-l-emerald-400',
  blue: 'border-l-blue-400',
  amber: 'border-l-amber-400',
}

function DashboardStat({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className={`bg-white border border-gray-200 border-l-4 ${colorMap[color] || 'border-l-gray-400'} rounded-lg px-4 py-3`}>
      <div className="text-xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  )
}
// #endregion
