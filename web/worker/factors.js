const SERIES=['DGS10','T10Y3M','CPIAUCNS','STLFSI4'];
const jsonText=value=>JSON.stringify(value)+'\n';
const hash=async raw=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw)))].map(x=>x.toString(16).padStart(2,'0')).join('');
export function parseSeries(raw,name){
 if(!SERIES.includes(name))throw Error('Unregistered economic series');
  const lines=raw.trim().split(/\r?\n/),header=lines.shift();
 if(!['observation_date,'+name,'DATE,'+name].includes(header))throw Error('Economic series identity changed');
 let previous='';const rows=[];
 for(const line of lines){const parts=line.split(',');if(parts.length!==2||!/^\d{4}-\d{2}-\d{2}$/.test(parts[0])||new Date(parts[0]+'T00:00:00Z').toISOString().slice(0,10)!==parts[0]||parts[0]<=previous)throw Error('Invalid economic observation date');previous=parts[0];const printed=parts[1],value=printed===''||printed==='.'?null:Number(printed);if(value!==null&&(!/^-?\d+(\.\d+)?$/.test(printed)||!Number.isFinite(value)||Math.abs(value)>10000||name==='CPIAUCNS'&&value<=0))throw Error('Invalid economic observation value');rows.push({date:parts[0],value});}
 const numeric=rows.filter(r=>r.value!==null),minimum=name==='CPIAUCNS'?190:name==='STLFSI4'?800:4000;
 if(numeric.length<minimum||rows[0].date>'2009-01-01'||numeric.at(-1).date<'2024-12-01')throw Error('Incomplete economic history');
 return rows;
}
async function download(url,options={},fetcher=fetch){const response=await fetcher(url,{...options,headers:{Accept:'text/csv, application/xml, text/xml, application/json',...options.headers},signal:AbortSignal.timeout(20000),redirect:'follow'});if(!response.ok||new URL(response.url||url).hostname!==new URL(url).hostname)throw Error('Economic source HTTP '+response.status+' at '+new URL(url).hostname+' '+(new URL(url).searchParams.get('id')||'CPI API'));const raw=await response.text();if(raw.length>2_000_000)throw Error('Economic source exceeds expected size');return raw;}
export async function retrieveFactors(fetcher=fetch,now=new Date(),cachedBls=null){
 const retrieved=now.toISOString(),parts=await Promise.all(SERIES.map(async name=>{const url='https://fred.stlouisfed.org/graph/fredgraph.csv?'+new URLSearchParams({id:name,cosd:'2008-01-01',coed:retrieved.slice(0,10)});const raw=await download(url,{},fetcher),rows=parseSeries(raw,name),last=rows.filter(r=>r.value!==null).at(-1),maxAge=name==='CPIAUCNS'?120:name==='STLFSI4'?35:14;if(now-Date.parse(last.date+'T00:00:00Z')>maxAge*86400000)throw Error('Economic source is stale: '+name);return {name,raw,rows,source:{series_id:name,url,series_url:'https://fred.stlouisfed.org/series/'+name,retrieved_at_utc:retrieved,raw_sha256:await hash(raw),rows:rows.length,latest:last}};}));
 // Direct BLS API validates CPI through a separate retrieval route.
 let bls=[],blsSources=[],blsRaw={},blsDate=retrieved,blsMode='api';
 const cacheAge=now-Date.parse(cachedBls?.retrieved_at_utc||'');
 const cacheValid=cachedBls?.series_id==='CUUR0000SA0'&&cachedBls.observations?.length>=190&&cacheAge>=0&&cacheAge<45*86400000;
 try{if(cacheValid&&cacheAge<86400000){blsMode='cached_api';}else for(let start=2008;start<=now.getUTCFullYear();start+=10){const end=Math.min(start+9,now.getUTCFullYear()),url='https://api.bls.gov/publicAPI/v2/timeseries/data/',raw=await download(url,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({seriesid:['CUUR0000SA0'],startyear:String(start),endyear:String(end)})},fetcher),data=JSON.parse(raw),series=data.Results?.series;
  if(data.status!=='REQUEST_SUCCEEDED'||series?.length!==1||series[0].seriesID!=='CUUR0000SA0')throw Error('BLS CPI validation unavailable: '+data.status+' '+(data.message||[]).join(';').slice(0,200));
  for(const row of series[0].data){if(/^M(0[1-9]|1[0-2])$/.test(row.period)){const value=row.value==='-'?null:Number(row.value);if(value!==null&&(!Number.isFinite(value)||value<=0))throw Error('Invalid BLS CPI');bls.push({date:row.year+'-'+row.period.slice(1)+'-01',value});}}
  blsRaw['bls-'+start+'-'+end+'.json']=raw;
  blsSources.push({url,startyear:start,endyear:end,raw_sha256:await hash(raw),retrieved_at_utc:retrieved});
 }}catch(error){if(!cacheValid)throw error;console.warn('bls_api_using_dated_cache',error.message);blsMode='stale_cached_api';}
 if(blsMode!=='api'){bls=cachedBls.observations;blsSources=cachedBls.sources;blsDate=cachedBls.retrieved_at_utc;blsRaw={};}
 if(bls.some((r,i)=>!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||r.value!==null&&(!Number.isFinite(r.value)||r.value<=0))||new Set(bls.map(r=>r.date)).size!==bls.length)throw Error('Invalid cached BLS observations');
 const cpi=new Map(parts.find(p=>p.name==='CPIAUCNS').rows.filter(r=>r.value!==null).map(r=>[r.date,r.value]));
 const overlap=bls.filter(r=>r.value!==null&&cpi.has(r.date)),mismatches=overlap.filter(r=>Math.abs(cpi.get(r.date)-r.value)>1e-8);
 if(overlap.length<190||mismatches.length)throw Error('BLS and FRED CPI histories do not reconcile');
 const snapshot={schema:'anchored-returns-factor-snapshot/1',id:retrieved.replace(/[:.]/g,'-'),retrieved_at_utc:retrieved,vintage:'Current historical data, not an as-known historical panel',series:Object.fromEntries(parts.map(p=>[p.name,p.rows])),sources:parts.map(p=>p.source),bls_data:{series_id:'CUUR0000SA0',retrieved_at_utc:blsDate,observations:bls,sources:blsSources},bls_check:{series_id:'CUUR0000SA0',mode:blsMode,retrieved_at_utc:blsDate,overlap:overlap.length,mismatches:0,unmatched_fred_months:cpi.size-overlap.length,meaning:'Two delivery routes for the same CPI series, not independent measurement; BLS retrieval date is separate from FRED retrieval',sources:blsSources}};
 return {snapshot,raw:{...Object.fromEntries(parts.map(p=>[p.name+'.csv',p.raw])),...blsRaw}};
}
export async function readFactors(bucket){const pointer=await bucket.get('factors/latest.json');if(!pointer)return null;const {id}=await pointer.json();if(!/^[0-9TZ-]+$/.test(id))throw Error('Invalid economic snapshot pointer');const value=await bucket.get('factors/'+id+'/snapshot.json');if(!value)throw Error('Economic snapshot missing');return value.json();}
export async function saveFactors(bucket,result){const base='factors/'+result.snapshot.id+'/';for(const[name,raw]of Object.entries(result.raw))await bucket.put(base+name,raw);await bucket.put(base+'snapshot.json',jsonText(result.snapshot));await bucket.put('factors/latest.json',jsonText({id:result.snapshot.id}));return result.snapshot;}
