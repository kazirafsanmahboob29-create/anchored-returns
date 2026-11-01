import test from 'node:test';
import assert from 'node:assert/strict';

test('aggregate results remain readable when local case data are not installed',async()=>{
  const previousDocument=globalThis.document,previousFetch=globalThis.fetch;
  const elements=new Map(['start','end','region','query','export'].map(id=>[id,{disabled:id==='export',textContent:''}]));
  globalThis.document={getElementById(id){
    if(!elements.has(id)) elements.set(id,{disabled:id==='export',textContent:''});
    return elements.get(id);
  }};
  // Display fixture only; no rows or empirical outputs are written by this test.
  globalThis.fetch=async url=>url.endsWith('cases.json')
    ? new Response('',{status:404})
    : Response.json({prediction_metrics:[{rule:'with_request',n:3,mae_bp:12},{rule:'prior',n:3,mae_bp:20}]});
  try {
    await import('../presentation/filing/view.mjs?test=missing-cases');
    assert.match(elements.get('result').textContent,/In 3 filing-stage comparisons/);
    assert.match(elements.get('status').textContent,/Local case data are not installed/);
    for(const id of ['start','end','region','query','export']) assert.equal(elements.get(id).disabled,true);
  } finally {
    globalThis.document=previousDocument;
    globalThis.fetch=previousFetch;
  }
});
