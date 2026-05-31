"""Encuentra la estructura correcta de priceInfo con campos anidados."""
import asyncio, warnings, json
warnings.filterwarnings("ignore")

GQL = "https://super.lider.cl/orchestra/graphql"
HEADERS = {
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": "https://super.lider.cl", "Referer": "https://super.lider.cl/search?q=arroz",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
VARS = {"q": "arroz", "p": 1, "prg": "desktop"}

QUERIES = {
    "currentPrice{value}": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { currentPrice { value } }
            }}}}}
    """,
    "currentPrice{price}": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { currentPrice { price } }
            }}}}}
    """,
    "currentPrice{amount}": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { currentPrice { amount } }
            }}}}}
    """,
    "linePrice{value}": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { linePrice { value } }
            }}}}}
    """,
    "linePrice{price}": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { linePrice { price } }
            }}}}}
    """,
    "wasPrice scalar": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { wasPrice }
            }}}}}
    """,
    "basePrice scalar": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand
              priceInfo { basePrice }
            }}}}}
    """,
    "full currentPrice+linePrice+wasPrice": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult { itemStacks { items { id name brand image
              canonicalUrl sellerName
              availabilityStatusV2 { value display }
              priceInfo {
                currentPrice { value }
                linePrice { value }
                wasPrice
                basePrice
              }
            }}}}}
    """,
}

async def main():
    import httpx

    async with httpx.AsyncClient(timeout=20, verify=False) as c:
        for name, q in QUERIES.items():
            r = await c.post(GQL, json={"operationName": "S", "variables": VARS, "query": q}, headers=HEADERS)
            if r.status_code == 200:
                data = r.json()
                if "errors" not in data:
                    print(f"\nSUCCESS: {name}")
                    stacks = data.get("data", {}).get("search", {}).get("searchResult", {}).get("itemStacks", [])
                    items = stacks[0].get("items", []) if stacks else []
                    if items:
                        print(f"  Producto 0: {json.dumps(items[0], ensure_ascii=False)}")
                    print(f"  Total stacks: {len(stacks)}, items[0]: {len(items)}")
                    if name == "full currentPrice+linePrice+wasPrice":
                        return  # ya encontramos el esquema completo
                else:
                    msg = data["errors"][0].get("message", "")[:150]
                    print(f"  FAIL {name}: {msg}")
            else:
                try:
                    msg = r.json()["errors"][0]["message"][:150]
                except Exception:
                    msg = r.text[:80]
                print(f"  {r.status_code} {name}: {msg}")

asyncio.run(main())
