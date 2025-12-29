# 🎉 MemoryIndex 现在可以全系统使用了！

## 快速开始

### 一键安装（推荐）

```bash
# 在项目目录运行
./install.sh
```

安装后，你可以在**任何目录**使用以下命令：

```bash
# 搜索视频内容（简写）
mi search "关键词"

# 列出所有视频
mi list

# 查看主题
mi topics

# 处理新视频
mi-process video.mp4

# 查看帮助
mi --help
```

## 三种安装方式

### 方式 1：开发模式（推荐用于开发）

```bash
pip install -e .
```

- ✅ 代码修改立即生效
- ✅ 适合开发和调试

### 方式 2：用户模式（推荐个人使用）

```bash
pip install --user .
```

- ✅ 不需要管理员权限
- ✅ 不影响系统 Python

### 方式 3：Homebrew（推荐分发）

**创建你自己的 Homebrew Tap：**

```bash
# 详细步骤见 PACKAGING.md
brew tap Catherina0/memoryindex
brew install memoryindex
```

## 可用命令

安装后，以下命令全局可用：

| 命令 | 说明 | 示例 |
|------|------|------|
| `mi` 或 `memoryindex` | 主命令（搜索） | `mi search "AI"` |
| `mi search` | 全文搜索 | `mi search "机器学习" --field transcript` |
| `mi list` | 列出所有视频 | `mi list --limit 20` |
| `mi topics` | 查看主题 | `mi topics "神经网络"` |
| `mi tags` | 按标签搜索 | `mi tags --tags 教育 科技` |
| `mi show` | 查看视频详情 | `mi show 1` |
| `mi-process` | 处理视频 | `mi-process video.mp4` |

## 验证安装

```bash
# 检查命令位置
which mi

# 查看版本
mi --version

# 测试搜索
mi search "测试"
```

## 卸载

```bash
./uninstall.sh

# 或者
pip uninstall memoryindex
```

## 更多信息

- 📦 **打包指南**: 查看 [PACKAGING.md](PACKAGING.md)
- 📖 **安装指南**: 查看 [INSTALL.md](INSTALL.md)
- 🍺 **Homebrew Formula**: 查看 [Formula.rb](Formula.rb)

## 常见问题

### 命令找不到？

```bash
# 添加到 PATH（加入 ~/.zshrc）
export PATH="$PATH:$(python3 -m site --user-base)/bin"
source ~/.zshrc
```

### 更新代码后如何重新加载？

如果使用开发模式（`pip install -e .`），代码修改会立即生效，无需重新安装！

---

**现在就试试吧！** 🚀

```bash
./install.sh
mi search "你感兴趣的内容"
```
