#!/usr/bin/env python3
"""
演示多关键词搜索的简单实现
"""
from db.search import SearchRepository

def multi_keyword_search(query: str, match_all: bool = False):
    """
    多关键词搜索的简单实现
    
    Args:
        query: 空格分隔的多个关键词
        match_all: True=AND逻辑（所有关键词都匹配），False=OR逻辑（任一匹配）
    """
    repo = SearchRepository()
    keywords = [k.strip() for k in query.split() if k.strip()]
    
    if not keywords:
        return []
    
    if len(keywords) == 1:
        # 单关键词，直接搜索
        return repo.search(keywords[0], group_by_video=True)
    
    # 多关键词
    if match_all:
        # AND逻辑：找到包含所有关键词的视频
        # 1. 对每个关键词分别搜索
        all_results = {}
        for keyword in keywords:
            results = repo.search(keyword, group_by_video=True)
            for r in results:
                if r.video_id not in all_results:
                    all_results[r.video_id] = {
                        'result': r,
                        'matched_keywords': set()
                    }
                all_results[r.video_id]['matched_keywords'].add(keyword)
        
        # 2. 只保留匹配所有关键词的视频
        final_results = [
            data['result'] 
            for data in all_results.values()
            if len(data['matched_keywords']) == len(keywords)
        ]
        return final_results
    else:
        # OR逻辑：合并所有关键词的搜索结果（去重）
        seen_ids = set()
        all_results = []
        for keyword in keywords:
            results = repo.search(keyword, group_by_video=True)
            for r in results:
                if r.video_id not in seen_ids:
                    seen_ids.add(r.video_id)
                    all_results.append(r)
        return all_results

if __name__ == '__main__':
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "美国 流浪汉"
    
    print(f"\n🔍 搜索: {query}")
    print("=" * 60)
    
    # OR逻辑
    print("\n📊 OR逻辑（任一关键词匹配）:")
    results_or = multi_keyword_search(query, match_all=False)
    print(f"找到 {len(results_or)} 个视频:")
    for i, r in enumerate(results_or, 1):
        print(f"  {i}. [ID={r.video_id}] {r.video_title[:50]}")
    
    # AND逻辑
    print("\n📊 AND逻辑（所有关键词都匹配）:")
    results_and = multi_keyword_search(query, match_all=True)
    print(f"找到 {len(results_and)} 个视频:")
    for i, r in enumerate(results_and, 1):
        print(f"  {i}. [ID={r.video_id}] {r.video_title[:50]}")
