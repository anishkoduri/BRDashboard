// A supplied recording instead of synthesis: slices shots.json -> voiceover.file
// at voiceover.cuts (seconds, one start per shot) into public/vo/<id>.wav and
// writes the cache entries tts.mjs expects, so `npm run all` treats every line
// as already rendered. Cuts sit in the pauses, so gapMs stays 0.
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import './ffpath.mjs';
import fs from 'node:fs';
import path from 'node:path';

const cfg = JSON.parse(fs.readFileSync('shots.json', 'utf8'));
const { file, cuts } = cfg.voiceover ?? {};
const tts = cfg.tts ?? {};
if (!file || !fs.existsSync(file)) throw new Error(`voiceover.file not found: ${file}`);
if (cuts?.length !== cfg.shots.length) throw new Error(`voiceover.cuts needs one start per shot (${cfg.shots.length}), got ${cuts?.length}`);

const probe = (f) =>
  Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f]).toString().trim());

const VO = path.resolve('public/vo');
fs.mkdirSync(VO, { recursive: true });
const end = probe(file);
const cache = {};
cfg.shots.forEach((s, i) => {
  const wav = path.join(VO, `${s.id}.wav`);
  const from = cuts[i];
  const to = cuts[i + 1] ?? end;
  if (!(to > from)) throw new Error(`voiceover.cuts must increase (shot ${s.id})`);
  execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', file, '-ss', String(from), '-to', String(to), '-ar', '48000', '-ac', '1', wav]);
  // Same key tts.mjs computes, so its cache check passes untouched.
  const key = crypto
    .createHash('sha1')
    .update(`${tts.provider ?? 'say'}|${tts.voice}|${tts.model}|${tts.speed}|${tts.stability}|${tts.similarityBoost}|${tts.style}|${tts.piperModel}|${JSON.stringify(tts.fallback)}|${s.say}`)
    .digest('hex');
  const dur = Number(probe(wav).toFixed(3));
  cache[s.id] = { key, provider: tts.provider ?? 'say', dur };
  console.log(`${s.id.padEnd(9)} ${from.toFixed(2)} -> ${to.toFixed(2)}  ${dur.toFixed(2)}s`);
});
fs.writeFileSync(path.join(VO, '.cache.json'), JSON.stringify(cache, null, 2));
