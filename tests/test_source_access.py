import hashlib
import json
from zipfile import ZipFile

import pytest

from scripts.check_public_release import distribution_errors
from scripts.import_eei import install


def metadata(tmp_path):
    folder = tmp_path / "data/external/eei"
    folder.mkdir(parents=True)
    (folder / "source.json").write_text(
        json.dumps(
            {
                "sha256": hashlib.sha256(b"recorded fixture").hexdigest(),
                "path": "data/external/eei/eei_rate_review_2025_q3.xlsx",
            }
        )
    )
    return folder


def test_import_checks_fingerprint_before_changing_local_source(tmp_path):
    folder = metadata(tmp_path)
    source = tmp_path / "download.xlsx"
    source.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="not the recorded"):
        install(source, tmp_path)
    assert not (folder / "eei_rate_review_2025_q3.xlsx").exists()
    source.write_bytes(b"recorded fixture")
    destination = install(source, tmp_path)
    assert destination.read_bytes() == b"recorded fixture"
    assert install(source, tmp_path) == destination


def test_distribution_check_catches_direct_and_archived_workbook(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    name = "data/external/eei/eei_rate_review_2025_q3.xlsx"
    (docs / "eei_withdrawal.json").write_text(json.dumps({"paths": [name]}))
    with ZipFile(tmp_path / "old-release.zip", "w") as archive:
        archive.writestr(name, b"restricted fixture")
    assert distribution_errors(tmp_path, [name, "old-release.zip"]) == [
        name,
        "old-release.zip: " + name,
    ]
