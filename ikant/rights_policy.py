from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib, json
from pathlib import Path
from typing import Any

RIGHTS_SCHEMA = 'ikant-rights-policy/v0.12-test'
RIGHTS_VERSION = '0.12.0'
RIGHTS_PATH = 'RIGHTS.json'
RIGHTS_NOTICE_PATH = 'RIGHTS.md'
REPOSITORY = 'Luke883i/ikant'
RIGHTSHOLDER = 'Luke883i'

class AccessMode(str, Enum):
    HUMAN_MANUAL='HUMAN_MANUAL';CONFORMANCE_MATERIALIZATION='CONFORMANCE_MATERIALIZATION';AI_ASSISTED_STUDY='AI_ASSISTED_STUDY';AUTOMATED_REPOSITORY_ANALYSIS='AUTOMATED_REPOSITORY_ANALYSIS';MODEL_TRAINING='MODEL_TRAINING';OFFICIAL_IKANT='OFFICIAL_IKANT'
class ExternalBasis(str, Enum):
    NONE='NONE';PLATFORM_DIRECT_GRANT='PLATFORM_DIRECT_GRANT';STATUTORY_EXCEPTION='STATUTORY_EXCEPTION';SEPARATE_LICENSE='SEPARATE_LICENSE'
@dataclass(frozen=True)
class RightsDecision:
    schema:str;mode:str;code:str;owner_authorization:str;ikant_conformance:str;legal_status:str;epistemic_authority:bool;reason:str

def _decision(mode,code,owner,conformance,reason):
    return RightsDecision('ikant-rights-decision/v0.12-test',mode.value,code,owner,conformance,'NOT_ADJUDICATED',False,reason)

def decide_owner_authorization(mode:AccessMode|str,*,accepted_current_terms=False,clean_admission=False,remediated_admission=False,technical_conformance=False,external_basis:ExternalBasis|str=ExternalBasis.NONE)->RightsDecision:
    mode=AccessMode(mode);external_basis=ExternalBasis(external_basis)
    if mode is AccessMode.HUMAN_MANUAL:return _decision(mode,'HUMAN_MANUAL_OUTSIDE_AI_GATE','NOT_REQUIRED_BY_IKANT_POLICY','NOT_APPLICABLE','Manual human viewing or study is outside the iKant AI-admission gate; this creates no additional copyright licence.')
    if external_basis is not ExternalBasis.NONE:return _decision(mode,'EXTERNAL_BASIS_NOT_ADJUDICATED','NOT_GRANTED_BY_IKANT','NOT_CONFORMING','An independently asserted platform grant, statutory exception or separate licence must be assessed outside iKant and does not establish iKant conformance.')
    if mode is AccessMode.CONFORMANCE_MATERIALIZATION:
        if accepted_current_terms and clean_admission:return _decision(mode,'MATERIALIZATION_FOR_CONFORMANCE_ALLOWED','GRANTED_FOR_CONFORMANCE_BOOTSTRAP','PENDING','Current digest-bound acceptance and a clean admission context authorize materialization only to verify or establish a conforming iKant runtime.')
        return _decision(mode,'OWNER_AUTHORIZATION_RESERVED','RESERVED','NOT_CONFORMING','Materialization for iKant conformance requires current digest-bound acceptance in a clean admission context.')
    if mode is AccessMode.MODEL_TRAINING:return _decision(mode,'SEPARATE_LICENSE_REQUIRED','SEPARATE_LICENSE_REQUIRED','NOT_CONFORMING','The iKant access contract does not itself grant owner permission for model training or training-dataset construction.')
    if mode in {AccessMode.AI_ASSISTED_STUDY,AccessMode.AUTOMATED_REPOSITORY_ANALYSIS}:
        if accepted_current_terms and clean_admission:return _decision(mode,'OWNER_AUTHORIZED_CHAT_STUDY','GRANTED_UNDER_CURRENT_IKANT_TERMS','NOT_REQUIRED_FOR_CHAT_STUDY','Digest-bound current-session acceptance in a clean admission context authorizes substantive AI study in that chat/session without requiring a local ACTIVE runtime.')
        if accepted_current_terms and remediated_admission:return _decision(mode,'OWNER_AUTHORIZED_REMEDIATED_CHAT_STUDY','GRANTED_PROSPECTIVELY_AFTER_REMEDIATION','NOT_CONFORMING','The prior pre-acceptance access remains a recorded non-retroactive breach; re-presented terms plus exact current-session acceptance authorize only prospective same-session study. A fresh clean context is still required for conforming runtime materialization.')
        return _decision(mode,'OWNER_AUTHORIZATION_RESERVED','RESERVED','NOT_CONFORMING','Substantive AI study requires current digest-bound acceptance in either a clean admission context or the explicit remediated chat-study state.')
    if mode is AccessMode.OFFICIAL_IKANT:
        if accepted_current_terms and clean_admission and technical_conformance:return _decision(mode,'OWNER_AUTHORIZED_CONFORMING_IKANT','GRANTED_UNDER_CURRENT_IKANT_TERMS','CONFORMING','Official/conforming iKant requires current acceptance, clean admission and current technical host/runtime/transport conformance.')
        return _decision(mode,'OWNER_AUTHORIZATION_RESERVED','RESERVED','NOT_CONFORMING','Official/conforming iKant remains reserved unless current terms, clean admission and technical conformance all hold.')
    raise AssertionError(mode)

def policy_manifest()->dict[str,Any]:
    return {
      'schema':RIGHTS_SCHEMA,'version':RIGHTS_VERSION,'repository':REPOSITORY,'rightsholder':RIGHTSHOLDER,
      'tdm':{'reservation':1,'express_reservation':True,'owner_permission_for_ai_study_requires_conforming_ikant':False,'owner_permission_for_ai_study_requires_current_acceptance':True,'model_training_requires_separate_license':True,'legal_anchors':['Directive (EU) 2019/790 Article 4(3)','Italian Law 22 April 1941 no. 633 Article 70-quater','Regulation (EU) 2024/1689 Article 53(1)(c)'],'repository_signal':RIGHTS_PATH,'origin_protocol_note':'When the rightsholder controls the origin server, publish an appropriate machine-readable reservation such as robots.txt, a TDMRep signal, or another legally appropriate protocol. A file inside a GitHub repository does not control github.com origin headers or /.well-known paths.'},
      'scope':{'public_visibility_is_not_owner_ai_authorization':True,'manual_human_review_requires_ikant_acceptance':False,'conformance_materialization_requires_current_acceptance':True,'substantive_ai_study_requires_current_acceptance':True,'substantive_ai_study_requires_clean_or_remediated_admission':True,'substantive_ai_study_requires_technical_conformance':False,'remediated_chat_study_allowed':True,'remediated_chat_study_is_prospective_only':True,'remediated_context_may_claim_ikant_conformance':False,'external_legal_bases_not_adjudicated':True,'platform_direct_grants_not_overridden':True,'mandatory_exceptions_not_overridden':True,'rights_control_is_not_epistemic_evidence':True},
      'hierarchy':['higher_priority_system_safety_law','mandatory_law_and_independently_valid_external_legal_bases','direct_platform_grants_within_their_scope','rightsholder_copyright_and_express_tdm_reservation','digest_bound_ikant_owner_authorization','runtime_admission_transport_and_egress_conformance','control_and_audit_projections_with_zero_epistemic_authority'],
      'authorization':{'acceptance_phrase':'I ACCEPT','contract_path':'IKANT_ACCESS_CONTRACT.md','acceptance_binding':'exact current-session human message bound to the presented contract digest','materialization_purpose':'establish_or_verify_conforming_ikant_only','substantive_ai_study_channel':'digest_bound_chat_session_or_remediated_chat_session','official_ikant_channel':'clean_admission_plus_technical_conformance','model_training_channel':'separate_license_required'}
    }

def canonical_policy_bytes(payload=None)->bytes:
    payload=policy_manifest() if payload is None else payload;return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def policy_sha256(payload=None)->str:return hashlib.sha256(canonical_policy_bytes(payload)).hexdigest()

def _contract_header(contract_text):
    lines=contract_text.replace('\r\n','\n').splitlines()
    if not lines or lines[0].strip()!='---':return {}
    out={}
    for line in lines[1:]:
        if line.strip()=='---':break
        if ':' in line:
            key,value=line.split(':',1);out[key.strip()]=value.strip()
    return out

def validate_repository_rights(root,contract_text):
    root=Path(root);errors=[]
    try:payload=json.loads((root/RIGHTS_PATH).read_text(encoding='utf-8'))
    except Exception:payload={};errors.append('rights policy unreadable')
    expected=policy_manifest()
    if payload!=expected:errors.append('rights policy manifest mismatch')
    if not (root/RIGHTS_NOTICE_PATH).is_file():errors.append('rights notice missing')
    expected_binding={'schema':RIGHTS_SCHEMA,'path':RIGHTS_PATH,'notice_path':RIGHTS_NOTICE_PATH,'sha256':policy_sha256(expected),'tdm_rights_reserved':True,'manual_human_review_requires_ikant_acceptance':False,'substantive_ai_study_requires_conforming_ikant':False,'remediated_chat_study_allowed':True,'model_training_requires_separate_license':True,'external_legal_bases_not_adjudicated':True}
    for manifest_name in ('ADMISSION.json','BOOTSTRAP.json'):
        try:manifest=json.loads((root/manifest_name).read_text(encoding='utf-8'))
        except Exception:errors.append(f'{manifest_name} unreadable for rights binding');continue
        if manifest.get('rights_policy')!=expected_binding:errors.append(f'{manifest_name} rights policy binding mismatch')
    header=_contract_header(contract_text)
    required={'rights_policy_schema':RIGHTS_SCHEMA,'rights_policy_path':RIGHTS_PATH,'rights_notice_path':RIGHTS_NOTICE_PATH,'tdm_rights_reserved':'true','ai_assisted_owner_authorization_requires_conforming_ikant':'false','chat_study_requires_current_acceptance':'true','remediated_chat_study_allowed':'true','official_ikant_requires_technical_conformance':'true','manual_human_review_requires_acceptance':'false','external_legal_bases_not_adjudicated':'true','rights_policy_sha256':policy_sha256(expected)}
    for key,value in required.items():
        if header.get(key)!=value:errors.append(f'contract header {key} mismatch')
    return not errors,list(dict.fromkeys(errors))

def semantic_access_slice(mode:AccessMode|str,**kwargs):
    decision=decide_owner_authorization(mode,**kwargs);return {'schema':'ikant-semantic-access-slice/v0.12-test','control':asdict(decision),'epistemic_boundary':{'authority':0.0,'may_create_external_evidence':False,'may_corroborate_claims':False,'may_relax_practical_or_horizon_blocks':False}}
