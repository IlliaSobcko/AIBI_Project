import os
import requests
from typing import Optional

class TrelloClient:
    def __init__(self, api_key: str, token: str, board_id: str):
        self.api_key = api_key
        self.token = token
        self.board_id = board_id
        self.base_url = "https://api.trello.com/1"

    def get_lists(self):
        """Отримує список всіх списків на дошці"""
        url = f"{self.base_url}/boards/{self.board_id}/lists"
        params = {"key": self.api_key, "token": self.token}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def create_card(self, list_id: str, title: str, description: str, labels: Optional[list] = None):
        """Створює картку у вказаному списку"""
        url = f"{self.base_url}/cards"
        params = {
            "key": self.api_key,
            "token": self.token,
            "idList": list_id,
            "name": title,
            "desc": description
        }
        if labels:
            params["idLabels"] = ",".join(labels)

        resp = requests.post(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def create_task_from_report(self, list_name: str, chat_title: str, report: str, confidence: int):
        """Створює задачу в Trello на основі звіту"""
        lists = self.get_lists()
        target_list = next((l for l in lists if l["name"].lower() == list_name.lower()), None)

        if not target_list:
            target_list = lists[0] if lists else None

        if not target_list:
            raise ValueError("Не знайдено жодного списку на дошці Trello")

        title = f"[{confidence}%] {chat_title}"
        card = self.create_card(target_list["id"], title, report)
        return card
