#!/usr/bin/env node
'use strict';

// Host-only distribution binding. Static checks remain in the verified Rust binary.
const fs = require('node:fs');
const crypto = require('node:crypto');
const https = require('node:https');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const LOCK_PATH = path.join(__dirname, 'codeguard.lock.json');
const SYSTEM_TAR = '/usr/bin/tar';
const EXPECTED_MEMBERS = [
  'package/LICENSE',
  'package/NOTICE',
  'package/README.md',
  'package/codeguard.cjs',
  'package/native/codeguard',
  'package/package.json',
].sort();

function fail(reason) {
  throw new Error(`codeguard runtime incomplete: ${reason}`);
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function readLock() {
  const lock = JSON.parse(fs.readFileSync(LOCK_PATH, 'utf8'));
  const hex = (value, length) => typeof value === 'string' && new RegExp(`^[0-9a-f]{${length}}$`).test(value);
  if (lock.schema_version !== '1.0.0' || lock.package !== '@partme.ai/codeguard'
      || lock.version !== '0.1.2' || lock.platform !== 'macos_arm64'
      || lock.check_protocol_major !== 1 || !hex(lock.source_commit, 40)
      || !hex(lock.tarball_sha256, 64) || !hex(lock.binary_sha256, 64)
      || lock.tarball_url !== 'https://registry.npmjs.org/@partme.ai/codeguard/-/codeguard-0.1.2.tgz'
      || typeof lock.tarball_integrity !== 'string'
      || !/^sha512-[A-Za-z0-9+/]{86}==$/.test(lock.tarball_integrity)) {
    fail('runtime_lock_invalid');
  }
  return lock;
}

function platformId() {
  return `${process.platform === 'darwin' ? 'macos' : process.platform}_${process.arch === 'arm64' ? 'arm64' : process.arch}`;
}

function checkPlatform(lock) {
  if (platformId() !== lock.platform) fail('platform_unsupported');
}

function cacheRoot() {
  const root = process.env.CODEGUARD_RUNTIME_CACHE || path.join(os.homedir(), '.codeguard', 'plugin-runtime');
  if (!path.isAbsolute(root)) fail('cache_path_not_absolute');
  return root;
}

function ensureCache(root) {
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const info = fs.lstatSync(root);
  if (!info.isDirectory() || info.isSymbolicLink() || (info.mode & 0o022) !== 0) {
    fail('cache_directory_unsafe');
  }
}

function regularFile(file) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || info.nlink !== 1) fail('runtime_file_unsafe');
  return info;
}

function verifyPackage(root, lock = readLock()) {
  checkPlatform(lock);
  if (!path.isAbsolute(root)) fail('package_path_not_absolute');
  const rootInfo = fs.lstatSync(root);
  if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) fail('package_directory_unsafe');
  const packageFile = path.join(root, 'package.json');
  if (regularFile(packageFile).size > 16 * 1024) fail('package_manifest_too_large');
  const manifest = JSON.parse(fs.readFileSync(packageFile, 'utf8'));
  if (manifest.name !== lock.package || manifest.version !== lock.version
      || JSON.stringify(manifest.os) !== '["darwin"]'
      || JSON.stringify(manifest.cpu) !== '["arm64"]') fail('package_identity_mismatch');
  const binary = path.join(root, 'native', 'codeguard');
  if (regularFile(binary).size > 32 * 1024 * 1024) fail('binary_too_large');
  if (sha256(fs.readFileSync(binary)) !== lock.binary_sha256) fail('binary_digest_mismatch');
  const result = spawnSync(binary, ['--version', '--format=json'], {
    encoding: 'utf8', shell: false, timeout: 3000, maxBuffer: 8192,
    env: { ...process.env, CODEGUARD_SKIP_GATE: '' },
  });
  if (result.error || result.status !== 0 || result.signal) fail('binary_version_unavailable');
  let version;
  try { version = JSON.parse(result.stdout); } catch { fail('binary_version_invalid'); }
  if (version.cli_version !== lock.version || version.target !== lock.platform
      || version.build_identity !== lock.source_commit
      || version.check_protocol_major !== lock.check_protocol_major) fail('binary_version_mismatch');
  return binary;
}

function verifyTarball(file, lock) {
  const info = regularFile(file);
  if (info.size > 8 * 1024 * 1024) fail('tarball_too_large');
  const bytes = fs.readFileSync(file);
  if (sha256(bytes) !== lock.tarball_sha256
      || `sha512-${crypto.createHash('sha512').update(bytes).digest('base64')}` !== lock.tarball_integrity) {
    fail('tarball_digest_mismatch');
  }
}

function installTarball(file, root = cacheRoot()) {
  const lock = readLock();
  checkPlatform(lock);
  ensureCache(root);
  verifyTarball(file, lock);
  const final = path.join(root, `sha256-${lock.binary_sha256}`);
  const lease = path.join(root, '.install.lock');
  let leaseFd;
  try { leaseFd = fs.openSync(lease, 'wx', 0o600); } catch { fail('installation_busy'); }
  let staging;
  try {
    if (!fs.existsSync(final)) {
      staging = fs.mkdtempSync(path.join(root, '.stage-'));
      fs.chmodSync(staging, 0o700);
      const list = spawnSync(SYSTEM_TAR, ['-tzf', file], { encoding: 'utf8', shell: false, timeout: 10000, maxBuffer: 8192 });
      if (list.error || list.status !== 0 || list.signal
          || JSON.stringify(list.stdout.trim().split('\n').sort()) !== JSON.stringify(EXPECTED_MEMBERS)) {
        fail('tarball_members_invalid');
      }
      const kinds = spawnSync(SYSTEM_TAR, ['-tvzf', file], { encoding: 'utf8', shell: false, timeout: 10000, maxBuffer: 8192 });
      if (kinds.error || kinds.status !== 0 || kinds.signal
          || kinds.stdout.trim().split('\n').length !== EXPECTED_MEMBERS.length
          || kinds.stdout.trim().split('\n').some((entry) => !entry.startsWith('-'))) {
        fail('tarball_member_type_invalid');
      }
      const unpack = spawnSync(SYSTEM_TAR, ['-xzf', file, '-C', staging], { shell: false, timeout: 10000, maxBuffer: 8192 });
      if (unpack.error || unpack.status !== 0 || unpack.signal) fail('tarball_extract_failed');
      verifyPackage(path.join(staging, 'package'), lock);
      fs.renameSync(path.join(staging, 'package'), final);
    }
    verifyPackage(final, lock);
    const next = path.join(root, `.active-${process.pid}-${crypto.randomBytes(6).toString('hex')}`);
    try {
      const fd = fs.openSync(next, 'wx', 0o600);
      try {
        fs.writeFileSync(fd, JSON.stringify({ schema_version: '1.0.0', directory: path.basename(final), binary_sha256: lock.binary_sha256 }) + '\n');
        fs.fsyncSync(fd);
      } finally { fs.closeSync(fd); }
      fs.renameSync(next, path.join(root, 'active.json'));
    } finally { if (fs.existsSync(next)) fs.unlinkSync(next); }
    return final;
  } finally {
    if (staging) fs.rmSync(staging, { recursive: true, force: true });
    fs.closeSync(leaseFd);
    fs.unlinkSync(lease);
  }
}

function activeBinary(root = cacheRoot()) {
  const lock = readLock();
  checkPlatform(lock);
  ensureCache(root);
  const active = path.join(root, 'active.json');
  if (regularFile(active).size > 4096) fail('active_receipt_invalid');
  const receipt = JSON.parse(fs.readFileSync(active, 'utf8'));
  if (receipt.schema_version !== '1.0.0'
      || receipt.directory !== `sha256-${lock.binary_sha256}`
      || receipt.binary_sha256 !== lock.binary_sha256) fail('active_receipt_mismatch');
  return verifyPackage(path.join(root, receipt.directory), lock);
}

function downloadTarball(lock) {
  return new Promise((resolve, reject) => {
    const request = https.get(lock.tarball_url, { timeout: 30000 }, (response) => {
      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`registry_status_${response.statusCode}`));
        return;
      }
      const chunks = [];
      let size = 0;
      response.on('data', (chunk) => {
        size += chunk.length;
        if (size > 8 * 1024 * 1024) { request.destroy(new Error('tarball_too_large')); return; }
        chunks.push(chunk);
      });
      response.on('end', () => resolve(Buffer.concat(chunks)));
      response.on('error', reject);
    });
    request.on('timeout', () => request.destroy(new Error('registry_timeout')));
    request.on('error', reject);
  });
}

async function installFromRegistry(root = cacheRoot()) {
  const lock = readLock();
  checkPlatform(lock);
  ensureCache(root);
  const bytes = await downloadTarball(lock);
  const temporary = path.join(root, `.download-${process.pid}-${crypto.randomBytes(6).toString('hex')}`);
  try {
    fs.writeFileSync(temporary, bytes, { flag: 'wx', mode: 0o600 });
    return installTarball(temporary, root);
  } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
}

module.exports = { activeBinary, cacheRoot, installFromRegistry, installTarball, readLock, verifyPackage };

if (require.main === module) {
  const action = process.argv[2];
  (async () => {
    if (action === 'verify') {
      process.stdout.write(JSON.stringify({ status: 'verified', binary: activeBinary() }) + '\n');
    } else if (action === 'install' && process.argv[3] === '--download' && process.argv.length === 4) {
      process.stdout.write(JSON.stringify({ status: 'installed', root: await installFromRegistry() }) + '\n');
    } else if (action === 'install' && process.argv[3] === '--tarball' && path.isAbsolute(process.argv[4] || '') && process.argv.length === 5) {
      process.stdout.write(JSON.stringify({ status: 'installed', root: installTarball(process.argv[4]) }) + '\n');
    } else {
      fail('usage: verify | install --download | install --tarball ABS_PATH');
    }
  })().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 3;
  });
}
