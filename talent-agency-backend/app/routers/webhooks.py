import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks

from app.config import settings
from app.models.schemas import PipedriveWebhookPayload
from app.services.enrichment import enrich_deal
from app.services.sync import sync_deal_to_trello

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/pipedrive")
async def receive_pipedrive_webhook(
    payload: PipedriveWebhookPayload,
    background_tasks: BackgroundTasks,
) -> dict:
    data = payload.data

    if payload.meta:
        # --- Pipedrive Webhooks v2 ---
        meta = payload.meta
        action: str = meta.get("action", "")
        entity: str = meta.get("entity", "")
        raw_id = meta.get("entity_id")
        deal_id: Optional[int] = int(raw_id) if raw_id is not None else None

        logger.info(
            "Received Pipedrive webhook v2: action=%s entity=%s deal_id=%s",
            action, entity, deal_id,
        )

        if deal_id is None:
            logger.warning("Webhook v2 payload has no entity_id, skipping")
            return {"received": True}

        if action == "create" and entity == "deal":
            logger.info("Queuing enrichment for deal %s", deal_id)
            background_tasks.add_task(enrich_deal, deal_id)

            stage_id = data.get("stage_id")
            if stage_id == settings.PIPEDRIVE_STAGE_CONTRATO_ID:
                logger.info(
                    "Deal %s in stage %s, queuing Trello sync",
                    deal_id, settings.PIPEDRIVE_STAGE_CONTRATO_ID,
                )
                background_tasks.add_task(sync_deal_to_trello, deal_id)

    else:
        # --- Pipedrive Webhooks v1 ---
        event: str = payload.event or ""
        deal_id = data.get("id")

        logger.info(
            "Received Pipedrive webhook v1: event=%s deal_id=%s", event, deal_id,
        )

        if deal_id is None:
            logger.warning("Webhook v1 payload has no 'id' in data, skipping")
            return {"received": True}

        stage_id = data.get("stage_id")

        if "deal" in event and stage_id == settings.PIPEDRIVE_STAGE_CONTRATO_ID:
            logger.info(
                "Deal %s reached stage %s, queuing Trello sync",
                deal_id, settings.PIPEDRIVE_STAGE_CONTRATO_ID,
            )
            background_tasks.add_task(sync_deal_to_trello, deal_id)

        if "deal" in event or "person" in event:
            logger.info("Queuing enrichment for deal %s (event: %s)", deal_id, event)
            background_tasks.add_task(enrich_deal, deal_id)

    return {"received": True}
