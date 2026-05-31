"""Encuentra los campos de priceInfo con queries bien formados."""
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
    "minimal (id+name only)": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand }
              }
            }
          }
        }
    """,
    "priceInfo.price": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { price } }
              }
            }
          }
        }
    """,
    "priceInfo.salePrice": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { salePrice } }
              }
            }
          }
        }
    """,
    "priceInfo.offerPrice": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { offerPrice } }
              }
            }
          }
        }
    """,
    "priceInfo.currentPrice": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { currentPrice } }
              }
            }
          }
        }
    """,
    "priceInfo.linePrice+itemPrice": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { linePrice itemPrice } }
              }
            }
          }
        }
    """,
    "priceInfo.__typename": """
        query S($q:String,$p:Int,$prg:Prg!) {
          search(query:$q, page:$p, prg:$prg) {
            searchResult {
              itemStacks {
                items { id name brand priceInfo { __typename } }
              }
            }
          }
        }
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
                    print(f"\nSUCCESS! {name}")
                    # Muestra primer producto
                    stacks = data.get("data", {}).get("search", {}).get("searchResult", {}).get("itemStacks", [])
                    items = stacks[0].get("items", []) if stacks else []
                    if items:
                        print(f"  Primer producto: {json.dumps(items[0], ensure_ascii=False)}")
                    print(f"  Total items en stack 0: {len(items)}, stacks: {len(stacks)}")
                    return
                else:
                    msg = data["errors"][0].get("message", "")[:120]
                    print(f"  {name}: 200+err: {msg}")
            else:
                try:
                    msg = r.json()["errors"][0]["message"][:120]
                except Exception:
                    msg = r.text[:100]
                print(f"  {name}: {r.status_code}: {msg}")

asyncio.run(main())
