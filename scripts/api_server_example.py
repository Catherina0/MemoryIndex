#!/usr/bin/env python3
"""
Flask API 服务示例 - 使用 DrissionPage 浏览器单例

演示如何在 Web API 中使用浏览器单例：
- 服务启动时创建浏览器实例
- 每个请求使用新标签页
- 请求结束关闭标签页
- 服务关闭时关闭浏览器
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from archiver.core.drission_crawler import DrissionArchiver
from archiver.utils.browser_manager import cleanup_browser
import atexit
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)

# 全局归档器实例（使用浏览器单例）
archiver = None


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
    if archiver:
        logger.info("清理归档器...")
        archiver.close()
    logger.info("清理浏览器...")
    cleanup_browser()
    logger.info("✓ 清理完成")


# 注册清理函数
atexit.register(cleanup)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    from archiver.utils.browser_manager import get_browser_manager
    manager = get_browser_manager()
    
    return jsonify({
        'status': 'ok',
        'browser_alive': manager.is_alive()
    })


@app.route('/archive', methods=['POST'])
def archive_url():
    """
    归档网页
    
    请求格式：
    {
        "url": "https://www.zhihu.com/question/123456789",
        "mode": "default"  # 可选：default 或 full
    }
    """
    try:
        # 获取请求参数
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少 URL 参数'
            }), 400
        
        url = data['url']
        mode = data.get('mode', 'default')
        
        logger.info(f"收到归档请求: {url}")
        
        # 执行归档（每个请求使用新标签页）
        result = archiver.archive(url, mode=mode)
        
        if result['success']:
            logger.info(f"归档成功: {url}")
            return jsonify(result), 200
        else:
            logger.warning(f"归档失败: {url} - {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"处理请求时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/batch-archive', methods=['POST'])
def batch_archive():
    """
    批量归档网页
    
    请求格式：
    {
        "urls": [
            "https://www.zhihu.com/question/123456789",
            "https://www.zhihu.com/question/987654321"
        ],
        "mode": "default"
    }
    """
    try:
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({
                'success': False,
                'error': '缺少 URLs 参数'
            }), 400
        
        urls = data['urls']
        mode = data.get('mode', 'default')
        
        if not isinstance(urls, list):
            return jsonify({
                'success': False,
                'error': 'URLs 必须是数组'
            }), 400
        
        logger.info(f"收到批量归档请求: {len(urls)} 个 URL")
        
        # 执行批量归档
        results = []
        for url in urls:
            try:
                result = archiver.archive(url, mode=mode)
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'url': url,
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r.get('success'))
        logger.info(f"批量归档完成: {success_count}/{len(urls)} 成功")
        
        return jsonify({
            'success': True,
            'total': len(urls),
            'success_count': success_count,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"处理批量请求时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def main():
    """启动服务"""
    print("=" * 60)
    print("Flask API 服务 - DrissionPage 浏览器单例")
    print("=" * 60)
    print()
    print("启动中...")
    
    # 初始化归档器
    init_archiver()
    
    print()
    print("服务已启动！")
    print()
    print("API 端点：")
    print("  GET  /health         - 健康检查")
    print("  POST /archive        - 归档单个URL")
    print("  POST /batch-archive  - 批量归档")
    print()
    print("示例请求：")
    print('  curl -X POST http://localhost:5000/archive \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"url": "https://www.zhihu.com/question/123456789"}\'')
    print()
    print("=" * 60)
    print()
    
    # 启动服务
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False  # 生产环境设置为 False
    )


if __name__ == '__main__':
    main()
