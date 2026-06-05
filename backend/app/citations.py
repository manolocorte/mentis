"""Deterministic, DOI-verified, claim-checked reference handling.

After the agent drafts, we:
  1. find the [n] markers it actually cited,
  2. map them to the REAL retrieved sources (app.sources collector, with abstracts),
  3. verify each DOI resolves (OpenAlex),
  4. run the Validator: does each source's abstract actually support how it's cited?
  5. strip the model's own References and append our verified, claim-checked one.

This is the safeguard against hallucinated AND off-topic citations.
"""
from __future__ import annotations

import json
import re

import httpx

from . import models, prompts
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


def _check_support(draft: str, pairs: list[tuple[int, object]]) -> dict[int, bool | None]:
    """Validator: for each cited source with an abstract, does it support the citation?"""
    with_abs = [(n, s) for n, s in pairs if getattr(s, "abstract", "")]
    if not with_abs:
        return {}
    src_text = "\n\n".join(f"[{n}] {s.title}\nAbstract: {s.abstract}" for n, s in with_abs)
    prompt = (
        f"DRAFT:\n{draft[:6000]}\n\nCITED SOURCES (abstracts):\n{src_text}\n\n"
        "Return ONLY a JSON object mapping each source number to true/false/null."
    )
    try:
        raw = models.converse_text(
            prompts.VALIDATOR_SYSTEM, prompt, models.validator_models(), max_tokens=400
        )
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
        return {int(k): (None if v is None else bool(v)) for k, v in data.items()}
    except Exception:  # noqa: BLE001
        return {}


def finalize_with_references(text: str) -> tuple[str, list[dict]]:
    """Return (text_with_verified_references, citation_records). Network-bound — call via to_thread."""
    coll = current()
    cited = _cited_numbers(text)
    body = _strip_model_refs(text)

    pairs = [(n, coll.items[n - 1]) for n in cited if 1 <= n <= len(coll.items)]
    for _, s in pairs:
        s.verified = _verify_doi(s.doi)
    verdicts = _check_support(body, pairs)

    records: list[dict] = []
    lines = ["", "## References", ""]
    for n in cited:
        if 1 <= n <= len(coll.items):
            s = coll.items[n - 1]
            supp = verdicts.get(n)
            s.supported = supp
            doi_txt = f" https://doi.org/{s.doi}" if s.doi else ""
            if supp is False:
                flag = "  *[⚠ source may not support this claim]*"
            elif not s.verified:
                flag = "  *[DOI unverified]*" if s.doi else "  *[no DOI]*"
            else:
                flag = ""
            lines.append(f"[{n}] {s.authors} ({s.year}). {s.title}. {s.venue}.{doi_txt}{flag}")
            records.append(
                {
                    "n": n, "title": s.title, "authors": s.authors, "year": s.year,
                    "doi": s.doi, "verified": s.verified, "supported": supp,
                }
            )
        else:
            lines.append(f"[{n}] *(unsupported — not in retrieved sources)*")
            records.append({"n": n, "title": None, "verified": False, "supported": False, "unsupported": True})

    if len(lines) <= 3:
        return body, records
    return body + "\n" + "\n".join(lines), records
