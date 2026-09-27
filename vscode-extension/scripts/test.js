const { spawnSync } = require('node:child_process');

const python = process.env.DTM_BUILD_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const result = spawnSync(python, ['-m', 'unittest', 'discover', '-s', 'tests'], {
  cwd: require('node:path').resolve(__dirname, '..'),
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exit(result.status || 0);
