import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getStats, listVideos, listArchives } from '@/api/client'
import ContentPreview from '@/components/ContentPreview'
import SearchBar from '@/components/SearchBar'

export default function HomePage() {
  const [stats, setStats] = useState(null)
  const [recentVideos, setRecentVideos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, videosRes] = await Promise.all([
          getStats(),
          listVideos(3, 0, 'recent'),
        ])
        setStats(statsData)
        setRecentVideos(videosRes.items)
      } catch (err) {
        console.error('加载数据失败:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          📚 MemoryIndex
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          基于 AI 代理的个人知识管理系统
        </p>
        <div className="max-w-2xl mx-auto">
          <SearchBar onSearch={() => {}} placeholder="在这里开始搜索..." />
        </div>
      </section>

      {/* 统计概览 */}
      {!loading && stats && (
        <section className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">📊 知识库概况</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{stats.total_videos}</div>
              <p className="text-gray-700 mt-2">📹 视频</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{stats.total_archives}</div>
              <p className="text-gray-700 mt-2">📄 网页</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{stats.total_tags}</div>
              <p className="text-gray-700 mt-2">🏷️ 标签</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600">
                {stats.average_video_duration
                  ? Math.round(stats.average_video_duration / 60)
                  : 0}
              </div>
              <p className="text-gray-700 mt-2">⏱️ 平均分钟</p>
            </div>
          </div>

          {stats.top_tags.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-sm font-medium text-gray-600 mb-3">🔥 热门标签：</p>
              <div className="flex flex-wrap gap-2">
                {stats.top_tags.slice(0, 8).map((tag) => (
                  <Link
                    key={tag.id}
                    to={`/search?tags=${tag.name}`}
                    className="inline-block bg-white text-gray-800 px-3 py-1 rounded-full text-sm hover:bg-gray-100 transition-colors"
                  >
                    #{tag.name} ({tag.count})
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* 最近添加 */}
      {!loading && recentVideos.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">📹 最近添加的视频</h2>
            <Link to="/search" className="text-blue-600 hover:text-blue-800 font-medium">
              查看全部 →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recentVideos.map((video) => (
              <ContentPreview key={`video-${video.id}`} content={video} />
            ))}
          </div>
        </section>
      )}

      {/* 功能介绍 */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 py-8">
        <div className="bg-white p-8 rounded-lg shadow-md hover:shadow-lg transition-shadow">
          <div className="text-4xl mb-4">🎬</div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">智能视频处理</h3>
          <p className="text-gray-600">
            自动提取、转写和总结视频内容，支持本地文件、YouTube、Bilibili
          </p>
        </div>
        <div className="bg-white p-8 rounded-lg shadow-md hover:shadow-lg transition-shadow">
          <div className="text-4xl mb-4">🕸️</div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">网页归档</h3>
          <p className="text-gray-600">
            智能提取网页内容，支持知乎、Reddit、Twitter、XHS 等多平台
          </p>
        </div>
        <div className="bg-white p-8 rounded-lg shadow-md hover:shadow-lg transition-shadow">
          <div className="text-4xl mb-4">🔍</div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">全文搜索</h3>
          <p className="text-gray-600">
            毫秒级全文搜索，支持中文分词、标签过滤和高级筛选
          </p>
        </div>
      </section>

      {/* 快速开始 */}
      <section className="bg-white rounded-lg shadow-md p-8 border-l-4 border-blue-500">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">🚀 快速开始</h2>
        <ol className="space-y-3 text-gray-700">
          <li>
            <span className="font-bold text-blue-600">1. 搜索</span> - 点击顶部搜索框找到你感兴趣的内容
          </li>
          <li>
            <span className="font-bold text-blue-600">2. 浏览</span> - 查看视频转写、OCR 和 AI 总结
          </li>
          <li>
            <span className="font-bold text-blue-600">3. 管理</span> - 使用标签和主题组织你的知识库
          </li>
          <li>
            <span className="font-bold text-blue-600">4. 导入</span> - 通过 CLI 命令导入新的视频和网页
          </li>
        </ol>
      </section>
    </div>
  )
}
