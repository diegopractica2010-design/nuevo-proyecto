"""Prueba searchResult como campo anidado dentro de search()."""
import asyncio, warnings
warnings.filterwarnings("ignore")

async def main():
    import httpx, json

    url = "https://super.lider.cl/orchestra/graphql"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://super.lider.cl",
        "Referer": "https://super.lider.cl/search?q=arroz",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    attempts = [
        # searchResult con distintos sub-campos
        ("searchResult.itemStacks",
         "query S($q:String,$p:Int,$prg:Prg!){search(query:$q,page:$p,prg:$prg){searchResult{itemStacks{items{id name brand priceInfo{linePrice itemPrice}}}}}}"),
        ("searchResult.products",
         "query S($q:String,$p:Int,$prg:Prg!){search(query:$q,page:$p,prg:$prg){searchResult{products{id name brand priceInfo{linePrice itemPrice}}}}}"),
        ("searchResult.items",
         "query S($q:String,$p:Int,$prg:Prg!){search(query:$q,page:$p,prg:$prg){searchResult{items{id name brand priceInfo{linePrice itemPrice}}}}}"),
        ("searchResult.__typename",
         "query S($q:String,$p:Int,$prg:Prg!){search(query:$q,page:$p,prg:$prg){searchResult{__typename}}}"),
        # searchResult como query raiz (forma antigua)
        ("root searchResult with prg",
         "query S($q:String,$p:Int,$prg:Prg!){searchResult(query:$q,page:$p,prg:$prg){itemStacks{items{id name}}}}"),
        # search con __typename para ver qué tipo es searchResult
        ("search __typename",
         "query S($q:String,$p:Int,$prg:Prg!){search(query:$q,page:$p,prg:$prg){__typename searchResult{__typename}}}"),
    ]

    for name, q in attempts:
        payload = {"operationName": "S", "variables": {"q": "arroz", "p": 1, "prg": "desktop"}, "query": q}
        async with httpx.AsyncClient(timeout=15, verify=False) as c:
            r = await c.post(url, json=payload, headers=headers)

        if r.status_code == 200:
            data = r.json()
            if "errors" not in data:
                print(f"\nSUCCESS! {name}")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:800])
                return
            else:
                print(f"200 con errores ({name}): {str(data['errors'][0].get('message',''))[:120]}")
        else:
            body = r.text[:200]
            # Extrae el mensaje de error
            try:
                err = json.loads(body)
                msg = err['errors'][0]['message'][:120] if err.get('errors') else body[:80]
            except Exception:
                msg = body[:80]
            print(f"400 ({name}): {msg}")

asyncio.run(main())
