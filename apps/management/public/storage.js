// Browser storage/transport only. Rust validates every save and owns all game rules.
const DB_NAME = 'cm-management-checkpoints-v1';
const STORE = 'checkpoints';
const KEY = 'active';

function openDatabase() {
  return new Promise((resolve, reject) => {
    let expired = false;
    const timer = setTimeout(() => { expired = true; reject(new Error('storage-open-timeout')); }, 5000);
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onerror = () => { clearTimeout(timer); reject(new Error('storage-unavailable')); };
    request.onblocked = () => { expired = true; clearTimeout(timer); reject(new Error('storage-blocked')); };
    request.onsuccess = () => { clearTimeout(timer); if (expired) request.result.close(); else resolve(request.result); };
  });
}

// Resolve only at transaction commit, never at an individual request's success.
async function storageTransaction(mode, perform) {
  const db = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE, mode);
      let result;
      let failure = 'storage-transaction-failed';
      const timer = setTimeout(() => { failure = 'storage-transaction-timeout'; transaction.abort(); }, 10000);
      transaction.oncomplete = () => { clearTimeout(timer); resolve(result); };
      transaction.onabort = () => { clearTimeout(timer); reject(new Error(failure)); };
      perform(transaction.objectStore(STORE), value => { result = value; }, reason => {
        failure = reason;
        transaction.abort();
      });
    });
  } finally { db.close(); }
}

async function readCheckpoint() {
  return storageTransaction('readonly', (store, done) => {
    const read = store.get(KEY);
    read.onsuccess = () => done(read.result || null);
  });
}

async function publishCheckpoint(expectedToken, checkpoint, previous) {
  const token = crypto.randomUUID();
  await storageTransaction('readwrite', (store, done, abort) => {
    const read = store.get(KEY);
    read.onsuccess = () => {
      if ((read.result?.token ?? null) !== expectedToken) {
        abort('storage-conflict-reopen-to-recover');
        return;
      }
      try {
        store.put({version: 1, token, current: checkpoint, previous}, KEY);
        done(token);
      } catch { abort('storage-write-failed'); }
    };
  });
  return token;
}
