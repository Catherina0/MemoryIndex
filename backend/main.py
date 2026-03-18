#region FastAPI 后端应用主入口

"""
MemoryIndex 后端 API 服务
提供 REST API 接口，连接前端与核心功能
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
from typing import Optional, List
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.repository import (
    VideoRepository, ArchiveRepository, TagRepository, 
    SearchRepository, StatsRepository
)
from db.models import Video, SourceType, ProcessingStatus
from backend.models import (
    SearchResultResponse, VideoDetailResponse, StatsResponse,
    TagResponse, ContentListResponse, ImportRequest, ImportResponse
)
from backend.services import SearchService, ContentService, StatsService, ImportService
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# #region 初始化依赖注入

# 数据库存储库
video_repo = VideoRepository()
archive_repo = ArchiveRepository()
tag_repo = TagRepository()
search_repo = SearchRepository()
stats_repo = StatsRepository()

# 业务服务层
search_service = SearchService(search_repo, video_repo, archive_repo)
content_service = ContentService(video_repo, archive_repo)
stats_service = StatsService(stats_repo, tag_repo, video_repo, archive_repo)
import_service = ImportService(video_repo, archive_repo)

# #endregion

# #region FastAPI 应用配置

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 MemoryIndex API 服务器启动")
    yield
    logger.info("🛑 MemoryIndex API 服务器关闭")

app = FastAPI(
    title="MemoryIndex API",
    description="基于 MIAP 的知识管理系统后端 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应改为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# #endregion

# #region 根路由

@app.get("/")
async def root():
    """API 健康检查"""
    return {
        "status": "healthy",
        "service": "MemoryIndex API",
        "version": "1.0.0"
    }

# #endregion

# #region 搜索 API

@app.get("/api/search", response_model=SearchResultResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤，逗号分隔"),
    source_type: Optional[str] = Query(None, description="内容类型过滤"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    全文搜索接口
    
    参数:
        q: 搜索关键词
        tags: 按标签过滤（逗号分隔）
        source_type: 按内容类型过滤（video/archive）
        limit: 返回数量（最多100）
        offset: 分页偏移
    
    返回:
        搜索结果列表及统计信息
    """
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        results = search_service.search(
            query=q,
            tags=tag_list,
            source_type=source_type,
            limit=limit,
            offset=offset
        )
        return results
    except Exception as e:
        logger.error(f"搜索错误: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败")

# #endregion

# #region 内容 API

@app.get("/api/videos", response_model=ContentListResponse)
async def list_videos(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("recent", pattern="^(recent|oldest|popular)$")
):
    """列出所有视频"""
    try:
        return content_service.list_videos(limit, offset, sort)
    except Exception as e:
        logger.error(f"获取视频列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取视频列表失败")

@app.get("/api/archives", response_model=ContentListResponse)
async def list_archives(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("recent", pattern="^(recent|oldest|popular)$")
):
    """列出所有网页归档"""
    try:
        return content_service.list_archives(limit, offset, sort)
    except Exception as e:
        logger.error(f"获取归档列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取归档列表失败")

@app.get("/api/content/{content_id}", response_model=VideoDetailResponse)
async def get_content_detail(
    content_id: int,
    content_type: str = Query("video", pattern="^(video|archive)$")
):
    """获取内容详情"""
    try:
        if content_type == "video":
            return content_service.get_video_detail(content_id)
        else:
            return content_service.get_archive_detail(content_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取内容详情错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取内容详情失败")

# #endregion

# #region 标签 API

@app.get("/api/tags", response_model=List[TagResponse])
async def list_tags(limit: int = Query(50, ge=1, le=200)):
    """获取所有标签及其使用频次"""
    try:
        return stats_service.get_all_tags(limit)
    except Exception as e:
        logger.error(f"获取标签列表错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取标签列表失败")

# #endregion

# #region 统计 API

@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics():
    """获取数据库统计信息"""
    try:
        return stats_service.get_statistics()
    except Exception as e:
        logger.error(f"获取统计信息错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")

# #endregion

# #region 导入 API

@app.post("/api/import", response_model=ImportResponse)
async def import_content(import_req: ImportRequest):
    """
    导入内容（URL）
    
    Args:
        import_req: ImportRequest 对象
            - url: 要导入的 URL
            - content_type: 内容类型（auto/video/archive，默认 auto）
            - use_ocr: 是否启用 OCR（默认 false）
    
    Returns:
        ImportResponse 对象
    """
    try:
        result = import_service.import_content(
            url=import_req.url,
            content_type=import_req.content_type,
            use_ocr=import_req.use_ocr
        )
        
        return ImportResponse(
            status=result['status'],
            content_id=result.get('content_id'),
            message=result['message'],
            content_type=result.get('content_type')
        )
    except Exception as e:
        logger.error(f"导入 API 错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")

# #endregion

# #region 健康检查和内省

@app.get("/api/health")
async def health_check():
    """详细的健康检查"""
    try:
        stats = stats_service.get_statistics()
        return {
            "status": "healthy",
            "database": "connected",
            "total_content": stats.total_videos + stats.total_archives
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="服务不可用")

# #endregion

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

# #endregion
