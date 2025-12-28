#!/usr/bin/env python3
"""
GPU加速测试脚本
测试OCR模块的GPU加速功能
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ocr.ocr_utils import init_ocr, check_gpu_available

def test_gpu_detection():
    """测试GPU检测功能"""
    print("=" * 70)
    print("🔍 GPU 检测测试")
    print("=" * 70)
    
    gpu_available = check_gpu_available()
    
    if gpu_available:
        print("✅ GPU 可用！将使用GPU加速")
    else:
        print("❌ GPU 不可用，将使用CPU模式")
    
    return gpu_available


def test_ocr_performance(image_path, use_gpu=None):
    """测试OCR性能（CPU vs GPU）"""
    if not Path(image_path).exists():
        print(f"❌ 测试图片不存在: {image_path}")
        return
    
    print("\n" + "=" * 70)
    print(f"⚡ OCR 性能测试: {'GPU模式' if use_gpu else 'CPU模式'}")
    print("=" * 70)
    
    # 初始化OCR
    print("\n>> 初始化OCR模型...")
    start_init = time.time()
    ocr = init_ocr(lang='ch', use_gpu=use_gpu)
    init_time = time.time() - start_init
    print(f"   初始化耗时: {init_time:.2f}秒")
    
    # 执行OCR识别
    print(f"\n>> 识别图片: {image_path}")
    start_ocr = time.time()
    result = ocr.ocr(image_path)
    ocr_time = time.time() - start_ocr
    
    # 统计结果
    text_count = 0
    if result and len(result) > 0:
        item = result[0]
        if isinstance(item, dict):
            text_count = len(item.get('rec_texts', []))
    
    print(f"   识别耗时: {ocr_time:.2f}秒")
    print(f"   识别到 {text_count} 条文本")
    
    return {
        'mode': 'GPU' if use_gpu else 'CPU',
        'init_time': init_time,
        'ocr_time': ocr_time,
        'text_count': text_count,
        'total_time': init_time + ocr_time
    }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GPU加速测试脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'image',
        nargs='?',
        help='测试图片路径（可选，如果不提供则只进行GPU检测）'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='对比CPU和GPU性能（需要提供测试图片）'
    )
    
    args = parser.parse_args()
    
    # GPU检测
    gpu_available = test_gpu_detection()
    
    # 如果没有提供图片，只进行GPU检测
    if not args.image:
        print("\n💡 提示: 使用 --help 查看完整用法")
        return
    
    # 性能测试
    if args.compare and gpu_available:
        print("\n" + "🏁" * 35)
        print("开始CPU vs GPU性能对比测试")
        print("🏁" * 35)
        
        # CPU测试
        cpu_result = test_ocr_performance(args.image, use_gpu=False)
        
        # GPU测试
        gpu_result = test_ocr_performance(args.image, use_gpu=True)
        
        # 对比结果
        print("\n" + "=" * 70)
        print("📊 性能对比结果")
        print("=" * 70)
        print(f"{'模式':<10} {'初始化':<12} {'识别':<12} {'总耗时':<12} {'加速比'}")
        print("-" * 70)
        print(f"{'CPU':<10} {cpu_result['init_time']:>8.2f}秒   {cpu_result['ocr_time']:>8.2f}秒   {cpu_result['total_time']:>8.2f}秒   {'1.00x'}")
        speedup = cpu_result['total_time'] / gpu_result['total_time']
        print(f"{'GPU':<10} {gpu_result['init_time']:>8.2f}秒   {gpu_result['ocr_time']:>8.2f}秒   {gpu_result['total_time']:>8.2f}秒   {speedup:.2f}x")
        print("=" * 70)
        print(f"\n🚀 GPU相比CPU快 {speedup:.2f} 倍")
        
    else:
        # 单次测试（自动检测GPU）
        test_ocr_performance(args.image, use_gpu=gpu_available if not args.compare else True)
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    main()
