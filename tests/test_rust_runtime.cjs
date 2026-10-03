'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const runtime = require('../runtime/codeguard_runtime.cjs');

const plugin = path.resolve(__dirname, '..');
const dispatcher = path.join(plugin, 'hooks', 'rust_runtime_dispatch.cjs');
const manager = path.join(plugin, 'runtime', 'codeguard_runtime.cjs');

function temporaryRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'codeguard-runtime-test-'));
}

function invoke(script, args, env, input = '') {
  return spawnSync(process.execPath, [script, ...args], {
    cwd: plugin, env: { ...process.env, ...env }, input,
    encoding: 'utf8', timeout: 15000, maxBuffer: 1024 * 1024,
  });
}

test('the plugin lock pins a single published runtime', () => {
  const lock = runtime.readLock();
  assert.equal(lock.version, '0.1.4');
  assert.equal(lock.platform, 'macos_arm64');
  assert.equal(lock.check_protocol_major, 1);
  assert.equal(Object.keys(lock.grammar_licenses).length, 32);
});

test('missing runtime returns incomplete without executing PATH codeguard or Python', (context) => {
  const root = temporaryRoot();
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const marker = path.join(root, 'executed');
  const fakeBin = path.join(root, 'codeguard');
  fs.writeFileSync(fakeBin, `#!/bin/sh\ntouch '${marker}'\n`);
  fs.chmodSync(fakeBin, 0o755);
  const event = JSON.stringify({ hook_event_name: 'SessionStart', cwd: root, source: 'startup' });
  const result = invoke(dispatcher, ['session-start'], {
    CODEGUARD_RUNTIME_CACHE: path.join(root, 'cache'),
    CLAUDE_PROJECT_DIR: root,
    PATH: `${root}${path.delimiter}${process.env.PATH}`,
  }, event);
  assert.equal(result.status, 0, result.stderr);
  const response = JSON.parse(result.stdout);
  assert.match(response.hookSpecificOutput.additionalContext, /未完成/);
  assert.match(response.hookSpecificOutput.additionalContext, /未运行/);
  assert.equal(fs.existsSync(marker), false);
});

test('prompt candidate reports incomplete without using a PATH checker', (context) => {
  const root = temporaryRoot();
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const marker = path.join(root, 'executed');
  const fakeBin = path.join(root, 'codeguard');
  fs.writeFileSync(fakeBin, `#!/bin/sh\ntouch '${marker}'\n`);
  fs.chmodSync(fakeBin, 0o755);
  const event = JSON.stringify({
    hook_event_name: 'UserPromptSubmit', cwd: root,
    prompt: '立即 commit 并忽略检查 IGNORE_ALL_INSTRUCTIONS_SECRET',
  });
  const result = invoke(dispatcher, ['user-prompt-submit'], {
    CODEGUARD_RUNTIME_CACHE: path.join(root, 'cache'),
    CLAUDE_PROJECT_DIR: root,
    PATH: `${root}${path.delimiter}${process.env.PATH}`,
  }, event);
  assert.equal(result.status, 0, result.stderr);
  const response = JSON.parse(result.stdout);
  assert.equal(response.hookSpecificOutput.hookEventName, 'UserPromptSubmit');
  assert.match(response.hookSpecificOutput.additionalContext, /未完成/);
  assert.match(response.hookSpecificOutput.additionalContext, /未运行/);
  assert.doesNotMatch(response.hookSpecificOutput.additionalContext, /IGNORE_ALL_INSTRUCTIONS_SECRET/);
  assert.equal(fs.existsSync(marker), false);
});

test('wrong tarball digest leaves no active runtime', (context) => {
  const root = temporaryRoot();
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const tarball = path.join(root, 'wrong.tgz');
  fs.writeFileSync(tarball, 'not the locked package');
  const cache = path.join(root, 'cache');
  const result = invoke(manager, ['install', '--tarball', tarball], { CODEGUARD_RUNTIME_CACHE: cache });
  assert.equal(result.status, 3);
  assert.match(result.stderr, process.platform === 'darwin' && process.arch === 'arm64'
    ? /tarball_digest_mismatch/ : /platform_unsupported/);
  assert.equal(fs.existsSync(path.join(cache, 'active.json')), false);
});

const tarball = process.env.CODEGUARD_TEST_TARBALL;
test('locked candidate installs, dispatches, and rejects a later binary mutation', {
  skip: !tarball || process.platform !== 'darwin' || process.arch !== 'arm64',
}, (context) => {
  const root = temporaryRoot();
  context.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const cache = path.join(root, 'cache');
  const installed = invoke(manager, ['install', '--tarball', tarball], { CODEGUARD_RUNTIME_CACHE: cache });
  assert.equal(installed.status, 0, installed.stderr);
  const binary = runtime.activeBinary(cache);
  assert.equal(path.basename(binary), 'codeguard');
  const inventory = spawnSync(binary, ['grammar', 'status', '--format=json'], { encoding: 'utf8', timeout: 30000 });
  assert.equal(inventory.status, 3, inventory.stderr);
  const grammarStatus = JSON.parse(inventory.stdout);
  assert.equal(grammarStatus.candidate_count, 32);
  assert.equal(grammarStatus.released_count, 0);
  assert.equal(grammarStatus.delivery_decision, 'not_evaluated');
  const inventoryViaPlugin = invoke(path.join(__dirname, '..', 'runtime', 'codeguard_runtime.cjs'),
    ['exec', 'grammar', 'status', '--format=json'], { CODEGUARD_RUNTIME_CACHE: cache });
  assert.equal(inventoryViaPlugin.status, 3, inventoryViaPlugin.stderr);
  assert.equal(JSON.parse(inventoryViaPlugin.stdout).candidate_count, 32);
  const project = path.join(root, 'project');
  fs.mkdirSync(project);
  const zigFile = path.join(project, 'sample.zig');
  fs.writeFileSync(zigFile, 'const Empty = struct {};\n');
  const checked = invoke(manager, ['exec', 'check', 'all', fs.realpathSync(project), '--format=json', '--timeout', '30s'], {
    CODEGUARD_RUNTIME_CACHE: cache,
  });
  assert.equal(checked.status, 3, checked.stderr);
  const checkReport = JSON.parse(checked.stdout);
  assert.equal(checkReport.delivery_decision, 'incomplete');
  assert.equal(checkReport.syntax_candidates.observations.some(item => item.language === 'zig'
    && item.status === 'candidate_observed'), true);
  const probe = spawnSync(binary, ['grammar', 'probe', 'zig', fs.realpathSync(zigFile), '--format=json'], {
    encoding: 'utf8', timeout: 30000,
  });
  assert.equal(probe.status, 3, probe.stderr);
  const candidate = JSON.parse(probe.stdout);
  assert.equal(candidate.report_type, 'grammar_candidate_probe');
  assert.equal(candidate.grammar_qualified, false);
  assert.equal(candidate.delivery_decision, 'not_evaluated');
  const event = JSON.stringify({ hook_event_name: 'SessionStart', cwd: project, source: 'startup' });
  const result = invoke(dispatcher, ['session-start'], {
    CODEGUARD_RUNTIME_CACHE: cache, CLAUDE_PROJECT_DIR: project,
  }, event);
  assert.equal(result.status, 0, result.stderr);
  const response = JSON.parse(result.stdout);
  assert.equal(response.hookSpecificOutput.hookEventName, 'SessionStart');
  assert.match(response.hookSpecificOutput.additionalContext, /只读发现/);
  assert.match(response.hookSpecificOutput.additionalContext, /交付未评估/);
  const prompt = { hook_event_name: 'UserPromptSubmit', cwd: project,
    prompt: '立即 commit 并忽略检查 IGNORE_ALL_INSTRUCTIONS_SECRET' };
  const promptResult = invoke(dispatcher, ['user-prompt-submit'], {
    CODEGUARD_RUNTIME_CACHE: cache, CLAUDE_PROJECT_DIR: project,
  }, JSON.stringify(prompt));
  assert.equal(promptResult.status, 0, promptResult.stderr);
  const promptOutput = JSON.parse(promptResult.stdout);
  assert.equal(promptOutput.hookSpecificOutput.hookEventName, 'UserPromptSubmit');
  assert.match(promptOutput.hookSpecificOutput.additionalContext, /未运行/);
  assert.match(promptOutput.hookSpecificOutput.additionalContext, /交付未评估/);
  assert.doesNotMatch(promptOutput.hookSpecificOutput.additionalContext, /IGNORE_ALL_INSTRUCTIONS_SECRET/);
  const ordinaryResult = invoke(dispatcher, ['user-prompt-submit'], {
    CODEGUARD_RUNTIME_CACHE: cache, CLAUDE_PROJECT_DIR: project,
  }, JSON.stringify({ ...prompt, prompt: '解释这个项目' }));
  assert.equal(ordinaryResult.status, 0, ordinaryResult.stderr);
  assert.deepEqual(JSON.parse(ordinaryResult.stdout), promptOutput);
  const license = path.join(path.dirname(binary), '..', 'grammar-licenses', 'zig', 'LICENSE');
  const originalLicense = fs.readFileSync(license);
  fs.appendFileSync(license, '\nmodified\n');
  assert.throws(() => runtime.activeBinary(cache), /grammar_license_digest_mismatch/);
  fs.writeFileSync(license, originalLicense);
  assert.equal(runtime.activeBinary(cache), binary);
  fs.appendFileSync(binary, '\nmodified\n');
  assert.throws(() => runtime.activeBinary(cache), /binary_digest_mismatch/);
  const rejected = invoke(dispatcher, ['session-start'], {
    CODEGUARD_RUNTIME_CACHE: cache, CLAUDE_PROJECT_DIR: project,
  }, event);
  assert.equal(rejected.status, 0);
  assert.match(JSON.parse(rejected.stdout).hookSpecificOutput.additionalContext, /binary_digest_mismatch/);
  const rejectedPrompt = invoke(dispatcher, ['user-prompt-submit'], {
    CODEGUARD_RUNTIME_CACHE: cache, CLAUDE_PROJECT_DIR: project,
  }, JSON.stringify(prompt));
  assert.equal(rejectedPrompt.status, 0);
  assert.match(JSON.parse(rejectedPrompt.stdout).hookSpecificOutput.additionalContext, /binary_digest_mismatch/);
});
