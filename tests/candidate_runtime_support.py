"""Test-only explicit candidate assembly. Not a runtime manager or default override."""
import hashlib
import json
import pathlib
import re
import shutil
import stat
import tarfile

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_BINARY = 256 * 1024 * 1024

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def validate_lock(lock):
    platforms = {'linux_x86_64': ('linux', 'x64', 'native/codeguard'),
                 'macos_arm64': ('darwin', 'arm64', 'native/codeguard'),
                 'windows_x86_64': ('win32', 'x64', 'native/codeguard.exe')}
    if (lock.get('schema_version') != 'candidate-test-1'
        or lock.get('package') != '@full-stack-plugins/codeguard'
        or not re.fullmatch(r'\d+\.\d+\.\d+', lock.get('version', ''))
        or not re.fullmatch(r'[a-f0-9]{40}', lock.get('source_commit', ''))
        or platforms.get(lock.get('platform')) != (lock.get('os'), lock.get('cpu'), lock.get('binary'))
        or any(not re.fullmatch(r'[a-f0-9]{64}', lock.get(key, '')) for key in ['tarball_sha256', 'binary_sha256'])):
        raise ValueError('candidate_lock_invalid')
    licenses = lock.get('grammar_licenses')
    if (not isinstance(licenses, dict) or len(licenses) != 32 or 'LICENSE.codegraph' not in licenses
        or any(not re.fullmatch(r'(?:LICENSE\.codegraph|[a-z0-9_-]+/LICENSE)', name)
               or not re.fullmatch(r'[a-f0-9]{64}', digest) for name, digest in licenses.items())):
        raise ValueError('candidate_license_lock_invalid')

def validate_version(version, lock):
    if (version.get('report_type') != 'version' or version.get('cli_version') != lock['version']
        or version.get('target') != lock['platform'] or version.get('build_identity') != lock['source_commit']
        or version.get('check_protocol_major') != 1):
        raise ValueError('binary_identity_mismatch')

def regular_bytes(path, limit):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
        raise ValueError('candidate_file_unsafe')
    return path.read_bytes()

def verify_files(root, lock):
    validate_lock(lock)
    manifest = json.loads(regular_bytes(root/'package.json', 16*1024))
    if (manifest.get('name') != lock['package'] or manifest.get('version') != lock['version']
        or manifest.get('private') is not True or manifest.get('os') != [lock['os']]
        or manifest.get('cpu') != [lock['cpu']] or manifest.get('bin') != {'codeguard':'./codeguard.cjs'}):
        raise ValueError('package_identity_mismatch')
    binary = root/lock['binary']
    if sha256(regular_bytes(binary,MAX_BINARY)) != lock['binary_sha256']:
        raise ValueError('binary_digest_mismatch')
    for name, expected in lock['grammar_licenses'].items():
        if sha256(regular_bytes(root/'grammar-licenses'/name,16*1024)) != expected:
            raise ValueError('license_digest_mismatch')
    return binary

def install_archive(archive, lock, destination):
    validate_lock(lock)
    if sha256(regular_bytes(archive,MAX_ARCHIVE)) != lock['tarball_sha256']:
        raise ValueError('tarball_digest_mismatch')
    expected = {'package/package.json', 'package/codeguard.cjs', 'package/'+lock['binary']}
    expected.update('package/grammar-licenses/'+name for name in lock['grammar_licenses'])
    with tarfile.open(archive, 'r:gz') as package:
        members = package.getmembers()
        if (len(members) != len(expected) or {m.name for m in members} != expected
            or any(not m.isfile() or m.size < 0 or m.size > (MAX_BINARY if m.name == 'package/'+lock['binary'] else 16*1024) for m in members)):
            raise ValueError('archive_members_invalid')
        destination.mkdir(mode=0o700)  # fresh temporary test profile only
        try:
            for member in members:
                relative = pathlib.PurePosixPath(member.name).relative_to('package')
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with target.open('xb') as output, package.extractfile(member) as source:
                    shutil.copyfileobj(source,output)
                if member.name == 'package/'+lock['binary']:
                    target.chmod(0o700)
            verify_files(destination,lock)
            return destination
        except Exception:
            shutil.rmtree(destination)
            raise
