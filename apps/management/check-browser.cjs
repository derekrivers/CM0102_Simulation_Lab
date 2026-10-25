// Run from this directory after npm run build. Requires Playwright + Chromium.
const fs=require('node:fs'), path=require('node:path'),http=require('node:http');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve('../..'),out=path.resolve('test-output');fs.mkdirSync(out,{recursive:true});
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const encoded=value=>JSON.stringify(canonical(value));
const hash=value=>createHash('sha256').update(value).digest('hex');
const command=(id,revision,club,plan)=>({action:'command',command:{session_id:'fictional-club-session-v1',command_id:id,expected_revision:revision,club_id:club,plan_id:plan}});
function native(operations){const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(operations),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);}
const oracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/plan-selection-oracle-v1.json')));
const prefix=oracle.cases.map((c,i)=>command('oracle-'+i,i,c.club_id,c.selected_plan));
prefix.push(command('negative',24,0,-1),command('wide',24,0,65536),command('missing',24,99,0),command('stale',0,0,0),command('oracle-0',0,0,4),{action:'state'}, {action:'save'});
const saved=native(prefix).at(-1).result;
const operations=[...prefix,command('continuation',24,2,1),{action:'load',save:saved},command('continuation',24,2,1),command('continuation',24,2,1),{action:'load',save:'corrupt'}, {action:'state',unexpected:true}];
const expected=native(operations);
for(const index of [24,25,26,27,28,35,36]){assert.equal(expected[index].ok,false);assert.deepEqual(expected[index].state,expected[index-1].state);}
assert.deepEqual(expected[31].state,expected[33].state);assert.deepEqual(expected[33].state,expected[34].state);
const allowed=new Map([['/','index.html'],...['index.html','app.js','worker.js','storage.js','style.css','cm_management.wasm'].map(x=>['/'+x,x])]);
const server=http.createServer((req,res)=>{const file=allowed.get(req.url);if(!file){res.writeHead(404).end();return;}const mime=file.endsWith('.wasm')?'application/wasm':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html';res.setHeader('Content-Type',mime);res.end(fs.readFileSync(path.join('dist',file)));});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:'+server.address().port);await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  const actual=await page.evaluate(async ops=>{const results=[];for(const op of ops)results.push(await window.managementRequest(op));return results;},operations);
  assert.equal(encoded(actual),encoded(expected),'native/browser full state/event/save/rejection mismatch');
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  await page.getByLabel('Choose a research plan').selectOption('4');await page.getByRole('button',{name:'Apply plan',exact:true}).click();
  await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();assert.equal(await page.getByTestId('selected-plan').textContent(),'Research plan 5');
  const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Export state'}).click();const download=await downloadEvent;await download.saveAs(path.join(out,'club-plan-slice-v1.json'));
  await page.getByLabel('Choose a research plan').selectOption('2');await page.getByRole('button',{name:'Apply plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
  await page.getByLabel('Import state',{exact:true}).setInputFiles(path.join(out,'club-plan-slice-v1.json'));await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();assert.equal(await page.getByTestId('selected-plan').textContent(),'Research plan 5');
  await page.getByLabel('Import state',{exact:true}).setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('invalid')});await page.getByRole('status').filter({hasText:'Rejected:'}).waitFor();assert.equal(await page.getByTestId('selected-plan').textContent(),'Research plan 5');
  await page.screenshot({path:path.join(out,'management.png'),fullPage:true});assert.deepEqual(errors,[]);
  const verifyReference=require('./check-reference.cjs');
  const referenceProfiles=[await verifyReference(page,root,out,fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-managers-v1.json'),'utf8'))];
  if(process.env.REFERENCE_FIXTURE) referenceProfiles.push(await verifyReference(page,root,out,fs.readFileSync(process.env.REFERENCE_FIXTURE,'utf8')));
  const verifyHuman=require('./check-human.cjs');
  const humanProfiles=[await verifyHuman(page,root,out,fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-human-registry.json'),'utf8'))];
  if(process.env.HUMAN_REFERENCE_FIXTURE)humanProfiles.push(await verifyHuman(page,root,out,fs.readFileSync(process.env.HUMAN_REFERENCE_FIXTURE,'utf8')));
  assert.deepEqual(errors,[]);
  const receipt={schema_version:1,command_count:operations.length,original_instruction_cases:oracle.cases.length,native_browser_equal:true,canonical_sha256:hash(encoded(actual)),wasm_sha256:hash(fs.readFileSync('dist/cm_management.wasm')),browser_version:browser.version(),controls:['invalid plan/bound/club/revision/id atomic','save/load deterministic continuation','duplicate commands idempotent after reload','invalid save import preserves state','React command/save/import interaction'],limitations:['legacy profile uses fictional squad and a null manager pointer','ordinary reference profiles admit only pinned ordinary club/nonhuman manager records','retained production capture uses an older instrumented Bosman platform with no contemporaneous input-consumption seal','plan labels remain fictional; original UI, full human registry lifecycle and match effects unqualified']};
  receipt.reference_profiles=referenceProfiles;
  receipt.human_profiles=humanProfiles;
  fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
