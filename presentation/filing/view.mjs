import {selectCases,describe,annual,exportCsv} from './data.mjs';

const $=id=>document.getElementById(id);
const number=(x,d=1)=>x==null ? 'Unavailable' : x.toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});
const svgNode=(name,attributes={},text)=>{
  const node=document.createElementNS('http://www.w3.org/2000/svg',name);
  for(const [key,value] of Object.entries(attributes)) node.setAttribute(key,value);
  if(text!==undefined) node.textContent=text;
  return node;
};

function drawChart(rows) {
  const svg=$('chart'); svg.replaceChildren();
  if(!rows.length) { svg.append(svgNode('text',{x:70,y:100},'No cases match this selection.')); return; }
  const points=annual(rows); const left=64,right=858,top=30,bottom=278;
  let minimum=Math.floor(Math.min(...points.map(x=>x.meanAward),...points.map(x=>x.meanRequest)));
  let maximum=Math.ceil(Math.max(...points.map(x=>x.meanAward),...points.map(x=>x.meanRequest)));
  if(minimum===maximum) { minimum-=1; maximum+=1; }
  const first=points[0].year,last=points.at(-1).year;
  const x=year=>first===last ? (left+right)/2 : left+(year-first)/(last-first)*(right-left);
  const y=value=>bottom-(value-minimum)/(maximum-minimum)*(bottom-top);
  for(let i=0;i<=4;i++) {
    const value=minimum+(maximum-minimum)*i/4;
    svg.append(svgNode('line',{x1:left,y1:y(value),x2:right,y2:y(value),stroke:'#dedbd3'}));
    svg.append(svgNode('text',{x:left-12,y:y(value)+4,'text-anchor':'end',fill:'#66615b'},number(value,1)));
  }
  for(const year of [...new Set([first,Math.round((first+last)/2),last])]) svg.append(svgNode('text',{x:x(year),y:bottom+24,'text-anchor':'middle',fill:'#66615b'},year));
  svg.append(svgNode('text',{x:left,y:16,fill:'#66615b'},'Return on equity (%)'));
  for(const [key,color,dash] of [['meanRequest','#20201d',''],['meanAward','#637a68','5 3']]) {
    const path=points.map((p,i)=>(i && p.year===points[i-1].year+1 ? 'L' : 'M')+x(p.year)+','+y(p[key])).join(' ');
    svg.append(svgNode('path',{d:path,fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':dash}));
    for(const p of points) {
      const dot=svgNode('circle',{cx:x(p.year),cy:y(p[key]),r:3,fill:color});
      dot.append(svgNode('title',{},`${p.year}: ${number(p[key],2)}%, ${p.n} paired cases`)); svg.append(dot);
    }
  }
}

function populateTable(rows) {
  const body=$('case-rows'); body.replaceChildren();
  for(const row of [...rows].sort((a,b)=>b.authorized_date.localeCompare(a.authorized_date)||a.id.localeCompare(b.id)).slice(0,50)) {
    const tr=document.createElement('tr');
    for(const value of [row.authorized_date,row.state,row.utility,number(row.request_bp/100,2),number(row.award_bp/100,2),number(row.award_bp-row.request_bp,0),String(row.source_row)]) {
      const td=document.createElement('td'); td.textContent=value; tr.append(td);
    }
    body.append(tr);
  }
  $('table-note').textContent=`Showing the latest ${Math.min(rows.length,50)} of ${rows.length.toLocaleString()} selected cases. The CSV includes every selected row and the docket.`;
}

try {
  const responses=await Promise.all(['cases.json','study.json'].map(name=>fetch('../reports/filing-study/'+name)));
  if(responses.some(r=>!r.ok)) throw new Error('The published data files could not be loaded. Start the local research server and reload this page.');
  const [data,study]=await Promise.all(responses.map(r=>r.json()));
  if(data.schema!=='anchored-returns-filing-study/1' || !Array.isArray(data.cases)) throw new Error('Unrecognized research export.');
  for(const row of data.cases) if(!Number.isFinite(row.request_bp)||!Number.isFinite(row.award_bp)) throw new Error('Incomplete numeric case in the published export.');
  for(const id of ['start','end']) for(let year=1980;year<=2024;year++) {
    const option=document.createElement('option'); option.value=year; option.textContent=year;
    $(id).append(option);
  }
  $('start').value='1980'; $('end').value='2024';
  const model=study.prediction_metrics.find(r=>r.rule==='with_request');
  const prior=study.prediction_metrics.find(r=>r.rule==='prior');
  $('result').textContent=`In ${model.n} filing-stage comparisons, the model using the request has an average absolute error of ${number(model.mae_bp)} basis points. Carrying forward the known prior award gives ${number(prior.mae_bp)}. The detailed study reports the uncertainty and results for every evaluation block.`;
  let selected=[];
  function update() {
    try {
      selected=selectCases(data.cases,{start:Number($('start').value),end:Number($('end').value),region:$('region').value,query:$('query').value});
      const s=describe(selected);
      $('status').textContent=`${s.n.toLocaleString()} paired observations selected`;
      $('description').textContent=s.n ? `Mean request ${number(s.meanRequest,2)}%; mean award ${number(s.meanAward,2)}%. Award minus request: ${number(s.meanGap)} basis points on average and ${number(s.medianGap)} at the median.` : 'No observations match these filters.';
      $('export').disabled=!s.n; drawChart(selected); populateTable(selected);
    } catch(error) {
      selected=[]; $('status').textContent=error.message; $('description').textContent='';
      $('export').disabled=true; drawChart([]); populateTable([]);
    }
  }
  for(const id of ['start','end','region']) $(id).addEventListener('change',update);
  $('query').addEventListener('input',update);
  $('export').addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob([exportCsv(selected)],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a'); link.href=url; link.download='anchored-returns-selected-cases.csv'; link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  update();
} catch(error) { $('status').textContent=error.message; }
