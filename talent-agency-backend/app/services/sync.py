import logging
from typing import List, Optional

from app.models.schemas import SyncResult
from app.services.pipedrive import PipedriveClient
from app.services.trello import TrelloClient

logger = logging.getLogger(__name__)

BOARD_ADMIN_TA = "Admin TA"
BOARD_TA_CAMPANAS = "TA Campañas"
LIST_EN_CURSO = "En curso"

CHECKLIST_SEGUIMIENTO: List[str] = [
    "Pedir info cliente",
    "Info recibida",
    "Elaboración de contrato",
    "Mandar contrato",
    "Firma de contrato",
    "Factura",
    "Complemento",
    "Pago 1",
    "Pago 2",
    "Encuesta de satisfacción",
]

CHECKLIST_PRODUCCION: List[str] = [
    "Brief recibido",
    "Contenido en producción",
    "Contenido entregado",
    "Publicado",
]

# Maps Pipedrive label (uppercase) → keyword to find in Trello board name
TALENT_BOARD_KEYWORDS: dict = {
    "EMICANICO": "emicanico",
    "MAMA MECANIC": "mecanic",
    "NAVARRETES": "navarretes",
    "MARIANA SÁNCHEZ": "mariana",
    "MARIANA SANCHEZ": "mariana",
    "DON SILVERIO Y DON WICHO": "silverio",
    "DON SILVERIO": "silverio",
    "ABELITO": "abelito",
    "HANK": "hank",
    "KARAMELA": "karamela",
}


def _board_keyword_for_talent(talent_name: str) -> str:
    upper = talent_name.upper().strip()
    return TALENT_BOARD_KEYWORDS.get(upper, talent_name.lower())


def _find_board_by_keyword(keyword: str, boards: List[dict]) -> Optional[dict]:
    kw = keyword.lower()
    for board in boards:
        if kw in board.get("name", "").lower():
            return board
    return None


def _build_card_name(deal_title: str, org_name: Optional[str]) -> str:
    if org_name:
        return f"{deal_title} — {org_name}"
    return deal_title


def _build_card_description(
    deal_id: int,
    person_name: Optional[str],
    org_name: Optional[str],
    talent_label: Optional[str],
    owner_name: Optional[str],
    value: Optional[float],
    campaign_note: Optional[str] = None,
) -> str:
    deal_section = "\n".join([
        "--- Datos del deal ---",
        f"Cliente: {person_name or 'N/A'}",
        f"Empresa: {org_name or 'N/A'}",
        f"Talento: {talent_label or 'N/A'}",
        f"Ejecutiva: {owner_name or 'N/A'}",
        f"Valor: {int(value or 0)} MXN",
        f"Pipedrive Deal ID: {deal_id}",
    ])
    campaign_body = campaign_note if campaign_note else (
        "⚠️ Sin nota de campaña — el equipo debe llenar la plantilla en Pipedrive"
    )
    campaign_section = "--- Detalle de campaña ---\n" + campaign_body
    return f"{deal_section}\n\n{campaign_section}"


async def sync_deal_to_trello(deal_id: int) -> SyncResult:
    result = SyncResult(deal_id=deal_id, success=False)
    pipedrive = PipedriveClient()
    trello = TrelloClient()

    # --- 1. Fetch deal ---
    deal = await pipedrive.get_deal(deal_id)
    if not deal:
        logger.error("Deal %s not found, aborting Trello sync", deal_id)
        result.errors.append(f"Deal {deal_id} not found")
        return result

    deal_title: str = deal.get("title") or f"Deal {deal_id}"
    person_name: Optional[str] = deal.get("person_name")
    org_name: Optional[str] = deal.get("org_name")
    owner_name: Optional[str] = deal.get("owner_name")
    value: Optional[float] = deal.get("value")

    # --- 2. Fetch products (talentos) ---
    products = await pipedrive.get_deal_products(deal_id)
    talent_names: List[str] = [
        p.get("name") or str(p.get("product_id", ""))
        for p in products
        if p.get("name") or p.get("product_id")
    ]
    talent_label: Optional[str] = ", ".join(talent_names) if talent_names else None

    # --- 3. Fetch campaign note ---
    campaign_note: Optional[str] = None
    try:
        campaign_note = await pipedrive.get_latest_structured_note(deal_id)
    except Exception as exc:
        logger.warning("Deal %s: could not fetch structured note, continuing without it: %s", deal_id, exc)

    card_name = _build_card_name(deal_title, org_name)
    card_desc = _build_card_description(
        deal_id, person_name, org_name, talent_label, owner_name, value, campaign_note
    )

    # --- 4. Fetch all Trello boards once ---
    all_boards = await trello.get_boards_in_workspace()
    if not all_boards:
        logger.error("No Trello boards accessible, aborting sync for deal %s", deal_id)
        result.errors.append("No Trello boards accessible")
        return result

    card_links: List[str] = []

    # --- 5. Card on Admin TA — checklist Seguimiento ---
    admin_board = trello.find_board_by_name(BOARD_ADMIN_TA, all_boards)
    if admin_board:
        try:
            list_id = await trello.find_or_create_list(admin_board["id"], LIST_EN_CURSO)
            if list_id:
                card = await trello.create_card(
                    list_id=list_id, name=card_name, description=card_desc
                )
                if card:
                    await trello.add_checklist_to_card(
                        card["id"], "Seguimiento", CHECKLIST_SEGUIMIENTO
                    )
                    result.cards_created.append(
                        {"board": BOARD_ADMIN_TA, "list": LIST_EN_CURSO, "card": card_name}
                    )
                    card_links.append(f"• Admin TA: {card['url']}")
                    logger.info("Deal %s: created Admin TA card", deal_id)
        except Exception as exc:
            logger.error("Deal %s: failed to create Admin TA card: %s", deal_id, exc)
            result.errors.append(f"Admin TA card failed: {exc}")
    else:
        logger.warning("Deal %s: board '%s' not found", deal_id, BOARD_ADMIN_TA)
        result.errors.append(f"Board '{BOARD_ADMIN_TA}' not found")

    # --- 6. Card on TA Campañas — checklist Producción ---
    campanas_board = trello.find_board_by_name(BOARD_TA_CAMPANAS, all_boards)
    if campanas_board:
        try:
            list_id = await trello.find_or_create_list(campanas_board["id"], LIST_EN_CURSO)
            if list_id:
                card = await trello.create_card(
                    list_id=list_id, name=card_name, description=card_desc
                )
                if card:
                    await trello.add_checklist_to_card(
                        card["id"], "Producción", CHECKLIST_PRODUCCION
                    )
                    result.cards_created.append(
                        {"board": BOARD_TA_CAMPANAS, "list": LIST_EN_CURSO, "card": card_name}
                    )
                    card_links.append(f"• TA Campañas: {card['url']}")
                    logger.info("Deal %s: created TA Campañas card", deal_id)
        except Exception as exc:
            logger.error("Deal %s: failed to create TA Campañas card: %s", deal_id, exc)
            result.errors.append(f"TA Campañas card failed: {exc}")
    else:
        logger.warning("Deal %s: board '%s' not found", deal_id, BOARD_TA_CAMPANAS)
        result.errors.append(f"Board '{BOARD_TA_CAMPANAS}' not found")

    # --- 7. Card on each talent's individual board (no checklist) — DISABLED ---
    # for talent_name in talent_names:
    #     keyword = _board_keyword_for_talent(talent_name)
    #     talent_board = _find_board_by_keyword(keyword, all_boards)
    #     if not talent_board:
    #         logger.warning(
    #             "Deal %s: tablero no encontrado para talento: %s", deal_id, talent_name
    #         )
    #         result.errors.append(f"No board found for talent: {talent_name}")
    #         continue
    #     try:
    #         list_id = await trello.find_or_create_list(talent_board["id"], LIST_EN_CURSO)
    #         if list_id:
    #             card = await trello.create_card(
    #                 list_id=list_id, name=card_name, description=card_desc
    #             )
    #             if card:
    #                 result.cards_created.append(
    #                     {
    #                         "board": talent_board["name"],
    #                         "list": LIST_EN_CURSO,
    #                         "card": card_name,
    #                     }
    #                 )
    #                 card_links.append(f"• {talent_name}: {card['url']}")
    #                 logger.info(
    #                     "Deal %s: created card on board '%s'", deal_id, talent_board["name"]
    #                 )
    #     except Exception as exc:
    #         logger.error(
    #             "Deal %s: failed to create card for talent '%s': %s",
    #             deal_id,
    #             talent_name,
    #             exc,
    #         )
    #         result.errors.append(f"Talent card failed for {talent_name}: {exc}")

    # --- 8. Add Pipedrive note with all card URLs ---
    if card_links:
        note = "🟢 Tarjetas Trello creadas:\n" + "\n".join(card_links)
        try:
            await pipedrive.add_deal_note(deal_id, note)
            logger.info("Deal %s: Pipedrive note with Trello links added", deal_id)
        except Exception as exc:
            logger.error("Deal %s: failed to add Pipedrive note: %s", deal_id, exc)

    result.success = True
    logger.info(
        "Trello sync completed for deal %s: %d cards created", deal_id, len(result.cards_created)
    )
    return result
