'use strict';
// Test-only adapter caller. The Python harness authenticates the candidate first.
const fs = require('node:fs');
const { invokeVerifiedRuntime } = require('../hooks/rust_runtime_adapter.cjs');
if (process.argv.length !== 5) throw new Error('expected verified binary, isolated project, event');
const [, , binary, root, event] = process.argv;
process.stdout.write(JSON.stringify(invokeVerifiedRuntime(event,binary,root,fs.readFileSync(0)))+'\n');
