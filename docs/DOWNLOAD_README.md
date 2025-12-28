# 统一视频下载功能 - 快速参考

## 🎯 核心功能

**一键从任何平台下载视频并自动处理**

```bash
# 下载并自动处理
make download-run URL="https://www.youtube.com/watch?v=xxxxx"
make download-ocr URL="https://www.bilibili.com/video/BVxxxxx"
```

## 📥 可用命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `make download URL=<url>` | 仅下载视频 | `make download URL="https://youtube.com/xxx"` |
| `make download-run URL=<url>` | 下载+音频转写+总结 | `make download-run URL="https://bilibili.com/xxx"` |
| `make download-ocr URL=<url>` | 下载+完整处理(OCR) | `make download-ocr URL="https://youtube.com/xxx"` |

## 🌐 支持平台

- ✅ YouTube
- ✅ Bilibili（B站）
- ⚠️ 小红书（需配置）
- ⚠️ 抖音（需测试）
- ⚠️ Twitter/X（需测试）

## 🚀 快速开始

### 1. 安装依赖
```bash
make setup  # 会自动安装 yt-dlp
```

### 2. 下载并处理视频
```bash
# YouTube视频
make download-run URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# B站视频
make download-ocr URL="https://www.bilibili.com/video/BV1xx411c7mD"
```

### 3. 查看结果
- 下载的视频：`videos/` 目录
- 处理结果：`output/` 目录

## 📖 详细文档

完整功能说明请查看：[DOWNLOAD_GUIDE.md](DOWNLOAD_GUIDE.md)

## 💡 工作原理

```
输入URL
  ↓
检测平台（YouTube/Bilibili/小红书...）
  ↓
智能下载（yt-dlp → BBDown → XHS-Downloader）
  ↓
统一存储（videos/平台_ID_标题.mp4）
  ↓
自动处理（抽帧 → OCR → ASR → AI总结）
  ↓
生成报告（output/）
```

## 🔧 Python API

```python
from video_downloader import VideoDownloader

downloader = VideoDownloader()
file_info = downloader.download_video("https://youtube.com/watch?v=xxx")

print(f"下载完成: {file_info.file_path}")
print(f"平台: {file_info.platform}")
print(f"标题: {file_info.title}")
```

## ⚠️ 注意事项

1. **必需依赖**：`yt-dlp`（自动安装）
2. **可选工具**：BBDown（B站降级）、XHS-Downloader（小红书）
3. **网络要求**：某些平台可能需要代理
4. **存储空间**：视频文件通常较大，确保有足够空间

## 🎨 命名规范

下载的视频文件命名格式：
```
平台_视频ID_清洗后的标题.mp4
```

示例：
- `youtube_dQw4w9WgXcQ_Rick_Astley_Never_Gonna_Give_You_Up.mp4`
- `bilibili_BV1xx411c7mD_某个视频标题.mp4`

## 📝 更新日志

### 2025-12-11
- ✅ 实现统一下载层
- ✅ 支持 YouTube、Bilibili
- ✅ 集成到 Makefile
- ✅ 集成到 process_video.py
- ✅ 添加降级策略

---

**相关文档**：
- 📚 [完整下载指南](DOWNLOAD_GUIDE.md)
- 🚀 [快速开始](QUICKSTART.md)
- 📖 [项目README](../README.md)
