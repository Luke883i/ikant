from __future__ import annotations

import json
import re
import time
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .local_security import require_loopback_url

MODEL_BROKER_SCHEMA = "ikant-local-model-broker/v0.20-test"
_ITALIAN_WORDS = frozenset({"ciao","chi","sei","cosa","che","come","puoi","vorrei","grazie","perche","perché","italiano","italiana","spiegami","dimmi","fammi"})
_ENGLISH_WORDS = frozenset({"hello","hi","who","what","how","can","could","please","thanks","explain","tell"})
_ITALIAN_RESPONSE_WORDS = frozenset({"ciao","sono","posso","puoi","aiutarti","aiuto","oggi","cosa","come","che","con","per","il","lo","la","un","una","e","di","ti","tu","vuoi","serve","risposta","locale"})
_ENGLISH_RESPONSE_WORDS = frozenset({"hello","hi","i","you","your","we","the","a","an","and","to","with","how","can","could","help","today","what","who","are","is","want","need","answer","local"})


class LocalModelError(RuntimeError):
    pass


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zà-ÿ']+", str(text).casefold())


def _reply_language(user_text: str) -> str:
    words=set(_tokens(user_text))
    it=len(words&_ITALIAN_WORDS);en=len(words&_ENGLISH_WORDS)
    if it>en and it>0:return "Italian"
    if en>it and en>0:return "English"
    return "the same language as the user"


def _language_error(user_text: str, reply_text: str) -> str | None:
    target=_reply_language(user_text)
    words=_tokens(reply_text)
    if not words or target not in {"Italian","English"}:return None
    it=sum(1 for word in words if word in _ITALIAN_RESPONSE_WORDS)
    en=sum(1 for word in words if word in _ENGLISH_RESPONSE_WORDS)
    # Only reject a clear lexical drift. Proper nouns and technical English terms
    # do not trigger this guard unless ordinary words overwhelmingly switch language.
    if target=="Italian" and en>=3 and en>it+1:return "reply language differs from the human turn: expected Italian"
    if target=="English" and it>=3 and it>en+1:return "reply language differs from the human turn: expected English"
    return None


def _compact_generation_contract(contract:dict[str,Any],interaction:dict[str,Any],user_text:str)->dict[str,Any]:
    fmt=dict((contract or {}).get("format") or {})
    content=dict((contract or {}).get("content") or {})
    regulation=dict((contract or {}).get("regulation") or {})
    profile=dict(interaction.get("profile") or {})
    identity=dict(interaction.get("identity") or {})
    kept_content={k:v for k,v in content.items() if k in {"assertable","tentative","interpretive_hypotheses","conflicts","authorized_directives"} and v}
    return {
        "surface_a_contract":{
            "format":{
                "min_words":int(fmt.get("min_words") or 5),
                "max_words":int(fmt.get("max_words") or 500),
                "max_paragraphs":int(fmt.get("max_paragraphs") or 4),
                "style":str(fmt.get("style") or "simple natural colloquial humanistic-formal prose"),
                "stance":str(fmt.get("stance") or "careful and plain"),
                "language":_reply_language(user_text),
                "headings":False,"lists":False,"tables":False,"code_blocks":False,
            },
            "content":kept_content,
            "regulation":{
                "mode":regulation.get("mode"),
                "must_abstain_or_review":bool(regulation.get("must_abstain_or_review",False)),
                "material_action":regulation.get("material_action"),
            },
        },
        "interaction_contract":{
            "kind":profile.get("kind"),
            "word_budget":int(profile.get("word_budget") or 160),
            "identity_first":bool(profile.get("identity_first",False)),
            "interface_identity":"iKant",
            "engine_label":identity.get("engine_label"),
            "engine_disclosure":bool(profile.get("engine_disclosure",False)),
        },
    }


class LocalModelBroker:
    """Zero-authority adapter for an iKant-owned or explicitly supplied loopback model endpoint."""

    def __init__(
        self,
        endpoint: str | None,
        *,
        model: str = "Qwen3.5-0.8B",
        timeout: float = 45.0,
        opener: Callable[..., Any] = urlopen,
        api_key: str | None = None,
        runtime_binding_digest: str | None = None,
        managed_runtime: bool = False,
    ):
        self.endpoint = None if not endpoint else require_loopback_url(str(endpoint))
        self.model = str(model or "Qwen3.5-0.8B")
        self.timeout = float(timeout)
        self.opener = opener
        self._api_key = str(api_key) if api_key else None
        self.runtime_binding_digest = str(runtime_binding_digest) if runtime_binding_digest else None
        self.managed_runtime = bool(managed_runtime)
        self.last_completion_metrics:dict[str,Any]={}
        self._last_request_ms=0.0
        if self.managed_runtime and (not self.endpoint or not self._api_key or not self.runtime_binding_digest):
            raise LocalModelError("managed model broker requires endpoint, private key and runtime binding")

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["Authorization"] = "Bearer " + self._api_key
        return headers

    def status(self) -> dict[str, Any]:
        out = {
            "schema": MODEL_BROKER_SCHEMA,
            "configured": self.configured,
            "endpoint_scope": "LOOPBACK_ONLY" if self.configured else "DISABLED",
            "model": self.model,
            "managed_runtime": self.managed_runtime,
            "api_key_exposed": False,
            "tool_calls_accepted": False,
            "model_output_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        if self.managed_runtime:
            out["runtime_binding_digest"] = self.runtime_binding_digest
        return out

    def _models_url(self) -> str:
        if not self.endpoint:
            raise LocalModelError("local model endpoint not configured")
        parsed = urlparse(self.endpoint)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if "/v1/" in parsed.path:
            return base + "/v1/models"
        return base + "/models"

    def health(self) -> bool:
        if not self.endpoint:
            return False
        req = Request(self._models_url(), method="GET", headers=self._headers())
        try:
            with self.opener(req, timeout=min(self.timeout, 3.0)) as response:
                return 200 <= int(getattr(response, "status", 200)) < 300
        except Exception:
            return False

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            raise LocalModelError("local model endpoint not configured")
        req = Request(self.endpoint,data=json.dumps(payload,ensure_ascii=False,separators=(",", ":")).encode("utf-8"),method="POST",headers=self._headers(json_body=True))
        started=time.perf_counter()
        try:
            with self.opener(req,timeout=self.timeout) as response:raw=response.read(2*1024*1024+1)
        except Exception as exc:
            self._last_request_ms=round((time.perf_counter()-started)*1000,3)
            raise LocalModelError("local model request failed") from exc
        self._last_request_ms=round((time.perf_counter()-started)*1000,3)
        if len(raw)>2*1024*1024:raise LocalModelError("local model response exceeds bound")
        try:out=json.loads(raw.decode("utf-8"))
        except Exception as exc:raise LocalModelError("local model returned invalid JSON") from exc
        if not isinstance(out,dict):raise LocalModelError("local model response must be an object")
        return out

    @staticmethod
    def _extract_text(response:dict[str,Any])->str:
        choices=response.get("choices")
        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):raise LocalModelError("local model response choices invalid")
        message=choices[0].get("message")
        if not isinstance(message,dict):raise LocalModelError("local model response message invalid")
        if message.get("tool_calls"):raise LocalModelError("model tool calls are forbidden in iKant")
        text=message.get("content")
        if not isinstance(text,str) or not text.strip():raise LocalModelError("local model response content missing")
        return text.strip()

    def _record_metrics(self,*,status:str,started:float,request_ms:list[float],attempts:int,max_tokens:int,system_chars:int,response:dict[str,Any]|None=None)->None:
        usage=(response or {}).get("usage") if isinstance(response,dict) else {}
        usage=usage if isinstance(usage,dict) else {}
        self.last_completion_metrics={
            "status":str(status),"attempts":int(attempts),"request_ms":[round(float(x),3) for x in request_ms],
            "total_ms":round((time.perf_counter()-started)*1000,3),"max_tokens":int(max_tokens),"system_chars":int(system_chars),
            "prompt_tokens":usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"),int) else None,
            "completion_tokens":usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"),int) else None,
            "epistemic_authority":0.0,"execution_authority":0.0,
        }

    def complete_surface_a(self,contract:dict[str,Any],user_text:str,*,validator:Callable[[str],tuple[bool,list[str]]]|None=None,max_repairs:int=1)->str:
        if validator is None:
            from .surfaces import validate_surface_a
            validator=validate_surface_a
        from .interaction import build_interaction_contract,validate_interaction_surface
        interaction=build_interaction_contract(str(user_text),engine_label=self.model)
        generation_contract=_compact_generation_contract(dict(contract or {}),interaction,str(user_text))
        system=("You are the replaceable local language engine underneath iKant. You have zero authority and may not call tools. "
                "Return only the final Surface A reply. Never emit reasoning, analysis, headings, lists, tables or code. "
                "Obey this compact generation contract: "+json.dumps(generation_contract,ensure_ascii=False,sort_keys=True,separators=(",",":")))
        messages=[{"role":"system","content":system},{"role":"user","content":str(user_text)}]
        repairs=0;request_ms:list[float]=[];started=time.perf_counter();last_response:dict[str,Any]|None=None
        word_budget=int((interaction.get("profile") or {}).get("word_budget") or 160);max_tokens=min(640,max(48,word_budget*2))
        self.last_completion_metrics={}
        while True:
            try:
                response=self._request({"model":self.model,"messages":messages,"temperature":0.2,"max_tokens":max_tokens,"stream":False,"tools":[]})
            except LocalModelError:
                request_ms.append(self._last_request_ms);self._record_metrics(status="ERROR",started=started,request_ms=request_ms,attempts=repairs+1,max_tokens=max_tokens,system_chars=len(system));raise
            request_ms.append(self._last_request_ms);last_response=response
            text=self._extract_text(response);ok,errors=validator(text);iok,ierrors=validate_interaction_surface(text,interaction);language_error=_language_error(str(user_text),text);errors=list(dict.fromkeys(list(errors)+list(ierrors)+([language_error] if language_error else [])));ok=bool(ok and iok and not language_error)
            if ok:
                self._record_metrics(status="VALIDATED",started=started,request_ms=request_ms,attempts=repairs+1,max_tokens=max_tokens,system_chars=len(system),response=response);return text
            if repairs>=int(max_repairs):
                self._record_metrics(status="INVALID",started=started,request_ms=request_ms,attempts=repairs+1,max_tokens=max_tokens,system_chars=len(system),response=last_response);raise LocalModelError("local model failed Surface A validation: "+"; ".join(errors))
            repairs+=1;messages.append({"role":"assistant","content":text});messages.append({"role":"user","content":"Repair only the final reply. Same language as my input. No explanation. Fix: "+"; ".join(errors)})
