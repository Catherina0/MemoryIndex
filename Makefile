# Makefile for Video Report Pipeline
# 使用方法：make <target> VIDEO=/path/to/video.mp4

.PHONY: help setup test clean run run-ocr install check ensure-venv

# 虚拟环境路径
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# 确保虚拟环境存在（首次运行时自动创建）
ensure-venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "🔧 首次运行：创建虚拟环境..."; \
		python3 -m venv $(VENV_DIR); \
		echo "  ✅ 虚拟环境已创建: $(VENV_DIR)"; \
		echo ""; \
		echo "📦 安装依赖..."; \
		$(PIP) install --upgrade pip setuptools wheel; \
		$(PIP) install -r requirements.txt; \
		echo "  ✅ 依赖安装完成"; \
		echo ""; \
		if [ ! -f ".env" ]; then \
			echo "📝 创建配置文件..."; \
			cp .env.example .env 2>/dev/null || touch .env; \
			echo "  ⚠️  请编辑 .env 文件，填入你的 GROQ_API_KEY"; \
		fi; \
		echo ""; \
		echo "🧪 运行环境自检..."; \
		$(PYTHON) test_env.py; \
		echo ""; \
		echo "✅ 环境初始化完成！"; \
	fi

# 默认目标：显示帮助
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📹 Video Report Pipeline - 快速命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 快速开始："
	@echo "  make run VIDEO=视频路径   首次运行自动创建虚拟环境 + 处理视频"
	@echo "  make setup              手动初始化/重置环境"
	@echo "  make test               运行环境自检"
	@echo ""
	@echo "📹 处理视频："
	@echo "  make run VIDEO=视频路径   音频转文字 + AI总结（快速模式）"
	@echo "  make ocr VIDEO=视频路径   音频 + OCR + AI总结（完整模式）"
	@echo ""
	@echo "🤖 OCR 模型选择（可选参数）："
	@echo "  DET_MODEL=mobile|server   检测模型（默认 mobile=快速）"
	@echo "  REC_MODEL=mobile|server   识别模型（默认 mobile=快速）"
	@echo "  USE_GPU=1                 启用 GPU 加速"
	@echo ""
	@echo "🔧 维护命令："
	@echo "  make install            安装/更新依赖"
	@echo "  make check              检查环境配置"
	@echo "  make clean              清理输出文件"
	@echo "  make clean-all          清理所有（含虚拟环境）"
	@echo ""
	@echo "� 下载视频："
	@echo "  make download URL=视频链接             下载视频到 videos/ 目录"
	@echo "  make download-run URL=视频链接         下载后自动处理（音频模式）"
	@echo "  make download-ocr URL=视频链接         下载后自动处理（完整模式）"	@echo ""
	@echo "💡 URL 输入支持："
	@echo "  • 纯 URL: make download URL=https://www.youtube.com/watch?v=xxx"
	@echo "  • 分享文本: make download URL=\"分享一个视频给你：https://www.bilibili.com/video/BVxxx 看看\""
	@echo "  • 自动提取: 会自动从文本中识别视频链接"	@echo ""
	@echo "📝 示例："
	@echo "  make run VIDEO=~/Downloads/meeting.mp4"
	@echo "  make ocr VIDEO=~/Downloads/lecture.mp4"
	@echo "  make download URL=https://www.youtube.com/watch?v=xxxxx"
	@echo "  make download-run URL=https://www.bilibili.com/video/BVxxxxx"
	@echo "  make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server  # 高精度"
	@echo "  make ocr VIDEO=xxx DET_MODEL=mobile REC_MODEL=mobile  # 快速"
	@echo ""
	@echo "💡 提示："
	@echo "  • 首次运行任何命令会自动创建虚拟环境"
	@echo "  • 所有依赖会自动安装在项目的 .venv 目录"
	@echo "  • mobile模型：速度快，内存占用小，适合普通设备"
	@echo "  • server模型：精度高，资源消耗大，适合高性能设备"
	@echo "  • 需要配置 .env 文件中的 GROQ_API_KEY"
	@echo "  • 支持平台：YouTube, Bilibili, 小红书等（需安装对应工具）"
	@echo ""
	@echo "🗄️  数据库与搜索："
	@echo "  make db-init                初始化数据库"
	@echo "  make db-status              查看数据库状态"
	@echo "  make search Q=\"关键词\"      搜索视频内容"
	@echo "  make search-tags TAGS=\"标签1 标签2\"  按标签搜索"
	@echo "  make db-tags                查看热门标签"
	@echo "  make db-backup              备份数据库"
	@echo ""
	@echo "💡 搜索示例："
	@echo "  make search Q=\"机器学习\""
	@echo "  make search Q=\"深度学习\" FLAGS=\"--field transcript\""
	@echo "  make search-tags TAGS=\"教育 科技\""
	@echo "  make search-topics Q=\"神经网络\""
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 初始化环境（手动运行）
setup: ensure-venv
	@echo "🔧 重新初始化环境..."
	@echo "  → 更新 pip..."
	@$(PIP) install --upgrade pip setuptools wheel
	@echo "  → 安装/更新依赖..."
	@$(PIP) install -r requirements.txt
	@echo "  → 检查配置文件..."
	@if [ ! -f ".env" ]; then \
		echo "  ⚠️  .env 文件不存在，从模板创建..."; \
		cp .env.example .env 2>/dev/null || touch .env; \
		echo "  ⚠️  请编辑 .env 文件，填入你的 GROQ_API_KEY"; \
	fi
	@echo "  → 运行环境测试..."
	@$(PYTHON) test_env.py
	@echo ""
	@echo "✅ 环境初始化完成！"
	@echo "📝 下一步：编辑 .env 文件填入 API Key"
	@echo "   nano .env"

# 安装/更新依赖
install: ensure-venv
	@echo "📦 安装依赖..."
	@$(PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 运行环境测试
test: ensure-venv
	@echo "🧪 运行环境测试..."
	@$(PYTHON) test_env.py

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
run: ensure-venv
	@if [ -z "$(VIDEO)" ]; then \
		echo "❌ 错误：请指定视频路径"; \
		echo "用法：make run VIDEO=/path/to/video.mp4"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎬 处理视频（音频模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📹 视频: $(VIDEO)"
	@echo "🔊 流程: 音频提取 → Groq转写 → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@$(PYTHON) process_video.py "$(VIDEO)"
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
#   REC_MODEL=mobile|server  - 识别模型（默认 mobile）
#   USE_GPU=1                - 启用 GPU 加速
ocr: ensure-venv
	@if [ -z "$(VIDEO)" ]; then \
		echo "❌ 错误：请指定视频路径"; \
		echo "用法：make ocr VIDEO=/path/to/video.mp4"; \
		echo "可选：make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server"; \
		exit 1; \
	fi
	@DET=$${DET_MODEL:-mobile}; \
	REC=$${REC_MODEL:-mobile}; \
	GPU_FLAG=""; \
	if [ "$(USE_GPU)" = "1" ]; then GPU_FLAG="--use-gpu"; fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "🎬 处理视频（完整模式：OCR + 音频）"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 视频: $(VIDEO)"; \
	echo "🔍 流程: 1️⃣  OCR识别 → 2️⃣  音频转写 → 3️⃣  AI总结"; \
	echo "🤖 OCR模型: det=$$DET, rec=$$REC"; \
	echo "⏱️  注意：OCR 处理较慢，带进度条显示"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	$(PYTHON) process_video.py "$(VIDEO)" --with-frames --ocr-det-model $$DET --ocr-rec-model $$REC $$GPU_FLAG; \
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
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📥 下载视频"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "📁 存储位置: videos/"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) video_downloader.py "$(URL)"
	@echo ""
	@echo "✅ 下载完成！"

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
	@echo "🔊 流程: 下载 → 音频提取 → Groq转写 → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@# 下载视频并获取文件路径
	@$(PYTHON) video_downloader.py "$(URL)" > /tmp/download_output.txt 2>&1; \
	VIDEO_PATH=$$($(PYTHON) -c "import json,sys; line = open('/tmp/download_output.txt').readlines()[-1]; data = json.loads(line) if line.strip().startswith('{') else {}; print(data.get('file_path', ''))" 2>/dev/null); \
	if [ -z "$$VIDEO_PATH" ] || [ "$$VIDEO_PATH" = "null" ]; then \
		cat /tmp/download_output.txt | tail -20; \
		echo "❌ 下载失败"; \
		rm /tmp/download_output.txt; \
		exit 1; \
	fi; \
	rm /tmp/download_output.txt; \
	echo "✅ 下载完成: $$VIDEO_PATH"; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 开始处理视频"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	$(PYTHON) process_video.py "$$VIDEO_PATH"

# 下载视频后自动处理（完整OCR模式）
download-ocr: ensure-venv
	@if [ -z "$(URL)" ]; then \
		echo "❌ 错误：请指定视频URL"; \
		echo "用法：make download-ocr URL=https://example.com/video"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📥 下载并处理视频（完整模式）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔗 URL: $(URL)"
	@echo "📺 流程: 下载 → 抽帧 → OCR → ASR → AI总结"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@# 下载视频并获取文件路径
	@$(PYTHON) video_downloader.py "$(URL)" > /tmp/download_output.txt 2>&1; \
	VIDEO_PATH=$$($(PYTHON) -c "import json,sys; line = open('/tmp/download_output.txt').readlines()[-1]; data = json.loads(line) if line.strip().startswith('{') else {}; print(data.get('file_path', ''))" 2>/dev/null); \
	if [ -z "$$VIDEO_PATH" ] || [ "$$VIDEO_PATH" = "null" ]; then \
		cat /tmp/download_output.txt | tail -20; \
		echo "❌ 下载失败"; \
		rm /tmp/download_output.txt; \
		exit 1; \
	fi; \
	rm /tmp/download_output.txt; \
	echo "✅ 下载完成: $$VIDEO_PATH"; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 开始处理视频"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	DET_MODEL=$(DET_MODEL) REC_MODEL=$(REC_MODEL) USE_GPU=$(USE_GPU) \
	$(PYTHON) process_video.py "$$VIDEO_PATH" --with-frames

# 查看所有报告列表
list-reports:
	@if [ -d "output/reports" ]; then \
		echo "📋 报告列表:"; \
		ls -lht output/reports/*.txt 2>/dev/null || echo "  (无报告)"; \
	else \
		echo "ℹ️  output/reports/ 目录不存在"; \
	fi

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
	@echo "✅ 数据库初始化完成！"
	@echo "📂 数据库位置: storage/database/knowledge.db"

# 重建数据库（删除所有数据）
db-reset: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "⚠️  重建数据库（将删除所有数据）"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@read -p "确认删除所有数据？[y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(PYTHON) -m db.schema --force; \
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

# 测试数据库功能
db-test: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 测试数据库功能"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) test_database.py

# 导入真实数据测试
db-import-test: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 导入 output 目录真实数据测试"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) test_database_import.py

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
	@$(PYTHON) search_cli.py search "$(Q)" $(FLAGS)

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
	@$(PYTHON) search_cli.py tags --tags $(TAGS) --match-all

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
	@$(PYTHON) search_cli.py topics "$(Q)"

# 列出热门标签
db-tags: ensure-venv
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🏷️  热门标签"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTHON) search_cli.py list-tags --limit 50

# 列出所有视频（带标签和摘要）
db-list: ensure-venv
	@LIMIT=$${LIMIT:-20}; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📹 视频列表 (前 $$LIMIT 条)"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	$(PYTHON) search_cli.py list --limit $$LIMIT

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
