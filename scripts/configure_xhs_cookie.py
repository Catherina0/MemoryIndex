#!/usr/bin/env python3
"""
XHS-Downloader Cookie 配置工具
用于配置小红书下载器的 Cookie
"""

import json
from pathlib import Path


def configure_cookie():
    """交互式配置 Cookie"""
    
    print("=" * 60)
    print("🍪 小红书 Cookie 配置工具")
    print("=" * 60)
    print()
    
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "XHS-Downloader" / "Volume" / "settings.json"
    
    # 检查配置文件是否存在
    if not config_path.exists():
        print("❌ 错误：配置文件不存在")
        print(f"   路径：{config_path}")
        return
    
    # 读取当前配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败：{e}")
        return
    
    # 显示当前配置
    current_cookie = config.get('cookie', '')
    if current_cookie:
        print(f"✅ 当前已配置 Cookie（前30字符）：{current_cookie[:30]}...")
        print()
        update = input("是否更新 Cookie？(y/n): ").strip().lower()
        if update != 'y':
            print("取消配置")
            return
    else:
        print("⚠️  当前未配置 Cookie")
    
    print()
    print("📝 如何获取 Cookie：")
    print()
    print("1. 打开浏览器访问：https://www.xiaohongshu.com/explore")
    print("2. 登录你的小红书账号")
    print("3. 按 F12 打开开发者工具")
    print("4. 点击 'Network'（网络）标签")
    print("5. 刷新页面（F5）")
    print("6. 点击任意请求，找到 'Request Headers'")
    print("7. 复制完整的 Cookie 值")
    print()
    print("详细教程：docs/XHS_COOKIE_SETUP.md")
    print()
    print("=" * 60)
    print()
    
    # 输入 Cookie
    print("请粘贴你的 Cookie（按 Enter 结束）：")
    cookie = input().strip()
    
    if not cookie:
        print("❌ Cookie 不能为空")
        return
    
    # 基本验证
    if 'web_session' not in cookie:
        print()
        print("⚠️  警告：Cookie 中没有找到 'web_session' 字段")
        print("   这可能不是有效的小红书 Cookie")
        print()
        proceed = input("是否继续配置？(y/n): ").strip().lower()
        if proceed != 'y':
            print("取消配置")
            return
    
    # 更新配置
    config['cookie'] = cookie
    
    # 同时更新 User-Agent
    if not config.get('user_agent'):
        config['user_agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    
    # 保存配置
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        print()
        print("=" * 60)
        print("✅ Cookie 配置成功！")
        print("=" * 60)
        print()
        print("📊 配置信息：")
        print(f"   Cookie 长度：{len(cookie)} 字符")
        print(f"   配置文件：{config_path}")
        print()
        print("🧪 测试下载：")
        print('   make download URL="https://www.xiaohongshu.com/explore/xxx"')
        print()
        
    except Exception as e:
        print(f"❌ 保存配置失败：{e}")
        return


if __name__ == "__main__":
    try:
        configure_cookie()
    except KeyboardInterrupt:
        print("\n\n取消配置")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
