// All source values are integer basis points. Missing measurements remain null.
export const defaults={a0:2020,a1:2021,b0:2023,b1:2024,state:'',type:'',weight:'case'};
export const newEngland=new Set(['Connecticut','Maine','Massachusetts','New Hampshire','Rhode Island','Vermont']);
export const geography=(r,s)=>!s||r.state===s||(s==='@NE'&&newEngland.has(r.state))||(s==='@other'&&!newEngland.has(r.state));
export function validate(s){
  for(const k of ['a0','a1','b0','b1'])if(!Number.isInteger(s[k])||s[k]<2010||s[k]>2025)throw Error('Choose years between 2010 and 2025.');
  if(s.a0>s.a1||s.b0>s.b1)throw Error('Each period must end on or after its start year.');
  if(s.a1>=s.b0)throw Error('The two periods must be separate, with the earlier period first.');
  if(!['case','state','utility'].includes(s.weight))throw Error('Unknown weighting.');
  if(!['','Distribution','Vertically Integrated'].includes(s.type))throw Error('Unknown case type.');
  return s;
}
const mean=a=>a.length?a.reduce((a,b)=>a+b,0)/a.length:null;
const median=a=>{if(!a.length)return null;const s=[...a].sort((a,b)=>a-b);return s.length%2?s[(s.length-1)/2]:(s[s.length/2-1]+s[s.length/2])/2;};
export function describe(rows){
  const a=rows.filter(r=>r.award_bp!==null),p=a.filter(r=>r.request_bp!==null),t=a.filter(r=>r.treasury_bp!==null),g=p.map(r=>r.award_bp-r.request_bp);
  return {cases:rows.length,awards:a.length,missing_awards:rows.length-a.length,pairs:p.length,matched_treasury:t.length,
    mean_award_bp:mean(a.map(r=>r.award_bp)),median_gap_bp:median(g),mean_gap_bp:mean(g),
    mean_treasury_bp:mean(t.map(r=>r.treasury_bp)),mean_matched_award_bp:mean(t.map(r=>r.award_bp)),
    below_request:g.filter(v=>v<0).length};
}
export function evaluate(records,selection){
  const s=validate(selection),filter=(start,end)=>records.filter(r=>r.year>=start&&r.year<=end&&geography(r,s.state)&&(!s.type||r.case_type===s.type));
  const earlier=filter(s.a0,s.a1),later=filter(s.b0,s.b1),matched=rows=>rows.filter(r=>r.award_bp!==null&&r.treasury_bp!==null);
  const a=matched(earlier),b=matched(later),groups=[];
  let award=null,treasury=null,earlier_n=a.length,later_n=b.length;
  if(s.weight==='case'){
    if(a.length&&b.length){award=mean(b.map(r=>r.award_bp))-mean(a.map(r=>r.award_bp));treasury=mean(b.map(r=>r.treasury_bp))-mean(a.map(r=>r.treasury_bp));}
  }else{
    const key=r=>s.weight==='state'?r.state:r.state+' / '+r.utility,ak=new Set(a.map(key)),bk=new Set(b.map(key));
    for(const k of [...ak].filter(k=>bk.has(k)).sort()){
      const l=a.filter(r=>key(r)===k),r=b.filter(r=>key(r)===k);
      groups.push({group:k,earlier_n:l.length,later_n:r.length,award_change_bp:mean(r.map(r=>r.award_bp))-mean(l.map(r=>r.award_bp)),treasury_change_bp:mean(r.map(r=>r.treasury_bp))-mean(l.map(r=>r.treasury_bp))});
    }
    award=mean(groups.map(g=>g.award_change_bp));treasury=mean(groups.map(g=>g.treasury_change_bp));
    earlier_n=groups.reduce((a,g)=>a+g.earlier_n,0);later_n=groups.reduce((a,g)=>a+g.later_n,0);
  }
  return {earlier:describe(earlier),later:describe(later),comparison:{weighting:s.weight,earlier_n,later_n,common_groups:s.weight==='case'?null:groups.length,award_change_bp:award,treasury_change_bp:treasury,groups},records:[...earlier,...later]};
}
export function csv(records){
  const fields=['source_row','state','utility','docket','case_type','authorized_date','requested_date','award_bp','request_bp','treasury_bp','treasury_date','treasury_gap_days'];
  const cell=v=>{if(v===null||v===undefined)return '';let s=String(v);if(typeof v!=='number'&&/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  return [fields,...records.map(r=>fields.map(f=>r[f]))].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
}
