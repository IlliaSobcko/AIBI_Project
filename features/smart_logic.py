"""
AI Decision Engine with Multi-Source Confidence Scoring
Evaluates confidence based on: AI analysis, Calendar availability, Trello tasks, Price lists.
MODULAR: No imports from main.py or core modules.
"""

import asyncio
import re
import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta


class DataSourceManager:
    """
    Async wrapper for all external data sources.
    Provides unified interface for Calendar, Trello, Business Data access.
    """

    def __init__(self, calendar_client=None, trello_client=None, business_data: str = ""):
        """
        Initialize data source manager.

        Args:
            calendar_client: GoogleCalendarClient instance (sync)
            trello_client: TrelloClient instance (sync)
            business_data: Business data text (prices, services, etc)
        """
        self.calendar = calendar_client
        self.trello = trello_client
        self.business_data = business_data
        print(f"[SMART_LOGIC] DataSourceManager initialized")
        print(f"  Calendar available: {calendar_client is not None}")
        print(f"  Trello available: {trello_client is not None}")
        print(f"  Business data: {len(business_data)} chars")

    async def check_calendar_availability(self, hours_ahead: int = 24) -> Dict:
        """
        Check calendar availability for decision making.
        Wrapper around sync calendar API.

        Args:
            hours_ahead: Look ahead window (default 24 hours)

        Returns:
            {
                "is_available": bool,
                "next_free_slot": datetime or None,
                "busy_count": int,
                "error": str or None
            }
        """
        if not self.calendar:
            return {
                "is_available": True,
                "next_free_slot": None,
                "busy_count": 0,
                "error": "Calendar not configured"
            }

        try:
            # Run sync calendar API in thread pool
            now = datetime.now()
            end = now + timedelta(hours=hours_ahead)

            result = await asyncio.to_thread(
                self._check_calendar_sync,
                now,
                end
            )
            return result

        except Exception as e:
            print(f"[WARNING] Calendar check failed: {e}")
            return {
                "is_available": True,
                "next_free_slot": None,
                "busy_count": 0,
                "error": str(e)
            }

    def _check_calendar_sync(self, start_time: datetime, end_time: datetime) -> Dict:
        """Synchronous calendar check (runs in thread pool)."""
        try:
            # This is a placeholder - actual implementation depends on GoogleCalendarClient API
            # For now, assume calendar.get_events() or similar method exists
            if hasattr(self.calendar, 'get_events'):
                events = self.calendar.get_events(
                    start_time.isoformat(),
                    end_time.isoformat()
                )
                busy_count = len(events) if events else 0
            else:
                # Fallback: just check if client is responsive
                busy_count = 0
                events = []

            # Determine next free slot
            next_free = None
            if not events or busy_count == 0:
                next_free = datetime.now() + timedelta(minutes=30)

            return {
                "is_available": busy_count < 3,  # Consider busy if 3+ events
                "next_free_slot": next_free,
                "busy_count": busy_count,
                "error": None
            }
        except Exception as e:
            print(f"[ERROR] Calendar sync check failed: {e}")
            return {
                "is_available": True,
                "next_free_slot": None,
                "busy_count": 0,
                "error": str(e)
            }

    async def get_relevant_trello_tasks(self, chat_title: str, limit: int = 5) -> List[Dict]:
        """
        Get relevant Trello tasks matching chat context.
        Wrapper around sync Trello API.

        Args:
            chat_title: Chat title to match against task context
            limit: Maximum tasks to return

        Returns:
            List of relevant task dicts with priority and status
        """
        if not self.trello:
            return []

        try:
            result = await asyncio.to_thread(
                self._get_trello_tasks_sync,
                chat_title,
                limit
            )
            return result

        except Exception as e:
            print(f"[WARNING] Trello tasks fetch failed: {e}")
            return []

    def _get_trello_tasks_sync(self, chat_title: str, limit: int) -> List[Dict]:
        """Synchronous Trello task fetch (runs in thread pool)."""
        try:
            tasks = []

            # Get lists from Trello board
            if hasattr(self.trello, 'get_lists'):
                lists = self.trello.get_lists()
            else:
                return []

            # Search for tasks matching chat title
            chat_title_lower = chat_title.lower()

            for list_item in lists:
                if 'id' not in list_item:
                    continue

                # Get cards in list
                if hasattr(self.trello, 'get_cards'):
                    cards = self.trello.get_cards(list_item['id'])
                else:
                    continue

                for card in cards:
                    card_name_lower = card.get('name', '').lower()

                    # Match: exact match or keyword match
                    if (chat_title_lower in card_name_lower or
                            any(word in card_name_lower for word in chat_title_lower.split())):
                        tasks.append({
                            'title': card.get('name'),
                            'list': list_item.get('name'),
                            'priority': 'high' if 'важ' in card_name_lower else 'normal',
                            'url': card.get('url')
                        })

                    if len(tasks) >= limit:
                        return tasks

            return tasks

        except Exception as e:
            print(f"[ERROR] Trello sync fetch failed: {e}")
            return []

    def extract_prices(self, message_text: str, query_text: str = "") -> Dict:
        """
        Extract price information from business data if user asked about pricing.

        Args:
            message_text: User message text
            query_text: Query or summary to check against

        Returns:
            {
                "has_price_request": bool,
                "matching_services": [str],
                "price_range": (min, max) or None,
                "exact_match": bool
            }
        """
        # Check if user asked about price/cost
        price_patterns = [
            r'(?:скільки коштує|сколько стоит|how much|price|cost|вартість)',
            r'(?:вартість|стоимость|цена)',
            r'(?:безкоштовно|бесплатно|free)',
            r'(?:знижка|скидка|discount)',
        ]

        message_lower = message_text.lower()
        has_price_request = any(
            re.search(pattern, message_lower) for pattern in price_patterns
        )

        if not has_price_request:
            return {
                "has_price_request": False,
                "matching_services": [],
                "price_range": None,
                "exact_match": False
            }

        # Extract prices from business_data
        matching_services = []
        prices = []

        # Parse business_data for services and prices
        lines = self.business_data.split('\n')
        for line in lines:
            # Look for price patterns: "Service - $XXX" or "Service: from $XXX"
            if '$' in line or 'грн' in line or '€' in line:
                # Extract service name and price
                match = re.search(r'([^-$€]+)[-:]\s*(?:від|from)?\s*\$?([0-9]+)', line, re.IGNORECASE)
                if match:
                    service = match.group(1).strip()
                    try:
                        price = int(match.group(2))
                        prices.append(price)
                        matching_services.append(f"{service}: ${price}")
                    except ValueError:
                        pass

        # Calculate price range
        price_range = (min(prices), max(prices)) if prices else None

        return {
            "has_price_request": True,
            "matching_services": matching_services,
            "price_range": price_range,
            "exact_match": len(matching_services) > 0
        }


class SmartDecisionEngine:
    """
    Enhanced AI decision engine with multi-source confidence evaluation.
    Combines AI analysis with contextual business data for better decisions.
    """

    def __init__(self, data_source_manager: DataSourceManager):
        """
        Initialize decision engine.

        Args:
            data_source_manager: DataSourceManager instance
        """
        self.dsm = data_source_manager
        self.confidence_threshold = int(os.getenv("SMART_CONFIDENCE_THRESHOLD", "90"))
        self.ai_weight = 0.60
        self.calendar_weight = float(os.getenv("CALENDAR_WEIGHT", "0.20"))
        self.trello_weight = float(os.getenv("TRELLO_WEIGHT", "0.10"))
        self.price_weight = float(os.getenv("PRICE_LIST_WEIGHT", "0.10"))

        print(f"[SMART_LOGIC] DecisionEngine initialized")
        print(f"  Confidence threshold: {self.confidence_threshold}%")
        print(f"  Weights: AI={self.ai_weight}, Cal={self.calendar_weight}, "
              f"Trello={self.trello_weight}, Prices={self.price_weight}")

    async def evaluate_confidence(
        self,
        base_confidence: int,
        chat_context: Dict[str, Any],
        has_unreadable_files: bool = False
    ) -> Dict:
        """
        Evaluate multi-source confidence for smart decision making.

        Args:
            base_confidence: AI model confidence (0-100)
            chat_context: {
                "chat_title": str,
                "message_history": str,
                "analysis_report": str
            }
            has_unreadable_files: Force low confidence if unreadable files

        Returns:
            {
                "final_confidence": int (0-100),
                "needs_manual_review": bool,
                "reasoning": str,
                "data_sources": {
                    "ai": int,
                    "calendar": int,
                    "trello": int,
                    "price_list": int
                },
                "boosts": {
                    "calendar_boost": int,
                    "trello_boost": int,
                    "price_boost": int
                }
            }
        """

        # RULE 1: Zero Confidence Rule - Unreadable files present
        if has_unreadable_files:
            print(f"[SMART_LOGIC] ZERO CONFIDENCE: Unreadable files detected")
            return {
                "final_confidence": 0,
                "needs_manual_review": True,
                "reasoning": "Unreadable files present - manual review required",
                "data_sources": {
                    "ai": 0,
                    "calendar": 0,
                    "trello": 0,
                    "price_list": 0
                },
                "boosts": {
                    "calendar_boost": 0,
                    "trello_boost": 0,
                    "price_boost": 0
                }
            }

        # Initialize scores
        scores = {"ai": base_confidence}
        boosts = {
            "calendar_boost": 0,
            "trello_boost": 0,
            "price_boost": 0
        }

        # RULE 2: Calendar availability check (async)
        cal_data = await self.dsm.check_calendar_availability(hours_ahead=24)
        cal_score = self._score_calendar(cal_data)
        scores["calendar"] = cal_score
        boosts["calendar_boost"] = cal_score - 50  # Deviation from neutral

        # RULE 3: Trello tasks relevance (async)
        tasks = await self.dsm.get_relevant_trello_tasks(chat_context["chat_title"])
        trello_score = self._score_trello(tasks)
        scores["trello"] = trello_score
        boosts["trello_boost"] = trello_score - 50

        # RULE 4: Price list matching (sync)
        price_data = self.dsm.extract_prices(
            chat_context["message_history"],
            chat_context.get("analysis_report", "")
        )
        price_score = self._score_prices(price_data)
        scores["price_list"] = price_score
        boosts["price_boost"] = price_score - 50

        # Calculate final weighted score
        final_confidence = self._calculate_final_score(scores)

        # Clamp to 0-100
        final_confidence = min(100, max(0, final_confidence))

        # Determine if manual review needed
        needs_review = final_confidence < self.confidence_threshold

        # Generate reasoning
        reasoning = self._generate_reasoning(scores, chat_context, price_data, tasks)

        print(f"[SMART_LOGIC] Evaluation: AI={scores['ai']}, Cal={scores['calendar']}, "
              f"Trello={scores['trello']}, Prices={scores['price_list']} "
              f"-> Final={final_confidence}")

        return {
            "final_confidence": final_confidence,
            "needs_manual_review": needs_review,
            "reasoning": reasoning,
            "data_sources": scores,
            "boosts": boosts
        }

    def _score_calendar(self, cal_data: Dict) -> int:
        """
        Score calendar availability impact.

        Returns: 0-100 score
        """
        if cal_data.get("error"):
            return 50  # Neutral if unavailable

        if cal_data.get("is_available"):
            return 70  # Positive boost for available time
        else:
            return 30  # Penalty for busy schedule

    def _score_trello(self, tasks: List[Dict]) -> int:
        """
        Score Trello task relevance impact.

        Returns: 0-100 score
        """
        if not tasks:
            return 50  # Neutral if no relevant tasks

        # Boost based on task count and priority
        high_priority_count = sum(1 for t in tasks if t.get("priority") == "high")
        base_score = min(70, 50 + len(tasks) * 5)  # +5 per task, max 70

        if high_priority_count > 0:
            base_score = min(85, base_score + high_priority_count * 5)

        return base_score

    def _score_prices(self, price_data: Dict) -> int:
        """
        Score price list match impact.

        Returns: 0-100 score
        """
        if not price_data.get("has_price_request"):
            return 50  # Neutral if not asking about price

        if price_data.get("exact_match"):
            return 85  # Strong confidence if exact match found
        else:
            return 60  # Moderate confidence for partial match

    def _calculate_final_score(self, scores: Dict) -> int:
        """
        Calculate weighted final confidence.

        Weights:
        - AI: 60% (base model)
        - Calendar: 20% (availability)
        - Trello: 10% (task context)
        - Prices: 10% (business rules)
        """
        final = (
            scores.get("ai", 0) * self.ai_weight +
            scores.get("calendar", 50) * self.calendar_weight +
            scores.get("trello", 50) * self.trello_weight +
            scores.get("price_list", 50) * self.price_weight
        )
        return int(final)

    def _generate_reasoning(
        self,
        scores: Dict,
        chat_context: Dict,
        price_data: Dict,
        tasks: List[Dict]
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        reasoning_parts = [
            f"AI Analysis: {scores['ai']}% confidence"
        ]

        if scores['calendar'] > 60:
            reasoning_parts.append("Calendar shows availability")
        elif scores['calendar'] < 40:
            reasoning_parts.append("Calendar shows busy schedule")

        if tasks:
            reasoning_parts.append(f"Found {len(tasks)} related Trello tasks")

        if price_data.get("has_price_request") and price_data.get("matching_services"):
            reasoning_parts.append(f"Price query matched {len(price_data['matching_services'])} services")

        return " | ".join(reasoning_parts)


async def evaluate_smart_confidence(
    base_confidence: int,
    chat_title: str,
    message_history: str,
    analysis_report: str,
    calendar_client=None,
    trello_client=None,
    business_data: str = "",
    has_unreadable_files: bool = False
) -> Dict:
    """
    Convenience function: Evaluate confidence with all sources.

    Returns: Full evaluation result dict
    """
    # Initialize managers
    dsm = DataSourceManager(calendar_client, trello_client, business_data)
    engine = SmartDecisionEngine(dsm)

    # Evaluate
    return await engine.evaluate_confidence(
        base_confidence=base_confidence,
        chat_context={
            "chat_title": chat_title,
            "message_history": message_history,
            "analysis_report": analysis_report
        },
        has_unreadable_files=has_unreadable_files
    )
