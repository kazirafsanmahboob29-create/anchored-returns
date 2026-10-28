#!/usr/bin/env python3
"""Build the static Dartmouth portfolio from its page map and checked results."""

from pathlib import Path
from html import escape
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "portfolio/site"
OUT = SITE / "pages"
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((SITE / "site.json").read_text())
base = cfg["base"]
ids = cfg["pages"]
profiles = cfg["profiles"]
seo = json.loads((SITE / "seo.json").read_text()) if (SITE / "seo.json").exists() else {}
urls = {
    name: cfg.get("urls", {}).get(name, base + "?page_id=" + str(value))
    for name, value in ids.items()
}
urls["home"] = base
media = {
    u.rsplit("/", 1)[-1]: u for u in json.loads((ROOT / "wordpress/media-urls.json").read_text())
}
study = json.loads((ROOT / "reports/factor-study/study.json").read_text())
assert study["coverage"]["complete"] == 533
models = {m["id"]: m for m in study["models"]}
coefficient = lambda model, term: next(
    c for c in models[model]["coefficients"] if c["term"] == term
)
metrics = {m["model"]: m for m in study["holdout"]["metrics"]}
source_zip = media["anchored-returns-code-0.2.0.zip"]
study_zip = media["factor-study-wordpress-20261026.zip"]


def link(label, url, **attrs):
    extra = "".join(
        " " + escape(key) + '="' + escape(value, quote=True) + '"' for key, value in attrs.items()
    )
    return '<a href="' + escape(url, quote=True) + '"' + extra + ">" + escape(label) + "</a>"


def page_link(label, key):
    return link(label, urls[key])


def write(name, html):
    assert "—" not in html
    (OUT / (name + ".html")).write_text(
        "<!-- wp:html -->\n" + html.strip() + "\n<!-- /wp:html -->\n"
    )


github = link("GitHub", profiles["github"], rel="me")
goodreads = link(
    "Goodreads",
    profiles.get("goodreads") or urls["goodreads"],
    **({"rel": "me"} if profiles.get("goodreads") else {}),
)
scholar = link(
    "Google Scholar",
    profiles.get("scholar") or urls["scholar"],
    **({"rel": "me"} if profiles.get("scholar") else {}),
)
contact = (
    '<nav class="ar-social" aria-label="Contact and profiles">'
    + link("Email", "mailto:" + cfg["email"])
    + link("LinkedIn", profiles["linkedin"], rel="me")
    + github
    + goodreads
    + scholar
    + "</nav>"
)
write(
    "home",
    """<section aria-labelledby="about-me"><h1 class="ar-home-name">Kazi Rafsan Mahboob</h1><h2 class="ar-about-label" id="about-me">About me</h2><div class="ar-home-copy"><p>I’m a student at """
    + link("Dartmouth College", "https://home.dartmouth.edu/")
    + """, originally from """
    + link("Dhaka, Bangladesh", "https://en.wikipedia.org/wiki/Dhaka")
    + """. My interests include mathematics, economics and how people make decisions.</p><p>My current research looks at how utility commissions set returns on equity. In """
    + page_link("Anchored Returns", "article")
    + """, I compare earlier awards with interest rates and other financial conditions using rate-case records and economic data.</p><p class="ar-home-browse">You can find my """
    + page_link("projects", "projects")
    + """, """
    + page_link("coursework", "coursework")
    + """, """
    + page_link("papers", "papers")
    + """ and """
    + page_link("photography", "photography")
    + """ here.</p></div>"""
    + contact
    + """</section>""",
)
write(
    "about",
    """<p>I’m Kazi Rafsan Mahboob, a student at """
    + link("Dartmouth College", "https://home.dartmouth.edu/")
    + """. I grew up in """
    + link("Dhaka, Bangladesh", "https://en.wikipedia.org/wiki/Dhaka")
    + """ and am interested in mathematics, economics and how people make decisions.</p><p>My current project, """
    + page_link("Anchored Returns", "article")
    + """, studies how utility commissions set authorized returns on equity. I use rate-case records and financial data to examine the role of market conditions and earlier awards.</p><p>This site brings together my """
    + page_link("projects", "projects")
    + """, """
    + page_link("coursework", "coursework")
    + """, """
    + page_link("papers", "papers")
    + """ and """
    + page_link("photography", "photography")
    + """.</p>"""
    + contact,
)
write(
    "projects",
    """<p class="ar-subtitle">Research and technical projects.</p><ul class="ar-list"><li><h2>"""
    + page_link("Market Conditions and Persistence in Authorized Utility Returns", "article")
    + """</h2><p class="ar-list-meta"><time datetime="2026-10-26">October 26, 2026</time> · Regulatory economics · Python, R and JavaScript</p><p>Why do successive utility awards look so similar? A study of 533 observations tests the relationship between authorized returns, financial conditions and the utility’s previous award.</p><div class="ar-text-links">"""
    + page_link("Read the findings", "article")
    + page_link("Code and replication", "github")
    + """</div></li></ul>""",
)

rows = "".join(
    "<tr><td>"
    + label
    + "</td><td>"
    + f"{metrics[key]['mae_bp']:.1f}"
    + "</td><td>"
    + f"{metrics[key]['rmse_bp']:.1f}"
    + "</td></tr>"
    for key, label in [
        ("training_mean", "Training-period mean"),
        ("previous_award", "Previous award"),
        ("market_case", "Market and case variables"),
        ("with_prior", "Model with previous award"),
    ]
)
coefs = "".join(
    "<tr><td>"
    + label
    + "</td><td>"
    + f"{coefficient(key, 'treasury90')['estimate']:.3f}"
    + "</td><td>"
    + ("Not included" if key == "market_case" else f"{coefficient(key, 'prior')['estimate']:.3f}")
    + "</td><td>"
    + f"{models[key]['r2']:.3f}"
    + "</td></tr>"
    for key, label in [
        ("market_case", "Market and case variables"),
        ("with_prior", "Add previous award"),
        ("state_year", "State and year controls"),
        ("entity_year", "Utility-state and year controls"),
    ]
)
article = (
    """<p class="ar-meta"><time datetime="2026-10-26">October 26, 2026</time> · Regulatory economics · Kazi Rafsan Mahboob</p><div class="ar-text-links">"""
    + page_link("Code and replication", "github")
    + link("Study data", study_zip)
    + """</div><div class="ar-article-intro"><p>State commissions set the return on equity a regulated utility can earn through its rates. I wanted to understand how those awards relate to financial conditions and how much information is already contained in the utility’s previous award.</p><p>I built a panel of <strong>533 complete observations from 2010–2024</strong>. Current and previous awards have a correlation of <strong>0.793</strong>. The positive Treasury relationship in the pooled model becomes close to zero after state and year controls. In a later-case test, adding the previous award reduces mean absolute error from <strong>53.1 to 23.3 basis points</strong>. Using the previous award alone gives 24.2, so most of that improvement comes from accounting for persistence.</p></div>
<nav class="ar-toc" aria-label="Article contents"><a href="#question">Question</a><a href="#data">Data and method</a><a href="#results">Results</a><a href="#orders">Original decisions</a><a href="#checks">Checks</a><a href="#sources">Sources</a></nav>
<h2 id="question">The question</h2>
<p>Higher interest rates make a change in allowed returns plausible. They do not imply that the two should move one for one. A commission considers utility risk, financial estimates, investment needs, regulatory rules and the evidence in the proceeding. A formula adjustment or performance penalty can also change the return used in rates.</p>
<p>I therefore compare three sources of variation: financial conditions, differences between cases, and earlier awards for the same utility. The question is whether the market relationship remains after those differences are taken into account. """
    + link(
        "Rode and Fischbeck’s study of regulated equity returns",
        "https://doi.org/10.1016/j.enpol.2019.110891",
    )
    + """ provides a useful starting point for the financial question.</p>
<h2 id="data">Data and method</h2>
<p>The case records come from the """
    + link(
        "Edison Electric Institute’s Rate Review workbook",
        "https://www.eei.org/issues-and-policy/finance-and-tax",
    )
    + """, preserved at its 2025 Q3 version. Its completed base-rate table contains 2,230 observations spanning 1980 through September 2025. For this study I use complete calendar years from 2010 through 2024: 777 entries, of which 589 report an award. Requiring the economic measures, filing duration and a valid earlier award leaves 533 observations across 47 jurisdictions and 131 utility-state groups.</p>
<p>I join each authorization to Treasury yields, the yield curve, CPI inflation and financial stress from """
    + link("FRED", "https://fred.stlouisfed.org/")
    + '''. Market windows end before the authorization date. The previous award is the latest strictly earlier observation for the same utility-state label within ten years. Missing returns remain missing, and the exported panel retains the excluded entries and their reasons.</p>
<p>I estimate four OLS specifications on the same 533 observations: market and case variables; the same model with the previous award; state and year effects; and utility-state and year effects. Using one common sample prevents a change in the observations from being mistaken for a change caused by adding a predictor. Uncertainty is clustered by state and authorization quarter.</p>
<h2 id="results">What the models show</h2>
<p>The simple correlation with the previous award is 0.793, compared with 0.149 for the prior 90-day Treasury mean. In the market-and-case model, a one-percentage-point higher Treasury yield is associated with 15.8 basis points of higher allowed ROE. With state and year controls, that estimate is -0.3 basis points and its interval includes zero.</p>
<figure><img src="'''
    + media["persistence.png"]
    + '''" width="1700" height="1000" alt="Current versus previous authorized utility returns for 533 observations, with an unchanged-award reference line."><figcaption>Each point is a recorded authorization. The dashed line marks an unchanged award. Figure produced in R from the estimation panel.</figcaption></figure>
<p>The previous-award coefficient remains positive with state and year controls: a one-percentage-point higher earlier award is associated with 26.7 basis points of higher current ROE. Adding utility-state effects gives a similar point estimate, but its wider interval includes zero. Stable utility characteristics, regulatory mechanisms and persistent policy differences are therefore plausible parts of the explanation.</p>
<figure><img src="'''
    + media["coefficients.png"]
    + """" width="1800" height="1150" loading="lazy" alt="Treasury and previous-award coefficients across four models, with clustered confidence intervals."><figcaption>The models use the same observations. Lines show 95% normal Wald intervals with finite-sample-corrected clustering by state and authorization quarter. Year controls absorb much of the common movement in national financial series.</figcaption></figure>
<details><summary>Regression estimates and units</summary><div class="table-wrap"><table><thead><tr><th>Specification</th><th>Treasury coefficient</th><th>Previous-award coefficient</th><th>R²</th></tr></thead><tbody>"""
    + coefs
    + """</tbody></table></div><p class="ar-note">The outcome and return predictors are in percentage points. A coefficient of 0.10 represents 10 basis points of associated ROE change per one-percentage-point predictor change. R² includes the fixed effects and does not measure forecasting accuracy.</p></details>
<h3>A test on later decisions</h3>
<p>I estimate coefficients on 345 observations from 2010–2019, then evaluate 188 observations from 2020–2024. The market-and-case model performs worse than the training-period mean. Adding the previous award substantially improves that model, but improves on the previous-award baseline by only 0.9 basis points of mean absolute error.</p>
<div class="table-wrap"><table><thead><tr><th>Prediction rule</th><th>MAE, bp</th><th>RMSE, bp</th></tr></thead><tbody>"""
    + rows
    + """</tbody></table></div>
<p>That comparison changed how I read the result. A more elaborate model does not automatically give a useful forecasting gain. Here the previous award is the stronger benchmark to beat. The test is retrospective: coefficients stay fixed, earlier test-period awards can inform later cases, and the economic histories include later revisions.</p>
<h2 id="orders">What the original decisions add</h2>
<p>A persistent numerical outcome does not identify a commission’s reasoning. The New England document cohort contains 27 orders and 68 source-linked numeric facts. I use those decisions to distinguish financial return estimates from the return actually used in rates.</p>
<p>In """
    + link("Central Maine Power’s 2020 order", media["ar-cand-me-2018-00194.pdf"] + "#page=142")
    + """, a 9.25% base return becomes an 8.25% operative award after a 100-basis-point performance reduction. In """
    + link("United Illuminating’s 2023 order", media["ar-cand-ct-22-08-08.pdf"] + "#page=7")
    + """, a 9.10% base return becomes 8.63% after a 47-basis-point reduction. Neither operative award should be treated as an unadjusted financial estimate of the cost of equity.</p>
<p>The broader EEI New England panel contains 57 completed electric observations from 2010–2024, with 46 reported awards. Among eight utility-state labels present in both 2010–2014 and 2020–2024, seven have lower later-period means. Equal weighting of those groups gives a decline of 39.8 basis points. This reduces changes in the utility mix, although the proceedings and mechanisms still differ.</p>
<h2 id="checks">Checks and next questions</h2>
<p>The state-and-year previous-award coefficient is 0.269 with a 30-day market window and 0.264 when New England is omitted, close to the main estimate of 0.267. Adding requested ROE on the same 531 request-pair observations reduces it from 0.265 to 0.178. Requests add information, but are part of the same proceeding and should not be treated as an external cause.</p>
<p>Python builds the panel and estimates the models. Base R reproduces 27 coefficient and clustered-standard-error pairs and draws the figures. A separate JavaScript implementation reproduces the browser calculations. The """
    + link("replication package", study_zip)
    + """ includes the source records, exclusion reasons, timing rules, models and native statistical scripts.</p>
<p>The numerical result is persistence in authorized returns. It is consistent with several mechanisms, including stable risk, formula design, commission policy and reliance on earlier decisions. Distinguishing them requires evidence about the rules and reasoning in individual proceedings. Complete first-pass text coding currently covers three orders and 67 units; independent coding agreement remains unmeasured. The separate historical RRA benchmark series also remains incomplete.</p>
<h2 id="sources">Sources</h2><ol class="ar-references"><li>"""
    + link(
        "Edison Electric Institute, Rate Review 2025 Q3",
        "https://www.eei.org/issues-and-policy/finance-and-tax",
    )
    + """. Original worksheet rows and workbook fingerprint are retained in the study.</li><li>Board of Governors: """
    + link("DGS10", "https://fred.stlouisfed.org/series/DGS10")
    + """. Federal Reserve Bank of St. Louis: """
    + link("T10Y3M", "https://fred.stlouisfed.org/series/T10Y3M")
    + """ and """
    + link("STLFSI4", "https://fred.stlouisfed.org/series/STLFSI4")
    + """. Bureau of Labor Statistics: """
    + link("CPIAUCNS", "https://fred.stlouisfed.org/series/CPIAUCNS")
    + """. Historical vintage retrieved October 26, 2026 through FRED.</li><li>"""
    + link("BLS Public Data API", "https://www.bls.gov/developers/")
    + """, CPI-U CUUR0000SA0. All 189 overlapping months from January 2010 to September 2025 match the preserved FRED CPI series.</li><li>David C. Rode and Paul S. Fischbeck (2019), """
    + link("Regulated equity returns: A puzzle", "https://doi.org/10.1016/j.enpol.2019.110891")
    + """, <em>Energy Policy</em> 133, 110891.</li></ol><p class="ar-related">"""
    + page_link("All projects", "projects")
    + """ · """
    + page_link("Code and replication", "github")
    + """ · """
    + link("Download the study", study_zip)
    + """</p>"""
)
write("article", article)
write(
    "coursework",
    """<p class="ar-subtitle">Selected work from my courses at Dartmouth.</p><ul class="ar-course-list"><li>"""
    + link(
        "Game Theory & Economic Behavior · ECON 35", base + "game-theory-economic-behavior-econ-35/"
    )
    + """</li><li>"""
    + link(
        "Englishes of the World · First-Year Seminar",
        base + "englishes-of-the-world-first-year-seminar/",
    )
    + """</li><li>"""
    + link("Words in Context · Writing 5", base + "words-in-context-writing-5/")
    + """</li></ul><h2>Writing</h2><ul class="ar-course-list"><li>"""
    + link("Project One", base + "project-one/")
    + """</li><li>"""
    + link("Project Two", base + "project-two/")
    + """</li><li>"""
    + link("A Language I Thought I Knew", base + "a-language-i-thought-i-knew/")
    + """</li></ul>""",
)
write(
    "papers",
    """<p>Research notes, working papers and selected essays.</p><h2>Working research</h2><ul class="ar-list"><li><h3>"""
    + page_link("Market Conditions and Persistence in Authorized Utility Returns", "article")
    + """</h3><p class="ar-list-meta">Research note · October 2026</p><p>A source-linked empirical study of market conditions and previous awards in utility rate cases.</p>"""
    + page_link("Read the research note", "article")
    + """</li></ul><p class="ar-note">Journal publications and formal manuscripts will be listed separately when available.</p>""",
)
write(
    "github",
    """<p>Code, reproducible analyses and project documentation.</p><p>"""
    + link("My GitHub profile ↗", profiles["github"], rel="me")
    + """</p><h2>Anchored Returns</h2><p>The source package contains the Python analysis, R and Stata scripts, browser tools, tests and documentation. The study download includes the preserved inputs needed to reproduce the numerical results.</p><div class="ar-text-links">"""
    + link("Source code", source_zip)
    + link("Study and input data", study_zip)
    + page_link("Research findings", "article")
    + """</div><details><summary>Run the project locally</summary><pre><code>python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
./research serve</code></pre><p class="ar-note">The included README explains the analysis commands, source restoration and optional R checks. Native Stata syntax is included, with execution unverified.</p></details>""",
)
write(
    "code",
    """<p>The research findings are published in """
    + page_link("Market Conditions and Persistence in Authorized Utility Returns", "article")
    + """. Code, tools and replication instructions are collected on the """
    + page_link("code page", "github")
    + """.</p><div class="ar-text-links">"""
    + page_link("Read the findings", "article")
    + page_link("Code and replication", "github")
    + link("Download the study", study_zip)
    + """</div>""",
)
write(
    "goodreads",
    (
        "<p>" + link("My Goodreads profile ↗", profiles["goodreads"], rel="me") + "</p>"
        if profiles.get("goodreads")
        else ""
    )
    + """<p>Books and reading notes.</p><div class="ar-empty"><p>No reading notes posted yet.</p></div>""",
)
write(
    "scholar",
    (
        "<p>" + link("My Google Scholar profile ↗", profiles["scholar"], rel="me") + "</p>"
        if profiles.get("scholar")
        else ""
    )
    + """<p>Publications and citations will be listed here when available.</p><p>For current work, see my """
    + page_link("research projects", "projects")
    + """ and """
    + page_link("papers", "papers")
    + """.</p>""",
)
write(
    "photography",
    """<p>Photographs and notes.</p><div class="ar-empty"><p>No photographs posted yet.</p></div>""",
)
nav = (
    '<nav aria-label="Portfolio">'
    + "".join(
        page_link(label, key)
        for key, label in [
            ("projects", "Projects"),
            ("coursework", "Coursework"),
            ("papers", "Papers"),
            ("photography", "Photography"),
        ]
    )
    + "</nav>"
)
header = (
    '<header class="ar-header">'
    + link(cfg["author"], base, **{"class": "ar-name"})
    + nav
    + "</header>"
)
footer = (
    '<footer class="ar-footer"><span>'
    + cfg["author"]
    + " · Dartmouth College</span><div>"
    + page_link("About", "about")
    + link("Email", "mailto:" + cfg["email"])
    + link("GitHub", profiles["github"])
    + "</div></footer>"
)
template = (
    "<!-- wp:html -->\n"
    + header
    + '\n<!-- /wp:html -->\n<!-- wp:group {"tagName":"main","className":"ar-page"} -->\n<main class="wp-block-group ar-page"><!-- wp:post-title {"level":1} /--><!-- wp:post-content /--></main>\n<!-- /wp:group -->\n<!-- wp:html -->\n'
    + footer
    + "\n<!-- /wp:html -->\n"
)
(SITE / "template.html").write_text(template)
person = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": base + "#person",
    "name": cfg["author"],
    "url": base,
    "email": "mailto:" + cfg["email"],
    "affiliation": {
        "@type": "CollegeOrUniversity",
        "name": "Dartmouth College",
        "url": "https://home.dartmouth.edu/",
    },
    "sameAs": [v for v in profiles.values() if v],
}
head = (
    "<style>\n"
    + (SITE / "style.css").read_text()
    + '\n</style>\n<script type="application/ld+json">'
    + json.dumps(person, ensure_ascii=False).replace("<", "\\u003c")
    + "</script>\n"
)
(SITE / "header.html").write_text(head)
(SITE / "footer.html").write_text(
    "<!-- Research software is distributed separately. Portfolio pages require no application runtime. -->\n"
)
# Preview uses the same content and CSS as the WordPress fragments.
for name in ids:
    if not (OUT / (name + ".html")).exists():
        continue
    html = (OUT / (name + ".html")).read_text()
    title = (
        "Kazi Rafsan Mahboob"
        if name == "home"
        else (
            "Market Conditions and Persistence in Authorized Utility Returns"
            if name == "article"
            else name.title()
        )
    )
    page_meta = seo.get(name, {})
    preview = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + escape(page_meta.get("title", title))
        + '</title><meta name="description" content="'
        + escape(page_meta.get("description", ""), quote=True)
        + '">'
        + head
        + "</head><body"
        + (' class="home"' if name == "home" else "")
        + ">"
        + header
        + '<main class="ar-page">'
        + ("" if name == "home" else '<h1 class="wp-block-post-title">' + title + "</h1>")
        + html
        + "</main>"
        + footer
        + "</body></html>"
    )
    (SITE / (name + "-preview.html")).write_text(preview)
(SITE / "manifest.json").write_text(
    json.dumps(
        {
            "schema": "dartmouth-portfolio/2",
            "base": base,
            "pages": ids,
            "profiles": profiles,
            "seo": seo,
            "research_panel_n": 533,
            "files": {
                str(p.relative_to(SITE)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(SITE.glob("pages/*.html"))
            },
        },
        indent=2,
    )
    + "\n"
)
print(
    json.dumps(
        {
            "pages": len(ids),
            "home_id": ids["home"],
            "application_runtime": False,
            "output": str(SITE),
        }
    )
)
