import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseBls} from '../../wordpress/src/live.mjs';
const raw=JSON.parse(fs.readFileSync(new URL('../../data/external/bls_cpi/2026-10-26/bls-2018-2026.json',import.meta.url),'utf8'));
test('direct CPI parser retains published observations and a missing source month stays missing',()=>{const rows=parseBls(raw);assert.equal(rows.at(-1).date,'2026-09-01');assert.equal(rows.at(-1).value,336.94);assert.ok(rows.length>90);assert.ok(!rows.some(r=>r.date==='2025-10-01'));assert.ok(rows.every(r=>Number.isFinite(r.value)&&r.value>0));});
test('CPI parser rejects a wrong series, failed request and unrecognized numeric value',()=>{assert.throws(()=>parseBls({...raw,status:'REQUEST_FAILED'}),/successful/);const wrong=structuredClone(raw);wrong.Results.series[0].seriesID='OTHER';assert.throws(()=>parseBls(wrong),/series/);const bad=structuredClone(raw);bad.Results.series[0].data[0].value='unavailable';assert.throws(()=>parseBls(bad),/Invalid CPI/);});
