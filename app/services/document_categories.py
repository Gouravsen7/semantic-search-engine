"""Fixed document categories used for routing search."""

DOCUMENT_CATEGORIES: tuple[str, ...] = (
    "HR",
    "Legal",
    "Finance",
    "Technical",
    "Policy",
    "General",
)

GENERAL = "General"


def normalize_category(value: str | None) -> str:
    if value is None:
        return GENERAL
    cleaned = value.strip()
    for category in DOCUMENT_CATEGORIES:
        if cleaned.lower() == category.lower():
            return category
    return GENERAL
