from alfred import AlfredWorkflowClient
from emojidb import EmojiDBClient


async def main(alfred_client: AlfredWorkflowClient):
    async with EmojiDBClient() as client:
        for emoji, info in await client.search_for_emojis(alfred_client.query):
            alfred_client.add_result(emoji, info, arg=emoji)


if __name__ == "__main__":
    AlfredWorkflowClient.run(main)
