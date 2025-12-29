#!/usr/bin/env python3
"""
MemoryIndex - 智能视频知识库系统
从视频下载到文本搜索的完整解决方案
"""
from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取依赖
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="memoryindex",
    version="1.0.0",
    description="智能视频知识库系统 - 视频下载、OCR识别、全文搜索一体化解决方案",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Catherina",
    author_email="",
    url="https://github.com/Catherina0/MemoryIndex",
    packages=find_packages(exclude=["tests", "docs", "scripts"]),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            # 主命令
            "memoryindex=cli.search_cli:main",
            "memidx=cli.search_cli:main",
            
            # 视频处理命令
            "memidx-process=core.process_video:main",
            "memidx-download=core.video_downloader:main",
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
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="video ocr search knowledge-base paddleocr",
)
