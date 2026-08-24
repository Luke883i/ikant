await import('./public_v1_browser_liveness_core.mjs');
if(!process.exitCode){
  try{
    const {runReactiveHybridBrowserLiveness}=await import('./reactive_hybrid_browser_liveness.mjs');
    await runReactiveHybridBrowserLiveness();
    const {runRuntimeEpochBrowserLiveness}=await import('./runtime_epoch_browser_liveness.mjs');
    await runRuntimeEpochBrowserLiveness();
    await import('./runtime_recovery_browser_liveness.mjs');
  }catch(error){
    console.error(JSON.stringify({schema:'ikant-browser-liveness-suite/v1-test',status:'FAIL',error:String(error?.message||error),real_browser_execution:true,production_reactive_http:true}));
    process.exitCode=1;
  }
}
