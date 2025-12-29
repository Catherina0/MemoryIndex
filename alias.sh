#!/bin/bash
# MemoryIndex Shell 别名和函数
# 
# 用法：将以下内容添加到你的 ~/.zshrc 或 ~/.bashrc
# 或者直接运行：source alias.sh

# ============================================
# 基础别名
# ============================================

# 简短别名
alias mi-s='mi search'
alias mi-l='mi list'
alias mi-t='mi topics'
alias mi-tag='mi tags'

# ============================================
# 便捷函数
# ============================================

# 快速搜索并打开结果
mis() {
    if [ -z "$1" ]; then
        echo "用法: mis <关键词>"
        return 1
    fi
    mi search "$@"
}

# 搜索转写内容
mit() {
    if [ -z "$1" ]; then
        echo "用法: mit <关键词>"
        return 1
    fi
    mi search "$1" --field transcript
}

# 搜索 OCR 内容
mio() {
    if [ -z "$1" ]; then
        echo "用法: mio <关键词>"
        return 1
    fi
    mi search "$1" --field ocr
}

# 处理视频并自动搜索
mip() {
    if [ -z "$1" ]; then
        echo "用法: mip <视频文件>"
        return 1
    fi
    mi-process "$1" && echo "处理完成！你现在可以搜索内容了。"
}

# 列出最近的视频
mi-recent() {
    mi list --limit "${1:-10}" --sort-by date --desc
}

# 快速查看视频详情
mid() {
    if [ -z "$1" ]; then
        echo "用法: mid <视频ID>"
        return 1
    fi
    mi show "$1"
}

# 按标签搜索
mi-tag-search() {
    if [ -z "$1" ]; then
        echo "用法: mi-tag-search <标签1> [标签2] ..."
        return 1
    fi
    mi tags --tags "$@"
}

# 查看热门标签
mi-hot-tags() {
    mi list-tags --limit "${1:-20}"
}

# ============================================
# 高级功能
# ============================================

# 下载并处理视频
mi-dl-process() {
    if [ -z "$1" ]; then
        echo "用法: mi-dl-process <URL>"
        return 1
    fi
    
    echo "→ 下载视频..."
    if mi-download "$1"; then
        echo "→ 开始处理..."
        # 找到最新下载的视频
        latest_video=$(ls -t videos/*.mp4 | head -1)
        if [ -n "$latest_video" ]; then
            mi-process "$latest_video"
            echo "✅ 完成！现在可以搜索内容了。"
        else
            echo "❌ 未找到下载的视频"
            return 1
        fi
    else
        echo "❌ 下载失败"
        return 1
    fi
}

# 批量处理视频
mi-batch() {
    if [ -z "$1" ]; then
        echo "用法: mi-batch <视频目录>"
        return 1
    fi
    
    for video in "$1"/*.mp4; do
        if [ -f "$video" ]; then
            echo "→ 处理: $video"
            mi-process "$video"
        fi
    done
    echo "✅ 批量处理完成！"
}

# 搜索并导出结果
mi-export() {
    if [ -z "$1" ]; then
        echo "用法: mi-export <关键词> [输出文件]"
        return 1
    fi
    
    output_file="${2:-search_results.txt}"
    mi search "$1" > "$output_file"
    echo "✅ 结果已导出到: $output_file"
}

# ============================================
# 开发和调试
# ============================================

# 重新加载 MemoryIndex（开发模式）
mi-reload() {
    echo "→ 重新加载 MemoryIndex..."
    cd ~/Documents/GitHub/knowledge || return 1
    pip install -e . --quiet
    echo "✅ 重新加载完成"
    cd - > /dev/null || return 0
}

# 查看 MemoryIndex 状态
mi-status() {
    echo "MemoryIndex 状态:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "命令位置: $(which mi)"
    echo "Python 版本: $(python3 --version)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "视频总数:"
    mi list --limit 1 | tail -1
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ============================================
# 帮助信息
# ============================================

mi-help-aliases() {
    cat << 'EOF'
MemoryIndex 别名和函数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

基础别名:
  mi-s           → mi search
  mi-l           → mi list
  mi-t           → mi topics
  mi-tag         → mi tags

便捷函数:
  mis <关键词>                     快速搜索
  mit <关键词>                     搜索转写内容
  mio <关键词>                     搜索 OCR 内容
  mip <视频文件>                   处理视频
  mi-recent [数量]                 列出最近视频
  mid <ID>                         查看视频详情
  mi-tag-search <标签...>         按标签搜索
  mi-hot-tags [数量]              查看热门标签

高级功能:
  mi-dl-process <URL>             下载并处理视频
  mi-batch <目录>                 批量处理视频
  mi-export <关键词> [文件]       导出搜索结果

开发和调试:
  mi-reload                       重新加载 MemoryIndex
  mi-status                       查看状态

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# 打印欢迎信息
echo "✅ MemoryIndex 别名已加载"
echo "💡 输入 'mi-help-aliases' 查看所有可用命令"
