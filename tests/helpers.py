from pathlib import Path
from ikant.admission import issue_receipt,save_receipt,probe,save_probe
from ikant.runtime import Runtime
from ikant.dynamics import DynamicsParameters
def active_runtime(tmp:Path,*,durable=False,params=None):
    root=tmp/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture');contract='fixture';(root/'IKANT_ACCESS_CONTRACT.md').write_text(contract);s=root/'.ikant';save_receipt(s,issue_receipt(contract,'I ACCEPT'));p=probe(root,s,contract);save_probe(s,p);return Runtime.initialize(s,contract,durable=durable,params=params or DynamicsParameters())
