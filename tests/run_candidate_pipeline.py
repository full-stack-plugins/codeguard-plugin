#!/usr/bin/env python3
"""CI driver preserving actual subprocess results and bounded failure evidence."""
import json
import os
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

plugin=pathlib.Path(__file__).resolve().parents[1]
engine=pathlib.Path(sys.argv[1]).resolve()
evidence=plugin/'candidate-evidence'
evidence.mkdir(exist_ok=True)
source='cc7b907f6ba22b61bc19e5371df31d03ee72f452'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=engine,text=True).strip()==source

def execute(label,command,cwd,env=None):
    log=evidence/(label+'.log')
    with log.open('wb') as output:
        result=subprocess.run(command,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:
        tail=log.read_bytes()[-2048:].decode('utf-8','replace')
        escaped=tail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print(f'::error title=Candidate {label} failed::{escaped}',flush=True)
        raise SystemExit(result.returncode)
    print(f'{label}: passed ({log})',flush=True)

execute('build',['cargo','build','--locked','-p','codeguard-cli','--features','wasm-precheck'],engine,
        {**os.environ,'CODEGUARD_BUILD_SHA':source})
binary=engine/'target/debug'/('codeguard.exe' if os.name=='nt' else 'codeguard')
# The engine harness tests real offline npm installation and emits a digest receipt.
receipt=evidence/'package-receipt.json'
with receipt.open('wb') as output, (evidence/'package.log').open('wb') as errors:
    result=subprocess.run(['node','tests/npm_candidate_install.mjs',str(binary)],cwd=engine,stdout=output,stderr=errors)
if result.returncode:
    tail=(evidence/'package.log').read_bytes()[-2048:].decode('utf-8','replace')
    print('::error title=Candidate package failed::'+tail.replace('%','%25').replace('\r','%0D').replace('\n','%0A'),flush=True)
    raise SystemExit(result.returncode)
json.loads(receipt.read_text(encoding='utf-8'))
execute('plugin-adapter',[sys.executable,'tests/acceptance_candidate_runtime.py','--engine-source',str(engine),
        '--package-receipt',str(receipt),'--output',str(evidence/'plugin-candidate.json')],plugin)
