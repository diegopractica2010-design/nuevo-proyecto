import re
import unicodedata


def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9.,]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

