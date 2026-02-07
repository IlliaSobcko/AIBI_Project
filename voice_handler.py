import speech_recognition as sr
from pydub import AudioSegment
import os

def process_voice_message(file_path):
    """Безкоштовне розпізнавання голосу через Google"""
    try:
        # Конвертуємо .ogg (телеграм) у .wav (стандарт)
        wav_path = file_path.replace(".ogg", ".wav")
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            # Розпізнаємо українською мовою
            text = recognizer.recognize_google(audio_data, language="uk-UA")
        
        print(f"🎤 Розпізнано безкоштовно: {text}")

        # Додаємо в інструкції
        with open("instructions_dynamic.txt", "a", encoding="utf-8") as f:
            f.write(f"\n- {text}")

        # Видаляємо тимчасові файли
        if os.path.exists(wav_path): os.remove(wav_path)
        return text
    except Exception as e:
        print(f"❌ Помилка безкоштовного розпізнавання: {e}")
        return None