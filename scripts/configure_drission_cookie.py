#!/usr/bin/env python3
"""
DrissionPage 手动 Cookie 配置工具
用于配置浏览器登录态（当 make login 失败时使用）
"""

import json
import sys
from pathlib import Path


def configure_cookie():
    """交互式配置 Cookie 到 browser_data"""
    
    print("=" * 60)
    print("🍪 DrissionPage 手动 Cookie 配置")
    print("=" * 60)
    print()
    print("⚠️  使用场景：当 'make login' 无法正常工作时")
    print("✅ 推荐优先使用：make login（自动浏览器登录）")
    print()
    
    # 选择平台
    print("请选择平台：")
    print("  1. 知乎 (zhihu.com)")
    print("  2. 小红书 (xiaohongshu.com)")
    print("  3. B站 (bilibili.com)")
    print()
    
    choice = input("请输入选项 (1-3): ").strip()
    
    platform_map = {
        "1": ("zhihu", "知乎", "https://www.zhihu.com", ".zhihu.com", "z_c0"),
        "2": ("xiaohongshu", "小红书", "https://www.xiaohongshu.com", ".xiaohongshu.com", "web_session"),
        "3": ("bilibili", "B站", "https://www.bilibili.com", ".bilibili.com", "SESSDATA"),
    }
    
    if choice not in platform_map:
        print("❌ 无效选项")
        return
    
    platform_id, platform_name, platform_url, platform_domain, key_cookie = platform_map[choice]
    
    print()
    print(f"平台: {platform_name}")
    print(f"URL: {platform_url}")
    print()
    
    # 配置文件路径
    config_dir = Path(__file__).parent.parent / "archiver" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{platform_id}_drission_cookie.txt"
    
    # 检查现有配置
    if config_path.exists():
        print(f"✅ 当前已配置 Cookie")
        print()
        update = input("是否更新 Cookie？(y/n): ").strip().lower()
        if update != 'y':
            print("取消配置")
            return
    else:
        print("⚠️  当前未配置 Cookie")
    
    print()
    print("=" * 60)
    print("📝 如何获取 Cookie：")
    print("=" * 60)
    print("1. 打开浏览器（Chrome/Firefox/Safari）")
    print(f"2. 访问并登录：{platform_url}")
    print("3. 按 F12 打开开发者工具")
    print("4. 点击 'Application' 或 'Storage' 标签")
    print("5. 展开 'Cookies' → 选择对应域名")
    print(f"6. 找到并复制关键 Cookie：{key_cookie}")
    print()
    
    if platform_id == "zhihu":
        print("💡 知乎关键 Cookie：")
        print("   - z_c0：主要认证 Cookie")
        print("   - _xsrf：CSRF 令牌")
        print("   格式：z_c0=xxx; _xsrf=yyy")
    elif platform_id == "xiaohongshu":
        print("💡 小红书关键 Cookie：")
        print("   - web_session：主要认证 Cookie")
        print("   - a1：设备标识")
        print("   格式：web_session=xxx; a1=yyy")
    elif platform_id == "bilibili":
        print("💡 B站关键 Cookie：")
        print("   - SESSDATA：会话数据")
        print("   - bili_jct：CSRF 令牌")
        print("   - DedeUserID：用户ID")
        print("   格式：SESSDATA=xxx; bili_jct=yyy; DedeUserID=zzz")
    
    print()
    print("=" * 60)
    print()
    
    # 输入 Cookie
    print(f"请粘贴 {platform_name} 的 Cookie（格式：name1=value1; name2=value2）：")
    cookie = input().strip()
    
    if not cookie:
        print("❌ Cookie 不能为空")
        return
    
    # 基本验证
    if key_cookie not in cookie:
        print()
        print(f"⚠️  警告：Cookie 中没有找到 '{key_cookie}' 字段")
        print(f"   这可能不是有效的{platform_name} Cookie")
        print()
        proceed = input("是否继续配置？(y/n): ").strip().lower()
        if proceed != 'y':
            print("取消配置")
            return
    
    # 保存 Cookie
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(cookie)
        
        print()
        print("=" * 60)
        print("✅ Cookie 配置成功！")
        print("=" * 60)
        print()
        print("📊 配置信息：")
        print(f"   平台：{platform_name}")
        print(f"   Cookie 长度：{len(cookie)} 字符")
        print(f"   配置文件：{config_path}")
        print()
        print("🎯 使用方法：")
        print(f"   make drission-archive URL={platform_url}/xxx")
        print()
        print("💡 提示：")
        print("   - Cookie 会在归档时自动加载")
        print("   - Cookie 可能会过期，过期后需要重新配置")
        print("   - 建议定期更新（每周或每月）")
        print()
        
    except Exception as e:
        print(f"❌ 保存配置失败：{e}")
        return


if __name__ == "__main__":
    try:
        configure_cookie()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        sys.exit(1)
