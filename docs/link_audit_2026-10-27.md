# Repository link audit

Kazi Rafsan Mahboob · October 27, 2026

This audit checks the repository documentation and its public destinations. It does not reclassify a source document or verify a new economic observation.

## Repairs

- Replaced stale portfolio addresses in the current usage and publication guides.
- Replaced references to unpublished repositories with an accurate description of the separately maintained theme.
- Rewrote the source guide around the national panel, current document cohort and strict historical benchmark registry.
- Restored the small October 4 acquisition record linked by the dated review. Its bytes match the original local record.
- Changed the dated review's omitted local PDF link to the recorded official Kentucky commission attachment, retaining its page fragment.
- Added a results index and direct links into the repository map.

No empirical input, coding record, result table or figure was changed. The dated review received a link correction only. The preserved service export retains its original files.

## Link checks

The internal checker scans Markdown links, images, reference destinations and heading fragments in maintained documentation. Local server examples require a running server and are excluded from public HTTP checks.

A separate scan of the frozen service export found 19 historical paths to omitted PDFs, old module reports and a former latest-release pointer. Those copied documents describe the earlier export, not the current repository. They remain preserved with their original bytes and are excluded from the maintained-documentation check. Use `--include-export` to reproduce that scan. The current documentation index links to the maintained guides.

The final maintained-documentation scan covered 30 Markdown files and passed 102 internal link checks. Of 29 distinct public URLs, 22 returned HTTP 200 and seven returned HTTP 403. No maintained public destination returned 404 or 410. The portfolio, research article, workbench and official Kentucky attachment loaded successfully. The seven restricted requests were BLS documentation and S&P publisher pages.

Public checks use normal HTTPS requests with certificate verification. A successful HTTP response establishes reachability, not factual accuracy. Publisher and government access controls are recorded separately; a 403 response is not labeled a successful source review or a missing page. API endpoints may require a method other than GET.

Run `python -m scripts.check_links` for the offline check. Run `python -m scripts.check_links --external --output /tmp/anchored-returns-links.json` to repeat network checks and save their destinations and status codes. The read-only GitHub workflow runs the offline check before the calculation tests.
