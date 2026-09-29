#!/usr/bin/env node
'use strict';

// Candidate Claude Code binding. It never resolves `codeguard` from PATH or falls back to Python.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const pluginRoot = fs.existsSync(path.join(__dirname, '..', 'runtime', 'codeguard_runtime.cjs'))
  ? path.resolve(__dirname, '..') : path.resolve(__dirname, '..', '..');
const { activeBinary } = require(path.join(pluginRoot, 'runtime', 'codeguard_runtime.cjs'));

const EVENTS = new Map([
  ['session-start', 'SessionStart'],
  ['user-prompt-submit', 'UserPromptSubmit'],
  ['post-tool-use', 'PostToolUse'],
  ['post-tool-use-failure', 'PostToolUseFailure'],
  ['stop', 'Stop'],
]);

function incomplete(event, reason) {
  const safe = /^[a-z_]+$/.test(reason) ? reason : 'runtime_unavailable';
  const message = `CodeGuard Rust 运行时未完成（${safe}）；本次源码检查未运行，交付未评估。请执行插件 runtime/codeguard_runtime.cjs verify 或修复安装。`;
  return event === 'stop'
    ? { systemMessage: message }
    : { hookSpecificOutput: { hookEventName: EVENTS.get(event), additionalContext: message } };
}

function readInput() {
  const pieces = [];
  const buffer = Buffer.allocUnsafe(64 * 1024);
  let total = 0;
  for (;;) {
    const length = fs.readSync(0, buffer, 0, buffer.length, null);
    if (length === 0) break;
    total += length;
    if (total > 1024 * 1024) throw new Error('host_input_too_large');
    pieces.push(Buffer.from(buffer.subarray(0, length)));
  }
  return Buffer.concat(pieces);
}

function projectRoot() {
  const configured = process.env.CLAUDE_PROJECT_DIR;
  const value = configured && path.isAbsolute(configured) ? configured : process.cwd();
  return fs.realpathSync(value);
}

function run(event) {
  if (!EVENTS.has(event)) throw new Error('event_unsupported');
  const input = readInput();
  const binary = activeBinary();
  const root = projectRoot();
  const result = spawnSync(binary, ['hook', 'claude', event, root, '--timeout=5s', '--format=json'], {
    input, encoding: 'utf8', shell: false, timeout: 8000, maxBuffer: 16 * 1024,
    env: process.env,
  });
  if (result.error || result.signal || result.status !== 0) throw new Error('runtime_execution_failed');
  let output;
  try { output = JSON.parse(result.stdout); } catch { throw new Error('runtime_response_invalid'); }
  if (event === 'stop') {
    if (typeof output.systemMessage !== 'string'
        && output.hookSpecificOutput?.hookEventName !== 'Stop') {
      throw new Error('runtime_response_invalid');
    }
  } else if (output.hookSpecificOutput?.hookEventName !== EVENTS.get(event)
             || typeof output.hookSpecificOutput.additionalContext !== 'string') {
    throw new Error('runtime_response_invalid');
  }
  return output;
}

if (require.main === module) {
  const event = process.argv[2];
  try {
    process.stdout.write(JSON.stringify(run(event)) + '\n');
  } catch (error) {
    const reason = typeof error.message === 'string' && error.message.startsWith('codeguard runtime incomplete: ')
      ? error.message.slice('codeguard runtime incomplete: '.length)
      : error.message;
    if (EVENTS.has(event)) process.stdout.write(JSON.stringify(incomplete(event, reason)) + '\n');
    else {
      process.stderr.write('CodeGuard Rust 宿主事件无效。\n');
      process.exitCode = 2;
    }
  }
}

module.exports = { run };
