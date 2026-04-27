import logging
import re
from typing import Optional

from app.models.schemas import EnrichmentResult
from app.services.pipedrive import PipedriveClient

logger = logging.getLogger(__name__)

# Matches 10 consecutive digits, optionally preceded by country code +52 / 52
# with an optional separator (space, dash, dot).
# Group 1 captures the 10 digits.
PHONE_REGEX = re.compile(r"(?:(?:\+?52)?[\s\-\.]?)?(\d{10})(?!\d)")


def _extract_phone_from_text(text: str) -> Optional[str]:
    match = PHONE_REGEX.search(text)
    if match:
        return match.group(1)
    return None


def _person_has_valid_phone(person: dict) -> Optional[str]:
    """Return the first phone value that has at least 10 digits, or None."""
    phones = person.get("phone") or []
    for entry in phones:
        raw = entry.get("value", "") if isinstance(entry, dict) else str(entry)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            return raw
    return None


async def enrich_deal(deal_id: int) -> EnrichmentResult:
    result = EnrichmentResult(deal_id=deal_id, success=False)
    client = PipedriveClient()

    # --- Paso 1: Obtener el deal ---
    deal = await client.get_deal(deal_id)
    if not deal:
        logger.error("Deal %s not found in Pipedrive", deal_id)
        result.errors.append("Deal not found")
        return result

    # person_id is already normalized by get_deal()
    person_id: Optional[int] = deal.get("person_id")

    # --- Paso 2: Extraer etiqueta del talento ---
    label = deal.get("label")
    label_name: Optional[str] = None
    if label:
        label_map = await client.get_deal_labels()
        try:
            label_name = label_map.get(int(label), str(label))
        except (ValueError, TypeError):
            label_name = str(label)
        logger.info("Deal %s: label found → %s (%s)", deal_id, label_name, label)
        result.tags_added.append(label_name)
    else:
        current_products = await client.get_deal_products(deal_id)
        if current_products:
            first_name = current_products[0].get("name") or str(current_products[0].get("product_id", ""))
            if first_name:
                logger.info("Deal %s: talent inferred from product → %s", deal_id, first_name)
                result.tags_added.append(first_name)
                label_name = first_name

    # --- Paso 2b: Agregar etiqueta al Person ---
    if label_name and person_id:
        updated = await client.update_person_label(person_id, label_name)
        if updated:
            logger.info("Deal %s: etiqueta '%s' agregada al Person %s", deal_id, label_name, person_id)
            result.person_label_updated = True
            if label_name not in result.tags_added:
                result.tags_added.append(label_name)

    # --- Paso 2c: Agregar talento como Producto al deal ---
    if label_name:
        existing_products = await client.get_deal_products(deal_id)
        existing_names = [p.get("name", "").lower() for p in existing_products]
        if label_name.lower() in existing_names:
            logger.info("Deal %s: producto '%s' ya existe en el deal", deal_id, label_name)
            result.product_in_deal = True
        else:
            added = await client.add_product_to_deal(deal_id, label_name)
            result.product_in_deal = added
            if added:
                logger.info("Deal %s: producto '%s' agregado al deal", deal_id, label_name)

    # --- Paso 3: Extraer teléfono ---
    person = await client.get_person(person_id) if person_id else None

    existing_phone = _person_has_valid_phone(person) if person else None

    if existing_phone:
        # Contact already has a valid phone — record it, do NOT overwrite
        logger.info("Deal %s: contact already has phone %s", deal_id, existing_phone)
        result.phone_found = True
        result.phone_value = existing_phone
    else:
        # Search notes for a phone number to save on the contact
        notes = await client.get_deal_notes(deal_id)
        for note in notes:
            found = _extract_phone_from_text(note.get("content") or "")
            if found:
                formatted = f"+52{found}"
                logger.info("Deal %s: phone found in notes → %s", deal_id, formatted)
                if person_id:
                    updated = await client.update_person_phone(person_id, formatted)
                    if updated:
                        logger.info("Deal %s: phone saved on contact %s", deal_id, person_id)
                result.phone_found = True
                result.phone_value = formatted
                break

    # --- Paso 4: Detectar duplicados ---
    if person:
        # Check by email
        emails = person.get("email") or []
        primary_email: Optional[str] = next(
            (e["value"] for e in emails if isinstance(e, dict) and e.get("value")),
            None,
        )
        if primary_email:
            email_matches = await client.search_persons_by_email(primary_email)
            if len(email_matches) > 1:
                ids = [m.get("item", {}).get("id") for m in email_matches]
                result.duplicates_found.append(
                    {"field": "email", "value": primary_email, "ids": ids}
                )
                await client.add_deal_note(
                    deal_id,
                    (
                        f"⚠️ DUPLICADO DETECTADO\n"
                        f"Se encontraron {len(email_matches)} contactos con el mismo email.\n"
                        f"IDs encontrados: {ids}\n"
                        "Revisión manual requerida."
                    ),
                )
                logger.warning("Deal %s: duplicate by email — IDs %s", deal_id, ids)

        # Check by phone
        phone_to_check = result.phone_value
        if phone_to_check:
            phone_matches = await client.search_persons_by_phone(phone_to_check)
            if len(phone_matches) > 1:
                ids = [m.get("item", {}).get("id") for m in phone_matches]
                result.duplicates_found.append(
                    {"field": "phone", "value": phone_to_check, "ids": ids}
                )
                await client.add_deal_note(
                    deal_id,
                    (
                        f"⚠️ DUPLICADO DETECTADO\n"
                        f"Se encontraron {len(phone_matches)} contactos con el mismo teléfono.\n"
                        f"IDs encontrados: {ids}\n"
                        "Revisión manual requerida."
                    ),
                )
                logger.warning("Deal %s: duplicate by phone — IDs %s", deal_id, ids)

    # --- Paso 5: Éxito ---
    result.success = True
    logger.info(
        "Deal %s enrichment done — tags=%s phone=%s duplicates=%d",
        deal_id,
        result.tags_added,
        result.phone_value,
        len(result.duplicates_found),
    )
    return result
