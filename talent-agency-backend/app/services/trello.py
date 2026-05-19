import logging
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TrelloClient:
    def __init__(self) -> None:
        self.base_url = "https://api.trello.com/1"
        self.key = settings.TRELLO_API_KEY
        self.token = settings.TRELLO_TOKEN

    def _auth_params(self) -> dict:
        return {"key": self.key, "token": self.token}

    async def get_boards_in_workspace(self) -> List[dict]:
        logger.debug("Fetching boards for authenticated Trello member")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/members/me/boards",
                    params=self._auth_params(),
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("Error fetching Trello boards: %s", exc)
            return []

    def find_board_by_name(self, name: str, boards: List[dict]) -> Optional[dict]:
        name_lower = name.lower()

        # Exact case-insensitive match first
        for board in boards:
            if board.get("name", "").lower() == name_lower:
                return board

        # Partial match: board name contains talent name or talent name contains board name
        for board in boards:
            board_name_lower = board.get("name", "").lower()
            if name_lower in board_name_lower or board_name_lower in name_lower:
                return board

        logger.debug("No Trello board found matching name: %s", name)
        return None

    async def get_lists_in_board(self, board_id: str) -> List[dict]:
        logger.debug("Fetching lists for board %s", board_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/boards/{board_id}/lists",
                    params=self._auth_params(),
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("Error fetching lists for board %s: %s", board_id, exc)
            return []

    async def find_or_create_list(self, board_id: str, list_name: str) -> Optional[str]:
        """Return list_id for list_name in board; create it at the bottom if it doesn't exist."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/boards/{board_id}/lists",
                    params={**self._auth_params(), "filter": "open", "fields": "name,id"},
                )
                response.raise_for_status()
                lists = response.json()

            name_lower = list_name.lower()
            for lst in lists:
                if lst.get("name", "").lower() == name_lower:
                    return lst["id"]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/lists",
                    params=self._auth_params(),
                    json={"name": list_name, "idBoard": board_id, "pos": "bottom"},
                )
                response.raise_for_status()
                logger.info("Created list '%s' in board %s", list_name, board_id)
                return response.json()["id"]
        except Exception as exc:
            logger.error(
                "Error finding/creating list '%s' in board %s: %s", list_name, board_id, exc
            )
            return None

    async def create_card(
        self, list_id: str, name: str, description: str = "", pos: str = "top"
    ) -> Optional[dict]:
        logger.debug("Creating Trello card '%s' in list %s", name, list_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/cards",
                    params=self._auth_params(),
                    json={"idList": list_id, "name": name, "desc": description, "pos": pos},
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("Error creating Trello card '%s': %s", name, exc)
            return None

    async def add_checklist_to_card(
        self, card_id: str, name: str, items: List[str]
    ) -> Optional[dict]:
        logger.debug("Adding checklist '%s' to card %s", name, card_id)
        try:
            async with httpx.AsyncClient() as client:
                # Create the checklist
                checklist_response = await client.post(
                    f"{self.base_url}/checklists",
                    params=self._auth_params(),
                    json={"idCard": card_id, "name": name},
                )
                checklist_response.raise_for_status()
                checklist = checklist_response.json()
                checklist_id = checklist["id"]

                # Add each item
                for item in items:
                    item_response = await client.post(
                        f"{self.base_url}/checklists/{checklist_id}/checkItems",
                        params=self._auth_params(),
                        json={"name": item},
                    )
                    item_response.raise_for_status()

                return checklist
        except Exception as exc:
            logger.error(
                "Error adding checklist '%s' to card %s: %s", name, card_id, exc
            )
            return None
