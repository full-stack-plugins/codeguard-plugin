"""Candidate-only archive contract; never touches the default runtime/cache."""
import hashlib
import io
import json
import pathlib
import tarfile
import tempfile
import unittest
from candidate_runtime_support import install_archive, verify_files, validate_version

class CandidateArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cg-candidate-contract-')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.files = {'package/package.json': json.dumps({'name':'@full-stack-plugins/codeguard','version':'0.1.4','private':True,'os':['linux'],'cpu':['x64'],'bin':{'codeguard':'./codeguard.cjs'}}).encode(),
                      'package/codeguard.cjs':b'// wrapper', 'package/native/codeguard':b'candidate bytes'}
        self.licenses = {'LICENSE.codegraph':hashlib.sha256(b'license').hexdigest()}
        self.licenses.update({f'lang{i}/LICENSE':hashlib.sha256(b'license').hexdigest() for i in range(31)})
        self.files.update({f'package/grammar-licenses/{name}':b'license' for name in self.licenses})
        self.lock = {'schema_version':'candidate-test-1','package':'@full-stack-plugins/codeguard','version':'0.1.4','source_commit':'a'*40,'platform':'linux_x86_64','os':'linux','cpu':'x64','binary':'native/codeguard','binary_sha256':hashlib.sha256(b'candidate bytes').hexdigest(),'grammar_licenses':self.licenses}
    def archive(self, extra=None):
        target = self.root/'candidate.tgz'
        with tarfile.open(target,'w:gz') as tf:
            for name, data in self.files.items():
                entry = tarfile.TarInfo(name);entry.size=len(data)
                tf.addfile(entry,io.BytesIO(data))
            if extra: tf.addfile(extra)
        self.lock['tarball_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        return target
    def test_digest_failure_writes_no_installation(self):
        archive=self.archive();archive.write_bytes(archive.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'tarball_digest_mismatch'): install_archive(archive,self.lock,self.root/'installed')
        self.assertFalse((self.root/'installed').exists())
    def test_links_and_extra_members_rejected_before_extraction(self):
        extra=tarfile.TarInfo('package/escape');extra.type=tarfile.SYMTYPE;extra.linkname='../outside'
        with self.assertRaisesRegex(ValueError,'archive_members_invalid'): install_archive(self.archive(extra),self.lock,self.root/'installed')
        self.assertFalse((self.root/'installed').exists())
    def test_install_and_binary_license_tampering(self):
        installed=install_archive(self.archive(),self.lock,self.root/'installed')
        binary=verify_files(installed,self.lock)
        binary.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'binary_digest_mismatch'):verify_files(installed,self.lock)
        binary.write_bytes(b'candidate bytes')
        (installed/'grammar-licenses/LICENSE.codegraph').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'license_digest_mismatch'):verify_files(installed,self.lock)
    def test_commit_version_platform_protocol_must_all_match(self):
        version={'report_type':'version','cli_version':'0.1.4','target':'linux_x86_64','build_identity':'a'*40,'check_protocol_major':1}
        validate_version(version,self.lock)
        for key in ['cli_version','target','build_identity','check_protocol_major']:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'binary_identity_mismatch'):
                validate_version({**version,key:'wrong'},self.lock)
if __name__=='__main__': unittest.main()
