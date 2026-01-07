#!/usr/bin/env python3
"""
测试网页归档+数据库集成功能
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.archive_processor import archive_and_save


async def test_archive_run():
    """测试 archive-run 功能"""
    print("=" * 60)
    print("测试：archive-run 功能")
    print("=" * 60)
    
    # 测试URL（使用公开的测试页面）
    test_url = "https://example.com"
    
    try:
        db_id = await archive_and_save(
            url=test_url,
            output_dir="output",
            with_ocr=False,
            headless=True
        )
        
        print(f"\n✅ 测试成功！数据库ID: {db_id}")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_archive_ocr():
    """测试 archive-ocr 功能"""
    print("\n" + "=" * 60)
    print("测试：archive-ocr 功能（OCR开发中）")
    print("=" * 60)
    
    test_url = "https://example.com"
    
    try:
        db_id = await archive_and_save(
            url=test_url,
            output_dir="output",
            with_ocr=True,  # 启用OCR
            headless=True
        )
        
        print(f"\n✅ 测试成功！数据库ID: {db_id}")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_query():
    """测试数据库查询"""
    print("\n" + "=" * 60)
    print("测试：数据库查询")
    print("=" * 60)
    
    try:
        from db import VideoRepository
        repo = VideoRepository()
        
        # 获取所有记录
        videos = repo.list_videos(limit=5)
        
        print(f"\n数据库中的记录数: {len(videos)}")
        
        for video in videos:
            print(f"\nID: {video.id}")
            print(f"  类型: {video.source_type}")
            print(f"  标题: {video.title}")
            print(f"  URL: {video.source_url}")
            print(f"  状态: {video.status}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("🧪 开始测试网页归档+数据库集成功能\n")
    
    results = []
    
    # 测试1: archive-run
    result1 = await test_archive_run()
    results.append(("archive-run", result1))
    
    # 测试2: 数据库查询
    result2 = test_database_query()
    results.append(("database-query", result2))
    
    # 可选：测试archive-ocr（需要较长时间）
    # result3 = await test_archive_ocr()
    # results.append(("archive-ocr", result3))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
