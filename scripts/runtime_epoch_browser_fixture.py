from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from ikant.managed_runtime import _binding_digest
from ikant.reactive_http import build_server


def model_projection(model_id:str,sha:str)->dict:
 binding={'manifest_sha256':'1'*64,'engine':{'id':'llama.cpp','version':'b9999','platform':'linux-x86_64','artifact_sha256':'2'*64},'model':{'id':model_id,'revision':'3'*40,'sha256':sha}}
 return {'schema':'ikant-managed-local-runtime/v0.23-test','status':'READY','managed':True,'manifest_sha256':binding['manifest_sha256'],'binding_sha256':_binding_digest(binding),'engine':binding['engine'],'model':binding['model'],'browser_model_transport':False,'model_output_is_authority':False,'component_presence_is_authority':False,'runtime_readiness_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}

class EpochFixtureService:
 def __init__(self,root:Path):self.root=root;self.web_adapter=None
 def bind_web_adapter(self,adapter):self.web_adapter=adapter
 def lifecycle(self):return {'state':'ACTIVE'}
 def product_status(self):return {'stage':'READY','attempt':1,'runtime_ready':True,'voice':{'configured':False},'epistemic_authority':0.0,'execution_authority':0.0}

def main()->int:
 with tempfile.TemporaryDirectory(prefix='ikant-s17-browser-') as tmp:
  root=Path(tmp).resolve();state=root/'.ikant';state.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'PRODUCT_CONTRACT.json',root/'PRODUCT_CONTRACT.json')
  (state/'runtime.json').write_text(json.dumps({'status':'ACTIVE','session_id':'browser-s17','contract_sha256':'c'*64}),encoding='utf-8')
  current=state/'model-runtime.json';next_model=state/'model-runtime-b.json';current.write_text(json.dumps(model_projection('model-a','a'*64)),encoding='utf-8');next_model.write_text(json.dumps(model_projection('model-b','b'*64)),encoding='utf-8')
  service=EpochFixtureService(root);server,pairing=build_server(service,host='127.0.0.1',port=0,assets_dir=ROOT/'ikant'/'web')
  print(json.dumps({'schema':'ikant-runtime-epoch-browser-fixture/v1-test','port':int(server.server_address[1]),'pairing_code':pairing.code,'model_current':str(current),'model_next':str(next_model)}),flush=True)
  try:server.serve_forever(poll_interval=.05)
  finally:server.server_close()
 return 0
if __name__=='__main__':raise SystemExit(main())
