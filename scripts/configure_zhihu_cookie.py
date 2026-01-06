#!/usr/bin/env python3
"""
知乎 Cookie 配置工具
用于配置知乎归档器的 Cookie（通过浏览器加载）
"""

import json
from pathlib import Path


def configure_cookie():
    """交互式配置 Cookie"""
    
    print("=" * 60)
    print("🍪 知乎 Cookie 配置工具")
    print("=" * 60)
    print()
    
    # 配置文件路径 - 保存到 archiver/config 目录
    config_dir = Path(__file__).parent.parent / "archiver" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "zhihu_cookie.json"
    
    # 检查现有配置
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            current_cookie = config.get('cookie', '')
            if current_cookie:
                print(f"✅ 当前已配置 Cookie（前30字符）：{current_cookie[:30]}...")
                print()
                update = input("是否更新 Cookie？(y/n): ").strip().lower()
                if update != 'y':
                    print("取消配置")
                    return
        except:
            config = {}
    else:
        config = {}
        print("⚠️  当前未配置 Cookie")
    
    print()
    print("📝 如何获取 Cookie：")
    print()
    print("方法一：浏览器扩展（推荐）")
    print("  1. 安装 'EditThisCookie' 或 'Cookie Editor' 浏览器扩展")
    print("  2. 登录知乎：https://www.zhihu.com")
    print("  3. 点击扩展图标，选择 'Export' -> 'Netscape format'")
    print("  4. 复制导出的内容")
    print()
    print("方法二：手动复制")
    print("  1. 打开浏览器访问：https://www.zhihu.com")
    print("  2. 登录你的知乎账号")
    print("  3. 按 F12 打开开发者工具")
    print("  4. 点击 'Application'（应用程序）标签")
    print("  5. 展开 'Cookies' -> 'https://www.zhihu.com'")
    print("  6. 手动复制关键 Cookie（z_c0, d_c0 等）")
    print("  7. 格式：name1=value1; name2=value2; ...")
    print()
    print("💡 提示：程序会自动尝试从 Chrome 浏览器读取 Cookie")
    print("   如果你已在 Chrome 登录知乎，可以直接按 Enter 跳过手动配置")
    print()
    print("=" * 60)
    print()
    
    # 输入 Cookie
    print("请粘贴你的 Cookie（直接按 Enter 使用浏览器自动读取）：")
    cookie = input().strip()
    
    if cookie:
        # 用户手动输入了 Cookie
        # 基本验证
        if 'z_c0' not in cookie and 'd_c0' not in cookie:
            print()
            print("⚠️  警告：Cookie 中没有找到 'z_c0' 或 'd_c0' 字段")
            print("   这可能不是有效的知乎 Cookie")
            print()
            proceed = input("是否继续配置？(y/n): ").strip().lower()
            if proceed != 'y':
                print("取消配置")
                return
        
        # 更新配置
        config['cookie'] = cookie
        config['use_browser'] = False
        
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
            print("🚀 现在可以归档知乎内容了：")
            print("   make archive URL=https://zhuanlan.zhihu.com/p/xxx")
            print("   make archive URL=https://www.zhihu.com/question/xxx")
            print()
            
        except Exception as e:
            print(f"❌ 保存配置失败：{e}")
            return
    else:
        # 使用浏览器自动读取
        print()
        print("🔍 将使用浏览器自动读取模式...")
        print()
        print("配置说明：")
        print("  • 程序会在归档时自动从 Chrome 浏览器读取 Cookie")
        print("  • 请确保你已在 Chrome 浏览器登录知乎")
        print("  • 如果遇到权限问题，可能需要授权 Terminal 访问浏览器")
        print()
        
        # 保存使用浏览器标记
        config['use_browser'] = True
        config['cookie'] = ''
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            print("✅ 配置完成（使用浏览器自动读取模式）")
            print()
            print("🚀 现在可以归档知乎内容了：")
            print("   make archive URL=https://zhuanlan.zhihu.com/p/xxx")
            print("   make archive URL=https://www.zhihu.com/question/xxx")
            print()
            print("💡 如果自动读取失败，请重新运行此命令并手动输入 Cookie")
            print()
            
        except Exception as e:
            print(f"❌ 保存配置失败：{e}")
            return


if __name__ == '__main__':
    configure_cookie()
