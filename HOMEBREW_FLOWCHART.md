# 🗺️ Homebrew 发布流程图

```
┌─────────────────────────────────────────────────────────────────┐
│  第一步：准备代码和标签                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. cd /Users/catherina/Documents/GitHub/knowledge              │
│  2. git add .                                                    │
│  3. git commit -m "Release v1.0.0"                              │
│  4. git push origin main                                         │
│  5. git tag -a v1.0.0 -m "Release v1.0.0"                       │
│  6. git push origin v1.0.0                                       │
│                                                                  │
│  ✅ 完成标志：git tag -l 能看到 v1.0.0                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第二步：创建 GitHub Release                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 打开：https://github.com/Catherina0/MemoryIndex/releases/new│
│  2. 选择标签：v1.0.0                                             │
│  3. 填写标题和描述                                               │
│  4. 点击 "Publish release"                                       │
│                                                                  │
│  ✅ 完成标志：能在 Releases 页面看到 v1.0.0                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第三步：下载源码并计算 SHA256                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. mkdir -p ~/homebrew-release                                  │
│  2. cd ~/homebrew-release                                        │
│  3. curl -L -o memoryindex-1.0.0.tar.gz \                       │
│       https://github.com/Catherina0/MemoryIndex/archive/\       │
│       refs/tags/v1.0.0.tar.gz                                    │
│  4. shasum -a 256 memoryindex-1.0.0.tar.gz                      │
│                                                                  │
│  ⚠️  重要：复制输出的 SHA256 值！                                │
│  ✅ 完成标志：得到一个 64 位的十六进制字符串                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第四步：创建 Homebrew Tap 仓库                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 访问：https://github.com/new                                 │
│  2. 仓库名：homebrew-memoryindex                                 │
│  3. 类型：Public                                                 │
│  4. 勾选 "Initialize with README"                                │
│  5. 点击 "Create repository"                                     │
│                                                                  │
│  然后在本地：                                                     │
│  6. cd ~/Documents/GitHub                                        │
│  7. git clone https://github.com/Catherina0/\                   │
│       homebrew-memoryindex.git                                   │
│  8. cd homebrew-memoryindex                                      │
│  9. mkdir -p Formula                                             │
│                                                                  │
│  ✅ 完成标志：有 homebrew-memoryindex/Formula/ 目录             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第五步：创建并编辑 Formula                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. cp /Users/catherina/Documents/GitHub/knowledge/Formula.rb \ │
│        ~/Documents/GitHub/homebrew-memoryindex/Formula/\        │
│        memoryindex.rb                                            │
│                                                                  │
│  2. nano Formula/memoryindex.rb                                  │
│     找到这行：                                                    │
│     sha256 "REPLACE_WITH_ACTUAL_SHA256"                         │
│     替换成第三步计算的 SHA256 值                                  │
│                                                                  │
│  3. 保存并退出（Ctrl+O, Enter, Ctrl+X）                         │
│                                                                  │
│  ✅ 完成标志：Formula 文件存在且 SHA256 已替换                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第六步：提交 Formula 到 GitHub                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. cd ~/Documents/GitHub/homebrew-memoryindex                   │
│  2. git add Formula/memoryindex.rb                              │
│  3. git commit -m "Add memoryindex formula v1.0.0"              │
│  4. git push origin main                                         │
│                                                                  │
│  可选：更新 README                                                │
│  5. nano README.md （添加安装说明）                              │
│  6. git add README.md                                            │
│  7. git commit -m "Update README"                                │
│  8. git push origin main                                         │
│                                                                  │
│  ✅ 完成标志：GitHub 仓库中能看到 Formula/memoryindex.rb        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  第七步：测试安装                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. brew tap Catherina0/memoryindex                             │
│  2. brew info memoryindex                                        │
│  3. brew audit --strict memoryindex                             │
│  4. brew install memoryindex                                     │
│                                                                  │
│  测试命令：                                                       │
│  5. which memidx                                                 │
│  6. memidx --help                                                │
│  7. memidx list --limit 5                                        │
│                                                                  │
│  ✅ 完成标志：所有命令都能正常工作                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  🎉 完成！                                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  现在用户可以这样安装：                                          │
│                                                                  │
│    brew tap Catherina0/memoryindex                              │
│    brew install memoryindex                                      │
│                                                                  │
│  然后使用：                                                       │
│                                                                  │
│    memidx search "关键词"                                        │
│    memidx list                                                   │
│    memidx-process video.mp4                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 时间估算

| 步骤 | 预计时间 | 难度 |
|------|----------|------|
| 第一步：代码和标签 | 2 分钟 | ⭐ 简单 |
| 第二步：GitHub Release | 3 分钟 | ⭐ 简单 |
| 第三步：计算 SHA256 | 2 分钟 | ⭐ 简单 |
| 第四步：创建 Tap 仓库 | 3 分钟 | ⭐ 简单 |
| 第五步：编辑 Formula | 2 分钟 | ⭐⭐ 需要注意 |
| 第六步：提交 Formula | 2 分钟 | ⭐ 简单 |
| 第七步：测试安装 | 5 分钟 | ⭐⭐ 可能遇到问题 |
| **总计** | **约 20 分钟** | |

---

## 🎯 关键检查点

每一步完成后的验证：

### ✅ 第一步检查
```bash
git tag -l | grep v1.0.0
# 应该看到：v1.0.0
```

### ✅ 第二步检查
访问：https://github.com/Catherina0/MemoryIndex/releases
应该看到 v1.0.0 Release

### ✅ 第三步检查
```bash
ls -lh ~/homebrew-release/memoryindex-1.0.0.tar.gz
# 文件大小应该在几百 KB 到几 MB
```

### ✅ 第四步检查
```bash
ls -la ~/Documents/GitHub/homebrew-memoryindex/Formula/
# 应该看到目录存在
```

### ✅ 第五步检查
```bash
grep "sha256" ~/Documents/GitHub/homebrew-memoryindex/Formula/memoryindex.rb
# 应该看到实际的 SHA256 值，不是 "REPLACE_WITH_ACTUAL_SHA256"
```

### ✅ 第六步检查
```bash
cd ~/Documents/GitHub/homebrew-memoryindex
git log --oneline -1
# 应该看到最新的 commit
```

### ✅ 第七步检查
```bash
which memidx
memidx --version 2>/dev/null || memidx --help 2>&1 | head -3
# 应该能看到命令帮助信息
```

---

## 🚨 常见错误和解决

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| `sha256 mismatch` | SHA256 不匹配 | 重新下载 tar.gz 并计算 |
| `Formula not found` | Tap 未添加 | `brew tap Catherina0/memoryindex` |
| `command not found` | 安装失败 | 检查 Formula 语法 |
| `Permission denied` | 权限问题 | 不要使用 sudo |

---

## 📝 快速参考

### 一行命令查看流程
```bash
cat HOMEBREW_FLOWCHART.md
```

### 执行所有命令
```bash
# 查看命令列表
./homebrew-commands.sh
```

### 详细指南
```bash
# 打开详细指南
cat HOMEBREW_GUIDE.md | less
```

---

**准备好了吗？从第一步开始！** 🚀
