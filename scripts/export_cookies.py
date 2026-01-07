#!/usr/bin/env python3
"""
Cookie 统一导出工具
将各种来源的 cookie 导出到统一的存储位置：archiver/config/
"""

import sys
import json
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 统一存储目录
COOKIE_DIR = PROJECT_ROOT / "archiver" / "config"


def export_from_xhs_downloader():
    """从 XHS-Downloader 导出小红书 cookie"""
    print("📥 导出小红书 Cookie...")
    
    xhs_config = PROJECT_ROOT / "XHS-Downloader" / "Volume" / "settings.json"
    output_file = COOKIE_DIR / "xiaohongshu_cookie.json"
    
    if not xhs_config.exists():
        print("   ⚠️  XHS-Downloader 配置不存在")
        return False
    
    try:
        with open(xhs_config, 'r', encoding='utf-8') as f:
            xhs_data = json.load(f)
        
        cookie = xhs_data.get('cookie', '')
        user_agent = xhs_data.get('user_agent', '')
        
        if not cookie:
            print("   ⚠️  未找到 cookie")
            return False
        
        # 统一格式
        unified_data = {
            "cookie": cookie,
            "user_agent": user_agent,
            "source": "XHS-Downloader"
        }
        
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ 已导出到: {output_file}")
        print(f"   📊 Cookie 长度: {len(cookie)} 字符")
        return True
        
    except Exception as e:
        print(f"   ❌ 导出失败: {e}")
        return False


def export_from_drission_page(platform="twitter"):
    """从 DrissionPage browser_data 导出 cookie"""
    print(f"📥 导出 {platform.title()} Cookie (DrissionPage)...")
    
    browser_data = PROJECT_ROOT / "browser_data" / "Default" / "Cookies"
    output_file = COOKIE_DIR / f"{platform}_cookie.json"
    
    if not browser_data.exists():
        print("   ⚠️  browser_data 不存在")
        return False
    
    try:
        # 域名映射
        domain_map = {
            "twitter": [".twitter.com", ".x.com"],
            "reddit": [".reddit.com"],
        }
        
        domains = domain_map.get(platform, [f".{platform}.com"])
        
        # 连接 SQLite 数据库
        conn = sqlite3.connect(str(browser_data))
        cursor = conn.cursor()
        
        # 查询 cookie
        cookies = []
        for domain in domains:
            query = """
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies 
                WHERE host_key LIKE ?
            """
            cursor.execute(query, (f"%{domain}%",))
            cookies.extend(cursor.fetchall())
        
        conn.close()
        
        if not cookies:
            print(f"   ⚠️  未找到 {platform} 相关的 cookie")
            return False
        
        # 转换为 cookie 字符串
        cookie_parts = []
        for name, value, host, path, expires, secure, httponly in cookies:
            cookie_parts.append(f"{name}={value}")
        
        cookie_string = "; ".join(cookie_parts)
        
        # 统一格式
        unified_data = {
            "cookie": cookie_string,
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "source": "DrissionPage",
            "count": len(cookies)
        }
        
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ 已导出到: {output_file}")
        print(f"   📊 Cookie 数量: {len(cookies)} 条")
        print(f"   📊 Cookie 长度: {len(cookie_string)} 字符")
        return True
        
    except Exception as e:
        print(f"   ❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_existing_cookies():
    """列出现有的 cookie 配置"""
    print("\n📋 现有 Cookie 配置:")
    print("=" * 60)
    
    if not COOKIE_DIR.exists():
        print("   ⚠️  配置目录不存在")
        return
    
    cookie_files = list(COOKIE_DIR.glob("*cookie*.json"))
    
    if not cookie_files:
        print("   ⚠️  未找到任何 cookie 配置")
        return
    
    for cookie_file in sorted(cookie_files):
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cookie = data.get('cookie', '')
            source = data.get('source', '未知')
            
            print(f"\n   📄 {cookie_file.name}")
            print(f"      来源: {source}")
            print(f"      长度: {len(cookie)} 字符")
            
            if 'count' in data:
                print(f"      数量: {data['count']} 条")
                
        except Exception as e:
            print(f"   ❌ {cookie_file.name}: 读取失败 - {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🍪 Cookie 统一导出工具")
    print("=" * 60)
    print()
    print("将各种来源的 cookie 统一导出到: archiver/config/")
    print("💡 XHS-Downloader 和 archiver 将共用统一位置的 cookie")
    print()
    
    # 导出小红书
    export_from_xhs_downloader()
    print()
    
    # 导出推特
    export_from_drission_page("twitter")
    print()
    
    # 导出 Reddit (如果有)
    if (PROJECT_ROOT / "browser_data" / "Default" / "Cookies").exists():
        export_from_drission_page("reddit")
        print()
    
    # 列出所有配置
    list_existing_cookies()
    print()
    print("=" * 60)
    print("✅ Cookie 导出完成！")
    print()
    print("💡 提示:")
    print("   • 统一存储位置: archiver/config/")
    print("   • 统一格式: {\"cookie\": \"...\", \"user_agent\": \"...\"}")
    print("   • XHS-Downloader 和 archiver 共用小红书 cookie")
    print("   • 可以手动编辑 JSON 文件更新 cookie")
    print("   • 配置文件已被 .gitignore 忽略，不会提交到 Git")
    print("=" * 60)


if __name__ == "__main__":
    main()
