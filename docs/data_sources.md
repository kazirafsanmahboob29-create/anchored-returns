# Data sources

The main numerical study uses the preserved EEI rate-case table and dated economic series. The original-order study has its own documents, coding records and historical benchmark definitions. A source being accessible today does not establish that its present revision was available when a commission decided a case.

## Main study inputs

| Source | Included records | Role and access |
|---|---|---|
| [Edison Electric Institute Rate Review](https://www.eei.org/issues-and-policy/finance-and-tax) | 2025 Q3 workbook, 2,589 source rows | Public electric rate-case table. The complete-case estimation panel has 533 observations from 2010 to 2024. [Source metadata](../data/external/eei/source.json) and reconstruction. |
| [FRED DGS10](https://fred.stlouisfed.org/series/DGS10) | Preserved daily Treasury history | Lagged nominal ten-year Treasury yield. Public CSV transport; the documented JSON API requires a key. |
| [FRED T10Y3M](https://fred.stlouisfed.org/series/T10Y3M) | Preserved daily term spread | Ten-year minus three-month Treasury yield, in percentage points. |
| [FRED STLFSI4](https://fred.stlouisfed.org/series/STLFSI4) | Preserved weekly financial stress index | Financial conditions. Version 4 includes reconstructed earlier history. |
| [FRED CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) and [BLS CPI](https://www.bls.gov/cpi/questions-and-answers.htm) | Preserved monthly CPI levels and separate BLS responses | Year-over-year inflation from index levels. The browser connector can request CPI through the BLS API. |
| [Federal Reserve H.15](https://www.federalreserve.gov/releases/h15/) and [Treasury XML](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) | Separate official Treasury retrievals | Source definitions and a second dissemination route for yield checks. |

The October 26 source review records definitions, retrieval dates, revision issues and redistribution restrictions. The [publication allowlist](../data/external/factor_research_2026-10-26/publication_allowlist.json) identifies the permitted economic inputs. Moody's histories reviewed locally are excluded from publication inputs. Source notices and required citations remain with the data.

The EEI workbook's bytes were rechecked on October 26 against its recorded SHA-256 hash. Its original publication date remains unverified. The empirical paper keeps that workbook and the saved economic vintage. Refreshing an API does not silently replace the paper's inputs.

## Original decisions and numerical evidence

The current document cohort contains 27 orders. The [cohort protocol](cohort_protocol_v0.1.5.md), screening records and source catalog distinguish eligible orders, excluded records and supporting material. The cohort is a public-document study, not a completed census of all eligible six-state decisions.

The source library includes original commission PDFs, public docket attachments and publisher reports. The restoration manifest records each source file's URL, relative path and SHA-256 fingerprint. Large original PDFs and review images are restored separately; they are not required to run the included browser snapshot. See [source restoration](REPRODUCIBILITY.md#source-dependent-and-document-checks).

Applications, draft minutes and municipal debt-coverage decisions are not reclassified as final equity-return orders. Numeric facts retain their document, page, role and units. The three completed first coding passes are separate from the numerical panel; independent coding agreement remains unmeasured.

## Historical benchmarks

The strict RRA registry contains ten service-period values across five half-years: H2 2019 and H1 2020, 2021, 2022 and 2024. Two values are complete-table reconstructions; eight are publisher-reported. The reconstruction note and 126-row decision table document the H2 2019 calculation.

Five exact periods remain unresolved under the original same-service, rider-excluded definition: H1 2023, H2 2023, H2 2024, H1 2025 and H1 2026. The October 4 acquisition record explains why all-case means, annual summaries and changed dataset coverage do not fill those fields. No licensed S&P/RRA connection is available.

The context registry keeps other publisher reports separate. The EEI half-year reconstruction supplies a broader retrospective electric comparison. It does not supply gas observations or silently replace a missing RRA benchmark.

## Refresh and access rules

- `./research refresh-treasury` preserves a new immutable FRED retrieval and its date matches.
- `./research verify-treasury` preserves the official XML responses and compares overlapping observations without overwriting either series.
- Browser Treasury and BLS refreshes recalculate a local scenario. They leave the published results fixed and include source dates in exports.
- An authenticated FRED JSON transport is optional. No key is needed for the included study or its CI checks.

Date matching never uses a future observation. It records the actual observation date and day gap. Missing values remain missing. Revision-sensitive historical research would require historical vintages in addition to observation-date lags.

The link audit records current website checks. Some commission, BLS and publisher pages reject automated requests. That response is reported as restricted access, not evidence that a page was read or that a new value was verified.

## Preserved economic series and source files

The expanded fetcher reads the user's local EEI workbook only to choose which state unemployment series to fetch, and the workbook is not distributed.

Census state codes are a static state code lookup. [Source](https://www2.census.gov/geo/docs/reference/state.txt).

| Series ID | Publisher | Retrieval date (UTC) | File path | SHA-256 |
|---|---|---|---|---|
| AKUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/AKUR.csv` | `bf91e4ffef3322b215ae5ce3d73acd0c38750aa14614b3fdbf5b0dffb721ecc2` |
| ALUR | U.S. Bureau of Labor Statistics, Local Area Unemployment Statistics | 2026-10-30 | `data/external/filing_2026-10-30/ALUR.csv` | `abf2e2a3484af9843392cfb29ac1457ad11b36d8895954f586762054a42236ec` |
| ARUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/ARUR.csv` | `21470c9b9952a803cb63433bef9495a382df8fec35de2baec5010ac69dc1b06d` |
| AZUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/AZUR.csv` | `6e2c887f033ca04f5d7af3ee69d919fdb2bd26f473991644190dc37ffacac4e7` |
| CAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/CAUR.csv` | `75bfa02885bef0e853eddc8532bf7f7ed619bd742fb4928d3c1fd7f8b8db7a33` |
| COUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/COUR.csv` | `04ea6c15915ba417946d13982cabf9fad48f948f4379f9142c722ea10f67e67f` |
| CPIAUCNS | Federal Reserve Bank of St. Louis | 2026-10-26 | `data/external/factor_research_2026-10-26/CPIAUCNS_2008_present.csv` | `451ae1dc667ca3d69e8a2d030b340dd3bcf92a32f72a5ad31b933182b226aa0e` |
| CPIAUCNS | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/macro/CPIAUCNS.csv` | `08645d9c50b2b3d3e19e7fed50e74f61be61c2b72e02016b9841a801b1bde900` |
| CTUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/CTUR.csv` | `18697da982374e9aeaf148931b5333b0bf28be7aefc3c2bcc9fc45eac6066ba3` |
| CUUR0000SA0 | U.S. Bureau of Labor Statistics | 2026-10-26 | `data/external/bls_cpi/2026-10-26/bls-2008-2017.json` | `c04fe8a8b08fe5cb3ece0c5395298fb4edcb3c061c9d35db863e16430fb4b2fc` |
| CUUR0000SA0 | U.S. Bureau of Labor Statistics | 2026-10-26 | `data/external/bls_cpi/2026-10-26/bls-2018-2026.json` | `0e908a92c75bc1850e3884983480728c2f4a9db22c66e52e9e0837cf81c048bb` |
| Census state codes | U.S. Census Bureau | retrieval date not recorded | `data/external/expanded_2026-10-28/census_state.txt` | `bea4e03f71a1fa0045ae732aabad11fa541e5932b071c2369bb0d325e8cba5a0` |
| DCUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/DCUR.csv` | `e271bd4f36259e6edf24be7e0a02bb0bb797c942abbc2e96d41551fb457db6bd` |
| DEUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/DEUR.csv` | `67bd4e7dfadf70a33c9835df1a81fd01278fd86cc8fc6a71c4840edd4416f2d2` |
| DGS10 | Federal Reserve Bank of St. Louis | 2026-10-26 | `data/external/factor_research_2026-10-26/DGS10_2008_present.csv` | `ca303c6e3fbb6457c7167abb03fb5116e93e6015c614db15de03f7fcc4801449` |
| DGS10 | Federal Reserve Board | 2026-10-29 | `data/external/expanded_2026-10-28/macro/DGS10.csv` | `de2e0365d6e4c12bca39008904c2f611aa43cd66e4feeb61748f1a4f402e0a9e` |
| FLUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/FLUR.csv` | `ce37469e1c234029ca839bc0687fcb0842748da16e7b97c477186e1de6f4bfdc` |
| GAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/GAUR.csv` | `b52ea3d03399125c33907718243d8c71b9b05582ad4adbf419ed820fbc63a6e4` |
| HIUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/HIUR.csv` | `ddfa4ead91d48372f1865f62f7e2cea5fc94a183ce91e12b52516bd133471379` |
| IAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/IAUR.csv` | `c3e345f1529e8e294a129bc0148f149690b271bf80a19afb1e0cb16c5c5b52f8` |
| IDUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/IDUR.csv` | `6a16e1716a1c9db335c2d6c337b2ac7423b0b791cb6f945f1fc44280601cf84e` |
| ILUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/ILUR.csv` | `ffe1f98a9bcad6f311124d079a95afbb0bc303fe4fb867c1445dbf45e4fe853d` |
| INUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/INUR.csv` | `9b11cc67e5bc9e1198b4b9a0fe5e9d7b1a9d7c6923866ac46f45a52c5b8bf9ae` |
| KSUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/KSUR.csv` | `e48411b2c10b6aaf5170966075198d8137f587393b2bda1a78d07fe9f261fc5e` |
| KYUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/KYUR.csv` | `0e5d4aec6c64ff575146698a973f177f0cfd46ac61cbb877e228b5ec697cb4d4` |
| LAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/LAUR.csv` | `d37046cfa7c27fc2d270512d1497f7bdf9994aeecb92d80399b9be94a172b024` |
| MAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MAUR.csv` | `2cfed9a956ca16d67ddeb79b82162f58c2eac27ddded9d8e07833d83ec36a1fc` |
| MDUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MDUR.csv` | `486520798bb0d644f80c59d784c1b10666523e69b59d5e125598c1876642d5cc` |
| MEUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MEUR.csv` | `03b7d36e26bc59d1e91e161767c8a7c2f3775d2b8d82e6e13b9784db0251b590` |
| MIUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MIUR.csv` | `05e7b241e9940bee965f1492a03e0bf7a2d5aa5f4301b34ce01d66d6e24908c4` |
| MNUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MNUR.csv` | `73ff51a7ad86c6642abe8e63f79da42382f57d16d8a72701a775f4da3901a71f` |
| MOUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MOUR.csv` | `ae45b6746e4adc355fa7e46076bd76c381289a42d23eb17bb6cd36c7a7697088` |
| MSUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MSUR.csv` | `52204532d5697af16acc1b8d10879669879e83c4de19805cca8173745e5fd06b` |
| MTUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/MTUR.csv` | `cbabaa9b960549eb67fd0f4ea46afb8fa949df911884b57d25f15124298462ed` |
| NCUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NCUR.csv` | `2d53ca82e70821804e95da7716c87e8aab3a76059b2c52be2d83cf7b42f49722` |
| NDUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NDUR.csv` | `fa3edcd7205dc9816a522460d82eaa9b3a5e0cf2df6db2ddb3b1c2bbed3b51df` |
| NHUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NHUR.csv` | `a3577be476fefab1ae75ff341ac88bfe3689be609166051a33cd022b82719f43` |
| NJUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NJUR.csv` | `fcde05c4acfc9f6af07cbbf5082e7c3eb801fc9249a1988eda12e0fd083a88d8` |
| NMUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NMUR.csv` | `432f9017e00494d4fea5550c3187df2ee9293170749a61526eda3d5957ef5ed3` |
| NVUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NVUR.csv` | `20f301069f60fc0085a727f13d427e95b42fa502f4e25cf65c8ced8c7086dd70` |
| NYUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/NYUR.csv` | `3ea7d86b2cb736759140a134739bae8909715d4c231e8c2a59796e27a4d45921` |
| OHUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/OHUR.csv` | `430953b1905dea47f55122134576261a16528c36f48643eab66f99c613cde569` |
| OKUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/OKUR.csv` | `275890b64edf658939c9b936ac1f9b003490cbaf0c3fcaa00d2358263955ff62` |
| ORUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/ORUR.csv` | `1930f50b4d6434646f9015cd23786a021a7316dce67218e2252ce6c3ee83b5c5` |
| PAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/PAUR.csv` | `1593f20546788fb7db6a50cc115a778ddae8f028e3bfc2cc5765bdd3c6cb4caf` |
| RIUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/RIUR.csv` | `8e897457b460f28dc3c1d24109d31b533d1324ca77f59c5537429ef1328c4595` |
| SCUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/SCUR.csv` | `a62078f088b361bf8be4015445af80755e1dda4052187975f0dc87bf29d02d69` |
| SDUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/SDUR.csv` | `fa38de2a1e42b06d2731a670809c630e7b01ea0cccea5efbde172e519c280008` |
| STLFSI4 | Federal Reserve Bank of St. Louis | 2026-10-26 | `data/external/factor_research_2026-10-26/STLFSI4_2008_present.csv` | `afcce8f5a71cd3dcf9285b8088bac135eb3b107aa437efcb100099ef4688ece2` |
| STLFSI4 | Federal Reserve Bank of St. Louis | 2026-10-29 | `data/external/expanded_2026-10-28/macro/STLFSI4.csv` | `e673fdfafac9980b043d9f4a36690e7f3d6551c43e3c4c67072eebcc35e380ff` |
| T10Y3M | Federal Reserve Bank of St. Louis | 2026-10-26 | `data/external/factor_research_2026-10-26/T10Y3M_2008_present.csv` | `c9cf830c54da4da76b97a1f10a2db298fe1f845f96bafde6dbf37f26cfcd5e43` |
| T10Y3M | Federal Reserve Bank of St. Louis | 2026-10-29 | `data/external/expanded_2026-10-28/macro/T10Y3M.csv` | `70bacaf24535a37fe33ec4f6664985a776466e03adab35485abaecc26986d20a` |
| TNUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/TNUR.csv` | `98d4e7dfe67a2798081177d79510063a56cad968d077a098b4625db14513be14` |
| TXUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/TXUR.csv` | `cbdb44e431785c9b1774ef3f168e7d50563a0145c56edd6c148749b3227bc143` |
| UTUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/UTUR.csv` | `30f06ca6753c621bf4878b4d7937e058b1e6cdf3169b76952817c9af2d4ddd44` |
| VAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/VAUR.csv` | `00b75c58e08f5cf9c2aa8203cb1af898e12964d78acf63bccdfcd2c91050f8e4` |
| VTUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/VTUR.csv` | `8198f2910d91e2a857dd67a428033e0d0b935402909ca22e15dcabd45fff8ade` |
| WAUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/WAUR.csv` | `de96c352a9a34ee86c19b07d81f013834d2c3bd324bf9959bcf203d37df47705` |
| WIUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/WIUR.csv` | `bc42b65bcbe96779d3449d672e0a94c8745f3564f6c925fe390c84bea8c22b59` |
| WVUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/WVUR.csv` | `6f1b64e8d7bb20dc16be97acb0ad89ada8f27a4c8846cd6489017f00da6c1cbe` |
| WYUR | U.S. Bureau of Labor Statistics | 2026-10-29 | `data/external/expanded_2026-10-28/states/WYUR.csv` | `4722483542c801c16ca547e0a6cbc740b5eccab031e8eb2167b1d4729dd66412` |
