import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {defaults,evaluate,validate,csv} from '../../presentation/national/analysis.mjs';
const data=JSON.parse(readFileSync(new URL('../../reports/national-study/study.json',import.meta.url),'utf8'));
test('browser calculations reproduce Python for every headline weighting',()=>{
 for(const expected of data.comparisons){const r=evaluate(data.records,{...defaults,weight:expected.weighting});for(const k of ['earlier_n','later_n','common_groups'])assert.equal(r.comparison[k],expected[k]);for(const k of ['award_change_bp','treasury_change_bp'])assert.ok(Math.abs(r.comparison[k]-expected[k])<1e-9);}
});
test('missing measurements remain counted and out of paired arithmetic',()=>{
 const r=evaluate(data.records,defaults);assert.equal(r.earlier.cases,101);assert.equal(r.earlier.awards,77);assert.equal(r.earlier.pairs,75);assert.equal(r.later.cases,117);assert.equal(r.later.awards,89);
 assert.equal(evaluate(data.records,{...defaults,state:'Nebraska'}).comparison.award_change_bp,null);
});
test('separate windows, supported years and known weights are required',()=>{
 assert.throws(()=>validate({...defaults,a1:2023}));assert.throws(()=>validate({...defaults,a0:2015,a1:2014}));assert.throws(()=>validate({...defaults,b1:2026}));assert.throws(()=>validate({...defaults,weight:'invented'}));
});
test('shared utility labels in different states do not form a common group',()=>{
 const row=(year,state,award)=>({year,state,utility:'Shared label',case_type:'Distribution',award_bp:award,treasury_bp:200,request_bp:null});
 const r=evaluate([row(2020,'Maine',900),row(2023,'Ohio',1000)],{...defaults,weight:'utility'});assert.equal(r.comparison.common_groups,0);assert.equal(r.comparison.award_change_bp,null);
});
test('CSV preserves missing cells and protects spreadsheet text',()=>{
 const r={...data.records[0],utility:'=1+1',award_bp:null};const output=csv([r]);assert.ok(output.includes("'=1+1"));assert.ok(!output.includes('null'));assert.equal(output.split('\r\n').filter(Boolean).length,2);
});
