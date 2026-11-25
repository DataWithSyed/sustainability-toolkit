"""ESRS topical standards and sustainability matters.

The list follows ESRS 1 *General requirements*, Appendix A, Application
Requirement AR 16 (the list of sustainability matters covered in topical
ESRS), as adopted in Commission Delegated Regulation (EU) 2023/2772.
Only topics and sub-topics are listed here; sub-sub-topics are left for a
later release. Wording is shortened in places for readability.
"""

from __future__ import annotations

ESRS_TOPICS: dict[str, dict[str, object]] = {
    "E1": {
        "name": "Climate change",
        "pillar": "E",
        "subtopics": [
            "Climate change adaptation",
            "Climate change mitigation",
            "Energy",
        ],
    },
    "E2": {
        "name": "Pollution",
        "pillar": "E",
        "subtopics": [
            "Pollution of air",
            "Pollution of water",
            "Pollution of soil",
            "Pollution of living organisms and food resources",
            "Substances of concern",
            "Substances of very high concern",
            "Microplastics",
        ],
    },
    "E3": {
        "name": "Water and marine resources",
        "pillar": "E",
        "subtopics": ["Water", "Marine resources"],
    },
    "E4": {
        "name": "Biodiversity and ecosystems",
        "pillar": "E",
        "subtopics": [
            "Direct impact drivers of biodiversity loss",
            "Impacts on the state of species",
            "Impacts on the extent and condition of ecosystems",
            "Impacts and dependencies on ecosystem services",
        ],
    },
    "E5": {
        "name": "Resource use and circular economy",
        "pillar": "E",
        "subtopics": [
            "Resources inflows, including resource use",
            "Resource outflows related to products and services",
            "Waste",
        ],
    },
    "S1": {
        "name": "Own workforce",
        "pillar": "S",
        "subtopics": [
            "Working conditions",
            "Equal treatment and opportunities for all",
            "Other work-related rights",
        ],
    },
    "S2": {
        "name": "Workers in the value chain",
        "pillar": "S",
        "subtopics": [
            "Working conditions",
            "Equal treatment and opportunities for all",
            "Other work-related rights",
        ],
    },
    "S3": {
        "name": "Affected communities",
        "pillar": "S",
        "subtopics": [
            "Communities' economic, social and cultural rights",
            "Communities' civil and political rights",
            "Rights of indigenous peoples",
        ],
    },
    "S4": {
        "name": "Consumers and end-users",
        "pillar": "S",
        "subtopics": [
            "Information-related impacts for consumers and/or end-users",
            "Personal safety of consumers and/or end-users",
            "Social inclusion of consumers and/or end-users",
        ],
    },
    "G1": {
        "name": "Business conduct",
        "pillar": "G",
        "subtopics": [
            "Corporate culture",
            "Protection of whistle-blowers",
            "Animal welfare",
            "Political engagement and lobbying activities",
            "Management of relationships with suppliers including payment practices",
            "Corruption and bribery",
        ],
    },
}

#: Code used for entity-specific topics that are not covered by a topical ESRS.
ENTITY_SPECIFIC = "ENTITY"

PILLARS = {"E": "Environmental", "S": "Social", "G": "Governance"}


def pillar_for(esrs_code: str) -> str | None:
    """Return the E/S/G pillar for an ESRS topical code such as ``"E1"``."""
    entry = ESRS_TOPICS.get(str(esrs_code).strip().upper())
    return None if entry is None else str(entry["pillar"])


def is_known_code(esrs_code: str) -> bool:
    code = str(esrs_code).strip().upper()
    return code in ESRS_TOPICS or code == ENTITY_SPECIFIC
