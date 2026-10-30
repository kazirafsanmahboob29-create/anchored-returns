import test from 'node:test';
import assert from 'node:assert/strict';
import {selectCases,describe,annual,exportCsv} from '../presentation/filing/data.mjs';

// Calculation fixtures are separate from the exported research records.
const rows=[{id:'a',year:2020,region:'South',state:'A',utility:'One',docket:'D1',request_bp:1050,award_bp:975},
  {id:'b',year:2020,region:'South',state:'A',utility:'Two',docket:'D2',request_bp:1000,award_bp:1000},
  {id:'c',year:2022,region:'West',state:'B',utility:'Three',docket:'D3',request_bp:1100,award_bp:950}];
test('selection combines date, geography and text without changing inputs',()=>{
  assert.deepEqual(selectCases(rows,{start:2020,end:2021,region:'South',query:'two'}),[rows[1]]);
  assert.equal(rows.length,3); assert.throws(()=>selectCases(rows,{start:2023,end:2020}));
});
test('paired means and median gaps use the same denominators',()=>{
  const s=describe(rows); assert.equal(s.n,3); assert.equal(s.meanGap,-75); assert.equal(s.medianGap,-75);
  assert.equal(s.below,2); assert.equal(describe([]).meanGap,null);
});
test('annual export preserves a missing year rather than inventing an observation',()=>{
  assert.deepEqual(annual(rows).map(r=>[r.year,r.n]),[[2020,2],[2022,1]]);
});
test('CSV quotes source strings and neutralizes spreadsheet formulas',()=>{
  const csv=exportCsv([{...rows[0],utility:'One, "Company"',docket:'=1+1'}]);
  assert.ok(csv.includes('"One, ""Company"""')); assert.ok(csv.includes("'=1+1"));
  assert.ok(csv.includes(',1050,975,'));
});
