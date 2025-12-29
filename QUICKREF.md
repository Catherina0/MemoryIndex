# MemoryIndex 快速参考卡

## 🚀 一分钟开始

```bash
# 1. 安装（仅需一次）
./install.sh

# 2. 立即使用
mi search "关键词"
```

## 📝 常用命令

```bash
# 搜索
mi search "机器学习"                    # 全文搜索
mi search "AI" --field transcript       # 搜索转写
mi search "代码" --field ocr            # 搜索 OCR

# 浏览
mi list                                 # 所有视频
mi list --limit 10                      # 前 10 个
mi topics                               # 所有主题
mi tags --tags 教育                     # 按标签

# 详情
mi show 1                               # 查看 ID=1 的视频

# 处理
mi-process video.mp4                    # 处理新视频
```

## 🔥 高级技巧

### 多关键词搜索

```bash
mi search "Python 机器学习"             # AND 搜索
mi search "Python OR 机器学习"          # OR 搜索
mi search "Python NOT 入门"             # 排除关键词
```

### 按日期排序

```bash
mi list --sort-by date --desc           # 最新的
mi list --sort-by date --asc            # 最旧的
```

### 限制结果

```bash
mi search "AI" --limit 5                # 只显示 5 个结果
```

### 查看热门标签

```bash
mi list-tags --limit 20                 # 前 20 个热门标签
```

## 🛠️ 配置

### 环境变量

在 `~/.memoryindex.env` 或项目 `.env` 中设置：

```bash
# Groq API（语音识别）
GROQ_API_KEY=your_key_here

# 数据库路径
DB_PATH=/path/to/database.db

# OCR 配置
OCR_WORKERS=4
USE_GPU=false
```

### Shell 别名

将以下添加到 `~/.zshrc`：

```bash
# 加载 MemoryIndex 别名
source /path/to/knowledge/alias.sh

# 或手动添加
alias mi-s='mi search'
alias mi-l='mi list'
alias mi-recent='mi list --limit 10 --sort-by date --desc'
```

## 📦 安装方式

### 方式 1：开发模式

```bash
pip install -e .
```

- ✅ 代码修改立即生效
- ✅ 适合开发

### 方式 2：用户模式

```bash
pip install --user .
```

- ✅ 不需要 sudo
- ✅ 适合个人使用

### 方式 3：Homebrew

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

- ✅ 系统集成
- ✅ 易于分发

## 🐛 故障排除

### 命令找不到

```bash
# 添加到 PATH
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# 重新加载 shell
source ~/.zshrc
```

### 重新安装

```bash
# 卸载
pip uninstall memoryindex

# 重新安装
pip install -e .
```

### 查看日志

```bash
# 详细输出
mi search "test" -v

# 调试模式
MI_DEBUG=1 mi search "test"
```

## 📚 更多文档

- 📖 [完整安装指南](INSTALL.md)
- 📦 [打包和发布](PACKAGING.md)
- 🎯 [使用指南](USAGE.md)
- 🍺 [Homebrew Formula](Formula.rb)
- 💡 [Shell 别名](alias.sh)

## 🎯 工作流示例

### 处理新视频

```bash
# 1. 下载视频（如果需要）
# 手动下载或使用其他工具

# 2. 处理视频
mi-process video.mp4

# 3. 搜索内容
mi search "关键词"
```

### 批量处理

```bash
# 处理目录中所有视频
for video in videos/*.mp4; do
    mi-process "$video"
done

# 或使用别名（如果已加载）
mi-batch videos/
```

### 导出搜索结果

```bash
# 搜索并保存结果
mi search "AI" > results.txt

# 或使用别名
mi-export "AI" results.txt
```

## 💡 Pro Tips

1. **使用简写**: `mi` 比 `memoryindex` 更快
2. **配置别名**: 加载 `alias.sh` 获得更多便捷命令
3. **开发模式**: 使用 `pip install -e .` 可以边开发边测试
4. **批量处理**: 晚上睡觉前运行批量任务
5. **标签管理**: 使用 `mi list-tags` 发现内容

## 🔗 快速链接

```bash
# 检查状态
which mi                                # 命令位置
mi --version                            # 版本信息
mi --help                               # 帮助信息

# 项目位置
cd ~/Documents/GitHub/knowledge         # 进入项目目录

# 更新代码（开发模式自动生效）
git pull origin main
```

---

**需要帮助？** 查看 [README.md](README.md) 或运行 `mi --help` 🚀
