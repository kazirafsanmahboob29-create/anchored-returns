import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {basisPoints,cohortRows,filterRows,summary,validateSelection,exportCsv} from '../../presentation/workspace/analysis.mjs';
const html=readFileSync(new URL('../../presentation/index.html',import.meta.url),'utf8');
const data=JSON.parse(html.match(/<script id="research-data" type="application\/json">(.*?)<\/script>/s)[1]);
test('preserved settlement precision and exact whole-basis-point arithmetic',()=>{
  assert.equal(basisPoints('9.275'),927.5);
  assert.equal(basisPoints('9.99')-basisPoints('10.20'),-21);
  assert.throws(()=>basisPoints('9.12345'));
});
test('real expanded cohort keeps all documents and explicit missing awards',()=>{
  const rows=cohortRows(data),primary=filterRows(rows),all=filterRows(rows,{stratum:'all'});
  assert.equal(rows.length,27);assert.equal(primary.length,22);
  assert.equal(summary(primary).award_observations,19);
  assert.equal(summary(primary).missing_awards,3);
  assert.equal(summary(all).award_observations,22);
  assert.equal(rows.find(r=>r.candidate_id==='CAND-RI-4770-4780').awardBp,927.5);
  assert.equal(rows.find(r=>r.candidate_id==='SUPP-VT-22-5085-ORDER').awardBp,null);
});
test('joint services do not duplicate documents when filtering',()=>{
  const rows=cohortRows(data),gas=filterRows(rows,{service:'Gas'});
  assert.equal(new Set(gas.map(r=>r.candidate_id)).size,gas.length);
  assert.equal(gas.filter(r=>r.candidate_id==='CAND-MA-23-80-81').length,1);
  assert.equal(filterRows(rows,{query:'fitchburg'}).length,1);
  assert.equal(filterRows(rows,{state:'RI'}).length,0);
  assert.equal(filterRows(rows,{state:'RI',stratum:'all'}).length,1);
});
test('proceeding weighting changes award denominator without treating missing as zero',()=>{
  const row=(id,g,a)=>({candidate_id:id,proceeding_group:g,awardBp:a,requestBp:null,coded:false,benchmarks:[]});
  const rows=[row('TEST-A','G1',900),row('TEST-B','G1',900),row('TEST-C','G2',1000),row('TEST-D','G3',null)];
  assert.equal(summary(rows).median_award_percent,9);
  assert.equal(summary(rows,'proceeding').median_award_percent,9.5);
  assert.equal(summary(rows,'proceeding').weighted_observations,2);
  assert.equal(summary(rows).missing_awards,1);
  assert.equal(summary([]).median_award_percent,null);
  assert.equal(summary([]).median_award_minus_request_bp,null);
});
test('saved selections reject changed releases, unknown IDs and duplicate IDs',()=>{
  const valid={schema:'anchored-returns-workspace/1',cohort_sha256:data.cohort.manifest_sha256,selected_ids:[],weighting:'order'};
  assert.deepEqual(validateSelection(valid,data),valid);
  assert.throws(()=>validateSelection({...valid,cohort_sha256:'changed'},data));
  assert.throws(()=>validateSelection({...valid,selected_ids:['invented']},data));
  const id=data.cohort.members[0].candidate_id;
  assert.throws(()=>validateSelection({...valid,selected_ids:[id,id]},data));
});
test('CSV preserves nulls and protects spreadsheet text cells',()=>{
  const rows=cohortRows(data).slice(0,1);rows[0]={...rows[0],utility:'=1+1'};
  const csv=exportCsv(rows);
  assert.ok(csv.includes("'=1+1"));assert.ok(!csv.includes('undefined'));
  assert.equal(csv.split('\r\n').filter(Boolean).length,2);
});

test('EEI series remains retrospective and never supplies gas or future half-year values',()=>{
  const rows=cohortRows(data),s=summary(rows,'order','eei');
  assert.ok(s.retrospective_comparisons>0);assert.equal(s.contemporaneous_comparisons,0);
  assert.ok(rows.flatMap(r=>r.eei_benchmarks).filter(j=>j.service==='Gas').every(j=>j.status==='missing_EEI_context'));
  assert.ok(rows.find(r=>r.candidate_id==='CAND-VT-26-0096').eei_benchmarks.every(j=>j.status==='missing_EEI_context'));
  assert.equal(summary(rows.filter(r=>r.candidate_id==='CAND-MA-23-80-81'),'order','eei').retrospective_comparisons,1);
});
