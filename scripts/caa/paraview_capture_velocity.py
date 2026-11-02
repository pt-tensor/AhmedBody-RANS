# pvpython — ParaView screenshots of Ahmed-body velocity magnitude
# Run:
#   python3 scripts/caa/export_velocity_vtk.py
#   python3 scripts/caa/export_velocity_vtk.py --instantaneous
#   xvfb-run -a pvpython scripts/caa/paraview_capture_velocity.py
#
# Turbulence model in the CAA case: kOmegaSSTIDDES (hybrid RANS/LES), not pure LES.

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
    LegacyVTKReader,
    Render,
    ResetSession,
    STLReader,
    SaveScreenshot,
    Show,
    Slice,
    Text,
    Transform,
)


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Reports", "caa", "figures")
STL = os.path.join(ROOT, "constant", "triSurface", "ahmed_25deg_m.stl")


def capture(vtk_path, title, outfile, origin, normal, camera, umin=0.0, umax=62.0):
    print("Capturing", outfile)
    if not os.path.isfile(vtk_path):
        print("Missing", vtk_path, file=sys.stderr)
        sys.exit(1)

    ResetSession()
    field = LegacyVTKReader(FileNames=[vtk_path])
    field.UpdatePipeline()

    sl = Slice(Input=field)
    sl.SliceType = "Plane"
    sl.SliceType.Origin = list(origin)
    sl.SliceType.Normal = list(normal)
    sl.UpdatePipeline()

    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1920, 1080]
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
    view.CameraPosition = list(camera["pos"])
    view.CameraFocalPoint = list(camera["focal"])
    view.CameraViewUp = list(camera["up"])
    view.CameraParallelProjection = int(camera.get("parallel", 1))
    if view.CameraParallelProjection:
        view.CameraParallelScale = float(camera["scale"])
    else:
        view.CameraViewAngle = float(camera.get("angle", 30))

    lut = GetColorTransferFunction("U_magnitude")
    try:
        lut.ApplyPreset("Cool to Warm", True)
    except Exception:
        pass
    lut.RescaleTransferFunction(umin, umax)
    GetOpacityTransferFunction("U_magnitude").RescaleTransferFunction(umin, umax)

    disp = Show(sl, view, "GeometryRepresentation")
    ColorBy(disp, ("POINTS", "U_magnitude"))
    disp.SetScalarBarVisibility(view, True)

    # Contour lines of |U|
    cont = Contour(Input=sl)
    cont.ContourBy = ["POINTS", "U_magnitude"]
    cont.Isosurfaces = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    cont.UpdatePipeline()
    cd = Show(cont, view, "GeometryRepresentation")
    ColorBy(cd, ("POINTS", "U_magnitude"))
    cd.LineWidth = 1.5

    sb = GetScalarBar(lut, view)
    sb.Title = "|U| [m/s]"
    sb.ComponentTitle = ""
    sb.TitleFontSize = 14
    sb.LabelFontSize = 12
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
        bd.DiffuseColor = [1.0, 1.0, 1.0]
        bd.Specular = 0.2

    ann = Text(Text=title)
    ad = Show(ann, view)
    ad.Color = [1, 1, 1]
    ad.FontSize = 16
    ad.Bold = 1
    ad.WindowLocation = "Upper Center"

    # Re-apply camera after pipeline show
    view.CameraPosition = list(camera["pos"])
    view.CameraFocalPoint = list(camera["focal"])
    view.CameraViewUp = list(camera["up"])
    if view.CameraParallelProjection:
        view.CameraParallelScale = float(camera["scale"])
    Render()
    view.Update()
    Render()

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    SaveScreenshot(outfile, view, ImageResolution=[1920, 1080], TransparentBackground=0)
    print("  wrote", outfile)


def main():
    mean_vtk = os.path.join(ROOT, "Reports", "caa", "paraview", "velocity_mean.vtk")
    inst_vtk = os.path.join(ROOT, "Reports", "caa", "paraview", "velocity_instantaneous.vtk")

    cam_side = {
        "pos": [2.2, -5.5, 0.55],
        "focal": [2.2, 0.0, 0.45],
        "up": [0.0, 0.0, 1.0],
        "parallel": 1,
        "scale": 1.05,
    }
    cam_top = {
        "pos": [2.0, 0.0, 6.5],
        "focal": [2.0, 0.0, 0.20],
        "up": [0.0, 1.0, 0.0],
        "parallel": 1,
        "scale": 1.8,
    }
    cam_persp = {
        "pos": [4.8, -3.6, 2.4],
        "focal": [1.8, 0.0, 0.35],
        "up": [0.0, 0.0, 1.0],
        "parallel": 0,
        "angle": 28.0,
    }

    capture(
        mean_vtk,
        "Velocity |U| — symmetry (y=0) | IDDES-demo mean | ParaView 5.11",
        os.path.join(OUT, "paraview_velocity_symmetry.png"),
        origin=[2.0, 0.0, 0.5],
        normal=[0.0, 1.0, 0.0],
        camera=cam_side,
    )
    capture(
        mean_vtk,
        "Velocity |U| — horizontal (z=0.20 m) | IDDES-demo mean | ParaView 5.11",
        os.path.join(OUT, "paraview_velocity_horizontal.png"),
        origin=[2.0, 0.0, 0.20],
        normal=[0.0, 0.0, 1.0],
        camera=cam_top,
    )
    if os.path.isfile(inst_vtk):
        capture(
            inst_vtk,
            "Velocity |U| — symmetry (y=0) | IDDES-demo instantaneous | ParaView 5.11",
            os.path.join(OUT, "paraview_velocity_symmetry_instantaneous.png"),
            origin=[2.0, 0.0, 0.5],
            normal=[0.0, 1.0, 0.0],
            camera=cam_side,
        )
        capture(
            inst_vtk,
            "Velocity |U| — perspective | IDDES-demo instantaneous | ParaView 5.11",
            os.path.join(OUT, "paraview_velocity_perspective.png"),
            origin=[2.0, 0.0, 0.5],
            normal=[0.0, 1.0, 0.0],
            camera=cam_persp,
        )
    print("Done.")


if __name__ == "__main__":
    main()
