"""Behavior checks for official AppImage updates, without network access."""

import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("update_launcher", ROOT / "scripts/update_launcher.py")
updater = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = updater
spec.loader.exec_module(updater)


def appimage():
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    header[8:11] = b"AI\x02"
    header[18:20] = (62).to_bytes(2, "little")
    return bytes(header) + b"fixture image content"


class Response(io.BytesIO):
    def __init__(self, url, body, length=None):
        super().__init__(body)
        self.url = url
        self.headers = {"Content-Length": str(len(body) if length is None else length)}

    def geturl(self):
        return self.url


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (updater.MANIFEST, updater.METAINFO):
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        self.before = self.files()
        _, self.current = updater.read_source(self.before[0])
        self.version = "99.1.0+gtest"
        self.url = self.current.url.replace(
            self.current.version.replace("+", "%2B"), self.version.replace("+", "%2B")
        )

    def files(self):
        return tuple(
            (self.root / name).read_text(encoding="utf-8")
            for name in (updater.MANIFEST, updater.METAINFO)
        )

    def run_update(self, body=None, url=None, dry_run=False, length=None):
        response = Response(url or self.url, appimage() if body is None else body, length)
        with patch.object(updater.urllib.request, "urlopen", return_value=response):
            return updater.update(self.root, dry_run=dry_run)

    def test_new_image_pins_download_and_preserves_release_history(self):
        changed, previous, latest = self.run_update()
        self.assertTrue(changed)
        self.assertEqual(previous, self.current)
        self.assertEqual(latest.sha256, hashlib.sha256(appimage()).hexdigest())
        self.assertEqual(latest.size, len(appimage()))
        manifest, metainfo = self.files()
        _, source = updater.read_source(manifest)
        self.assertEqual(source, latest)
        self.assertEqual(latest.url, self.url)
        releases = ET.fromstring(metainfo).findall("./releases/release")
        self.assertEqual(releases[0].get("version"), self.version)
        self.assertIn(self.current.version, [r.get("version") for r in releases])
        self.assertEqual(manifest.count("type: extra-data"), 1)
        self.assertIn("d7f86f2a0d7ec3a69211125207d5f127386b849a", manifest)
        # A second check for the same immutable URL produces no changes.
        after = self.files()
        changed, _, _ = self.run_update(url=self.url)
        self.assertFalse(changed)
        self.assertEqual(self.files(), after)

    def test_current_image_is_a_noop_without_reading_its_body(self):
        response = Response(self.current.url, b"not downloaded")
        with patch.object(updater.urllib.request, "urlopen", return_value=response):
            with patch.object(response, "read", side_effect=AssertionError("Unneeded download")):
                changed, _, latest = updater.update(self.root)
        self.assertFalse(changed)
        self.assertEqual(latest, self.current)
        self.assertEqual(self.files(), self.before)

    def test_dry_run_reports_update_without_writing(self):
        changed, _, latest = self.run_update(dry_run=True)
        self.assertTrue(changed)
        self.assertEqual(latest.version, self.version)
        self.assertEqual(self.files(), self.before)

    def test_invalid_download_leaves_both_files_untouched(self):
        for body in (b"", b"<html>download failed</html>", b"x" * 100):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, "AppImage"):
                    self.run_update(body=body)
                self.assertEqual(self.files(), self.before)

    def test_unexpected_redirect_is_rejected(self):
        urls = (
            self.url.replace("https:", "http:"),
            self.url.replace(updater.DOWNLOAD_HOST, "example.com"),
            self.url.replace("x86_64.AppImage", "aarch64.AppImage"),
        )
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "URL"):
                    self.run_update(url=url)
                self.assertEqual(self.files(), self.before)

    def test_truncated_download_leaves_both_files_untouched(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.run_update(length=len(appimage()) + 1)
        self.assertEqual(self.files(), self.before)

    def test_older_installer_version_is_rejected(self):
        url = self.url.replace("99.1.0%2Bgtest", "0.0.1%2Bgold")
        with self.assertRaisesRegex(ValueError, "older"):
            self.run_update(url=url)
        self.assertEqual(self.files(), self.before)

    def test_invalid_metadata_cannot_partially_update_manifest(self):
        (self.root / updater.METAINFO).write_text("<component>")
        with self.assertRaises(ET.ParseError):
            self.run_update()
        self.assertEqual((self.root / updater.MANIFEST).read_text(), self.before[0])


if __name__ == "__main__":
    unittest.main()
