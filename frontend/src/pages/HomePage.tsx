import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getStats, listVideos, listArchives, type ContentListItem } from '@/api/client'
import ContentPreview from '@/components/ContentPreview'
import SearchBar from '@/components/SearchBar'

const logger = {
  error: (msg: string, err: any) => console.error(msg, err),
}

interface TaskStatus {
  task_id: string
  status: string
  progress: number
  current_step: string
  error_message?: string
}

export default function HomePage() {
  const [stats, setStats] = useState<any>(null)
  const [recentVideos, setRecentVideos] = useState<ContentListItem[]>([])
  const [recentArchives, setRecentArchives] = useState<ContentListItem[]>([])
  const [loading, setLoading] = useState(true)
  
  // 链接导入表单状态
  const [importUrl, setImportUrl] = useState('')
  const [contentType, setContentType] = useState('auto')
  const [useOcr, setUseOcr] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [importError, setImportError] = useState('')
  const [importSuccess, setImportSuccess] = useState('')
  
  // 任务追踪状态
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, videosRes, archivesRes] = await Promise.all([
          getStats(),
          listVideos(3, 0, 'recent'),
          listArchives(3, 0, 'recent'),
        ])
        setStats(statsData)
        setRecentVideos(videosRes.items)
        setRecentArchives(archivesRes.items)
      } catch (err) {
        console.error('加载数据失败:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])
  
  // 轮询任务状态
  useEffect(() => {
    if (!taskId) {
      return
    }
    
    const pollTaskStatus = async () => {
      try {
        const response = await fetch(`/api/tasks/${taskId}`)
        if (!response.ok) {
          console.error(`获取任务状态失败: ${response.status}`)
          return
        }
        
        const data = await response.json()
        console.log(`📊 [前端] 任务状态: ${data.status}, 进度: ${data.progress}%`)
        setTaskStatus(data)
        
        // 任务完成或出错时停止轮询
        if (data.status === 'completed' || data.status === 'error') {
          if (pollingInterval) {
            clearInterval(pollingInterval)
            setPollingInterval(null)
          }
          
          if (data.status === 'completed') {
            setImportSuccess(`✅ 任务完成！(进度: 100%)`)
            // 5 秒后清除成功消息
            setTimeout(() => {
              setImportSuccess('')
              setTaskId(null)
              setTaskStatus(null)
            }, 5000)
          } else {
            setImportError(`❌ 任务失败: ${data.error_message || '未知错误'}`)
          }
          setIsImporting(false)
        }
      } catch (err) {
        console.error('轮询任务状态错误:', err)
      }
    }
    
    // 立即检查一次
    pollTaskStatus()
    
    // 然后每 1 秒轮询一次
    const interval = setInterval(pollTaskStatus, 1000)
    setPollingInterval(interval)
    
    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [taskId, pollingInterval])
  
  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!importUrl.trim()) {
      setImportError('请输入链接')
      return
    }
    
    setIsImporting(true)
    setImportError('')
    setImportSuccess('')
    setTaskId(null)
    setTaskStatus(null)
    
    try {
      // 决定调用哪个 API 端点及其函数名
      let endpoint = ''
      let actionName = ''
      
      // 自动检测内容类型
      const detection_url = importUrl.trim().toLowerCase()
      let detected_type = contentType
      
      if (contentType === 'auto') {
        const video_domains = [
          'youtube.com', 'youtu.be',
          'bilibili.com', 'b23.tv',
          'vimeo.com', 'dailymotion.com',
          'qq.com', 'iqiyi.com'
        ]
        detected_type = video_domains.some(d => detection_url.includes(d)) ? 'video' : 'archive'
      }
      
      // 根据内容类型和 OCR 选择端点
      if (detected_type === 'video') {
        endpoint = useOcr ? '/api/download-ocr' : '/api/download-run'
        actionName = useOcr ? '🎬 下载视频（完整处理）' : '🎬 下载视频（快速处理）'
      } else {
        endpoint = useOcr ? '/api/archive-ocr' : '/api/archive-run'
        actionName = useOcr ? '🕸️ 归档网页（OCR识别）' : '🕸️ 归档网页（快速处理）'
      }
      
      console.log(`📡 [前端] ${actionName}`)
      console.log(`📍 调用端点: ${endpoint}`)
      console.log(`🔗 链接: ${importUrl.trim()}`)
      console.log(`⚙️ 参数: OCR=${useOcr}`)
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: importUrl.trim(),
        }),
      })
      
      if (!response.ok) {
        throw new Error(`API 返回错误: ${response.status}`)
      }
      
      const data = await response.json()
      console.log(`✅ [前端] API 响应:`, data)
      
      if (data.status === 'error') {
        console.error(`❌ [前端] 错误: ${data.message}`)
        setImportError(data.message)
        setIsImporting(false)
      } else {
        // 成功收到 task_id，开始任务追踪
        if (data.task_id) {
          console.log(`✅ [前端] 任务已创建: ${data.task_id}`)
          setImportSuccess(`✅ ${data.message}`)
          setTaskId(data.task_id)
          setImportUrl('')
          setContentType('auto')
          setUseOcr(false)
          // 不立即清除成功消息，等待任务完成
        } else {
          console.warn(`⚠️ [前端] 响应中没有 task_id`)
          setImportSuccess(data.message)
          setIsImporting(false)
          setTimeout(() => setImportSuccess(''), 3000)
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '导入失败，请稍后重试'
      console.error(`❌ [前端] 异常错误:`, err)
      setImportError(errorMsg)
      setIsImporting(false)
      logger.error('导入错误:', err)
    }
  }

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
      
      {/* 快速导入区域 */}
      <section className="max-w-2xl mx-auto w-full bg-blue-50 rounded-lg p-8 border border-blue-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">🔗 快速导入</h2>
        <form onSubmit={handleImport} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              链接地址
            </label>
            <input
              type="url"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              placeholder="粘贴视频或网页链接 (YouTube, Bilibili, Twitter, etc.)"
              disabled={isImporting}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                内容类型
              </label>
              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                disabled={isImporting}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
              >
                <option value="auto">自动检测</option>
                <option value="video">视频</option>
                <option value="archive">网页</option>
              </select>
            </div>
            
            <div className="flex items-end">
              <label className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer h-full">
                <input
                  type="checkbox"
                  checked={useOcr}
                  onChange={(e) => setUseOcr(e.target.checked)}
                  disabled={isImporting}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span>启用 OCR 识别</span>
              </label>
            </div>
            
            <div className="flex items-end">
              <button
                type="submit"
                disabled={isImporting || !importUrl.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isImporting ? '处理中...' : '导入'}
              </button>
            </div>
          </div>
          
          {importError && (
            <div className="p-3 bg-red-100 border border-red-300 text-red-700 rounded-lg text-sm">
              {importError}
            </div>
          )}
          
          {importSuccess && (
            <div className="space-y-3">
              <div className="p-3 bg-green-100 border border-green-300 text-green-700 rounded-lg text-sm">
                ✓ {importSuccess}
              </div>
              
              {/* 任务进度显示 */}
              {taskStatus && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">
                      {taskStatus.current_step}
                    </span>
                    <span className="text-sm text-gray-600">
                      {taskStatus.progress}%
                    </span>
                  </div>
                  
                  {/* 进度条 */}
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        taskStatus.status === 'error' 
                          ? 'bg-red-500' 
                          : taskStatus.status === 'completed'
                          ? 'bg-green-500'
                          : 'bg-blue-500'
                      }`}
                      style={{ width: `${taskStatus.progress}%` }}
                    ></div>
                  </div>
                  
                  {/* 状态标签 */}
                  <div className="flex items-center space-x-2 text-sm">
                    {taskStatus.status === 'processing' && (
                      <>
                        <span className="animate-spin">⏳</span>
                        <span className="text-gray-600">处理中...</span>
                      </>
                    )}
                    {taskStatus.status === 'pending' && (
                      <>
                        <span>⏳</span>
                        <span className="text-gray-600">等待处理...</span>
                      </>
                    )}
                    {taskStatus.status === 'completed' && (
                      <>
                        <span>✅</span>
                        <span className="text-green-600 font-medium">已完成</span>
                      </>
                    )}
                    {taskStatus.status === 'error' && (
                      <>
                        <span>❌</span>
                        <span className="text-red-600 font-medium">处理失败</span>
                      </>
                    )}
                  </div>
                  
                  {/* 任务ID */}
                  <div className="text-xs text-gray-500 border-t border-gray-200 pt-2">
                    Task ID: {taskStatus.task_id}
                  </div>
                </div>
              )}
            </div>
          )}
        </form>
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
            <Link to="/archives" className="text-blue-600 hover:text-blue-800 font-medium">
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

      {/* 最近添加的网页 */}
      {!loading && recentArchives.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">📄 最近保存的网页</h2>
            <Link to="/archives?type=archives" className="text-blue-600 hover:text-blue-800 font-medium">
              查看全部 →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recentArchives.map((archive) => (
              <ContentPreview key={`archive-${archive.id}`} content={archive} />
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
