#!/usr/bin/env python3
"""
定时任务示例 - 使用 DrissionPage 浏览器单例

演示如何在定时任务（如 cron job）中使用浏览器单例：
- 程序启动时创建浏览器实例
- 定时执行归档任务
- 每个任务使用新标签页
- 程序退出时关闭浏览器
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.core.drission_crawler import DrissionArchiver
from archiver.utils.browser_manager import cleanup_browser
import schedule
import time
import logging
import signal
import atexit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
archiver = None
running = True


def init_archiver():
    """初始化归档器"""
    global archiver
    logger.info("初始化归档器...")
    archiver = DrissionArchiver(
        output_dir="archived",
        browser_data_dir="./browser_data",
        headless=True,
        verbose=True
    )
    logger.info("✓ 归档器已初始化")


def cleanup():
    """清理资源"""
    global archiver
    logger.info("清理资源...")
    if archiver:
        archiver.close()
    cleanup_browser()
    logger.info("✓ 清理完成")


def signal_handler(signum, frame):
    """处理退出信号"""
    global running
    logger.info(f"收到退出信号 ({signum})，准备退出...")
    running = False


# 注册清理和信号处理
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def archive_task(url: str):
    """
    归档任务
    
    Args:
        url: 要归档的 URL
    """
    try:
        logger.info(f"开始归档任务: {url}")
        result = archiver.archive(url)
        
        if result['success']:
            logger.info(f"✓ 归档成功: {url}")
            logger.info(f"  输出路径: {result.get('output_path')}")
        else:
            logger.error(f"✗ 归档失败: {url} - {result.get('error')}")
    
    except Exception as e:
        logger.error(f"归档任务出错: {url} - {e}", exc_info=True)


def hourly_job():
    """每小时执行的任务"""
    logger.info("=" * 60)
    logger.info("执行每小时任务")
    logger.info("=" * 60)
    
    # 示例：归档多个 URL
    urls = [
        "https://www.zhihu.com/question/123456789",
        "https://www.zhihu.com/question/987654321",
    ]
    
    for url in urls:
        archive_task(url)
        time.sleep(2)  # 任务间隔


def daily_job():
    """每天执行的任务"""
    logger.info("=" * 60)
    logger.info("执行每日任务")
    logger.info("=" * 60)
    
    # 示例：归档重要内容
    urls = [
        "https://www.zhihu.com/question/important1",
        "https://www.zhihu.com/question/important2",
    ]
    
    for url in urls:
        archive_task(url)
        time.sleep(2)


def example_1_simple_schedule():
    """
    示例 1: 简单定时任务
    """
    logger.info("启动简单定时任务...")
    
    # 每 5 分钟执行一次
    schedule.every(5).minutes.do(hourly_job)
    
    # 每天 8:00 执行
    schedule.every().day.at("08:00").do(daily_job)
    
    logger.info("定时任务已配置:")
    logger.info("  - 每 5 分钟: hourly_job")
    logger.info("  - 每天 8:00: daily_job")
    logger.info()
    
    # 运行调度器
    while running:
        schedule.run_pending()
        time.sleep(1)


def example_2_dynamic_schedule():
    """
    示例 2: 动态任务调度
    """
    logger.info("启动动态任务调度...")
    
    # 任务队列（可以从数据库、配置文件等加载）
    task_queue = [
        {"url": "https://www.zhihu.com/question/111", "interval_minutes": 10},
        {"url": "https://www.zhihu.com/question/222", "interval_minutes": 30},
        {"url": "https://www.zhihu.com/question/333", "interval_minutes": 60},
    ]
    
    # 为每个 URL 配置定时任务
    for task in task_queue:
        url = task['url']
        interval = task['interval_minutes']
        
        # 创建任务函数（使用闭包捕获 url）
        def make_job(url):
            return lambda: archive_task(url)
        
        schedule.every(interval).minutes.do(make_job(url))
        logger.info(f"  - {url}: 每 {interval} 分钟")
    
    logger.info()
    
    # 运行调度器
    while running:
        schedule.run_pending()
        time.sleep(1)


def example_3_one_time_batch():
    """
    示例 3: 一次性批量任务
    """
    logger.info("执行一次性批量任务...")
    
    # 从文件读取 URL 列表
    urls_file = Path("urls_to_archive.txt")
    
    if not urls_file.exists():
        logger.warning(f"URL 列表文件不存在: {urls_file}")
        # 使用示例 URLs
        urls = [
            "https://www.zhihu.com/question/123456789",
            "https://www.zhihu.com/question/987654321",
            "https://www.zhihu.com/question/555555555",
        ]
    else:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"共 {len(urls)} 个 URL 待归档")
    
    success_count = 0
    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] {url}")
        archive_task(url)
        success_count += 1
        time.sleep(2)  # 避免请求过快
    
    logger.info(f"批量任务完成: {success_count}/{len(urls)}")


def main():
    """主函数"""
    print("=" * 60)
    print("定时任务示例 - DrissionPage 浏览器单例")
    print("=" * 60)
    print()
    
    # 初始化归档器
    init_archiver()
    
    print()
    print("选择运行模式：")
    print("  1. 简单定时任务（每 5 分钟 + 每天 8:00）")
    print("  2. 动态任务调度（不同 URL 不同频率）")
    print("  3. 一次性批量任务")
    print()
    
    # 这里可以根据命令行参数选择模式
    # 示例：直接运行模式 3
    mode = 3
    
    try:
        if mode == 1:
            example_1_simple_schedule()
        elif mode == 2:
            example_2_dynamic_schedule()
        elif mode == 3:
            example_3_one_time_batch()
        else:
            logger.error("无效的模式")
    
    except KeyboardInterrupt:
        logger.info("收到中断信号，退出...")
    
    finally:
        logger.info("程序退出")


if __name__ == '__main__':
    main()
