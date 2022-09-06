import unicodedata
from json import dump, load
from pathlib import Path
from typing import Any

from aiohttp import ClientSession
from bs4 import BeautifulSoup


class EmojiDBClient:
    """A client for the EmojiDB website."""

    data_path: Path

    jsondb_path: Path

    session: ClientSession

    def __init__(self, relative_path: str = "emojidb") -> None:
        self.data_path = Path.home() / relative_path
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.jsondb_path = self.data_path / "emojis.json"
        if not self.jsondb_path.exists():
            self.jsondb_path.write_text("{}")

    async def __aenter__(self):
        self.session = ClientSession()
        return self

    async def __aexit__(self, *args: Any):
        await self.session.close()

    async def search_for_emojis(self, query: str) -> list[tuple[str, str]]:
        """Search emojis for query"""
        query = query.replace(" ", "-")
        with self.jsondb_path.open("r") as f:
            jsondb = load(f)
        if query not in jsondb:
            async with self.session.get(f"https://emojidb.org/{query}-emojis") as response:
                soup = BeautifulSoup(await response.content.read(), "html.parser")
                results = soup.find_all("div", class_="emoji")
                emojis = [result.text for result in results]
            jsondb[query] = emojis
            with self.jsondb_path.open("w") as f:
                dump(jsondb, f, ensure_ascii=False)
        emojis_info = []
        for emoji in jsondb[query]:
            try:
                info = unicodedata.name(emoji).capitalize()
            except:
                info = ""
            emojis_info.append((emoji, info))
        return emojis_info
