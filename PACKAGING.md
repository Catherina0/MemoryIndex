# MemoryIndex 打包和发布指南

## 🎯 三种使用方式

### 方式 1：开发模式安装（推荐用于开发）

**最简单快速的方式：**

```bash
# 自动安装脚本
./install.sh

# 或者手动安装
pip install -e .
```

安装后立即可用：

```bash
mi search "关键词"          # 搜索
mi list                     # 列表
mi-process video.mp4        # 处理视频
```

**优点：**
- ✅ 代码修改立即生效
- ✅ 可以边开发边使用
- ✅ 不需要重新安装

---

### 方式 2：用户级安装（推荐用于个人使用）

```bash
# 构建并安装
pip install --user .

# 或使用安装脚本选择选项 2
./install.sh
```

**优点：**
- ✅ 不需要管理员权限
- ✅ 不影响系统 Python
- ✅ 多个 Python 环境隔离

---

### 方式 3：Homebrew 安装（推荐用于分发）

**创建你自己的 Homebrew Tap：**

#### 步骤 1：准备发布

```bash
# 1. 打标签
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 2. 在 GitHub 创建 Release
# 访问：https://github.com/Catherina0/MemoryIndex/releases/new
# - 选择标签 v1.0.0
# - 填写发布说明
# - 发布
```

#### 步骤 2：创建 Tap

```bash
# 创建你的 Homebrew Tap
brew tap-new Catherina0/memoryindex

# 进入 Tap 目录
cd $(brew --repository)/Library/Taps/catherina0/homebrew-memoryindex

# 创建 Formula 目录
mkdir -p Formula

# 复制 Formula 文件
cp /Users/catherina/Documents/GitHub/knowledge/Formula.rb Formula/memoryindex.rb
```

#### 步骤 3：计算 SHA256

```bash
# 下载并计算 SHA256
curl -L https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz -o memoryindex-1.0.0.tar.gz
shasum -a 256 memoryindex-1.0.0.tar.gz

# 复制输出的 SHA256，更新 Formula 文件
```

#### 步骤 4：编辑并测试 Formula

```bash
# 编辑 Formula（替换 SHA256）
nano Formula/memoryindex.rb

# 测试安装
brew install --build-from-source catherina0/memoryindex/memoryindex

# 测试命令
brew test memoryindex

# 审核 Formula
brew audit --strict memoryindex
```

#### 步骤 5：发布 Tap

```bash
cd $(brew --repository)/Library/Taps/catherina0/homebrew-memoryindex
git add Formula/memoryindex.rb
git commit -m "Add memoryindex v1.0.0"
git push origin main
```

#### 步骤 6：用户安装

**现在其他人可以这样安装：**

```bash
# 添加你的 Tap
brew tap Catherina0/memoryindex

# 安装
brew install memoryindex

# 使用
mi search "测试"
```

---

## 📦 构建分发包

### PyPI 发布（Python Package Index）

```bash
# 1. 安装构建工具
pip install build twine

# 2. 构建包
python -m build

# 3. 检查包
twine check dist/*

# 4. 上传到 TestPyPI（测试）
twine upload --repository testpypi dist/*

# 5. 测试安装
pip install --index-url https://test.pypi.org/simple/ memoryindex

# 6. 上传到正式 PyPI
twine upload dist/*
```

**然后用户可以直接：**

```bash
pip install memoryindex
```

---

## 🚀 快速验证安装

### 检查安装

```bash
# 检查命令是否可用
which mi
which memoryindex

# 查看版本
mi --version

# 查看帮助
mi --help
```

### 测试功能

```bash
# 1. 搜索测试
mi search "测试"

# 2. 列出视频
mi list

# 3. 查看主题
mi topics

# 4. 处理视频（如果有测试视频）
mi-process test.mp4
```

---

## 🔧 常见问题

### 问题 1：命令找不到

```bash
# 方案 A：检查 PATH
echo $PATH | grep -o "[^:]*bin"

# 方案 B：找到安装位置
python3 -c "import site; print(site.USER_BASE + '/bin')"

# 方案 C：添加到 PATH（加入 ~/.zshrc）
export PATH="$PATH:$(python3 -m site --user-base)/bin"
source ~/.zshrc
```

### 问题 2：权限问题

```bash
# 使用 --user 标志
pip install --user .
```

### 问题 3：虚拟环境冲突

```bash
# 先退出虚拟环境
deactivate

# 再安装
pip install .
```

### 问题 4：依赖冲突

```bash
# 创建干净的虚拟环境
python3 -m venv ~/.memoryindex-venv
source ~/.memoryindex-venv/bin/activate
pip install .

# 添加别名到 ~/.zshrc
alias mi='~/.memoryindex-venv/bin/mi'
```

---

## 📊 不同方式对比

| 方式 | 优点 | 缺点 | 适合场景 |
|------|------|------|----------|
| **开发模式** | 即改即用，方便调试 | 依赖项目目录 | 开发者 |
| **用户安装** | 隔离干净，易卸载 | 需要重新安装更新 | 个人使用 |
| **Homebrew** | 系统集成，易更新 | 配置复杂 | 分发给他人 |
| **PyPI** | 最易分发 | 需要账号认证 | 公开发布 |

---

## 🎯 推荐流程

1. **开发阶段**：使用 `pip install -e .`
2. **测试阶段**：使用 `./install.sh` 测试安装流程
3. **个人使用**：使用 `pip install --user .`
4. **分享给朋友**：创建 Homebrew Tap
5. **公开发布**：发布到 PyPI

---

## 🎉 下一步

选择一种方式安装后，你就可以在任何地方使用 `mi` 命令了！

```bash
# 立即尝试
mi --help
```

祝你使用愉快！ 🚀
