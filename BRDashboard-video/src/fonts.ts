// The app's own self-hosted faces (copied from frontend/public/fonts), so the
// cards and the footage read as one piece.
import { loadFont } from '@remotion/fonts';
import { staticFile } from 'remotion';

for (const weight of ['500', '600', '700']) {
  loadFont({ family: 'Red Hat Display', url: staticFile(`fonts/RedHatDisplay-${weight}.woff2`), weight });
}
for (const weight of ['400', '500']) {
  loadFont({ family: 'Red Hat Mono', url: staticFile(`fonts/RedHatMono-${weight}.woff2`), weight });
}
