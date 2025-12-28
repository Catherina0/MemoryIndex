# 视频下载功能使用指南

## 概览

项目新增了统一的视频下载层，支持从多个平台（YouTube、Bilibili、小红书等）下载视频，并自动处理。

## 核心特性

### 🎯 统一接口
- **单一入口**：`download_video(url)` → 返回本地文件信息
- **自动降级**：智能选择下载工具
  - 优先：yt-dlp（支持大多数平台）
  - B站降级：BBDown
  - 小红书降级：XHS-Downloader

### 📁 统一存储
- 所有视频下载到 `videos/` 目录
- 文件命名格式：`平台_视频ID_标题.mp4`
- 示例：
  - `youtube_dQw4w9WgXcQ_Rick_Astley_Never_Gonna_Give_You_Up.mp4`
  - `bilibili_BV1xx411c7mD_某UP主的视频标题.mp4`

### 🔄 处理流程
```
下载视频 → 抽帧 → OCR → ASR → AI总结 → 存档
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 yt-dlp（必需）
make install

# 或手动安装
pip install yt-dlp
```

### 2. 基本使用

#### 命令行直接下载

```bash
# 下载 YouTube 视频
python video_downloader.py "https://www.youtube.com/watch?v=xxxxx"

# 下载 B站视频
python video_downloader.py "https://www.bilibili.com/video/BVxxxxx"

# 指定下载目录
python video_downloader.py -d my_videos "https://example.com/video"

# 强制重新下载
python video_downloader.py -f "https://example.com/video"
```

#### Makefile 快捷命令

```bash
# 仅下载视频
make download URL="https://www.youtube.com/watch?v=xxxxx"

# 下载后自动处理（音频模式）
make download-run URL="https://www.bilibili.com/video/BVxxxxx"

# 下载后自动处理（完整OCR模式）
make download-ocr URL="https://www.youtube.com/watch?v=xxxxx"
```

#### Python 代码调用

```python
from video_downloader import VideoDownloader

# 创建下载器
downloader = VideoDownloader(download_dir="videos")

# 下载视频
file_info = downloader.download_video("https://www.youtube.com/watch?v=xxxxx")

print(f"文件路径: {file_info.file_path}")
print(f"平台: {file_info.platform}")
print(f"视频ID: {file_info.video_id}")
print(f"标题: {file_info.title}")
print(f"时长: {file_info.duration} 秒")
```

### 3. 集成到处理流程

```bash
# process_video.py 现在也支持URL
python process_video.py "https://www.youtube.com/watch?v=xxxxx"
python process_video.py "https://www.bilibili.com/video/BVxxxxx" --with-frames
```

## 支持的平台

| 平台 | URL示例 | 主要工具 | 降级工具 | 状态 |
|------|---------|----------|----------|------|
| YouTube | youtube.com/watch?v=xxx | yt-dlp | - | ✅ 已测试 |
| Bilibili | bilibili.com/video/BVxxx | yt-dlp | BBDown | ✅ 已测试 |
| 小红书 | xiaohongshu.com/xxx | yt-dlp | XHS-Downloader | ⚠️ 需配置 |
| 抖音 | douyin.com/xxx | yt-dlp | - | ⚠️ 需测试 |
| Twitter/X | twitter.com/xxx | yt-dlp | - | ⚠️ 需测试 |

## 降级工具配置

### BBDown（B站专用）

```bash
# 安装（如需要）
# macOS
brew install bbdown

# Windows
# 从 https://github.com/nilaoda/BBDown/releases 下载

# Linux
# 从 https://github.com/nilaoda/BBDown/releases 下载
```

### XHS-Downloader（小红书专用）

```bash
# 参考官方文档
# https://github.com/JoeanAmier/XHS-Downloader

# 注意：小红书下载可能需要登录态
```

## 完整示例

### 示例1：YouTube → 完整处理

```bash
# 下载 + 音频转写 + OCR + AI总结
make download-ocr URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 示例2：B站 → 仅音频处理

```bash
# 下载 + 音频转写 + AI总结（不含OCR）
make download-run URL="https://www.bilibili.com/video/BV1xx411c7mD"
```

### 示例3：批量下载处理

```bash
#!/bin/bash
# batch_download.sh

urls=(
  "https://www.youtube.com/watch?v=video1"
  "https://www.youtube.com/watch?v=video2"
  "https://www.bilibili.com/video/BV1234567890"
)

for url in "${urls[@]}"; do
  echo "处理: $url"
  make download-run URL="$url"
done
```

## 返回值结构

`LocalFileInfo` 数据类包含：

```python
@dataclass
class LocalFileInfo:
    file_path: Path           # 本地文件路径
    platform: str             # 平台名称
    video_id: str             # 视频ID
    title: str                # 视频标题
    duration: Optional[float] # 时长（秒）
    uploader: Optional[str]   # 上传者
    upload_date: Optional[str] # 上传日期
    metadata: Dict[str, Any]  # 其他元数据
```

## 注意事项

### 1. 依赖项
- **必需**：`yt-dlp`（通过 `pip install yt-dlp` 或 `make install`）
- **可选**：`BBDown`（B站降级）
- **可选**：`XHS-Downloader`（小红书降级）

### 2. 网络要求
- 部分平台可能需要代理
- B站下载可能需要登录
- 小红书下载通常需要登录态

### 3. 存储空间
- 视频文件通常较大，确保有足够存储空间
- 默认存储在 `videos/` 目录

### 4. 文件名
- 自动清洗文件名中的非法字符
- 标题过长时会自动截断（最长100字符）

## 故障排查

### 下载失败

```bash
# 1. 检查网络连接
ping youtube.com

# 2. 更新 yt-dlp
pip install --upgrade yt-dlp

# 3. 查看详细错误信息
python video_downloader.py "URL" -v
```

### B站下载失败

```bash
# 尝试使用 BBDown
bbdown "https://www.bilibili.com/video/BVxxxxx"

# 检查是否需要登录
# 某些视频可能需要大会员
```

### 小红书下载失败

```bash
# 小红书通常需要特殊处理
# 参考 XHS-Downloader 文档进行配置
```

## 架构设计

### 核心组件

```
video_downloader.py
├── VideoDownloader         # 主下载器类
├── LocalFileInfo          # 文件信息数据类
├── _detect_platform()     # 平台检测
├── _download_with_ytdlp() # yt-dlp 下载
├── _download_with_bbdown() # BBDown 降级
└── _download_with_xhs()   # XHS-Downloader 降级
```

### 集成点

1. **独立使用**：`video_downloader.py` 命令行工具
2. **Makefile集成**：`make download`, `make download-run`, `make download-ocr`
3. **Python集成**：`process_video.py` 支持URL输入
4. **库调用**：`from video_downloader import VideoDownloader`

## 未来改进

- [ ] 支持播放列表批量下载
- [ ] 支持更多平台（Instagram, Facebook等）
- [ ] 添加下载进度条
- [ ] 支持断点续传
- [ ] 缓存视频元数据
- [ ] 支持自定义命名模板

## 相关文档

- [README.md](../README.md) - 项目总览
- [QUICKSTART.md](../docs/QUICKSTART.md) - 快速开始
- [process_video.py](../process_video.py) - 视频处理主脚本
- [Makefile](../Makefile) - Make命令参考

## 许可与致谢

本下载功能基于以下开源项目：
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 通用视频下载工具
- [BBDown](https://github.com/nilaoda/BBDown) - B站下载工具
- [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) - 小红书下载工具
