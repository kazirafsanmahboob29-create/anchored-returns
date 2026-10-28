import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const root = process.argv[2];
if (!root) throw new Error('Supply the absolute project root. This script writes only synthetic QA fixtures.');
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/project_docs/Anchored_Returns_Pilot_Coding_Sheet_v0.1.2.xlsx'));
const sheet = workbook.worksheets.getItem('Reliability');
const before = await workbook.render({sheetName:'Reliability',range:'F1:O5',scale:1.5,format:'png'});
await fs.writeFile(root+'/reports/pdf_qa/m7/before.png',new Uint8Array(await before.arrayBuffer()));
// Render first. The next invocation resumes authoring only after inspection.
if (process.argv[3] !== 'author') process.exit(0);
const a=[1,1,1,1,0,0,0,0], b=[1,1,1,0,1,0,0,0];
workbook.worksheets.getItem('Cases').getRange('D3').values=[['SYNTHETIC M7 SOFTWARE TEST']];
const input = a.map((x,i)=>[`P01-${String(i+1).padStart(3,'0')}`,'MKT',x,b[i]]);
sheet.getRange('A2:D9').values=input;
workbook.worksheets.getItem('Passages').getRange('A3:E10').values=input.map(x=>[x[0],'P01','Synthetic p. 1',null,'SYNTHETIC TEST ONLY. Not an order passage.']);
const evidence=[];
for (const [name,value,expected] of [['toy',0,.5],['changed',1,.75],['restored',0,.5]]) {
  sheet.getRange('D5').values=[[value]];
  workbook.recalculate();
  const values=sheet.getRange('G2:O2').values;
  if (Math.abs(values[0][7]-expected)>1e-12) throw new Error(`${name} expected ${expected}: ${JSON.stringify(values)}`);
  evidence.push({name,changedCell:'D5',value,summary:values[0],expectedKappa:expected});
  const out=await SpreadsheetFile.exportXlsx(workbook);
  await out.save(root+`/reports/m7_fixtures/engine-${name}.xlsx`);
}
const check=await workbook.inspect({kind:'table',range:'Reliability!F1:O3',include:'values,formulas',tableMaxRows:3,tableMaxCols:10,maxChars:3000});
const errors=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'synthetic engine formula error scan'});
const after=await workbook.render({sheetName:'Reliability',range:'F1:O5',scale:1.5,format:'png'});
await fs.writeFile(root+'/reports/pdf_qa/m7/after.png',new Uint8Array(await after.arrayBuffer()));
await fs.writeFile(root+'/reports/m7_engine_check.json',JSON.stringify({engine:'Artifact Tool bundled spreadsheet calculation engine',nativeExcelTested:false,syntheticOnly:true,evidence,inspection:check.ndjson,errorScan:errors.ndjson},null,2)+'\n');
console.log(JSON.stringify(evidence));
