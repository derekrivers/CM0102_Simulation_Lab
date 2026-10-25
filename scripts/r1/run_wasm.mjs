import { readFileSync, writeFileSync } from 'node:fs';
const [wasm, output] = process.argv.slice(2);
const { instance } = await WebAssembly.instantiate(readFileSync(wasm), {});
const length = instance.exports.corpus_run();
const pointer = instance.exports.corpus_ptr();
writeFileSync(output, new Uint8Array(instance.exports.memory.buffer, pointer, length));
console.log(JSON.stringify({runtime: process.version, bytes: length, executed: true}));
