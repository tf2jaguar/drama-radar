"""飞书报告器的测试：每天只发一次、内容来自今日要点、无 FSKEY 时不发送不标记。

发送函数用假实现替换（不打真实请求）。build_site 全链路跑一遍，验证去重标记。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.core.config import Config, Paths
from radar.core.store import Store
from radar.reporters import feishu as feishu_mod
from radar.site import build_site


def _snap(date, heat, fav):
    return {
        "schema": 1, "source": "hongguo", "date": date, "fetched_at": date + "T03:00:00Z", "stale": False,
        "boards": {"hot": {"label": "热播榜", "label_date": date, "items": [{"id": "A", "rank": 1, "heat": heat}]}},
        "items": {"A": {"title": "剧A", "heat": heat, "fav": fav, "like": fav * 2, "rating": 8.5,
                        "tags": ["穿越"], "status_tags": ["新剧"], "first_visible": "2026-10-01", "episodes": 80}},
        "watchlist": [], "errors": [],
    }


class TestFeishuReporter(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="radar-feishu-test-"))
        shutil.copytree(Path(__file__).resolve().parents[1] / "web", self.root / "web")
        self.store = Store(Paths(self.root), "hongguo")
        self.store.save(_snap("2026-11-05", 900, 1000))
        self.store.save(_snap("2026-11-06", 950, 1100))
        self.calls = []
        self._orig = feishu_mod._load_sender
        feishu_mod._load_sender = lambda: (lambda title, content: self.calls.append((title, content)))
        self.config = Config(raw={"reporters": {"feishu": {"enabled": True}}, "sources": {"hongguo": {}}},
                             paths=Paths(self.root))

    def tearDown(self):
        feishu_mod._load_sender = self._orig
        shutil.rmtree(self.root, ignore_errors=True)

    def test_sends_once_per_day_with_insights(self):
        os.environ["FSKEY"] = "test-key"
        try:
            build_site(self.config, self.root / "_site", ["hongguo"], log=lambda m: None)
            self.assertEqual(len(self.calls), 1)
            title, content = self.calls[0]
            self.assertIn("2026-11-06", title)
            self.assertIn("今日要点", title)
            self.assertIn("热播榜第一", content)  # 内容来自 insights 的今日要点
            self.assertTrue(content.rstrip().endswith("详情请查看：https://tf2jaguar.github.io/drama-radar"), content)
            marker = json.loads((self.root / "data" / "state" / "hongguo" / "feishu_sent.json").read_text())
            self.assertEqual(marker["date"], "2026-11-06")

            # 同一天再构建：不再发送
            build_site(self.config, self.root / "_site", ["hongguo"], log=lambda m: None)
            self.assertEqual(len(self.calls), 1)
        finally:
            del os.environ["FSKEY"]

    def test_no_fskey_skips_without_marker(self):
        os.environ.pop("FSKEY", None)
        build_site(self.config, self.root / "_site", ["hongguo"], log=lambda m: None)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / "data" / "state" / "hongguo" / "feishu_sent.json").exists())


if __name__ == "__main__":
    unittest.main()
