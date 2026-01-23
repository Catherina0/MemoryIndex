#!/usr/bin/env python3
"""修复 Unicode 转义字符"""
import re

# 读取文件
with open('core/archive_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 计数
unicode_escapes = re.findall(r'\\u[0-9a-fA-F]{4}', content)
print(f"找到 {len(unicode_escapes)} 个 Unicode 转义字符")

# 替换所有 \uXXXX 格式的字符
new_content = re.sub(
    r'\\u([0-9a-fA-F]{4})', 
    lambda m: chr(int(m.group(1), 16)), 
    content
)

# 写回文件
with open('core/archive_processor.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ 已修复所有 Unicode 转义字符")

# 验证
with open('core/archive_processor.py', 'r', encoding='utf-8') as f:
    check_content = f.read()

remaining = re.findall(r'\\u[0-9a-fA-F]{4}', check_content)
print(f"剩余转义字符: {len(remaining)}")

# 显示修复后的前几行
print("\n修复后的内容示例：")
for i, line in enumerate(check_content.split('\n')[28:38], 29):
    print(f"{i}: {line}")
