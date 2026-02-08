"""
Knowledge Base Storage Module - AI Self-Learning System

This module handles:
1. Storing successful reply patterns (approved by owner)
2. Retrieving relevant examples for AI prompt injection
3. Generating FAQ from successful patterns
4. Updating dynamic instructions
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict


class KnowledgeBaseStorage:
    """
    Manages successful reply patterns for AI self-learning.

    Storage Structure:
    {
        "replies": [
            {
                "timestamp": "2026-02-07T22:00:00",
                "chat_id": 526791303,
                "chat_title": "John Doe",
                "client_question": "Can you send pricing?",
                "approved_response": "Sure! Here's our price list...",
                "confidence": 87,
                "used_count": 5  # How many times this pattern was referenced
            }
        ],
        "metadata": {
            "total_approvals": 150,
            "last_updated": "2026-02-07T22:00:00",
            "version": "1.0"
        }
    }
    """

    def __init__(self, storage_file: str = "successful_replies.json"):
        """Initialize knowledge base storage"""
        self.storage_file = Path(storage_file)
        self.data = self._load_data()

    # ========================================================================
    # DATA LOADING & SAVING
    # ========================================================================

    def _load_data(self) -> Dict:
        """Load existing knowledge base or create new one"""
        if not self.storage_file.exists():
            print(f"[KNOWLEDGE] Creating new knowledge base: {self.storage_file}")
            return {
                "replies": [],
                "metadata": {
                    "total_approvals": 0,
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }

        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[KNOWLEDGE] Loaded {len(data.get('replies', []))} successful patterns")
                return data
        except Exception as e:
            print(f"[KNOWLEDGE] [ERROR] Failed to load {self.storage_file}: {e}")
            return {
                "replies": [],
                "metadata": {
                    "total_approvals": 0,
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }

    def _save_data(self):
        """Save knowledge base to disk"""
        try:
            # Update metadata
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            self.data["metadata"]["total_approvals"] = len(self.data["replies"])

            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            print(f"[KNOWLEDGE] Saved {len(self.data['replies'])} patterns to {self.storage_file}")
            return True
        except Exception as e:
            print(f"[KNOWLEDGE] [ERROR] Failed to save: {e}")
            return False

    # ========================================================================
    # CAPTURE SUCCESS PATTERNS
    # ========================================================================

    def add_successful_reply(
        self,
        chat_id: int,
        chat_title: str,
        client_question: str,
        approved_response: str,
        confidence: int = 90
    ) -> bool:
        """
        Store a successful reply pattern (approved by owner).

        Args:
            chat_id: Client's Telegram ID
            chat_title: Client's name
            client_question: Original message from client
            approved_response: Response that was approved/sent
            confidence: AI confidence score

        Returns:
            True if saved successfully
        """
        try:
            # Create new pattern entry
            pattern = {
                "timestamp": datetime.now().isoformat(),
                "chat_id": chat_id,
                "chat_title": chat_title,
                "client_question": client_question[:500],  # Limit length
                "approved_response": approved_response[:1000],  # Limit length
                "confidence": confidence,
                "used_count": 0  # Will increment when used as reference
            }

            # Add to storage
            self.data["replies"].append(pattern)

            # Save to disk
            if self._save_data():
                print(f"[KNOWLEDGE] ✓ Saved successful pattern from '{chat_title}'")
                print(f"[KNOWLEDGE] Total patterns: {len(self.data['replies'])}")
                return True
            else:
                return False

        except Exception as e:
            print(f"[KNOWLEDGE] [ERROR] Failed to add pattern: {e}")
            return False

    # ========================================================================
    # RETRIEVE RELEVANT EXAMPLES
    # ========================================================================

    def get_relevant_examples(
        self,
        client_question: str,
        chat_title: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get most relevant successful examples for AI prompt injection.

        Strategy:
        1. Prioritize examples from same client (if chat_title provided)
        2. Find examples with similar keywords
        3. Return most recent if no keyword matches

        Args:
            client_question: Current client's question
            chat_title: Client name (optional, for personalization)
            limit: Max number of examples to return

        Returns:
            List of relevant example dictionaries
        """
        if not self.data["replies"]:
            print(f"[KNOWLEDGE] No examples available yet")
            return []

        relevant_examples = []

        # Strategy 1: Examples from same client
        if chat_title:
            same_client = [
                r for r in self.data["replies"]
                if r["chat_title"].lower() == chat_title.lower()
            ]
            relevant_examples.extend(same_client[:2])  # Max 2 from same client

        # Strategy 2: Keyword matching
        question_lower = client_question.lower()
        keywords = self._extract_keywords(question_lower)

        if keywords:
            keyword_matches = []
            for reply in self.data["replies"]:
                question_text = reply["client_question"].lower()
                # Score based on keyword matches
                score = sum(1 for kw in keywords if kw in question_text)
                if score > 0:
                    keyword_matches.append((score, reply))

            # Sort by score (highest first)
            keyword_matches.sort(key=lambda x: x[0], reverse=True)

            # Add top matches (avoid duplicates from same client)
            for score, reply in keyword_matches:
                if reply not in relevant_examples:
                    relevant_examples.append(reply)
                if len(relevant_examples) >= limit:
                    break

        # Strategy 3: Most recent if still need more
        if len(relevant_examples) < limit:
            recent = sorted(
                self.data["replies"],
                key=lambda x: x["timestamp"],
                reverse=True
            )
            for reply in recent:
                if reply not in relevant_examples:
                    relevant_examples.append(reply)
                if len(relevant_examples) >= limit:
                    break

        # Increment used_count for returned examples
        for example in relevant_examples[:limit]:
            example["used_count"] = example.get("used_count", 0) + 1

        self._save_data()  # Save updated used_count

        print(f"[KNOWLEDGE] Found {len(relevant_examples)} relevant examples")
        return relevant_examples[:limit]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Common question words (Ukrainian + English)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "can", "could", "will",
            "що", "як", "чи", "де", "коли", "хто", "чому", "я", "ти", "ви", "він"
        }

        # Split and filter
        words = text.lower().split()
        keywords = [
            w for w in words
            if len(w) > 3 and w not in stopwords
        ]

        return keywords[:10]  # Max 10 keywords

    # ========================================================================
    # GENERATE FAQ & DYNAMIC INSTRUCTIONS
    # ========================================================================

    def generate_faq(self, output_file: str = "dynamic_instructions.txt") -> Dict:
        """
        Generate FAQ and dynamic instructions from successful patterns.

        Returns:
            Dictionary with statistics and file path
        """
        if not self.data["replies"]:
            return {
                "success": False,
                "error": "No successful patterns available yet",
                "file_path": None
            }

        try:
            # Group by topic/keywords
            topics = self._group_by_topics()

            # Generate FAQ content
            faq_content = self._format_faq(topics)

            # Save to file
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(faq_content)

            stats = {
                "success": True,
                "file_path": str(output_path.absolute()),
                "total_patterns": len(self.data["replies"]),
                "topics_identified": len(topics),
                "generated_at": datetime.now().isoformat()
            }

            print(f"[KNOWLEDGE] ✓ Generated FAQ with {len(topics)} topics")
            print(f"[KNOWLEDGE] File: {output_path}")

            return stats

        except Exception as e:
            print(f"[KNOWLEDGE] [ERROR] Failed to generate FAQ: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": None
            }

    def _group_by_topics(self) -> Dict[str, List[Dict]]:
        """Group replies by common topics/keywords"""
        topics = defaultdict(list)

        for reply in self.data["replies"]:
            question = reply["client_question"].lower()

            # Identify topic based on keywords
            if any(kw in question for kw in ["ціна", "price", "pricing", "вартість", "скільки"]):
                topics["Pricing & Cost"].append(reply)
            elif any(kw in question for kw in ["зустріч", "meeting", "call", "дзвінок"]):
                topics["Meetings & Calls"].append(reply)
            elif any(kw in question for kw in ["термін", "deadline", "коли", "when", "час"]):
                topics["Timeline & Deadlines"].append(reply)
            elif any(kw in question for kw in ["послуг", "service", "робота", "work"]):
                topics["Services & Work"].append(reply)
            elif any(kw in question for kw in ["питання", "question", "допомога", "help"]):
                topics["General Questions"].append(reply)
            else:
                topics["Other"].append(reply)

        return dict(topics)

    def _format_faq(self, topics: Dict[str, List[Dict]]) -> str:
        """Format FAQ content for dynamic instructions"""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("DYNAMIC INSTRUCTIONS - AI KNOWLEDGE BASE")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Total Successful Patterns: {len(self.data['replies'])}")
        lines.append("=" * 80)
        lines.append("")
        lines.append("INSTRUCTIONS FOR AI:")
        lines.append("Below are SUCCESSFUL reply patterns approved by the owner.")
        lines.append("Use these as examples for tone, style, and content when generating responses.")
        lines.append("Match the owner's communication style based on these patterns.")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        # Topics
        for topic_name, replies in topics.items():
            lines.append(f"\n## TOPIC: {topic_name.upper()}")
            lines.append(f"Examples: {len(replies)}")
            lines.append("-" * 80)

            # Show top 5 examples per topic
            for i, reply in enumerate(replies[:5], 1):
                lines.append(f"\n### Example {i}:")
                lines.append(f"Client: {reply['chat_title']}")
                lines.append(f"Date: {reply['timestamp'][:10]}")
                lines.append(f"Confidence: {reply['confidence']}%")
                lines.append(f"Used: {reply.get('used_count', 0)} times")
                lines.append("")
                lines.append(f"CLIENT QUESTION:")
                lines.append(f'"{reply["client_question"]}"')
                lines.append("")
                lines.append(f"APPROVED RESPONSE:")
                lines.append(f'"{reply["approved_response"]}"')
                lines.append("")

        # Footer
        lines.append("\n" + "=" * 80)
        lines.append("END OF DYNAMIC INSTRUCTIONS")
        lines.append("=" * 80)

        return "\n".join(lines)

    # ========================================================================
    # STATISTICS & UTILITIES
    # ========================================================================

    def get_statistics(self) -> Dict:
        """Get knowledge base statistics"""
        return {
            "total_patterns": len(self.data["replies"]),
            "last_updated": self.data["metadata"]["last_updated"],
            "most_used": self._get_most_used_patterns(5),
            "recent": self._get_recent_patterns(5),
            "clients_helped": len(set(r["chat_id"] for r in self.data["replies"]))
        }

    def _get_most_used_patterns(self, limit: int = 5) -> List[Dict]:
        """Get most frequently used patterns"""
        sorted_replies = sorted(
            self.data["replies"],
            key=lambda x: x.get("used_count", 0),
            reverse=True
        )
        return sorted_replies[:limit]

    def _get_recent_patterns(self, limit: int = 5) -> List[Dict]:
        """Get most recent patterns"""
        sorted_replies = sorted(
            self.data["replies"],
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return sorted_replies[:limit]


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_knowledge_base_instance: Optional[KnowledgeBaseStorage] = None


def get_knowledge_base() -> KnowledgeBaseStorage:
    """Get or create knowledge base storage singleton"""
    global _knowledge_base_instance

    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBaseStorage()

    return _knowledge_base_instance
