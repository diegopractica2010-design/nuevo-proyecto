"""Descubre el schema GraphQL actual de Lider y prueba queries alternativas."""
import asyncio
import warnings
warnings.filterwarnings("ignore")

async def main():
    import httpx, json
    from urllib.parse import quote_plus

    url = "https://super.lider.cl/orchestra/graphql"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://super.lider.cl",
        "Referer": "https://super.lider.cl/search?q=arroz",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # 1. Introspección: qué tipos existen en el schema
    introspect = {
        "operationName": "IntrospectionQuery",
        "variables": {},
        "query": "{ __schema { queryType { fields { name description } } } }",
    }
    async with httpx.AsyncClient(timeout=20, verify=False) as c:
        r = await c.post(url, json=introspect, headers=headers)
        print(f"Introspection: HTTP {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            fields = d.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
            print(f"  Query fields: {[f['name'] for f in fields]}")

    # 2. Intenta query con 'products' en vez de 'itemStacks'
    queries_to_try = [
        ("products field", "query S($q:String,$p:Int){search(query:$q,page:$p){products{id name brand priceInfo{linePrice itemPrice}}}}"),
        ("items field",    "query S($q:String,$p:Int){search(query:$q,page:$p){items{id name brand priceInfo{linePrice itemPrice}}}}"),
        ("results field",  "query S($q:String,$p:Int){search(query:$q,page:$p){results{id name brand}}}"),
        ("data field",     "query S($q:String,$p:Int){search(query:$q,page:$p){data{id name brand}}}"),
        # Introspect the SearchViewResponse type
        ("introspect SearchViewResponse", "{ __type(name:\"SearchViewResponse\") { fields { name type { name kind ofType { name } } } } }"),
    ]

    for name, q in queries_to_try:
        payload = {"operationName": "S", "variables": {"q": "arroz", "p": 1}, "query": q}
        async with httpx.AsyncClient(timeout=15, verify=False) as c:
            r = await c.post(url, json=payload, headers=headers)
            body = r.text[:400]
            print(f"\n{name}: HTTP {r.status_code}")
            print(f"  {body}")

asyncio.run(main())
