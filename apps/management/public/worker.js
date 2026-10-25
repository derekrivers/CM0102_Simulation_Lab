// One WASM instance owns state. Engine and storage work share one queue.
importScripts('storage.js');
const moduleReady = WebAssembly.compileStreaming(fetch('cm_management.wasm'));
const ready = moduleReady.then(module => new WebAssembly.Instance(module, {}).exports);
let queue = Promise.resolve();
let token = null, previous = null, hostSession = crypto.randomUUID(), storageReady = false;
let durability = {status: 'empty', durable: null};

function invoke(wasm, operation) {
  const input = new TextEncoder().encode(JSON.stringify(operation));
  if (input.length > 1048576) throw new Error('Request too large');
  const inputPointer = wasm.input_ptr();
  new Uint8Array(wasm.memory.buffer, inputPointer, input.length).set(input);
  const length = wasm.request(input.length);
  const output = new Uint8Array(wasm.memory.buffer, wasm.output_ptr(), length).slice();
  return JSON.parse(new TextDecoder().decode(output));
}
const identity = state => ({schema_version: state.schema_version, profile: state.profile,
  fixture_sha256: state.fixture_sha256, session_id: state.session_id, revision: state.revision});
const digest = async text => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',
  new TextEncoder().encode(text))), b => b.toString(16).padStart(2, '0')).join('');
const sameIdentity = (a, b) => a && b && Object.keys(identity(b)).every(key => a[key] === b[key]);

async function validateCheckpoint(checkpoint) {
  if (!checkpoint || checkpoint.version !== 1 || typeof checkpoint.save !== 'string' ||
      checkpoint.save.length > 1048576 || typeof checkpoint.host_session !== 'string' ||
      checkpoint.host_session.length > 64 || await digest(checkpoint.save) !== checkpoint.save_sha256)
    throw new Error('invalid-checkpoint');
  // Validate in an isolated instance before touching the active world.
  const scratch = new WebAssembly.Instance(await moduleReady, {}).exports;
  const result = invoke(scratch, {action: 'load', save: checkpoint.save});
  if (!result.ok || !sameIdentity(checkpoint.identity, result.state)) throw new Error('unsupported-checkpoint');
  return checkpoint;
}

async function connectStorage(forPublication = false) {
  const head = await readCheckpoint();
  if (head && (head.version !== 1 || typeof head.token !== 'string')) throw new Error('invalid-storage-head');
  // A tab that could not recover must not adopt another tab's newer token and
  // publish its unrelated in-memory world. Only explicit recovery may rebind.
  if (forPublication && (head?.token ?? null) !== token)
    throw new Error('storage-conflict-reopen-to-recover');
  token = head?.token ?? null;
  if (!head) { storageReady = true; previous = null; return {checkpoint: null, fallback: false}; }
  for (const [index, candidate] of [head.current, head.previous].entries()) {
    try {
      const checkpoint = await validateCheckpoint(candidate);
      storageReady = true;
      previous = checkpoint;
      return {checkpoint, fallback: index === 1};
    } catch { /* Retain invalid bytes; try the separately committed previous save. */ }
  }
  throw new Error('no-valid-checkpoint-manual-import-or-export-required');
}

function storageFailure(error) {
  durability = {...durability, status: 'failed', error: error.message || 'storage-unavailable'};
}
async function recover(wasm) {
  try {
    const {checkpoint, fallback} = await connectStorage();
    if (checkpoint) {
      const result = invoke(wasm, {action: 'load', save: checkpoint.save});
      if (!result.ok) throw new Error('checkpoint-load-failed');
      hostSession = checkpoint.host_session;
      durability = {status: fallback ? 'fallback' : 'recovered', durable: checkpoint.identity};
    } else durability = {status: 'empty', durable: null};
  } catch (error) { storageReady = false; storageFailure(error); }
  return invoke(wasm, {action: 'state'});
}
async function persist(wasm) {
  try {
    // Retry availability without replacing accepted in-memory commands.
    if (!storageReady) await connectStorage(true);
    const saved = invoke(wasm, {action: 'save'});
    if (!saved.ok) throw new Error('save-rejected');
    const checkpoint = {version: 1, host_session: hostSession, identity: identity(saved.state),
      save: saved.result, save_sha256: await digest(saved.result)};
    token = await publishCheckpoint(token, checkpoint, previous);
    previous = checkpoint;
    durability = {status: 'saved', durable: checkpoint.identity};
  } catch (error) { storageFailure(error); }
}

self.onmessage = ({data: {id, operation, storage}}) => {
  queue = queue.then(async () => {
    try {
      const wasm = await ready;
      let response;
      if (storage && operation.action === 'recover') response = await recover(wasm);
      else if (storage && operation.action === 'persist') {
        await persist(wasm); response = invoke(wasm, {action: 'state'});
      } else {
        response = invoke(wasm, operation);
        if (storage && response.ok && ['command', 'human_command', 'load', 'reset', 'import_reference', 'import_human_reference'].includes(operation.action)) {
          if (!['command', 'human_command'].includes(operation.action)) hostSession = crypto.randomUUID();
          await persist(wasm);
        }
      }
      if (storage) response.durability = {...durability, accepted_revision: response.state.revision};
      self.postMessage({id, response});
    } catch (error) { self.postMessage({id, error: String(error)}); }
  });
};
