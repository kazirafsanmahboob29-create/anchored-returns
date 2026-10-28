# Dartmouth portfolio

The public portfolio is https://journeys.dartmouth.edu/kazirafsanmahboob29/ . It presents research findings, figures, coursework and downloadable study files. Analysis software is distributed separately for local use and manual GitHub publication.

## Pages and layout

| Page | WordPress ID |
|---|---:|
| Home | 844 |
| Projects | 764 |
| Research article | 761 |
| Coursework | 767 |
| Papers | 846 |
| Code and GitHub | 848 |
| Goodreads | 850 |
| Google Scholar | 852 |
| Photography | 854 |
| About Me | 4 |
| Earlier workbench URL, now a code pointer | 769 |

The Twenty Twenty-Three Pages template supplies the shared header, navigation and footer. The Advanced Settings plugin supplies the cream and black stylesheet and a Person metadata record. No application runtime is loaded by the portfolio. The home page uses text only. Empty sections state that content has not been posted, rather than implying a publication, profile or collection exists.

`portfolio/site/site.json` records the page map and verified profile URLs. `portfolio/site/style.css` is the visual source. `scripts/build_portfolio.py` builds the eleven page fragments, shared template, header and footer. It reads the checked factor-study results and the media URLs already recorded in `wordpress/media-urls.json`. `portfolio/site/manifest.json` fingerprints the generated page fragments. Local account backups and preview files are excluded from repository exports.

The installed WP SEO plugin supplies the unique page titles and descriptions recorded in `portfolio/site/seo.json`. Canonical links remain managed by WordPress. The unfinished Goodreads, Scholar and Photography directory pages, and the earlier code-pointer URL, carry `noindex`; their links remain usable. Remove the setting as substantive content is added. The core XML sitemap is public at `wp-sitemap.xml`. Unused WordPress emoji scripts are disabled through Advanced Settings. These changes support crawling and search presentation, without guaranteeing indexing or ranking.

## Research and code

The research article reports the 533-observation panel, model specifications, later-case evaluation, original-order examples and remaining research limits. Figures link to the preserved study. The public source archive includes the Python, R, Stata and browser modules, tests and documentation. The code page links to the author's actual GitHub profile; a project repository has not yet been uploaded.

The local workbench supports regressions, correlations, national comparisons and document inspection. The earlier browser application implementation is preserved in `wordpress/`, including official Treasury XML and BLS CPI connectors and the blinded coding worksheet. `scripts/build_wordpress.py` rebuilds that historical application export. Its page fragments and runtime are not the current portfolio deployment. Do not install that export over the static portfolio.

Python and R execute in the reproducible research environment. Native Stata syntax is included, with execution unverified. The numerical paper retains its dated input vintage. A new API retrieval must be checked and documented before changing a published result. First-pass coding provenance is retained; independent reliability remains unmeasured.

## Updating the portfolio

1. Rebuild affected research outputs and run the relevant checks if the findings change.
2. Upload changed public figures or archives through WordPress Media and record the resulting URLs in `wordpress/media-urls.json`.
3. Run `python scripts/build_portfolio.py`.
4. Update each affected page from `portfolio/site/pages/` in the WordPress code editor.
5. Install `portfolio/site/template.html` in the shared Pages template, `header.html` in the low-priority head field and `footer.html` in the footer field. Preserve any unrelated settings.
6. Keep Home 844 as the static front page. Projects 764 remains a separate index.
7. Enter page-specific titles, descriptions and noindex settings from `portfolio/site/seo.json` in the WP SEO meta box. Do not add generic keyword lists or duplicate canonical tags.
8. Check the public landing page, article, directory links, downloads, figure loading, narrow-screen layout and rendered search metadata.

The source archive preserves the original evidence and reproducible tools. Changes to presentation do not change research records, quoted documents or author attribution.
