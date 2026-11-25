"""Small, rule-based (LLM-free) text helpers.

v0.1 only guesses an E/S/G pillar from a topic name with a keyword list.
A fuller mapping of free text to ESRS topics is on the roadmap.
"""

from __future__ import annotations

_KEYWORDS = {
    "E": (
        "climate", "carbon", "emission", "ghg", "energy", "water", "pollution", "waste",
        "biodiversity", "ecosystem", "circular", "recycl", "material", "packaging", "land",
        "air", "chemical", "substance", "deforestation", "nature", "marine",
    ),
    "G": (
        "governance", "ethic", "corruption", "bribery", "whistle", "board", "lobby",
        "political", "compliance", "tax", "audit", "transparen", "payment practice",
        "business conduct", "risk management", "anti-competitive",
    ),
    "S": (
        "labor", "labour", "worker", "employee", "health", "safety", "diversity", "inclusion",
        "human right", "community", "privacy", "data", "customer", "consumer", "training",
        "wage", "equal", "child", "forced", "wellbeing", "well-being",
    ),
}


def guess_pillar(text: str, default: str = "S") -> str:
    """Guess E, S or G for a topic name; ``default`` if nothing matches."""
    s = str(text).lower()
    hits = {p: sum(k in s for k in kws) for p, kws in _KEYWORDS.items()}
    best = max(hits, key=lambda p: hits[p])
    return best if hits[best] > 0 else default
