# Dartmouth portfolio deployment

The public portfolio is https://journeys.dartmouth.edu/kazirafsanmahboob29/ . WordPress hosts the project article, application, figures, original-order copies and study downloads.

## Pages and layout

- Projects: page 764, set as the static homepage.
- Research article: page 761.
- Anchored Returns workbench: page 769.
- Coursework index: page 767.
- Existing biography: page 4. Earlier course pages remain available.

The Twenty Twenty-Three Pages template supplies a shared header, navigation and footer. The supported Advanced Settings plugin supplies the portfolio CSS and application JavaScript. No credentials are included in the application. `wordpress/` contains the installed fragments, browser modules, media locations and build manifest. `scripts/build_wordpress.py` rebuilds them from the checked research outputs and preserved source index.

## Application

The application runs in the reader's browser. Its model estimator, period comparisons, original-order summaries, 68 numeric fact records, source search and blinded 67-unit coding worksheet use preserved project inputs. Compressed data are verified with SHA-256 before initialization. Browser calculations use the same tested modules as the standalone workbench. Codebook wording and source quotations are preserved.

Readers can change periods, case types, controls, market windows and comparison weights, inspect source rows and PDF pages, export calculation records and download the study inputs. Coding drafts are saved only in browser local storage. The site collects no ratings. Exported ratings use integer 0/1/null values and identify the frozen packet; completion also requires identity and self-reported independence. Independent reliability remains unmeasured until separately completed ratings actually exist.

## Direct economic connections

Treasury annual XML and BLS CPI-U JSON are fetched from their official public APIs over HTTPS, without a proxy or API key. Nineteen annual Treasury files cover 2008–2026. CPI requests use nonoverlapping windows of at most ten years. Missing BLS values remain missing. The connector validates dates, series identity, numeric ranges, duplicate observations, coverage and freshness before replacing the browser's working inputs. Raw responses and their hashes accompany an exported snapshot.

The refreshed run uses Treasury's ten-year par yield, the ten-year minus three-month spread and BLS CPI. STLFSI4 retains the October 26, 2026 archived vintage; it is explicitly identified as archived. The EEI case table also remains the preserved 2025 Q3 version. A refreshed browser run never changes the published paper. FRED's public CSV endpoint does not permit direct cross-origin browser requests, so the WordPress application does not pretend to refresh that series through an unavailable backend.

Python and R execute in the reproducible research environment, rather than on the WordPress server. Native Stata syntax is included, with execution unverified. The browser JavaScript performs the interactive calculations. One benchmark PDF exceeds the site's media upload limit and remains linked to its recorded original public source. Published media locations are recorded in `wordpress/media-urls.json`.

## Updating

1. Rebuild the affected research outputs and run their checks.
2. Upload changed public figures or archives through the WordPress Media interface; record the resulting URLs.
3. Run `python scripts/build_wordpress.py`.
4. Update the page fragments and Advanced Settings fields through WordPress.
5. Verify the public pages, model results, downloads and direct connections at desktop and mobile widths.

The prepared repository remains available for manual GitHub upload. Source provenance and historical coding records are retained; the portfolio does not label the first coding pass as independent human work.
