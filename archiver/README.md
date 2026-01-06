# 网页归档模块 (Web Archiver)

基于 `agents.md` 规范实现的通用网页归档系统，支持精准提取正文并保存为 Markdown 格式。

## 📦 模块结构

```
archiver/
├── __init__.py                    # 模块入口
├── example.py                     # 使用示例
├── core/                          # 核心功能
│   ├── __init__.py
│   ├── crawler.py                 # 通用爬虫（基于Crawl4AI）
│   └── markdown_converter.py      # HTML→Markdown转换器
├── platforms/                     # 平台适配器
│   ├── __init__.py
│   ├── base.py                    # 适配器基类
│   ├── zhihu.py                   # 知乎
│   ├── xiaohongshu.py             # 小红书
│   ├── bilibili.py                # B站
│   ├── reddit.py                  # Reddit
│   └── wordpress.py               # 通用/WordPress
└── utils/                         # 工具模块
    ├── __init__.py
    ├── url_parser.py              # URL解析与平台检测
    └── cookie_manager.py          # Cookie管理

cli/
└── archive_cli.py                 # 命令行接口

tests/
└── test_archiver.py               # 测试用例

docs/
└── ARCHIVER_GUIDE.md              # 使用指南
```

## ✨ 核心特性

- ✅ **智能平台识别**: 自动检测知乎、小红书、B站、Reddit等
- ✅ **精准内容提取**: 基于CSS选择器精确定位正文，排除评论/广告
- ✅ **Markdown转换**: 保留图片链接，生成标准Markdown格式
- ✅ **反爬虫处理**: 支持浏览器Cookie注入，应对登录限制
- ✅ **批量归档**: 异步并发，高效处理多个URL
- ✅ **模块化设计**: 独立的平台适配器，易于扩展

## 🚀 快速开始

### 1. 安装依赖

```bash
make install
```

### 2. 使用命令

```bash
# 归档单个网页
make archive URL=https://www.zhihu.com/question/123456/answer/789012

# 批量归档
make archive-batch FILE=urls.txt

# 检测平台
make archive-detect URL=https://www.zhihu.com/question/123456

# 运行测试
make test-archiver
```

### 3. Python API

```python
import asyncio
from archiver import UniversalArchiver, detect_platform

async def main():
    archiver = UniversalArchiver(output_dir="archived")
    result = await archiver.archive("https://example.com")
    print(f"归档成功: {result['output_path']}")

asyncio.run(main())
```

## 📚 支持的平台

| 平台 | 自动识别 | 正文提取 | 评论过滤 | 需要登录 |
|------|---------|---------|---------|---------|
| 知乎 | ✅ | ✅ | ✅ | ❌ |
| 小红书 | ✅ | ✅ | ✅ | ✅ |
| B站 | ✅ | ✅ | ✅ | ❌ |
| Reddit | ✅ | ✅ | ✅ | ❌ |
| 通用 | ✅ | ✅ | ✅ | ❌ |

## 📖 详细文档

查看完整使用指南: [docs/ARCHIVER_GUIDE.md](../docs/ARCHIVER_GUIDE.md)

## 🧪 测试

```bash
# 运行所有测试
python tests/test_archiver.py

# 或使用 make
make test-archiver
```

## 🛠️ 技术栈

- **Crawl4AI**: 智能爬虫框架
- **Playwright**: 浏览器自动化
- **BeautifulSoup4**: HTML解析
- **html2text**: HTML→Markdown转换
- **browser-cookie3**: 浏览器Cookie提取

## 📝 配置

### 平台适配器配置

每个平台适配器定义了：

```python
PlatformConfig(
    name="zhihu",                              # 平台名称
    content_selector=".RichContent-inner",     # 正文CSS选择器
    exclude_selector=".Comments-container",    # 排除区域
    wait_for_selector=".RichContent-inner",    # 等待加载
    requires_login=False,                      # 是否需要登录
    user_agent="..."                           # 自定义UA
)
```

### 添加新平台

1. 在 `archiver/platforms/` 创建新文件
2. 继承 `PlatformAdapter` 基类
3. 实现 `get_default_config()` 方法
4. 在 `utils/url_parser.py` 添加平台检测逻辑

## 🔍 故障排查

### 常见问题

**Q: 提示 Crawl4AI 未安装**
```bash
pip install crawl4ai
playwright install chromium
```

**Q: 需要登录的网站无法访问**
```bash
python -m cli.archive_cli URL --browser chrome
```

**Q: 内容提取不完整**
```bash
python -m cli.archive_cli URL --show-browser -v
```

## 📄 许可证

遵循 MemoryIndex 项目许可证

---

**版本**: 0.1.0  
**更新**: 2026-01-07
