'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { invokeVerifiedRuntime } = require('../hooks/rust_runtime_adapter.cjs');
test('adapter rejects unsupported events, relative binary/root and oversized input', () => {
  assert.throws(() => invokeVerifiedRuntime('unknown', process.execPath, process.cwd(), Buffer.alloc(0)), /event_unsupported/);
  assert.throws(() => invokeVerifiedRuntime('session-start','relative',process.cwd(),Buffer.alloc(0)), /runtime_arguments_invalid/);
  assert.throws(() => invokeVerifiedRuntime('session-start',process.execPath,'relative',Buffer.alloc(0)), /runtime_arguments_invalid/);
  assert.throws(() => invokeVerifiedRuntime('session-start',process.execPath,process.cwd(),Buffer.alloc(1024*1024+1)), /host_input_too_large/);
});
test('failed native dispatch stays incomplete rather than accepting arbitrary output', () => {
  assert.throws(() => invokeVerifiedRuntime('session-start',process.execPath,process.cwd(),Buffer.from('{}')), /runtime_execution_failed/);
});
