# pvpython script — capture ParaView screenshots of Ahmed-body SPL contours.
# Run:
#   python3 scripts/caa/export_spl_vtk.py
#   xvfb-run -a pvpython scripts/caa/paraview_capture_spl.py
#
# Target: ParaView 5.11+

from __future__ import print_function

import os
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
OUT = os.path.join(ROOT, "Reports", "caa", "figures")


def _ensure_data():
    if not os.path.isfile(VTK):
        print(
            "Missing VTK — generate with: python3 scripts/caa/export_spl_vtk.py",
            file=sys.stderr,
        )
        sys.exit(1)


def _setup_view(view, camera):
    # ParaView 5.11+: BackgroundColorMode replaces UseGradientBackground
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
    view.CenterAxesVisibility = 0
    view.CameraPosition = list(camera["pos"])
    view.CameraFocalPoint = list(camera["focal"])
    view.CameraViewUp = list(camera["up"])
    view.CameraParallelProjection = int(camera.get("parallel", 0))
    if view.CameraParallelProjection:
        view.CameraParallelScale = float(camera["scale"])
    else:
        view.CameraViewAngle = float(camera.get("angle", 30.0))


def _configure_spl_lut():
    lut = GetColorTransferFunction("SPL_dB")
    try:
        lut.ApplyPreset("Cool to Warm", True)
    except Exception:
        lut.ApplyPreset("Cool to Warm (Extended)", True)
    lut.RescaleTransferFunction(55.0, 105.0)
    pw = GetOpacityTransferFunction("SPL_dB")
    pw.RescaleTransferFunction(55.0, 105.0)
    return lut


def _show_scalar_bar(view, lut):
    sb = GetScalarBar(lut, view)
    sb.Title = "SPL [dB re 20 uPa]"
    sb.ComponentTitle = ""
    sb.TitleFontSize = 14
    sb.LabelFontSize = 12
    sb.Visibility = 1
    sb.WindowLocation = "Any Location"
    sb.Position = [0.86, 0.12]
    sb.ScalarBarLength = 0.70
    return sb


def capture_slice(view_name, origin, normal, camera, outfile, use_contour=True):
    print("Capturing", outfile)
    ResetSession()

    field = LegacyVTKReader(FileNames=[VTK])
    field.UpdatePipeline()

    sl = Slice(Input=field)
    sl.SliceType = "Plane"
    sl.SliceType.Origin = list(origin)
    sl.SliceType.Normal = list(normal)
    try:
        sl.Triangulatetheslice = 0
    except Exception:
        pass
    sl.UpdatePipeline()

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1920, 1080]
    _setup_view(view, camera)

    lut = _configure_spl_lut()
    disp = Show(sl, view, "GeometryRepresentation")
    ColorBy(disp, ("POINTS", "SPL_dB"))
    disp.SetScalarBarVisibility(view, True)
    lut.RescaleTransferFunction(55.0, 105.0)
    GetOpacityTransferFunction("SPL_dB").RescaleTransferFunction(55.0, 105.0)
    _show_scalar_bar(view, lut)

    if use_contour:
        cont = Contour(Input=sl)
        cont.ContourBy = ["POINTS", "SPL_dB"]
        cont.Isosurfaces = [60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0]
        cont.UpdatePipeline()
        cd = Show(cont, view, "GeometryRepresentation")
        ColorBy(cd, ("POINTS", "SPL_dB"))
        cd.LineWidth = 2.0
        cd.Opacity = 0.95

    if os.path.isfile(STL):
        body = STLReader(FileNames=[STL])
        # STL raw bounds ≈ x∈[-0.1,0.944]; shift +0.1 so nose@0 matches case/probes
        body_xf = Transform(Input=body)
        body_xf.Transform = "Transform"
        body_xf.Transform.Translate = [0.1, 0.0, 0.0]
        bd = Show(body_xf, view, "GeometryRepresentation")
        bd.Representation = "Surface"
        bd.ColorArrayName = ["POINTS", ""]
        bd.DiffuseColor = [0.12, 0.12, 0.12]
        bd.Specular = 0.25
        bd.SpecularPower = 40.0

    if os.path.isfile(OBS):
        obs = LegacyVTKReader(FileNames=[OBS])
        glyph = Glyph(Input=obs, GlyphType="Sphere")
        try:
            glyph.OrientationArray = ["POINTS", "No orientation array"]
            glyph.ScaleArray = ["POINTS", "No scale array"]
        except Exception:
            pass
        glyph.ScaleFactor = 0.12
        glyph.GlyphMode = "All Points"
        try:
            glyph.GlyphType.Radius = 0.5
        except Exception:
            pass
        gd = Show(glyph, view, "GeometryRepresentation")
        gd.ColorArrayName = ["POINTS", ""]
        gd.DiffuseColor = [0.15, 1.0, 0.15]

    src = Sphere(Radius=0.06, Center=[1.094, 0.0, 0.1796])
    sd = Show(src, view, "GeometryRepresentation")
    sd.ColorArrayName = ["POINTS", ""]
    sd.DiffuseColor = [0.0, 1.0, 1.0]

    ann = Text(Text=view_name)
    ad = Show(ann, view)
    ad.Color = [1.0, 1.0, 1.0]
    ad.FontSize = 18
    ad.Bold = 1
    ad.WindowLocation = "Upper Center"

    _setup_view(view, camera)
    Render()
    view.Update()
    _setup_view(view, camera)
    Render()

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    SaveScreenshot(
        outfile,
        view,
        ImageResolution=[1920, 1080],
        TransparentBackground=0,
    )
    print("  wrote", outfile)


def main():
    _ensure_data()
    os.makedirs(OUT, exist_ok=True)

    capture_slice(
        view_name="SPL — symmetry plane (y = 0) | ParaView 5.11",
        origin=[3.0, 0.0, 0.5],
        normal=[0.0, 1.0, 0.0],
        camera={
            "pos": [3.2, -6.5, 0.9],
            "focal": [3.2, 0.0, 0.7],
            "up": [0.0, 0.0, 1.0],
            "parallel": 1,
            "scale": 1.35,
        },
        outfile=os.path.join(OUT, "paraview_spl_symmetry.png"),
    )

    capture_slice(
        view_name="SPL — horizontal plane (z = 0.20 m) | ParaView 5.11",
        origin=[3.0, 0.0, 0.20],
        normal=[0.0, 0.0, 1.0],
        camera={
            "pos": [3.2, 0.0, 8.0],
            "focal": [3.2, 0.0, 0.20],
            "up": [0.0, 1.0, 0.0],
            "parallel": 1,
            "scale": 2.4,
        },
        outfile=os.path.join(OUT, "paraview_spl_horizontal.png"),
    )

    capture_slice(
        view_name="SPL — perspective (slice y = 0) | ParaView 5.11",
        origin=[3.0, 0.0, 0.5],
        normal=[0.0, 1.0, 0.0],
        camera={
            "pos": [5.8, -4.2, 2.8],
            "focal": [2.5, 0.0, 0.4],
            "up": [0.0, 0.0, 1.0],
            "parallel": 0,
            "angle": 28.0,
        },
        outfile=os.path.join(OUT, "paraview_spl_perspective.png"),
    )

    print("Done.")


if __name__ == "__main__":
    main()
