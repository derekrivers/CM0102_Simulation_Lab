// One WASM instance owns state. Requests execute in arrival order.
const ready = WebAssembly.instantiateStreaming(fetch('cm_management.wasm'),{}).then(({instance})=>instance.exports);
let queue = Promise.resolve();
self.onmessage = ({data:{id,operation}}) => {
  queue = queue.then(async()=>{
    try {
      const wasm=await ready;
      const input=new TextEncoder().encode(JSON.stringify(operation));
      if(input.length>1048576) throw new Error('Request too large');
      const inputPointer=wasm.input_ptr(); // Initial buffer allocation can grow memory.
      new Uint8Array(wasm.memory.buffer,inputPointer,input.length).set(input);
      const length=wasm.request(input.length);
      // Acquire a fresh memory view after execution, which may grow memory.
      const output=new Uint8Array(wasm.memory.buffer,wasm.output_ptr(),length).slice();
      self.postMessage({id,response:JSON.parse(new TextDecoder().decode(output))});
    } catch(error) {self.postMessage({id,error:String(error)});}
  });
};
