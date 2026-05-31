import asyncio
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/radar_precios.db")

async def test(store, fn):
    try:
        result = await fn("arroz", limit=5)
        print(f"OK  {store}: {len(result.products)} productos | {result.fetch_strategy}")
        if result.products:
            p = result.products[0]
            name = str(p.get("name", ""))[:60]
            price = p.get("price", 0)
            print(f"    -> {name} | ${price}")
    except Exception as e:
        print(f"ERR {store}: {type(e).__name__}: {str(e)[:200]}")

async def main():
    from backend.infrastructure.scrapers.acuenta import search_acuenta
    from backend.scraper_jumbo import search_jumbo
    from backend.infrastructure.scrapers.santa_isabel import search_santa_isabel
    from backend.infrastructure.scrapers.tottus import search_tottus
    from backend.infrastructure.scrapers.unimarc import search_unimarc

    await test("acuenta",      search_acuenta)
    await test("jumbo",        search_jumbo)
    await test("santa_isabel", search_santa_isabel)
    await test("tottus",       search_tottus)
    await test("unimarc",      search_unimarc)

asyncio.run(main())
