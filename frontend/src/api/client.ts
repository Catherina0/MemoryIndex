// #region API 客户端

// 前端 API 请求客户端（TypeScript/JavaScript）

import axios, { AxiosInstance } from 'axios'

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// #region 搜索 API

export interface SearchResult {
  id: number
  type: 'video' | 'archive'
  title: string
  summary?: string
  source_type: string
  tags: string[]
  created_at: string
  url?: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  limit: number
  offset: number
  estimated_time_ms?: number
}

export async function searchContent(
  query: string,
  tags?: string[],
  sourceType?: string,
  limit = 20,
  offset = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
    offset: offset.toString(),
  })

  if (tags && tags.length > 0) {
    params.append('tags', tags.join(','))
  }
  if (sourceType) {
    params.append('source_type', sourceType)
  }

  const { data } = await apiClient.get<SearchResponse>(`/search?${params}`)
  return data
}

// #endregion

// #region 内容 API

export interface ContentDetail {
  id: number
  type: 'video' | 'archive'
  title: string
  summary?: string
  source_type: string
  source_url?: string
  created_at: string
  tags: string[]
  transcript?: string
  ocr_text?: string
  report?: string
  raw_archive?: string
  readme_text?: string
  duration_seconds?: number
  file_path?: string
}

export interface ContentListItem {
  id: number
  title: string
  summary?: string
  source_type: string
  source_url?: string
  tags: string[]
  created_at: string
  type: 'video' | 'archive'
  duration?: number  // 视频时长（秒）
  file_size?: number  // 文件大小（字节）
}

export interface ContentListResponse {
  items: ContentListItem[]
  total: number
  limit: number
  offset: number
}

export async function getContentDetail(
  contentId: number,
  contentType: 'video' | 'archive' = 'video'
): Promise<ContentDetail> {
  const { data } = await apiClient.get<ContentDetail>(
    `/content/${contentId}?content_type=${contentType}`
  )
  return data
}

export async function listVideos(
  limit = 20,
  offset = 0,
  sort: 'recent' | 'oldest' | 'duration' = 'recent'
): Promise<ContentListResponse> {
  const { data } = await apiClient.get<ContentListResponse>(
    `/videos?limit=${limit}&offset=${offset}&sort=${sort}`
  )
  return data
}

export async function listArchives(
  limit = 20,
  offset = 0,
  sort: 'recent' | 'oldest' = 'recent'
): Promise<ContentListResponse> {
  const { data } = await apiClient.get<ContentListResponse>(
    `/archives?limit=${limit}&offset=${offset}&sort=${sort}`
  )
  return data
}

// #endregion

// #region 标签 API

export interface Tag {
  id: number
  name: string
  count: number
  category?: string
}

export async function listTags(limit = 50): Promise<Tag[]> {
  const { data } = await apiClient.get<Tag[]>(`/tags?limit=${limit}`)
  return data
}

// #endregion

// #region 统计 API

export interface Stats {
  total_videos: number
  total_archives: number
  total_tags: number
  top_tags: Tag[]
  average_video_duration?: number
  storage_used_gb?: number
  last_updated: string
}

export async function getStats(): Promise<Stats> {
  const { data } = await apiClient.get<Stats>('/stats')
  return data
}

export async function healthCheck() {
  const { data } = await apiClient.get('/health')
  return data
}

// #endregion

export default apiClient

// #endregion
