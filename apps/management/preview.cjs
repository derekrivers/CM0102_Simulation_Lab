// Local-only preview. Private fixtures are served on demand, never copied into dist.
const fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const root=path.join(__dirname,'dist'),fixture=process.env.REFERENCE_FIXTURE;
const assets=new Map([['/','index.html'],...['index.html','app.js','worker.js','style.css','cm_management.wasm'].map(name=>['/'+name,name])]);
const server=http.createServer((request,response)=>{
 try {
  let file;
  if(request.url==='/reference-fixture.json'&&fixture){
   if(!path.isAbsolute(fixture)||fs.statSync(fixture).size>65536)throw new Error('invalid fixture');
   file=fixture;
  } else if(assets.has(request.url))file=path.join(root,assets.get(request.url));
  else {response.writeHead(404).end();return;}
  response.setHeader('Cache-Control','no-store');
  response.setHeader('Content-Type',file.endsWith('.wasm')?'application/wasm':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/html');
  response.end(fs.readFileSync(file));
 }catch{response.writeHead(404).end();}
});
server.listen(8766,'127.0.0.1',()=>console.log('Management preview: http://localhost:8766'));
