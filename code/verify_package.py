"""Check fixed release files without modifying data or interpreting annotations."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'release_manifest.json').read_text())
checked=0
for name,entry in manifest['files'].items():
    path=root/name
    if not path.is_file():raise SystemExit('Missing release file: '+name)
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    if path.stat().st_size!=entry['bytes'] or h.hexdigest()!=entry['sha256']:
        raise SystemExit('Release file identity differs: '+name)
    checked+=1
print(json.dumps({'status':'PASS','version':manifest['version'],'files_verified':checked,'scope':'Byte integrity only'},indent=2))
