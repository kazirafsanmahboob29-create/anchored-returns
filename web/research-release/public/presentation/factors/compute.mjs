/* OLS by reorthogonalized QR; two-way cluster covariance follows the methods note. */
export const market=['treasury90','curve90','inflation','stress'];
export const main=[...market,'duration','distribution','prior'];
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length;
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const zeros=(n,m)=>Array.from({length:n},()=>Array(m).fill(0));
const valid=x=>typeof x==='number'&&Number.isFinite(x);
const day=s=>Date.parse(s+'T00:00:00Z');
const iso=x=>new Date(x).toISOString().slice(0,10);
export function complete(rows,features=main){return rows.filter(r=>['roe',...features].every(k=>valid(r[k])));}
export function pearson(a,b){if(a.length<3)return null;const am=mean(a),bm=mean(b),x=a.map(v=>v-am),y=b.map(v=>v-bm);const denominator=Math.sqrt(dot(x,x)*dot(y,y));return denominator>0?dot(x,y)/denominator:null;}
function ranks(a){const order=a.map((v,i)=>({v,i})).sort((x,y)=>x.v-y.v),out=Array(a.length);for(let i=0;i<a.length;){let j=i+1;while(j<a.length&&order[j].v===order[i].v)j++;for(let k=i;k<j;k++)out[order[k].i]=(i+j+1)/2;i=j;}return out;}
export function correlation(rows,x,y){const pairs=rows.filter(r=>valid(r[x])&&valid(r[y])),a=pairs.map(r=>r[x]),b=pairs.map(r=>r[y]);return {n:pairs.length,pearson:pearson(a,b),spearman:pearson(ranks(a),ranks(b))};}
function qr(columns,y){const p=columns.length,n=y.length,Q=[],R=zeros(p,p);for(let j=0;j<p;j++){let v=columns[j].slice();for(let pass=0;pass<2;pass++)for(let k=0;k<j;k++){const projection=dot(Q[k],v);R[k][j]+=projection;v=v.map((x,i)=>x-projection*Q[k][i]);}const length=Math.sqrt(dot(v,v));if(length<1e-9*Math.max(1,Math.sqrt(dot(columns[j],columns[j]))))throw Error('These controls are collinear in this selection. Choose fewer controls or a wider sample.');R[j][j]=length;Q.push(v.map(x=>x/length));}
 const back=b=>{const result=Array(p).fill(0);for(let i=p-1;i>=0;i--)result[i]=(b[i]-R[i].slice(i+1).reduce((s,x,j)=>s+x*result[i+1+j],0))/R[i][i];return result;};
 const beta=back(Q.map(q=>dot(q,y))),inverse=zeros(p,p);for(let j=0;j<p;j++){const col=back(Array.from({length:p},(_,i)=>Number(i===j)));for(let i=0;i<p;i++)inverse[i][j]=col[i];}
 const bread=zeros(p,p);for(let i=0;i<p;i++)for(let j=0;j<p;j++)bread[i][j]=dot(inverse[i],inverse[j]);
 return {beta,bread,residuals:y.map((v,i)=>v-columns.reduce((s,c,k)=>s+c[i]*beta[k],0)),parameters:p};
}
function clusterScores(columns,residuals,groups){const scores=new Map();for(let i=0;i<groups.length;i++){if(!scores.has(groups[i]))scores.set(groups[i],Array(columns.length).fill(0));const score=scores.get(groups[i]);for(let j=0;j<columns.length;j++)score[j]+=columns[j][i]*residuals[i];}return [...scores.values()];}
export function fit(rows,{features=main,effects='state_year'}={}){
 const data=complete(rows,features),n=data.length;
 const terms=features.filter(k=>new Set(data.map(r=>r[k])).size>1),names=['const',...terms],columns=[Array(n).fill(1),...terms.map(k=>data.map(r=>r[k]))];
 const omitted=features.filter(k=>!terms.includes(k));
 for(const field of effects==='none'?[]:effects==='state_year'?['state','year']:effects==='entity_year'?['entity','year']:['year']){
  const levels=[...new Set(data.map(r=>String(r[field])))].sort();for(const level of levels.slice(1)){names.push(field+'_'+level);columns.push(data.map(r=>Number(String(r[field])===level)));}}
 if(n<columns.length+10)throw Error('Too few observations for this specification. Use a wider period or fewer controls.');
 const result=qr(columns,data.map(r=>r.roe)),p=columns.length;
 const clusters=[data.map(r=>r.state),data.map(r=>r.quarter),data.map(r=>r.state+'|'+r.quarter)],scores=clusters.map(g=>clusterScores(columns,result.residuals,g)),counts=scores.map(s=>s.length),covarianceAvailable=counts.every(g=>g>1);
 const coefficients=terms.map((term,j)=>{const index=j+1,estimate=result.beta[index];let variance=null;if(covarianceAvailable){variance=scores.reduce((total,group,k)=>total+(k===2?-1:1)*(group.length/(group.length-1))*((n-1)/(n-p))*group.reduce((s,score)=>s+dot(result.bread[index],score)**2,0),0);}const se=variance>0?Math.sqrt(variance):null;return {term,estimate,se,low:se?estimate-1.959963984540054*se:null,high:se?estimate+1.959963984540054*se:null};});
 const centered=data.map(r=>r.roe-mean(data.map(d=>d.roe))),r2=1-dot(result.residuals,result.residuals)/dot(centered,centered);
 return {n,parameters:p,r2,adjusted_r2:1-(1-r2)*(n-1)/(n-p),effects,features,omitted,states:counts[0],quarters:counts[1],entities:new Set(data.map(r=>r.entity)).size,coefficients,rows:data.map(r=>r.id),warning:counts[0]<20||counts[1]<20?'Fewer than 20 clusters in at least one dimension. Treat the uncertainty estimates cautiously.':null};
}
function monthBefore(written,months){const d=new Date(day(written));return new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()-months,1)).toISOString().slice(0,10);}
export function rejoin(records,series){const cpi=new Map(series.CPIAUCNS.map(r=>[r.date,r.value]));return records.map(row=>{const out={...row},written=day(row.authorized_date);for(const [name,key]of[['DGS10','treasury'],['T10Y3M','curve']])for(const window of[30,90]){const values=series[name].filter(r=>day(r.date)>=written-window*86400000&&day(r.date)<written&&valid(r.value));out[key+window+'_n']=values.length;out[key+window]=values.length>=(window===90?40:10)&&written-day(values.at(-1).date)<=7*86400000?mean(values.map(r=>r.value)):null;}
 const target=monthBefore(row.authorized_date,2),prior=monthBefore(row.authorized_date,14);out.inflation_month=target;out.inflation=cpi.get(target)&&cpi.get(prior)?100*(cpi.get(target)/cpi.get(prior)-1):null;
 const cutoff=written-14*86400000,stress=series.STLFSI4.filter(r=>day(r.date)<=cutoff&&valid(r.value)).at(-1),good=stress&&cutoff-day(stress.date)<=14*86400000;out.stress=good?stress.value:null;out.stress_date=good?stress.date:null;return out;});}
