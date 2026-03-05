# Makefile for Video Report Pipeline
# 使用方法：make <target> Path=/path/to/video.mp4

.PHONY: help setup test clean run run-ocr install check ensure-venv url-clean tg-bot-stop \
        report transcript ocr \
        downrun downocr show db-search

# 虚拟环境路径
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# 支持将小写参数自动映射到大写变量（兼容各种输入习惯）
PAGE ?= $(page)
export PAGE
LIMIT ?= $(limit)
export LIMIT
FLAGS ?= $(flags)
export FLAGS
ID ?= $(id)
export ID
URL ?= $(url)
export URL
SCREENSHOT_OCR ?= $(screenshot_ocr)
export SCREENSHOT_OCR
VIDEO ?= $(video)
export VIDEO
Q ?= $(q)
export Q
TAGS ?= $(tags)
export TAGS
MODE ?= $(mode)
export MODE
FILE ?= $(file)
export FILE
OUTPUT ?= $(output)
export OUTPUT
FORCE ?= $(force)
export FORCE

# 确保虚拟环境存在且可用（首次运行或损坏时自动创建）
ensure-venv:
	@VENV_OK=0; \
	if [ -d "$(VENV_DIR)" ] && [ -f "$(PYTHON)" ]; then \
		$(PYTHON) -c "import sys; sys.exit(0)" 2>/dev/null && VENV_OK=1; \
	fi; \
	if [ "$$VENV_OK" = "0" ]; then \
		if [ -d "$(VENV_DIR)" ]; then \
			echo "⚠️  检测到虚拟环境已损坏（解释器失效），正在重建..."; \
			rm -rf "$(VENV_DIR)"; \
		else \
			echo "🔧 首次运行：创建虚拟环境..."; \
		fi; \
		python3.12 -m venv $(VENV_DIR) 2>/dev/null || python3 -m venv $(VENV_DIR); \
		echo "  ✅ 虚拟环境已创建: $(VENV_DIR)"; \
		echo ""; \
		echo "📦 安装依赖..."; \
		$(PIP) install --upgrade pip setuptools wheel; \
		$(PIP) install -r requirements.txt; \
		$(PIP) install -r XHS-Downloader/requirements.txt 2>/dev/null || true; \
		echo "  ✅ 依赖安装完成"; \
		echo ""; \
		echo "🌐 初始化 Playwright 浏览器..."; \
		$(PYTHON) -m playwright install --with-deps chromium 2>/dev/null || echo "  ⚠️ Playwright 浏览器安装跳过或失败"; \
		echo ""; \
		echo "🗄️  初始化数据库与检索引擎..."; \
		$(PYTHON) -m db.schema 2>/dev/null || true; \
		$(PYTHON) -c "from db.whoosh_search import get_whoosh_index; get_whoosh_index()" 2>/dev/null || true; \
		echo ""; \
		if [ ! -f ".env" ]; then \
			echo "📝 创建配置文件..."; \
			cp .env.example .env 2>/dev/null || touch .env; \
			echo "  ⚠️  请编辑 .env 文件，填入你的 GROQ_API_KEY / GEMINI_API_KEY"; \
		fi; \
		echo ""; \
		echo "✅ 环境初始化完成！"; \
	fi

# 默认目标：显示帮助
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎥 MemoryIndex - 智能视频知识库系统"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 快速开始："
	@echo "  make setup                          初始化环境"
	@echo "  make run Path=视频路径              处理视频（音频转写+AI摘要）"
	@echo "  make ocr Path=视频路径              处理视频（音频+OCR+AI摘要）"
	@echo "  make download URL=视频链接           下载在线视频"
	@echo ""
	@echo "📹 视频处理："
	@echo "  make run Path=路径                  音频转写 + AI摘要"
	@echo "  make ocr Path=路径                  音频转写 + OCR识别 + AI摘要"
	@echo "  make download URL=链接               下载视频到 videos/"
	@echo "  make download-run URL=链接           下载后立即处理（音频模式）"
	@echo "  make download-ocr URL=链接           下载后立即处理（完整模式）"
	@echo ""
	@echo "🌐 网页归档："
	@echo "  make login                          浏览器登录（保存登录态，一次搞定所有平台）"
	@echo "  make list-cookies                   列出当前保存的所有 Cookie 统计"
	@echo "  make delete-cookie DOMAIN=...       删除指定域名的 Cookie（如 xiaohongshu.com）"
	@echo "  make clear-cookies                  清除浏览器所有 Cookie"

	@echo "  make archive URL=网址                保存网页为 Markdown"
	@echo "  make archive-run URL=网址            归档 + 生成AI报告"
	@echo "  make archive-ocr URL=网址            归档 + OCR + AI报告"
	@echo "  make archive-batch FILE=urls.txt     批量归档"
	@echo "  make url-clean URL=链接              URL 反追踪 & 短链接还原"
	@echo ""
	@echo "🔍 搜索与管理："
	@echo "  make search Q=\"关键词\"              全文搜索"
	@echo "  make search-tags TAGS=\"标签1 标签2\"  按标签搜索"
	@echo "  make db-show ID=1                    查看视频详情"
	@echo "  make db-stats                        数据库统计"
	@echo ""
	@echo "🤖 Telegram Bot："
	@echo "  make tg-bot-setup                    配置 Telegram Bot Token"
	@echo "  make tg-bot-start                    启动 Telegram Bot（终端常驻）"
	@echo "  make tg-bot-stop                     停止 Telegram Bot"
	@echo ""
	@echo "🤖 OCR 引擎选择（make ocr 时可用）："
	@echo "  OCR_ENGINE=vision                    Apple Vision（macOS 默认，免配置）"
	@echo "  OCR_ENGINE=paddle                    PaddleOCR（跨平台，需安装）"
	@echo "  OCR_WORKERS=4                        并行进程数（默认=CPU核心/2）"
	@echo ""
	@echo "🔧 环境管理："
	@echo "  make install                         安装基础依赖"
	@echo "  make install-paddle-ocr              安装 PaddleOCR（非 macOS）"
	@echo "  make install-chromium                安装 Chromium（网页归档）"
	@echo "  make check                           检查环境配置"
	@echo "  make clean                           清理输出文件"
	@echo ""
	@echo "📝 示例："
	@echo "  make run Path=~/meeting.mp4"
	@echo "  make ocr Path=lecture.mp4 OCR_WORKERS=4"
	@echo "  make download URL=https://www.youtube.com/watch?v=xxx"
	@echo "  make archive URL=https://zhihu.com/question/123"
	@echo "  make search Q=\"机器学习\""
	@echo ""
	@echo "💡 提示："
	@echo "  • 首次运行会自动创建虚拟环境（.venv）"
	@echo "  • macOS 使用 Vision OCR（无需配置）"
	@echo "  • 其他系统需安装 PaddleOCR：make install-paddle-ocr"
	@echo "  • 需要配置 .env 文件中的 GROQ_API_KEY"
	@echo ""
	@echo "⚡ 命令别名（短命令）："
	@echo "  make downrun  URL=链接          → download-run"
	@echo "  make downocr  URL=链接          → download-ocr"
	@echo "  make show     id=<N>            → db-show"
	@echo "  make show     id=<N> report     → db-show + 打开 report"
	@echo "  make show     id=<N> transcript → db-show + 打开 transcript"
	@echo "  make show     id=<N> ocr        → db-show + 打开 ocr"
	@echo "  make ls                         → db-list"
	@echo "  make search   Q=\"关键词\"        → 与 make search 相同"
	@echo "  make db-search Q=\"关键词\"       → search"
	@echo "  make report   id=<N>            → db-show <N> report"
	@echo "  make transcript id=<N>          → db-show <N> transcript"
        @echo "  make show-ocr id=<N>            → db-show <N> ocr"
setup: ensure-venv
	@echo "🔧 重新初始化环境..."
	@echo "  → 更新 pip..."
	@$(PIP) install --upgrade pip setuptools wheel
	@echo "  → 安装/更新依赖..."
	@$(PIP) install -r requirements.txt
	@echo "  → 检查关键依赖包..."
	@echo "    必需依赖："
	@$(PYTHON) -c "import numpy" 2>/dev/null && echo "      ✅ numpy" || (echo "      ⚠️  numpy 未安装，正在安装..." && $(PIP) install numpy)
	@$(PYTHON) -c "import groq" 2>/dev/null && echo "      ✅ groq" || (echo "      ⚠️  groq 未安装，正在安装..." && $(PIP) install groq)
	@$(PYTHON) -c "import dotenv" 2>/dev/null && echo "      ✅ python-dotenv" || (echo "      ⚠️  python-dotenv 未安装，正在安装..." && $(PIP) install python-dotenv)
	@$(PYTHON) -c "import tqdm" 2>/dev/null && echo "      ✅ tqdm" || (echo "      ⚠️  tqdm 未安装，正在安装..." && $(PIP) install tqdm)
	@$(PYTHON) -c "import tabulate" 2>/dev/null && echo "      ✅ tabulate" || (echo "      ⚠️  tabulate 未安装，正在安装..." && $(PIP) install tabulate)
	@echo "    可选依赖："
	@$(PYTHON) -c "import google.genai" 2>/dev/null && echo "      ✅ google-genai (长文本处理)" || (echo "      ⚠️  google-genai 未安装，正在安装..." && $(PIP) install google-genai)
	@$(PYTHON) -c "import yt_dlp" 2>/dev/null && echo "      ✅ yt-dlp (视频下载)" || echo "      ℹ️  yt-dlp 未安装 (视频下载功能需要)"
	@$(PYTHON) -c "import whoosh" 2>/dev/null && echo "      ✅ Whoosh (全文搜索)" || echo "      ℹ️  Whoosh 未安装 (搜索功能需要)"
	@$(PYTHON) -c "import jieba" 2>/dev/null && echo "      ✅ jieba (中文分词)" || echo "      ℹ️  jieba 未安装 (中文搜索需要)"
	@$(PYTHON) -c "import bs4" 2>/dev/null && echo "      ✅ beautifulsoup4 (HTML解析)" || echo "      ℹ️  beautifulsoup4 未安装 (网页归档需要)"
	@$(PYTHON) -c "import html2text" 2>/dev/null && echo "      ✅ html2text (HTML转换)" || echo "      ℹ️  html2text 未安装 (网页归档需要)"
	@echo "  → 检查配置文件..."
	@if [ ! -f ".env" ]; then \
		echo "  ⚠️  .env 文件不存在，从模板创建..."; \
		cp .env.example .env 2>/dev/null || touch .env; \
		echo "  ⚠️  请编辑 .env 文件，填入你的 GROQ_API_KEY"; \
	fi
	@echo "  → 检查外部工具..."
	@if ! command -v ffmpeg >/dev/null 2>&1; then \
		echo "  ⚠️  ffmpeg 未安装，尝试安装..."; \
		brew install ffmpeg 2>/dev/null || echo "  ❌ 请手动安装: brew install ffmpeg"; \
	else \
		echo "  ✅ ffmpeg 已安装"; \
	fi
	@if ! command -v BBDown >/dev/null 2>&1; then \
		echo "  ⚠️  BBDown 未安装，尝试安装（B站视频下载）..."; \
		curl -sL -o /tmp/BBDown_osx-x64.zip "https://github.com/nilaoda/BBDown/releases/download/1.6.3/BBDown_1.6.3_20240814_osx-x64.zip" && \
		unzip -o -q /tmp/BBDown_osx-x64.zip -d /tmp && \
		chmod +x /tmp/BBDown && \
		cp /tmp/BBDown /usr/local/bin/ 2>/dev/null && \
		rm -f /tmp/BBDown /tmp/BBDown_osx-x64.zip && \
		echo "  ✅ BBDown 安装成功" || \
		echo "  ⚠️  BBDown 自动安装失败，请手动下载: https://github.com/nilaoda/BBDown/releases"; \
	else \
		echo "  ✅ BBDown 已安装"; \
	fi
	@echo "  → 初始化数据库..."
	@$(PYTHON) -m db.schema 2>/dev/null || true
	@echo "  → 初始化 Whoosh 搜索索引..."
	@$(PYTHON) -m db.whoosh_search init 2>/dev/null || true
	@echo "  → 运行环境测试..."
	@$(PYTHON) tests/test_env.py
	@echo ""
	@echo "✅ 环境初始化完成！"
	@echo "📝 下一步：编辑 .env 文件填入 API Key"
	@echo "   nano .env"

# 安装/更新依赖（默认不包含 PaddleOCR）
install: ensure-venv
	@echo "📦 安装依赖..."
	@$(PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"
	@echo ""
	@echo "💡 提示："
	@echo "  • macOS 用户：默认使用 Vision OCR（系统自带，零配置）"
	@echo "  • 跨平台支持：运行 'make install-paddle-ocr' 安装 PaddleOCR"

# 安装 Playwright 浏览器（网页归档需要）
install-playwright: ensure-venv
	@echo "📦 安装 Playwright Chromium 浏览器..."
	@$(VENV_DIR)/bin/playwright install chromium
	@echo "✅ Playwright Chromium 安装完成"
	@echo "💡 使用方法：make archive URL=https://example.com"

# 安装 PaddleOCR（可选）
install-paddle-ocr: ensure-venv
	@echo "📦 安装 PaddleOCR 及相关依赖..."
	@$(PIP) install paddlepaddle>=3.0.0 paddleocr>=2.7.0 opencv-python
	@echo "✅ PaddleOCR 安装完成"
	@echo "💡 使用方法：make ocr Path=xxx.mp4 OCR_ENGINE=paddle"

# 运行环境测试
test: ensure-venv
	@echo "🧪 运行环境测试..."
	@$(PYTHON) tests/test_env.py

# 全功能自检和测试
selftest: ensure-venv
	@$(PYTHON) scripts/selftest.py

# Cookie 统一管理

cleanup-project:
	@echo "🧹 清理项目临时文件..."
	@$(PYTHON) scripts/cleanup_project.py --yes

# 测试 Vision OCR（仅 macOS）
test-vision-ocr: ensure-venv
	@echo "🧪 测试 Apple Vision OCR..."
	@$(PYTHON) tests/test_vision_ocr.py

# 测试 Vision OCR（带图片）
test-vision-ocr-image: ensure-venv
	@if [ -z "$(IMAGE)" ]; then \
		echo "❌ 错误：请提供图片路径"; \
		echo "   用法: make test-vision-ocr-image IMAGE=图片路径"; \
		echo ""; \
		echo "💡 示例:"; \
		echo "   make test-vision-ocr-image IMAGE=XHS-Downloader/static/screenshot/命令行模式截图CN1.png"; \
		echo "   make test-vision-ocr-image IMAGE=test.png"; \
		exit 1; \
	fi
	@$(PYTHON) tests/test_vision_ocr.py $(IMAGE)

# 安装独立 Chromium（用于网页归档）
install-chromium:
	@echo "🔧 安装独立 Chromium 浏览器..."
	@if [ -d "chromium/chrome-mac" ]; then \
		echo "  ✓ Chromium 已存在: chromium/chrome-mac/Chromium.app"; \
		exit 0; \
	fi
	@echo "  → 创建 chromium 目录..."
	@mkdir -p chromium
	@echo "  → 检测系统架构..."
	@ARCH=$$(uname -m); \
	if [ "$$ARCH" = "arm64" ]; then \
		echo "  → 检测到 Apple Silicon (ARM64)"; \
		DOWNLOAD_URL="https://storage.googleapis.com/chromium-browser-snapshots/Mac_Arm/1355694/chrome-mac.zip"; \
	else \
		echo "  → 检测到 Intel (x86_64)"; \
		DOWNLOAD_URL="https://storage.googleapis.com/chromium-browser-snapshots/Mac/1355694/chrome-mac.zip"; \
	fi; \
	echo "  → 下载 Chromium..."; \
	curl -L "$$DOWNLOAD_URL" -o chromium/chrome-mac.zip || { echo "❌ 下载失败"; exit 1; }; \
	echo "  → 解压..."; \
	cd chromium && unzip -q chrome-mac.zip && rm chrome-mac.zip; \
	echo "  → 清除隔离属性 (Quarantine)..."; \
	xattr -cr chromium/chrome-mac/Chromium.app; \
	echo "  → 授权执行权限..."; \
	chmod -R +x chromium/chrome-mac/Chromium.app/Contents/MacOS/; \
	echo "  ✓ Chromium 安装完成！"; \
	echo ""; \
	echo "📍 安装路径: chromium/chrome-mac/Chromium.app"; \
	echo "💡 已配置为使用 --headless=new 模式运行"

# 检查环境
check: ensure-venv
	@echo "🔍 检查环境配置..."
	@echo ""
	@echo "Python 虚拟环境："
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "  ✅ $(VENV_DIR) 存在"; \
		echo "  ℹ️  Python: $(PYTHON)"; \
	else \
		echo "  ❌ $(VENV_DIR) 不存在，请运行: make setup"; \
	fi
	@echo ""
	@echo "配置文件："
	@if [ -f ".env" ]; then \
		echo "  ✅ .env 存在"; \
		if grep -q "GROQ_API_KEY=$$" .env || grep -q "GROQ_API_KEY=your" .env; then \
			echo "  ⚠️  GROQ_API_KEY 未设置"; \
		else \
			echo "  ✅ GROQ_API_KEY 已配置"; \
		fi \
	else \
		echo "  ❌ .env 不存在"; \
	fi
	@echo ""
	@echo "FFmpeg："
	@if command -v ffmpeg >/dev/null 2>&1; then \
		echo "  ✅ ffmpeg 已安装"; \
	else \
		echo "  ❌ ffmpeg 未安装，请运行: brew install ffmpeg"; \
	fi

# 处理视频：仅音频转文字 + AI总结（不含OCR）
# 可选参数：
#   LLM=oss|gemini         - 指定总结模型 (默认自动)
#   ASR=v3|turbo           - 指定语音识别模型 (默认 v3)
run: ensure-venv
	@if [ -z "$(Path)" ]; then \
		echo "❌ 错误：请指定视频路径"; \
		echo "用法：make run Path=/path/to/video.mp4 [LLM=oss|gemini] [ASR=v3|turbo]"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎬 处理视频（音频模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📹 视频: $(Path)"
	@if [ "$(LLM)" = "gemini" ]; then echo "🧠 LLM模型: Gemini (强制)"; else echo "🧠 LLM模型: 自动 (OpenAI-120B / Gemini)"; fi
	@if [ "$(ASR)" = "turbo" ]; then echo "🎤 ASR模型: Whisper Large V3 Turbo"; else echo "🎤 ASR模型: Whisper Large V3 (Default)"; fi
	@echo "🔊 流程: 音频提取 → Groq转写 → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@export LLM_PROVIDER=$(LLM) && \
	 export ASR_MODEL_TYPE=$(ASR) && \
	 $(PYTHON) core/process_media.py "$(Path)"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ 处理完成！"
	@echo "� 输出目录: output/视频名_时间戳/"
	@echo "   • report.txt - 格式化报告"
	@echo "   • transcript_raw.txt - 语音识别原文"
	@echo "   • ocr_raw.txt - OCR识别原文（如启用）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 处理视频：音频 + OCR + AI总结（完整流程）
# 可选参数：
#   DET_MODEL=mobile|server  - 检测模型（默认 mobile）
#   USE_GPU=1                - 启用 GPU 加速
#   OCR_WORKERS=N            - 并行进程数（默认=CPU核心数/2）
#   LLM=oss|gemini         - 指定总结模型 (默认自动)
#   ASR=v3|turbo           - 指定语音识别模型 (默认 v3)
#   LEGACY=1                 - 使用传统 1FPS 抽帧（禁用智能抽帧）

ocr-legacy:
	@$(MAKE) ocr LEGACY=1

ocr: ensure-venv
	@if [ -z "$(Path)" ]; then \
		echo "❌ 错误：请指定视频路径"; \
		echo "用法：make ocr Path=/path/to/video.mp4"; \
		echo "可选：make ocr Path=xxx DET_MODEL=server REC_MODEL=server"; \
		echo "可选：make ocr Path=xxx OCR_WORKERS=3  # 使用3个进程"; \
		exit 1; \
	fi
	@DET=$${DET_MODEL:-mobile}; \
	REC=$${REC_MODEL:-mobile}; \
	if [ -n "$(OCR_WORKERS)" ]; then \
		WORKERS=$(OCR_WORKERS); \
	else \
		WORKERS=auto; \
	fi; \
	GPU_FLAG=""; \
	if [ "$(USE_GPU)" = "1" ]; then GPU_FLAG="--use-gpu"; fi; \
	LEGACY_FLAG=""; \
	if [ "$(LEGACY)" = "1" ]; then LEGACY_FLAG="--legacy-ocr"; fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🎬 处理视频（完整模式：OCR + 音频）"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 视频: $(Path)"; \
	if [ "$(LLM)" = "gemini" ]; then echo "🧠 LLM模型: Gemini (强制)"; else echo "🧠 LLM模型: 自动 (OpenAI-120B / Gemini)"; fi; \
	if [ "$(ASR)" = "turbo" ]; then echo "🎤 ASR模型: Whisper Large V3 Turbo"; else echo "🎤 ASR模型: Whisper Large V3 (Default)"; fi; \
	if [ "$(LEGACY)" = "1" ]; then echo "📷 抽帧模式: 传统固定 1 FPS"; else echo "🚀 抽帧模式: 智能变化触发 & 融合"; fi; \
	echo "🔍 流程: 1️⃣  OCR识别 → 2️⃣  音频转写 → 3️⃣  AI总结"; \
	echo "🤖 OCR模型: det=$$DET, rec=$$REC"; \
	if [ "$$WORKERS" != "auto" ]; then \
		echo "⚡ 并行进程: $$WORKERS (用户指定)"; \
	else \
		echo "⚡ 并行进程: 自动 (CPU核心数/2 ≈ 5)"; \
	fi; \
	echo "⏱️  注意：OCR 处理较慢，带进度条显示"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	export LLM_PROVIDER=$(LLM) && \
	export ASR_MODEL_TYPE=$(ASR) && \
	OCR_WORKERS=$$WORKERS $(PYTHON) core/process_media.py "$(Path)" --with-frames --ocr-det-model $$DET --ocr-rec-model $$REC $$GPU_FLAG $$LEGACY_FLAG; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ 处理完成！"; \
	echo "� 输出目录: output/视频名_时间戳/"; \
	echo "   • ocr_raw.txt - OCR识别原文"; \
	echo "   • frames/ - 视频抽帧图片"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 清理输出文件
clean:
	@echo "🧹 清理输出文件..."
	@if [ -d "output" ]; then \
		rm -rf output/*; \
		echo "✅ 已清理 output/ 目录"; \
	else \
		echo "ℹ️  output/ 目录不存在"; \
	fi

# 深度清理（包括虚拟环境）
clean-all: clean
	@echo "🧹 深度清理..."
	@if [ -d "$(VENV_DIR)" ]; then \
		rm -rf $(VENV_DIR); \
		echo "✅ 已删除虚拟环境"; \
	fi
	@if [ -d "__pycache__" ]; then \
		rm -rf __pycache__; \
		echo "✅ 已删除缓存文件"; \
	fi
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ 深度清理完成"

# 查看报告（显示最新的报告）
show-report:
	@if [ -d "output/reports" ]; then \
		LATEST=$$(ls -t output/reports/*.txt 2>/dev/null | head -1); \
		if [ -n "$$LATEST" ]; then \
			echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
			echo "📄 最新报告: $$LATEST"; \
			echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
			echo ""; \
			cat "$$LATEST"; \
		else \
			echo "ℹ️  未找到报告文件"; \
		fi \
	else \
		echo "ℹ️  output/reports/ 目录不存在"; \
	fi

# 下载视频
download: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定视频URL"; \
		echo "用法：make download URL=https://example.com/video"; \
		echo "强制重新下载：make download URL=... FORCE=1"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📥 下载视频"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "📁 存储位置: videos/"
	@if [ "$(FORCE)" = "1" ]; then \
		echo "⚠️  强制重新下载模式"; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ "$(FORCE)" = "1" ]; then \
		cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)" --force; \
	else \
		cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)"; \
	fi
	@echo ""
	@echo "✅ 完成！"

# 下载视频后自动处理（音频模式）
download-run: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定视频URL"; \
		echo "用法：make download-run URL=https://example.com/video"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📥 下载并处理视频（音频模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@if [ "$(LLM)" = "gemini" ]; then echo "🧠 LLM模型: Gemini (强制)"; else echo "🧠 LLM模型: 自动 (OpenAI-120B / Gemini)"; fi
	@if [ "$(ASR)" = "turbo" ]; then echo "🎤 ASR模型: Whisper Large V3 Turbo"; else echo "🎤 ASR模型: Whisper Large V3 (Default)"; fi
	@echo "🔊 流程: 下载 → 音频提取 → Groq转写 → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@# 先下载视频（保持实时进度条显示）
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)"
	@DOWNLOAD_EXIT=$$?; \
	if [ $$DOWNLOAD_EXIT -ne 0 ]; then \
		echo "❌ 下载失败"; \
		exit 1; \
	fi
	@echo ""
	@# 获取已下载的文件路径（再次运行，此时应直接返回结果）
	@VIDEO_PATH=$$(cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)" --json 2>/dev/null | $(PYTHON) -c "import json, sys; print(json.load(sys.stdin)['file_path'])"); \
	if [ -z "$$VIDEO_PATH" ]; then \
		echo "❌ 无法从下载输出中提取文件路径"; \
		exit 1; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 开始处理视频"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	cd $(PWD) && PYTHONPATH=$(PWD) LLM_PROVIDER=$(LLM) ASR_MODEL_TYPE=$(ASR) $(PYTHON) core/process_video.py "$$VIDEO_PATH"

# 下载视频后自动处理（完整OCR模式）
download-ocr: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定视频URL"; \
		echo "用法：make download-ocr URL=https://example.com/video"; \
		exit 1; \
	fi
	@LEGACY_FLAG=""; \
	if [ "$(LEGACY)" = "1" ]; then LEGACY_FLAG="--legacy-ocr"; fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📥 下载并处理视频（完整模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@if [ "$(LLM)" = "gemini" ]; then echo "🧠 LLM模型: Gemini (强制)"; else echo "🧠 LLM模型: 自动 (OpenAI-120B / Gemini)"; fi; \
	if [ "$(ASR)" = "turbo" ]; then echo "🎤 ASR模型: Whisper Large V3 Turbo"; else echo "🎤 ASR模型: Whisper Large V3 (Default)"; fi; \
	if [ "$(LEGACY)" = "1" ]; then echo "📷 抽帧模式: 传统固定 1 FPS"; else echo "🚀 抽帧模式: 智能变化触发 & 融合"; fi; \
	echo "📺 流程: 下载 → 抽帧 → OCR → ASR → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@# 先下载视频（所有输出正常显示，包括进度条）
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)"; \
	if [ $$? -ne 0 ]; then \
		echo "❌ 下载失败"; \
		exit 1; \
	fi; \
	echo ""; \
	VIDEO_PATH=$$(cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/video_downloader.py "$(URL)" --json 2>/dev/null | $(PYTHON) -c "import json, sys; data = json.load(sys.stdin); print(data['file_path'])"); \
	if [ -z "$$VIDEO_PATH" ]; then \
		echo "❌ 无法获取下载文件路径"; \
		exit 1; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 开始处理视频"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	cd $(PWD) && PYTHONPATH=$(PWD) DET_MODEL=$(DET_MODEL) REC_MODEL=$(REC_MODEL) USE_GPU=$(USE_GPU) \
	LLM_PROVIDER=$(LLM) ASR_MODEL_TYPE=$(ASR) \
	$(PYTHON) core/process_video.py "$$VIDEO_PATH" --with-frames $$LEGACY_FLAG

# 查看所有报告列表
list-reports:
	@if [ -d "output/reports" ]; then \
		echo "📋 报告列表:"; \
		ls -lht output/reports/*.txt 2>/dev/null || echo "  (无报告)"; \
	else \
		echo "ℹ️  output/reports/ 目录不存在"; \
	fi

# 配置小红书 Cookie
config-xhs-cookie: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🍪 配置小红书 Cookie"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) scripts/configure_xhs_cookie.py

# 配置知乎 Cookie
config-zhihu-cookie: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🍪 配置知乎 Cookie"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) scripts/configure_zhihu_cookie.py

# ============================================
# 数据库相关命令（新增）
# ============================================

# 初始化数据库
db-init: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🗄️  初始化数据库"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) -m db.schema
	@echo ""
	@echo "🔍 初始化 Whoosh 搜索索引..."
	@$(PYTHON) -m db.whoosh_search init
	@echo ""
	@echo "✅ 数据库初始化完成！"
	@echo "📂 数据库位置: storage/database/knowledge.db"
	@echo "📂 搜索索引位置: storage/whoosh_index/"

# 重建数据库（删除所有数据）
db-reset: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "⚠️  重建数据库（将删除所有数据）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@read -p "确认删除所有数据？[y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(PYTHON) -m db.schema --force; \
		$(PYTHON) -m db.whoosh_search init --force; \
		echo "✅ 数据库已重建"; \
	else \
		echo "❌ 取消操作"; \
	fi

# 检查数据库状态
db-status: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 数据库状态"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) -m db.schema --check
	@echo ""
	@echo "🔍 搜索索引状态:"
	@$(PYTHON) -m db.whoosh_search status

# 数据库详细统计
db-stats: ensure-venv
	@$(PYTHON) cli/db_stats.py --all

# 网页归档统计
db-stats-archives: ensure-venv
	@$(PYTHON) cli/db_stats.py --archives

# 视频文件统计
db-stats-videos: ensure-venv
	@$(PYTHON) cli/db_stats.py --videos

# 标签统计
db-stats-tags: ensure-venv
	@$(PYTHON) cli/db_stats.py --tags

# 重建搜索索引（从数据库同步）
whoosh-rebuild: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔄 重建 Whoosh 搜索索引"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) -m db.whoosh_search rebuild
	@echo ""
	@echo "✅ 搜索索引重建完成！"

# 测试 Whoosh 搜索
whoosh-search: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 Whoosh 搜索测试"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ifdef Q
	@$(PYTHON) -m db.whoosh_search search "$(Q)"
else
	@echo "用法: make whoosh-search Q=\"搜索词\""
	@echo ""
	@echo "示例:"
	@echo "  make whoosh-search Q=\"美国\""
	@echo "  make whoosh-search Q=\"INTP\""
	@echo "  make whoosh-search Q=\"深度学习\""
endif

# 测试数据库功能
db-test: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 测试数据库功能"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) tests/test_database.py

# 导入真实数据测试
db-import-test: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 导入 output 目录真实数据测试"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) tests/test_database_import.py

# 搜索命令
search: ensure-venv
	@if [ -z "$(Q)" ]; then \
		echo "❌ 错误：请指定搜索关键词"; \
		echo "用法：make search Q=\"关键词\""; \
		echo "示例：make search Q=\"机器学习\""; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 搜索: $(Q)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) cli/search_cli.py search "$(Q)" $(FLAGS)

# 按标签搜索
search-tags: ensure-venv
	@if [ -z "$(TAGS)" ]; then \
		echo "❌ 错误：请指定标签"; \
		echo "用法：make search-tags TAGS=\"标签1 标签2\""; \
		echo "示例：make search-tags TAGS=\"教育 科技\""; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🏷️  按标签搜索: $(TAGS)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) cli/search_cli.py tags --tags $(TAGS) --match-all

# 搜索主题
search-topics: ensure-venv
	@if [ -z "$(Q)" ]; then \
		echo "❌ 错误：请指定搜索关键词"; \
		echo "用法：make search-topics Q=\"关键词\""; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📚 搜索主题: $(Q)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) cli/search_cli.py topics "$(Q)"

# 列出热门标签
db-tags: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🏷️  热门标签"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) cli/search_cli.py list-tags --limit 50

# 列出所有视频（带标签和摘要）
db-list: ensure-venv
	@LIMIT=$${LIMIT:-20}; \
	OFFSET=$${OFFSET:-0}; \
	PAGE_VAL=$${PAGE:-$${page:-}}; \
	if [ -n "$$PAGE_VAL" ]; then \
		OFFSET=$$((($$PAGE_VAL-1)*$$LIMIT)); \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 知识库列表 (Limit: $$LIMIT, Offset: $$OFFSET)"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	$(PYTHON) cli/main_cli.py list --limit $$LIMIT --offset $$OFFSET

# 展示特定ID的视频详情
db-show: ensure-venv
	@if [ -z "$(ID)" ]; then \
		echo "❌ 错误：请指定视频ID"; \
		echo "用法：make db-show ID=1 [FILE=report/transcript/ocr]"; \
		exit 1; \
	fi
	@if [ -n "$(FILE)" ]; then \
		$(PYTHON) cli/search_cli.py show $(ID) $(FILE) $(FLAGS); \
	else \
		$(PYTHON) cli/search_cli.py show $(ID) $(FLAGS); \
	fi

# 快捷目标：make db-show id=<N> report / transcript / ocr
# 用法示例：make db-show id=66 report
report: ensure-venv
	@if [ -z "$(ID)" ]; then \
		echo "❌ 错误：请先指定视频ID"; \
		echo "用法：make db-show id=<N> report"; \
		exit 1; \
	fi
	@$(PYTHON) cli/search_cli.py show $(ID) report $(FLAGS)

transcript: ensure-venv
	@if [ -z "$(ID)" ]; then \
		echo "❌ 错误：请先指定视频ID"; \
		echo "用法：make db-show id=<N> transcript"; \
		exit 1; \
	fi
	@$(PYTHON) cli/search_cli.py show $(ID) transcript $(FLAGS)

show-ocr: ensure-venv
	@if [ -z "$(ID)" ]; then \
		echo "❌ 错误：请先指定视频ID"; \
		echo "用法：make db-show id=<N> ocr"; \
		exit 1; \
	fi
	@$(PYTHON) cli/search_cli.py show $(ID) ocr $(FLAGS)

# 删除特定ID的视频记录
db-delete: ensure-venv
	@if [ -z "$(ID)" ]; then \
		echo "❌ 错误：请指定视频ID"; \
		echo "用法：make db-delete ID=1"; \
		echo "用法：make db-delete ID=1 FORCE=1  # 强制删除，不提示确认"; \
		exit 1; \
	fi
	@if [ -n "$(FORCE)" ]; then \
		$(PYTHON) cli/search_cli.py delete $(ID) --force; \
	else \
		$(PYTHON) cli/search_cli.py delete $(ID); \
	fi

# 数据库备份
db-backup: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "💾 备份数据库"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@mkdir -p storage/backups
	@BACKUP_FILE="storage/backups/knowledge_backup_$$(date +%Y%m%d_%H%M%S).db"; \
	if [ -f "storage/database/knowledge.db" ]; then \
		cp storage/database/knowledge.db "$$BACKUP_FILE"; \
		echo "✅ 备份完成: $$BACKUP_FILE"; \
		echo "📊 文件大小: $$(du -h $$BACKUP_FILE | cut -f1)"; \
	else \
		echo "❌ 数据库文件不存在"; \
	fi

# 数据库维护（优化）
db-vacuum: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧹 数据库优化（VACUUM）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -f "storage/database/knowledge.db" ]; then \
		echo "📊 优化前大小: $$(du -h storage/database/knowledge.db | cut -f1)"; \
		sqlite3 storage/database/knowledge.db "VACUUM;"; \
		echo "✅ 优化完成"; \
		echo "📊 优化后大小: $$(du -h storage/database/knowledge.db | cut -f1)"; \
	else \
		echo "❌ 数据库文件不存在"; \
	fi

# 快捷命令：搜索（简化版）
s: search

# 快捷命令：数据库状态
ds: db-status

# 快捷命令：列出视频
ls: db-list

# ── 别名映射 ────────────────────────────────────────────────────────────────
downrun: download-run   # make downrun URL=...
downocr: download-ocr   # make downocr URL=...
show: db-show           # make show id=<N> [report/transcript/ocr]
db-search: search       # make db-search q=<关键词>（search 是主目标）

# ============================================
# 网页归档功能 (Web Archiver)
# ============================================

# 归档单个URL（智能选择引擎，无头模式）
# 默认：只保存内容 + LLM 重命名，不生成 report
archive: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make archive URL=网址 [MODE=full] [SCREENSHOT_OCR=true]"; \
		echo "💡 支持分享文本格式（自动提取URL）"; \
		exit 1; \
	fi
	@PYTHONPATH=. $(PYTHON) scripts/unified_archive_cli.py "$(URL)" --mode=$(or $(MODE),default) $(if $(SCREENSHOT_OCR),--screenshot-ocr)

# 归档单个URL（显示浏览器界面，供调试使用）
archive-visible: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make archive-visible URL=网址 [MODE=full] [SCREENSHOT_OCR=true]"; \
		echo "💡 此命令会显示浏览器界面，供调试使用"; \
		exit 1; \
	fi
	@PYTHONPATH=. $(PYTHON) scripts/unified_archive_cli.py "$(URL)" --mode=$(or $(MODE),default) --visible $(if $(SCREENSHOT_OCR),--screenshot-ocr)

# 批量归档（从文件读取URL列表）
archive-batch: ensure-venv
	@if [ -z "$(FILE)" ]; then \
		echo "❌ 错误: 请提供URL列表文件"; \
		echo "用法: make archive-batch FILE=urls.txt"; \
		exit 1; \
	fi
	@if [ ! -f "$(FILE)" ]; then \
		echo "❌ 错误: 文件不存在: $(FILE)"; \
		exit 1; \
	fi
	@echo "🌐 批量归档 $(FILE) 中的URL..."
	@$(PYTHON) -m cli.archive_cli -f "$(FILE)" $(if $(OUTPUT),-o $(OUTPUT))

# 检测URL平台
archive-detect: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make archive-detect URL=网址"; \
		exit 1; \
	fi
	@$(PYTHON) -m cli.archive_cli --detect "$(URL)"

# 测试归档功能
test-archiver: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make test-archiver URL=网址"; \
		exit 1; \
	fi
	@$(PYTHON) -c "from archiver import UniversalArchiver; import asyncio; \
		async def test(): \
			archiver = UniversalArchiver(); \
			result = await archiver.archive('$(URL)'); \
			print(f'Platform: {result[\"platform\"]}'); \
			print(f'Title: {result[\"title\"]}'); \
			print(f'Content length: {result[\"content_length\"]}'); \
		asyncio.run(test())"

# URL 反追踪 & 短链接还原
url-clean: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make url-clean URL=\"链接或包含链接的文本\""; \
		exit 1; \
	fi
	@$(PYTHON) scripts/url_cleaner.py "$(URL)"
	@echo ""
	@CLEAN_URL=$$($(PYTHON) scripts/url_cleaner.py --clean-only "$(URL)" 2>/dev/null); \
	if [ -n "$$CLEAN_URL" ]; then \
		echo "📋 清理后链接（已复制到剪贴板）："; \
		echo "   $$CLEAN_URL"; \
		echo "$$CLEAN_URL" | pbcopy 2>/dev/null && echo "✅ 已复制" || echo "⚠️  pbcopy 不可用（非 macOS）"; \
	fi

# DrissionPage 归档（高级：强制使用真实浏览器）
drission-archive: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误: 请提供URL参数"; \
		echo "用法: make drission-archive URL=网址"; \
		echo "💡 提示: 支持分享文本格式，会自动提取URL"; \
		exit 1; \
	fi
	@PYTHONPATH=. $(PYTHON) scripts/drission_archive_cli.py "$(URL)"

# 浏览器登录辅助（保存登录态）
login: ensure-venv
	@echo "🔐 启动浏览器登录辅助..."
	@$(PYTHON) scripts/login_helper.py

# 推特登录辅助
login-twitter: ensure-venv
	@echo "🔐 启动推特登录辅助..."
	@$(PYTHON) scripts/login_twitter.py

# 测试推特 Cookie
test-twitter-cookie: ensure-venv
	@echo "🧪 测试推特 Cookie..."
	@$(PYTHON) scripts/test_twitter_cookie.py

# 导出推特 Cookies 到文件
export-twitter-cookies: ensure-venv
	@echo "📤 导出推特 Cookies..."
	@$(PYTHON) scripts/login_twitter.py --export

# 手动配置 Cookie（login 失败时的备选方案）
config-drission-cookie: ensure-venv
	@echo "🍪 手动配置 DrissionPage Cookie..."
	@$(PYTHON) scripts/configure_drission_cookie.py

# 重置浏览器数据（清空登录态）
# Cookie 管理工具
list-cookies: ensure-venv
	@echo "📋 获取所有保存的 Cookie..."
	@$(PYTHON) scripts/cookie_manager.py --list

delete-cookie: ensure-venv
	@if [ -z "$(DOMAIN)" ]; then \
		echo "❌ 错误: 请提供 DOMAIN 参数。示例: make delete-cookie DOMAIN=xiaohongshu.com"; \
		exit 1; \
	fi
	@echo "🗑️ 正在删除涉及 $$(DOMAIN) 的 Cookie..."
	@$(PYTHON) scripts/cookie_manager.py --delete "$(DOMAIN)"

clear-cookies: ensure-venv
	@echo "🧹 清除所有 Cookie 数据 (不删除插件等其他浏览器数据)..."
	@$(PYTHON) scripts/cookie_manager.py --clear-all


reset-browser:
	@echo "🔄 重置浏览器数据..."
	@$(PYTHON) scripts/reset_browser.py

# 清理归档输出
clean-archived:
	@echo "🗑️  清理归档输出..."
	@rm -rf archived/ test_archived/
	@echo "✅ 清理完成"

# 测试 OCR_WORKERS 参数传递
test-workers:
	@if [ -n "$(OCR_WORKERS)" ]; then \
		WORKERS=$(OCR_WORKERS); \
	else \
		WORKERS=auto; \
	fi; \
	echo "Make 变量: OCR_WORKERS=$(OCR_WORKERS)"; \
	echo "Shell 变量: WORKERS=$$WORKERS"; \
	OCR_WORKERS=$$WORKERS $(PYTHON) tests/test_make_workers.py

# ============================================
# 网页归档 + 数据库集成 (新增)
# ============================================

# 归档网页并生成AI报告（类似 download-run）
# 生成 report.md，使用 LLM 重命名
archive-run: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定网页URL"; \
		echo "用法：make archive-run URL=https://example.com"; \
		echo ""; \
		echo "💡 示例："; \
		echo "  make archive-run URL=https://www.zhihu.com/question/123/answer/456"; \
		echo "  make archive-run URL=https://www.xiaohongshu.com/explore/abc123"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 归档网页并生成报告"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "📝 流程: 归档 → AI报告 → LLM重命名 → 数据库存储"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/archive_processor.py "$(URL)" $(if $(SCREENSHOT_OCR),--screenshot-ocr)

# 归档网页并进行OCR识别（类似 download-ocr）
# 生成 report.md，使用 LLM 重命名
archive-ocr: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定网页URL"; \
		echo "用法：make archive-ocr URL=https://example.com"; \
		echo ""; \
		echo "💡 此功能将归档网页后对其中的图片进行OCR识别"; \
		echo ""; \
		echo "示例："; \
		echo "  make archive-ocr URL=https://www.zhihu.com/question/123/answer/456"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 归档网页并进行OCR识别"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "🔍 流程: 归档 → OCR识别 → AI报告 → LLM重命名 → 数据库存储"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/archive_processor.py "$(URL)" --with-ocr $(if $(SCREENSHOT_OCR),--screenshot-ocr)

# 归档网页（显示浏览器，供调试）
archive-run-visible: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定网页URL"; \
		echo "用法：make archive-run-visible URL=https://example.com"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 归档网页（可视化调试模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "👁️  浏览器窗口将可见"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@cd $(PWD) && PYTHONPATH=$(PWD) $(PYTHON) core/archive_processor.py "$(URL)" --visible $(if $(SCREENSHOT_OCR),--screenshot-ocr)

# ============================================
# Telegram Bot 集成
# ============================================

# 配置 Telegram Bot (设置 Token)
tg-bot-setup: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 配置 Telegram Bot"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) -c "import os; from pathlib import Path; from dotenv import load_dotenv, set_key; env_path = Path.home() / '.memoryindex' / '.env'; env_path.parent.mkdir(parents=True, exist_ok=True); env_path.touch(exist_ok=True); load_dotenv(env_path); current_token=os.getenv('TG_BOT_TOKEN', ''); current_user=os.getenv('TG_ALLOWED_USER_ID', ''); print(f'当前配置的 TG_BOT_TOKEN: {current_token[:5]}***{current_token[-4:]}' if current_token else '未配置 TG_BOT_TOKEN'); token=input('\n请输入新的 Telegram Bot Token (直接回车保持不变): ').strip(); set_key(str(env_path), 'TG_BOT_TOKEN', token) if token else None; print(f'\n当前允许使用的用户ID: {current_user}' if current_user else '\n当前未限制使用用户(所有人可用)'); user_id=input('\n请输入仅允许使用的 Telegram User ID (直接回车保持不变, 输入 -1 取消限制): ').strip(); set_key(str(env_path), 'TG_ALLOWED_USER_ID', '' if user_id == '-1' else user_id) if user_id else None; print('\n✅ 配置已更新。')"

# 停止 Telegram Bot
tg-bot-stop:
	@echo "🛑 停止 Telegram Bot..."
	@pkill -9 -f "cli/tg_bot.py" 2>/dev/null && echo "✅ Bot 已停止" || echo "ℹ️  Bot 未在运行"

# 常驻运行 Telegram Bot
tg-bot-start: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 启动 Telegram Bot (终端常驻)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🛑 清理已有实例..."
	@pkill -9 -f "cli/tg_bot.py" 2>/dev/null || true
	@sleep 1
	@if ! $(PYTHON) -c "import telegram" 2>/dev/null; then \
		echo "📦 未检测到 python-telegram-bot，正在安装..."; \
		$(PIP) install "python-telegram-bot[job-queue]"; \
		echo "✅ 安装完成"; \
	fi
	@PYTHONPATH=$(PWD) $(PYTHON) cli/tg_bot.py
