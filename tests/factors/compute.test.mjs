import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fit,complete,correlation,rejoin,main} from '../../presentation/factors/compute.mjs';
const study=JSON.parse(fs.readFileSync(new URL('../../reports/factor-study/study.json',import.meta.url)));
const snapshot=JSON.parse(fs.readFileSync(new URL('../../reports/factor-study/macro.json',import.meta.url)));
test('all browser core coefficients and two-way clustered intervals match Python on the real panel',()=>{
 const common=complete(study.records);
 for(const expected of study.models){const result=fit(common,{features:expected.features,effects:expected.effects});assert.equal(result.n,expected.n);assert.ok(Math.abs(result.r2-expected.r2)<1e-10);for(const c of result.coefficients){const reference=expected.coefficients.find(r=>r.term===c.term);for(const field of['estimate','se','low','high'])assert.ok(Math.abs(c[field]-reference[field])<1e-7,expected.id+' '+c.term+' '+field);}}
});
test('browser economic date joins reproduce all archived Python joins',()=>{const rows=rejoin(study.records,snapshot.series);for(let i=0;i<rows.length;i++)for(const key of['treasury90','treasury30','curve90','curve30','inflation','stress','inflation_month','stress_date']){if(typeof rows[i][key]==='number')assert.ok(Math.abs(rows[i][key]-study.records[i][key])<1e-10);else assert.equal(rows[i][key],study.records[i][key]);}});
test('Pearson and tied-rank Spearman match scipy for each empirical predictor',()=>{const rows=complete(study.records);for(const expected of study.common_correlations.filter(r=>r.x==='roe')){const result=correlation(rows,expected.x,expected.y);assert.equal(result.n,expected.n);for(const key of['pearson','spearman'])assert.ok(Math.abs(result[key]-expected[key])<1e-12);}});
test('constant correlations are unavailable and undersized fits fail clearly',()=>{assert.equal(correlation([{x:1,y:1},{x:1,y:2},{x:1,y:3}],'x','y').pearson,null);assert.throws(()=>fit(study.records.slice(0,2)),/Too few/);});
