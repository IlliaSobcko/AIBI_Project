"""
Тест Advanced AI Flow - перевірка автоматичних відповідей та чернеток
"""

import os
import asyncio
from dotenv import load_dotenv
from auto_reply import AutoReplyGenerator, is_working_hours, load_business_data
from utils import ChatHistory

load_dotenv()

async def test_auto_reply():
    print("=" * 60)
    print("TEST: ADVANCED AI FLOW")
    print("=" * 60)

    # Перевірка бізнес-даних
    print("\n[1/5] Перевірка business_data.txt...")
    business_data = load_business_data()
    print(f"  [OK] Завантажено {len(business_data)} символів бізнес-даних")
    print(f"  Перші 100 символів: {business_data[:100]}...")

    # Перевірка робочих годин
    print("\n[2/5] Перевірка робочих годин...")
    working_hours = is_working_hours()
    print(f"  Зараз робочі години: {'ТАК' if working_hours else 'НІ'}")
    print(f"  Start: {os.getenv('WORKING_HOURS_START', '9')}")
    print(f"  End: {os.getenv('WORKING_HOURS_END', '18')}")

    # Перевірка AI генератора
    print("\n[3/5] Ініціалізація AI генератора...")
    ai_key = os.getenv("AI_API_KEY")
    if not ai_key:
        print("  [ERROR] AI_API_KEY не встановлено!")
        return

    generator = AutoReplyGenerator(ai_key)
    print("  [OK] Генератор створено")

    # Тест генерації відповіді
    print("\n[4/5] Генерація тестової відповіді...")

    test_chat = ChatHistory(
        chat_id=123456,
        chat_title="Test Client",
        chat_type="private",
        text="Привіт! Скільки коштує ваш AI асистент і коли можна почати?"
    )

    test_analysis = """📌 РЕЗЮМЕ: Клієнт запитує про вартість та терміни AI асистента.

💰 ГРОШІ ТА УГОДИ: Запит на ціну послуги

🚩 КРИТИЧНІ РИЗИКИ: Потенційний клієнт, потребує швидкої відповіді

💡 РЕКОМЕНДАЦІЯ: Надати орієнтовну ціну та запропонувати дзвінок"""

    try:
        reply_text, confidence = await generator.generate_reply(
            chat_title=test_chat.chat_title,
            message_history=test_chat.text,
            analysis_report=test_analysis
        )

        print(f"  [OK] Відповідь згенеровано")
        print(f"  Впевненість: {confidence}%")
        print(f"  Текст відповіді:\n  {reply_text}\n")

        # Визначення логіки
        print("\n[5/5] Визначення логіки роботи...")
        threshold = int(os.getenv("AUTO_REPLY_CONFIDENCE", "85"))

        if confidence > threshold and working_hours:
            print(f"  ✅ AUTO-REPLY: Confidence {confidence}% > {threshold}% і робочі години")
            print(f"  Дія: Автоматична відправка відповіді")
        elif confidence > threshold and not working_hours:
            print(f"  ⏰ DELAYED: Confidence {confidence}% > {threshold}% але не робочі години")
            print(f"  Дія: Чекаємо робочих годин або відправляємо чернетку")
        else:
            print(f"  📝 DRAFT REVIEW: Confidence {confidence}% <= {threshold}%")
            print(f"  Дія: Відправка чернетки власнику для розгляду")

    except Exception as e:
        print(f"  [ERROR] Помилка генерації: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"\nOwner Telegram ID: {os.getenv('OWNER_TELEGRAM_ID')}")
    print(f"Auto-reply threshold: {os.getenv('AUTO_REPLY_CONFIDENCE')}%")
    print(f"Working hours: {os.getenv('WORKING_HOURS_START')}-{os.getenv('WORKING_HOURS_END')}")
    print()

if __name__ == "__main__":
    asyncio.run(test_auto_reply())
