# Data rights and source access

Reviewed October 30, 2026.

## EEI workbook

The source is [EEI Rate Review, 2025 Q3](../data/external/eei/source.json). EEI's [terms of use](https://www.eei.org/en/pages/terms-of-use), section 4, permit a single personal, noncommercial download subject to their conditions, but restrict reproduction, distribution and multiuser storage without prior written permission. The [privacy policy's copyright notice](https://www.eei.org/en/pages/privacy-policy) also limits redistribution. A public download URL does not establish permission to distribute the workbook through GitHub.

No written redistribution permission has been verified. The current source package therefore excludes the workbook, case-level extracts, reconstructed source tables and compiled bundles containing them. The analysis code, source metadata, aggregate estimates and original figures remain available. These exclusions are a conservative publication decision, not a legal opinion or a claim that all derived material has a separate license.

Obtain a copy from [EEI's finance page](https://www.eei.org/issues-and-policy/finance-and-tax) under terms applicable to your use. The [source import script](../scripts/import_eei.py) validates its recorded SHA-256 fingerprint before installation. Generated local files are ignored by Git. The [withdrawal manifest](eei_withdrawal.json) identifies the excluded paths; a [distribution check](../scripts/check_public_release.py) checks the tracked package.

### Earlier public copies

The earlier repository was made private and replaced by this one. Earlier public copies may persist in clones, forks and caches. No removal from external copies is claimed.

## Other sources

Source records retain the originating commissions, agencies and publishers. Federal economic series retain their producer credits and retrieval vintages. Commission documents and third-party reports do not acquire a new license through this project. Moody's series were excluded from the public data inputs because their notes restrict redistribution.

The project does not apply a blanket license to third-party evidence. Original code and research text are distinguished from third-party materials throughout the source records.
