import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from update_activity import collect, render, update


def repo(name, private=False, fork=False, language="Python"):
    return {"name": name, "private": private, "fork": fork, "language": language}


class ActivityTests(unittest.TestCase):
    def test_pagination_and_private_and_fork_filtering(self):
        def fetch(path):
            if "/repos?" in path:
                if path.endswith("&page=1"):
                    return [repo(str(i)) for i in range(98)] + [repo("private", private=True), repo("fork", fork=True)]
                return [repo("second page", language="Kotlin")]
            if "/search/" in path:
                self.assertIn("is%3Apublic", path)
                return {"total_count": 7, "incomplete_results": False}
            return {"public_repos": 100, "followers": 11}
        self.assertEqual(collect(fetch)["languages"], {"Python": 98, "Kotlin": 1})

    def test_failed_refresh_keeps_last_successful_graphic(self):
        def failed(path):
            raise OSError("API unavailable")
        with tempfile.TemporaryDirectory() as directory:
            graphic = Path(directory) / "activity.svg"
            graphic.write_text("last good version")
            with self.assertRaises(OSError):
                update(directory, failed)
            self.assertEqual(graphic.read_text(), "last good version")

    def test_incomplete_totals_are_rejected(self):
        def fetch(path):
            if "/repos?" in path:
                return []
            if "/search/" in path:
                return {"total_count": 0, "incomplete_results": True}
            return {"public_repos": 0, "followers": 0}
        with self.assertRaises(RuntimeError):
            collect(fetch)

    def test_graphics_escape_api_text_and_handle_empty_languages(self):
        for mobile in [False, True]:
            for languages in [{}, {"<script>&": 1}]:
                svg = render({"repositories": 3, "merged_prs": 2, "followers": 1, "languages": languages}, "2026-10-05", mobile)
                root = ET.fromstring(svg)
                self.assertFalse(root.findall(".//{http://www.w3.org/2000/svg}script"))


if __name__ == "__main__":
    unittest.main()
