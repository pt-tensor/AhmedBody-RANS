# pvpython — animate ParaView SPL visualization (camera orbit) → PNG frames
# Run:
#   python3 scripts/caa/export_spl_vtk.py   # if needed
#   xvfb-run -a pvpython scripts/caa/paraview_spl_video.py
#   bash scripts/caa/encode_spl_video.sh
#
# Target: ParaView 5.11+

from __future__ import print_function

import math
import os
import shutil
import sys

from paraview.simple import (
    ColorBy,
    Contour,
    GetActiveViewOrCreate,
    GetColorTransferFunction,
    GetOpacityTransferFunction,
    GetScalarBar,
    Glyph,
    LegacyVTKReader,
    Render,
    ResetSession,
    STLReader,
    SaveScreenshot,
    Show,
    Slice,
    Sphere,
    Text,
    Transform,
)


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VTK = os.path.join(ROOT, "Reports", "caa", "paraview", "spl_field.vtk")
OBS = os.path.join(ROOT, "Reports", "caa", "paraview", "observers.vtk")
STL = os.path.join(ROOT, "constant", "triSurface", "ahmed_25deg_m.stl")
FRAME_DIR = os.path.join(ROOT, "Reports", "caa", "paraview", "frames")
N_FRAMES = int(os.environ.get("SPL_VIDEO_FRAMES", "90"))
RES = [1280, 720]


def setup_scene():
    ResetSession()
    if not os.path.isfile(VTK):
        print("Missing", VTK, file=sys.stderr)
        sys.exit(1)

    field = LegacyVTKReader(FileNames=[VTK])
    field.UpdatePipeline()

    # Symmetry-plane slice (main visual)
    sl = Slice(Input=field)
    sl.SliceType = "Plane"
    sl.SliceType.Origin = [3.0, 0.0, 0.5]
    sl.SliceType.Normal = [0.0, 1.0, 0.0]
    sl.UpdatePipeline()

    # Horizontal slice for 3D context
    sl_h = Slice(Input=field)
    sl_h.SliceType = "Plane"
    sl_h.SliceType.Origin = [3.0, 0.0, 0.20]
    sl_h.SliceType.Normal = [0.0, 0.0, 1.0]
    sl_h.UpdatePipeline()

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = RES
    try:
        view.BackgroundColorMode = "Gradient"
    except Exception:
        pass
    view.Background = [0.32, 0.34, 0.43]
    try:
        view.Background2 = [0.05, 0.05, 0.08]
    except Exception:
        pass
    view.OrientationAxesVisibility = 1

    lut = GetColorTransferFunction("SPL_dB")
    try:
        lut.ApplyPreset("Cool to Warm", True)
    except Exception:
        pass
    lut.RescaleTransferFunction(55.0, 105.0)
    GetOpacityTransferFunction("SPL_dB").RescaleTransferFunction(55.0, 105.0)

    d1 = Show(sl, view, "GeometryRepresentation")
    ColorBy(d1, ("POINTS", "SPL_dB"))
    d1.SetScalarBarVisibility(view, True)
    d1.Opacity = 0.95

    d2 = Show(sl_h, view, "GeometryRepresentation")
    ColorBy(d2, ("POINTS", "SPL_dB"))
    d2.Opacity = 0.75

    cont = Contour(Input=sl)
    cont.ContourBy = ["POINTS", "SPL_dB"]
    cont.Isosurfaces = [70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0]
    cont.UpdatePipeline()
    cd = Show(cont, view, "GeometryRepresentation")
    ColorBy(cd, ("POINTS", "SPL_dB"))
    cd.LineWidth = 2.0

    sb = GetScalarBar(lut, view)
    sb.Title = "SPL [dB re 20 uPa]"
    sb.ComponentTitle = ""
    sb.TitleFontSize = 12
    sb.LabelFontSize = 10
    sb.Visibility = 1
    sb.WindowLocation = "Any Location"
    sb.Position = [0.86, 0.12]
    sb.ScalarBarLength = 0.65

    if os.path.isfile(STL):
        body = STLReader(FileNames=[STL])
        body_xf = Transform(Input=body)
        body_xf.Transform = "Transform"
        body_xf.Transform.Translate = [0.1, 0.0, 0.0]
        bd = Show(body_xf, view, "GeometryRepresentation")
        bd.Representation = "Surface"
        bd.ColorArrayName = ["POINTS", ""]
        bd.DiffuseColor = [0.1, 0.1, 0.1]
        bd.Specular = 0.3

    if os.path.isfile(OBS):
        obs = LegacyVTKReader(FileNames=[OBS])
        glyph = Glyph(Input=obs, GlyphType="Sphere")
        try:
            glyph.OrientationArray = ["POINTS", "No orientation array"]
            glyph.ScaleArray = ["POINTS", "No scale array"]
        except Exception:
            pass
        glyph.ScaleFactor = 0.11
        glyph.GlyphMode = "All Points"
        try:
            glyph.GlyphType.Radius = 0.5
        except Exception:
            pass
        gd = Show(glyph, view, "GeometryRepresentation")
        gd.ColorArrayName = ["POINTS", ""]
        gd.DiffuseColor = [0.15, 1.0, 0.15]

    src = Sphere(Radius=0.055, Center=[1.094, 0.0, 0.1796])
    sd = Show(src, view, "GeometryRepresentation")
    sd.ColorArrayName = ["POINTS", ""]
    sd.DiffuseColor = [0.0, 1.0, 1.0]

    ann = Text(Text="Ahmed 25deg — SPL Curle proxy | ParaView 5.11")
    ad = Show(ann, view)
    ad.Color = [1, 1, 1]
    ad.FontSize = 16
    ad.Bold = 1
    ad.WindowLocation = "Upper Center"

    return view


def set_camera(view, angle_deg):
    """Orbit about vertical axis through wake centre (~x=2.5)."""
    focal = [2.5, 0.0, 0.35]
    radius = 5.2
    elev = 1.6
    rad = math.radians(angle_deg)
    pos = [
        focal[0] + radius * math.cos(rad),
        focal[1] + radius * math.sin(rad),
        focal[2] + elev,
    ]
    view.CameraParallelProjection = 0
    view.CameraViewAngle = 28.0
    view.CameraPosition = pos
    view.CameraFocalPoint = focal
    view.CameraViewUp = [0.0, 0.0, 1.0]


def main():
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR)
    os.makedirs(FRAME_DIR, exist_ok=True)

    view = setup_scene()
    print("Rendering %d frames → %s" % (N_FRAMES, FRAME_DIR))

    for i in range(N_FRAMES):
        # Full 360° orbit
        angle = 360.0 * i / float(N_FRAMES)
        set_camera(view, angle)
        Render()
        path = os.path.join(FRAME_DIR, "frame_%04d.png" % i)
        SaveScreenshot(path, view, ImageResolution=RES, TransparentBackground=0)
        if i % 10 == 0 or i == N_FRAMES - 1:
            print("  frame %d/%d  angle=%.1f" % (i + 1, N_FRAMES, angle))

    print("Done frames. Encode with: bash scripts/caa/encode_spl_video.sh")


if __name__ == "__main__":
    main()
