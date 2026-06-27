QUERY_STOPWORDS: frozenset[str] = frozenset(
    {
        "barata",
        "barato",
        "bolsa",
        "con",
        "de",
        "del",
        "el",
        "en",
        "la",
        "las",
        "los",
        "mas",
        "o",
        "opcion",
        "pack",
        "paquete",
        "para",
        "por",
        "saco",
        "un",
        "una",
        "unas",
        "unos",
        "y",
        # ponytail: palabras de envase/formato; describen el empaque, no el producto,
        # así que no deben bloquear el match (caso "Detergente Líquido Bidón").
        "bidon",
        "botella",
        "caja",
        "envase",
        "frasco",
        "lata",
        "pote",
        "sachet",
        "tarro",
        "doypack",
    }
)

CHARCOAL_TERMS: frozenset[str] = frozenset(
    {
        "briqueta",
        "briquetas",
        "espino",
        "parrilla",
        "quebracho",
        "quincho",
        "vegetal",
    }
)
