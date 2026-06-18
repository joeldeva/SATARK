import { copyFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const out = join(root, 'www');

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

for (const file of ['index.html', 'styles.css', 'app.js']) {
  copyFileSync(join(root, file), join(out, file));
}

console.log('Prepared SATARK Citizen web assets in apps/citizen/www');
