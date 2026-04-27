import logging

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import EnrichmentResult, SyncResult
from app.services.enrichment import enrich_deal
from app.services.sync import sync_deal_to_trello

logger = logging.getLogger(__name__)

router = APIRouter(tags=["manual"])


@router.post("/enrich-lead/{deal_id}", response_model=EnrichmentResult)
async def manual_enrich_lead(deal_id: int) -> EnrichmentResult:
    logger.info("Manual enrichment triggered for deal %s", deal_id)
    return await enrich_deal(deal_id)


@router.post("/sync-to-trello/{deal_id}", response_model=SyncResult)
async def manual_sync_to_trello(deal_id: int) -> SyncResult:
    logger.info("Manual Trello sync triggered for deal %s", deal_id)
    return await sync_deal_to_trello(deal_id)


@router.get("/status")
async def status() -> dict:
    return {
        "status": "ok",
        "pipedrive_pipeline_id": settings.PIPEDRIVE_PIPELINE_ID,
        "stage_contrato_id": settings.PIPEDRIVE_STAGE_CONTRATO_ID,
    }
