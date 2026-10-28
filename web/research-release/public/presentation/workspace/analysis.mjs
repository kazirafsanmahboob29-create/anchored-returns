// Pure calculations shared by the browser workspace and its tests.
const awardFields = new Set(['awarded_roe','awarded_roe_as_issued','commission_awarded_roe','awarded_roe_after_performance_reductions','approved_settlement_roe','formula_implemented_roe']);
export function basisPoints(value) {
  if (!/^\d{1,2}(\.\d{1,4})?$/.test(String(value))) throw Error('Invalid ROE precision');
  const [whole,fraction='']=String(value).split('.');
  return Number(whole)*100+Number(fraction.padEnd(4,'0'))/100;
}
function fact(facts,id,date,fields) {
  const matches=facts.filter(f=>f.case_id===id && f.event_date===date && f.relation==='equal' && f.unit==='percent' && fields.has(f.field));
  if(new Set(matches.map(f=>basisPoints(f.value))).size>1)throw Error('Conflicting original values: '+id);
  return matches[0]||null;
}
export function cohortRows(data) {
  const cases=new Map(data.cases.map(c=>[c.case_id,c]));
  const sources=new Map(data.sources.map(s=>[s.source_id,s]));
  return data.cohort.members.map(c=>{
    const award=fact(data.facts,c.candidate_id,c.order_date,awardFields);
    const request=fact(data.facts,c.candidate_id,c.order_date,new Set(['company_requested_roe']));
    return {...c, award, request, coded:cases.get(c.candidate_id)?.coding_status==='first_pass_complete',
      awardBp:award?basisPoints(award.value):null, requestBp:request?basisPoints(request.value):null,
      source:sources.get(c.source_ids[0]),
      eei_benchmarks:(data.eei?.joins||[]).filter(j=>j.candidate_id===c.candidate_id),
      eei_source:data.eei?.sources[0]||null,
      benchmarks:data.cohort_benchmarks.joins.filter(j=>j.candidate_id===c.candidate_id)};
  });
}
export function filterRows(rows,{state='',service='',period='',stratum='primary',query=''}={}) {
  return rows.filter(r=>(!state || r.state===state) && (!service || r.services.includes(service)) &&
    (!period || (period==='early'?r.order_date<'2022-01-01':period==='later'?r.order_date>='2023-01-01':r.order_date>='2022-01-01' && r.order_date<'2023-01-01')) &&
    (stratum==='all' || r.stratum===stratum) &&
    (!query || (r.utility+' '+r.docket+' '+r.candidate_id).toLowerCase().includes(query.toLowerCase())));
}
export function median(values) {
  if(!values.length)return null;
  const a=[...values].sort((a,b)=>a-b), n=a.length;
  return n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2;
}
export function comparisonRows(row,mode='rra') {
  if(!['rra','eei'].includes(mode))throw Error('Unknown national series');
  return mode==='rra'?row.benchmarks:row.eei_benchmarks||[];
}
export function matchedBenchmark(join,mode='rra') {
  return join.status===(mode==='rra'?'matched':'matched_retrospective_context');
}
export function summary(rows,weighting='order',comparison='rra') {
  if(!['order','proceeding'].includes(weighting))throw Error('Unknown weighting');
  const observed=rows.filter(r=>r.awardBp!==null), groups=new Map();
  for(const r of observed){const key=weighting==='order'?r.candidate_id:r.proceeding_group;groups.set(key,[...(groups.get(key)||[]),r.awardBp]);}
  const values=[...groups.values()].map(a=>a.reduce((x,y)=>x+y,0)/a.length);
  const pairs=rows.filter(r=>r.awardBp!==null && r.requestBp!==null);
  const gaps=pairs.map(r=>r.awardBp-r.requestBp);
  const benchmarkRows=rows.flatMap(r=>comparisonRows(r,comparison).map(j=>({row:r,join:j})));
  const comparable=benchmarkRows.filter(x=>matchedBenchmark(x.join,comparison));
  const dated=comparable.filter(x=>(comparison==='eei'||x.join.available_at_written_date===true) && x.row.awardBp!==null);
  return {orders:rows.length,proceedings:new Set(rows.map(r=>r.proceeding_group)).size,
    award_observations:observed.length, missing_awards:rows.length-observed.length,
    weighted_observations:values.length, weighting,
    median_award_percent:values.length?median(values)/100:null,
    mean_award_percent:values.length?values.reduce((x,y)=>x+y,0)/values.length/100:null,
    min_award_percent:values.length?Math.min(...values)/100:null,max_award_percent:values.length?Math.max(...values)/100:null,
    request_award_pairs:pairs.length,median_award_minus_request_bp:median(gaps),
    below_request:gaps.filter(x=>x<0).length, missing_requests:rows.length-rows.filter(r=>r.requestBp!==null).length,
    coded_orders:rows.filter(r=>r.coded).length,benchmark_service_rows:benchmarkRows.length,
    matched_benchmark_service_rows:comparable.length,missing_benchmark_service_rows:benchmarkRows.length-comparable.length,
    comparison_source:comparison,comparison_timing:comparison==='eei'?'retrospective':'published_by_written_date',
    contemporaneous_comparisons:comparison==='rra'?dated.length:0,
    retrospective_comparisons:comparison==='eei'?dated.length:0,
    median_award_minus_benchmark_bp:median(dated.map(x=>x.row.awardBp-basisPoints(x.join.display_percent||x.join.printed_percent))),
    note:'Award summaries use the selected weighting. Request gaps and national comparisons use observed pairs. Benchmark pairs are service rows; joint-service orders can supply two pairs. Differences use the displayed two-decimal national mean. Missing values are excluded from calculations and counted explicitly.'};
}
export function validateSelection(value,data) {
  if(!value || value.schema!=='anchored-returns-workspace/1' || value.cohort_sha256!==data.cohort.manifest_sha256)throw Error('This file does not match the current cohort release.');
  if(!Array.isArray(value.selected_ids) || value.selected_ids.length>data.cohort.total || new Set(value.selected_ids).size!==value.selected_ids.length)throw Error('Invalid selection list.');
  const valid=new Set(data.cohort.members.map(r=>r.candidate_id));
  if(value.selected_ids.some(id=>!valid.has(id)))throw Error('The selection includes an unknown order.');
  if(!['order','proceeding'].includes(value.weighting))throw Error('Invalid weighting.');
  if(value.comparison_source && !['rra','eei'].includes(value.comparison_source))throw Error('Invalid national series.');
  return value;
}
function cell(value) {
  if(value===null || value===undefined)return '';
  let text=String(value);
  if(typeof value!=='number' && /^[=+\-@\t\r]/.test(text))text="'"+text;
  return '"'+text.replaceAll('"','""')+'"';
}
export function exportCsv(rows,comparison='rra') {
  const fields=['candidate_id','state','utility','docket','written_date','stratum','proceeding_group','services','award_percent','request_percent','award_minus_request_bp','coding_complete','benchmark_services_matched','benchmark_services_required','award_source_url','award_pdf_sha256','award_pdf_page','comparison_source','comparison_timing','national_benchmarks_percent','award_minus_national_mean_bp'];
  const records=rows.map(r=>{const joins=comparisonRows(r,comparison),matched=joins.filter(j=>matchedBenchmark(j,comparison));return [r.candidate_id,r.state,r.utility,r.docket,r.order_date,r.stratum,r.proceeding_group,r.services.join(';'),r.awardBp===null?null:r.awardBp/100,r.requestBp===null?null:r.requestBp/100,r.awardBp===null||r.requestBp===null?null:r.awardBp-r.requestBp,r.coded?1:0,matched.length,joins.length,r.award?.source_url,r.award?.pdf_sha256,r.award?.page,comparison,comparison==='eei'?'retrospective':'published_by_written_date',matched.map(j=>j.service+':'+j.display_percent).join(';'),matched.filter(j=>r.awardBp!==null && (comparison==='eei'||j.available_at_written_date===true)).map(j=>j.service+':'+(r.awardBp-basisPoints(j.display_percent||j.printed_percent))).join(';')];});
  return [fields,...records].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
}
