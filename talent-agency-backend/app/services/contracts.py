import logging

logger = logging.getLogger(__name__)


async def generate_contract(deal_id: int) -> dict:
    """
    M3: Automatic contract generation for a deal.

    TODO M3: Recibir deal_id y retornar ruta al .docx generado o error.

    TODO M3: Obtener datos del deal de Pipedrive:
        - Nombre del cliente (persona u organización)
        - RFC del cliente
        - Domicilio fiscal
        - Talento(s) involucrado(s) (productos del deal)
        - Entregables acordados (campo personalizado o notas)
        - Monto total del deal

    TODO M3: Leer la Constancia de Situación Fiscal (CSF) adjunta desde la
        tarjeta correspondiente en el tablero "Admin TA" de Trello.
        - Buscar tarjeta por nombre del deal
        - Descargar el archivo adjunto (PDF o imagen de la CSF)

    TODO M3: Enviar la CSF a Claude API (claude-sonnet-4-6 o claude-opus-4-6)
        para extracción de datos fiscales:
        - RFC
        - Razón social
        - Domicilio fiscal completo (calle, número, colonia, CP, municipio, estado)
        - Régimen fiscal
        Usar prompt estructurado y pedir respuesta en JSON.

    TODO M3: Usar python-docx para llenar el template de contrato .docx:
        - Leer template desde /templates/contrato_template.docx
        - Reemplazar marcadores de posición ({{CLIENTE_NOMBRE}}, {{RFC}}, etc.)
          con los datos extraídos de Pipedrive y de Claude
        - Guardar el .docx generado en /tmp/ con nombre único por deal

    TODO M3: Subir el .docx generado como adjunto a la tarjeta del deal
        en el tablero "Admin TA" de Trello.

    TODO M3: Notificar a Leilani (vía nota en Pipedrive o mensaje en Trello)
        que el contrato está listo para revisión.

    TODO M3: Retornar dict con éxito, ruta del archivo y URL de la tarjeta Trello.
    """
    logger.warning("Contract generation (M3) not yet implemented for deal %s", deal_id)
    return {
        "deal_id": deal_id,
        "success": False,
        "message": "M3 not yet implemented",
    }
