// Extra QA sheets cut from the rendered video: N stills per shot, six to a sheet.
import './ffpath.mjs';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';

const per = Number(process.argv[2] ?? 3);
const vo = JSON.parse(fs.readFileSync('src/vo-durations.json', 'utf8'));
const OUT = 'out/qa-video';
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
let t = 0.7;
let n = 0;
for (const s of vo.shots) {
  for (let i = 0; i < per; i++) {
    const at = t + s.dur * (per === 1 ? 0.5 : 0.14 + (0.76 * i) / (per - 1));
    n += 1;
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-ss', at.toFixed(2), '-i', 'out/demo.mp4', '-frames:v', '1',
      '-vf', `scale=960:-1,drawtext=text='${s.id} ${at.toFixed(1)}s':x=12:y=12:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.7:fontfile=/Windows/Fonts/arial.ttf`,
      `${OUT}/${String(n).padStart(3, '0')}.jpg`]);
  }
  t += s.dur;
}
execFileSync('ffmpeg', ['-y', '-v', 'error', '-i', `${OUT}/%03d.jpg`, '-vf', 'tile=3x2', '-q:v', '3', `${OUT}/sheet_%02d.jpg`]);
console.log(fs.readdirSync(OUT).filter((f) => f.startsWith('sheet')).join('\n'));
