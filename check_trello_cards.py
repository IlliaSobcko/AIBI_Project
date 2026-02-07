import os
from dotenv import load_dotenv
from trello_client import TrelloClient

load_dotenv()

trello = TrelloClient(
    api_key=os.getenv("TRELLO_API_KEY"),
    token=os.getenv("TRELLO_TOKEN"),
    board_id=os.getenv("TRELLO_BOARD_ID")
)

lists = trello.get_lists()
list_id = lists[0]['id']  # "To Do" list

# Get cards in the "To Do" list
import requests
url = f"{trello.base_url}/lists/{list_id}/cards"
params = {"key": trello.api_key, "token": trello.token}
resp = requests.get(url, params=params)
cards = resp.json()

print(f"Картки в списку 'To Do' ({len(cards)} шт.):")
for card in cards:
    print(f"  - {card['name']}")
    print(f"    URL: {card['url']}")
    print(f"    Created: {card['dateLastActivity']}")
    print()
