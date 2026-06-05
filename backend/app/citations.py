"""Deterministic, DOI-verified reference handling.

After the agent drafts, we:
  1. find the [n] markers it actually cited,
  2. map them to the REAL retrieved sources (app.sources collector),
  3. verify each DOI resolves (OpenAlex),
  4. strip the model's own References section and append our verified one.

This is the safeguard against hallucinated citations.
"""
from __future__ import annotations

import re

import httpx

from .sources import current

_CITE_GROUP = re.compile(r"\[([0-9][0-9,\s–—-]*)\]")
_REF_HEADING = re.compile(r"(?im)^\s*(?:#+\s*)?(?:\*\*)?\s*references\s*(?:\*\*)?\s*:?\s*$")
_UA = {"User-Agent": "Mentis/0.1 (mailto:research@example.org)"}


def _cited_numbers(text: str) -> list[int]:
    """Extract all cited indices, handling grouped/ranged forms: [1], [1, 2], [3-5]."""
    nums: set[int] = set()
    for group in _CITE_GROUP.findall(text):
        for part in re.split(r"[,\s]+", group.strip()):
            if not part:
                continue
            if part.isdigit():
                nums.add(int(part))
                continue
            m = re.match(r"^(\d+)[–—-](\d+)$", part)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if 0 < hi - lo < 50:
                    nums.update(range(lo, hi + 1))
    return sorted(nums)


def _verify_doi(doi: str) -> bool:
    if not doi:
        return False
    try:
        r = httpx.get(f"https://api.openalex.org/works/doi:{doi}", headers=_UA, timeout=12)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _strip_model_refs(text: str) -> str:
    last = None
    for m in _REF_HEADING.finditer(text):
        last = m
    return text[: last.start()].rstrip() if last else text.rstrip()


def finalize_with_references(text: str) -> tuple[str, list[dict]]:
    """Return (text_with_verified_references, citation_records).

    Network-bound (verifies DOIs) — call via asyncio.to_thread.
    """
    coll = current()
    cited = _cited_numbers(text)
    body = _strip_model_refs(text)

    records: list[dict] = []
    lines = ["", "## References", ""]
    for n in cited:
        if 1 <= n <= len(coll.items):
            s = coll.items[n - 1]
            ok = _verify_doi(s.doi)
            s.verified = ok
            doi_txt = f" https://doi.org/{s.doi}" if s.doi else ""
            flag = "" if ok else ("  *[DOI unverified]*" if s.doi else "  *[no DOI]*")
            lines.append(f"[{n}] {s.authors} ({s.year}). {s.title}. {s.venue}.{doi_txt}{flag}")
            records.append(
                {
                    "n": n,
                    "title": s.title,
                    "authors": s.authors,
                    "year": s.year,
                    "doi": s.doi,
                    "verified": ok,
                }
            )
        else:
            lines.append(f"[{n}] *(unsupported — not in retrieved sources)*")
            records.append({"n": n, "title": None, "verified": False, "unsupported": True})

    if len(lines) <= 3:  # nothing citable resolved
        return body, records
    return body + "\n" + "\n".join(lines), records
