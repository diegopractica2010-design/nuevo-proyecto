"""Busca el campo correcto del schema de Lider con prg requerido."""
import asyncio
import warnings
warnings.filterwarnings("ignore")

async def main():
    import httpx

    url = "https://super.lider.cl/orchestra/graphql"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://super.lider.cl",
        "Referer": "https://super.lider.cl/search?q=arroz",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # Prueba distintos nombres de campo con prg incluido (requerido)
    field_names = [
        "itemStacks { items { id name } }",
        "productStacks { items { id name } }",
        "searchContent { items { id name } }",
        "content { id name }",
        "products { id name }",
        "items { id name }",
        "data { id name }",
        "searchItems { id name }",
        "result { items { id name } }",
        # Probar si funciona un query completamente mínimo (solo __typename)
        "__typename",
    ]

    prg_values = ["desktop", "DESKTOP", "mobile", "app"]

    for prg in prg_values[:2]:  # solo 2 primeros para no hacer demasiadas requests
        for field in field_names:
            q = f"query S($q:String,$p:Int,$prg:Prg!){{search(query:$q,page:$p,prg:$prg){{{field}}}}}"
            payload = {"operationName": "S", "variables": {"q": "arroz", "p": 1, "prg": prg}, "query": q}
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.post(url, json=payload, headers=headers)

            body = r.text[:300]
            if r.status_code == 200:
                print(f"SUCCESS! prg={prg} field={field}: {body[:200]}")
                return
            elif "GRAPHQL_VALIDATION_FAILED" in body and "prg" not in body:
                # prg fue aceptado pero el campo falla
                print(f"prg='{prg}' ACEPTADO, campo '{field.split()[0]}' rechazado: {body[:150]}")
            elif r.status_code != 400:
                print(f"HTTP {r.status_code} prg={prg} field={field[:30]}: {body[:100]}")

asyncio.run(main())
