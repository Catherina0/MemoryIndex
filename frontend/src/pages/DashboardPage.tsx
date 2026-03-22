import { useState, useEffect } from 'react'
import { getStats, listVideos, listArchives, type ContentListItem } from '@/api/client'
import { useStatsStore } from '@/store'
import StatCard from '@/components/StatCard'
import ContentPreview from '@/components/ContentPreview'

export default function DashboardPage() {
  const { stats, setStats, isLoading, setIsLoading } = useStatsStore()
  const [recentVideos, setRecentVideos] = useState<ContentListItem[]>([])
  const [recentArchives, setRecentArchives] = useState<ContentListItem[]>([])
  const [loadingContent, setLoadingContent] = useState(true)

  useEffect(() => {
    const loadStats = async () => {
      setIsLoading(true)
      try {
        const statsData = await getStats()
        setStats(statsData)
      } catch (err) {
        console.error('加载统计信息失败:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadStats()
  }, [])

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
      } catch (err) {
        console.error('加载最近内容失败:', err)
      } finally {
        setLoadingContent(false)
      }
    }

    loadRecentContent()
  }, [])

  return (
    <div className="space-y-8">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">知识库统计</h1>
        <p className="text-gray-600 mt-2">概览你的个人知识库</p>
      </div>

      {/* 统计卡片 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border border-primary border-t-transparent"></div>
        </div>
      ) : stats ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="总视频数"
              value={stats.total_videos}
              icon="📹"
              color="blue"
            />
            <StatCard
              title="网页归档"
              value={stats.total_archives}
              icon="📄"
              color="green"
            />
            <StatCard
              title="标签数量"
              value={stats.total_tags}
              icon="🏷️"
              color="purple"
            />
            <StatCard
              title="平均视频时长"
              value={
                stats.average_video_duration
                  ? `${Math.round(stats.average_video_duration / 60)} 分钟`
                  : 'N/A'
              }
              icon="⏱️"
              color="orange"
            />
          </div>

          {/* 热门标签 */}
          {stats.top_tags.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">🔥 热门标签</h2>
              <div className="flex flex-wrap gap-2">
                {stats.top_tags.slice(0, 12).map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-50 to-blue-100 text-blue-900 px-4 py-2 rounded-full text-sm font-medium hover:shadow-md transition-shadow cursor-pointer"
                  >
                    {tag.name}
                    <span className="bg-blue-200 rounded-full px-2 py-0.5 text-xs font-bold">
                      {tag.count}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      ) : null}

      {/* 最近添加的内容 */}
      {loadingContent ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border border-primary border-t-transparent"></div>
        </div>
      ) : (
        <>
          {recentVideos.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">📹 最近的视频</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recentVideos.map((video) => (
                  <ContentPreview key={`video-${video.id}`} content={video} />
                ))}
              </div>
            </div>
          )}

          {recentArchives.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">📄 最近的网页</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
