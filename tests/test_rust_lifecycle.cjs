'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const test = require('node:test');
const runtime = require('../runtime/codeguard_runtime.cjs');
const plugin = path.resolve(__dirname, '..');
const manager = path.join(plugin, 'runtime/codeguard_runtime.cjs');
const hooks = JSON.parse(fs.readFileSync(path.join(plugin, 'hooks/hooks.json'), 'utf8')).hooks;
const routes = { SessionStart: 'session-start', UserPromptSubmit: 'user-prompt-submit',
  PostToolUse: 'post-tool-use', PostToolUseFailure: 'post-tool-use-failure', Stop: 'stop' };

function invoke(script, args, env, input = '') {
  return spawnSync(process.execPath, [script, ...args], { cwd: plugin,
    env: { ...process.env, ...env }, input, encoding: 'utf8',
    timeout: 15000, maxBuffer: 1024 * 1024 });
}
function defaultCall(event, env, payload) {
  const entry = hooks[event][0].hooks[0];
  const match = /^node "\$\{CLAUDE_PLUGIN_ROOT\}\/hooks\/rust_runtime_dispatch.cjs" ([a-z-]+)$/.exec(entry.command);
  assert.ok(match, `default ${event} does not route to the Rust dispatcher`);
  assert.equal(match[1], routes[event]);
  const start = performance.now();
  const result = invoke(path.join(plugin, 'hooks/rust_runtime_dispatch.cjs'), [match[1]], env,
    JSON.stringify(payload));
  assert.equal(result.status, 0, result.stderr);
  const value = JSON.parse(result.stdout);
  const context = value.hookSpecificOutput?.additionalContext ?? value.systemMessage;
  assert.equal(typeof context, 'string');
  assert.ok([...context].length <= 1200);
  assert.doesNotMatch(context, /RAW_HOST_INPUT_PRIVATE/);
  return { value, context, elapsed_ms: performance.now() - start };
}

test('canonical lifecycle selects pinned 0.1.4 and bounded Rust defaults while retaining Git gate', () => {
  assert.equal(runtime.readLock().version, '0.1.4');
  for (const [event, route] of Object.entries(routes)) {
    assert.equal(hooks[event][0].hooks[0].command,
      `node "\${CLAUDE_PLUGIN_ROOT}/hooks/rust_runtime_dispatch.cjs" ${route}`);
    assert.ok(hooks[event][0].hooks[0].timeout >= 10);
    assert.ok(hooks[event][0].hooks[0].timeout <= 15);
  }
  assert.equal(hooks.UserPromptSubmit[0].matcher, undefined);
  assert.match(hooks.PreToolUse[0].hooks[0].command, /pre_tool_git_guard\.py/);
});

test('missing runtime is visible on every default lifecycle and does not install or use PATH checkers', (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cg-default-missing-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const marker = path.join(root, 'checker-executed');
  for (const name of ['codeguard', 'python3']) {
    const file = path.join(root, name);
    fs.writeFileSync(file, `#!/bin/sh\ntouch '${marker}'\n`); fs.chmodSync(file, 0o755);
  }
  const env = { CODEGUARD_RUNTIME_CACHE: path.join(root, 'cache'), CLAUDE_PROJECT_DIR: root,
    PATH: `${root}${path.delimiter}${process.env.PATH}` };
  for (const event of Object.keys(routes)) {
    const result = defaultCall(event, env, { hook_event_name: event, cwd: root,
      source: 'startup', prompt: 'RAW_HOST_INPUT_PRIVATE', stop_hook_active: false });
    assert.match(result.context, /未完成/);
    assert.match(result.context, /未运行/);
    assert.match(result.context, /install/);
  }
  assert.equal(fs.existsSync(marker), false);
  assert.equal(fs.existsSync(path.join(root, 'cache/active.json')), false);
});

const tarball = process.env.CODEGUARD_TEST_TARBALL;
test('actual locked public package drives default editing, stable tasks and executable recheck guidance', {
  skip: !tarball || process.platform !== 'darwin' || process.arch !== 'arm64',
}, (t) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'cg-default-installed-'));
  t.after(() => fs.rmSync(temporary, { recursive: true, force: true }));
  const project = path.join(temporary, 'project'); fs.mkdirSync(project);
  const root = fs.realpathSync(project);
  const env = { CODEGUARD_RUNTIME_CACHE: path.join(temporary, 'cache'), CLAUDE_PROJECT_DIR: root };
  const installed = invoke(manager, ['install', '--tarball', tarball], env);
  assert.equal(installed.status, 0, installed.stderr);
  const init = invoke(manager, ['exec', 'init', root, '--apply', '--format=json'], env);
  assert.equal(init.status, 3, init.stderr);
  assert.equal(JSON.parse(init.stdout).report_type, "init_plan");
  const started = defaultCall('SessionStart', env, { hook_event_name: 'SessionStart', cwd: root, source: 'startup' });
  assert.match(started.context, /只读发现/);
  const file = path.join(root, 'bad.zig'); fs.writeFileSync(file, 'const broken = ;\n');
  const payload = { hook_event_name: 'PostToolUse', cwd: root, tool_name: 'Write',
    tool_input: { file_path: file, content: 'RAW_HOST_INPUT_PRIVATE' },
    tool_response: { filePath: file, type: 'create' } };
  const timings = [];
  for (let i = 0; i < 3; i++) {
    const result = defaultCall('PostToolUse', env, payload); timings.push(result.elapsed_ms);
    assert.match(result.context, /必须/);
    assert.match(result.context, /CG-B-[0-9a-f]{32}/);
    assert.match(result.context, /task show/);
  }
  const next = invoke(manager, ['exec', 'next', root, '--format=json'], env);
  assert.equal(next.status, 0, next.stderr);
  const brief = JSON.parse(next.stdout);
  const id = brief.repair_brief.task_id;
  assert.match(id, /^CG-B-[0-9a-f]{32}$/);
  const shown = invoke(manager, ['exec', 'task', 'show', id, root, '--format=json'], env);
  assert.equal(shown.status, 0, shown.stderr);
  assert.equal(JSON.parse(shown.stdout).task_id, id);
  const taskCount = fs.readdirSync(path.join(root, '.codeguard/tasks')).filter(n => n.endsWith('.md')).length;
  assert.equal(taskCount, 1);
  const failed = defaultCall('PostToolUseFailure', env, { ...payload,
    hook_event_name: 'PostToolUseFailure', error: 'RAW_HOST_INPUT_PRIVATE' });
  assert.match(failed.context, /未运行/);
  for (const [event, extra] of [['UserPromptSubmit', { prompt: 'commit RAW_HOST_INPUT_PRIVATE' }],
    ['Stop', { stop_hook_active: false }], ['Stop', { stop_hook_active: true }]]) {
    defaultCall(event, env, { hook_event_name: event, cwd: root, ...extra });
  }
  assert.equal(fs.readdirSync(path.join(root, '.codeguard/tasks')).filter(n => n.endsWith('.md')).length, 1);
  const unsupported = invoke(manager, ['exec', 'fix', root], env);
  assert.equal(unsupported.status, 3);
  assert.match(unsupported.stderr, /usage/);
  const zig = '/opt/homebrew/bin/zig';
  if (fs.existsSync(zig)) {
    const result = invoke(manager, ['exec', 'task', 'verify', id, root, '--zig-tool', zig,
      '--timeout', '5s', '--format=json'], env);
    assert.equal(result.status, 3, result.stderr);
    assert.equal(JSON.parse(result.stdout).observation, 'still_blocked');
    fs.writeFileSync(file, 'const Fixed = struct {};\n');
    const fixed = invoke(manager, ['exec', 'task', 'verify', id, root, '--zig-tool', zig,
      '--timeout', '5s', '--format=json'], env);
    assert.equal(fixed.status, 3, fixed.stderr);
    const observed = JSON.parse(fixed.stdout);
    assert.equal(observed.observation, 'candidate_absent_unverified_policy');
    assert.equal(JSON.parse(fs.readFileSync(path.join(root, '.codeguard/findings', id, 'finding.json'))).state, 'open');
  }
  t.diagnostic(JSON.stringify({ default_post_tool_ms: timings, task_id_stable: true,
    source: runtime.readLock().source_commit, native_zig_rechecked: fs.existsSync(zig), installed_host_accepted: false }));
});
