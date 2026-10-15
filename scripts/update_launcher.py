#!/usr/bin/env python3
"""Pin the latest official Linux AppImage in the Flatpak packaging."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "com.epicgames.EpicGamesLauncher.yml"
METAINFO = "com.epicgames.EpicGamesLauncher.metainfo.xml"
INSTALLER_URL = (
    "https://launcher-public-service-prod06.ol.epicgames.com"
    "/launcher/api/installer/download/EpicGamesLauncher-x86_64.AppImage"
)
DOWNLOAD_HOST = "content-download-egs.distro.on.epicgames.com"
SOURCE_RE = re.compile(
    r"^      - type: extra-data\n.*?(?=^      - type:|\Z)", re.M | re.S
)
VERSION_RE = re.compile(
    r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?"
)


@dataclass(frozen=True)
class Artifact:
    version: str
    url: str
    sha256: str
    size: int


def version_from_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    match = re.fullmatch(
        r"/Builds/EGLv2/([^/]+)/Linux/EpicGamesLauncher-x86_64\.AppImage",
        parsed.path,
    )
    if (
        parsed.scheme != "https"
        or parsed.netloc != DOWNLOAD_HOST
        or parsed.fragment
        or not match
    ):
        raise ValueError(f"Unexpected official AppImage URL: {url}")
    version = urllib.parse.unquote(match.group(1))
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Unexpected launcher version: {version}")
    return version


def field(source: str, name: str) -> str:
    matches = re.findall(rf"^        {re.escape(name)}: (\S+)$", source, re.M)
    if len(matches) != 1:
        raise ValueError(f"Expected one extra-data {name} field")
    return matches[0]


def read_source(manifest: str) -> tuple[re.Match[str], Artifact]:
    matches = list(SOURCE_RE.finditer(manifest))
    if len(matches) != 1:
        raise ValueError("Expected one extra-data source")
    match = matches[0]
    source = match.group()
    if field(source, "filename") != "epic-games-launcher.appimage":
        raise ValueError("Unexpected extra-data filename")
    url = field(source, "url")
    sha256 = field(source, "sha256")
    size = int(field(source, "size"))
    if not re.fullmatch(r"[a-f0-9]{64}", sha256) or size <= 0:
        raise ValueError("Invalid current AppImage checksum or size")
    return match, Artifact(version_from_url(url), url, sha256, size)


def fetch_latest(current: Artifact) -> Artifact:
    request = urllib.request.Request(
        INSTALLER_URL, headers={"User-Agent": "EpicGamesLauncher-Flatpak-updater"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        url = response.geturl()
        version = version_from_url(url)
        # Versioned CDN URLs are immutable; avoid downloading an unchanged image.
        if url == current.url:
            return current
        if tuple(map(int, version.split("+")[0].split("-")[0].split("."))) < tuple(
            map(int, current.version.split("+")[0].split("-")[0].split("."))
        ):
            raise ValueError("Installer endpoint returned an older launcher version")

        digest = hashlib.sha256()
        size = 0
        header = b""
        while chunk := response.read(1024 * 1024):
            if len(header) < 64:
                header = (header + chunk)[:64]
            digest.update(chunk)
            size += len(chunk)
        if (
            len(header) < 64
            or header[:6] != b"\x7fELF\x02\x01"
            or header[8:11] != b"AI\x02"
            or int.from_bytes(header[18:20], "little") != 62
        ):
            raise ValueError("Download is not a type-2 x86_64 AppImage")
        expected_size = response.headers.get("Content-Length")
        if expected_size is not None and size != int(expected_size):
            raise ValueError("AppImage download was truncated")
        return Artifact(version, url, digest.hexdigest(), size)


def render_update(
    manifest: str, metainfo: str, latest: Artifact, date: str
) -> tuple[str, str, Artifact]:
    match, current = read_source(manifest)
    component = ET.fromstring(metainfo)
    if component.findtext("id") != "com.epicgames.EpicGamesLauncher":
        raise ValueError("Unexpected AppStream component")
    releases = component.find("releases")
    if releases is None or releases.find(f"./release[@version='{current.version}']") is None:
        raise ValueError("Current manifest version is missing from AppStream releases")

    source = match.group()
    for name, value in (
        ("url", latest.url),
        ("sha256", latest.sha256),
        ("size", str(latest.size)),
    ):
        source = re.sub(
            rf"^(        {name}: )\S+$",
            lambda m: m.group(1) + value,
            source,
            count=1,
            flags=re.M,
        )
    manifest = manifest[: match.start()] + source + manifest[match.end() :]

    if latest.version != current.version:
        if releases.find(f"./release[@version='{latest.version}']") is not None:
            raise ValueError("Latest version is already an older AppStream release")
        marker = "  <releases>\n"
        if metainfo.count(marker) != 1:
            raise ValueError("Expected one AppStream releases section")
        entry = (
            f'    <release version="{latest.version}" date="{date}" type="development">\n'
            "      <url>https://launcher.epicgames.com/</url>\n"
            "      <description>\n"
            "        <p>Update the official Linux Preview AppImage.</p>\n"
            "      </description>\n"
            "    </release>\n"
        )
        metainfo = metainfo.replace(marker, marker + entry, 1)
    ET.fromstring(metainfo)
    return manifest, metainfo, current


def update(root: Path, *, dry_run: bool = False) -> tuple[bool, Artifact, Artifact]:
    manifest_path, metainfo_path = root / MANIFEST, root / METAINFO
    original_manifest = manifest_path.read_text(encoding="utf-8")
    original_metainfo = metainfo_path.read_text(encoding="utf-8")
    _, current = read_source(original_manifest)
    latest = fetch_latest(current)
    manifest, metainfo, _ = render_update(
        original_manifest,
        original_metainfo,
        latest,
        dt.datetime.now(dt.timezone.utc).date().isoformat(),
    )
    changed = (manifest, metainfo) != (original_manifest, original_metainfo)
    if changed and not dry_run:
        # Validate both files before writing either one.
        manifest_path.write_text(manifest, encoding="utf-8")
        metainfo_path.write_text(metainfo, encoding="utf-8")
    return changed, current, latest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report without changing files")
    args = parser.parse_args()
    try:
        changed, current, latest = update(ROOT, dry_run=args.dry_run)
    except (OSError, ValueError, urllib.error.URLError, ET.ParseError) as error:
        print(f"Update failed: {error}", file=sys.stderr)
        return 1

    status = "Update available" if changed else "Already current"
    print(f"{status}: {current.version} -> {latest.version}")
    print(f"URL: {latest.url}\nSHA-256: {latest.sha256}\nSize: {latest.size}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(
                f"changed={str(changed).lower()}\nprevious_version={current.version}\n"
                f"version={latest.version}\nurl={latest.url}\n"
                f"sha256={latest.sha256}\nsize={latest.size}\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
