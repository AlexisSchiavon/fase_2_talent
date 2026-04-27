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
    event = payload.event
    data = payload.data
    deal_id: Optional[int] = data.get("id")

    logger.info("Received Pipedrive webhook: event=%s deal_id=%s", event, deal_id)

    if deal_id is None:
        logger.warning("Webhook payload has no 'id' in data, skipping processing")
        return {"received": True}

    stage_id = data.get("stage_id")

    # Sync to Trello when deal reaches "Contrato y factura" stage
    if "deal" in event and stage_id == settings.PIPEDRIVE_STAGE_CONTRATO_ID:
        logger.info(
            "Deal %s reached stage %s, queuing Trello sync",
            deal_id,
            settings.PIPEDRIVE_STAGE_CONTRATO_ID,
        )
        background_tasks.add_task(sync_deal_to_trello, deal_id)

    # Enrich on any deal or person event
    if "deal" in event or "person" in event:
        logger.info("Queuing enrichment for deal %s (event: %s)", deal_id, event)
        background_tasks.add_task(enrich_deal, deal_id)

    # Return 200 immediately so Pipedrive does not timeout
    return {"received": True}
