#!/bin/bash
echo "测试 OCR_WORKERS 参数传递"
echo "命令行: OCR_WORKERS=3 python -c 'import os; print(f\"环境变量值: {os.getenv(\"OCR_WORKERS\", \"未设置\")}\")';"
OCR_WORKERS=3 python -c 'import os; print(f"环境变量值: {os.getenv(\"OCR_WORKERS\", \"未设置\")}")'
echo "---"
echo "命令行: OCR_WORKERS=8 python -c ..."
OCR_WORKERS=8 python -c 'import os; print(f"环境变量值: {os.getenv(\"OCR_WORKERS\", \"未设置\")}")'
