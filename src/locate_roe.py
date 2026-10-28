"""M3: rank suggested ROE page ranges from M2 JSON; never write research data."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata


ALGORITHM_VERSION = "1.0"
# Scores are transparent search heuristics, not fitted probabilities.
TERM_WEIGHTS = {
    "return on equity": 5,
    "cost of equity": 4,
    "cost of capital": 2,
    "ROE": 2,
    "proxy group": 2,
    "DCF": 1,
    "CAPM": 1,
}
TERM_PATTERNS = dict(
    zip(
        TERM_WEIGHTS,
        map(
            lambda pattern: re.compile(pattern, re.I),
            [
                r"\breturn\s+on\s+(?:common\s+)?equity\b",
                r"\bcost\s+of\s+equity\b",
                r"\bcost\s+of\s+capital\b",
                r"\broes?\b",
                r"\bproxy\s+groups?\b",
                r"\bdcf\b",
                r"\be?capm\b",
            ],
        ),
    )
)
HEADING_BONUSES = {"return on equity": 12, "cost of equity": 10, "cost of capital": 6}
HEADING = re.compile(
    r"^(?:(?:[a-z]|[ivxlcdm]+|\d+(?:\.\d+)*)(?:[.)])?\s+)?"
    r"(return on (?:common )?equity|cost of equity(?: capital)?|cost of capital)"
    r"(?:\s*\(roe\))?\s*:?$",
    re.I,
)
LEADER = re.compile(r"\.{3,}\s*(?:\d+|[ivxlcdm]+)\s*$", re.I)
PAGE_FIELDS = {"page", "text", "n_chars", "likely_scanned"}


class LocatorError(ValueError):
    """Invalid input or configuration; no plausible substitute is returned."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LocatorError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_pages(content: bytes) -> list[dict]:
    try:
        pages = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as error:
        raise LocatorError(f"Invalid text JSON: {error}") from error
    if not isinstance(pages, list) or not pages:
        raise LocatorError("M2 text JSON must be a nonempty list of page records.")
    for expected, row in enumerate(pages, 1):
        if not isinstance(row, dict) or set(row) != PAGE_FIELDS:
            raise LocatorError(f"Invalid page schema at position {expected}.")
        if type(row["page"]) is not int or row["page"] != expected:
            raise LocatorError("page must be an integer in contiguous viewer order starting at 1.")
        if not isinstance(row["text"], str):
            raise LocatorError(f"text must be a string on page {expected}.")
        if type(row["n_chars"]) is not int or row["n_chars"] != len(row["text"]):
            raise LocatorError(f"n_chars does not match text on page {expected}.")
        if type(row["likely_scanned"]) is not bool:
            raise LocatorError(f"likely_scanned must be boolean on page {expected}.")
    return pages


def _search_text(text: str) -> str:
    # Matching-only normalization. The M2 file and its excerpts are never edited.
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    return re.sub(r"(?<=\w)[-\u2010]\s*\n\s*(?=\w)", "", text)


def _lines(text: str) -> list[str]:
    return [" ".join(line.split()).casefold() for line in text.splitlines() if line.strip()]


def _score_pages(pages: list[dict]) -> tuple[list[dict], list[str]]:
    texts = [_search_text(row["text"]) for row in pages]
    edges = Counter()
    for text in texts:
        lines = _lines(text)
        # Short repeated edge lines without sentence punctuation are potential headers.
        edges.update(
            {
                line
                for line in lines[:2] + lines[-2:]
                if len(line) <= 80 and not re.search(r"[.!?;]", line)
            }
        )
    repeated = {line for line, count in edges.items() if count >= 3}
    scored = []
    for row, text in zip(pages, texts):
        lines = _lines(text)
        contents = (
            any(line in {"contents", "table of contents"} for line in lines)
            or sum(bool(LEADER.search(line)) for line in lines) >= 2
        )
        kept = [
            line
            for i, line in enumerate(lines)
            if not (line in repeated and (i < 2 or i >= len(lines) - 2))
        ]
        searchable = "\n".join(kept)
        counts = {term: len(pattern.findall(searchable)) for term, pattern in TERM_PATTERNS.items()}
        headings = []
        for line in kept:
            match = HEADING.fullmatch(line)
            if match:
                kind = match[1].replace("common ", "")
                if kind == "cost of equity capital":
                    kind = "cost of equity"
                if kind not in headings:
                    headings.append(kind)
        keyword_score = sum(TERM_WEIGHTS[term] * min(count, 3) for term, count in counts.items())
        bonus = max((HEADING_BONUSES[h] for h in headings), default=0)
        scored.append(
            dict(
                page=row["page"],
                score=0 if contents else keyword_score + bonus,
                term_counts=counts,
                headings=[] if contents else headings,
                likely_contents=contents,
                likely_scanned=row["likely_scanned"],
            )
        )
    return scored, sorted(repeated)


def _candidate(cluster: list[int], scored: list[dict]) -> dict:
    context_start, end = cluster[0], cluster[-1]
    # Prefer a specific equity heading to a preceding capital/debt/proxy discussion.
    equity = [
        i
        for i in cluster
        if any(h in {"return on equity", "cost of equity"} for h in scored[i - 1]["headings"])
    ]
    start = equity[0] if equity else context_start
    section = scored[start - 1 : end]
    total = sum(row["score"] for row in section)
    counts = {term: sum(row["term_counts"][term] for row in section) for term in TERM_WEIGHTS}
    headings = [row["page"] for row in section if row["headings"]]
    return dict(
        start_page=start,
        end_page=end,
        context_start_page=context_start,
        score=round(total / math.sqrt(len(section)), 6),
        score_sum=total,
        n_pages=len(section),
        term_counts=counts,
        heading_pages=headings,
        evidence_pages=[i for i in cluster if i >= start],
        gap_pages=[row["page"] for row in section if row["page"] not in cluster],
        low_text_pages=[row["page"] for row in section if row["likely_scanned"]],
        page_scores=[dict(page=row["page"], score=row["score"]) for row in section],
        boundary_method="first specific equity heading to last qualifying page"
        if equity
        else "first to last qualifying page; no specific equity heading",
    )


def locate_roe(
    text_json: str | Path, *, top_n: int = 5, max_gap_pages: int = 2, min_page_score: int = 4
) -> dict:
    """Return reproducible, explained candidate ranges without writing any file.

    Defaults are initial pilot heuristics. There is no confirmed range or human hit
    statistic until a separate review records one against the source PDF.
    """
    for name, value, minimum in [
        ("top_n", top_n, 1),
        ("max_gap_pages", max_gap_pages, 0),
        ("min_page_score", min_page_score, 1),
    ]:
        if type(value) is not int or value < minimum:
            raise LocatorError(f"{name} must be an integer >= {minimum}.")
    try:
        path = Path(text_json).expanduser().resolve()
        content = path.read_bytes()
        pages = _read_pages(content)
    except (OSError, RuntimeError, ValueError) as error:
        if isinstance(error, LocatorError):
            raise
        raise LocatorError(f"Cannot read text JSON: {error}") from error
    scored, repeated = _score_pages(pages)
    clusters, current = [], []
    for row in scored:
        number = row["page"]
        if row["likely_contents"]:
            if current:
                clusters.append(current)
                current = []
            continue
        if row["score"] < min_page_score:
            continue
        if current and number - current[-1] > max_gap_pages + 1:
            clusters.append(current)
            current = []
        current.append(number)
    if current:
        clusters.append(current)
    candidates = [_candidate(cluster, scored) for cluster in clusters]
    candidates.sort(key=lambda c: (-c["score"], c["start_page"], c["end_page"]))
    low_text = [row["page"] for row in scored if row["likely_scanned"]]
    warnings = [
        "Heuristic page boundaries can omit context or include unrelated text; inspect the PDF."
    ]
    if low_text:
        warnings.append(
            "Low-text flags are present; missing or erroneous text can hide relevant sections."
        )
    if not candidates:
        warnings.append(
            "No range meets the threshold. This does not establish absence of ROE discussion."
        )
    return dict(
        algorithm_version=ALGORITHM_VERSION,
        status="suggestions_only",
        source_path=str(path),
        source_sha256=hashlib.sha256(content).hexdigest(),
        n_pages=len(pages),
        page_numbering="one-based PDF viewer positions",
        config=dict(
            top_n=top_n,
            max_gap_pages=max_gap_pages,
            min_page_score=min_page_score,
            term_weights=dict(TERM_WEIGHTS),
            per_term_count_cap=3,
            heading_bonuses=dict(HEADING_BONUSES),
            ranking="sum(page scores) / sqrt(range page count); earlier page breaks ties",
        ),
        total_candidates=len(candidates),
        candidates=[dict(rank=i, **candidate) for i, candidate in enumerate(candidates[:top_n], 1)],
        suppressed_contents_pages=[row["page"] for row in scored if row["likely_contents"]],
        suppressed_repeated_edge_lines=repeated,
        low_text_pages=low_text,
        warnings=warnings,
        confirmed_range=None,
        human_top_hit=None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text_json", type=Path)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--max-gap-pages", type=int, default=2)
    parser.add_argument("--min-page-score", type=int, default=4)
    try:
        result = locate_roe(**vars(parser.parse_args(argv)))
    except LocatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
