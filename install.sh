#!/usr/bin/env bash

# 出错时退出
set -e

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

echo -e "${GREEN}🚀 开始一键安装并初始化 MemoryIndex...${NC}\n"

# 检测是否在 macOS 环境
if [[ $(uname) != "Darwin" ]]; then
    echo -e "${RED}❌ 错误: 此脚本专为 macOS 设计。${NC}"
    exit 1
fi

# ==========================================
# 如果是通过 curl | bash 运行的，则先 Clone 仓库
# 检测是否在 git 仓库内部
# ==========================================
if [ ! -d ".git" ] || ! grep -q "MemoryIndex" <<< "$(git remote -v 2>/dev/null)"; then
    echo -e "${YELLOW}📥 正在克隆 MemoryIndex 仓库到当前目录...${NC}"
    if [ -d "MemoryIndex" ]; then
        echo -e "${YELLOW}⚠️  目录 MemoryIndex 已存在，正在进入目录...${NC}"
    else
        git clone https://github.com/Catherina0/MemoryIndex.git
    fi
    cd MemoryIndex
    echo -e "✅ 已进入项目目录: $(pwd)\n"
fi

echo -e "${YELLOW}1. 检查环境变量和工具...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Homebrew。${NC}"
    echo -e "请先安装 Homebrew: ${BLUE}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
    exit 1
fi

echo "正在通过 Homebrew 检查系统依赖 (ffmpeg, python3)..."
brew install -q ffmpeg python@3.11 || true
echo -e "✅ 系统依赖就绪 (ffmpeg, python3)\n"

echo -e "${YELLOW}2. 创建并激活虚拟环境...${NC}"
if [ -d ".venv" ]; then
    echo "发现现有 .venv，清理重建中..."
    rm -rf .venv
fi
python3 -m venv .venv
export VIRTUAL_ENV="$(pwd)/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
echo -e "✅ 虚拟环境创建并激活完毕\n"

echo -e "${YELLOW}3. 更新 pip 并安装基础依赖...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo -e "✅ 依赖安装完毕\n"

echo -e "${YELLOW}4. 安装和初始化 Playwright 浏览器依赖 (用于网页爬虫)...${NC}"
python3 -m playwright install --with-deps chromium
echo -e "✅ Playwright 初始化完毕\n"

echo -e "${YELLOW}5. 初始化数据库与搜索引擎...${NC}"
python3 -m db.schema || echo -e "${YELLOW}⚠️ DB 初始化部分提示 (可忽略)${NC}"
python3 -c "from db.whoosh_search import get_whoosh_index; get_whoosh_index()" || echo -e "${YELLOW}⚠️ 搜索索引初始化部分提示 (可忽略)${NC}"
echo -e "✅ 数据库创建完毕\n"

echo -e "${YELLOW}6. 检查配置文件 (.env)...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "✅ 已根据模板生成 .env 文件。"
    else
        touch .env
        echo "GROQ_API_KEY=" >> .env
        echo "GEMINI_API_KEY=" >> .env
        echo -e "✅ 已生成空 .env 文件。"
    fi
    echo -e "${RED}⚠️ 注意: 请一定要编辑 .env 文件，填入你的 GROQ_API_KEY 和 GEMINI_API_KEY！${NC}\n"
else
    echo -e "✅ .env 已经存在\n"
fi

echo -e "${YELLOW}7. 运行依赖测试...${NC}"
if [ -f "tests/test_env.py" ]; then
    python3 tests/test_env.py || true
else
    make check || true
fi
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 安装流程已执行完毕！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "👉 请手动运行以下命令激活虚拟环境（如果你打开了新终端）："
echo -e "   ${YELLOW}source .venv/bin/activate${NC}"
echo -e ""
echo -e "👉 若想测试，准备工作完成后可执行："
echo -e "   ${YELLOW}make download-run URL=\"[你的视频链接]\"${NC}"
echo -e "   或"
echo -e "   ${YELLOW}make db-list${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
