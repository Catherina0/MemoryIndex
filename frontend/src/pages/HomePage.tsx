// #region HomePage - 首页

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

export default function HomePage() {
  const [stats, setStats] = useState<any>(null)
  const [recentItems, setRecentItems] = useState<ContentListItem[]>([])
  const [loading, setLoading] = useState(true)

  // #region 导入表单状态
  const [importUrl, setImportUrl] = useState('')
  const [contentType, setContentType] = useState<'archive' | 'video'>('archive')
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
      const endpoint = contentType === 'video'
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
        setContentType('archive')
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
    <div className="space-y-10 animate-fade-in">
      {/* #region Hero 区域 */}
      <section className="pt-6 sm:pt-10 pb-2">
        <div className="max-w-2xl mx-auto text-center space-y-5">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
              MemoryIndex
            </h1>
            <p className="text-slate-500 mt-2 text-sm sm:text-base">
              AI 驱动的个人知识管理系统
            </p>
          </div>

          {/* 搜索栏 */}
          <div className="max-w-xl mx-auto">
            <SearchBar size="large" placeholder="搜索视频、网页、笔记..." />
          </div>

          {/* 统计指标 */}
          {!loading && stats && (
            <div className="flex items-center justify-center gap-6 text-sm text-slate-500">
              <Link to="/archives" className="hover:text-primary-600 transition-colors">
                <span className="font-semibold text-slate-800">{stats.total_videos}</span> 个视频
              </Link>
              <span className="w-1 h-1 bg-slate-300 rounded-full" />
              <Link to="/archives" className="hover:text-primary-600 transition-colors">
                <span className="font-semibold text-slate-800">{stats.total_archives}</span> 个网页
              </Link>
              <span className="w-1 h-1 bg-slate-300 rounded-full" />
              <span>
                <span className="font-semibold text-slate-800">{stats.total_tags}</span> 个标签
              </span>
            </div>
          )}
        </div>
      </section>
      {/* #endregion */}

      {/* #region 快速导入 */}
      <section className="max-w-2xl mx-auto">
        <div className="card p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-4 h-4 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <h2 className="text-sm font-semibold text-slate-800">快速导入</h2>
          </div>

          <form onSubmit={handleImport} className="space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="粘贴链接或分享文本 (YouTube, Bilibili, 知乎, Twitter...)"
                disabled={isImporting}
                className="input-field disabled:bg-slate-50 disabled:text-slate-400"
              />
              <button
                type="submit"
                disabled={isImporting || !importUrl.trim()}
                className="btn-primary whitespace-nowrap px-5"
              >
                {isImporting ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    处理中
                  </span>
                ) : '导入'}
              </button>
            </div>

            {/* 内容类型选择 + OCR 选项 */}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              {/* 内容类型单选 */}
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none hover:text-slate-800 transition-colors">
                  <input
                    type="radio"
                    name="contentType"
                    value="archive"
                    checked={contentType === 'archive'}
                    onChange={() => setContentType('archive')}
                    disabled={isImporting}
                    className="w-3.5 h-3.5 border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                  />
                  <span>网页</span>
                </label>
                <label className="inline-flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none hover:text-slate-800 transition-colors">
                  <input
                    type="radio"
                    name="contentType"
                    value="video"
                    checked={contentType === 'video'}
                    onChange={() => setContentType('video')}
                    disabled={isImporting}
                    className="w-3.5 h-3.5 border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                  />
                  <span>视频</span>
                </label>
              </div>

              <span className="hidden sm:block w-px h-4 bg-slate-200" />

              {/* OCR 选项 */}
              <label className="inline-flex items-center gap-1.5 text-sm text-slate-500 cursor-pointer select-none hover:text-slate-700 transition-colors">
                <input
                  type="checkbox"
                  checked={useOcr}
                  onChange={(e) => setUseOcr(e.target.checked)}
                  disabled={isImporting}
                  className="w-3.5 h-3.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                />
                <span>OCR 识别</span>
              </label>
            </div>

            {/* #region 导入状态反馈 */}
            {importError && (
              <div className="flex items-start gap-2 px-3.5 py-2.5 bg-red-50 border border-red-200/60 text-red-700 rounded-xl text-sm animate-fade-in">
                <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {importError}
              </div>
            )}

            {importSuccess && (
              <div className="space-y-2.5 animate-fade-in">
                <div className="flex items-start gap-2 px-3.5 py-2.5 bg-emerald-50 border border-emerald-200/60 text-emerald-700 rounded-xl text-sm">
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {importSuccess}
                </div>

                {/* 任务进度 */}
                {taskStatus && (
                  <div className="card p-3.5 space-y-2.5">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-700 font-medium">{taskStatus.current_step}</span>
                      <span className="text-slate-400 tabular-nums text-xs">{taskStatus.progress}%</span>
                    </div>

                    {/* 进度条 */}
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`progress-bar ${
                          taskStatus.status === 'error' ? 'bg-red-500'
                          : taskStatus.status === 'completed' ? 'bg-emerald-500'
                          : 'bg-primary-500'
                        }`}
                        style={{ width: `${taskStatus.progress}%` }}
                      />
                    </div>

                    {/* 日志折叠 */}
                    {taskStatus.logs && taskStatus.logs.length > 0 && (
                      <details className="text-xs">
                        <summary className="text-slate-400 cursor-pointer hover:text-slate-600 transition-colors">
                          查看日志 ({taskStatus.logs.length})
                        </summary>
                        <div className="mt-2 bg-slate-900 text-slate-100 rounded-lg p-3 font-mono max-h-36 overflow-y-auto text-[11px] leading-relaxed">
                          {taskStatus.logs.map((log, idx) => (
                            <div key={idx} className="mb-0.5">
                              <span className={
                                log.level === 'error' || log.level === 'ERROR' ? 'text-red-400'
                                : log.level === 'warning' || log.level === 'WARNING' ? 'text-amber-400'
                                : 'text-emerald-400'
                              }>
                                [{log.level}]
                              </span>{' '}
                              <span className="text-slate-500">{log.timestamp}</span>{' '}
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
        </div>
      </section>
      {/* #endregion */}

      {/* #region 最近添加 */}
      {!loading && recentItems.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-800">最近添加</h2>
            <Link
              to="/archives"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors"
            >
              查看全部 &rarr;
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recentItems.map((item) => (
              <ContentPreview key={`${item.type}-${item.id}`} content={item} />
            ))}
          </div>
        </section>
      )}
      {/* #endregion */}

      {/* #region 热门标签 */}
      {!loading && stats?.top_tags?.length > 0 && (
        <section>
          <h2 className="text-base font-semibold text-slate-800 mb-3">热门标签</h2>
          <div className="flex flex-wrap gap-2">
            {stats.top_tags.slice(0, 15).map((tag: any) => (
              <Link
                key={tag.id}
                to={`/search?tags=${tag.name}`}
                className="tag-pill"
              >
                {tag.name}
                <span className="ml-1.5 text-slate-400">{tag.count}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
      {/* #endregion */}
    </div>
  )
}

// #endregion
