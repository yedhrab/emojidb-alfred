from __future__ import annotations

import json
import sys
from asyncio import run
from collections.abc import Callable, Coroutine
from os import environ
from pathlib import Path
from plistlib import dump, load
from shutil import copy2, move
from tempfile import TemporaryDirectory
from time import time
from zipfile import ZIP_DEFLATED, ZipFile

from aiohttp import ClientSession
from packaging import version

from .models import SNIPPET_INFO_TEMPLATE, AlfredResult, AlfredSnippet


class AlfredSnippetClient:

    snippets: list[AlfredSnippet]

    def __init__(self) -> None:
        self.snippets: list[AlfredSnippet] = []

    def insert_snippet(self, snippet: str, name: str, keyword: str):
        self.snippets.append(AlfredSnippet(snippet, name, keyword))

    def package(self, name: str, dst: str = "", prefix: str = "", suffix: str = "", iconpath: str = ""):
        """Package snippets into a .alfredsnippets file"""
        with TemporaryDirectory() as tempdir:
            workdir = Path(tempdir)
            infopath = workdir / "info.plist"
            infopath.write_text(SNIPPET_INFO_TEMPLATE.format(prefix, suffix))

            snippet_path = workdir / f"{name}.alfredsnippets"
            with ZipFile(snippet_path, "w", ZIP_DEFLATED) as zipfile:
                for snippet in self.snippets:
                    path = snippet.save(workdir)
                    zipfile.write(path, path.name)
                zipfile.write(infopath, infopath.name)
                if iconpath:
                    snippet_iconpath = workdir / "icon.png"
                    copy2(iconpath, snippet_iconpath)
                    zipfile.write(snippet_iconpath, snippet_iconpath.name)

            destination = (Path(dst) if dst else Path.cwd()) / f"{name}.alfredsnippets"
            move(snippet_path, destination)


class AlfredWorkflowClient:

    query: str
    page_count: int

    results: list[AlfredResult]

    def __init__(self) -> None:
        self.page_count = sys.argv[1].count("+") + 1
        self.query = sys.argv[1].replace("+", "")
        self.results = []

    @classmethod
    def run(cls, func: Callable[[AlfredWorkflowClient], Coroutine[None, None, None]]) -> None:
        """Give async main function, no need to call `client.response` method
        
        ```
        from alfred import AlfredWorkflowClient

        async def main(alfred_client: AlfredWorkflowClient):
            pass

        if __name__ == "__main__":
            AlfredWorkflowClient.run(main)
        ```
        """
        client = cls()
        run(func(client))
        client.response()

    def get_env(self, name: str) -> str:
        return environ.get(name, "")

    async def update(self, user: str, repo: str):
        """Update alfred workflow if needed"""
        with open("info.plist", "rb") as f:
            plist = load(f)
        current_version = plist["version"]
        if time() - plist.get("lastcheckedtime", 0) > 7 * 24 * 60 * 60:
            async with ClientSession() as session:
                async with session.get(f"https://api.github.com/repos/{user}/{repo}/releases") as response:
                    if response.status != 200:
                        self.add_result(
                            title="Update failed",
                            subtitle="Could not get latest release",
                            icon_path="alfred/icons/failed.png"
                        )
                    else:
                        releases = await response.json()
                        latest_release = releases[0]
                        latest_version = latest_release["tag_name"]
                        download_url = latest_release["assets"][0]["browser_download_url"]
                        current_version = plist["version"]
                        if version.parse(latest_version) > version.parse(current_version):
                            self.add_result(
                                title=f"Update available {current_version} → {latest_version}",
                                subtitle=f"Hold ⇧ and enter to update",
                                icon_path="alfred/icons/updated.png",
                                arg=download_url
                            )
                            plist["needupdate"] = True
                        plist["latestversion"] = latest_version
                        plist["downloadurl"] = download_url
                        plist["lastcheckedtime"] = int(time())
            with open("info.plist", "wb") as f:
                dump(plist, f)
        elif plist.get("needupdate", False):
            self.add_result(
                title=f"Update available {current_version} → {plist['latestversion']}",
                subtitle=f"Hold ⇧ and enter to update",
                icon_path="alfred/icons/updated.png",
                arg=plist["downloadurl"]
            )

    def add_result(
        self,
        title: str,
        subtitle: str = "",
        icon_path: str | Path = "",
        arg: str = "",
        http_downloader: Callable[[str], str] | None = None,
    ):
        """Create and add alfred result."""
        icon = None
        if icon_path:
            if http_downloader and "http" in str(icon_path):
                icon_path = http_downloader(str(icon_path))
            icon = AlfredResult.Icon(str(icon_path))
        self.results.append(AlfredResult(title=title, subtitle=subtitle, icon=icon, arg=arg))

    def error_response(self, title: str, subtitle: str, icon_path: str | Path = ""):
        self.add_result(title=title, subtitle=subtitle, icon_path=icon_path)
        self.response()

    def response(self):
        """Print alfred results and exit."""
        print(json.dumps({"items": [result.to_dict() for result in self.results]}))
        exit(0)
