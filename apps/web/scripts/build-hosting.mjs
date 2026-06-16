// Assemble the Firebase Hosting payload:
//   dist/            -> landing page (served at "/")
//   dist/app/        -> the SPA build (served at "/app/**" via rewrite)
//
// Run AFTER `vite build` (which emits the SPA into dist/ with base "/app/").
import { cpSync, existsSync, mkdirSync, readdirSync, renameSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, '..');
const dist = join(webRoot, 'dist');
const appDir = join(dist, 'app');
const landing = resolve(webRoot, '../../../landing page');

if (!existsSync(dist)) {
  console.error('[build-hosting] dist/ not found — run `vite build` first.');
  process.exit(1);
}

// 1. Move the SPA build into dist/app (everything except an existing app/ dir).
const staging = join(webRoot, '.spa-staging');
rmSync(staging, { recursive: true, force: true });
mkdirSync(staging, { recursive: true });
for (const entry of readdirSync(dist)) {
  if (entry === 'app') continue;
  renameSync(join(dist, entry), join(staging, entry));
}
rmSync(appDir, { recursive: true, force: true });
renameSync(staging, appDir);

// 2. Copy the landing page + its image assets to dist root ("/").
if (!existsSync(landing)) {
  console.error(`[build-hosting] landing page not found at ${landing}`);
  process.exit(1);
}
for (const entry of readdirSync(landing)) {
  cpSync(join(landing, entry), join(dist, entry), { recursive: true });
}

console.log('[build-hosting] dist/ assembled: landing at "/", SPA at "/app/".');
