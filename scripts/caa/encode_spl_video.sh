#!/bin/bash
# Encode ParaView SPL frames → MP4 (+ short webm preview)
set -euo pipefail
cd "$(dirname "$0")/../.."

FRAMES="Reports/caa/paraview/frames"
OUT_DIR="Reports/caa/figures"
mkdir -p "$OUT_DIR"

if [ ! -f "$FRAMES/frame_0000.png" ]; then
  echo "No frames in $FRAMES — run: xvfb-run -a pvpython scripts/caa/paraview_spl_video.py"
  exit 1
fi

# 24 fps, H.264, yuv420p for broad player compatibility
# (120 frames @ 24 fps ≈ 5 s full orbit)
ffmpeg -y -hide_banner -loglevel error \
  -framerate 24 \
  -i "$FRAMES/frame_%04d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset medium \
  -movflags +faststart \
  "$OUT_DIR/paraview_spl_orbit.mp4"

# Lightweight webm for quick preview
ffmpeg -y -hide_banner -loglevel error \
  -framerate 24 \
  -i "$FRAMES/frame_%04d.png" \
  -c:v libvpx-vp9 -b:v 0 -crf 32 -an \
  "$OUT_DIR/paraview_spl_orbit.webm"

# Also copy a demo alias used by walkthrough conventions
cp -f "$OUT_DIR/paraview_spl_orbit.mp4" "$OUT_DIR/recording_demo.mp4" 2>/dev/null || true

ls -lh "$OUT_DIR/paraview_spl_orbit.mp4" "$OUT_DIR/paraview_spl_orbit.webm"
echo "Video ready: $OUT_DIR/paraview_spl_orbit.mp4"
