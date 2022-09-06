from ..client import AlfredSnippetClient


def test_snippets():
    client = AlfredSnippetClient()
    client.insert_snippet("This is a snippet", "Snippet Name", "keyword")
    client.package("Snippet Name", iconpath="icons/updated.png")
