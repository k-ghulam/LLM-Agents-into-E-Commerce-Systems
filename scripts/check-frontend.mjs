import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
let count = 0;
function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path);
    else if (path.endsWith('.js')) {
      const result = spawnSync(process.execPath, ['--input-type=module', '--check'], { input: readFileSync(path), encoding: 'utf8' });
      if (result.status !== 0) { console.error(path, result.stderr); process.exit(1); }
      count++;
    }
  }
}
walk(fileURLToPath(new URL('../Frontend/src', import.meta.url)));
console.log(`Parsed ${count} browser modules successfully.`);
