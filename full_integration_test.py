import os
from dotenv import load_dotenv
from trello_client import TrelloClient
from utils import ChatHistory

# Load environment variables
load_dotenv()

print("=" * 60)
print("FULL INTEGRATION TEST - TRELLO")
print("=" * 60)

# Step 1: Check environment variables
print("\n[1/5] Перевірка змінних середовища...")
api_key = os.getenv("TRELLO_API_KEY")
token = os.getenv("TRELLO_TOKEN")
board_id = os.getenv("TRELLO_BOARD_ID")
list_name = os.getenv("TRELLO_LIST_NAME", "To Do")

print(f"  API Key: {api_key[:20]}..." if api_key else "  API Key: NOT SET")
print(f"  Token: {token[:20]}..." if token else "  Token: NOT SET")
print(f"  Board ID: {board_id}")
print(f"  List Name: {list_name}")

if not api_key or not token or not board_id:
    print("\n[ERROR] Trello credentials не налаштовані!")
    exit(1)

print("  [OK] Всі змінні встановлені")

# Step 2: Initialize Trello client
print("\n[2/5] Ініціалізація Trello клієнта...")
try:
    trello = TrelloClient(api_key, token, board_id)
    print("  [OK] Клієнт створено")
except Exception as e:
    print(f"  [ERROR] Помилка створення клієнта: {e}")
    exit(1)

# Step 3: Get board lists
print("\n[3/5] Отримання списків на дошці...")
try:
    lists = trello.get_lists()
    print(f"  [OK] Знайдено {len(lists)} списків:")
    for lst in lists:
        print(f"    - {lst['name']} (ID: {lst['id']})")

    # Check if target list exists
    target_list = next((l for l in lists if l["name"].lower() == list_name.lower()), None)
    if target_list:
        print(f"  [OK] Цільовий список '{list_name}' знайдено")
    else:
        print(f"  [WARNING] Список '{list_name}' не знайдено, буде використано перший список")
except Exception as e:
    print(f"  [ERROR] Помилка отримання списків: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Simulate chat analysis with high confidence
print("\n[4/5] Симуляція аналізу чату...")
simulated_chat = ChatHistory(
    chat_id=123456789,
    chat_title="TEST: Важливий клієнт",
    chat_type="private",
    text="Клієнт запитує про великий проект на $50,000. Потрібно терміново відповісти."
)

simulated_report = """📌 РЕЗЮМЕ: Клієнт зацікавлений у великому проекті вартістю $50,000.

💰 ГРОШІ ТА УГОДИ:
- Потенційна угода: $50,000
- Статус: Очікує відповіді

🚩 КРИТИЧНІ РИЗИКИ:
- Термінова відповідь необхідна
- Високовартісний проект може бути втрачено

💡 РЕКОМЕНДАЦІЯ:
1. Негайно зв'язатися з клієнтом
2. Підготувати комерційну пропозицію
3. Призначити зустріч для обговорення деталей
"""

simulated_confidence = 95  # High confidence to trigger Trello card creation

print(f"  Назва чату: {simulated_chat.chat_title}")
print(f"  Впевненість AI: {simulated_confidence}%")
print(f"  Звіт: [містить детальний аналіз]")
print("  [OK] Симуляція готова")

# Step 5: Create Trello card
print("\n[5/5] Створення картки в Trello...")
try:
    card = trello.create_task_from_report(
        list_name=list_name,
        chat_title=simulated_chat.chat_title,
        report=simulated_report,
        confidence=simulated_confidence
    )

    print(f"  [OK] Картка успішно створена!")
    print(f"  Назва: {card['name']}")
    print(f"  URL: {card['url']}")
    print(f"  ID: {card['id']}")

except Exception as e:
    print(f"  [ERROR] Помилка створення картки: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("TEST COMPLETE - SUCCESS!")
print("=" * 60)
print(f"\nПерейдіть до Trello: {card['url']}")
print("Картка має містити повний звіт AI аналізу.")
