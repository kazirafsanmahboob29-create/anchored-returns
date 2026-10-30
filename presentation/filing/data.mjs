// Small, dependency-free calculations shared by the explorer and its tests.
export function selectCases(cases, {start=1980, end=2024, region='all', query=''}={}) {
  if (!Number.isInteger(start) || !Number.isInteger(end) || start>end || start<1980 || end>2024) throw new Error('Choose a valid period within 1980-2024.');
  if (!['all','Northeast','Midwest','South','West'].includes(region)) throw new Error('Unknown region.');
  const text=query.trim().toLocaleLowerCase();
  return cases.filter(r=>r.year>=start && r.year<=end && (region==='all' || r.region===region) && (!text || `${r.utility} ${r.state} ${r.docket}`.toLocaleLowerCase().includes(text)));
}

export function describe(cases) {
  if (!cases.length) return {n:0,meanRequest:null,meanAward:null,meanGap:null,medianGap:null,below:0};
  const gaps=cases.map(r=>r.award_bp-r.request_bp).sort((a,b)=>a-b);
  const total=key=>cases.reduce((s,r)=>s+r[key],0)/cases.length;
  const mid=Math.floor(gaps.length/2);
  return {n:cases.length,meanRequest:total('request_bp')/100,meanAward:total('award_bp')/100,
    meanGap:gaps.reduce((s,x)=>s+x,0)/gaps.length,
    medianGap:gaps.length%2 ? gaps[mid] : (gaps[mid-1]+gaps[mid])/2,
    below:gaps.filter(x=>x<0).length};
}

export function annual(cases) {
  const groups=new Map();
  for (const row of cases) {
    if (!groups.has(row.year)) groups.set(row.year,[]);
    groups.get(row.year).push(row);
  }
  return [...groups].sort(([a],[b])=>a-b).map(([year,rows])=>({year,...describe(rows)}));
}

export function exportCsv(cases) {
  const fields=['id','authorized_date','requested_date','state','utility','docket','request_bp','award_bp','known_prior_date','known_prior','source_row'];
  const cell=value=>{
    if(value==null) return '';
    let text=String(value);
    if(typeof value==='string' && /^[=+\-@\t\r]/.test(text)) text="'"+text;
    return /[",\r\n]/.test(text) ? '"'+text.replaceAll('"','""')+'"' : text;
  };
  return fields.join(',')+'\r\n'+cases.map(r=>fields.map(key=>cell(r[key])).join(',')).join('\r\n')+'\r\n';
}
