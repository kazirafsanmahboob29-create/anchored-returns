"""M5: print percentage candidates near ROE terms, without writing research data."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from decimal import Decimal, InvalidOperation
import hashlib
import html
import json
from pathlib import Path
import re
import sys

from src.locate_roe import _read_pages

ALGORITHM_VERSION = "1.0"
ROE = re.compile(
    r"\b(?:ROEs?|returns?[\s-]+on[\s-]+(?:common[\s-]+)?equi(?:[-\u00ad]\s*)?ty|cost[\s-]+of[\s-]+(?:common[\s-]+)?equi(?:[-\u00ad]\s*)?ty(?:[\s-]+capital)?)\b",
    re.I,
)
SMALL = dict(
    zip(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(),
        range(20),
    )
)
TENS = dict(
    zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10))
)
WORDS = "|".join([*SMALL, *TENS, "hundred", "thousand", "half", "quarter"])
WORD_NUMBER = rf"(?:{WORDS})(?:[\s-]+(?:{WORDS}|and|point)){{0,8}}"
DIGIT_NUMBER = r"[+−-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
NUMBER = rf"(?:{DIGIT_NUMBER}|{WORD_NUMBER})"
UNIT = r"(?:percentage\s+points?|basis[\s-]+points?|bps\b|per[\s-]*cent\b|percent\b|[%％])"
# Range recognition precedes standalone recognition: the dash in 8-10% is not a minus.
RANGE = re.compile(
    rf"(?<![\w.$,])(?P<low>{NUMBER})\s*(?:to\b|through\b|[-–\u2014])\s*(?P<high>{NUMBER})[\s-]*(?P<unit>{UNIT})",
    re.I,
)
SINGLE = re.compile(rf"(?<![\w.$,])(?P<number>{NUMBER})[\s-]*(?P<unit>{UNIT})", re.I)
ACTORS = {
    "consumer_advocate": re.compile(
        r"\b(?:OCA|OCC|Office\s+of\s+Consumer\s+Counsel|Attorney\s+General|Consumer\s+Advocate|Public\s+Advocate|ratepayer\s+advocate)\b",
        re.I,
    ),
    "staff": re.compile(
        r"\b(?:staff|DOE|Department\s+of\s+Energy|Department\s+of\s+Public\s+Service)\b", re.I
    ),
    "alj": re.compile(r"\b(?:ALJ|administrative\s+law\s+judge|hearing\s+examiner)\b", re.I),
    "utility": re.compile(
        r"\b(?:compan(?:y|ies)|utilit(?:y|ies)|Eversource|National\s+Grid|NSTAR|CMP|VGS|GMP|PSNH)\b",
        re.I,
    ),
    "commission": re.compile(
        r"\b(?:Commission|Board|PURA|PUC|Authority|Department(?!\s+of\s+(?:Energy|Public\s+Service)))\b",
        re.I,
    ),
}
ABBREVIATION = re.compile(
    r"(?:\b(?:Dr|Mr|Mrs|Ms|Exh|Exhs|No|Nos|Inc|Corp|Co|Id|vs|n)|\b(?:[A-Z]\.)*[A-Z]|\be\.g|\bi\.e)\.$",
    re.I,
)


class NumberFinderError(ValueError):
    """Malformed input; do not substitute guessed values."""


def _decimal(value):
    """Parse a limited, explicit English number grammar; never repair OCR characters."""
    value = value.strip().lower().replace("−", "-")
    if re.fullmatch(DIGIT_NUMBER, value):
        return Decimal(value.replace(",", ""))
    tokens = re.split(r"[\s-]+", value)
    if tokens[:2] in (["one", "half"], ["one", "quarter"]):
        if len(tokens) != 2:
            raise ValueError("Unsupported fraction")
        return Decimal("0.5" if tokens[1] == "half" else "0.25")
    if tokens == ["half"]:
        return Decimal("0.5")
    if tokens == ["quarter"]:
        return Decimal("0.25")
    if tokens.count("point") > 1:
        raise ValueError("Repeated decimal point")
    decimals = []
    if "point" in tokens:
        i = tokens.index("point")
        decimals = tokens[i + 1 :]
        tokens = tokens[:i]
        if not decimals or any(t not in SMALL or SMALL[t] > 9 for t in decimals):
            raise ValueError("Unsupported spoken decimal")
    if not tokens or tokens[0] == "and" or tokens[-1] == "and":
        raise ValueError("Incomplete word number")
    if "and" in tokens and not any(t in tokens for t in ("hundred", "thousand")):
        raise ValueError("Ambiguous number list")
    total = current = 0
    previous = None
    for token in tokens:
        if token == "and":
            continue
        if token in SMALL or token in TENS:
            number = SMALL.get(token, TENS.get(token))
            if previous in SMALL or (previous in TENS and (token in TENS or number >= 10)):
                raise ValueError("Ambiguous adjacent word numbers")
            current += number
        elif token == "hundred":
            if current < 1 or current > 9:
                raise ValueError("Unsupported hundreds")
            current *= 100
        elif token == "thousand":
            if not current:
                raise ValueError("Unsupported thousands")
            total += current * 1000
            current = 0
        else:
            raise ValueError("Unsupported number word")
        previous = token
    value = Decimal(total + current)
    if decimals:
        value += Decimal("0." + "".join(str(SMALL[t]) for t in decimals))
    return value


def _number_string(value):
    return (
        format(value, "f").rstrip("0").rstrip(".")
        if "." in format(value, "f")
        else format(value, "f")
    )


def _unit(raw):
    low = raw.lower()
    if low.startswith(("basis", "bps")):
        return "basis_points"
    if low.startswith("percentage"):
        return "percentage_points"
    return "percent"


def _occurrences(text):
    matches, covered, warnings = [], [], []
    for pattern in (RANGE, SINGLE):
        for match in pattern.finditer(text):
            if any(a < match.end() and match.start() < b for a, b in covered):
                continue
            groups = ("low", "high") if pattern is RANGE else ("number",)
            try:
                values = [_decimal(match[g]) for g in groups]
            except (ValueError, InvalidOperation):
                warnings.append(
                    dict(
                        start_char=match.start(),
                        end_char=match.end(),
                        raw_match=match[0],
                        reason="unsupported_number_expression",
                    )
                )
                continue
            covered.append(match.span())
            for group, value in zip(groups, values):
                start, end = match.span(group)
                inferred = group == "low"
                # Explicit records include their printed unit; implicit range lows
                # point separately to the entire unit-bearing range for provenance.
                if not inferred:
                    end = match.end()
                matches.append(
                    dict(
                        start_char=start,
                        end_char=end,
                        raw_match=text[start:end],
                        value=_number_string(value),
                        unit=_unit(match["unit"]),
                        fraction=_number_string(
                            value / (10000 if _unit(match["unit"]) == "basis_points" else 100)
                        ),
                        unit_inferred_from_range=inferred,
                        unit_evidence=text[match.start() : match.end()],
                        unit_evidence_start_char=match.start(),
                        unit_evidence_end_char=match.end(),
                    )
                )
    return sorted(matches, key=lambda r: r["start_char"]), warnings


def _sentence(text, start, end):
    boundaries = [0]
    for m in re.finditer(r'[.!?](?:[”’"\)]*)\s+|[.!?][”’"\)]*$', text):
        punctuation = m.start()
        if text[punctuation] == ".":
            if (
                punctuation
                and punctuation + 1 < len(text)
                and text[punctuation - 1].isdigit()
                and text[punctuation + 1].isdigit()
            ):
                continue
            if ABBREVIATION.search(text[max(0, punctuation - 20) : punctuation + 1]):
                continue
        boundaries.append(m.end())
    boundaries.append(len(text))
    left = max(b for b in boundaries if b <= start)
    right = min((b for b in boundaries if b >= end), default=len(text))
    while left < start and text[left].isspace():
        left += 1
    while right > end and text[right - 1].isspace():
        right -= 1
    return left, right


def _distance(a, b, c, d):
    return max(c - b, a - d, 0)


def find_numbers(text_json, *, start_page, end_page, window_chars=300):
    """Read M2 JSON and return candidates; all offsets refer to untouched source text."""
    try:
        path = Path(text_json).expanduser().resolve()
        content = path.read_bytes()
        pages = _read_pages(content)
    except (OSError, ValueError, RuntimeError) as error:
        raise NumberFinderError(f"Cannot read valid M2 text: {error}") from error
    if (
        type(start_page) is not int
        or type(end_page) is not int
        or not 1 <= start_page <= end_page <= len(pages)
    ):
        raise NumberFinderError("Invalid inclusive viewer-page range.")
    if type(window_chars) is not int or not 0 <= window_chars <= 10000:
        raise NumberFinderError("window_chars must be an integer from 0 to 10000.")
    selected = pages[start_page - 1 : end_page]
    combined = ""
    starts = []
    for row in selected:
        starts.append(len(combined))
        combined += row["text"] + "\n\f\n"
    terms = list(ROE.finditer(combined))
    rows, unparsed = [], []
    for page_index, page in enumerate(selected):
        text = page["text"]
        base = starts[page_index]
        found, failed = _occurrences(text)
        unparsed.extend(dict(page=page["page"], **r) for r in failed)
        for number in found:
            start, end = number["start_char"], number["end_char"]
            close = [(_distance(base + start, base + end, t.start(), t.end()), t) for t in terms]
            close = [(distance, t) for distance, t in close if distance <= window_chars]
            if not close:
                continue
            distance, term = min(close, key=lambda item: (item[0], item[1].start()))
            term_page_index = bisect_right(starts, term.start()) - 1
            sentence_start, sentence_end = _sentence(text, start, end)
            raw_sentence = text[sentence_start:sentence_end]
            actors = []
            evidence = []
            for role, pattern in ACTORS.items():
                hits = list(pattern.finditer(raw_sentence))
                if hits:
                    actors.append(role)
                    evidence.extend(
                        dict(
                            role=role,
                            text=h[0],
                            start_char=sentence_start + h.start(),
                            end_char=sentence_start + h.end(),
                        )
                        for h in hits
                    )
            flags = ["nearby_number_is_not_necessarily_an_roe_level", "attribution_is_a_heuristic"]
            if page["likely_scanned"]:
                flags.append("low_text_source_page")
            if number["unit"] != "percent":
                flags.append("change_not_level")
            if number["unit_inferred_from_range"]:
                flags.append("unit_shared_by_range")
            if re.search(r"\b(?:reject\w*|not|deny|denied|declin\w*)\b", raw_sentence, re.I):
                flags.append("rejection_or_negation_nearby")
            if len(actors) > 1:
                flags.append("multiple_actors_in_sentence")
            if sentence_start == 0 or sentence_end == len(text):
                flags.append("page_boundary_sentence_may_be_fragment")
            context_start = max(0, base + start - window_chars)
            context_end = min(len(combined), base + end + window_chars)
            context_pages = [
                selected[i]["page"]
                for i, offset in enumerate(starts)
                if offset < context_end and offset + len(selected[i]["text"]) > context_start
            ]
            rows.append(
                dict(
                    candidate_id=f"p{page['page']}:c{start}-{end}",
                    page=page["page"],
                    **number,
                    sentence=" ".join(raw_sentence.split()),
                    sentence_raw=raw_sentence,
                    sentence_start_char=sentence_start,
                    sentence_end_char=sentence_end,
                    sentence_scope="page-bounded sentence or fragment; punctuation heuristic",
                    context=combined[context_start:context_end],
                    context_pages=context_pages,
                    nearest_roe_term=dict(
                        text=term[0],
                        page=selected[term_page_index]["page"],
                        start_char=term.start() - starts[term_page_index],
                        distance_chars=distance,
                    ),
                    attribution_guess=actors[0]
                    if len(actors) == 1
                    else "ambiguous"
                    if actors
                    else "unknown",
                    attribution_candidates=actors,
                    attribution_evidence=evidence,
                    verification_status="candidate_only",
                    flags=flags,
                )
            )
    return dict(
        algorithm_version=ALGORITHM_VERSION,
        status="candidates_only",
        source_path=str(path),
        source_sha256=hashlib.sha256(content).hexdigest(),
        page_numbering="one-based PDF viewer positions",
        character_offsets="zero-based, end-exclusive offsets in original per-page M2 text",
        config=dict(start_page=start_page, end_page=end_page, window_chars=window_chars),
        n_candidates=len(rows),
        candidates=rows,
        unparsed_expressions=unparsed,
        low_text_pages=[r["page"] for r in selected if r["likely_scanned"]],
        limits=[
            "Candidate discovery, not verified research values or automated research coding.",
            "Proximity counts original characters including whitespace and a 3-character page separator.",
            "ROE terms: ROE(s), return(s) on (common) equity, cost of (common) equity (capital).",
            "Recognizes explicit units and simple shared-unit ranges; preserves all occurrences, including non-ROE percentages.",
            "Spelled numbers use a limited English grammar; unsupported/OCR/missing text can hide values.",
            "Sentence and actor guesses are conservative heuristics; source PDF/context determines the actual meaning.",
        ],
    )


def format_table(result):
    def safe(value):
        return html.escape(" ".join(str(value).split()), quote=False).replace("|", "\\|")

    lines = [
        f"Source: {safe(result['source_path'])}",
        f"SHA-256: {result['source_sha256']}",
        "Candidate values only; attribution is a guess. Offsets and exact source text are available with --format json.",
        "",
        "| PDF page | Value | Unit | Attribution guess | Sentence / page fragment |",
        "|---:|---:|---|---|---|",
    ]
    lines.extend(
        "| "
        + " | ".join(safe(r[k]) for k in ("page", "value", "unit", "attribution_guess", "sentence"))
        + " |"
        for r in result["candidates"]
    )
    if not result["candidates"]:
        lines.append("\nNo matching candidates. This does not establish absence of an ROE figure.")
    if result["low_text_pages"]:
        lines.append("\nLow-text source pages: " + ", ".join(map(str, result["low_text_pages"])))
    if result["unparsed_expressions"]:
        lines.append(
            f"\nUnsupported expressions: {len(result['unparsed_expressions'])}; see JSON output."
        )
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text_json", type=Path)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--window-chars", type=int, default=300)
    parser.add_argument("--format", choices=("table", "json"), default="table")
    args = vars(parser.parse_args(argv))
    style = args.pop("format")
    try:
        result = find_numbers(**args)
    except NumberFinderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(result, indent=2, ensure_ascii=False)
        if style == "json"
        else format_table(result),
        end="\n" if style == "json" else "",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
