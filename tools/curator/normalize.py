"""normalize.py — the shared normalization map for the scrape pipeline.

Factored out of reconcile.py so the changeset, merge, and build steps all apply
ONE source of truth for terminology normalization (IMPLEMENTATION_PLAN.md §5,
breadcrumb step 2). Two jobs:

  1. Text/term normalization for *comparing* a book value to a scrape value
     (`norm`, `bucket`) — decides same / spelling / conflict.
  2. Canonical-value rules for what actually ships (`canonical_color`,
     `normalize_coat_pattern`, `sexn`) — e.g. roster color wins, tobiano→pinto.

The headline map entries (from the verified scrape, see `pedigree-site-scraping`
memory): prose says `tobiano` where the roster/app say `pinto` (100% of ~140);
`color` is taken from the roster column (common usage, richer modifiers), never
the prose.
"""

from __future__ import annotations

import re

# prose coat-pattern term -> common-usage term (the app/roster vocabulary).
# parse_pedigree.py already applies this when emitting coat_pattern; kept here so
# the changeset/merge/build layers share the identical map.
PATTERN_NORM = {"tobiano": "pinto"}

# number words the book occasionally spells out (e.g. "fifteen" in a name).
_NUM_WORDS = {"fifteen": "15", "twelve": "12", "eleven": "11", "ten": "10", "two": "2"}


def norm(s: str | None) -> str:
    """Loose normalization for *equality comparison* (not for display)."""
    s = (s or "").lower().strip()
    for w, d in _NUM_WORDS.items():
        s = re.sub(r"\b" + w + r"\b", d, s)
    s = s.replace("&", "and")
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def sexn(s: str | None) -> str:
    """Canonical sex token: book uses mare/stallion, the site uses female/male."""
    s = (s or "").lower()
    if s in ("mare", "female", "filly"):
        return "f"
    if s in ("stallion", "male", "gelding", "colt"):
        return "m"
    return s


def normalize_coat_pattern(p: str | None) -> str | None:
    """tobiano -> pinto, etc. (parse already does this; idempotent here)."""
    if not p:
        return p
    return PATTERN_NORM.get(p.lower().strip(), p)


def canonical_color(roster_color: str | None, prose_color: str | None = None) -> str | None:
    """`color` comes from the ROSTER column (common usage + richer modifiers);
    the prose color is only a fallback when the roster lacks one."""
    return (roster_color or prose_color or None)


def bucket(book_val, new_val) -> str | None:
    """Classify a book value vs a scrape value:
      None       both empty (nothing to say)
      same       identical after normalization
      spelling   one contains the other (case/punct/precision differs; site wins)
      book-only  only the book has a value (don't-clobber: keep it)
      new-only   only the scrape has a value (pure fill)
      CONFLICT   genuinely different — a human should look
    """
    if not book_val and not new_val:
        return None
    if not book_val or not new_val:
        return "new-only" if new_val else "book-only"
    a, b = norm(book_val), norm(new_val)
    if a == b:
        return "same"
    if a in b or b in a:
        return "spelling"
    return "CONFLICT"
