import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
const manifest=JSON.parse(await fs.readFile('dist/client/release.json','utf8'));
for(const [name,record]of Object.entries(manifest.files)){const raw=await fs.readFile('dist/client/'+name+(name.endsWith('.md')?'.html':''));if(createHash('sha256').update(raw).digest('hex')!==record.sha256||raw.length!==record.bytes)throw Error('Release fingerprint differs: '+name);}
const html=await fs.readFile('dist/client/presentation/index.html','utf8');
if(html.includes('Start the local service')||html.includes('Checking the local data service.')||/__(STYLES|RESEARCH_DATA|APP_SCRIPT)__/.test(html))throw Error('Local-only content or unresolved placeholders remain');
const server=await import('../dist/server/index.js');
if(typeof server.default?.fetch!=='function')throw Error('Worker fetch entrypoint missing');
console.log(JSON.stringify({status:'verified',release_files:Object.keys(manifest.files).length,worker:true}));
