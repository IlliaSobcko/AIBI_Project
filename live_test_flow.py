"""
Live Test - Advanced AI Flow
Симулює два сценарії:
1. Високий confidence (>85%) - автоматична відповідь
2. Низький confidence (<85%) - чернетка на розгляд
"""

import os
import asyncio
from dotenv import load_dotenv
from auto_reply import AutoReplyGenerator, is_working_hours, draft_system
from draft_bot import DraftReviewBot
from utils import ChatHistory

load_dotenv()

async def live_test():
    print("=" * 70)
    print("LIVE TEST: ADVANCED AI FLOW")
    print("=" * 70)

    # Ініціалізація
    ai_key = os.getenv("AI_API_KEY")
    owner_id = int(os.getenv("OWNER_TELEGRAM_ID"))
    auto_reply_threshold = int(os.getenv("AUTO_REPLY_CONFIDENCE", "85"))

    print(f"\nКонфігурація:")
    print(f"  Owner ID: {owner_id}")
    print(f"  Auto-reply threshold: {auto_reply_threshold}%")
    print(f"  Working hours: {os.getenv('WORKING_HOURS_START')}-{os.getenv('WORKING_HOURS_END')}")
    print(f"  Currently working hours: {'ТАК' if is_working_hours() else 'НІ'}")

    # Створюємо AI генератор
    generator = AutoReplyGenerator(ai_key)

    # Ініціалізуємо Draft Bot (використовуємо існуючу сесію)
    print("\n[INIT] Запуск Draft Bot для Telegram...")
    draft_bot = DraftReviewBot(
        api_id=int(os.getenv("TG_API_ID")),
        api_hash=os.getenv("TG_API_HASH"),
        session_name="aibi_session"  # Використовуємо існуючу сесію
    )
    success = await draft_bot.start()
    if not success:
        print("[ERROR] Draft Bot не вдалося запустити")
        return
    print("[OK] Draft Bot активовано")

    # === ТЕСТ 1: ВИСОКИЙ CONFIDENCE ===
    print("\n" + "=" * 70)
    print("ТЕСТ 1: ВИСОКИЙ CONFIDENCE (повинна бути авто-відповідь)")
    print("=" * 70)

    test1_chat = ChatHistory(
        chat_id=999888777,  # Фейковий ID для тесту
        chat_title="Тест: Важливий клієнт",
        chat_type="private",
        text="Яка ціна на Pro пакет зі знижкою для малого бізнесу?"
    )

    test1_analysis = """📌 РЕЗЮМЕ: Клієнт запитує про ціну Pro пакету зі знижкою для малого бізнесу.

💰 ГРОШІ ТА УГОДИ: Інтерес до платної послуги Pro пакету

🚩 КРИТИЧНІ РИЗИКИ: Потенційний клієнт, швидка відповідь важлива

💡 РЕКОМЕНДАЦІЯ: Надати інформацію про ціну та знижку згідно business_data.txt"""

    print(f"\nЧат: {test1_chat.chat_title}")
    print(f"Повідомлення: '{test1_chat.text}'")
    print("\n[AI] Генерація відповіді...")

    reply1, confidence1 = await generator.generate_reply(
        chat_title=test1_chat.chat_title,
        message_history=test1_chat.text,
        analysis_report=test1_analysis
    )

    print(f"\n[RESULT]")
    print(f"  Confidence: {confidence1}%")
    print(f"  Reply: {reply1}")

    # Логіка рішення
    if confidence1 > auto_reply_threshold and is_working_hours():
        print(f"\n[AUTO-REPLY] Confidence {confidence1}% > {auto_reply_threshold}% і робочі години")
        print(f"[ACTION] Автоматична відправка (симуляція - не відправляємо насправді)")
        print(f"  В реальності відправилось би повідомлення в чат {test1_chat.chat_id}")
    elif confidence1 > auto_reply_threshold:
        print(f"\n[DELAYED] Confidence {confidence1}% > {auto_reply_threshold}% але НЕ робочі години")
        print(f"[ACTION] Чекаємо робочих годин або відправляємо чернетку")
    else:
        print(f"\n[DRAFT MODE] Confidence {confidence1}% <= {auto_reply_threshold}%")
        print(f"[ACTION] Відправка чернетки власнику")

    # === ТЕСТ 2: НИЗЬКИЙ CONFIDENCE ===
    print("\n" + "=" * 70)
    print("ТЕСТ 2: НИЗЬКИЙ CONFIDENCE (повинна бути чернетка)")
    print("=" * 70)

    test2_chat = ChatHistory(
        chat_id=777666555,  # Інший фейковий ID
        chat_title="Тест: Питання поза межами",
        chat_type="private",
        text="Ви робите сайти на WordPress?"
    )

    test2_analysis = """📌 РЕЗЮМЕ: Клієнт запитує про послугу (WordPress сайти), якої немає в прайсі.

💰 ГРОШІ ТА УГОДИ: Потенційна послуга поза основним профілем

🚩 КРИТИЧНІ РИЗИКИ: Неясність, чи можемо взяти це завдання

💡 РЕКОМЕНДАЦІЯ: Запитати CEO для індивідуальної оцінки"""

    print(f"\nЧат: {test2_chat.chat_title}")
    print(f"Повідомлення: '{test2_chat.text}'")
    print("\n[AI] Генерація відповіді...")

    reply2, confidence2 = await generator.generate_reply(
        chat_title=test2_chat.chat_title,
        message_history=test2_chat.text,
        analysis_report=test2_analysis
    )

    print(f"\n[RESULT]")
    print(f"  Confidence: {confidence2}%")
    print(f"  Reply: {reply2}")

    # Логіка рішення
    if confidence2 > auto_reply_threshold and is_working_hours():
        print(f"\n[AUTO-REPLY] Confidence {confidence2}% > {auto_reply_threshold}% і робочі години")
        print(f"[ACTION] Автоматична відправка")
    else:
        print(f"\n[DRAFT MODE] Confidence {confidence2}% <= {auto_reply_threshold}%")
        print(f"[ACTION] Відправка чернетки власнику для розгляду")

        # Додаємо в систему чернеток
        draft_system.add_draft(test2_chat.chat_id, test2_chat.chat_title, reply2, confidence2)

        # ВІДПРАВЛЯЄМО В TELEGRAM!
        print(f"\n[TELEGRAM] Відправка чернетки вам у Telegram (ID: {owner_id})...")
        await draft_bot.send_draft_for_review(
            chat_id=test2_chat.chat_id,
            chat_title=test2_chat.chat_title,
            draft_text=reply2,
            confidence=confidence2
        )
        print(f"[OK] Чернетку відправлено! Перевірте ваш Telegram.")

    # Підсумки
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"\nРезультати:")
    print(f"  Тест 1 (Pro пакет): Confidence {confidence1}% - {'AUTO-REPLY' if confidence1 > auto_reply_threshold and is_working_hours() else 'DRAFT'}")
    print(f"  Тест 2 (WordPress): Confidence {confidence2}% - {'AUTO-REPLY' if confidence2 > auto_reply_threshold else 'DRAFT'}")

    if confidence2 <= auto_reply_threshold:
        print(f"\n📱 ПЕРЕВІРТЕ ВАШ TELEGRAM!")
        print(f"   Ви повинні отримати повідомлення з чернеткою для '{test2_chat.chat_title}'")
        print(f"\n   Команди:")
        print(f"   • SEND {test2_chat.chat_id} - відправити як є")
        print(f"   • EDIT {test2_chat.chat_id} - редагувати")
        print(f"   • SKIP {test2_chat.chat_id} - пропустити")

    print("\n[INFO] Draft Bot залишається активним для обробки команд...")
    print("[INFO] Натисніть Ctrl+C для виходу")

    # Тримаємо бота активним
    try:
        await asyncio.sleep(300)  # 5 хвилин для тестування
    except KeyboardInterrupt:
        print("\n[EXIT] Зупинка Draft Bot...")

    await draft_bot.stop()

if __name__ == "__main__":
    asyncio.run(live_test())
