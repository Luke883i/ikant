from __future__ import annotations
from dataclasses import dataclass
import json,re
from typing import Any,Callable
from urllib.request import Request,urlopen

SCHEMA='ikant-commercial-abstract-assist/v1-test';MAX_TASK_CHARS=1800;MAX_RESPONSE_BYTES=1024*1024
_ENDPOINTS={'openai':'https://api.openai.com/v1/responses','anthropic':'https://api.anthropic.com/v1/messages','deepseek':'https://api.deepseek.com/chat/completions'}
_FORBIDDEN=re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|bearer\s+\S+|password\s*[:=]|api[_-]?key\s*[:=]|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?:[A-Za-z]:\\|/home/|/Users/|/mnt/|~[/\\])\S+)",re.I)
_CAPSULE=re.compile(r"^op=(?:ANALYZE|COMPARE|SUMMARIZE|EXPLAIN|VERIFY); keys=[A-Za-zÀ-ÿ0-9_.+:-]+(?:,[A-Za-zÀ-ÿ0-9_.+:-]+){0,15}$")
class CommercialAssistError(RuntimeError):pass
@dataclass(frozen=True)
class CommercialAssistConfig:
 provider:str;model:str;api_key:str;timeout_seconds:float=12.0
 def validate(self):
  if self.provider not in _ENDPOINTS or not self.model.strip() or not self.api_key.strip():raise CommercialAssistError('commercial assist configuration invalid')

def build_request(task:str,config:CommercialAssistConfig)->Request:
 config.validate();text=str(task).strip()
 if not text or len(text)>MAX_TASK_CHARS or _FORBIDDEN.search(text) or not _CAPSULE.fullmatch(text):raise CommercialAssistError('commercial task outside typed abstract capsule boundary')
 contract='Abstract analysis only. No tools, no actions, no hidden rationale. Return concise findings. Authority is zero.';headers={'Content-Type':'application/json','Accept':'application/json'}
 if config.provider=='openai':headers['Authorization']='Bearer '+config.api_key;body={'model':config.model,'input':contract+'\n\n'+text,'store':False}
 elif config.provider=='anthropic':headers['x-api-key']=config.api_key;headers['anthropic-version']='2023-06-01';body={'model':config.model,'max_tokens':800,'system':contract,'messages':[{'role':'user','content':text}]}
 else:headers['Authorization']='Bearer '+config.api_key;body={'model':config.model,'messages':[{'role':'system','content':contract},{'role':'user','content':text}],'stream':False,'thinking':{'type':'disabled'}}
 return Request(_ENDPOINTS[config.provider],data=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode(),method='POST',headers=headers)

def _text(provider:str,p:dict[str,Any])->str:
 if provider=='openai':
  rows=[]
  for item in p.get('output') or []:
   if isinstance(item,dict) and item.get('type')=='message':
    for part in item.get('content') or []:
     if isinstance(part,dict) and part.get('type')=='output_text' and isinstance(part.get('text'),str):rows.append(part['text'])
     elif isinstance(part,dict) and 'tool' in str(part.get('type') or ''):raise CommercialAssistError('provider tool output forbidden')
  out='\n'.join(rows).strip()
 elif provider=='anthropic':
  rows=[]
  for part in p.get('content') or []:
   if isinstance(part,dict) and part.get('type')=='tool_use':raise CommercialAssistError('provider tool use forbidden')
   if isinstance(part,dict) and part.get('type')=='text' and isinstance(part.get('text'),str):rows.append(part['text'])
  out='\n'.join(rows).strip()
 else:
  choices=p.get('choices');msg=choices[0].get('message') if isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict) else None
  if not isinstance(msg,dict) or msg.get('tool_calls'):raise CommercialAssistError('provider response invalid or tool-bearing')
  out=str(msg.get('content') or '').strip()
 if not out or len(out)>8192:raise CommercialAssistError('provider text outside bound')
 return out

def call_abstract(task:str,config:CommercialAssistConfig,*,opener:Callable[...,Any]=urlopen)->dict[str,Any]:
 try:
  req=build_request(task,config)
  with opener(req,timeout=max(.25,min(float(config.timeout_seconds),30.0))) as response:raw=response.read(MAX_RESPONSE_BYTES+1)
  if len(raw)>MAX_RESPONSE_BYTES:raise CommercialAssistError('provider response exceeds bound')
  payload=json.loads(raw.decode())
  if not isinstance(payload,dict):raise CommercialAssistError('provider response must be object')
  return {'schema':SCHEMA,'status':'AVAILABLE','provider':config.provider,'text':_text(config.provider,payload),'evidence':0.0,'epistemic_authority':0.0,'execution_authority':0.0,'tool_calls_accepted':False}
 except Exception as exc:
  return {'schema':SCHEMA,'status':'UNAVAILABLE','provider':config.provider,'text':None,'error_class':type(exc).__name__,'local_fallback_required':True,'evidence':0.0,'epistemic_authority':0.0,'execution_authority':0.0,'tool_calls_accepted':False}
