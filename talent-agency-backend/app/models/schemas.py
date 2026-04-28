from typing import List, Optional

from pydantic import BaseModel


class PipedriveWebhookPayload(BaseModel):
    event: Optional[str] = None  # v1 only
    data: dict
    meta: Optional[dict] = None  # v2 only


class DealData(BaseModel):
    id: int
    title: str
    stage_id: int
    pipeline_id: int
    person_id: Optional[int] = None
    org_id: Optional[int] = None
    value: Optional[float] = None
    label: Optional[str] = None
    owner_id: Optional[int] = None


class EnrichmentResult(BaseModel):
    deal_id: int
    success: bool
    tags_added: List[str] = []
    phone_found: bool = False
    phone_value: Optional[str] = None
    duplicates_found: List[dict] = []
    errors: List[str] = []
    person_label_updated: bool = False
    product_in_deal: bool = False


class SyncResult(BaseModel):
    deal_id: int
    success: bool
    cards_created: List[dict] = []
    errors: List[str] = []
