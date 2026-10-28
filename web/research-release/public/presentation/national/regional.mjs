// Regional summaries use original-order facts, separate from the EEI table.
export const states=['CT','MA','ME','NH','RI','VT'];
const median=a=>{if(!a.length)return null;const s=[...a].sort((a,b)=>a-b),n=s.length;return n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;};
export function selectRegional(rows,{service='',settlements=false,formulas=false,state=''}={}){
  return rows.filter(r=>(!service||r.services.includes(service))&&(r.stratum==='primary'||settlements&&r.stratum==='settlement'||formulas&&r.stratum==='formula')&&(!state||r.state===state));
}
export function stateSummary(rows){return states.map(state=>{const r=rows.filter(r=>r.state===state),a=r.filter(r=>r.award_bp!==null).map(r=>r.award_bp);return {state,orders:r.length,awards:a.length,missing:r.length-a.length,proceedings:new Set(r.map(r=>r.proceeding_group)).size,median_bp:median(a),mean_bp:a.length?a.reduce((x,y)=>x+y,0)/a.length:null,min_bp:a.length?Math.min(...a):null,max_bp:a.length?Math.max(...a):null,early:r.filter(r=>r.order_date<'2022-01-01').length,later:r.filter(r=>r.order_date>='2023-01-01').length};});}
const pct=v=>v===null?'Unavailable':(v/100).toFixed(3).replace(/0$/,'')+'%';
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
function download(text,name,type){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
if(typeof document!=='undefined'&&document.getElementById('regional-data')){
 const data=JSON.parse(document.getElementById('regional-data').textContent),get=id=>document.getElementById(id);
 function render(){
  const selection={service:get('regional-service').value,state:get('regional-state').value,settlements:get('regional-settlements').checked,formulas:get('regional-formulas').checked};
  const rows=selectRegional(data.records,selection),observed=rows.filter(r=>r.award_bp!==null),summary=stateSummary(rows);
  get('regional-summary').innerHTML=summary.filter(r=>!selection.state||r.state===selection.state).map(r=>`<tr><td>${r.state}</td><td>${r.orders}</td><td>${r.awards}</td><td>${r.missing}</td><td>${r.proceedings}</td><td>${pct(r.median_bp)}</td><td>${r.awards?pct(r.min_bp)+' to '+pct(r.max_bp):'Unavailable'}</td></tr>`).join('');
  get('regional-status').textContent=`${rows.length} documents, ${observed.length} entered awards, ${rows.length-observed.length} missing awards. Settlements ${selection.settlements?'included':'excluded'}; formula implementations ${selection.formulas?'included':'excluded'}. State summaries combine different years and utilities.`;
  // Each dot is an original recorded award. Position has one common percent scale.
  const low=800,high=1100,w=680,left=180,right=40,h=60+observed.length*26,x=v=>left+(v-low)/(high-low)*(w-left-right);
  const ordered=[...observed].sort((a,b)=>a.state.localeCompare(b.state)||a.order_date.localeCompare(b.order_date));
  get('regional-plot').innerHTML=observed.length?`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Recorded allowed returns by state, date and docket. Each mark is an original order.">${[800,850,900,950,1000,1050,1100].map(v=>`<line x1="${x(v)}" x2="${x(v)}" y1="22" y2="${h-18}" stroke="#e6e9ec"/><text x="${x(v)}" y="13" text-anchor="middle" fill="#667681" font-size="11">${(v/100).toFixed(1)}%</text>`).join('')}${ordered.map((r,i)=>{const y=40+i*26;return `<text x="0" y="${y+4}" font-size="11" fill="#53636f">${escape(r.state+' '+r.order_date+' · '+r.docket.replace(/^(DE|DG) /,''))}</text>${r.stratum==='formula'?`<rect x="${x(r.award_bp)-4}" y="${y-4}" width="8" height="8" fill="#7d929f"><title>${escape(r.utility)}: ${pct(r.award_bp)} (formula)</title></rect>`:`<circle cx="${x(r.award_bp)}" cy="${y}" r="${r.stratum==='settlement'?4:4.5}" fill="${r.stratum==='settlement'?'white':'#345e78'}" stroke="#345e78"><title>${escape(r.utility)}: ${pct(r.award_bp)}${r.stratum==='settlement'?' (settlement)':''}</title></circle>`}<text x="${x(r.award_bp)+9}" y="${y+4}" font-size="10" fill="#345e78">${pct(r.award_bp)}</text>`}).join('')}</svg>`:'<p class="note">No entered awards for this selection.</p>';
  get('regional-records').innerHTML=rows.map(r=>`<tr><td>${escape(r.state)}<small>${escape(r.order_date)}</small></td><td>${escape(r.utility)}<small>${escape(r.docket)} · ${r.services.join(' / ')}${r.stratum==='settlement'?' · settlement':r.stratum==='formula'?' · formula':''}</small></td><td>${pct(r.award_bp)}</td><td>${r.award_page?`<a href="/reader?file=${encodeURIComponent(r.pdf_path)}&amp;page=${r.award_page}">PDF p. ${r.award_page}</a>`:'No award entered'}</td></tr>`).join('');
  get('regional-export').onclick=()=>download(JSON.stringify({schema:data.schema,cohort_sha256:data.manifest_sha256,selection,summary,records:rows,note:data.note},null,2),'regional-selection.json','application/json');
  const url=new URL(location.href);url.hash='regional';for(const [k,v] of Object.entries(selection))url.searchParams.set('region_'+k,String(v));
  get('regional-share').onclick=async()=>{try{await navigator.clipboard.writeText(url.href);get('regional-status').textContent='Selection link copied.';}catch{get('regional-status').textContent='The browser could not copy this link.';}};
 }
 const params=new URL(location.href).searchParams;
 if(['','Electric','Gas'].includes(params.get('region_service')))get('regional-service').value=params.get('region_service');
 if(['',...states].includes(params.get('region_state')))get('regional-state').value=params.get('region_state');
 get('regional-settlements').checked=params.get('region_settlements')==='true';
 get('regional-formulas').checked=params.get('region_formulas')==='true';
 for(const id of ['regional-service','regional-state','regional-settlements','regional-formulas'])get(id).addEventListener('change',render);
 render();
}
