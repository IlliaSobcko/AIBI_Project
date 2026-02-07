"""
Demo - Advanced AI Flow (без реального відправлення в Telegram)
Показує як працює система auto-reply та draft review
"""

import os
import asyncio
from dotenv import load_dotenv
from auto_reply import AutoReplyGenerator, is_working_hours
from utils import ChatHistory

load_dotenv()

async def demo():
    print("="*80)
    print("DEMO: ADVANCED AI FLOW")
    print("="*80)

    # Конфігурація
    ai_key = os.getenv("AI_API_KEY")
    owner_id = os.getenv("OWNER_TELEGRAM_ID")
    threshold = int(os.getenv("AUTO_REPLY_CONFIDENCE", "85"))
    working = is_working_hours()

    print(f"\n[CONFIG]")
    print(f"  Owner Telegram ID: {owner_id}")
    print(f"  Auto-reply threshold: {threshold}%")
    print(f"  Working hours: {os.getenv('WORKING_HOURS_START')}-{os.getenv('WORKING_HOURS_END')}")
    print(f"  Currently working hours: {'YES' if working else 'NO'}")

    generator = AutoReplyGenerator(ai_key)

    # ТЕСТ 1: Високий confidence
    print("\n" + "="*80)
    print("TEST 1: HIGH CONFIDENCE - Pro package with discount")
    print("="*80)

    chat1 = ChatHistory(
        chat_id=999888777,
        chat_title="Important Client",
        chat_type="private",
        text="Яка ціна на Pro пакет зі знижкою для малого бізнесу?"
    )

    analysis1 = """Клієнт запитує про ціну Pro пакету зі знижкою для малого бізнесу.
Інформація є в business_data.txt: Pro пакет +$200/місяць, знижка 10%."""

    print(f"\nCustomer message: '{chat1.text}'")
    print("\nGenerating AI reply...")

    reply1, conf1 = await generator.generate_reply(
        chat_title=chat1.chat_title,
        message_history=chat1.text,
        analysis_report=analysis1
    )

    print(f"\n[AI RESPONSE]")
    print(f"  Confidence: {conf1}%")
    print(f"  Reply:\n  '{reply1}'")

    # Рішення
    if conf1 > threshold and working:
        print(f"\n[DECISION] AUTO-REPLY")
        print(f"  Reason: Confidence {conf1}% > {threshold}% AND working hours")
        print(f"  Action: Send reply automatically to chat {chat1.chat_id}")
    elif conf1 > threshold:
        print(f"\n[DECISION] DELAYED AUTO-REPLY")
        print(f"  Reason: Confidence {conf1}% > {threshold}% BUT outside working hours")
        print(f"  Action: Wait for working hours or send as draft")
    else:
        print(f"\n[DECISION] DRAFT FOR REVIEW")
        print(f"  Reason: Confidence {conf1}% <= {threshold}%")
        print(f"  Action: Send draft to owner for approval")

    # ТЕСТ 2: Низький confidence
    print("\n" + "="*80)
    print("TEST 2: LOW CONFIDENCE - WordPress (not in our services)")
    print("="*80)

    chat2 = ChatHistory(
        chat_id=777666555,
        chat_title="Potential Client",
        chat_type="private",
        text="Ви робите сайти на WordPress?"
    )

    analysis2 = """Клієнт запитує про WordPress сайти.
Цієї послуги немає в business_data.txt."""

    print(f"\nCustomer message: '{chat2.text}'")
    print("\nGenerating AI reply...")

    reply2, conf2 = await generator.generate_reply(
        chat_title=chat2.chat_title,
        message_history=chat2.text,
        analysis_report=analysis2
    )

    print(f"\n[AI RESPONSE]")
    print(f"  Confidence: {conf2}%")
    print(f"  Reply:\n  '{reply2}'")

    # Рішення
    if conf2 > threshold and working:
        print(f"\n[DECISION] AUTO-REPLY")
        print(f"  Reason: Confidence {conf2}% > {threshold}% AND working hours")
        print(f"  Action: Send reply automatically")
    else:
        print(f"\n[DECISION] DRAFT FOR REVIEW")
        print(f"  Reason: Confidence {conf2}% <= {threshold}%")
        print(f"  Action: Send draft to owner (Telegram ID: {owner_id})")

        print(f"\n[TELEGRAM MESSAGE TO OWNER]")
        print("-" * 80)
        print(f"НОВА ЧЕРНЕТКА ДЛЯ РОЗГЛЯДУ\n")
        print(f"Чат: {chat2.chat_title}")
        print(f"Впевненість AI: {conf2}%")
        print(f"Chat ID: {chat2.chat_id}\n")
        print(f"ЗАПРОПОНОВАНА ВІДПОВІДЬ:")
        print(f"{reply2}\n")
        print("━━━━━━━━━━━━━━━━━━━━")
        print("Команди:")
        print(f"• SEND {chat2.chat_id} - відправити як є")
        print(f"• EDIT {chat2.chat_id} - редагувати (надішли новий текст)")
        print(f"• SKIP {chat2.chat_id} - пропустити")
        print("-" * 80)

    # Підсумок
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTest 1 (Pro package): {conf1}% confidence")
    print(f"  → {'AUTO-REPLY' if conf1 > threshold and working else 'DRAFT REVIEW'}")

    print(f"\nTest 2 (WordPress): {conf2}% confidence")
    print(f"  → {'AUTO-REPLY' if conf2 > threshold else 'DRAFT REVIEW'}")

    print(f"\n[INFO] In production, Test 2 draft would be sent to Telegram ID: {owner_id}")
    print(f"[INFO] You would receive the message above in your Telegram app")
    print(f"[INFO] Commands SEND/EDIT/SKIP would control the final message")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(demo())
