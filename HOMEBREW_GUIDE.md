# 📦 Homebrew 发布完整指南

## 🎯 发布 MemoryIndex 到 Homebrew 的完整流程

### 准备工作清单

- [x] 项目已打包（setup.py, pyproject.toml 已配置）
- [x] 命令别名已设置为 `memidx`
- [ ] 创建 GitHub Release
- [ ] 创建 Homebrew Tap
- [ ] 编写 Formula
- [ ] 测试安装
- [ ] 发布

---

## 第一步：准备发布版本

### 1.1 确保代码已提交

```bash
cd /Users/catherina/Documents/GitHub/knowledge

# 查看状态
git status

# 提交所有更改
git add .
git commit -m "Release v1.0.0: Add Homebrew support with memidx command"

# 推送到 GitHub
git push origin main
```

### 1.2 创建 Git 标签

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0 - First stable release"

# 推送标签到 GitHub
git push origin v1.0.0
```

### 1.3 验证标签

```bash
# 查看所有标签
git tag -l

# 查看标签详情
git show v1.0.0
```

---

## 第二步：创建 GitHub Release

### 2.1 访问 GitHub Release 页面

在浏览器中打开：
```
https://github.com/Catherina0/MemoryIndex/releases/new
```

### 2.2 填写 Release 信息

**Tag version:** `v1.0.0`

**Release title:** `v1.0.0 - MemoryIndex First Stable Release`

**Description:**
```markdown
## 🎉 MemoryIndex v1.0.0

MemoryIndex 首个稳定版本发布！一个智能视频知识库系统，支持视频下载、OCR识别、全文搜索。

### ✨ 主要功能

- 🎬 **视频处理**：自动提取音频、OCR识别、语音转文字
- 🔍 **智能搜索**：支持中文分词的全文检索
- 📥 **多平台下载**：YouTube, Bilibili, 小红书等
- 💾 **数据库管理**：SQLite + Whoosh 全文索引
- 🖥️ **命令行工具**：强大的 CLI 界面

### 📦 安装方式

#### Homebrew（推荐）
```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

#### pip 安装
```bash
pip install memoryindex
```

#### 从源码安装
```bash
git clone https://github.com/Catherina0/MemoryIndex.git
cd MemoryIndex
./install.sh
```

### 🚀 快速开始

```bash
# 搜索视频内容
memidx search "关键词"

# 处理视频
memidx-process video.mp4

# 查看帮助
memidx --help
```

### 📚 文档

- [快速参考](https://github.com/Catherina0/MemoryIndex/blob/main/QUICKREF.md)
- [使用指南](https://github.com/Catherina0/MemoryIndex/blob/main/USAGE.md)
- [安装指南](https://github.com/Catherina0/MemoryIndex/blob/main/INSTALL.md)

### 🙏 反馈

如有问题或建议，请提交 [Issue](https://github.com/Catherina0/MemoryIndex/issues)。
```

### 2.3 发布 Release

点击 **"Publish release"** 按钮

---

## 第三步：下载并计算 SHA256

### 3.1 下载源码包

```bash
# 创建临时目录
mkdir -p ~/homebrew-release
cd ~/homebrew-release

# 下载 Release 源码包
curl -L -o memoryindex-1.0.0.tar.gz \
  https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz
```

### 3.2 计算 SHA256

```bash
# 计算 SHA256 哈希值
shasum -a 256 memoryindex-1.0.0.tar.gz

# 输出示例：
# 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef  memoryindex-1.0.0.tar.gz
```

**⚠️ 重要：复制这个 SHA256 值，后面会用到！**

---

## 第四步：创建 Homebrew Tap

### 4.1 创建新的 GitHub 仓库

1. 访问：https://github.com/new
2. 仓库名称：`homebrew-memoryindex`
3. 描述：`Homebrew tap for MemoryIndex`
4. 设为 Public
5. 初始化 README
6. 点击 **Create repository**

### 4.2 克隆 Tap 仓库

```bash
cd ~/Documents/GitHub

# 克隆你刚创建的仓库
git clone https://github.com/Catherina0/homebrew-memoryindex.git
cd homebrew-memoryindex
```

### 4.3 创建 Formula 目录

```bash
# 创建 Formula 目录
mkdir -p Formula
```

---

## 第五步：编写 Homebrew Formula

### 5.1 创建 Formula 文件

```bash
cd ~/Documents/GitHub/homebrew-memoryindex
nano Formula/memoryindex.rb
```

### 5.2 Formula 内容

复制以下内容，**记得替换 SHA256 值**：

```ruby
class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "智能视频知识库系统 - 视频下载、OCR识别、全文搜索"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "替换成你在第三步计算的SHA256值"
  license "MIT"
  head "https://github.com/Catherina0/MemoryIndex.git", branch: "main"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  # Python 依赖资源
  resource "paddlepaddle" do
    url "https://files.pythonhosted.org/packages/source/p/paddlepaddle/paddlepaddle-3.2.2.tar.gz"
    sha256 "8f5c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c"
  end

  resource "paddleocr" do
    url "https://files.pythonhosted.org/packages/source/p/paddleocr/paddleocr-2.7.0.tar.gz"
    sha256 "8f5c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c7e8c5e8c"
  end

  # 其他依赖...（实际使用时可以简化）

  def install
    # 创建虚拟环境并安装
    virtualenv_install_with_resources
    
    # 创建配置目录
    (etc/"memoryindex").mkpath
  end

  def post_install
    # 创建数据目录
    (var/"memoryindex").mkpath
    (var/"memoryindex/storage").mkpath
    (var/"memoryindex/output").mkpath
    (var/"memoryindex/videos").mkpath
  end

  def caveats
    <<~EOS
      MemoryIndex 已安装！

      快速开始：
        memidx search "关键词"
        memidx list
        memidx-process video.mp4

      数据目录：
        #{var}/memoryindex/

      查看帮助：
        memidx --help

      更多文档：
        https://github.com/Catherina0/MemoryIndex
    EOS
  end

  test do
    system bin/"memidx", "--help"
    system bin/"memidx", "list", "--limit", "1"
  end
end
```

### 5.3 简化版 Formula（推荐）

如果依赖管理太复杂，使用简化版：

```ruby
class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "智能视频知识库系统"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "在这里替换你的SHA256值"
  license "MIT"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      MemoryIndex 已安装！

      快速开始：
        memidx search "关键词"
        memidx-process video.mp4

      文档：
        https://github.com/Catherina0/MemoryIndex
    EOS
  end

  test do
    system bin/"memidx", "--help"
  end
end
```

---

## 第六步：提交并发布 Formula

### 6.1 提交 Formula

```bash
cd ~/Documents/GitHub/homebrew-memoryindex

# 添加文件
git add Formula/memoryindex.rb

# 提交
git commit -m "Add memoryindex formula v1.0.0"

# 推送到 GitHub
git push origin main
```

### 6.2 更新 README

编辑 `README.md`：

```markdown
# Homebrew Tap for MemoryIndex

智能视频知识库系统的 Homebrew Tap

## 安装

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

## 使用

```bash
# 搜索视频内容
memidx search "关键词"

# 列出所有视频
memidx list

# 处理视频
memidx-process video.mp4

# 查看帮助
memidx --help
```

## 更多信息

- 项目主页：https://github.com/Catherina0/MemoryIndex
- 文档：https://github.com/Catherina0/MemoryIndex/blob/main/README.md
- 问题反馈：https://github.com/Catherina0/MemoryIndex/issues
```

提交 README：

```bash
git add README.md
git commit -m "Update README with installation instructions"
git push origin main
```

---

## 第七步：测试安装

### 7.1 添加 Tap

```bash
# 添加你的 Tap
brew tap Catherina0/memoryindex
```

### 7.2 检查 Formula

```bash
# 检查 Formula 语法
brew audit --strict memoryindex

# 显示 Formula 信息
brew info memoryindex
```

### 7.3 安装测试

```bash
# 从源码构建并安装
brew install --build-from-source Catherina0/memoryindex/memoryindex

# 或者直接安装
brew install memoryindex
```

### 7.4 验证安装

```bash
# 检查命令是否可用
which memidx
memidx --help

# 测试功能
memidx list --limit 5
```

### 7.5 测试卸载

```bash
# 测试卸载
brew uninstall memoryindex

# 重新安装
brew install memoryindex
```

---

## 第八步：完成发布

### 8.1 更新主项目文档

回到主项目更新 README：

```bash
cd /Users/catherina/Documents/GitHub/knowledge

# 编辑 README.md，添加 Homebrew 安装说明
```

### 8.2 创建公告

可以在主项目创建一个 Issue 或 Discussion 公告：

```markdown
## 🎉 MemoryIndex 现已支持 Homebrew 安装！

MemoryIndex v1.0.0 已发布，现在可以通过 Homebrew 一键安装：

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

安装后立即使用：
```bash
memidx search "关键词"
```

欢迎试用并反馈！
```

---

## 💡 使用指南

### 用户安装（发布后）

其他人可以这样安装：

```bash
# 1. 添加 Tap
brew tap Catherina0/memoryindex

# 2. 安装
brew install memoryindex

# 3. 使用
memidx search "测试"
```

### 更新版本

当你发布新版本时：

```bash
# 1. 创建新标签
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# 2. 创建 GitHub Release

# 3. 计算新的 SHA256
curl -L -o memoryindex-1.1.0.tar.gz \
  https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.1.0.tar.gz
shasum -a 256 memoryindex-1.1.0.tar.gz

# 4. 更新 Formula
cd ~/Documents/GitHub/homebrew-memoryindex
nano Formula/memoryindex.rb
# 更新 url 和 sha256

# 5. 提交
git add Formula/memoryindex.rb
git commit -m "Update memoryindex to v1.1.0"
git push origin main
```

用户升级：

```bash
brew update
brew upgrade memoryindex
```

---

## 🔍 故障排除

### Formula 语法错误

```bash
# 检查语法
brew audit --strict memoryindex

# 查看详细错误
brew install --verbose --debug memoryindex
```

### 依赖问题

```bash
# 检查依赖
brew deps memoryindex

# 重新安装依赖
brew reinstall python@3.11
```

### 清理缓存

```bash
# 清理 Homebrew 缓存
brew cleanup

# 删除下载的文件
rm -rf ~/Library/Caches/Homebrew/downloads/*memoryindex*
```

---

## 📚 参考资源

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula 指南](https://docs.brew.sh/Python-for-Formula-Authors)
- [Tap 创建指南](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)

---

## ✅ 完成清单

发布完成后检查：

- [ ] GitHub Release 已创建
- [ ] homebrew-memoryindex 仓库已创建
- [ ] Formula 已提交
- [ ] `brew tap` 成功
- [ ] `brew install` 成功
- [ ] `memidx --help` 正常工作
- [ ] README 已更新
- [ ] 文档已更新

---

**🎉 恭喜！你的项目现在可以通过 Homebrew 安装了！**
