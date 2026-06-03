import asyncio, os, sys, time
os.environ["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
sys.path.insert(0, ".")
from backend.search_service import search_products

# Queries EXACTAS de la lista de compras del usuario
QUERIES = ["arroz 1 kilo", "leche entera 1 litro", "aceite 1 litro"]

async def one(store, q):
    t = time.time()
    try:
        r = await asyncio.wait_for(search_products(q, limit=10, store=store), timeout=12)
        el = time.time() - t
        ej = f"${int(r.results[0].price)} {r.results[0].name[:30]}" if r.results else "0 RESULTADOS"
        warn = (r.warning or "")[:55]
        return f"{store:13} {r.count}p {el:4.1f}s  {ej}  {('WARN:'+warn) if warn else ''}"
    except asyncio.TimeoutError:
        return f"{store:13} TIMEOUT >12s (se corta en el compare)"
    except Exception as e:
        return f"{store:13} ERROR {type(e).__name__}: {str(e)[:45]}"

async def main():
    for q in QUERIES:
        print(f"\n### '{q}' ###")
        for store in ["lider", "jumbo", "santa_isabel"]:
            print("  " + await one(store, q))

asyncio.run(main())
