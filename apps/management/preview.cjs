// Local-only preview. Private fixtures are served on demand, never copied into dist.
const fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const root=path.join(__dirname,'dist'),fixture=process.env.REFERENCE_FIXTURE,humanFixture=process.env.HUMAN_REFERENCE_FIXTURE,effectiveFixture=process.env.EFFECTIVE_REFERENCE_FIXTURE,assignmentFixture=process.env.ASSIGNMENT_REFERENCE_FIXTURE;
const assets=new Map([['/','index.html'],...['index.html','app.js','worker.js','storage.js','style.css','cm_management.wasm'].map(name=>['/'+name,name])]);
const server=http.createServer((request,response)=>{
 try {
  let file;
  const local=request.url==='/reference-fixture.json'?fixture:request.url==='/human-reference-fixture.json'?humanFixture:request.url==='/effective-reference-fixture.json'?effectiveFixture:request.url==='/assignment-reference-fixture.json'?assignmentFixture:null;
  if(local){
   if(!path.isAbsolute(local)||fs.statSync(local).size>65536)throw new Error('invalid fixture');
   file=local;
  } else if(assets.has(request.url))file=path.join(root,assets.get(request.url));
  else {response.writeHead(404).end();return;}
  response.setHeader('Cache-Control','no-store');
  response.setHeader('Content-Type',file.endsWith('.wasm')?'application/wasm':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/html');
  response.end(fs.readFileSync(file));
 }catch{response.writeHead(404).end();}
});
const port=Number(process.env.MANAGEMENT_PREVIEW_PORT||8766);
if(!Number.isInteger(port)||port<0||port>65535)throw new Error('invalid preview port');
server.listen(port,'127.0.0.1',()=>console.log('Management preview: http://127.0.0.1:'+server.address().port));
