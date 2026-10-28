import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectRegional,stateSummary} from '../../presentation/national/regional.mjs';
import {evaluate,defaults} from '../../presentation/national/analysis.mjs';
const r=JSON.parse(readFileSync(new URL('../../reports/national-study/regional.json',import.meta.url)));
const national=JSON.parse(readFileSync(new URL('../../reports/national-study/study.json',import.meta.url)));
test('regional browser summaries reproduce the Python results',()=>{
 assert.deepEqual(stateSummary(selectRegional(r.records)),r.primary);
 assert.deepEqual(stateSummary(selectRegional(r.records,{settlements:true,formulas:true})),r.all);
});
test('formula and settlement inclusion are independent and missing awards remain missing',()=>{
 assert.equal(selectRegional(r.records).length,22);
 assert.equal(selectRegional(r.records,{settlements:true}).length,23);
 assert.equal(selectRegional(r.records,{formulas:true}).length,26);
 assert.equal(selectRegional(r.records,{settlements:true,formulas:true}).length,27);
 assert.equal(selectRegional(r.records,{state:'RI'}).length,0);
 assert.equal(selectRegional(r.records,{state:'RI',settlements:true}).length,1);
 assert.equal(selectRegional(r.records,{service:'Gas',formulas:true}).filter(r=>r.case_id==='CAND-VT-24-2137')[0].award_bp,null);
});
test('New England geography filter agrees with the Python region result',()=>{
 const result=evaluate(national.records,{...defaults,state:'@NE'});
 assert.equal(result.comparison.earlier_n,7);assert.equal(result.comparison.later_n,7);
 assert.ok(Math.abs(result.comparison.award_change_bp-national.regional.recent.award_change_bp)<1e-9);
 const state=evaluate(national.records,{...defaults,state:'@NE',weight:'state'});
 assert.equal(state.comparison.common_groups,3);
 const a=evaluate(national.records,{...defaults,state:'@other'});
 assert.equal(a.comparison.earlier_n+result.comparison.earlier_n,77);
});
