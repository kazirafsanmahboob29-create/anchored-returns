#!/usr/bin/env python3
"""Build a self-contained WordPress application and portfolio page fragments.

The footer is installed through WordPress Advanced Settings. Data compression is
lossless and verified before use. No third-party application host is required.
"""

from pathlib import Path
import base64, gzip, hashlib, json, mimetypes, re
from html import escape, unescape
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "wordpress"
OUT.mkdir(exist_ok=True)
BASE = "https://journeys.dartmouth.edu/kazirafsanmahboob29/"
urls = json.loads((OUT / "media-urls.json").read_text())
by_name = {u.rsplit("/", 1)[-1]: u for u in urls}
upl = json.loads((OUT / "uploads.json").read_text())
source_index = json.loads((OUT / "source-index.json").read_text())
media = {k: by_name[v["upload_name"]] for k, v in upl.items() if v["upload_name"] in by_name}
media.update(
    {
        "reports/factor-study/persistence.png": by_name["persistence.png"],
        "reports/factor-study/coefficients.png": by_name["coefficients.png"],
        "reports/factor-study/factor-study.zip": by_name.get(
            "factor-study-wordpress-20261026.zip", by_name["factor-study.zip"]
        ),
    }
)
for k, v in source_index.items():
    if k not in media and v.get("source_url"):
        media[k] = v["source_url"]
files = {}


def asset(path):
    p = ROOT / path
    if p.exists() and p.is_file() and p.stat().st_size < 4_000_000:
        files[path] = {
            "mime": mimetypes.guess_type(path)[0] or "application/octet-stream",
            "base64": base64.b64encode(p.read_bytes()).decode(),
        }
        return "ar-file:" + path
    return BASE + "?page_id=769#sources"


def resolve(url):
    if url.startswith("/reader?"):
        q = parse_qs(urlsplit(unescape(url)).query)
        path = q.get("file", [""])[0]
        page = q.get("page", ["1"])[0]
        return media.get(path, BASE + "?page_id=769#sources") + "#page=" + page
    if url in ("models.html", "/models"):
        return BASE + "?page_id=769"
    if url in ("project.html", "project"):
        return BASE + "?page_id=761"
    if url.startswith("index.html"):
        return BASE + "?page_id=769#sources"
    if url.startswith("?") and "#compare" in url:
        return BASE + "?page_id=769&" + url[1:]
    if url.startswith("../"):
        path = url[3:]
        return media.get(path) or asset(path)
    return url


pattern = re.compile(r'\b(href|src)="([^"]+)"')


def rewrite(html):
    return pattern.sub(
        lambda m: m[1] + '="' + escape(resolve(unescape(m[2])), quote=True) + '"', html
    )


project = (ROOT / "presentation/project.html").read_text()
regional = json.loads(
    re.search(r'<script id="regional-data"[^>]*>(.*?)</script>', project, re.S)[1]
)
models = (ROOT / "presentation/models.html").read_text()
modelhtml = re.search(r"<main[^>]*>(.*?)</main>", models, re.S)[1]
# The application owns its visible primary heading.
modelhtml = modelhtml.replace("Retrieve current economic data", "Refresh Treasury and CPI").replace(
    "Refresh retrieves four FRED CSV histories and checks CPI against the direct BLS API. It updates economic measurements and reruns the selected model. It does not add newly decided cases or revise the paper.",
    "Refresh retrieves Treasury yield histories and CPI directly from their publishers. Financial stress remains at the paper’s saved vintage. The recalculated model is a separate run; the paper and EEI case table remain fixed.",
)
regionalhtml = re.search(r'<div class="regional-tool">(.*?)</div>\s*<p>Vermont Gas', project, re.S)[
    0
].split("<p>Vermont Gas")[0]
comparehtml = re.search(r'<div class="comparison-tool">(.*?)</div>\s*<noscript>', project, re.S)[
    0
].split("<noscript>")[0]
cohort = {r["pdf_path"]: r for r in regional["records"]}
source_rows = [
    dict(
        v,
        pdf_path=k,
        local_url=media.get(k, v.get("source_url")),
        display_role=("Selected cohort: " + cohort[k]["stratum"] + " order")
        if k in cohort
        else v.get("role", v.get("source_kind", "Research figure")),
    )
    for k, v in source_index.items()
    if k.endswith(".pdf")
]
facts = []
for path in [
    "data/research/assistant_verified_case_facts.json",
    "data/research/cohort_numeric_facts_v0.1.5.json",
]:
    for row in json.loads((ROOT / path).read_text())["facts"]:
        spans = row.get("spans") or [
            dict(page=row.get("pdf_page"), exact_text=row.get("evidence", {}).get("exact_text", ""))
        ]
        facts.append(
            dict(
                fact_id=row["fact_id"],
                case_id=row["case_id"],
                field=row["field"],
                value=row.get("value", row.get("printed_value")),
                unit=row.get("unit", row.get("printed_unit")),
                spans=spans,
                pdf_sha256=row["pdf_sha256"],
                notes=row.get("notes", ""),
            )
        )
ledger = json.loads((ROOT / "data/research/empirical_ledger_v0.1.3.json").read_text())
ledger_sources = {r["source_id"]: r for r in ledger["sources"]}
for row in ledger["numeric_facts"]:
    facts.append(
        dict(
            fact_id=row["fact_id"],
            case_id=row["case_id"],
            field=row["field"],
            value=row["printed_value"],
            unit=row["printed_unit"],
            spans=row["spans"],
            pdf_sha256=ledger_sources[row["source_id"]]["pdf_sha256"],
            notes=row.get("notes", ""),
        )
    )
assert len(facts) == 68
packet_path = "data/research/reliability/three-orders-2026-10-02/rater/"
packet = json.loads((ROOT / (packet_path + "packet.json")).read_text())
blank = json.loads((ROOT / (packet_path + "ratings_blank.json")).read_text())
for path in ["codebook/Anchored_Returns_Codebook_v0.1.2.docx", "docs/empirical_protocol_v0.1.3.md"]:
    if (ROOT / path).exists():
        asset(path)
# Every local link is packaged or mapped to a verified media URL.
markup = (
    """<div class="app-shell"><nav class="tool-nav" aria-label="Research tools"><button data-view="models" aria-pressed="true">Models</button><button data-view="compare" aria-pressed="false">Period comparison</button><button data-view="regional" aria-pressed="false">Original orders</button><button data-view="sources" aria-pressed="false">Sources</button><button data-view="coding" aria-pressed="false">Coding worksheet</button></nav><section data-panel="models" class="workbench">"""
    + modelhtml
    + """</section><section data-panel="compare" class="workbench" hidden><p class="eyebrow">EEI / 2010–2025 Q3</p><h2>Compare authorization periods</h2><p>Filter the national records and compare changes in awards and matched Treasury yields.</p>"""
    + comparehtml
    + """</section><section data-panel="regional" class="workbench" hidden><p class="eyebrow">NEW ENGLAND / ORIGINAL DECISIONS</p><h2>Read the awards in context</h2><p>27 documents in the selected cohort. Primary orders, settlement approvals and formula implementations are identified separately. PDF page links open the preserved original decision.</p>"""
    + regionalhtml
    + """<details><summary>Search 68 verified numeric facts</summary><p class="note">Each entry records the printed value and the exact supporting passage. These source checks are separate from independent passage ratings.</p><label>Search facts<input type="search" id="fact-search" placeholder="Utility, field or passage"></label><p id="fact-count" class="note"></p><div id="fact-results"></div></details></section><section data-panel="sources" class="workbench" hidden><p class="eyebrow">SOURCE LIBRARY</p><h2>Documents and reproducible data</h2><p>Search original decisions, supporting documents and benchmark reports. Each record includes its publisher link and preserved-file fingerprint.</p><label>Search documents<input type="search" id="source-search" placeholder="State, docket, title or source ID"></label><p id="source-count" class="note" role="status"></p><div id="source-results"></div><h3>Study downloads</h3><ul><li><a href="../reports/factor-study/factor-study.zip">Factor study: Python, R, Stata, data and methods</a></li><li><a href="../reports/national-study/national-study.zip">National period-comparison study</a></li><li><a href="../data/external/eei/eei_rate_review_2025_q3.xlsx">Original EEI workbook</a></li><li><a href="../docs/factor_study.md">Technical methods</a></li></ul></section><section data-panel="coding" class="workbench" hidden><p class="eyebrow">TEXT CODING / 67 UNITS</p><h2>Independent coding worksheet</h2><p>Record a separate set of passage ratings without seeing the first-pass labels. Read the full page context and source decision before assigning a code. Unset values remain missing. Ratings stay in this browser until exported; the site does not collect submissions.</p><p><a href="../codebook/Anchored_Returns_Codebook_v0.1.2.docx">Read the codebook</a></p><label>Rater identifier (use an alias)<input id="rater-id" maxlength="80" autocomplete="off"></label><label class="check-label"><input type="checkbox" id="rater-independent"> I completed these ratings myself without consulting reference labels.</label><div class="tool-actions"><button id="coding-prev">Previous unit</button><button id="coding-next">Next unit</button><button id="coding-export">Export ratings</button></div><p id="coding-status" class="note" role="status"></p><div id="coding-unit"></div></section></div>"""
)
markup = rewrite(markup)
article = re.search(r'<main id="main">(.*?)</main>', project, re.S)[1]
article = re.sub(r'<header class="article-header">.*?</header>', "", article, flags=re.S)
# Interactive calculations have a dedicated workbench; article keeps the findings.
article = re.sub(
    r'<div class="regional-tool">.*?</div>\s*<p>Vermont Gas',
    '<p><a href="'
    + BASE
    + '?page_id=769#regional">Explore the original orders</a>.</p><p>Vermont Gas',
    article,
    flags=re.S,
)
article = re.sub(
    r'<div class="comparison-tool">.*?</div>\s*<noscript>.*?</noscript>',
    '<p><a href="' + BASE + '?page_id=769#compare">Open the period-comparison tool</a>.</p>',
    article,
    flags=re.S,
)
article = article.replace(
    "refresh the economic histories", "refresh Treasury and CPI histories"
).replace(
    "Economic refreshes are stored separately so a live retrieval cannot silently change the paper’s results.",
    "The browser exports each economic retrieval separately, including the raw responses and retrieval dates. Financial stress remains at the saved vintage. Refreshing the workbench does not revise the paper.",
)
article = article.replace(
    "The table below reports that coverage alongside the awards.",
    "The original-order tool reports that coverage alongside the awards.",
)
article = rewrite(article)
# Documents linked in the static WordPress article are available inside the app.
article = re.sub(r'ar-file:([^"#]+)', lambda m: BASE + "?page_id=769&download=" + m[1], article)
article = (
    '<p class="ar-meta">Kazi Rafsan Mahboob · Regulatory economics · October 2026</p><p class="ar-links"><a href="'
    + BASE
    + '?page_id=769">Open the research workbench ↗</a><a href="'
    + media["reports/factor-study/factor-study.zip"]
    + '">Download the study</a></p>'
    + article
)
home = (
    '''<div class="ar-intro"><p>I’m a student at Dartmouth College. I use this site to share my research, software and coursework.</p><p>My current project studies how utility commissions set returns on equity, using rate-case records and financial data.</p></div><article class="ar-project"><p class="ar-meta">01 / REGULATORY ECONOMICS · OCTOBER 2026</p><h2><a href="'''
    + BASE
    + '''?page_id=761">Market Conditions and Persistence in Authorized Utility Returns</a></h2><p>Do authorized utility returns move with interest rates, or do earlier awards explain more of the variation? I built a panel of 533 observations and compared market variables, prior awards and jurisdiction controls. Readers can change the specifications and inspect the source records.</p><p class="ar-tags">Python · R · JavaScript · Panel regression · Primary-source research</p><div class="ar-links"><a href="'''
    + BASE
    + '''?page_id=761">Read the investigation ↗</a><a href="'''
    + BASE
    + '''?page_id=769">Use the workbench ↗</a><a href="'''
    + media["reports/factor-study/factor-study.zip"]
    + """">Data and code ↗</a></div></article>"""
)
course = (
    """<p>Selected work from my courses at Dartmouth. These pages include essays, projects and reflections from the original course sites.</p><ul class="ar-course-list">"""
    + "".join(
        '<li><a href="' + BASE + url + '">' + label + " ↗</a></li>"
        for url, label in [
            ("fys/", "Spring 2026 coursework"),
            ("game-theory-economic-behavior-econ-35/", "Game Theory & Economic Behavior"),
            ("englishes-of-the-world-first-year-seminar/", "Englishes of the World"),
            ("words-in-context-writing-5/", "Words in Context"),
            ("project-one/", "Writing project one"),
            ("project-two/", "Writing project two"),
            ("a-language-i-thought-i-knew/", "A Language I Thought I Knew"),
        ]
    )
    + """</ul>"""
)
source_zip = by_name.get("anchored-returns-code-0.2.0.zip") or by_name.get(
    "anchored-returns-source-0.2.0.zip"
)
if source_zip:
    article += (
        '<p><a href="'
        + source_zip
        + '">Download the complete project source</a> · Python, R, Stata, browser modules, WordPress installation files and tests.</p>'
    )
    home = home.replace("Data and code ↗", "Study data and code ↗").replace(
        "</div></article>", '<a href="' + source_zip + '">Full project source ↗</a></div></article>'
    )
    markup = markup.replace(
        "<h3>Study downloads</h3>",
        '<p><a href="'
        + source_zip
        + '">Download the complete project source ↗</a></p><h3>Study downloads</h3>',
    )
for name, html in [("project", article), ("home", home), ("coursework", course)]:
    assert "—" not in html
    (OUT / (name + ".html")).write_text("<!-- wp:html -->\n" + html + "\n<!-- /wp:html -->")
for path in [
    "reports/factor-study/study.json",
    "reports/factor-study/macro.json",
    "reports/national-study/study.json",
]:
    asset(path)
payload = {
    "files": files,
    "media": media,
    "sources": source_rows,
    "regional": regional,
    "facts": facts,
    "packet": packet,
    "blank": blank,
}
raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
bootstrap = r"""(async()=>{const host=document.getElementById('anchored-returns-app');if(!host)return;const realDocument=document;try{const bytes=Uint8Array.from(atob(PAYLOAD),c=>c.charCodeAt(0)),raw=new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==HASH)throw Error('The study bundle failed its integrity check.');const assets=JSON.parse(new TextDecoder().decode(raw)),root=host.attachShadow({mode:'open'});root.innerHTML='<style>'+STYLES+'</style>'+MARKUP;const document=new Proxy(realDocument,{get(target,key){if(['getElementById','querySelector','querySelectorAll','addEventListener'].includes(key))return root[key].bind(root);const value=target[key];return typeof value==='function'?value.bind(target):value;}});const localBytes=path=>Uint8Array.from(atob(assets.files[path].base64),c=>c.charCodeAt(0));const fetch=async url=>{const path=String(url).replace(/^\.\.\//,'');if(!assets.files[path])throw Error('Unknown local study asset: '+path);return new Response(localBytes(path),{headers:{'Content-Type':assets.files[path].mime}});};const fileUrl=path=>URL.createObjectURL(new Blob([localBytes(path)],{type:assets.files[path].mime}));root.addEventListener('click',event=>{const a=event.target.closest('a');if(a?.getAttribute('href')?.startsWith('ar-file:')){event.preventDefault();const path=a.getAttribute('href').slice(8),url=fileUrl(path),link=realDocument.createElement('a');link.href=url;link.download=path.split('/').at(-1);link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}});function showView(view){if(!root.querySelector('[data-panel="'+view+'"]'))view='models';for(const panel of root.querySelectorAll('[data-panel]'))panel.hidden=panel.dataset.panel!==view;for(const button of root.querySelectorAll('[data-view]'))button.setAttribute('aria-pressed',String(button.dataset.view===view));}for(const button of root.querySelectorAll('[data-view]'))button.addEventListener('click',()=>{showView(button.dataset.view);history.replaceState(null,'','#'+button.dataset.view);});showView(location.hash.slice(1));window.addEventListener('hashchange',()=>showView(location.hash.slice(1)));MODULES
const requested=new URL(location.href).searchParams.get('download');if(requested&&assets.files[requested]){showView('sources');const a=realDocument.createElement('a');a.href=fileUrl(requested);a.download=requested.split('/').at(-1);a.textContent='Download '+requested.split('/').at(-1);root.getElementById('source-results').prepend(a);}
}catch(error){host.textContent='The workbench could not load: '+error.message+'. The study download on the research page remains available.';console.error(error);}})();"""
css = (
    (ROOT / "presentation/national/style.css")
    .read_text()
    .replace(":root", ":host")
    .replace("body{", ":host{")
    + (ROOT / "presentation/factors/style.css").read_text()
    + """\n:host{display:block;font-size:15px;line-height:1.85;color:#30383e}[hidden]{display:none!important}.workbench{padding:28px 0;max-width:none}.workbench h1{font-size:27px;text-align:left}.workbench h2{font-size:24px;margin:0 0 16px}.workbench .source-bar h2{font-size:13px;margin:0 0 4px}.workbench .model-charts h2,.workbench section>h2{font-size:17px;margin-top:28px}.tool-nav{display:flex;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--line);padding-bottom:18px}.tool-nav button{border:0;border-bottom:2px solid transparent;border-radius:0;padding:9px 13px;color:#71808a}.tool-nav button[aria-pressed=true]{color:#345e78;border-color:#345e78}.workbench input[type=search],.workbench input[type=text],#rater-id{display:block;width:100%;padding:10px;border:1px solid #ccd6dd;background:white;font:inherit;color:inherit;margin-top:6px}#fact-results article,#source-results article{border-top:1px solid var(--line);padding:20px 0}#source-results h3{font-size:15px;margin:0 0 8px}#fact-results p,#source-results p{font-size:12px;margin:8px 0}code{overflow-wrap:anywhere}#source-results code{font-size:10px}#coding-unit blockquote{margin:20px 0;padding:15px 20px;border-left:2px solid #ccd6dd;background:#f8fafb;white-space:pre-wrap;font-size:14px}.coding-codes{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}#coding-unit textarea{display:block;width:100%;font:inherit;border:1px solid #ccd6dd;min-height:100px;padding:10px}#coding-unit pre{font-size:12px;white-space:pre-wrap;max-height:400px;overflow:auto}@media(max-width:600px){.tool-nav{gap:2px}.tool-nav button{font-size:11px;padding:8px}.workbench{padding:23px 0}.coding-codes{grid-template-columns:1fr 1fr}}"""
)


def module(path):
    return (
        re.sub(r"^import .*?;\n", "", (ROOT / path).read_text(), flags=re.M)
        .replace("export const ", "const ")
        .replace("export function ", "function ")
        .replace("export async function ", "async function ")
    )


compute = module("presentation/factors/compute.mjs")
app = module("presentation/factors/app.mjs")
live = module("wordpress/src/live.mjs")
start = app.index("function sourceStatus(")
end = app.index("\nfunction scatter", start)
app = (
    app[:start]
    + """function sourceStatus(note=''){const latest=snapshot.latest; $('source-status').textContent=(current?'Direct Treasury and BLS retrieval: '+snapshot.retrieved_at_utc+'. Latest Treasury '+latest.treasury.date+': '+latest.treasury.ten.toFixed(2)+'%; latest CPI '+latest.cpi.date+': '+latest.cpi.value+'. Financial stress remains archived. ':'Paper inputs: October 26, 2026 economic histories; EEI 2025 Q3 case table. ')+note;$('use-archive').disabled=!current;$('factor-source-links').replaceChildren();for(const source of snapshot.sources){const a=document.createElement('a');a.href=source.series_url||'https://fred.stlouisfed.org/series/'+source.series_id;a.textContent=source.series_id+' · '+(source.latest?.date||'saved history');a.target='_blank';a.rel='noopener';$('factor-source-links').append(a);}}
"""
    + app[end:]
)
start = app.index("$('refresh-factors').addEventListener")
end = app.index("$('use-archive').addEventListener", start)
app = (
    app[:start]
    + """$('refresh-factors').addEventListener('click',async()=>{const button=$('refresh-factors');button.disabled=true;try{const candidate=await directRefresh(archive,note=>{$('source-status').textContent=note+' Existing model inputs retained until validation completes.';});const joined=rejoin(study.records,candidate.series);if(complete(joined).length<study.coverage.complete)throw Error('The retrieval reduced historical coverage. Existing inputs retained.');snapshot=candidate;records=joined;current=true;sourceStatus('Raw source responses are included in the economic snapshot export.');run();}catch(error){sourceStatus('Refresh unavailable: '+error.message+' Existing inputs retained.');}finally{button.disabled=false;}});
"""
    + app[end:]
)
analysis = module("presentation/national/analysis.mjs")
national = (
    module("presentation/national/index.mjs")
    .replace(
        "Current Site access permissions apply.", "The link preserves these comparison settings."
    )
    .replace(
        "../data/external/eei/eei_rate_review_2025_q3.xlsx",
        media["data/external/eei/eei_rate_review_2025_q3.xlsx"],
    )
)
region = (
    module("presentation/national/regional.mjs")
    .replace("JSON.parse(document.getElementById('regional-data').textContent)", "assets.regional")
    .replace(
        "typeof document!=='undefined'&&document.getElementById('regional-data')", "assets.regional"
    )
    .replace(
        "/reader?file=${encodeURIComponent(r.pdf_path)}&amp;page=${r.award_page}",
        "${assets.media[r.pdf_path]||r.source_url}#page=${r.award_page}",
    )
)
extra = (OUT / "src/library.mjs").read_text()
modules = (
    "await (async()=>{"
    + compute
    + "\n"
    + live
    + "\n"
    + app
    + "})();\n(async()=>{"
    + analysis
    + "\n"
    + national
    + "})();\n(()=>{"
    + region
    + "})();\n(()=>{"
    + extra
    + "})();"
)
slots = {
    "PAYLOAD": json.dumps(encoded),
    "HASH": json.dumps(hashlib.sha256(raw).hexdigest()),
    "STYLES": json.dumps(css),
    "MARKUP": json.dumps(markup),
    "MODULES": modules,
}
script = re.sub(
    r"\b(PAYLOAD|HASH|STYLES|MARKUP|MODULES)\b", lambda match: slots[match[0]], bootstrap
)
assert "__MARKUP__" not in markup and "__MODULES__" not in script
(OUT / "app.js").write_text(script)
footer_slots = dict(
    slots,
    PAYLOAD="host.querySelector('[data-ar-bundle]').getAttribute('data-payload')",
    HASH="host.querySelector('[data-ar-bundle]').getAttribute('data-sha256')",
)
footer_script = re.sub(
    r"\b(PAYLOAD|HASH|STYLES|MARKUP|MODULES)\b", lambda match: footer_slots[match[0]], bootstrap
)
(OUT / "footer.html").write_text(
    "<script>\n" + footer_script.replace("</script", "<\\/script") + "\n</script>"
)
(OUT / "workbench.html").write_text(
    '<!-- wp:html -->\n<div id="anchored-returns-app"><p>Loading the research workbench.</p><div hidden data-ar-bundle="1" data-sha256="'
    + hashlib.sha256(raw).hexdigest()
    + '" data-payload="'
    + encoded
    + '"></div><noscript>The interactive tools require JavaScript. Research data and methods remain available on the project page.</noscript></div>\n<!-- /wp:html -->'
)
(OUT / "header.html").write_text("<style>\n" + (OUT / "src/site.css").read_text() + "\n</style>")
(OUT / "template.html").write_text(
    '''<!-- wp:html -->
<header class="ar-header"><a class="ar-name" href="'''
    + BASE
    + '''">Kazi Rafsan Mahboob</a><nav aria-label="Portfolio"><a href="'''
    + BASE
    + '''">Projects</a><a href="'''
    + BASE
    + '''?page_id=4">About</a><a href="'''
    + BASE
    + '''?page_id=767">Coursework</a></nav></header>
<!-- /wp:html -->
<!-- wp:group {"tagName":"main","className":"ar-page"} -->
<main class="wp-block-group ar-page"><!-- wp:post-title {"level":1} /--><!-- wp:post-content /--></main>
<!-- /wp:group -->
<!-- wp:html -->
<footer class="ar-footer"><span>Kazi Rafsan Mahboob · Dartmouth College</span><a href="'''
    + BASE
    + """?page_id=764">Research and coursework</a></footer>
<!-- /wp:html -->"""
)
(OUT / "manifest.json").write_text(
    json.dumps(
        {
            "schema": "anchored-returns-wordpress/1",
            "canonical": BASE,
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "app_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "footer_sha256": hashlib.sha256(footer_script.encode()).hexdigest(),
            "embedded_files": len(files),
            "media_mappings": len(media),
            "source_records": len(source_rows),
            "compressed_bytes": len(encoded),
            "source_urls": sorted(set(v["source_url"] for v in source_rows if v.get("source_url"))),
        },
        indent=2,
    )
)
print(
    json.dumps(
        {
            "app_bytes": len(script.encode()),
            "data_bytes": len(raw),
            "embedded_files": len(files),
            "media": len(media),
        }
    )
)
