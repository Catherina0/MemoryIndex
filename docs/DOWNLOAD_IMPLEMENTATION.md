# 统一下载层实现总结

## ✅ 已完成功能

### 1. 核心下载模块 (`video_downloader.py`)

**功能特性：**
- ✅ 统一下载接口 `download_video(url) -> LocalFileInfo`
- ✅ 自动平台检测（YouTube, Bilibili, 小红书, 抖音, Twitter等）
- ✅ 智能降级策略：
  - 优先使用 yt-dlp（支持大多数平台）
  - B站失败时降级到 BBDown
  - 小红书失败时降级到 XHS-Downloader
- ✅ 统一文件命名：`平台_视频ID_标题.mp4`
- ✅ 文件名清洗（移除非法字符、截断过长标题）
- ✅ 跳过已下载文件（可选强制重新下载）
- ✅ 完整元数据提取（标题、时长、上传者、上传日期等）
- ✅ 命令行独立使用

**代码结构：**
```
VideoDownloader 类
├── __init__(download_dir)         # 初始化下载目录
├── download_video(url)            # 主入口
├── _detect_platform(url)          # 平台检测
├── _sanitize_filename(filename)   # 文件名清洗
├── _download_with_ytdlp()         # yt-dlp 下载
├── _download_with_bbdown()        # BBDown 降级
└── _download_with_xhs()           # XHS-Downloader 降级

LocalFileInfo 数据类
├── file_path: Path                # 本地文件路径
├── platform: str                  # 平台名称
├── video_id: str                  # 视频ID
├── title: str                     # 视频标题
├── duration: Optional[float]      # 时长
├── uploader: Optional[str]        # 上传者
├── upload_date: Optional[str]     # 上传日期
└── metadata: Dict[str, Any]       # 其他元数据
```

### 2. Makefile 集成

**新增命令：**
```bash
make download URL=<url>        # 仅下载视频
make download-run URL=<url>    # 下载 + 音频转写 + AI总结
make download-ocr URL=<url>    # 下载 + 完整OCR处理
```

**实现细节：**
- ✅ 自动调用 video_downloader.py
- ✅ 提取下载后的文件路径
- ✅ 自动传递给 process_video.py
- ✅ 支持OCR参数传递（DET_MODEL, REC_MODEL, USE_GPU）
- ✅ 友好的进度提示和错误处理

### 3. process_video.py 集成

**新增功能：**
- ✅ 支持URL作为输入参数
- ✅ 自动检测输入是URL还是本地文件
- ✅ URL自动触发下载流程
- ✅ 下载后无缝进入处理流程
- ✅ 向后兼容（不影响现有本地文件处理）

**代码改动：**
```python
# 导入下载器（可选）
from video_downloader import VideoDownloader

# main() 函数中
if is_url:
    downloader = VideoDownloader()
    file_info = downloader.download_video(url)
    video_path = file_info.file_path
else:
    video_path = Path(input_str)
```

### 4. 项目结构更新

**新增文件：**
- ✅ `video_downloader.py` - 核心下载模块
- ✅ `docs/DOWNLOAD_GUIDE.md` - 完整使用指南
- ✅ `docs/DOWNLOAD_README.md` - 快速参考
- ✅ `videos/` - 视频存储目录

**更新文件：**
- ✅ `requirements.txt` - 添加 yt-dlp 依赖
- ✅ `Makefile` - 添加下载相关命令
- ✅ `process_video.py` - 集成下载功能
- ✅ `.gitignore` - 排除视频文件

## 🎯 使用示例

### 命令行使用

```bash
# 1. 仅下载
make download URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 2. 下载并处理（音频模式）
make download-run URL="https://www.bilibili.com/video/BV1xx411c7mD"

# 3. 下载并处理（完整OCR模式）
make download-ocr URL="https://www.youtube.com/watch?v=xxxxx"

# 4. 直接通过 Python
python video_downloader.py "https://www.youtube.com/watch?v=xxxxx"
python process_video.py "https://www.bilibili.com/video/BVxxxxx" --with-frames
```

### Python API 使用

```python
from video_downloader import VideoDownloader

# 创建下载器
downloader = VideoDownloader(download_dir="videos")

# 下载视频
file_info = downloader.download_video("https://www.youtube.com/watch?v=xxxxx")

# 使用下载的文件
print(f"文件位置: {file_info.file_path}")
print(f"平台: {file_info.platform}")
print(f"标题: {file_info.title}")
print(f"时长: {file_info.duration}秒")

# 继续处理...
```

## 🌐 支持的平台

| 平台 | 检测规则 | 主要工具 | 降级工具 | 状态 |
|------|----------|----------|----------|------|
| YouTube | youtube.com, youtu.be | yt-dlp | - | ✅ 完全支持 |
| Bilibili | bilibili.com, b23.tv | yt-dlp | BBDown | ✅ 完全支持 |
| 小红书 | xiaohongshu.com, xhslink.com | yt-dlp | XHS-Downloader | ⚠️ 需配置 |
| 抖音 | douyin.com | yt-dlp | - | ⚠️ 待测试 |
| Twitter/X | twitter.com, x.com | yt-dlp | - | ⚠️ 待测试 |

## 📊 工作流程

```
用户输入URL
    ↓
检测平台类型
    ↓
尝试 yt-dlp 下载 ────── 成功 ──→ 返回文件信息
    ↓ 失败                          ↓
判断平台                         统一存储
    ↓                              ↓
B站? → 尝试 BBDown          videos/平台_ID_标题.mp4
小红书? → 尝试 XHS              ↓
其他 → 报错                  可选：继续处理
                                ↓
                          抽帧 → OCR → ASR → 总结
```

## 🎨 文件命名规范

**格式：**`平台_视频ID_清洗后的标题.mp4`

**实例：**
```
youtube_dQw4w9WgXcQ_Rick_Astley_Never_Gonna_Give_You_Up.mp4
bilibili_BV1xx411c7mD_某个有趣的视频标题.mp4
xiaohongshu_xxxxx_小红书笔记标题.mp4
```

**清洗规则：**
- 移除非法字符：`<>:"/\|?*`
- 空格替换为下划线
- 截断过长标题（最长100字符）
- 移除前后的点和空格

## 💡 技术要点

### 1. 平台检测
```python
def _detect_platform(self, url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "bilibili.com" in url_lower or "b23.tv" in url_lower:
        return "bilibili"
    # ... 更多平台
```

### 2. 降级策略
```python
try:
    return self._download_with_ytdlp(url, platform)
except Exception as e:
    if platform == "bilibili":
        try:
            return self._download_with_bbdown(url)
        except Exception as e2:
            raise Exception("B站下载失败（已尝试所有方法）")
```

### 3. 元数据提取
```python
# 使用 yt-dlp 的 --dump-json
info = json.loads(subprocess.run(
    ["yt-dlp", "--dump-json", "--no-playlist", url],
    capture_output=True, text=True, check=True
).stdout)

video_id = info.get("id")
title = info.get("title")
duration = info.get("duration")
uploader = info.get("uploader")
```

## 🔧 依赖管理

**必需依赖：**
```txt
yt-dlp  # 通过 pip install yt-dlp 或 make install
```

**可选依赖：**
```bash
# BBDown（B站降级）
brew install bbdown  # macOS
# 或从 https://github.com/nilaoda/BBDown/releases 下载

# XHS-Downloader（小红书降级）
# 参考 https://github.com/JoeanAmier/XHS-Downloader
```

## 🚨 错误处理

### 常见错误及解决方案

1. **yt-dlp 未安装**
   ```bash
   make install  # 自动安装所有依赖
   ```

2. **下载失败**
   ```bash
   # 更新 yt-dlp
   pip install --upgrade yt-dlp
   
   # 检查网络
   ping youtube.com
   ```

3. **B站下载失败**
   ```bash
   # 安装 BBDown 作为后备
   brew install bbdown  # macOS
   ```

4. **文件已存在**
   ```bash
   # 使用 -f 强制重新下载
   python video_downloader.py -f "URL"
   ```

## 📈 性能考量

### 下载速度
- yt-dlp：取决于网络带宽和视频平台限制
- BBDown：B站专用，通常更快
- 建议：首次下载选择高峰时段外进行

### 存储空间
- 1080p视频：约 500MB - 2GB（取决于时长）
- 720p视频：约 200MB - 800MB
- 建议：定期清理 `videos/` 目录

### 并发下载
- 当前：单线程顺序下载
- 未来优化：可添加并发下载支持

## 🔮 未来改进方向

### 短期（下一版本）
- [ ] 添加下载进度条（rich库）
- [ ] 支持断点续传
- [ ] 批量下载（播放列表）
- [ ] 下载队列管理

### 中期
- [ ] 更多平台支持（Instagram, Facebook, TikTok）
- [ ] 视频质量选择（720p, 1080p, 4K）
- [ ] 字幕下载
- [ ] 缩略图提取

### 长期
- [ ] Web UI 界面
- [ ] 数据库存储元数据
- [ ] 视频去重检测
- [ ] 自动分类和标签

## 📚 相关文档

- [DOWNLOAD_GUIDE.md](DOWNLOAD_GUIDE.md) - 完整使用指南
- [DOWNLOAD_README.md](DOWNLOAD_README.md) - 快速参考
- [README.md](../README.md) - 项目主文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始

## 🎉 总结

统一下载层成功实现了以下目标：

1. ✅ **统一接口**：一个函数处理所有平台
2. ✅ **智能降级**：自动选择最佳下载工具
3. ✅ **无缝集成**：与现有处理流程完美配合
4. ✅ **易于使用**：Make命令一键完成
5. ✅ **可扩展性**：易于添加新平台支持

上层 pipeline 现在完全不需要关心视频来源，只需：
```python
# 给一个URL，返回一个本地文件
file_info = downloader.download_video(url)
```

然后就可以直接进入：
```
下载 → 抽帧 → ASR → OCR → 总结 → 存档
```

的标准流程！🚀
