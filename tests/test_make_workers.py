#!/usr/bin/env python3
"""模拟 process_video.py 调用 ocr_parallel 的场景"""

import os
import sys

# 模拟读取环境变量
env_workers = os.environ.get('OCR_WORKERS', '未设置')
print(f"DEBUG: 环境变量 OCR_WORKERS = '{env_workers}'")

# 模拟 ocr_parallel.py 的逻辑
num_workers = None
if env_workers != '未设置' and env_workers.lower() != 'auto':
    try:
        num_workers = int(env_workers)
        print(f"DEBUG: 成功转换为整数 = {num_workers}")
    except ValueError:
        print(f"DEBUG: 转换失败")
        pass

if num_workers is None:
    from multiprocessing import cpu_count
    total_cores = cpu_count()
    num_workers = max(1, total_cores // 2)
    print(f"DEBUG: 使用默认值 = {num_workers} (CPU={total_cores})")

print(f"\n🔧 工作进程: {num_workers}")
