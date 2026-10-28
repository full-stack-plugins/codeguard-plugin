#!/usr/bin/env python3
"""Explicit source-built candidate assembly; never activates the default lock."""
import argparse
import json
import os
import pathlib
import platform
import subprocess
import tempfile
from candidate_runtime_support import install_archive, regular_bytes, sha256, validate_version, verify_files

PLUGIN = pathlib.Path(__file__).resolve().parents[1]
SOURCE = 'cc7b907f6ba22b61bc19e5371df31d03ee72f452'
VERSION = '0.1.4'

def run(argv, *, cwd=PLUGIN, input=None, expected=(0,), env=None):
    result = subprocess.run([str(x) for x in argv],cwd=cwd,input=input,env=env,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,encoding='utf-8')
    if result.returncode not in expected:
        raise AssertionError(f'{argv[0]} returned {result.returncode}: {result.stderr[-2048:]} {result.stdout[-1024:]}')
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--engine-source',type=pathlib.Path,required=True)
    parser.add_argument('--package-receipt',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args()
    engine=args.engine_source.resolve()
    assert run(['git','rev-parse','HEAD'],cwd=engine).stdout.strip()==SOURCE, 'engine source commit mismatch'
    run(['git','diff','HEAD','--exit-code'],cwd=engine)
    original_lock=regular_bytes(PLUGIN/'runtime/codeguard.lock.json',32*1024)
    receipt=json.loads(args.package_receipt.read_text(encoding='utf-8'))
    assert receipt['status']=='passed' and receipt['identity']['build_identity']==SOURCE
    assert receipt['identity']['cli_version']==VERSION
    target=receipt['identity']['target']
    node=json.loads(run(['node','-p','JSON.stringify({os:process.platform,cpu:process.arch})']).stdout)
    assert receipt['platform']==node['os'] and receipt['architecture']==node['cpu']
    manifest=json.loads((engine/'grammars/manifest.json').read_text(encoding='utf-8'))
    licenses={manifest['codegraph_license']:manifest['codegraph_license_sha256']}
    licenses.update({asset['license']:asset['license_sha256'] for asset in manifest['assets']})
    lock={'schema_version':'candidate-test-1','package':'@full-stack-plugins/codeguard','version':VERSION,
          'source_commit':SOURCE,'platform':target,'os':node['os'],'cpu':node['cpu'],
          'binary':'native/codeguard.exe' if node['os']=='win32' else 'native/codeguard',
          'tarball_sha256':receipt['tarball_sha256'],'binary_sha256':receipt['native_sha256'],
          'grammar_licenses':licenses}
    archive=pathlib.Path(receipt['tarball']).resolve()
    provenance_paths=['hooks/rust_runtime_adapter.cjs','hooks/rust_runtime_dispatch.cjs',
                      'runtime/codeguard_runtime.cjs','runtime/codeguard.lock.json',
                      'tests/candidate_runtime_support.py','tests/candidate_adapter_driver.cjs',
                      'tests/acceptance_candidate_runtime.py']
    source_changes=run(['git','diff','HEAD','--name-only']).stdout.splitlines()
    source_untracked=run(['git','ls-files','--others','--exclude-standard','hooks','runtime','tests','.github/workflows']).stdout.splitlines()
    evidence={'schema_version':'1.0.0','plugin_commit':run(['git','rev-parse','HEAD']).stdout.strip(),
              'plugin_worktree_clean':not (source_changes or source_untracked),
              'plugin_source_changes':source_changes,'plugin_untracked_sources':source_untracked,
              'plugin_files_sha256':{name:sha256((PLUGIN/name).read_bytes()) for name in provenance_paths},
              'platform':platform.platform(),'machine':platform.machine(),'candidate_lock':lock,
              'default_lock_sha256':sha256(original_lock),'default_runtime_activated':False,
              'actual_host_hook_triggered':False,'default_runtime_chain_verified':False,'events':{}}
    with tempfile.TemporaryDirectory(prefix='codeguard-candidate-profile-') as temp:
        profile=pathlib.Path(temp).resolve()
        installed=install_archive(archive,lock,profile/'installed')
        binary=verify_files(installed,lock)
        version=json.loads(run([binary,'--version','--format=json']).stdout)
        validate_version(version,lock)
        # A recorded source mismatch must not be accepted even with matching bytes.
        try: validate_version(version,{**lock,'source_commit':'0'*40})
        except ValueError: pass
        else: raise AssertionError('source mismatch accepted')
        inventory=json.loads(run([binary,'grammar','status','--format=json'],expected=(3,)).stdout)
        assert inventory['candidate_count']==32 and inventory['released_count']==0
        assert inventory['delivery_decision']=='not_evaluated'
        expected_assets={asset['language']:asset['sha256'] for asset in manifest['assets']}
        assert {asset['language']:asset['candidate_wasm_sha256'] for asset in inventory['assets']}==expected_assets
        project=profile/'project';project.mkdir()
        source=project/'sample.zig';source.write_text('const Empty = struct {};\n',encoding='utf-8')
        probe=json.loads(run([binary,'grammar','probe','zig',source,'--format=json'],expected=(3,)).stdout)
        assert probe['source_sha256']==sha256(source.read_bytes()) and probe['grammar_sha256']==expected_assets['zig']
        assert probe['precheck']['checked_files']==1 and probe['grammar_qualified'] is False
        assert probe['delivery_decision']=='not_evaluated'
        evidence['grammar_probe']=probe
        # Adapter transport exercises real engine responses, not Codex Hook activation.
        event_names={'session-start':'SessionStart','user-prompt-submit':'UserPromptSubmit',
                     'post-tool-use':'PostToolUse','post-tool-use-failure':'PostToolUseFailure','stop':'Stop'}
        for event, name in event_names.items():
            verify_files(installed,lock)
            payload={'hook_event_name':name,'cwd':str(project),'prompt':'Explain this temporary example.',
                     'tool_name':'Write','tool_input':{'file_path':str(source),'content':source.read_text(encoding='utf-8')},
                     'tool_response':{'success':event!='post-tool-use-failure'}}
            result=run(['node',PLUGIN/'tests/candidate_adapter_driver.cjs',binary,project,event],input=json.dumps(payload))
            evidence['events'][event]=json.loads(result.stdout)
        # Default dispatch must still require its original public lock; the private
        # candidate cannot become active merely because this harness installed it.
        env={**os.environ,'CODEGUARD_RUNTIME_CACHE':str(profile/'default-cache'),'CLAUDE_PROJECT_DIR':str(project)}
        default=run(['node',PLUGIN/'hooks/rust_runtime_dispatch.cjs','session-start'],
                    input=json.dumps({'hook_event_name':'SessionStart','cwd':str(project)}),env=env)
        message=json.loads(default.stdout)['hookSpecificOutput']['additionalContext']
        assert '未完成' in message and '未运行' in message
        assert not (profile/'default-cache/active.json').exists()
        evidence['default_dispatch']='incomplete_without_candidate_activation'
        # Each real installed object is checked again before candidate execution.
        with binary.open('ab') as output: output.write(b'changed')
        try: verify_files(installed,lock)
        except ValueError as error: assert str(error)=='binary_digest_mismatch'
        else: raise AssertionError('binary tampering accepted')
        evidence['negative_cases']=['wrong_source_commit','mutated_installed_binary','default_lock_not_overridden']
    assert regular_bytes(PLUGIN/'runtime/codeguard.lock.json',32*1024)==original_lock
    evidence['status']='passed'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'passed','output':str(args.output.resolve()),'source_commit':SOURCE,'target':target,
                      'default_runtime_chain_verified':False,'actual_host_hook_triggered':False}))

if __name__=='__main__': main()
