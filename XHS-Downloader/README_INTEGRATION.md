# XHS-Downloader 集成说明

## ⚠️ 重要提示

此目录包含 [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) 作为子模块。

**敏感文件已被 .gitignore 排除**：
- `Volume/settings.json` - 包含 Cookie 的配置文件
- `Volume/*.db` - 数据库文件
- `Volume/Download/` - 下载的文件

## 配置方法

### 快速配置

在项目根目录运行：

```bash
make config-xhs-cookie
```

### 手动配置

1. 确保 `Volume/settings.json` 存在
2. 如果不存在，复制示例文件：
   ```bash
   cp Volume/settings.json.example Volume/settings.json
   ```
3. 编辑 `Volume/settings.json`，添加你的 Cookie

## 获取 Cookie

详细教程：[docs/XHS_COOKIE_SETUP.md](../docs/XHS_COOKIE_SETUP.md)

## 文档

- [配置完成说明](../docs/XHS_CONFIG_DONE.md)
- [小红书下载指南](../docs/XIAOHONGSHU_DOWNLOAD.md)

## Git 安全

- ✅ `settings.json` 已被忽略（包含敏感 Cookie）
- ✅ `*.db` 文件已被忽略
- ✅ 下载文件夹已被忽略
- ✅ 提供 `settings.json.example` 作为模板

## 更新 XHS-Downloader

```bash
cd XHS-Downloader
git pull origin master
```

## 卸载

删除此目录即可，不会影响主项目。
