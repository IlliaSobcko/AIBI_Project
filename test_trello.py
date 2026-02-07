import os
from dotenv import load_dotenv
from trello_client import TrelloClient

load_dotenv()

api_key = os.getenv("TRELLO_API_KEY")
token = os.getenv("TRELLO_TOKEN")
board_id = os.getenv("TRELLO_BOARD_ID")
list_name = os.getenv("TRELLO_LIST_NAME", "Важливі завдання")

print(f"API Key: {api_key[:20]}...")
print(f"Token: {token[:20]}...")
print(f"Board ID: {board_id}")
print(f"List Name: {list_name}")
print("\nТестування підключення до Trello...")

try:
    trello = TrelloClient(api_key, token, board_id)
    lists = trello.get_lists()
    print(f"\n[OK] Підключення успішне! Знайдено {len(lists)} списків:")
    for lst in lists:
        print(f"  - {lst['name']} (ID: {lst['id']})")

    # Тест створення картки
    print(f"\nСтворюю тестову картку в списку '{list_name}'...")
    card = trello.create_task_from_report(
        list_name=list_name,
        chat_title="TEST: AIBI_Secretary_Bot",
        report="Це тестовий звіт для перевірки інтеграції Trello",
        confidence=100
    )
    print(f"[OK] Картка створена успішно!")
    print(f"  URL: {card['url']}")
    print(f"  ID: {card['id']}")

except Exception as e:
    print(f"\n[ERROR] Помилка: {e}")
    import traceback
    traceback.print_exc()
