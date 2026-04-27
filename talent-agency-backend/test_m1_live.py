import asyncio
import sys

from app.services.enrichment import enrich_deal


async def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python test_m1_live.py <deal_id>")
        sys.exit(1)

    deal_id = int(sys.argv[1])
    print(f"\nProbando enriquecimiento del deal {deal_id}...")
    print("-" * 50)

    result = await enrich_deal(deal_id)

    print(f"✅ Success: {result.success}")
    print(f"🏷️  Tags encontrados: {result.tags_added}")
    print(f"🏷️  Etiqueta en Person: {result.person_label_updated}")
    print(f"📦  Talento como producto: {result.product_in_deal}")
    print(f"📱 Teléfono encontrado: {result.phone_found} → {result.phone_value}")
    print(f"⚠️  Duplicados: {len(result.duplicates_found)}")
    if result.duplicates_found:
        for dup in result.duplicates_found:
            print(f"   - {dup}")
    if result.errors:
        print(f"❌ Errores: {result.errors}")
    print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
