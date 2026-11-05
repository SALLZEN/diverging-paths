#!/usr/bin/env python3
from pathlib import Path
import sys,os
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'code/modules'))
from workflow import run
print(run(root,render=os.environ.get('DAMADI_ANALYSIS_ONLY')!='1')['status'])
