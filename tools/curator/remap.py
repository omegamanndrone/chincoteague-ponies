"""Local-id <-> pedigree-id mapping, loaded from the authoring DB.

Every horse in horses.db carries its pedigree-site id inside qr_pedigree_url
(e.g. ".../pedigree.php?id=166"). This module is the single source of truth for
translating the app's arbitrary local id (1..143) to the website's pedigree_id,
which Phase 1 promotes to the canonical id everywhere.

WHY THIS MATTERS (the id-overlap landmine): 10+ local ids collide with a
*different* horse's pedigree_id, so any remap must be done by lookup against this
table -- never by renumbering in place. See IMPLEMENTATION_PLAN.md §3d.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Repo root is two levels up from tools/curator/.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "horses.db"

_PED_RE = re.compile(r"[?&]id=(\d+)")


@dataclass(frozen=True)
class Horse:
    local_id: int
    pedigree_id: int
    name: str
    sex: str | None


class Remapper:
    """Bidirectional local_id <-> pedigree_id map plus name/sex lookup."""

    def __init__(self, horses: list[Horse]):
        self._by_local: dict[int, Horse] = {h.local_id: h for h in horses}
        self._by_ped: dict[int, Horse] = {h.pedigree_id: h for h in horses}
        if len(self._by_ped) != len(horses):
            raise ValueError("pedigree_id is not unique across horses -- cannot remap")

    @classmethod
    def from_db(cls, db_path: Path | str = DEFAULT_DB) -> "Remapper":
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"authoring DB not found: {db_path}")
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute(
                "SELECT id, name, sex, qr_pedigree_url FROM horses"
            ).fetchall()
        finally:
            con.close()

        horses: list[Horse] = []
        for local_id, name, sex, url in rows:
            m = _PED_RE.search(url or "")
            if not m:
                raise ValueError(
                    f"horse local_id={local_id} ({name!r}) has no pedigree id in "
                    f"qr_pedigree_url={url!r}"
                )
            horses.append(Horse(local_id, int(m.group(1)), name, sex))
        return cls(horses)

    # --- lookups -----------------------------------------------------------
    def to_pedigree(self, local_id: int) -> int:
        return self._by_local[local_id].pedigree_id

    def horse(self, local_id: int) -> Horse:
        return self._by_local[local_id]

    def has_local(self, local_id: int) -> bool:
        return local_id in self._by_local

    def __len__(self) -> int:
        return len(self._by_local)


if __name__ == "__main__":
    rm = Remapper.from_db()
    print(f"loaded {len(rm)} horses from {DEFAULT_DB}")
    # Show a few of the colliding-id cases for sanity.
    for lid in (4, 42, 47):
        if rm.has_local(lid):
            h = rm.horse(lid)
            print(f"  local {h.local_id:>3} -> pedigree {h.pedigree_id:<5} {h.name}")
