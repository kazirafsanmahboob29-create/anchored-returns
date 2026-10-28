import {defaults,validate,evaluate,csv} from './analysis.mjs';
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const bp=n=>n===null?'Unavailable':(n>0?'+':'')+n.toFixed(1)+' bp',pct=n=>n===null?'Unavailable':(n/100).toFixed(2)+'%';
let data,result,selection={...defaults},page=0;
function status(s){$('tool-status').textContent=s;}
function read(){return Object.fromEntries(Object.keys(defaults).map(k=>[k,['a0','a1','b0','b1'].includes(k)?Number($('study-'+k).value):$('study-'+k).value]));}
function drawChange(c){
  const entries=[['Allowed ROE',c.award_change_bp,'#376b8b'],['10-year Treasury',c.treasury_change_bp,'#7d929f']];
  if(entries.some(e=>e[1]===null)){ $('change-plot').innerHTML='<p>No matched observations in both periods. Broaden the filters.</p>';return;}
  const min=Math.min(0,...entries.map(e=>e[1])),max=Math.max(0,...entries.map(e=>e[1])),lo=min<0?Math.floor(min/50)*50:0,hi=max>0?Math.ceil(max/50)*50:50;
  if(window.matchMedia('(max-width:580px)').matches){
    const x=v=>15+(v-lo)/(hi-lo||50)*300,zero=x(0);
    $('change-plot').innerHTML=`<svg viewBox="0 0 430 195" role="img" aria-label="Change in mean allowed ROE ${esc(bp(c.award_change_bp))}; change in matched Treasury yield ${esc(bp(c.treasury_change_bp))}">${entries.map(([label,v,color],i)=>`<text x="15" y="${18+i*82}" fill="#334b5a" font-size="15">${label}</text><line x1="${zero}" x2="${zero}" y1="${29+i*82}" y2="${62+i*82}" stroke="#aebbc5"/><rect x="${Math.min(zero,x(v))}" y="${33+i*82}" width="${Math.max(1,Math.abs(x(v)-zero))}" height="25" rx="1" fill="${color}"/><text x="${Math.max(zero,x(v))+9}" y="${51+i*82}" fill="#243a49" font-size="14">${esc(bp(v))}</text>`).join('')}<text x="15" y="186" fill="#667987" font-size="12">Change in basis points, on the same matched observations.</text></svg>`;return;
  }
  const x=v=>160+(v-lo)/(hi-lo||50)*410,zero=x(0);
  $('change-plot').innerHTML=`<svg viewBox="0 0 720 185" role="img" aria-label="Change in mean allowed ROE ${esc(bp(c.award_change_bp))}; change in matched Treasury yield ${esc(bp(c.treasury_change_bp))}"><line x1="${zero}" x2="${zero}" y1="15" y2="130" stroke="#aebbc5"/>${entries.map(([label,v,color],i)=>`<text x="0" y="${48+i*62}" fill="#334b5a" font-size="14">${label}</text><rect x="${Math.min(zero,x(v))}" y="${28+i*62}" width="${Math.max(1,Math.abs(x(v)-zero))}" height="27" rx="1" fill="${color}"/><text x="${Math.max(zero,x(v))+10}" y="${47+i*62}" fill="#243a49" font-size="14">${esc(bp(v))}</text>`).join('')}<text x="160" y="163" fill="#667987" font-size="12">Changes in basis points. Both series use the same matched authorizations.</text></svg>`;
}
function table(){
  const rows=result.records,start=page*10;
  $('study-rows').innerHTML=rows.slice(start,start+10).map(r=>`<tr><td>${esc(r.authorized_date)}</td><td>${esc(r.utility)}<small>${esc(r.state)} · ${esc(r.docket)}</small></td><td>${pct(r.award_bp)}</td><td>${r.award_bp===null||r.request_bp===null?'Unavailable':bp(r.award_bp-r.request_bp)}</td><td>${pct(r.treasury_bp)}<small>${esc(r.treasury_date||'No date match')}</small></td><td><a href="../data/external/eei/eei_rate_review_2025_q3.xlsx" download aria-label="Download EEI source workbook for row ${r.source_row}">Row ${r.source_row} ↗</a></td></tr>`).join('')||'<tr><td colspan="6">No source observations match these periods and filters.</td></tr>';
  $('study-page').textContent=rows.length?`${start+1} to ${Math.min(start+10,rows.length)} of ${rows.length} completed observations`:'No observations';
  $('study-prev').disabled=page===0;$('study-next').disabled=start+10>=rows.length;
}
function render(){
  try{selection=read();result=evaluate(data.records,selection);page=0;const {earlier:a,later:b,comparison:c}=result;
    $('comparison-values').innerHTML=`<table><thead><tr><th>Observed measure</th><th>${selection.a0}–${selection.a1}</th><th>${selection.b0}–${selection.b1}</th></tr></thead><tbody>${[['Completed observations',a.cases,b.cases],['Reported awards',a.awards,b.awards],['Mean recorded award',pct(a.mean_award_bp),pct(b.mean_award_bp)],['Recorded request-award pairs',a.pairs,b.pairs],['Median award minus request',bp(a.median_gap_bp),bp(b.median_gap_bp)],['Entries without reported ROE',a.missing_awards,b.missing_awards]].map(r=>'<tr>'+r.map((v,i)=>`<${i?'td':'th'}>${esc(v)}</${i?'td':'th'}>`).join('')+'</tr>').join('')}</tbody></table>`;
    drawChange(c);
    $('comparison-note').textContent=(selection.weight==='case'?`${c.earlier_n} earlier and ${c.later_n} later authorizations have both an award and a Treasury match. Each authorization has equal weight.`:`${c.common_groups} ${c.common_groups===1?'group occurs':'groups occur'} in both periods, containing ${c.earlier_n} earlier and ${c.later_n} later matched authorizations. Each common group has equal weight.`)+' The table reports all filtered observations; the chart uses these matched observations. '+(selection.b1===2025?'2025 includes only observations through September 30. ':'')+'This is a descriptive period comparison.';
    $('study-export').disabled=!result.records.length;$('study-report').disabled=!result.records.length;$('study-share').disabled=false;table();status('Comparison recalculated from the preserved source records.');
  }catch(error){result=null;status(error.message);$('comparison-values').replaceChildren();$('change-plot').textContent='Choose two valid, separate periods.';$('comparison-note').textContent='';$('study-rows').replaceChildren();$('study-page').textContent='No valid comparison';$('study-prev').disabled=true;$('study-next').disabled=true;$('study-export').disabled=true;$('study-report').disabled=true;$('study-share').disabled=true;}
}
function download(raw,name,type){const url=URL.createObjectURL(new Blob([raw],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status(name+' exported.');}
async function init(){
  try{const response=await fetch('../reports/national-study/study.json');if(!response.ok)throw Error('Source data could not be loaded. Download the study tables below.');data=await response.json();if(data.schema!=='anchored-returns-national/1')throw Error('The data release is not supported.');
    for(const k of ['a0','a1','b0','b1'])$('study-'+k).innerHTML=Array.from({length:16},(_,i)=>2010+i).map(y=>`<option value="${y}">${y===2025?y+' (through Q3)':y}</option>`).join('');
    $('study-state').innerHTML='<option value="">All jurisdictions</option><option value="@NE">New England (six states)</option><option value="@other">Outside New England</option>'+[...new Set(data.records.map(r=>r.state))].sort().map(s=>`<option>${esc(s)}</option>`).join('');
    const q=new URL(location.href).searchParams;for(const k of Object.keys(defaults))if(q.has(k))selection[k]=['a0','a1','b0','b1'].includes(k)?Number(q.get(k)):q.get(k);
    try{validate(selection);if(selection.state&&!['@NE','@other'].includes(selection.state)&&!data.records.some(r=>r.state===selection.state))throw Error();}catch{selection={...defaults};}
    for(const k of Object.keys(defaults)){$('study-'+k).value=selection[k];$('study-'+k).addEventListener('change',render);}
    $('study-reset').addEventListener('click',()=>{for(const k of Object.keys(defaults))$('study-'+k).value=defaults[k];render();});
    $('study-prev').addEventListener('click',()=>{page--;table();});$('study-next').addEventListener('click',()=>{page++;table();});
    $('study-export').addEventListener('click',()=>download(csv(result.records),'utility-roe-selection.csv','text/csv;charset=utf-8'));
    $('study-report').addEventListener('click',()=>download(JSON.stringify({schema:'anchored-returns-period-comparison/1',selection,input_sha256:data.input_sha256,source:data.source,summary:{earlier:result.earlier,later:result.later,comparison:result.comparison},records:result.records,limitations:data.limitations},null,2)+'\n','utility-roe-comparison.json','application/json'));
    $('study-share').addEventListener('click',async()=>{const url=new URL(location.href);for(const [k,v]of Object.entries(selection))url.searchParams.set(k,v);url.hash='compare';try{await navigator.clipboard.writeText(url.href);status('Comparison link copied. Current Site access permissions apply.');}catch{status('Copy this link: '+url.href);}});
    window.addEventListener('resize',()=>{if(result)drawChange(result.comparison);});
    $('study-controls').disabled=false;render();
  }catch(error){status(error.message);}
}
init();
