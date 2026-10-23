from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    items: list
    number: int
    total_pages: int


def paginate(items: list, page: int, per_page: int = 10) -> Page:
    """Return the 1-based page `page` of `items`."""
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be >= 1")
    total_pages = max(1, -(-len(items) // per_page))
    start = (page - 1) * per_page
    return Page(items=items[start:start + per_page], number=page, total_pages=total_pages)
