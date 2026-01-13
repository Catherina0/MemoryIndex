#!/usr/bin/env python3
"""
MemoryIndex - 智能视频知识库系统
从视频下载到文本搜索的完整解决方案

注意：此 setup.py 作为 pyproject.toml 的备用方案
推荐使用 pyproject.toml 进行构建
"""
from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 基础依赖
install_requires = [
    "numpy",
    "groq",
    "python-dotenv",
    "yt-dlp",
    "tabulate>=0.9.0",
    "Whoosh>=2.7.4",
    "jieba>=0.42.1",
]

# 可选依赖
extras_require = {
    "paddle": [
        "paddlepaddle>=3.0.0",
        "paddleocr>=2.7.0",
        "opencv-python",
    ],
    "archiver": [
        "crawl4ai>=0.2.0",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "html2text>=2024.0.0",
        "DrissionPage>=4.0.0",
    ],
}
extras_require["full"] = (
    extras_require["paddle"] 
    + extras_require["archiver"] 
    + [
        "browser-cookie3>=0.19.0",
        "httpx>=0.27.0",
        "aiosqlite>=0.20.0",
        "aiofiles>=24.0.0",
    ]
)

setup(
    name="memoryindex",
    version="1.0.4",
    description="智能视频知识库系统 - 视频下载、OCR识别、全文搜索一体化解决方案",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Catherina",
    author_email="",
    url="https://github.com/Catherina0/MemoryIndex",
    packages=find_packages(exclude=["tests", "docs", "scripts", "archived", "browser_data", "chromium"]),
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            # 主命令：全文搜索
            "memoryindex=cli.search_cli:main",  # 主命令：memoryindex search "关键词"
            "memidx=cli.search_cli:main",       # 简写：memidx search "关键词"
            
            # 视频处理：下载、转写、OCR、AI摘要
            "memidx-process=core.process_video:main",    # 处理本地视频
            "memidx-download=core.video_downloader:main", # 下载在线视频
            
            # 网页归档：知乎、小红书、B站等网页转 Markdown
            "memidx-archive=cli.archive_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Text Processing :: Indexing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    keywords="video ocr search knowledge-base paddleocr web-archiver",
)
