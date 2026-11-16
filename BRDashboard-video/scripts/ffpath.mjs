// The machine may have no ffmpeg: put the locally installed builds (devDependencies) first on PATH.
// Imported for its side effect by the scripts that are run directly; child processes inherit it.
import path from 'node:path';

const dirs = ['@ffmpeg-installer', '@ffprobe-installer'].map((p) => path.resolve('node_modules', p, `${process.platform}-${process.arch}`));
process.env.PATH = [...dirs, process.env.PATH].join(path.delimiter);
