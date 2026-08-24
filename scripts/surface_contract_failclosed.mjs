import fs from 'node:fs';
import vm from 'node:vm';
import {performance} from 'node:perf_hooks';

const source=fs.readFileSync(new URL('../ikant/web/surface-contract.js',import.meta.url),'utf8');
const snapshot={schema:'ikant-surface-contract/v1-test',snapshot_sha256:'s16bis-fixture',public:{experience:{}},foundation:{config:{}},work:{active:false,phase:'IDLE'},manifest:{semantic_contract_sha256:'same',surface_profiles:[{id:'webapp',semantic_contract_sha256:'same'},{id:'floating_pwa_profile',semantic_contract_sha256:'same'}]}};

function context(mode){
 let legacyCalls=0,v10Calls=0;
 const nativeFetch=async input=>{
  const path=new URL(typeof input==='string'?input:input.url,'http://127.0.0.1/').pathname;
  if(path==='/api/v10/surface'){
   v10Calls++;
   if(mode.state==='v10-ok')return new Response(JSON.stringify(snapshot),{status:200,headers:{'Content-Type':'application/json'}});
   return new Response('{}',{status:503,headers:{'Content-Type':'application/json'}});
  }
  if(path==='/api/v8/public'){legacyCalls++;return new Response(JSON.stringify({legacy:true}),{status:200,headers:{'Content-Type':'application/json'}});}
  return new Response('{}',{status:404});
 };
 const document={documentElement:{dataset:{}},dispatchEvent(){},getElementById(){return null;},querySelector(){return null;}};
 const sandbox={URL,URLSearchParams,Headers,Request,Response,performance,queueMicrotask,location:{href:'http://127.0.0.1/',search:''},sessionStorage:{getItem(){return '';},setItem(){}},document,CustomEvent:class{constructor(type,init={}){this.type=type;this.detail=init.detail;}},matchMedia(){return {matches:false};},console};
 sandbox.window={fetch:nativeFetch};sandbox.globalThis=sandbox;
 vm.createContext(sandbox);vm.runInContext(source,sandbox,{filename:'surface-contract.js'});
 return {sandbox,counts:()=>({legacyCalls,v10Calls})};
}

// Before the first canonical ACTIVE bind, bootstrap compatibility may still use legacy reads.
{
 const mode={state:'v10-fail'},h=context(mode);const r=await h.sandbox.window.fetch('/api/v8/public');
 if(r.status!==200)throw new Error('pre-bind bootstrap fallback unexpectedly blocked');
 const c=h.counts();if(c.legacyCalls!==1||c.v10Calls!==1)throw new Error('pre-bind fallback did not exercise expected compatibility path');
 if(h.sandbox.window.ikantSurfaceContract.isCanonicalBound())throw new Error('failed v10 request must not bind canonical surface');
}

// Once canonical state has been observed, a later v10 failure must never resurrect legacy semantic reads.
{
 const mode={state:'v10-ok'},h=context(mode);let r=await h.sandbox.window.fetch('/api/v8/public');
 if(r.status!==200||!h.sandbox.window.ikantSurfaceContract.isCanonicalBound())throw new Error('canonical bind failed');
 h.sandbox.window.ikantSurfaceContract.invalidate();mode.state='v10-fail';r=await h.sandbox.window.fetch('/api/v8/public');
 if(r.status!==503)throw new Error('post-bind canonical failure did not fail closed');
 const body=await r.json();if(body.legacy_semantic_fallback!==false||body.canonical_surface_bound!==true)throw new Error('post-bind failure receipt drift');
 const c=h.counts();if(c.legacyCalls!==0||c.v10Calls!==2)throw new Error('post-bind failure reached legacy semantic endpoint');
}

console.log(JSON.stringify({schema:'ikant-s16bis-surface-failclosed/v1-test',status:'PASS',pre_active_compatibility:true,active_post_bind_legacy_fallback:false}));
