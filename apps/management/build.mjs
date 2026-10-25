import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
await mkdir('dist',{recursive:true});
await build({entryPoints:['src/main.tsx'],bundle:true,minify:true,outfile:'dist/app.js',define:{'process.env.NODE_ENV':'"production"'}});
for(const file of ['index.html','worker.js','style.css']) await copyFile(`public/${file}`,`dist/${file}`);
await copyFile('../../target/wasm32-unknown-unknown/release/cm_management.wasm','dist/cm_management.wasm');
