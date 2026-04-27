from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.services.enrichment import PHONE_REGEX, enrich_deal


@pytest.mark.asyncio
async def test_enrich_deal_no_deal():
    """When the deal does not exist, EnrichmentResult.success must be False."""
    with patch(
        "app.services.enrichment.PipedriveClient.get_deal",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await enrich_deal(deal_id=99999)

    assert result.success is False
    assert result.deal_id == 99999
    assert len(result.errors) > 0


@pytest.mark.parametrize(
    "text, expected_digits",
    [
        # 10 consecutive digits — matched directly
        ("Llamar al 5512345678 para confirmar", "5512345678"),
        # Country code prefix with space separator
        ("Tel: +52 5512345678", "5512345678"),
        # Country code without + and dash separator
        ("contacto: 52-5512345678", "5512345678"),
        # Country code dot separator
        ("cel: 52.5512345678", "5512345678"),
        # No number
        ("no phone here", None),
        # Too short
        ("short 123", None),
        # Digits with spaces are NOT 10 consecutive digits — no match
        ("WhatsApp: 55 1234 5678", None),
    ],
)
def test_phone_regex(text: str, expected_digits: Optional[str]) -> None:
    """Verify the regex correctly detects Mexican phone numbers in text.

    PHONE_REGEX uses a single capture group (group 1) for the 10 digits.
    """
    match = PHONE_REGEX.search(text)
    if expected_digits is None:
        assert match is None, f"Expected no match in: {text!r}"
    else:
        assert match is not None, f"Expected match in: {text!r}"
        assert match.group(1) == expected_digits
