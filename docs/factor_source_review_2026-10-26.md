# Historical factor sources

Reviewed October 26, 2026. The EEI analysis cutoff remains September 30, 2025.

I use public economic series to describe the financial conditions surrounding utility rate decisions. The preserved files contain current historical values retrieved in October 2026. They do not reconstruct the information originally available to a commission on each decision date.

## Recommended inputs

| Series | Definition and units | Frequency | Verified history | Proposed treatment |
|---|---|---|---|---|
| [DGS10](https://fred.stlouisfed.org/series/DGS10) | Nominal market yield on Treasury securities at a constant 10-year maturity, quoted on an investment basis. Percent per annum. | Daily | January 2, 2008 to October 22, 2026. 4,705 numeric values. | A lagged interest-rate level. A Treasury yield does not measure the utility's own financing cost. |
| [T10Y3M](https://fred.stlouisfed.org/series/T10Y3M) | Ten-year Treasury constant-maturity yield minus the three-month Treasury constant-maturity yield. Percentage points. | Daily | January 2, 2008 to October 23, 2026. 4,706 numeric values. | A lagged term-structure measure. One percentage point equals 100 basis points. |
| [STLFSI4](https://fred.stlouisfed.org/series/STLFSI4) | St. Louis Fed Financial Stress Index, version 4. Index units. Zero is its designed historical average, with positive values indicating greater-than-average stress. | Weekly, ending Friday | January 4, 2008 to October 16, 2026. 981 numeric values. | Latest observed week ending at least 14 calendar days before the decision. |
| [CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) | CPI-U, all items, U.S. city average, not seasonally adjusted. Index, 1982-1984 = 100. | Monthly | January 2008 to September 2026. 224 numeric values in 225 monthly rows. | Reference month two calendar months before the decision month. Calculate 12-month inflation from index levels. |

DGS10 comes from the Federal Reserve Board's H.15 release. T10Y3M is a St. Louis Fed calculation. Its notes identify a change to direct Treasury sourcing beginning June 21, 2019. The term spread describes the Treasury curve, rather than compensation for corporate default risk. [H.15 release description](https://www.federalreserve.gov/releases/h15/about.htm), [term-spread notes](https://fred.stlouisfed.org/series/T10Y3M).

STLFSI4 combines 18 financial series, including interest rates, yield spreads and other indicators. Some components overlap conceptually with the Treasury variables, so these regressors should not be described as independent economic shocks. Version 4 was introduced on November 10, 2022 and replaced backward-looking SOFR with forward-looking SOFR in two spreads. Earlier observations in the current file are reconstructed history under that definition. The index is a broad financial-stress measure, rather than a utility credit spread or an equity risk premium. [Series definition](https://fred.stlouisfed.org/series/STLFSI4), [version 4 methodology](https://fred.stlouisfed.org/blog/2022/11/the-st-louis-feds-financial-stress-index-version-4/).

CPI measures consumer prices rather than utility construction costs or investors' expected inflation. For a source reference month `m`, inflation is `100 * (CPI[m] / CPI[m-12] - 1)`. For a decision in September 2025, the two-month convention uses July 2025 and July 2024. The 2008 start supplies the earlier observations needed for inflation calculations near the beginning of the 2010 sample. October 2025 is blank in the current download and remains missing. It is outside the current EEI analysis window. [BLS CPI definition and revision policy](https://www.bls.gov/cpi/questions-and-answers.htm).

## Coverage within the EEI analysis window

| Series | Rows dated January 1, 2010 to September 30, 2025 | Numeric values | Last observation in window |
|---|---:|---:|---|
| DGS10 | 4,108 | 3,939 | September 30, 2025 |
| T10Y3M | 4,108 | 3,939 | September 30, 2025 |
| STLFSI4 | 822 | 822 | September 26, 2025 |
| CPIAUCNS | 189 | 189 | September 2025 |

Blank daily rows include holidays. Missing observations remain distinct from zero. Weekend dates are generally absent from the daily files. The source manifest records original file hashes, row counts, observation bounds and retrieval timestamps.

## Timing and vintages

An observation date, a publication date and a retrieval date serve different purposes. CPI's first-of-month date labels a reference month. STLFSI4's Friday date labels a week. Neither date establishes when the value became public. An HTTP `Last-Modified` header describes the downloaded resource and does not establish the first publication date of every historical observation.

The two-calendar-month CPI rule and the 14-calendar-day stress rule are conservative lag conventions for a retrospective study. They do not establish historical release availability or remove revisions. A daily Treasury specification also needs an explicit lag and averaging window. Same-day market observations should not be treated as information available before an order whose issuance time is unknown. Daily results should include a longer-lag sensitivity check.

FRED's default historical view uses information available today. ALFRED real-time dates can instead identify information available at a past date. A study claiming historical information sets would need those vintage records, original release dates and a documented intraday convention. They were not obtained in this review. [FRED real-time documentation](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

The unadjusted CPI-U series is preferable here to seasonally adjusted CPIAUCSL because BLS ordinarily treats unadjusted CPI-U as final when issued, subject to rare corrections. BLS re-estimates seasonally adjusted CPI factors and can revise up to five years of seasonally adjusted history. This preference reduces one source of revision risk but does not prove that every current value equals its original release. [BLS CPI FAQ](https://www.bls.gov/cpi/questions-and-answers.htm).

## Access and file schemas

The recommended series downloaded successfully without credentials from the official machine-readable CSV export:

`https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERIES_ID&cosd=2008-01-01`

Each preserved CSV has two columns, `observation_date` and its series identifier. Dates use `YYYY-MM-DD`; numeric rates and index levels are decimal strings. Empty values are missing. Importers should also reject or explicitly handle `.` if a future export uses that missing marker. Data remain at their native frequency and are sorted by observation date.

This export is distinct from the authenticated FRED observations API. A direct request to `api.stlouisfed.org/fred/series/observations` without a key returned HTTP 400 and reported that `api_key` was not set. A free registered key is required for the documented API. No key was supplied, obtained from another application or embedded in the project. The CSV histories are sufficient for the current retrospective extension. [FRED observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).

## Optional state unemployment

The preserved FRED series CTUR, MEUR, MAUR, NHUR, RIUR and VTUR contain monthly, seasonally adjusted unemployment rates for the six New England states. Their units are percentages of the civilian labor force. They describe local labor-market conditions rather than the risk of a specific utility. A two-reference-month lag is a useful retrospective convention. Monthly and annual revisions still prevent an as-known interpretation without historical vintages. [FRED example series](https://fred.stlouisfed.org/series/MAUR), [BLS LAUS definitions](https://www.bls.gov/lau/laufaq.htm), [BLS revision and seasonal-adjustment technical note](https://www.bls.gov/news.release/laus.tn.htm).

I also verified the official BLS JSON endpoint, `https://api.bls.gov/publicAPI/v2/timeseries/data/`, with two credential-free requests covering 2008-2017 and 2018-2026. Each request contained CPI series CUUR0000SA0 and six state unemployment series. Both returned HTTP 200 and `REQUEST_SUCCEEDED`. The response retains `seriesID`, `year`, `period`, `periodName`, `value` and `footnotes`, including preliminary flags. Monthly periods are M01 through M12. An M13 annual-average record must not be imported as a month.

All 1,323 overlapping monthly values from January 2010 through September 2025 matched the separately downloaded FRED files exactly: 189 values for CPI and 189 for each state. This confirms agreement between two retrieval routes for the current data, not independent statistical measurement. BLS documentation gives unregistered access a ten-year query limit and requires registration for expanded version-2 features. The successful keyless requests do not establish entitlement to higher limits or metadata options. [BLS API signatures](https://www.bls.gov/developers/api_signature_v2.htm), [BLS access limits](https://www.bls.gov/developers/api_faqs.htm).

## Publication rights

FRED labels DGS10, CPIAUCNS and the state unemployment series `Public Domain: Citation Requested`. It labels STLFSI4 and T10Y3M `Copyrighted: Citation Required`. The latter two should not be described as public-domain series. FRED's summarized terms permit displaying and publishing the citation-required category with source attribution and acknowledgment that the data were obtained through FRED, subject to its terms and prohibited uses. The project should retain the suggested citations and avoid implying Federal Reserve endorsement. [FRED terms and copyright categories](https://fred.stlouisfed.org/legal/).

Moody's AAA, BAA, DAAA, DBAA and BAA10Y histories were accessible for local review, but their series notes include provider-specific reproduction and redistribution restrictions. They are excluded from the recommended publication inputs. Local review copies are isolated in an ignored `restricted_moodys` directory. Public access to a download does not itself establish a redistribution license. [Moody's series notes](https://fred.stlouisfed.org/series/DBAA), [BAA10Y series notes](https://fred.stlouisfed.org/series/BAA10Y).

## EEI workbook check

Both official EEI finance-page routes still link to 2025 Q3 as the newest observed Rate Review workbook. A fresh download returned HTTP 200, 847,348 bytes and SHA-256 `b901b35640b222ae8ab6df8aca7c5b04d51c38d961b72354704ec8ecc5753895`, matching the preserved workbook. Newer 2025 Q4 links on the page concern credit ratings, dividends and stock performance. They do not establish a newer rate-case source table. I did not guess unlinked workbook URLs. The original 2025 Q3 publication date remains unverified. [EEI finance page](https://www.eei.org/issues-and-policy/finance-and-tax).

## Preserved evidence

The machine-readable review is `data/external/factor_research_2026-10-26/sources.json`. Recommended CSVs use the suffix `_2008_present.csv`, with an adjacent `.metadata.json` file. Metadata retain stable source URLs, UTC retrieval times, HTTP status, original SHA-256, byte counts, schemas and coverage controls. BLS responses, cross-source reconciliation and the EEI link and fingerprint checks are preserved in the same research directory. These files do not change the frozen EEI observations, original-order archive or benchmark catalog.

## Publication allowlist and attribution

`data/external/factor_research_2026-10-26/publication_allowlist.json` enumerates the four accepted CSV files and their four metadata files, including byte counts and SHA-256. This review and the allowlist itself are the accepted accompanying documentation. All other files in the research directory are excluded from this release's publication inputs, including local Moody's copies, exploratory HTML, capped-window duplicates, optional state series and raw BLS responses.

The allowlist provides full source citations for the four accepted series. Displayed data and results should credit the Federal Reserve Board for DGS10, the Federal Reserve Bank of St. Louis for T10Y3M and STLFSI4, and the Bureau of Labor Statistics for CPIAUCNS. Each citation also identifies FRED as the retrieval service and October 26, 2026 as the retrieval date. The two St. Louis Fed series retain their `Copyrighted: Citation Required` label. No endorsement or transfer of source ownership is implied.
