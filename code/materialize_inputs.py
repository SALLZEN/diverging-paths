"""Restore exact frozen tables from lossless transport parts."""
from pathlib import Path
import hashlib,json,os,shutil
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def materialize(root):
    root=Path(root).resolve();data=root/'data'
    spec=json.loads((data/'INPUT-STORAGE.json').read_text())
    restored=[]
    for name,entry in spec['tables'].items():
        target=data/name
        if target.exists():
            if target.stat().st_size!=entry['bytes'] or sha256(target)!=entry['sha256']:
                raise ValueError('Existing input has a different identity; preserve it and use a clean checkout: '+name)
            continue
        temporary=target.with_suffix(target.suffix+'.assembling')
        try:
            with temporary.open('wb') as output:
                for part in entry['parts']:
                    path=data/part['file']
                    if path.stat().st_size!=part['bytes'] or sha256(path)!=part['sha256']:
                        raise ValueError('Transport-part identity differs: '+part['file'])
                    with path.open('rb') as source:shutil.copyfileobj(source,output)
            if temporary.stat().st_size!=entry['bytes'] or sha256(temporary)!=entry['sha256']:
                raise ValueError('Restored table identity differs: '+name)
            os.replace(temporary,target);restored.append(name)
        finally:
            if temporary.exists():temporary.unlink()
    return restored
if __name__=='__main__':
    print(json.dumps({'restored':materialize(Path(__file__).resolve().parents[1])},indent=2))
