"""
测试轻量视频入库入口的分享文本 URL 提取。
"""

import io
import unittest
from pathlib import Path
from unittest.mock import patch

from core.import_video import _extract_video_url_from_input, main


#region 单元测试：轻量入库 URL 识别

class TestImportVideoUrlDetection(unittest.TestCase):
    """轻量入库入口的 URL 识别测试。"""

    def test_extract_bilibili_url_from_share_text(self):
        share_text = (
            "【SpaceX首个星舰纪录片，享受吧，像看电影一样！（视频版权属于SpaceX）】"
            "https://www.bilibili.com/video/BV1bko9BkENq?vd_source=99a0a798fd4f2116bab77eeef4b564e0"
        )

        self.assertEqual(
            _extract_video_url_from_input(share_text),
            "https://www.bilibili.com/video/BV1bko9BkENq",
        )

    def test_plain_local_path_is_not_treated_as_url(self):
        self.assertIsNone(_extract_video_url_from_input("videos/example.mp4"))

    def test_main_routes_share_text_to_download_mode(self):
        share_text = (
            "【SpaceX首个星舰纪录片】"
            "https://www.bilibili.com/video/BV1bko9BkENq?vd_source=99a0a798fd4f2116bab77eeef4b564e0"
        )
        expected_url = "https://www.bilibili.com/video/BV1bko9BkENq"
        video_info = {
            "title": "SpaceX首个星舰纪录片",
            "video_id": "BV1bko9BkENq",
            "platform": "bilibili",
        }

        with patch("sys.argv", ["import_video.py", share_text]):
            with patch("sys.stdout", new_callable=io.StringIO):
                with patch("core.import_video._download_from_url") as mock_download:
                    with patch("core.import_video.import_video") as mock_import:
                        mock_download.return_value = (
                            Path("videos/spacex.mp4"),
                            video_info,
                            expected_url,
                        )

                        main()

        mock_download.assert_called_once_with(
            url=expected_url,
            download_dir="videos",
            force=False,
        )
        mock_import.assert_called_once()
        self.assertEqual(mock_import.call_args.kwargs["source_url"], expected_url)


if __name__ == "__main__":
    unittest.main()

#endregion
