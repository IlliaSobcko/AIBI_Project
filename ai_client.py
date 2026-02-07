import json
import re
import asyncio
from typing import List, Tuple, Protocol
from openai import AsyncOpenAI
from utils import ChatHistory
from dataclasses import dataclass

@dataclass
class AIConfig:
    api_key: str
    base_url: str
    model: str

class Agent(Protocol):
    name: str
    async def analyze(self, system_instructions: str, history: ChatHistory) -> Tuple[str, int]:
        ...

class PerplexitySonarAgent:
    def __init__(self, api_key: str, model: str = "sonar"):
        self.name = "Perplexity"
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        self.model = model

    async def analyze(self, system_instructions: str, history: ChatHistory) -> Tuple[str, int]:
        prompt = f"ЧАТ: {history.chat_title}\nТЕКСТ:\n{history.text}"
        
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": f"Проаналізуй і поверни JSON {{'report': '...', 'confidence': 0-100}}. \n\n{prompt}"}
            ],
            temperature=0.2
        )
        return self._parse(resp.choices[0].message.content)

    def _parse(self, text: str) -> Tuple[str, int]:
        try:
            # Шукаємо JSON у відповіді (non-greedy to avoid capturing too much)
            match = re.search(r'\{.*?\}', text, re.DOTALL)
            if not match:
                print(f"[AI_CLIENT] [WARNING] No JSON found in response. Returning text with 0 confidence.")
                return text, 0

            data = json.loads(match.group())
            confidence = data.get("confidence")

            # Ensure confidence is an integer
            if isinstance(confidence, str):
                confidence = int(confidence)
            elif confidence is None:
                confidence = 50
            else:
                confidence = int(confidence)

            report = data.get("report", text)
            print(f"[AI_CLIENT] [PARSE] Extracted confidence: {confidence}% from AI response")
            return report, confidence

        except json.JSONDecodeError as e:
            print(f"[AI_CLIENT] [ERROR] JSON decode error: {e}. Returning text with 0 confidence.")
            return text, 0
        except (ValueError, TypeError) as e:
            print(f"[AI_CLIENT] [ERROR] Type conversion error: {e}. Returning text with 0 confidence.")
            return text, 0
        except Exception as e:
            print(f"[AI_CLIENT] [ERROR] Unexpected error in _parse: {e}. Returning text with 0 confidence.")
            return text, 0

class MultiAgentAnalyzer:
    def __init__(self, agents: List[Agent], threshold: int = 95):
        self.agents = agents
        self.threshold = threshold

    async def analyze_chat(self, system_instructions: str, history: ChatHistory):
        # ЗАПУСК КОНСИЛІУМУ (Паралельно)
        results = await asyncio.gather(*[a.analyze(system_instructions, history) for a in self.agents])
        
        # Вибираємо результат з найвищою впевненістю
        best_report, best_conf = max(results, key=lambda x: x[1])
        
        return {
            "report": best_report,
            "confidence": best_conf,
            "needs_review": best_conf < self.threshold
        }