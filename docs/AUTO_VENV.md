# 🎉 自动虚拟环境功能说明

## 新特性

从现在开始，你不再需要手动创建和管理虚拟环境！

**首次运行任何 `make` 命令时，系统会自动：**

1. ✅ 创建虚拟环境 (`.venv`)
2. ✅ 安装所有依赖包（从 `requirements.txt`）
3. ✅ 运行环境自检
4. ✅ 创建配置文件模板（`.env`）

## 使用方法

### 首次使用

直接运行你想要的命令：

```bash
# 处理视频（首次运行会自动配置环境）
make run VIDEO=/path/to/video.mp4

# 或者运行环境测试
make test

# 或者查看帮助
make help
```

### 后续使用

环境已配置好，直接使用即可：

```bash
make run VIDEO=/path/to/another_video.mp4
make ocr VIDEO=/path/to/video_with_text.mp4
```

## 工作原理

Makefile 中新增了 `ensure-venv` 目标，它会：

1. 检查 `.venv` 目录是否存在
2. 如果不存在，自动执行完整的环境初始化流程
3. 所有主要命令（`run`, `ocr`, `test`, `install`, `check`）都依赖这个目标

## 虚拟环境信息

- **位置**: `.venv/` （项目根目录下）
- **Python 路径**: `.venv/bin/python`
- **pip 路径**: `.venv/bin/pip`

所有包都安装在虚拟环境中，不会污染系统 Python。

## 常见命令

```bash
# 查看帮助
make help

# 处理视频（快速模式 - 仅音频）
make run VIDEO=/path/to/video.mp4

# 处理视频（完整模式 - 音频 + OCR）
make ocr VIDEO=/path/to/video.mp4

# 运行环境自检
make test

# 检查环境配置
make check

# 重新安装依赖
make install

# 手动重新初始化环境
make setup

# 清理输出文件
make clean

# 完全清理（包括虚拟环境）
make clean-all
```

## 故障排除

### 虚拟环境损坏

```bash
# 删除虚拟环境
make clean-all

# 重新运行任何命令（会自动重建）
make test
```

### 依赖包问题

```bash
# 重新安装依赖
make install
```

### 权限问题

如果遇到权限问题，确保项目目录有写入权限：

```bash
# 检查目录权限
ls -la .venv

# 如果需要，删除并重建
rm -rf .venv
make test
```

## 优势

✅ **零配置启动** - 新用户克隆项目后直接运行即可

✅ **环境隔离** - 所有依赖在项目目录下，不影响系统 Python

✅ **自动化** - 无需记忆复杂的初始化步骤

✅ **一致性** - 所有开发者使用相同的环境配置

✅ **易于重置** - 一条命令即可完全清理和重建

## 与旧版本的区别

**旧版本** (手动管理):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python test_env.py
```

**新版本** (自动化):
```bash
make run VIDEO=test.mp4
# 一切都自动完成！
```

---

💡 **提示**: 第一次运行会稍微慢一些（需要安装依赖），但后续运行会非常快！
