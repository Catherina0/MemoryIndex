#region 噪声标签过滤测试

import tempfile
import unittest
from pathlib import Path
from typing import List

from cli.db_stats import get_tag_stats
from db.models import ProcessingStatus, SourceType, Video
from db.repository import ArchiveRepository, SearchRepository, TagRepository, VideoRepository
from db.schema import get_connection, init_database


def _create_video(repo: VideoRepository, *, content_hash: str, title: str, source_type: SourceType) -> int:
    return repo.create_video(
        Video(
            content_hash=content_hash,
            title=title,
            source_type=source_type,
            file_path=f"output/{content_hash}",
            status=ProcessingStatus.COMPLETED,
        )
    )


def _attach_raw_tags(db_path: Path, video_id: int, tag_names: List[str]) -> None:
    conn = get_connection(str(db_path))
    try:
        for tag_name in tag_names:
            conn.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag_name,),
            )
            row = conn.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE",
                (tag_name,),
            ).fetchone()
            tag_id = row["id"]

            conn.execute(
                """
                INSERT OR IGNORE INTO video_tags (video_id, tag_id, source, confidence)
                VALUES (?, ?, 'auto', 1.0)
                """,
                (video_id, tag_id),
            )

        conn.commit()
    finally:
        conn.close()


class HiddenTagFilterTest(unittest.TestCase):
    def test_hidden_tags_are_filtered_from_database_and_web_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "knowledge.db"
            init_database(str(db_path))

            video_repo = VideoRepository(str(db_path))
            archive_repo = ArchiveRepository(str(db_path))
            tag_repo = TagRepository(str(db_path))
            search_repo = SearchRepository(str(db_path))

            video_id = _create_video(
                video_repo,
                content_hash="video-visible-tags",
                title="测试视频标签过滤",
                source_type=SourceType.LOCAL,
            )
            archive_id = _create_video(
                video_repo,
                content_hash="archive-visible-tags",
                title="测试网页标签过滤",
                source_type=SourceType.WEB_ARCHIVE,
            )
            future_video_id = _create_video(
                video_repo,
                content_hash="future-visible-tags",
                title="测试后续标签过滤",
                source_type=SourceType.LOCAL,
            )

            # 模拟历史脏数据：标签已经落库，但展示层需要隐藏。
            _attach_raw_tags(db_path, video_id, ["标签", "---", "OCR", "心理学"])
            _attach_raw_tags(db_path, archive_id, ["详细内容概括", "详细内容概括完整版", "教育"])

            # 验证未来写入：新保存的标签在入库前就会跳过噪声标签。
            video_repo.save_tags(future_video_id, ["标签", "---", "OCR", "哲学"], source="auto", confidence=0.9)

            self.assertEqual(video_repo.get_video_tags(video_id), ["心理学"])
            self.assertEqual(video_repo.get_video_tags(future_video_id), ["哲学"])
            self.assertEqual(archive_repo.get_archive(archive_id)["tags"], ["教育"])

            videos, total_videos = video_repo.list_videos(limit=10, offset=0)
            archives, total_archives = archive_repo.list_archives(limit=10, offset=0)

            hidden_tags = {"标签", "---", "OCR", "详细内容概括", "详细内容概括完整版"}

            self.assertEqual(total_videos, 2)
            self.assertEqual(total_archives, 1)
            self.assertTrue(all(set(item["tags"]).isdisjoint(hidden_tags) for item in videos))
            self.assertTrue(all(set(item["tags"]).isdisjoint(hidden_tags) for item in archives))

            visible_tag_names = {tag["name"] for tag in tag_repo.get_all_tags(limit=10)}
            top_tag_names = {tag["name"] for tag in tag_repo.get_top_tags(limit=10)}
            expected_visible_tags = {"教育", "科技", "娱乐", "新闻", "心理学", "哲学"}

            self.assertEqual(tag_repo.count(), 6)
            self.assertEqual(visible_tag_names, expected_visible_tags)
            self.assertEqual(top_tag_names, expected_visible_tags)

            search_results, total_results = search_repo.search(query="测试", limit=10)
            self.assertEqual(total_results, 3)
            self.assertTrue(all(set(result["tags"]).isdisjoint(hidden_tags) for result in search_results))

            cli_tag_stats = get_tag_stats(str(db_path))
            self.assertEqual({item["name"] for item in cli_tag_stats["top_tags"]}, {"心理学", "教育", "哲学"})


if __name__ == "__main__":
    unittest.main()


#endregion
