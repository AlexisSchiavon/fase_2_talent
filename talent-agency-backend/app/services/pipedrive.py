import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PipedriveClient:
    def __init__(self) -> None:
        self.base_url = "https://api.pipedrive.com/v1"
        self.api_token = settings.PIPEDRIVE_API_TOKEN
        self._label_cache: Optional[Dict[int, str]] = None

    async def get_deal_labels(self) -> Dict[int, str]:
        if self._label_cache is not None:
            return self._label_cache
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/dealFields",
                    params={"api_token": self.api_token},
                )
                response.raise_for_status()
                fields = response.json().get("data") or []
            label_map: Dict[int, str] = {}
            for field in fields:
                if field.get("key") == "label":
                    for opt in field.get("options") or []:
                        label_map[int(opt["id"])] = opt["label"]
                    break
            self._label_cache = label_map
            return label_map
        except Exception as exc:
            logger.error("Error fetching deal label fields: %s", exc)
            return {}

    async def get_deal(self, deal_id: int) -> Optional[dict]:
        logger.debug("Fetching deal %s from Pipedrive", deal_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/deals/{deal_id}",
                    params={"api_token": self.api_token},
                )
                response.raise_for_status()
                payload = response.json()
                deal_data = payload.get("data")
                if deal_data:
                    # Pipedrive sometimes returns person_id as {"value": 123}
                    raw = deal_data.get("person_id")
                    if isinstance(raw, dict):
                        deal_data["person_id"] = raw.get("value")
                return deal_data
        except Exception as exc:
            logger.error("Error fetching deal %s: %s", deal_id, exc)
            return None

    async def get_deal_products(self, deal_id: int) -> List[dict]:
        logger.debug("Fetching products for deal %s", deal_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/deals/{deal_id}/products",
                    params={"api_token": self.api_token},
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("data") or []
        except Exception as exc:
            logger.error("Error fetching products for deal %s: %s", deal_id, exc)
            return []

    async def get_deal_notes(self, deal_id: int) -> List[dict]:
        logger.debug("Fetching notes for deal %s", deal_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/notes",
                    params={"api_token": self.api_token, "deal_id": deal_id},
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("data") or []
        except Exception as exc:
            logger.error("Error fetching notes for deal %s: %s", deal_id, exc)
            return []

    async def get_person(self, person_id: int) -> Optional[dict]:
        logger.debug("Fetching person %s from Pipedrive", person_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/persons/{person_id}",
                    params={"api_token": self.api_token},
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("data")
        except Exception as exc:
            logger.error("Error fetching person %s: %s", person_id, exc)
            return None

    async def update_person_phone(self, person_id: int, phone: str) -> bool:
        logger.debug("Updating phone for person %s to %s", person_id, phone)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/persons/{person_id}",
                    params={"api_token": self.api_token},
                    json={"phone": [{"value": phone, "primary": True, "label": "mobile"}]},
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Error updating phone for person %s: %s", person_id, exc)
            return False

    async def update_person_label(self, person_id: int, label: str) -> bool:
        logger.debug("Updating label for person %s to '%s'", person_id, label)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/persons/{person_id}",
                    params={"api_token": self.api_token},
                    json={"label": label},
                )
                response.raise_for_status()
                logger.info("Label '%s' set on person %s", label, person_id)
                return True
        except Exception as exc:
            logger.error("Error updating label for person %s: %s", person_id, exc)
            return False

    async def add_product_to_deal(self, deal_id: int, product_name: str) -> bool:
        logger.debug("Adding product '%s' to deal %s", product_name, deal_id)
        try:
            async with httpx.AsyncClient() as client:
                search_resp = await client.get(
                    f"{self.base_url}/products/search",
                    params={"api_token": self.api_token, "term": product_name},
                )
                search_resp.raise_for_status()
                items = search_resp.json().get("data", {}).get("items") or []

            product_id: Optional[int] = None
            needle = product_name.lower()
            for item in items:
                name = (item.get("item") or {}).get("name") or ""
                if needle in name.lower():
                    product_id = (item.get("item") or {}).get("id")
                    break

            if product_id is None:
                logger.warning("Producto '%s' no encontrado en Pipedrive", product_name)
                return False

            async with httpx.AsyncClient() as client:
                add_resp = await client.post(
                    f"{self.base_url}/deals/{deal_id}/products",
                    params={"api_token": self.api_token},
                    json={"product_id": product_id, "item_price": 0, "quantity": 1},
                )
                add_resp.raise_for_status()
            logger.info("Product '%s' (id=%s) added to deal %s", product_name, product_id, deal_id)
            return True
        except Exception as exc:
            logger.error("Error adding product '%s' to deal %s: %s", product_name, deal_id, exc)
            return False

    async def search_persons_by_email(self, email: str) -> List[dict]:
        logger.debug("Searching persons by email: %s", email)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/persons/search",
                    params={
                        "api_token": self.api_token,
                        "term": email,
                        "fields": "email",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("data", {}).get("items") or []
        except Exception as exc:
            logger.error("Error searching persons by email %s: %s", email, exc)
            return []

    async def search_persons_by_phone(self, phone: str) -> List[dict]:
        logger.debug("Searching persons by phone: %s", phone)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/persons/search",
                    params={
                        "api_token": self.api_token,
                        "term": phone,
                        "fields": "phone",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("data", {}).get("items") or []
        except Exception as exc:
            logger.error("Error searching persons by phone %s: %s", phone, exc)
            return []

    async def add_deal_note(self, deal_id: int, content: str) -> bool:
        logger.debug("Adding note to deal %s", deal_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/notes",
                    params={"api_token": self.api_token},
                    json={"deal_id": deal_id, "content": content},
                )
                return response.status_code in (200, 201)
        except Exception as exc:
            logger.error("Error adding note to deal %s: %s", deal_id, exc)
            return False

    async def get_person_deals_count(self, person_id: int) -> int:
        logger.debug("Fetching deals count for person %s", person_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/persons/{person_id}/deals",
                    params={"api_token": self.api_token, "limit": 1},
                )
                response.raise_for_status()
                payload = response.json()
                pagination = (payload.get("additional_data") or {}).get("pagination") or {}
                total = pagination.get("total_count")
                if total is not None:
                    return int(total)
                return len(payload.get("data") or [])
        except Exception as exc:
            logger.error("Error fetching deals count for person %s: %s", person_id, exc)
            return 0

    async def merge_persons(self, primary_id: int, secondary_id: int) -> Optional[dict]:
        """Merge secondary_id into primary_id. primary_id survives, secondary_id disappears."""
        logger.info(
            "Merging person %s (disappears) into %s (survives)", secondary_id, primary_id
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/persons/{secondary_id}/merge",
                    params={"api_token": self.api_token},
                    json={"merge_with_id": primary_id},
                )
                response.raise_for_status()
                return response.json().get("data")
        except Exception as exc:
            logger.error(
                "Error merging person %s into %s: %s", secondary_id, primary_id, exc
            )
            return None
