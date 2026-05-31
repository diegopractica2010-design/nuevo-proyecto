import asyncio
import warnings
warnings.filterwarnings("ignore")

async def main():
    import httpx
    from urllib.parse import quote_plus

    query = "arroz"
    gql_url = "https://super.lider.cl/orchestra/graphql"
    gql_query = (
        "query getSearch($query: String, $page: Int) { "
        "search(query: $query, page: $page) { "
        "itemStacks { items { id name brand image priceInfo { linePrice itemPrice } } } } }"
    )
    payload = {
        "operationName": "getSearch",
        "variables": {"query": query, "page": 1},
        "query": gql_query,
    }

    # Test con Origin Lider
    headers_lider = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://super.lider.cl",
        "Referer": f"https://super.lider.cl/search?q={quote_plus(query)}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    async with httpx.AsyncClient(timeout=20, verify=False) as c:
        r = await c.post(gql_url, json=payload, headers=headers_lider)
        print(f"GraphQL Lider-origin: HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stacks = data.get("data", {}).get("search", {}).get("itemStacks", [])
            total = sum(len(s.get("items", [])) for s in stacks)
            print(f"  Productos: {total}")
            if stacks and stacks[0].get("items"):
                p = stacks[0]["items"][0]
                print(f"  Ejemplo: {p.get('name','')} | price={p.get('priceInfo',{})}")
        else:
            print(f"  Respuesta: {r.text[:200]}")

    # Test con Origin Acuenta
    headers_acuenta = {**headers_lider, "Origin": "https://www.acuenta.cl", "Referer": f"https://www.acuenta.cl/search?q={quote_plus(query)}"}
    async with httpx.AsyncClient(timeout=20, verify=False) as c:
        r2 = await c.post(gql_url, json=payload, headers=headers_acuenta)
        print(f"GraphQL Acuenta-origin: HTTP {r2.status_code}")
        if r2.status_code == 200:
            data2 = r2.json()
            stacks2 = data2.get("data", {}).get("search", {}).get("itemStacks", [])
            total2 = sum(len(s.get("items", [])) for s in stacks2)
            print(f"  Productos: {total2}")
        else:
            print(f"  Respuesta: {r2.text[:200]}")

    # Santa Isabel - buscar API alternativa
    print("\n-- Santa Isabel alternativas --")
    si_apis = [
        ("SI intelligent-search", "https://www.santaisabel.cl/_v/api/intelligent-search/product_search/trade_policy/1", {"query": "arroz", "page": 1, "count": 5}),
        ("SI search api", "https://www.santaisabel.cl/api/io/_v/api/intelligent-search/product_search", {"query": "arroz", "_from": 0, "_to": 4}),
    ]
    for name, url, params in si_apis:
        try:
            async with httpx.AsyncClient(timeout=15, verify=False, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}) as c:
                r = await c.get(url, params=params)
                print(f"{name}: HTTP {r.status_code} | {r.text[:200]}")
        except Exception as e:
            print(f"{name}: ERR {e}")

asyncio.run(main())
