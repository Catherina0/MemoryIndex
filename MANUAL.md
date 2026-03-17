# MemoryIndex 使用手册

## 🎯 一句话说明
**用 AI 自动把视频和网页转化成知识库，提供配套 Web 界面查询和管理。**

---

## ⚡ 最快开始（5分钟）

### 步骤1：启动系统
```bash
cd ~/Documents/GitHub/knowledge
bash start-dev.sh
```

### 步骤2：打开浏览器
- 🎨 **前端**：http://localhost:3000
- 📚 **API 文档**：http://localhost:8000/docs

---

## 📚 核心功能速查

| 功能 | 命令 | 说明 |
|------|------|------|
| 处理本地视频 | `make run Path=video.mp4` | 转写+摘要（快） |
| 完整视频处理 | `make ocr Path=video.mp4` | 转写+OCR+摘要（慢） |
| 下载并处理 | `make download-ocr URL=...` | YouTube/B站等 |
| 归档网页 | `make archive URL=...` | 提取内容+摘要 |
| 搜索知识库 | `make search Q="关键词"` | CLI 搜索 |
| 查看统计 | `make db-stats` | 库存统计 |

---

## 🌐 Web 界面功能

### 📖 首页
- 知识库概览（视频数、网页数、标签数）
- 热门标签云
- 最近添加的内容

### 🔍 搜索页
- 全文搜索
- 标签多选过滤
- 分页浏览

### 📄 内容详情
- 完整标题和元数据
- 转写文本标签页
- OCR 文本标签页
- AI 报告标签页

### 📊 统计仪表板
- 库存统计
- 热门标签排行
- 数据分析

---

## 🍪 Cookie 管理

```bash
make login              # 浏览器登录保存所有平台 Cookie
make list-cookies       # 列出已保存 Cookie
make delete-cookie DOMAIN=xiaohongshu.com  # 删除指定
```

---

## 🗄️ 数据库操作

```bash
make db-init            # 初始化数据库
make db-stats           # 查看详细统计
make db-clear           # 清除所有数据（谨慎！）
make db-delete ID=123   # 删除指定记录
```

---

## 📦 导入工作流

### 🎬 视频工作流

1️⃣ **获取视频**
```bash
make download-ocr URL="https://youtube.com/watch?v=..."
```

2️⃣ **查看前端**
```
打开 http://localhost:3000/search
搜索关键词找到视频
点击查看转写、OCR、报告
```

### 🕸️ 网页工作流

1️⃣ **归档网页**
```bash
make archive URL="https://zhuanlan.zhihu.com/p/xxxxx"
```

2️⃣ **在前端查看**
```
刷新 http://localhost:3000
搜索相关内容找到网页
```

---

## 🎨 前端操作

### API 请求示例

```bash
# 搜索
curl "http://localhost:8000/api/search?q=ai&limit=10"

# 获取统计
curl "http://localhost:8000/api/stats"

# 获取标签
curl "http://localhost:8000/api/tags"
```

### 浏览器 Console 测试

```javascript
// 测试 API 连接
fetch('/api/stats')
  .then(r => r.json())
  .then(d => console.log(d))
```

---

## 🛠️ 常见操作

### 添加标签
```bash
# 导入时自动提取，或通过数据库 API 手动添加
```

### 搜索文本
- **前端**：http://localhost:3000/search —— 使用搜索框
- **CLI**：`make search Q="关键词"` —— 命令行搜索

### 查看内容
- **前端**：点击内容卡片查看详情
- **CLI**：`make search Q="..."` —— 查看摘要

### 删除内容
```bash
make db-delete ID=123
```

---

## 🐛 故障排除

### ❌ 前端无法连接后端

**解决**：
1. 确保后端运行：`python -m backend.main`
2. 检查端口：`lsof -i :8000`
3. 清除浏览器缓存

### ❌ 搜索返回空结果

**解决**：
1. 确认数据已导入：`make db-stats`
2. 导入测试数据：`make run Path=...`

### ❌ 依赖安装失败

**解决**：
```bash
pip install -U pip
npm install -g npm@latest
```

---

## 📚 详细文档

| 文档 | 用途 |
|------|------|
| [API.md](API.md) | API 端点详解 |
| [CHEATSHEET.txt](CHEATSHEET.txt) | 命令速查 |
| [Remember.md](Remember.md) | 核心信息 |
| [Docs/FRONTEND_GUIDE.md](Docs/FRONTEND_GUIDE.md) | 前端开发 |
| [Docs/BACKEND_API_GUIDE.md](Docs/BACKEND_API_GUIDE.md) | 后端开发 |
| [Docs/FRONTEND_QUICKSTART.md](Docs/FRONTEND_QUICKSTART.md) | 前端启动 |

---

## 📊 项目结构速览

```
MemoryIndex/
├── 📹 core/              # 视频处理
├── 🕸️  archiver/         # 网页归档
├── 🔍 db/                # 数据库和搜索
├── 📚 backend/           # FastAPI 服务
├── 🎨 frontend/          # React 应用
├── 📖 docs/              # 用户生成的输出
├── Makefile              # 命令接口
└── start-dev.sh          # 启动脚本
```

---

## ⌨️ 完整命令速查

```bash
# 系统启动
bash start-dev.sh                    # 一键启动前后端

# 视频处理
make run Path=video.mp4              # 快速处理
make ocr Path=video.mp4              # 完整处理
make download-ocr URL=...            # 下载并处理

# 网页归档
make archive URL=...                 # 单个归档
make archive-batch FILE=urls.txt     # 批量归档
make url-clean URL="..."             # 清理追踪

# Cookie 管理
make login                           # 保存登录态
make list-cookies                    # 列出 Cookie
make clear-cookies                   # 清除所有

# 数据库操作
make db-init                         # 初始化
make db-stats                        # 查看统计
make db-delete ID=123                # 删除记录

# 搜索查询
make search Q="关键词"               # 命令行搜索
```

---

## 🎓 学习路径

1. ✅ 运行 `bash start-dev.sh` 启动系统
2. ✅ 访问 http://localhost:3000 浏览界面
3. ✅ 导入一个视频：`make run Path=...`
4. ✅ 在前端搜索和查看内容
5. ✅ 查看 [API.md](API.md) 了解更多 API
6. ✅ 阅读 [Docs/FRONTEND_GUIDE.md](Docs/FRONTEND_GUIDE.md) 深入学习

---

## 💬 获取帮助

- 📖 查看 [README.md](README.md) 项目总览
- 📚 查看本目录中的所有 `.md` 文件
- 🐛 提交 Issue 到 [GitHub](https://github.com/Catherina0/MemoryIndex)

---

**最后更新**：2025-03-18  
**状态**：✅ 完全就绪  
*Nya～*
