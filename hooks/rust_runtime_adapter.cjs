'use strict';
// Internal transport only. Callers must authenticate binary identity first.
// The default dispatcher always uses activeBinary(); no CLI or environment override.
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const EVENTS = new Map([
  ['session-start','SessionStart'], ['user-prompt-submit','UserPromptSubmit'],
  ['post-tool-use','PostToolUse'], ['post-tool-use-failure','PostToolUseFailure'], ['stop','Stop'],
]);
function invokeVerifiedRuntime(event, binary, root, input) {
  if (!EVENTS.has(event)) throw new Error('event_unsupported');
  if (!path.isAbsolute(binary) || !path.isAbsolute(root) || !Buffer.isBuffer(input)) throw new Error('runtime_arguments_invalid');
  if (input.length > 1024 * 1024) throw new Error('host_input_too_large');
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
module.exports = { invokeVerifiedRuntime };
