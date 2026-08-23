await import('./public_v1_browser_liveness_core.mjs');
if(!process.exitCode){
  try{
    const {runReactiveHybridBrowserLiveness}=await import('./reactive_hybrid_browser_liveness.mjs');
    await runReactiveHybridBrowserLiveness();
  }catch(error){
    console.error(JSON.stringify({schema:'ikant-reactive-browser-liveness/v1-test',status:'FAIL',error:String(error?.message||error),real_browser_execution:true,production_reactive_http:true}));
    process.exitCode=1;
  }
}
