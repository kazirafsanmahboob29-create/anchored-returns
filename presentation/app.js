'use strict';
if(location.hash)history.scrollRestoration='manual';
const data = JSON.parse(document.getElementById('research-data').textContent);
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => String(value).replaceAll('_', ' ');
const formatDate = day => new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(new Date(day+'T00:00:00Z'));
const codeNames = {MKT:'Market evidence',PEER:'Other regulators’ awards',OWN:'Own prior awards',GRAD:'Stability & gradualism',LAW:'Legal standard',CAP:'Capital attraction',RISK:'Risk adjustment',AFF:'Customer impact',PERF:'Performance adjustment',DEF:'Agreement deference',CONC:'Conclusory'};
const stateNames = {CT:'Connecticut',MA:'Massachusetts',ME:'Maine',NH:'New Hampshire',RI:'Rhode Island',VT:'Vermont'};
const sampleLabels = {eligible_contested_roe:'Contested ROE',eligible_formula_setting:'Formula setting',
 eligible_included_by_design:'Included by design',eligible_uncontested_roe_on_record:'Uncontested ROE, decided on record',
 conditional_settled_substitute:'Conditional settled substitute',
 excluded_formula_implementation:'Mechanical formula update',excluded_no_roe_determination:'No explicit ROE determination'};
const stateLinks = {
 CT:'https://www.dpuc.state.ct.us/dockcurr.nsf/8e6fc37a54110e3e852576190052b64d/dd7c1a0c81056b1485258a16004f1d22?OpenDocument', MA:'https://www.mass.gov/info-details/rate-cases-electric-companies',
 ME:'https://mpuc-cms.maine.gov/CQM.Public.WebUI/', NH:'https://www.puc.nh.gov/VirtualFileRoom/Docket.aspx?DocketNumber=DE+19-057',
 RI:'https://ripuc.ri.gov/Docket-25-45-GE', VT:'https://epuc.vermont.gov/'
};
const sourceById = Object.fromEntries(data.sources.map(s => [s.source_id, s]));
const pdfLink = (path,page) => '../'+path.split('/').map(encodeURIComponent).join('/')+(page?'#page='+page:'');
const links = (url,path,page) => `<div class="source-links"><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Official record / publisher ↗</a><a href="${esc(pdfLink(path,page))}" target="_blank" rel="noopener noreferrer">Saved PDF${page?' · page '+page:''} ↗</a></div>`;
const caseState = row => row.state || row.case_id?.replace(/^CAND-/, '').slice(0,2) || '';
document.querySelector('a[href="#treasury-matches-panel"]').addEventListener('click',()=>{$('treasury-matches-panel').open=true;});
let view='passages', page=1, filtered=[], chartRows=[], chartMax=6;
const pageSize=12;
const initialFinding=new URL(location.href).searchParams.get('finding');
if(['request','coding','benchmark'].includes(initialFinding))$('finding-select').value=initialFinding;


$('as-of').textContent='Evidence updated '+formatDate(data.date);
$('docs-count').textContent=data.stats.documents;
$('facts-count').textContent=data.stats.facts;
$('passages-count').textContent=data.stats.passages;
$('selected-count').textContent=data.cohort?.total || data.stats.selected_orders;
$('coding-progress').textContent=data.stats.coded_orders+' complete first coding passes; expanded cohort membership fixed';
$('allocation-summary').textContent=data.cohort?data.cohort.total+' orders in the fixed document cohort: '+data.cohort.primary+' primary decisions and '+data.cohort.supplemental+' supplemental settlement. '+data.sample.screened+' candidate groupings have been screened. The cohort is bounded by these source-checked documents; the six-state census remains incomplete.':data.sample.blockers.join(' ');
$('sample-rows').innerHTML=data.sample.candidates.map(c=>`<tr><td>${esc(c.state)}</td><td>${esc(c.utility)}<br><span class="small">${esc(c.docket)}</span></td><td>${esc(c.order_date)}</td><td>${esc(sampleLabels[c.status]||label(c.status))}</td></tr>`).join('');
const currentCoverage=data.cohort_benchmarks||data.benchmarks;
$('benchmark-summary').textContent=data.benchmarks.verified_records+' strict RRA values cover '+data.benchmarks.verified_half_years.length+' half-years. '+currentCoverage.orders_with_all_services_matched+' of '+currentCoverage.proposed_orders+' cohort orders have exact all-service matches ('+currentCoverage.matched_service_rows+' of '+currentCoverage.service_rows+' service rows). '+(data.eei?'The separate EEI series adds 15 retrospective electric half-years; gas and H1 2026 remain unfilled.':'');
const benchmarkSources=Object.fromEntries(data.benchmarks.sources.map(s=>[s.source_id,s]));
$('benchmark-rows').innerHTML=data.benchmarks.records.slice().sort((a,b)=>a.period_start.localeCompare(b.period_start)||a.service.localeCompare(b.service)).map(r=>{const s=benchmarkSources[r.source_id];return `<tr><td>${esc(r.period_start.slice(0,4))} ${r.period_start.slice(5,7)==='01'?'H1':'H2'}</td><td>${esc(r.service)}</td><td>${esc(r.display_percent || r.printed_percent)}%<br><span class="small">${r.estimation_method==='case_level_reconstruction'?'Reconstructed · '+r.reconstruction.result.observations+' decisions':'Publisher reported'}</span></td><td>${esc(r.published_date)}</td><td><a href="${esc(pdfLink(s.pdf_path,r.evidence.page))}" target="_blank" rel="noopener noreferrer">Saved report ↗</a><br><a class="small" href="${esc(s.source_url)}" target="_blank" rel="noopener noreferrer">Public docket ↗</a></td></tr>`;}).join('');
$('benchmark-matches').innerHTML=currentCoverage.joins.map(j=>`<tr><td>${esc(j.candidate_id.replace('CAND-',''))}</td><td>${esc(j.service)}</td><td>${esc(j.required_period_start.slice(0,4))} ${j.required_period_start.slice(5,7)==='01'?'H1':'H2'}</td><td>${j.status==='matched'?esc(j.display_percent || j.printed_percent)+'%':'Missing comparable period'}</td></tr>`).join('');
$('reliability-summary').textContent=data.reliability.status==='packet_not_built'?'The independent coding packet has not been built.':data.reliability.units+' units from '+data.reliability.orders+' orders are ready for separate coding. Agreement remains unmeasured. One human file supports a comparison with the documented first pass; two independently completed human files support human inter-rater agreement.';
$('reliability-workspace').hidden=data.reliability.status==='packet_not_built';
for(const type of ['passages','facts','sources']) $('tab-'+type+'-count').textContent=data[type].length;
for(const [code,name] of Object.entries(codeNames)) {
 const option=document.createElement('option');option.value=code;option.textContent=code+' · '+name;$('code').append(option);
}
$('case-cards').innerHTML=data.cases.map(c => `<article class="card"><div class="card-top"><span class="eyebrow">${esc(stateNames[c.state])}</span><span class="case-date">${esc(formatDate(c.order_date))}</span></div><h3>${esc(c.utility)}</h3><div class="docket">${esc(c.docket)}</div><div class="case-award">${c.award?esc(c.award)+'<span>%</span>':'Unavailable'}</div><div class="award-label">Original authorized return on equity</div><div class="card-footer"><span class="pill">${c.coding_status==='first_pass_complete'?'First coding pass':'Numeric review only'}</span><button class="text-button case-evidence" data-case="${esc(c.case_id)}">${c.coding_status==='first_pass_complete'?'View evidence':'View numeric evidence'} ↗</button></div><details><summary>Interpretation notes</summary><p>${esc(c.notes)}</p></details></article>`).join('');
$('state-sources').innerHTML=Object.entries(stateNames).map(([state,name]) => {
 const count=data.sources.filter(s=>s.state===state).length;
 return `<article class="source-card"><div class="source-card-top"><span class="state-code">${state}</span><span class="small">${count} saved<br>document${count===1?'':'s'}</span></div><h3>${name}</h3><p>Commission records & supporting material</p><div class="source-card-links"><a href="${esc(stateLinks[state])}" target="_blank" rel="noopener noreferrer">Official docket ↗</a><button class="text-button state-evidence" data-state="${state}">Browse library →</button></div></article>`;
}).join('');

function renderPassage(p) {
 const s=sourceById[p.source_id], pages=[...new Set(p.spans.map(span=>span.page))].join(', ');
 return `<article class="record"><div class="record-top"><span class="record-title">${esc(p.case_id.replace('CAND-',''))} · viewer page ${pages}</span><span class="small">${esc(p.section)} · ${esc(p.unit_type)}</span></div><div class="tags">${Object.entries(p.stances).map(([code,stance])=>`<span class="tag ${code===p.primary_code?'primary-code':''}" title="${esc(codeNames[code])}">${code} · ${esc(stance)}${code===p.primary_code?' · primary':''}</span>`).join('')||'<span class="tag">Structural unit · no code assigned</span>'}</div><blockquote class="excerpt">${esc(p.text.replace(/(?<!\n)\n(?!\n)/g,' '))}</blockquote><details><summary>Full passage, rationale & provenance</summary><blockquote>${esc(p.text)}</blockquote><p>${esc(p.notes)}</p><p>Method: ${esc(p.method)} · Codebook ${esc(data.provenance.version)}<br>Unit: ${esc(p.passage_id)}</p><div class="mono">PDF SHA-256 ${esc(s.pdf_sha256)}</div></details>${links(s.source_url,s.pdf_path,p.spans[0].page)}</article>`;
}
function renderFact(f) {
 return `<article class="record"><div class="record-top"><span class="record-title">${esc(f.case_id.replace('CAND-',''))} · ${esc(label(f.field))}</span><span class="value">${f.relation==='at_most'?'≤ ':f.relation==='at_least'?'≥ ':''}${esc(f.value)}${f.unit==='percent'?'%':' bp'}</span></div><div class="record-meta">Event date ${esc(f.event_date)} · viewer page ${f.page}</div><details><summary>Source evidence & attribution</summary><blockquote>${esc(f.quote)}</blockquote><p>${esc(f.notes)}</p><div class="mono">PDF SHA-256 ${esc(f.pdf_sha256)}</div></details>${links(f.source_url,f.pdf_path,f.page)}</article>`;
}
function renderSource(s) {
 const chronology=s.order_date?'Written order '+formatDate(s.order_date):s.event_date?'Document event '+formatDate(s.event_date):'';
 return `<article class="record"><div class="record-top"><span class="record-title">${esc(s.title)}</span><span class="small">${s.n_pages} pages · ${esc(s.state||'Reference')}</span></div><div class="record-meta">${esc(s.docket)}${chronology?' · '+esc(chronology):''}</div><div class="tags"><span class="tag">${esc(label(s.source_kind))}</span><span class="tag">${esc(label(s.review_status))}</span></div><details><summary>Document role & preservation record</summary><p>${esc(s.role)}<br>Retrieved ${esc(s.download_date)}</p><div class="mono">PDF SHA-256 ${esc(s.pdf_sha256)}</div></details>${links(s.landing_url||s.source_url,s.pdf_path)}</article>`;
}
function render() {
 const query=$('search').value.trim().toLowerCase(),state=$('state').value,section=$('section').value,code=$('code').value;
 filtered=data[view].filter(r => (!state||caseState(r)===state) && (view!=='passages'||!section||r.section===section) && (view!=='passages'||!code||r.codes[code]===1) && (!query||JSON.stringify(r).toLowerCase().includes(query)));
 const totalPages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.min(page,totalPages);
 const start=(page-1)*pageSize,shown=filtered.slice(start,start+pageSize);
 $('count').textContent=filtered.length+' of '+data[view].length+' '+(view==='sources'?'documents':view==='facts'?'numeric facts':'coded units');
 $('records').innerHTML=shown.length?shown.map(view==='passages'?renderPassage:view==='facts'?renderFact:renderSource).join(''):'<div class="empty">No records match these filters. Reset the filters to return to the complete library.</div>';
 $('page-count').textContent=filtered.length?'Showing '+(start+1)+'–'+(start+shown.length)+' · Page '+page+' of '+totalPages:'No matching records';
 $('prev-page').disabled=page===1;$('next-page').disabled=page>=totalPages;$('download-evidence').disabled=filtered.length===0;
 saveView();
}
function setView(type) {
 view=type;page=1;
 for(const tab of document.querySelectorAll('[role=tab]')) {const selected=tab.dataset.view===view;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;}
 $('records').setAttribute('aria-labelledby','tab-'+view);
 $('section-filter').hidden=view!=='passages';$('code-filter').hidden=view!=='passages';render();
}
function resetFilters() {for(const id of ['search','state','section','code'])$(id).value='';page=1;}
function openEvidence(type,{state='',query=''}={}) {resetFilters();$('state').value=state;$('search').value=query;setView(type);$('evidence').scrollIntoView({behavior:'smooth',block:'start'});}
for(const tab of document.querySelectorAll('[role=tab]')) {
 tab.addEventListener('click',()=>setView(tab.dataset.view));
 tab.addEventListener('keydown',event=>{const tabs=[...document.querySelectorAll('[role=tab]')],index=tabs.indexOf(tab);let next;
  if(event.key==='ArrowRight')next=(index+1)%tabs.length;if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;
  if(next!==undefined){event.preventDefault();tabs[next].focus();setView(tabs[next].dataset.view);}
 });
}
for(const id of ['search','state','section','code'])$(id).addEventListener('input',()=>{page=1;render();});
$('reset-filters').addEventListener('click',()=>{resetFilters();render();});
for(const direction of ['prev','next'])$(direction+'-page').addEventListener('click',()=>{page+=direction==='next'?1:-1;render();$('tab-'+view).focus();$('evidence').scrollIntoView({behavior:'smooth',block:'start'});});
for(const button of document.querySelectorAll('.case-evidence'))button.addEventListener('click',()=>openEvidence(data.cases.find(c=>c.case_id===button.dataset.case).coding_status==='first_pass_complete'?'passages':'facts',{query:button.dataset.case}));
for(const button of document.querySelectorAll('.state-evidence'))button.addEventListener('click',()=>openEvidence('sources',{state:button.dataset.state}));
$('view-new-sources').addEventListener('click',()=>openEvidence('sources',{state:'RI',query:'25-45-GE'}));

function downloadCSV(filename,headers,rows) {
 const cell=value=>{let text=String(value??'');const numeric=/^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(text);if(/^[=+\-@\t\r]/.test(text)&&!numeric)text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
 const contents=[headers,...rows].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
 const url=URL.createObjectURL(new Blob(['\ufeff'+contents],{type:'text/csv;charset=utf-8;'}));
 const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
}
$('download-evidence').addEventListener('click',()=>{
 let headers,rows;
 if(view==='passages') {headers=['passage_id','case_id','section','unit_type','primary_code','stances','exact_text','notes','method','viewer_pages','source_url','pdf_sha256'];rows=filtered.map(p=>[p.passage_id,p.case_id,p.section,p.unit_type,p.primary_code,JSON.stringify(p.stances),p.text,p.notes,p.method,[...new Set(p.spans.map(s=>s.page))].join(';'),sourceById[p.source_id].source_url,sourceById[p.source_id].pdf_sha256]);}
 else if(view==='facts') {headers=['case_id','field','printed_value','printed_unit','relation','event_date','viewer_page','exact_quote','notes','source_url','pdf_sha256'];rows=filtered.map(f=>[f.case_id,f.field,f.value,f.unit,f.relation,f.event_date,f.page,f.quote,f.notes,f.source_url,f.pdf_sha256]);}
 else {headers=['source_id','state','docket','title','written_order_date','document_event_date','source_kind','review_status','role','download_date','pages','source_url','pdf_path','pdf_sha256'];rows=filtered.map(s=>[s.source_id,s.state,s.docket,s.title,s.order_date,s.event_date,s.source_kind,s.review_status,s.role,s.download_date,s.n_pages,s.source_url,s.pdf_path,s.pdf_sha256]);}
 downloadCSV('anchored-returns-'+view+'-'+data.date+'.csv',headers,rows);
});

function inspectChart() {
 const row=chartRows[Number($('chart-observation').value)];if(!row)return;
 $('chart-readout').textContent=formatDate(row.date)+' · '+(row.percent===''?'Missing':Number(row.percent).toFixed(2)+'%');
 $('chart-observation').setAttribute('aria-valuetext',$('chart-readout').textContent);
 const chart=$('yield-chart'),width=Number(chart.getAttribute('viewBox').split(' ')[2]),height=Number(chart.getAttribute('viewBox').split(' ')[3]);
 const first=Date.parse(chartRows[0].date),last=Date.parse(chartRows.at(-1).date),x=39+(Date.parse(row.date)-first)/(last-first)*(width-54);
 const marker=$('chart-cursor');if(marker){marker.setAttribute('x1',x);marker.setAttribute('x2',x);}
 const point=$('chart-point');if(point){point.setAttribute('cx',x);point.setAttribute('cy',row.percent===''?height-32:18+(chartMax-Number(row.percent))/chartMax*(height-50));point.setAttribute('visibility',row.percent===''?'hidden':'visible');}
}
function drawChart(range='all') {
 if(!data.treasury)return;
 const start=range==='all'?'2019-01-01':range+'-01-01';chartRows=data.treasury.series.filter(row=>row.date>=start);
 const svg=$('yield-chart'),width=Math.max(280,Math.round(svg.parentElement.clientWidth)),height=width<420?215:255;
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
 const left=39,right=15,top=18,bottom=32,plotWidth=width-left-right,plotHeight=height-top-bottom;
 const first=Date.parse(chartRows[0].date),last=Date.parse(chartRows.at(-1).date);
 chartMax=Math.max(6,Math.ceil(Math.max(...chartRows.filter(r=>r.percent!=='').map(r=>Number(r.percent)))/2)*2);
 const x=day=>left+(Date.parse(day)-first)/(last-first)*plotWidth,y=value=>top+(chartMax-value)/chartMax*plotHeight;
 let markup='<title id="chart-svg-title">Daily 10-year Treasury yields</title><desc id="chart-svg-desc">Saved FRED DGS10 observations. Missing values break the line. Use the observation slider or download the chart data for exact dates and values.</desc>';
 for(let tick=0;tick<=chartMax;tick+=2)markup+=`<line x1="${left}" y1="${y(tick)}" x2="${width-right}" y2="${y(tick)}" stroke="#e7ecee"/><text x="${left-9}" y="${y(tick)+3}" text-anchor="end" fill="#7b8790" font-size="9" font-family="system-ui">${tick}%</text>`;
 let path='',connected=false;
 for(const row of chartRows){if(row.percent===''){connected=false;continue;}path+=(connected?'L':'M')+x(row.date).toFixed(2)+','+y(Number(row.percent)).toFixed(2);connected=true;}
 markup+=`<path d="${path}" fill="none" stroke="#377b75" stroke-width="1.5" stroke-linejoin="round"/>`;
 const yearFirst=Number(chartRows[0].date.slice(0,4)),yearLast=Number(chartRows.at(-1).date.slice(0,4)),every=width<420&&yearLast-yearFirst>3?2:1;
 if(range==='2026')for(const [month,name]of [['01','Jan'],['04','Apr'],['07','Jul'],['09','Sep']]){const day='2026-'+month+'-01';if(Date.parse(day)>=first&&Date.parse(day)<=last)markup+=`<text x="${x(day)}" y="${height-9}" text-anchor="middle" fill="#7b8790" font-size="9" font-family="system-ui">${name}</text>`;}
 else for(let year=yearFirst;year<=yearLast;year+=every){const day=year===yearFirst?chartRows[0].date:year+'-01-01';if(Date.parse(day)>=first&&Date.parse(day)<=last)markup+=`<text x="${x(day)}" y="${height-9}" text-anchor="middle" fill="#7b8790" font-size="9" font-family="system-ui">${year}</text>`;}
 markup+=`<line id="chart-cursor" x1="${width-right}" x2="${width-right}" y1="${top}" y2="${height-bottom}" stroke="#a6b7bc" stroke-dasharray="3 3"/><circle id="chart-point" r="3.5" fill="#fff" stroke="#377b75" stroke-width="2"/>`;
 svg.innerHTML=markup;$('chart-observation').max=chartRows.length-1;$('chart-observation').value=chartRows.length-1;inspectChart();
}
let chartRange='all';
if(data.treasury){const t=data.treasury;
 $('latest-yield').textContent=Number(t.latest.printed_percent).toFixed(2)+'%';$('latest-date').textContent=formatDate(t.latest.date);
 $('matched-orders').textContent=t.joins.filter(j=>j.status==='matched').length+' matches';
 $('treasury-vintage').textContent='Retrieved '+formatDate(t.retrieved_at_utc.slice(0,10))+'. '+t.rows.toLocaleString()+' source rows; '+t.missing+' missing values retained. Historical observations can be revised.';
 $('treasury-matches').innerHTML=t.joins.map(j=>`<tr><td>${esc(j.case_id.replace('CAND-',''))}</td><td>${esc(j.target_date)}</td><td>${esc(j.observation_date||'Unavailable')}</td><td>${j.value_fraction===null?esc(label(j.status)):(Number(j.value_fraction)*100).toFixed(2)+'%'}</td><td>${j.gap_days===null?'Unavailable':j.gap_days+' days'}</td></tr>`).join('');
 drawChart();
}else{$('market-panel').hidden=true;$('treasury-matches-panel').hidden=true;}
for(const button of document.querySelectorAll('[data-range]'))button.addEventListener('click',()=>{chartRange=button.dataset.range;for(const other of document.querySelectorAll('[data-range]'))other.setAttribute('aria-pressed',String(other===button));drawChart(chartRange);});
$('chart-observation').addEventListener('input',inspectChart);
$('download-treasury').addEventListener('click',()=>downloadCSV('anchored-returns-dgs10-'+chartRange+'-'+data.date+'.csv',['date','printed_percent','series','retrieved_at_utc','observations_sha256'],chartRows.map(r=>[r.date,r.percent,'DGS10',data.treasury.retrieved_at_utc,data.treasury.observations_sha256])));
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>drawChart(chartRange),150);});
const navigation=[...document.querySelectorAll('.sidebar nav a')];
if('IntersectionObserver'in window){const observer=new IntersectionObserver(entries=>{const hit=entries.find(e=>e.isIntersecting);if(hit)for(const a of navigation)a.classList.toggle('active',a.hash==='#'+hit.target.id);},{rootMargin:'-10% 0px -65% 0px'});for(const id of ['research','workspace','insights','market','evidence','sources','methods'])observer.observe($(id));}
const insight=data.insights;
const pct=value=>Number(value).toFixed(Math.abs(Number(value)*100-Math.round(Number(value)*100))<1e-8?2:3);
const basis=value=>value===null?'Not available':(Number(value)>0?'+':'')+value+' bp';
const share=value=>value===null?'Unavailable':Number(value).toFixed(1)+'%';
$('insight-scope').textContent=`I compare ${insight.entered_orders} entered orders with source-checked numeric records. ${insight.request_award_pairs} have a recorded company request and award. The coding view covers ${insight.commission_units} Commission-analysis units from ${insight.coded_orders} complete first passes. The expanded cohort has ${data.cohort?.total || 0} orders; coding coverage is reported separately.`;
const outcomeValues=insight.outcomes.flatMap(r=>[r.request,r.award].filter(Boolean).map(f=>Number(f.value)));
const plotLow=outcomeValues.length?Math.floor(Math.min(...outcomeValues))-0.5:0,plotHigh=outcomeValues.length?Math.ceil(Math.max(...outcomeValues))+0.5:1;
const position=value=>16+(Number(value)-plotLow)/(plotHigh-plotLow)*268;
const factAnchor=(f,kind)=>f?`<a href="${esc(pdfLink(f.pdf_path,f.page))}" target="_blank" rel="noopener noreferrer" aria-label="${esc(kind+' '+pct(f.value)+' percent, source page '+f.page)}">${pct(f.value)}% <span class="small">p. ${f.page} ↗</span></a>`:'<span class="small">Not entered</span>';
$('outcome-rows').innerHTML=insight.outcomes.map(r=>{
 const title=`${r.utility}. Company request ${r.request?pct(r.request.value)+' percent':'not entered'}. Allowed return ${r.award?pct(r.award.value)+' percent':'not entered'}. Award minus request ${basis(r.award_minus_request_bp)}.`;
 const line=r.request&&r.award?`<line x1="${position(r.request.value)}" x2="${position(r.award.value)}" y1="19" y2="19" stroke="#a6b8b9" stroke-width="3"/>`:'';
 const markers=(r.request?`<circle cx="${position(r.request.value)}" cy="19" r="4.5" fill="#fff" stroke="#a96d44" stroke-width="2"/>`:'')+(r.award?`<circle cx="${position(r.award.value)}" cy="19" r="4.5" fill="#2e736e"/>`:'');
 return `<article class="outcome-row"><div><h4>${esc(r.utility)}</h4><p class="small">${esc(r.docket)} · ${esc(formatDate(r.order_date))}${r.award_kind==='approved_settlement'?' · Approved settlement':r.award_kind==='formula_implementation'?' · Formula implementation':''}</p><button class="text-button outcome-evidence" data-case="${esc(r.case_id)}">Inspect numeric evidence ↗</button></div><div class="outcome-values"><span>Request ${factAnchor(r.request,'Company request')}</span><span>Allowed ${factAnchor(r.award,'Allowed return')}</span><svg role="img" aria-label="${esc(title)}" viewBox="0 0 300 44"><line x1="16" x2="284" y1="19" y2="19" stroke="#e5ebed"/>${line}${markers}<text x="16" y="40" fill="#64717c" font-size="9">${plotLow.toFixed(1)}%</text><text x="284" y="40" text-anchor="end" fill="#64717c" font-size="9">${plotHigh.toFixed(1)}%</text></svg></div><div class="outcome-delta"><strong>${esc(basis(r.award_minus_request_bp))}</strong><span class="small">Award minus request</span></div></article>`;
}).join('');
for(const button of document.querySelectorAll('.outcome-evidence'))button.addEventListener('click',()=>openEvidence('facts',{query:button.dataset.case}));
function renderStances(){
 const code=$('insight-code').value,total=insight.code_totals[code];
 $('stance-summary').textContent=`${codeNames[code]} is present in ${total.present} of ${insight.commission_units} recorded Commission-analysis units: ${total.stances['Relied on']} relied on, ${total.stances.Considered} considered and ${total.stances.Rejected} rejected. These counts describe coded text, not the final sample.`;
 $('stance-rows').innerHTML=insight.coding_rows.map(r=>{
  const c=r.codes[code],parts=[['Relied on',c.stances['Relied on'],'relied-key'],['Considered',c.stances.Considered,'considered-key'],['Rejected',c.stances.Rejected,'rejected-key'],['Not present',r.commission_units-c.present,'absent-key']];
  const text=parts.map(([name,count])=>count+' '+name.toLowerCase()).join(', ');
  return `<article class="stance-row"><div><h4>${esc(r.utility)}</h4><p class="small">${r.commission_units} analysis units · ${esc(r.docket)}</p></div><div><div class="stance-bar" role="img" aria-label="${esc(r.utility+': '+text)}">${parts.filter(p=>p[1]).map(([name,count,color])=>`<span class="${color}" style="width:${count/r.commission_units*100}%" title="${esc(name+': '+count)}"></span>`).join('')}</div><p class="stance-counts">${esc(text)}</p></div><button class="text-button stance-evidence" data-case="${esc(r.case_id)}"${c.present?'':' disabled'}>Inspect ${code} evidence ↗</button></article>`;
 }).join('');
 for(const button of document.querySelectorAll('.stance-evidence'))button.addEventListener('click',()=>{resetFilters();$('search').value=button.dataset.case;$('section').value='Commission analysis';$('code').value=code;setView('passages');$('evidence').scrollIntoView({behavior:'smooth',block:'start'});});
}
$('insight-code').addEventListener('change',renderStances);
renderStances();
$('adjustment-notes').innerHTML=insight.adjustments.map(r=>`<article><span class="eyebrow">Why base and final returns stay separate</span><h3>${esc(r.utility)}: ${pct(r.base.value)}% base, ${pct(r.award.value)}% allowed</h3><p>The original order applies a ${Math.abs(Number(r.adjustment.value))}-basis-point ${Number(r.adjustment.value)<0?'reduction':'increase'}. I retain the base return, signed adjustment and operative award as separate records.</p><div class="source-links"><a href="${esc(pdfLink(r.base.pdf_path,r.base.page))}" target="_blank" rel="noopener noreferrer">Base return · p. ${r.base.page} ↗</a><a href="${esc(pdfLink(r.award.pdf_path,r.award.page))}" target="_blank" rel="noopener noreferrer">Operative award · p. ${r.award.page} ↗</a></div></article>`).join('');
const release=data.analysis;
if(release?.status==='current'){
 $('research-figures').innerHTML=release.figures.map(f=>`<figure><a href="${esc(pdfLink(f.pdf_path))}" target="_blank" rel="noopener noreferrer"><img src="${esc(pdfLink(f.image_path))}" alt="${esc(f.title+'. '+f.caption)}" loading="lazy" width="1100"></a><figcaption><strong>${esc(f.title)}</strong><p>${esc(f.caption)}</p><a class="text-link" href="${esc(pdfLink(f.pdf_path))}" target="_blank" rel="noopener noreferrer">Download PDF ↗</a></figcaption></figure>`).join('');
 const c=release.treasury_crosscheck;
 $('figure-runtime').textContent=`R and Python outputs have been executed and checked. Native Stata scripts and matching DTA files are prepared; Stata execution remains pending.${c?` The separate official Treasury feed agrees with FRED on ${c.equal.toLocaleString()} of ${c.overlapping_dates.toLocaleString()} overlapping dates; ${c.disagreements.length} disagreements are recorded.`:''}`;
 if(c?.latest_nonmissing&&data.treasury){
  const f=data.treasury.latest,t=c.latest_nonmissing;
  const paragraph=document.createElement('p');paragraph.className='small';
  paragraph.textContent=`Latest saved source observations: FRED ${pct(f.printed_percent)}% on ${formatDate(f.date)}; U.S. Treasury ${pct(t.printed_percent)}% on ${formatDate(t.date)}. These dated values remain separate from the historical order matches.`;
  $('figure-runtime').after(paragraph);
 }
}else{
 $('figure-runtime').textContent='The reproducible figure release needs rebuilding from the current evidence. The reproduction guide describes the analysis workflow.';
}
$('download-insights').addEventListener('click',()=>{
 const record={...insight,as_of:data.date,coding_provenance:data.provenance,input_sha256:data.inputs};
 const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)+'\n'],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='anchored-returns-real-records-'+data.date+'.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
});
if(data.treasury)$('fred-connection-copy').textContent=`The FRED ${data.treasury.transport==='api'?'JSON API':'public CSV'} connection supplied ${data.treasury.rows.toLocaleString()} saved source rows. The latest observation is ${formatDate(data.treasury.latest.date)}, ${pct(data.treasury.latest.printed_percent)}%. Retrieved ${data.treasury.retrieved_at_utc.replace('T',' ').split('.')[0]} UTC. Refreshes are explicit; the page reads this preserved snapshot. ${data.treasury.transport==='api'?'This snapshot used the authenticated JSON transport.':'The optional keyed JSON API has not been live-verified.'}`;
restoreView();
render();

function saveView() {
 const url=new URL(location.href);
 const values={view,state:$('state').value,q:$('search').value,section:$('section').value,code:$('code').value,page:page>1?String(page):'',range:chartRange==='all'?'':chartRange,finding:$('finding-select').value==='request'?'':$('finding-select').value};
 for(const [key,value] of Object.entries(values)) {if(value&&(key!=='view'||value!=='passages'))url.searchParams.set(key,value);else url.searchParams.delete(key);}
 history.replaceState(null,'',url);
}
function restoreView() {
 const params=new URL(location.href).searchParams;
 for(const id of ['state','section','code']) {const value=params.get(id)||'';$(id).value=[...$(id).options].some(o=>o.value===value)?value:'';}
 $('search').value=(params.get('q')||'').slice(0,500);
 const requested=params.get('view');
 view=['passages','facts','sources'].includes(requested)?requested:'passages';
 for(const tab of document.querySelectorAll('[role=tab]')) {const selected=tab.dataset.view===view;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;}
 $('records').setAttribute('aria-labelledby','tab-'+view);
 $('section-filter').hidden=view!=='passages';$('code-filter').hidden=view!=='passages';
 page=Math.max(1,Math.min(10000,Number.parseInt(params.get('page'),10)||1));
 const range=params.get('range');chartRange=['2023','2026'].includes(range)?range:'all';
 for(const button of document.querySelectorAll('[data-range]'))button.setAttribute('aria-pressed',String(button.dataset.range===chartRange));
 if(data.treasury)drawChart(chartRange);
}
window.addEventListener('popstate',()=>{restoreView();render();});
for(const button of document.querySelectorAll('[data-range]'))button.addEventListener('click',saveView);
$('copy-view-link').addEventListener('click',async()=>{
 saveView();const url=new URL(location.href);url.hash='evidence';
 try {await navigator.clipboard.writeText(url.href);$('copy-view-status').textContent='Link copied';}
 catch { $('copy-view-status').textContent='Copy the URL from the address bar'; }
});

let serviceToken=null,followingJob=null,pollTimer;
document.addEventListener('click',event=>{
 const anchor=event.target.closest('a[href]');
 if(!serviceToken||!anchor||anchor.hasAttribute('download')||anchor.textContent.trim().startsWith('Download PDF')||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
 const url=new URL(anchor.href,location.href);
 if(url.origin!==location.origin||!url.pathname.endsWith('.pdf'))return;
 const match=url.hash.match(/^#page=(\d+)$/);
 const reader=new URL('/reader',location.origin);reader.searchParams.set('file',decodeURIComponent(url.pathname.slice(1)));reader.searchParams.set('page',match?.[1]||'1');
 event.preventDefault();location.assign(reader.href);
});
const serviceButton=$('refresh-sources');
async function serviceStatus() {
 try {
  const response=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(8000)});
  if(!response.ok)throw new Error('Service unavailable');
  const status=await response.json();if(status.service!=='anchored-returns')throw new Error('Unknown service');
  serviceToken=status.csrf_token;
  $('service-badge').textContent='Local service connected';$('service-badge').classList.add('connected');
  $('download-analysis-bundle').hidden=!status.analysis_available;
  const job=status.job,busy=job?.status==='running';serviceButton.disabled=busy;
  serviceButton.textContent=busy?'Refreshing sources…':'Refresh Treasury sources';
  if(busy) {followingJob=job.id;$('service-status').textContent=job.phase+'. Existing research remains available.';pollTimer=setTimeout(serviceStatus,1200);}
  else if(job?.status==='failed') {$('service-status').textContent=job.error;followingJob=null;}
  else if(job?.status==='completed') {
   $('service-status').textContent='Source refresh completed. The observations, official comparison and figures are saved.';
   if(followingJob===job.id){followingJob=null;location.reload();}
  } else {$('service-status').textContent='Refresh downloads FRED and official Treasury observations, checks the sources and rebuilds the research figures. Each retrieval is preserved.';}
 } catch {
  serviceToken=null;serviceButton.disabled=true;$('download-analysis-bundle').hidden=true;
  $('service-badge').textContent='Saved research records';$('service-badge').classList.remove('connected');
  $('service-status').textContent='The saved evidence is available. Start the local service with ./research serve to enable source refresh and the research bundle.';
 }
}
serviceButton.addEventListener('click',async()=>{
 if(!serviceToken)return;
 serviceButton.disabled=true;$('service-status').textContent='Starting source refresh.';clearTimeout(pollTimer);
 try {
  const response=await fetch('/api/refresh',{method:'POST',headers:{'Content-Type':'application/json','X-Research-Token':serviceToken},body:'{}',signal:AbortSignal.timeout(8000)});
  if(response.status!==202&&response.status!==409)throw new Error('Refresh unavailable');
  const job=await response.json();followingJob=job.id;await serviceStatus();
 } catch {$('service-status').textContent='The refresh could not be started. The saved evidence remains available.';serviceButton.disabled=false;}
});
if(location.protocol==='http:'||location.protocol==='https:')serviceStatus();
else {$('service-status').textContent='Offline reading mode. Start ./research serve for source refresh and the research bundle.';}

// Source lineage and denominator checks use the validated payload only.
function renderFindingMap() {
 const kind=$('finding-select').value,checks=insight.sensitivity;
 const nodes=(items)=>items.map(([title,value,description],i)=>`<article class="evidence-node"><div class="eyebrow">0${i+1} / ${esc(title)}</div><strong>${esc(value)}</strong><p>${esc(description)}</p>${i===0?'<button class="text-button" id="inspect-finding-inputs">Inspect source records ↓</button>':''}</article>`).join('');
 const table=(headers,rows)=>`<div class="table-scroll"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
 let markup='',limit='',items=[];
 if(kind==='request') {
  const g=checks.request_gap,paired=insight.outcomes.filter(r=>r.award_minus_request_bp!==null);
  items=[['Source records',`${g.pairs*2} numeric entries`,'Company requests and operative awards from the same original written decisions.'],['Calculation',`${g.pairs} order pairs`,'Difference in basis points = (allowed percent − requested percent) × 100.'],['Descriptive finding',basis(g.median_bp),'Median award minus request among entered pairs.']];
  limit=`${g.below_request} awards are below the request, ${g.equal_request} equal it and ${g.above_request} exceed it. Removing one order at a time gives medians from ${basis(g.leave_one_out_low_bp)} to ${basis(g.leave_one_out_high_bp)}. This range is a sensitivity check, not a confidence interval or a final-sample estimate.`;
  markup=table(['Order / written date','Request source','Award source','Difference','Median without this order'],paired.map(r=>`<tr><td>${esc(r.docket)}<br><span class="small">${esc(r.state+' · '+r.order_date)}</span></td><td>${factAnchor(r.request,'Company request')}</td><td>${factAnchor(r.award,'Allowed return')}</td><td>${esc(basis(r.award_minus_request_bp))}</td><td>${esc(basis(g.leave_one_out.find(o=>o.omitted_case_id===r.case_id)?.median_bp??null))}</td></tr>`));
 }else if(kind==='coding') {
  const w=checks.reliance_weighting.find(r=>r.code==='MKT'),total=insight.code_totals.MKT;
  items=[['Coded text',`${w.commission_units} analysis units`,`${w.orders} complete first passes, including units without market codes.`],['Calculation',`${w.reliance_units} reliance units`,'Units with MKT present and stance recorded as Relied on.'],['Descriptive finding',`${share(w.pooled_percent)} pooled share`,`${total.orders_with_reliance} of ${w.orders} orders contain at least one reliance unit.`]];
  limit=`Giving each order equal weight produces ${share(w.equal_order_percent)}, compared with ${share(w.pooled_percent)} when each text unit has equal weight. These quantities use different denominators. First-pass labels have not been independently validated.`;
  markup=table(['Order','Analysis units','Relied on','Order share','Original passages'],insight.coding_rows.map(r=>{const ids=r.codes.MKT.unit_ids['Relied on'];return `<tr><td>${esc(r.docket)}<br><span class="small">${esc(r.state)}</span></td><td>${r.commission_units}</td><td>${ids.length}</td><td>${(ids.length/r.commission_units*100).toFixed(1)}%</td><td>${ids.map(id=>{const p=data.passages.find(u=>u.passage_id===id),s=sourceById[p.source_id];return `<a href="${esc(pdfLink(s.pdf_path,p.spans[0].page))}" target="_blank" rel="noopener noreferrer">${esc(id)} · p. ${p.spans[0].page} ↗</a>`;}).join('<br>')}</td></tr>`;}));
 }else {
  const rows=insight.benchmark_comparisons,available=rows.filter(r=>r.published_at_decision);
  const reports=new Set(rows.map(r=>r.benchmark.source_id));
  items=[['Comparable sources',`${reports.size} original reports`,'Same-service, rider-excluded means for the exact previous half-year.'],['Calculation',`${available.length} dated comparisons`,'Allowed ROE minus the national mean, only when that report was published by the written decision.'],['Coverage finding',`${data.benchmarks.orders_with_all_services_matched} / ${data.sample.proposed} proposed orders`,'Orders with exact benchmark matches for every service; numeric comparisons also require an entered award.']];
  limit='Missing half-years remain unfilled. A later publication cannot represent information available at the written decision. Annual summaries without complete case data and the enhanced 2026 dataset are held separately. Benchmark differences do not identify anchoring.';
  markup=table(['Order / service','Award source','Previous half-year mean','Difference'],rows.map(r=>{const b=r.benchmark,s=benchmarkSources[b.source_id];return `<tr><td>${esc(r.case_id.replace('CAND-',''))}<br><span class="small">${esc(r.service)}${r.award_kind==='approved_settlement'?' · approved settlement':''}</span>${r.timing_note?'<p class="small">'+esc(r.timing_note)+'</p>':''}</td><td>${factAnchor(r.award,'Allowed return')}</td><td><a href="${esc(pdfLink(s.pdf_path,b.evidence.page))}" target="_blank" rel="noopener noreferrer">${esc(b.display_percent || b.printed_percent)}% · ${esc(b.period_start.slice(0,4))} ${b.period_start.slice(5,7)==='01'?'H1':'H2'} ↗</a><br><span class="small">Published ${esc(b.published_date)}${b.estimation_method==='case_level_reconstruction'?' · reconstructed':''}</span></td><td>${esc(r.published_at_decision?basis(r.award_minus_benchmark_bp):'Withheld: published later')}</td></tr>`;}));
  if(!rows.length)markup='<p class="small">No original award and exact benchmark pair has been entered. The coverage table records available and missing periods.</p>';
 }
 $('evidence-nodes').innerHTML=nodes(items);$('finding-limit').textContent=limit;$('finding-inputs').innerHTML=markup;
 $('inspect-finding-inputs').addEventListener('click',()=>{const detail=document.querySelector('.finding-inputs');detail.open=true;detail.querySelector('summary').focus();});
}
$('finding-select').addEventListener('change',()=>{renderFindingMap();saveView();});
renderFindingMap();
const audit=data.audit;
const connectionLabels={saved_snapshot_verified:'Verified saved feed',saved_crosscheck_verified:'Verified saved comparison',saved_library_verified_census_incomplete:'Preserved orders; census incomplete',partial_public_access:'Partial public report access',not_connected:'Not connected'};
if(audit) {
 $('connection-rows').innerHTML=audit.connections.map(c=>`<tr><th scope="row">${c.source_url?`<a href="${esc(c.source_url)}" target="_blank" rel="noopener noreferrer">${esc(c.name)} ↗</a>`:esc(c.name)}</th><td>${esc(c.mode)}</td><td>${esc(connectionLabels[c.status]||label(c.status))}${c.retrieved_at_utc?'<br><span class="small">Retrieved '+esc(c.retrieved_at_utc.replace('T',' ').split('.')[0])+' UTC</span>':''}${c.comparisons!=null?'<br><span class="small">'+c.comparisons.toLocaleString()+' date comparisons; '+c.disagreements+' disagreements</span>':''}${c.documents?'<br><span class="small">'+c.documents+' saved documents</span>':''}</td></tr>`).join('');
 $('context-reports').innerHTML=audit.context_sources.map(s=>`<article class="context-report"><h4>${esc(s.title)}</h4><p>${esc(s.note)}</p>${links(s.source_url,s.pdf_path,s.page)}<details><summary>Preservation record</summary><p class="small">Retrieved ${esc(s.retrieved_at_utc)} · ${s.n_pages} saved pages</p><div class="mono">PDF SHA-256 ${esc(s.pdf_sha256)}</div></details></article>`).join('');
 $('census-count').textContent=`${data.sample.screened} reviewed groupings; ${audit.census_complete} of 6 complete state inventories`;
 $('census-records').innerHTML=audit.census.map(c=>`<details class="census-state"><summary>${esc(stateNames[c.state])}<span class="small">${c.screened} screened · ${c.eligible} eligible · ${c.excluded} excluded · ${c.conditional} conditional · ${c.complete?'Inventory complete':'Inventory incomplete'}</span></summary>${c.records.map(r=>`<article class="census-record"><strong>${esc(r.docket)} · ${esc(r.order_date)} · ${esc(sampleLabels[r.status]||label(r.status))}</strong><p>${esc(r.reason)}</p><div class="source-links">${r.evidence.map(e=>`<a href="${esc(pdfLink(e.pdf_path,e.page))}" target="_blank" rel="noopener noreferrer">${esc(e.purpose)} · p. ${e.page} ↗</a>`).join('')}</div></article>`).join('')}${c.leads.length?'<h4>Open leads</h4><ul>'+c.leads.map(l=>`<li><a href="${esc(l.source_url)}" target="_blank" rel="noopener noreferrer">${esc(l.docket)} ↗</a>: ${esc(l.reason)}</li>`).join('')+'</ul>':'<p class="small">No individual open lead is listed. An incomplete inventory remains unresolved.</p>'}</details>`).join('');
}

// Resolve initial deep links after the data-driven sections have their final height.
window.addEventListener('load',()=>{
 const anchors=new Set(['research','workspace','insights','market','evidence','sources','methods','finding-map','treasury-matches-panel','top']);
 const id=location.hash.slice(1),target=anchors.has(id)?$(id):null;
 if(target)target.scrollIntoView({behavior:'instant',block:'start'});
},{once:true});
