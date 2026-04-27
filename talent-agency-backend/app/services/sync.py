import logging

from app.models.schemas import SyncResult
from app.services.pipedrive import PipedriveClient
from app.services.trello import TrelloClient

logger = logging.getLogger(__name__)

BOARD_ADMIN_TA = "Admin TA"
BOARD_TA_CAMPANAS = "TA Campañas"


async def sync_deal_to_trello(deal_id: int) -> SyncResult:
    result = SyncResult(deal_id=deal_id, success=False)
    pipedrive = PipedriveClient()
    trello = TrelloClient()

    # 1. Fetch the deal
    deal = await pipedrive.get_deal(deal_id)
    if not deal:
        logger.error("Deal %s not found in Pipedrive, aborting sync", deal_id)
        result.errors.append(f"Deal {deal_id} not found")
        return result

    deal_title = deal.get("title", f"Deal {deal_id}")

    # 2. Fetch products (talentos)
    products = await pipedrive.get_deal_products(deal_id)

    # 3. Fetch notes for card descriptions
    notes = await pipedrive.get_deal_notes(deal_id)
    notes_text = "\n\n".join(
        f"Nota: {n.get('content', '')}" for n in notes if n.get("content")
    )

    deal_description = (
        f"Deal ID: {deal_id}\n"
        f"Título: {deal_title}\n"
        f"Valor: {deal.get('value', 'N/A')}\n"
        f"Etapa ID: {deal.get('stage_id', 'N/A')}\n"
    )
    if notes_text:
        deal_description += f"\n{notes_text}"

    # 4. Fetch all Trello boards once
    all_boards = await trello.get_boards_in_workspace()
    if not all_boards:
        logger.error("No Trello boards found, aborting sync for deal %s", deal_id)
        result.errors.append("No Trello boards accessible")
        return result

    # 5. Create a card on each talent's individual board
    for product in products:
        talent_name: str = product.get("name") or str(product.get("product_id", ""))
        if not talent_name:
            continue

        board = trello.find_board_by_name(talent_name, all_boards)
        if not board:
            logger.warning(
                "Deal %s: no Trello board found for talent '%s', skipping",
                deal_id,
                talent_name,
            )
            result.errors.append(f"No board found for talent: {talent_name}")
            continue

        lists = await trello.get_lists_in_board(board["id"])
        if not lists:
            logger.warning(
                "Deal %s: board '%s' has no lists, skipping",
                deal_id,
                board["name"],
            )
            result.errors.append(f"Board '{board['name']}' has no lists")
            continue

        first_list = lists[0]
        card_name = f"{deal_title} - {talent_name}"
        card = await trello.create_card(
            list_id=first_list["id"],
            name=card_name,
            description=deal_description,
        )
        if card:
            result.cards_created.append(
                {"board": board["name"], "list": first_list["name"], "card": card_name}
            )
            logger.info(
                "Deal %s: created card '%s' on board '%s'",
                deal_id,
                card_name,
                board["name"],
            )

    # 6. Create card on "Admin TA" board
    admin_board = trello.find_board_by_name(BOARD_ADMIN_TA, all_boards)
    if admin_board:
        admin_lists = await trello.get_lists_in_board(admin_board["id"])
        if admin_lists:
            # TODO M2: add administrative checklist items here
            admin_card = await trello.create_card(
                list_id=admin_lists[0]["id"],
                name=deal_title,
                description=deal_description,
            )
            if admin_card:
                result.cards_created.append(
                    {
                        "board": BOARD_ADMIN_TA,
                        "list": admin_lists[0]["name"],
                        "card": deal_title,
                    }
                )
                logger.info("Deal %s: created card on Admin TA board", deal_id)
    else:
        logger.warning("Deal %s: board '%s' not found", deal_id, BOARD_ADMIN_TA)
        result.errors.append(f"Board '{BOARD_ADMIN_TA}' not found")

    # 7. Create card on "TA Campañas" board
    campanas_board = trello.find_board_by_name(BOARD_TA_CAMPANAS, all_boards)
    if campanas_board:
        campanas_lists = await trello.get_lists_in_board(campanas_board["id"])
        if campanas_lists:
            # TODO M2: add production checklist items here
            campanas_card = await trello.create_card(
                list_id=campanas_lists[0]["id"],
                name=deal_title,
                description=deal_description,
            )
            if campanas_card:
                result.cards_created.append(
                    {
                        "board": BOARD_TA_CAMPANAS,
                        "list": campanas_lists[0]["name"],
                        "card": deal_title,
                    }
                )
                logger.info("Deal %s: created card on TA Campañas board", deal_id)
    else:
        logger.warning("Deal %s: board '%s' not found", deal_id, BOARD_TA_CAMPANAS)
        result.errors.append(f"Board '{BOARD_TA_CAMPANAS}' not found")

    result.success = True
    logger.info(
        "Sync completed for deal %s: %d cards created",
        deal_id,
        len(result.cards_created),
    )
    return result
