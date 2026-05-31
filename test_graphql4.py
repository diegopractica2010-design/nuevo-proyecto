"""Encuentra los campos correctos de priceInfo en el schema actual."""
import asyncio, warnings, json
warnings.filterwarnings("ignore")

GQL = "https://super.lider.cl/orchestra/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://super.lider.cl",
    "Referer": "https://super.lider.cl/search?q=arroz",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

async def try_query(name, q, client):
    payload = {"operationName": "S", "variables": {"q": "arroz", "p": 1, "prg": "desktop"}, "query": q}
    r = await client.post(GQL, json=payload, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        if "errors" not in data:
            return True, data
        msg = data["errors"][0].get("message", "")[:150]
        return False, f"200+err: {msg}"
    body = r.text[:250]
    try:
        msg = json.loads(body)["errors"][0]["message"][:150]
    except Exception:
        msg = body[:100]
    return False, f"400: {msg}"

async def main():
    import httpx

    # Base: itemStacks existe pero priceInfo campos son incorrectos
    # Prueba con solo nombre e imagen primero
    base = "searchResult{itemStacks{items{id name brand image availabilityStatusV2{value display}"

    price_attempts = [
        ("sin priceInfo",         f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base}}}}}}}}}"),
        ("priceInfo{price}",      f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{price}}}}}}}}"),
        ("priceInfo{value}",      f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{value}}}}}}}}"),
        ("priceInfo{offerPrice}", f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{offerPrice}}}}}}}}"),
        ("priceInfo{currentPrice}",f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{currentPrice}}}}}}}}"),
        ("priceInfo{salePrice}",  f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{salePrice}}}}}}}}"),
        ("priceInfo{normalPrice}",f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{normalPrice}}}}}}}}"),
        ("priceInfo{__typename}", f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{base} priceInfo{{__typename}}}}}}}}"),
    ]

    async with httpx.AsyncClient(timeout=15, verify=False) as c:
        for name, q in price_attempts:
            ok, result = await try_query(name, q, c)
            if ok:
                print(f"\nSUCCESS! Campo: {name}")
                print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
                return
            print(f"  {name}: {result}")

asyncio.run(main())
