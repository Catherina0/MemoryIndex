#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 初始化日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 加载配置
env_path = Path.home() / '.memoryindex' / '.env'
load_dotenv(env_path)
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = os.getenv("TG_ALLOWED_USER_ID", "").strip()

if not BOT_TOKEN:
    print("❌ 未配置 TG_BOT_TOKEN。")
    print("💡 请先运行: `make tg-bot-setup` 配置 Token")
    sys.exit(1)

def is_allowed_user(update: Update) -> bool:
    """检查用户是否在白名单中"""
    if not ALLOWED_USER_ID:
        return True # 未设置则不限制
    user_id = str(update.effective_user.id)
    return user_id == ALLOWED_USER_ID

async def check_auth(update: Update) -> bool:
    if not is_allowed_user(update):
        await update.message.reply_text("⛔️ 抱歉，这是一个私人的 MemoryIndex 助理。\n如果您也是项目所有者，请运行 `make tg-bot-setup` 绑定您的 User ID。")
        return False
    return True

async def send_long_message(update: Update, status_message, text: str, chunk_size: int = 3800):
    """将长文本拆分成多条消息发送，超过 chunk_size 的部分作为新消息 reply"""
    text = text.replace("```", "'''")
    # 按行拆分，尽量保持段落完整
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > chunk_size and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))

    if not chunks:
        chunks = ["✅ 执行完成。"]

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        header = f"📄 ({i+1}/{total})\n" if total > 1 else ""
        msg = f"```text\n{header}{chunk}\n```"
        if i == 0:
            await status_message.edit_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    if not await check_auth(update): return
    
    welcome_text = (
        "👋 欢迎使用 **MemoryIndex** 智能助理！\n\n"
        "🔗 **直接发我链接**：无论是网页、B站还是YouTube，我都会自动提取并索引到你的知识库中。\n"
        "🔍 **搜索知识库**：使用 `/search <关键词>` 开始搜索。\n"
        "ℹ️ **获取帮助**：发送 `/help` 查看详细使用指南。\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    if not await check_auth(update): return
    
    help_text = (
        "🤖 **MemoryIndex 智能助理使用指南**\n\n"
        "1️⃣ **自动归档 (最常用)**\n"
        "直接发送包含 `http` 的网页、Bilibili 或 YouTube 链接，我会自动分析内容并将其录入你的知识库。\n\n"
        "2️⃣ **知识库检索**\n"
        "`/search <关键词>` - 全文检索你的知识库，例如：`/search 强化学习`\n\n"
        "3️⃣ **高级处理命令 (类似 Makefile)**\n"
        "`/download_run <URL>` - 下载由于爬虫异常失效的视频并处理 (音频分析)\n"
        "`/download_ocr <URL>` - 下载视频并处理 (完整OCR和图像分析)\n"
        "`/archive_run <URL>` - 指定对一个网页进行长篇归档分析\n"
        "`/archive_ocr <URL>` - 归档带大量图片的网页并执行页面级OCR\n"
        "`/db_list` - 默认列出前 20 条\n"
        "`/db_list <页码>` - 翻页查看第 N 页 (例如: `/db_list 2`)\n"
        "`/db_show <ID>` - 从数据库根据ID显示明细\n"
        "`/db_stats` - 查看知识库存储统计\n"
        "`/make <参数>` - 极客模式：直接执行任意 make 命令 (例: `/make db-list LIMIT=50`)\n\n"
        "4️⃣ **URL 工具**\n"
        "`/url_clean <URL或文本>` - 展开短链接并去除追踪参数（淘宝/京东/小红书/B站/抖音等）\n\n"
        "5️⃣ **系统命令**\n"
        "`/start` - 显示欢迎信息\n"
        "`/help`  - 显示本帮助信息\n\n"
        "💡 _提示：直接分享浏览器的网页链接给我即可，无需加额外文字。_"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def search_knowledge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /search 命令"""
    if not await check_auth(update): return
    
    if not context.args:
        await update.message.reply_text("❌ 请提供关键词，例如: `/search 机器学习`", parse_mode="Markdown")
        return
        
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 正在从知识库中检索：`{query}` ...", parse_mode="Markdown")
    
    try:
        # 调用 MemoryIndex 的搜索 CLI
        result = subprocess.run(
            [sys.executable, "cli/main_cli.py", "search", query], 
            capture_output=True, text=True
        )
        
        # Telegram 单条消息限制 4096 字符
        output = result.stdout[:4000] if result.stdout.strip() else "没有找到相关内容。"
        await update.message.reply_text(f"```text\n{output}\n```", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"⚠️ 搜索出错: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理所有直接发送的文本文本"""
    if not await check_auth(update): return
    
    text = update.message.text.strip()
    
    # 简单校验是否包含 HTTP
    if "http" not in text:
        await update.message.reply_text("🤔 无法识别您的输入。发送包含 `http` 的链接让我帮你归档，使用 `/search` 搜索内容，或者发送 `/help` 查看帮助。")
        return

    # 提取文本中的链接
    url = next((word for word in text.split() if word.startswith("http")), text)

    status_message = await update.message.reply_text(f"⏳ 检测到链接，已唤醒 **MemoryIndex 代理**...\n正准备智能处理和归档中，这可能需要一点时间。")
    
    try:
        # 直接利用你现有的智能路由进行处理: python cli/main_cli.py <url>
        result = subprocess.run(
            [sys.executable, "cli/main_cli.py", url], 
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # 成功时截取有价值的结尾日志
            summary_lines = result.stdout.split("\n")
            summary = "\n".join(summary_lines[-15:])
            await status_message.edit_text(f"✅ **处理和归档成功！**\n```text\n{summary}\n```", parse_mode="Markdown")
        else:
            # 失败时输出最后错误信息
            err_log = "\n".join(result.stderr.split("\n")[-15:])
            if not err_log.strip():
                err_log = "\n".join(result.stdout.split("\n")[-15:])
            await status_message.edit_text(f"❌ **处理失败**\n```text\n{err_log}\n```", parse_mode="Markdown")
            
    except Exception as e:
        await status_message.edit_text(f"💣 系统出现异常: {e}")

async def run_make_target(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str, arg_name: str = None):
    """通用的 make 目标执行函数"""
    if not await check_auth(update): return
    
    args_str = " ".join(context.args)
    if arg_name and not args_str:
        await update.message.reply_text(f"❌ 命令缺少参数: 需要提供 `{arg_name}`\n用法: `/{target.replace('-', '_')} XXX`", parse_mode="Markdown")
        return
        
    cmd = ["make", target]
    if arg_name:
        cmd.append(f"{arg_name}={args_str}")
        
    status_message = await update.message.reply_text(f"⏳ 正在执行: `{' '.join(cmd)}` ...", parse_mode="Markdown")
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        output = (result.stdout + "\n" + result.stderr).strip().replace("```", "'''")
        if len(output) > 3800:
            output = "... (前面的输出被截断)\n" + output[-3800:]
        if not output: output = "✅ 执行完成。"
        await status_message.edit_text(f"```text\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await status_message.edit_text(f"⚠️ 执行出错: {e}")

async def cmd_download_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_make_target(update, context, "download-run", "URL")

async def cmd_download_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_make_target(update, context, "download-ocr", "URL")

async def cmd_archive_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_make_target(update, context, "archive-run", "URL")

async def cmd_archive_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_make_target(update, context, "archive-ocr", "URL")

async def cmd_db_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    if not context.args:
        # 默认第一页
        await run_make_target(update, context, "db-list", None)
    else:
        # 支持分页参数，比如 /db_list 2
        # 我们使用 make db-list PAGE=2 方式调用
        page = context.args[0]
        cmd = ["make", "db-list", f"PAGE={page}"]
        status_message = await update.message.reply_text(f"⏳ 正在执行: `{' '.join(cmd)}` ...", parse_mode="Markdown")
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, text=True,
                cwd=str(Path(__file__).parent.parent)
            )
            output = (result.stdout + "\n" + result.stderr).strip().replace("```", "'''")
            if len(output) > 3800:
                output = "... (前面的输出被截断)\n" + output[-3800:]
            if not output: output = "✅ 执行完成。"
            await status_message.edit_text(f"```text\n{output}\n```", parse_mode="Markdown")
        except Exception as e:
            await status_message.edit_text(f"⚠️ 执行出错: {e}")

async def cmd_db_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("❌请提供 ID。例如: `/db_show 43`", parse_mode="Markdown")
        return
        
    cmd = ["make", "db-show", f"ID={context.args[0]}"]
    if len(context.args) > 1:
        cmd.append(f"FILE={context.args[1]}")
        
    status_message = await update.message.reply_text(f"⏳ 正在执行: `{' '.join(cmd)}` ...", parse_mode="Markdown")
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        if not output: output = "✅ 执行完成。"
        await send_long_message(update, status_message, output)
    except Exception as e:
        await status_message.edit_text(f"⚠️ 执行出错: {e}")

async def cmd_db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_make_target(update, context, "db-stats", None)

async def cmd_url_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /url_clean 命令：展开短链接 + 去除追踪参数，单独发送可复制链接"""
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text(
            "❌ 请提供链接或包含链接的文本。\n"
            "用法: `/url_clean <URL或文本>`",
            parse_mode="Markdown"
        )
        return

    status_message = await update.message.reply_text("⏳ 正在处理链接...", parse_mode="Markdown")
    try:
        # 调用模块获取结构化结果
        repo_root = str(Path(__file__).parent.parent)
        sys.path.insert(0, repo_root)
        from scripts.url_cleaner import clean_url

        raw = " ".join(context.args)
        result = clean_url(raw)

        if 'error' in result:
            await status_message.edit_text(f"❌ {result['error']}")
            return

        original = result['original']
        expanded = result['expanded']
        cleaned  = result['cleaned']

        # 第一条：处理摘要
        lines = []
        if expanded != original:
            lines.append(f"🔄 短链接已还原")
            lines.append(f"原始: {original}")
        if cleaned != expanded:
            lines.append(f"🧹 已去除追踪参数")
        if cleaned == original:
            lines.append("✅ 链接无需变更")
        summary = "\n".join(lines) if lines else "✅ 处理完成"
        await status_message.edit_text(summary)

        # 第二条：清理后的链接，独立 code 块，点击即可复制
        await update.message.reply_text(
            f"`{cleaned}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_message.edit_text(f"⚠️ 执行出错: {e}")

async def cmd_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理动态 make 命令 /make target xxx=yyy """
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("❌ 请提供 make 参数，例如: `/make db-stats`", parse_mode="Markdown")
        return
        
    cmd = ["make"] + context.args
    status_message = await update.message.reply_text(f"⏳ 正在执行: `{' '.join(cmd)}` ...", parse_mode="Markdown")
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        output = (result.stdout + "\n" + result.stderr).strip().replace("```", "'''")
        if len(output) > 3800:
            output = "... (前面的输出被截断)\n" + output[-3800:]
        if not output: output = "✅ 执行完成。"
        await status_message.edit_text(f"```text\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await status_message.edit_text(f"⚠️ 执行出错: {e}")

async def post_init(application):
    """设置 Telegram 快捷命令菜单"""
    commands = [
        BotCommand("start", "👋 欢迎与系统菜单"),
        BotCommand("help", "ℹ️ 帮助与使用指南"),
        BotCommand("search", "🔍 搜索知识库 (例如 /search AI)"),
        BotCommand("db_list", "📋 列出数据库内容 (可加页码, 例如 /db_list 2)"),
        BotCommand("db_show", "📄 查看文档/视频详细内容 (/db_show <ID>)"),
        BotCommand("db_stats", "📊 查看知识库存储统计数据"),
        BotCommand("download_run", "▶️ 下载视频并处理文本"),
        BotCommand("download_ocr", "▶️ 下载视频并处理文本与图像"),
        BotCommand("archive_run", "🌐 完整归档单个长网页"),
        BotCommand("archive_ocr", "🌐 归档网页并进行版面OCR"),
        BotCommand("url_clean", "🔗 展开短链接 & 去除追踪参数"),
        BotCommand("make", "🛠️ 极客模式: 直接执行 Makefile 命令")
    ]
    await application.bot.set_my_commands(commands)
    print("✅ 已成功向 Telegram 注册快捷指令菜单！用户可以在输入框左边看到 [/] 按钮了。")

def main():
    print("🤖 MemoryIndex Telegram Bot 已启动，正在轮询消息...")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    # 注册路由
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_knowledge))

    # 注册高级 Make 命令
    app.add_handler(CommandHandler("download_run", cmd_download_run))
    app.add_handler(CommandHandler("download_ocr", cmd_download_ocr))
    app.add_handler(CommandHandler("archive_run", cmd_archive_run))
    app.add_handler(CommandHandler("archive_ocr", cmd_archive_ocr))
    app.add_handler(CommandHandler("db_list", cmd_db_list))
    app.add_handler(CommandHandler("db_show", cmd_db_show))
    app.add_handler(CommandHandler("db_stats", cmd_db_stats))
    app.add_handler(CommandHandler("url_clean", cmd_url_clean))
    app.add_handler(CommandHandler("make", cmd_make))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    app.run_polling()

if __name__ == '__main__':
    main()
