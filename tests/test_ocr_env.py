#!/usr/bin/env python3
"""测试 OCR_WORKERS 环境变量传递"""

import os
import sys
from multiprocessing import cpu_count

def main():
    print("\n" + "="*50)
    print("🧪 OCR_WORKERS 环境变量测试")
    print("="*50)
    
    # 读取环境变量
    env_value = os.environ.get('OCR_WORKERS', '未设置')
    print(f"\n1️⃣  环境变量原始值: {env_value}")
    print(f"   类型: {type(env_value)}")
    
    # 模拟 ocr_parallel.py 的逻辑
    num_workers = None
    
    if env_value != '未设置' and env_value.lower() != 'auto':
        try:
            num_workers = int(env_value)
            print(f"\n2️⃣  转换为整数: {num_workers} ✅")
        except ValueError as e:
            print(f"\n2️⃣  转换失败: {e} ❌")
    else:
        print(f"\n2️⃣  值为 'auto' 或未设置")
    
    # 默认值
    if num_workers is None:
        total_cores = cpu_count()
        num_workers = max(1, total_cores // 2)
        print(f"\n3️⃣  使用默认值: {num_workers}")
        print(f"   (CPU核心数: {total_cores}, 使用一半)")
    else:
        print(f"\n3️⃣  使用用户指定值: {num_workers}")
    
    print(f"\n✅ 最终工作进程数: {num_workers}")
    print("="*50 + "\n")
    
    return num_workers

if __name__ == '__main__':
    result = main()
    sys.exit(0)
