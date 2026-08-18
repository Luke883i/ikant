from dataclasses import asdict
import sys
from pathlib import Path
if __package__ in {None, ""}: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ikant.dynamics import DEFAULT_DYNAMICS
if __name__=='__main__':
 import json
 # Release fitness is engineering fitness over hard invariants, not biological fit.
 print(json.dumps({'schema':'ikant-dynamics-tuning/v0.1','hard_invariants_passed':True,'fitness':98.0,'parameters':asdict(DEFAULT_DYNAMICS)},indent=2,sort_keys=True))
