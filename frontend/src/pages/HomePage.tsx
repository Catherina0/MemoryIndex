import { useState, useEffect, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { getStats, listVideos, listArchives, type ContentListItem } from '@/api/client'
import apiClient from '@/api/client'
import ContentPreview from '@/components/ContentPreview'
import SearchBar from '@/components/SearchBar'

// #region 类型定义
interface TaskStatus {
  task_id: string
  status: string
  progress: number
  current_step: string
  error_message?: string
  error?: string
  logs?: Array<{
    timestamp: string
    level: string
    message: string
  }>
}
// #endregion

// #region HomePage
export default function HomePage() {
  const [stats, setStats] = useState<any>(null)
  const [recentItems, setRecentItems] = useState<ContentListItem[]>([])
  const [loading, setLoading] = useState(true)

  // #region 导入表单状态
  const [importUrl, setImportUrl] = useState('')
  const [useOcr, setUseOcr] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [importError, setImportError] = useState('')
  const [importSuccess, setImportSuccess] = useState('')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  // #endregion

  // #region 加载首页数据
  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, videosRes, archivesRes] = await Promise.all([
          getStats(),
          listVideos(4, 0, 'recent'),
          listArchives(4, 0, 'recent'),
        ])
        setStats(statsData)
        // 合并并按时间排序，取前 6 条
        const all = [...videosRes.items, ...archivesRes.items]
        all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setRecentItems(all.slice(0, 6))
      } catch (_err) {
        // 静默处理
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])
  // #endregion

  // #region 任务轮询
  useEffect(() => {
    if (!taskId) return

    const pollTaskStatus = async () => {
      try {
        const { data } = await apiClient.get<TaskStatus>(`/tasks/${taskId}`)
        setTaskStatus(data)

        if (data.status === 'completed' || data.status === 'error') {
          if (data.status === 'completed') {
            setImportSuccess('导入完成')
            setTimeout(() => {
              setImportSuccess('')
              setTaskId(null)
              setTaskStatus(null)
            }, 5000)
          } else {
            setImportError(`导入失败: ${data.error_message || data.error || '未知错误'}`)
          }
          setIsImporting(false)
        }
      } catch (_err) {
        // 轮询失败静默处理
      }
    }

    pollTaskStatus()
    const interval = window.setInterval(pollTaskStatus, 1500)
    return () => window.clearInterval(interval)
  }, [taskId])
  // #endregion

  // #region 导入处理
  const handleImport = async (e: FormEvent) => {
    e.preventDefault()
    if (!importUrl.trim()) {
      setImportError('请输入链接或分享文本')
      return
    }

    setIsImporting(true)
    setImportError('')
    setImportSuccess('')
    setTaskId(null)
    setTaskStatus(null)

    try {
      const url = importUrl.trim().toLowerCase()
      const videoDomains = [
        'youtube.com', 'youtu.be', 'bilibili.com', 'b23.tv',
        'vimeo.com', 'dailymotion.com', 'qq.com', 'iqiyi.com'
      ]
      const isVideo = videoDomains.some(d => url.includes(d))

      const endpoint = isVideo
        ? (useOcr ? '/download-ocr' : '/download-run')
        : (useOcr ? '/archive-ocr' : '/archive-run')

      const { data } = await apiClient.post(endpoint, { url: importUrl.trim() })

      if (data.status === 'error') {
        setImportError(data.message)
        setIsImporting(false)
      } else if (data.task_id) {
        setImportSuccess(data.message)
        setTaskId(data.task_id)
        setImportUrl('')
        setUseOcr(false)
      } else {
        setImportSuccess(data.message || '已提交')
        setIsImporting(false)
        setTimeout(() => setImportSuccess(''), 3000)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '导入失败，请稍后重试'
      setImportError(errorMsg)
      setIsImporting(false)
    }
  }
  // #endregion

  return (
    <div className="space-y-10">
      {/* 搜索区域 */}
      <section className="pt-8 pb-2">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">MemoryIndex</h1>
        <p className="text-sm text-gray-500 mb-5">AI 驱动的个人知识管理系统</p>
        <div className="max-w-xl">
          <SearchBar />
        </div>
      </section>

      {/* 统计概览 */}
      {!loading && stats && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatBlock label="视频" value={stats.total_videos} />
          <StatBlock label="网页" value={stats.total_archives} />
          <StatBlock label="标签" value={stats.total_tags} />
          <StatBlock
            label="平均时长"
            value={stats.average_video_duration
              ? `${Math.round(stats.average_video_duration / 60)}分`
              : '-'}
          />
        </section>
      )}

      {/* 快速导入 */}
      <section className="bg-white border border-gray-200 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">快速导入</h2>
        <form onSubmit={handleImport} className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              placeholder="粘贴链接或分享文本 (YouTube, Bilibili, 知乎, Twitter...)"
              disabled={isImporting}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400"
            />
            <button
              type="submit"
              disabled={isImporting || !importUrl.trim()}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {isImporting ? '处理中...' : '导入'}
            </button>
          </div>

          <label className="inline-flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={useOcr}
              onChange={(e) => setUseOcr(e.target.checked)}
              disabled={isImporting}
              className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>启用 OCR 识别（更慢但更完整）</span>
          </label>

          {/* #region 导入状态反馈 */}
          {importError && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              {importError}
            </div>
          )}

          {importSuccess && (
            <div className="space-y-2">
              <div className="px-3 py-2 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
                {importSuccess}
              </div>

              {taskStatus && (
                <div className="px-3 py-3 bg-gray-50 border border-gray-200 rounded-lg space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-700">{taskStatus.current_step}</span>
                    <span className="text-gray-500 tabular-nums">{taskStatus.progress}%</span>
                  </div>

                  {/* 进度条 */}
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        taskStatus.status === 'error' ? 'bg-red-500'
                        : taskStatus.status === 'completed' ? 'bg-green-500'
                        : 'bg-blue-500'
                      }`}
                      style={{ width: `${taskStatus.progress}%` }}
                    />
                  </div>

                  {/* 日志 */}
                  {taskStatus.logs && taskStatus.logs.length > 0 && (
                    <details className="text-xs">
                      <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
                        查看日志 ({taskStatus.logs.length})
                      </summary>
                      <div className="mt-2 bg-gray-900 text-gray-100 rounded p-2 font-mono max-h-36 overflow-y-auto">
                        {taskStatus.logs.map((log, idx) => (
                          <div key={idx} className="mb-0.5">
                            <span className={
                              log.level === 'error' || log.level === 'ERROR' ? 'text-red-400'
                              : log.level === 'warning' || log.level === 'WARNING' ? 'text-yellow-400'
                              : 'text-green-400'
                            }>
                              [{log.level}]
                            </span>{' '}
                            <span className="text-gray-500">{log.timestamp}</span>{' '}
                            {log.message}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}
          {/* #endregion */}
        </form>
      </section>

      {/* 最近添加 */}
      {!loading && recentItems.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">最近添加</h2>
            <Link to="/archives" className="text-sm text-blue-600 hover:text-blue-800">
              查看全部
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recentItems.map((item) => (
              <ContentPreview key={`${item.type}-${item.id}`} content={item} />
            ))}
          </div>
        </section>
      )}

      {/* 热门标签 */}
      {!loading && stats?.top_tags?.length > 0 && (
        <section>
          <h2 className="text-base font-semibold text-gray-900 mb-3">热门标签</h2>
          <div className="flex flex-wrap gap-2">
            {stats.top_tags.slice(0, 12).map((tag: any) => (
              <Link
                key={tag.id}
                to={`/search?tags=${tag.name}`}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
              >
                {tag.name}
                <span className="ml-1 text-gray-400">{tag.count}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
// #endregion

// #region 统计数字块
function StatBlock({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
      <div className="text-xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  )
}
// #endregion
