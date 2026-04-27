from unittest.mock import AsyncMock, patch

import pytest

from app.services.sync import sync_deal_to_trello
from app.services.trello import TrelloClient


@pytest.mark.asyncio
async def test_sync_no_deal():
    """When the deal does not exist, SyncResult.success must be False."""
    with patch(
        "app.services.sync.PipedriveClient.get_deal",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await sync_deal_to_trello(deal_id=99999)

    assert result.success is False
    assert result.deal_id == 99999
    assert len(result.errors) > 0


@pytest.mark.parametrize(
    "search_name, board_names, expected_match",
    [
        # Exact match
        ("Admin TA", ["Admin TA", "TA Campañas"], "Admin TA"),
        # Case-insensitive exact match
        ("admin ta", ["Admin TA", "TA Campañas"], "Admin TA"),
        # Partial match: talent name inside board name
        ("MAMA MECANIC", ["Xcaret Mama Mecanic", "Emicanico", "Admin TA"], "Xcaret Mama Mecanic"),
        # Partial match: board name inside talent name
        ("Xcaret Mama Mecanic Oficial", ["Xcaret Mama Mecanic", "Admin TA"], "Xcaret Mama Mecanic"),
        # No match
        ("UNKNOWN TALENT", ["Admin TA", "TA Campañas"], None),
    ],
)
def test_find_board_partial_match(
    search_name: str, board_names: list[str], expected_match: str | None
):
    """Verify find_board_by_name performs case-insensitive and partial matching."""
    client = TrelloClient.__new__(TrelloClient)
    boards = [{"id": f"id_{n}", "name": n} for n in board_names]
    result = client.find_board_by_name(search_name, boards)

    if expected_match is None:
        assert result is None
    else:
        assert result is not None
        assert result["name"] == expected_match
