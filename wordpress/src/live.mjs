/* Primary-source retrieval. No proxy, account, key or external application host. */
export function parseBls(raw){
 if(raw.status!=='REQUEST_SUCCEEDED')throw Error('BLS did not return a successful response.');
 const series=raw.Results?.series;if(series?.length!==1||series[0].seriesID!=='CUUR0000SA0')throw Error('Unexpected CPI series.');
 return series[0].data.filter(r=>/^M(0[1-9]|1[0-2])$/.test(r.period)&&!['-','.',null,''].includes(r.value)).map(r=>{const value=Number(r.value),date=r.year+'-'+r.period.slice(1)+'-01';if(!Number.isFinite(value)||value<=0||value>1000)throw Error('Invalid CPI observation.');return {date,value,footnotes:r.footnotes};}).sort((a,b)=>a.date.localeCompare(b.date));
}
export function parseTreasury(text,year){
 const xml=new DOMParser().parseFromString(text,'application/xml');if(xml.querySelector('parsererror'))throw Error('Treasury returned invalid XML.');
 const properties=[...xml.getElementsByTagNameNS('*','properties')],get=(p,k)=>p.getElementsByTagNameNS('*',k)[0]?.textContent,rows=[];
 for(const p of properties){const date=get(p,'NEW_DATE')?.slice(0,10),ten=get(p,'BC_10YEAR'),three=get(p,'BC_3MONTH');if(!date||Number(date.slice(0,4))!==year)throw Error('Unexpected Treasury observation year.');if(!ten||!three)continue;const a=Number(ten),b=Number(three);if(!Number.isFinite(a)||!Number.isFinite(b)||a<0||a>25||b<0||b>25)throw Error('Invalid Treasury yield.');rows.push({date,ten:a,three:b});}
 if(rows.length<(year===new Date().getUTCFullYear()?1:100))throw Error('Treasury annual response is incomplete.');if(new Set(rows.map(r=>r.date)).size!==rows.length)throw Error('Duplicate Treasury dates.');return rows.sort((a,b)=>a.date.localeCompare(b.date));
}
const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(n=>n.toString(16).padStart(2,'0')).join('');
export async function directRefresh(archive,progress=()=>{}){
 const year=new Date().getUTCFullYear(),raw=[],histories=new Map();
 async function retrieve(url){const response=await globalThis.fetch(url,{signal:AbortSignal.timeout(30000),credentials:'omit'});if(!response.ok)throw Error('Source returned HTTP '+response.status);const text=await response.text();raw.push({url,retrieved_at_utc:new Date().toISOString(),sha256:await digest(text),body:text});return text;}
 const years=Array.from({length:year-2008+1},(_,i)=>2008+i);let done=0;
 // Limit requests to three at a time. Retain every response for the exported snapshot.
 for(let i=0;i<years.length;i+=3)await Promise.all(years.slice(i,i+3).map(async y=>{const url='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value='+y;histories.set(y,parseTreasury(await retrieve(url),y));progress('Treasury histories: '+(++done)+' of '+years.length+' years.');}));
 const cpi=[];for(let first=2008;first<=year;first+=10){const last=Math.min(first+9,year),url='https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?startyear='+first+'&endyear='+last;cpi.push(...parseBls(JSON.parse(await retrieve(url))));}
 const rows=[...histories.values()].flat().sort((a,b)=>a.date.localeCompare(b.date));
 if(new Set(cpi.map(r=>r.date)).size!==cpi.length)throw Error('Duplicate CPI dates.');if(cpi.length<180)throw Error('CPI historical coverage is incomplete.');
 const latest=rows.at(-1),latestCpi=cpi.at(-1),age=(Date.now()-Date.parse(latest.date))/86400000;if(age>10||age<0)throw Error('The Treasury response is stale or future dated.');if((Date.now()-Date.parse(latestCpi.date))/86400000>120)throw Error('The CPI response is stale.');
 return {schema:'anchored-returns-direct-snapshot/1',id:new Date().toISOString(),retrieved_at_utc:new Date().toISOString(),series:{DGS10:rows.map(r=>({date:r.date,value:r.ten})),T10Y3M:rows.map(r=>({date:r.date,value:r.ten-r.three})),CPIAUCNS:cpi,STLFSI4:archive.series.STLFSI4},sources:[{series_id:'Treasury 10-year',series_url:'https://home.treasury.gov/resource-center-data-chart-center/interest-rates',latest:{date:latest.date}},{series_id:'Treasury 10y minus 3m',series_url:'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',latest:{date:latest.date}},{series_id:'BLS CPI-U',series_url:'https://www.bls.gov/cpi/',latest:{date:latestCpi.date}},{series_id:'STLFSI4 (archive)',series_url:'https://fred.stlouisfed.org/series/STLFSI4',latest:{date:archive.series.STLFSI4.at(-1).date}}],raw_responses:raw,latest:{treasury:latest,cpi:latestCpi},limitations:['Treasury par yields are retrieved directly; the archived paper used FRED DGS10 and T10Y3M.','STLFSI4 remains the archived October 26, 2026 vintage.','EEI case observations remain the preserved 2025 Q3 table.','Historical revisions can change calculated measurements; this refresh does not revise the published paper.']};
}
