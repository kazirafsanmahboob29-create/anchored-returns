"""Blinded coding materials and agreement from documented separate observations."""

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .research_ledger import CODES, fingerprint, local_path, require, validate_ledger
from .reliability import binary_agreement

TARGET_CODES = ("MKT", "PEER", "OWN", "GRAD", "CONC")
PACKET_ID = "three-orders-2026-10-02"


def build_packet(root):
    root = Path(root)
    manifest_path = root / "data/research/reliability" / PACKET_ID / "manifest.json"
    baseline_dir = root / "data/research/reliability_baselines"
    snapshot_path = baseline_dir / (PACKET_ID + ".ledger.json")
    ledger_path = (
        local_path(root, json.loads(manifest_path.read_text())["ledger_path"])
        if manifest_path.exists()
        else root / "data/research/empirical_ledger_v0.1.3.json"
    )
    validate_ledger(ledger_path, root=root)
    ledger = json.loads(ledger_path.read_text())
    complete = {
        c["case_id"] for c in ledger["cases"] if c["coding_status"] == "first_pass_complete"
    }
    require(len(complete) == 3, "This packet is defined for the three completed first-pass orders")
    sources = {s["source_id"]: s for s in ledger["sources"]}
    # Order is determined by IDs, not observed labels or agreement.
    passages = sorted(
        (p for p in ledger["passages"] if p["case_id"] in complete),
        key=lambda p: sha256((PACKET_ID + p["passage_id"]).encode()).hexdigest(),
    )
    units, reference = [], []
    for i, p in enumerate(passages, 1):
        uid = f"R{i:03d}"
        s = sources[p["source_id"]]
        rows = json.loads(local_path(root, s["text_path"]).read_text())
        pages = sorted({span["page"] for span in p["spans"]})
        units.append(
            dict(
                unit_id=uid,
                text=p["text"],
                source_url=s["source_url"],
                pdf_sha256=s["pdf_sha256"],
                pages=pages,
                context=[dict(page=n, text=rows[n - 1]["text"]) for n in pages],
            )
        )
        reference.append(
            dict(
                unit_id=uid,
                passage_id=p["passage_id"],
                case_id=p["case_id"],
                codes=p["codes"],
                coding_date=p.get("coding_date", ledger["coding_date"]),
            )
        )
    codebook = root / "project_docs/Anchored_Returns_Codebook_v0.1.2.docx"
    amendment = root / "docs/empirical_protocol_v0.1.3.md"
    packet = dict(
        schema_version="1.0",
        packet_id=PACKET_ID,
        codes=list(CODES),
        units=units,
        order_count=3,
        unit_count=len(units),
        codebook_version=ledger["codebook_version"],
        codebook_sha256=fingerprint(codebook),
        amendment_sha256=fingerprint(amendment),
        sampling="All recorded units from the three complete first-pass ROE sections, including zero-code units. No selection by code presence.",
        unit_order="SHA-256 of fixed packet identity plus original unit ID",
        limits="Agreement on these three orders does not establish reliability for the final 15-order sample. Shared units within orders are not independent cases.",
    )
    directory = root / "data/research/reliability" / PACKET_ID / "rater"
    directory.mkdir(parents=True, exist_ok=True)
    baseline_dir.mkdir(parents=True, exist_ok=True)
    if snapshot_path.exists():
        require(
            snapshot_path.read_bytes() == ledger_path.read_bytes(),
            "Frozen coding ledger snapshot changed",
        )
    else:
        snapshot_path.write_bytes(ledger_path.read_bytes())
    packet_path = directory / "packet.json"
    content = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
    if packet_path.exists():
        require(
            packet_path.read_text() == content, "Frozen packet differs; create a new packet version"
        )
    else:
        packet_path.write_text(content)
    packet_hash = fingerprint(packet_path)
    baseline = dict(
        packet_id=PACKET_ID,
        packet_sha256=packet_hash,
        ledger_sha256=fingerprint(ledger_path),
        coder=ledger["coder"],
        rater_kind="assistant",
        codebook_version=ledger["codebook_version"],
        reference_ratings=reference,
    )
    baseline_path = baseline_dir / (PACKET_ID + ".json")
    baseline_content = json.dumps(baseline, indent=2) + "\n"
    if baseline_path.exists():
        require(
            baseline_path.read_text() == baseline_content, "Frozen first-pass reference changed"
        )
    else:
        baseline_path.write_text(baseline_content)
    frozen_at = (
        json.loads(manifest_path.read_text())["frozen_at_utc"]
        if manifest_path.exists()
        else datetime.now(timezone.utc).isoformat()
    )
    manifest = dict(
        packet_id=PACKET_ID,
        packet_path=str(packet_path.relative_to(root)),
        packet_sha256=packet_hash,
        baseline_path=str(baseline_path.relative_to(root)),
        baseline_sha256=fingerprint(baseline_path),
        ledger_sha256=fingerprint(ledger_path),
        ledger_path=str(snapshot_path.relative_to(root)),
        units=len(units),
        orders=3,
        frozen_at_utc=frozen_at,
    )
    manifest_content = json.dumps(manifest, indent=2) + "\n"
    if manifest_path.exists():
        require(manifest_path.read_text() == manifest_content, "Frozen packet manifest changed")
    else:
        manifest_path.write_text(manifest_content)
    blank = dict(
        schema_version="1.0",
        packet_id=PACKET_ID,
        packet_sha256=packet_hash,
        rater=dict(
            identity="",
            kind="human",
            started_at_utc=None,
            completed_at_utc=None,
            did_not_consult_reference_labels=None,
            notes="",
        ),
        ratings=[
            dict(unit_id=u["unit_id"], codes=dict.fromkeys(CODES, None), notes="") for u in units
        ],
    )
    (directory / "ratings_blank.json").write_text(json.dumps(blank, indent=2) + "\n")
    template = (root / "presentation/reliability.html").read_text()
    require(
        template.count("__PACKET__") == template.count("__BLANK__") == 1,
        "Reliability template slots differ",
    )
    encode = lambda value: (
        json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    )
    (directory / "index.html").write_text(
        template.replace("__PACKET__", encode(packet)).replace("__BLANK__", encode(blank))
    )
    return packet_status(root)


def packet_status(root):
    """Validate frozen inputs without creating or completing any ratings."""
    root = Path(root)
    manifest_path = root / "data/research/reliability" / PACKET_ID / "manifest.json"
    if not manifest_path.exists():
        return dict(status="packet_not_built", units=0, orders=0)
    manifest = json.loads(manifest_path.read_text())
    require(manifest["packet_id"] == PACKET_ID, "Frozen packet manifest identity differs")
    packet_path = local_path(root, manifest["packet_path"])
    baseline_path = local_path(root, manifest["baseline_path"])
    require(fingerprint(packet_path) == manifest["packet_sha256"], "Frozen rater packet changed")
    require(
        fingerprint(baseline_path) == manifest["baseline_sha256"],
        "Frozen first-pass reference changed",
    )
    ledger_path = local_path(root, manifest["ledger_path"])
    require(fingerprint(ledger_path) == manifest["ledger_sha256"], "Frozen coding ledger changed")
    validate_ledger(ledger_path, root=root)
    packet = json.loads(packet_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    require(
        baseline["packet_sha256"] == manifest["packet_sha256"]
        and baseline["ledger_sha256"] == manifest["ledger_sha256"],
        "First-pass reference identifies different inputs",
    )
    require(
        fingerprint(root / "project_docs/Anchored_Returns_Codebook_v0.1.2.docx")
        == packet["codebook_sha256"]
        and fingerprint(root / "docs/empirical_protocol_v0.1.3.md") == packet["amendment_sha256"],
        "Packet codebook or amendment changed",
    )
    ids = {u["unit_id"] for u in packet["units"]}
    require(
        len(ids) == len(packet["units"]) == packet["unit_count"] == manifest["units"],
        "Frozen packet unit count differs",
    )
    require(packet["order_count"] == manifest["orders"] == 3, "Frozen packet order count differs")
    require(set(packet["codes"]) == set(CODES), "Frozen packet code list differs")
    require(
        all(
            set(u) == {"unit_id", "text", "source_url", "pdf_sha256", "pages", "context"}
            for u in packet["units"]
        ),
        "Rater packet contains reference labels or coding metadata",
    )
    require(
        {r["unit_id"] for r in baseline["reference_ratings"]} == ids
        and len(baseline["reference_ratings"]) == len(ids),
        "Reference units differ from the packet",
    )
    return dict(
        status="awaiting_independent_observations",
        packet_id=PACKET_ID,
        units=len(ids),
        orders=3,
        rater_workspace=str((packet_path.parent / "index.html").relative_to(root)),
        packet_sha256=manifest["packet_sha256"],
        manifest_sha256=fingerprint(manifest_path),
        frozen_at_utc=manifest["frozen_at_utc"],
        reference_ledger_path=manifest["ledger_path"],
        reference_ledger_sha256=manifest["ledger_sha256"],
        comparisons_available=[
            "One completed human rating file against the documented assistant first pass",
            "Two separately completed human rating files for human inter-rater agreement",
        ],
    )


def export_rater_kit(root, output_path):
    """Export only frozen blinded materials, with their definition links intact."""
    root = Path(root).resolve()
    status = packet_status(root)
    require(
        status["status"] == "awaiting_independent_observations",
        "Build a frozen coding packet first",
    )
    directory = root / "data/research/reliability" / PACKET_ID / "rater"
    packet = json.loads((directory / "packet.json").read_text())
    blank = json.loads((directory / "ratings_blank.json").read_text())
    require(
        blank["packet_id"] == PACKET_ID and blank["packet_sha256"] == status["packet_sha256"],
        "Blank form identifies a different packet",
    )
    require(
        blank["rater"]
        == dict(
            identity="",
            kind="human",
            started_at_utc=None,
            completed_at_utc=None,
            did_not_consult_reference_labels=None,
            notes="",
        ),
        "Rater kit requires an unfilled identity and activity record",
    )
    require(
        blank["ratings"]
        == [
            dict(unit_id=u["unit_id"], codes=dict.fromkeys(CODES, None), notes="")
            for u in packet["units"]
        ],
        "Rater kit must contain only blank ratings",
    )
    template = (root / "presentation/reliability.html").read_text()
    require(
        template.count("__PACKET__") == template.count("__BLANK__") == 1,
        "Reliability template slots differ",
    )
    encode = lambda value: (
        json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    )
    expected = template.replace("__PACKET__", encode(packet)).replace("__BLANK__", encode(blank))
    require(
        (directory / "index.html").read_text() == expected,
        "Rater workspace differs from the blinded template",
    )
    paths = [
        directory / "index.html",
        directory / "packet.json",
        directory / "ratings_blank.json",
        root / "project_docs/Anchored_Returns_Codebook_v0.1.2.docx",
        root / "docs/empirical_protocol_v0.1.3.md",
    ]
    contents = {str(path.relative_to(root)): path.read_bytes() for path in paths}
    contents["README.md"] = (
        "# Independent coding packet\n\n"
        "Kazi Rafsan Mahboob\n\n"
        f"I am collecting separate ratings for {packet['unit_count']} text units from three orders. "
        "This packet contains definitions, source-page context and a blank coding workspace. "
        "Reference labels and research findings are excluded.\n\n"
        "Extract the entire ZIP before opening files. Keep the folder structure intact. "
        f"Open `data/research/reliability/{PACKET_ID}/rater/index.html`. "
        "The page includes its data and controls; a local web server is not required. "
        "The original codebook and protocol amendment are linked from the page.\n\n"
        "Read the definitions and all section context before rating. Do not consult the project site, "
        "first-pass labels or another rater. Record your actual identity and blinding statement. "
        "Mark every code present or absent for every unit, including units with no codes. "
        "Save a draft to resume and export the completed JSON when finished. "
        "Return that file to the researcher. Keep independent raters' work separate.\n\n"
        "No completed ratings or agreement statistics are included. The three orders are not a "
        "representative reliability sample of the final 15-order study.\n"
    ).encode("utf-8")
    manifest = dict(
        packet_id=PACKET_ID,
        packet_sha256=status["packet_sha256"],
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        units=status["units"],
        orders=status["orders"],
        file_sha256={name: sha256(data).hexdigest() for name, data in contents.items()},
        status="materials_only_no_completed_ratings",
        excluded="First-pass reference, coding ledger, findings, source catalog and completed ratings.",
    )
    contents["KIT_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr("Anchored_Returns_Rater_Kit/" + name, data)
    archive_bytes = buffer.getvalue()
    with ZipFile(BytesIO(archive_bytes)) as archive:
        require(archive.testzip() is None, "Rater kit archive failed its integrity check")
        for name, expected_hash in manifest["file_sha256"].items():
            require(
                sha256(archive.read("Anchored_Returns_Rater_Kit/" + name)).hexdigest()
                == expected_hash,
                "Rater kit file fingerprint differs",
            )
    output = Path(output_path)
    if not output.is_absolute():
        output = root / output
    require(output.suffix.lower() == ".zip", "Rater kit output must be a ZIP file")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(archive_bytes)
    return dict(
        status=manifest["status"],
        output_path=str(output.resolve()),
        archive_sha256=sha256(archive_bytes).hexdigest(),
        files=len(contents),
        packet_sha256=status["packet_sha256"],
        units=status["units"],
        orders=status["orders"],
        blinding_check="Only the explicit material allowlist was exported; reference labels are excluded.",
    )


def _read_ratings(path, packet, packet_hash, *, frozen_at=None, reference_identity=None):
    data = json.loads(Path(path).read_text())
    require(
        data["schema_version"] == "1.0"
        and data["packet_id"] == packet["packet_id"]
        and data["packet_sha256"] == packet_hash,
        "Rating file belongs to a different frozen packet",
    )
    rater = data["rater"]
    require(
        isinstance(rater["identity"], str)
        and rater["identity"].strip()
        and rater["identity"].strip().casefold() != "assistant"
        and rater["identity"].strip().casefold() != (reference_identity or "").strip().casefold(),
        "A separate rater identity is required",
    )
    require(
        rater["kind"] == "human", "This import requires actual separately recorded human ratings"
    )
    require(
        rater["did_not_consult_reference_labels"] is True,
        "Independent blinding has not been documented",
    )
    times = []
    for key in ("started_at_utc", "completed_at_utc"):
        require(isinstance(rater[key], str), "Actual start and completion times are required")
        try:
            t = datetime.fromisoformat(rater[key].replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("Invalid rating timestamp") from error
        require(
            t.utcoffset() is not None and t.utcoffset().total_seconds() == 0,
            "Rating times must identify UTC",
        )
        times.append(t)
    require(
        times[0] < times[1] <= datetime.now(timezone.utc),
        "Rating times are reversed, identical or future-dated",
    )
    if frozen_at is not None:
        require(
            datetime.fromisoformat(frozen_at) <= times[0],
            "Ratings predate the frozen coding packet",
        )
    by_id = {}
    for row in data["ratings"]:
        uid = row["unit_id"]
        require(uid not in by_id, "Duplicate rating unit")
        require(set(row["codes"]) == set(CODES), "Every code needs an explicit rating")
        require(
            all(type(x) is int and x in (0, 1) for x in row["codes"].values()),
            "All ratings must be integer 0 or 1; blanks and booleans are invalid",
        )
        by_id[uid] = row
    require(set(by_id) == {u["unit_id"] for u in packet["units"]}, "Missing or extra rating units")
    return data, by_id


def rating_preflight(root, path):
    """Inspect collection progress without generating agreement from blank ratings."""
    status = packet_status(root)
    require(
        status["status"] == "awaiting_independent_observations",
        "Build a frozen coding packet first",
    )
    packet_path = Path(root) / "data/research/reliability" / PACKET_ID / "rater/packet.json"
    packet = json.loads(packet_path.read_text())
    data = json.loads(Path(path).read_text())
    expected = {u["unit_id"] for u in packet["units"]}
    rows = data.get("ratings", [])
    require(
        isinstance(rows, list) and all(isinstance(r, dict) for r in rows),
        "Ratings must be an array of records",
    )
    ids = [r.get("unit_id") for r in rows]
    require(all(isinstance(i, str) for i in ids), "Rating unit identities must be strings")
    blanks = invalid = complete = 0
    for row in rows:
        codes = row.get("codes", {})
        require(isinstance(codes, dict), "Rating codes must be an object")
        values = [codes.get(c) for c in CODES]
        blanks += sum(v is None for v in values)
        invalid += sum(v is not None and not (type(v) is int and v in (0, 1)) for v in values)
        invalid += len(set(codes) - set(CODES))
        complete += int(
            set(codes) == set(CODES) and all(type(v) is int and v in (0, 1) for v in values)
        )
    error = None
    try:
        _read_ratings(path, packet, status["packet_sha256"], frozen_at=status["frozen_at_utc"])
    except (ValueError, KeyError, TypeError) as exc:
        error = str(exc)
    return dict(
        status="ready_for_comparison" if error is None else "not_ready",
        expected_units=len(expected),
        submitted_units=len(rows),
        complete_units=complete,
        blank_code_cells=blanks,
        invalid_code_cells=invalid,
        missing_unit_ids=sorted(expected - set(ids)),
        extra_unit_ids=sorted(set(ids) - expected),
        duplicate_units=len(ids) - len(set(ids)),
        validation_issue=error,
        agreement=None,
        packet_sha256=status["packet_sha256"],
        explanation="This checks file completeness and reported metadata only. It does not establish rater independence or calculate reliability. Complete separately recorded observations are required.",
    )


def evaluate_ratings(root, first_path, second_path=None):
    root = Path(root)
    status = packet_status(root)
    require(
        status["status"] == "awaiting_independent_observations",
        "Build a frozen coding packet first",
    )
    directory = root / "data/research/reliability" / PACKET_ID / "rater"
    packet_path = directory / "packet.json"
    packet = json.loads(packet_path.read_text())
    packet_hash = fingerprint(packet_path)
    require(
        fingerprint(root / "project_docs/Anchored_Returns_Codebook_v0.1.2.docx")
        == packet["codebook_sha256"]
        and fingerprint(root / "docs/empirical_protocol_v0.1.3.md") == packet["amendment_sha256"],
        "Packet codebook or amendment changed",
    )
    # Compare identities with the actual frozen reference, not a product-name list.
    baseline = json.loads(
        (root / "data/research/reliability_baselines" / (PACKET_ID + ".json")).read_text()
    )
    first, a = _read_ratings(
        first_path,
        packet,
        packet_hash,
        frozen_at=status["frozen_at_utc"],
        reference_identity=baseline["coder"],
    )
    if second_path is not None:
        second, b = _read_ratings(
            second_path,
            packet,
            packet_hash,
            frozen_at=status["frozen_at_utc"],
            reference_identity=baseline["coder"],
        )
        require(
            first["rater"]["identity"].strip().casefold()
            != second["rater"]["identity"].strip().casefold(),
            "Independent inter-rater agreement needs two distinct raters",
        )
        comparison, second_identity = "human_human", second["rater"]["identity"]
    else:
        baseline = json.loads(
            (root / "data/research/reliability_baselines" / (PACKET_ID + ".json")).read_text()
        )
        require(
            baseline["packet_sha256"] == packet_hash,
            "First-pass reference belongs to another packet",
        )
        require(
            baseline["ledger_sha256"] == status["reference_ledger_sha256"],
            "First-pass reference identifies a different frozen ledger",
        )
        b = {r["unit_id"]: r for r in baseline["reference_ratings"]}
        comparison, second_identity = "human_assistant", baseline["coder"]
    ids = [u["unit_id"] for u in packet["units"]]
    require(set(b) == set(ids), "Reference units differ from the packet")
    results = {
        code: binary_agreement(
            [a[i]["codes"][code] for i in ids], [b[i]["codes"][code] for i in ids]
        )
        for code in CODES
    }
    target = all(results[c]["meets_0_70"] is True for c in TARGET_CODES)
    return dict(
        status="recorded_pair_evaluated",
        comparison_type=comparison,
        rater_a=first["rater"]["identity"],
        rater_b=second_identity,
        units=len(ids),
        orders=packet["order_count"],
        results=results,
        main_code_target_met=target,
        main_codes=list(TARGET_CODES),
        interpretation="Undefined kappa is insufficient variation, not perfect reliability. These units come from three orders; this is not a 15-order validation result.",
        provenance_limit="Metadata and blinding are reported attestations. File validation cannot independently authenticate the person or prove that labels were concealed.",
        first_ratings_sha256=fingerprint(Path(first_path)),
        second_ratings_sha256=fingerprint(Path(second_path)) if second_path else None,
        packet_sha256=packet_hash,
    )
