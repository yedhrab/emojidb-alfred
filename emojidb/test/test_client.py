from pytest import mark

from ..client import EmojiDBClient

pytestmark = mark.asyncio


async def test_search():
    async with EmojiDBClient() as client:
        emojis = await client.search_for_emojis("happy")
        assert emojis
