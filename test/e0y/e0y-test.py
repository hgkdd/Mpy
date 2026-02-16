from mpylab.tools.gtem_e0y import GTEM

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

def build_cubic_grid(cell, Nx=120, Ny=120, Nz=120, zmin=None):
    """
    Erzeugt ein festes (Nz,Ny,Nx)-Gitter in physikalischen Koordinaten.
    y ist hier [0, h(zmax)] passend zu deinem Modell.
    """
    zmax = cell.zz
    if zmin is None:
        zmin = zmax / Nz  # vermeidet z=0

    x = np.linspace(-cell.a(zmax)/2, cell.a(zmax)/2, Nx)
    y = np.linspace(0.0, cell.h(zmax), Ny)
    z = np.linspace(zmin, zmax, Nz)

    # 3D grid (Nz,Ny,Nx)
    X, Y, Z = np.meshgrid(x, y, z, indexing="xy")   # (Ny,Nx,Nz)
    X = np.transpose(X, (2, 0, 1))
    Y = np.transpose(Y, (2, 0, 1))
    Z = np.transpose(Z, (2, 0, 1))

    return x, y, z, X, Y, Z

def evaluate_on_cubic_grid(cell, X, Y, Z, mask, max_m=100, chunk_size=20000):
    """
    Gibt V (Nz,Ny,Nx) zurück, außen NaN.
    """
    Nz, Ny, Nx = X.shape
    V = np.full((Nz, Ny, Nx), np.nan, dtype=float)

    # nur innere Punkte auswerten
    idx = np.where(mask.ravel())[0]
    if idx.size == 0:
        return V

    Xf = X.ravel()[idx]
    Yf = Y.ravel()[idx]
    Zf = Z.ravel()[idx]

    out = np.empty(idx.size, dtype=float)

    for i in range(0, idx.size, chunk_size):
        sl = slice(i, min(i + chunk_size, idx.size))
        out[sl] = cell.e0y(Xf[sl], Yf[sl], Zf[sl], max_m=max_m)

    V.ravel()[idx] = out
    return V


def inside_pyramid_mask(cell, X, Y, Z):
    """
    True für Punkte im Volumen: |x|<=a(z), 0<=y<=h(z).
    X,Y,Z sind (Nz,Ny,Nx).
    """
    aZ = cell.a(Z)   # nutzt numpy broadcasting, liefert (Nz,Ny,Nx)
    hZ = cell.h(Z)

    return (np.abs(X) <= 0.5 * aZ) & (Y >= 0.0) & (Y <= hZ)


def plotly_slicer_grid(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    V: np.ndarray,
    *,
    colorscale: str = "RdBu",
    renderer: str = "browser",
    symmetric_about_zero: bool = True,
    q_low: float = 0.02,
    q_high: float = 0.98,
    title_prefix: str = "e0y",
):
    """
    Interaktiver Plotly-Slicer für ein festes kubisches/rectangular Grid.
    - x: (Nx,)
    - y: (Ny,)
    - z: (Nz,)
    - V: (Nz, Ny, Nx) mit NaN außerhalb (Maske)

    Fixiert die Farbskala robust über eine globale coloraxis (kein "heimliches" Autoscaling).
    """

    pio.renderers.default = renderer

    x = np.asarray(x)
    y = np.asarray(y)
    z = np.asarray(z)
    V = np.asarray(V)

    if V.ndim != 3:
        raise ValueError("V muss Shape (Nz, Ny, Nx) haben.")
    Nz, Ny, Nx = V.shape
    if x.shape[0] != Nx or y.shape[0] != Ny or z.shape[0] != Nz:
        raise ValueError(f"Shape mismatch: x={x.shape}, y={y.shape}, z={z.shape}, V={V.shape}")

    finite = V[np.isfinite(V)]
    if finite.size == 0:
        raise ValueError("V enthält nur NaN/Inf – nichts darzustellen.")

    # Farbskala festlegen
    if symmetric_about_zero:
        absf = np.abs(finite)
        m = float(np.quantile(absf, q_high))  # z.B. 0.98 oder 0.99 statt global max
        cmin, cmax = -m, m
        cmid = 0
    else:
        cmin = float(np.quantile(finite, q_low))
        cmax = float(np.quantile(finite, q_high))
        cmid = None

    # Startindices
    z0, y0, x0 = Nz // 2, Ny // 2, Nx // 2

    # Helper: Heatmap mit globaler coloraxis (wichtig!)
    def heatmap_trace(slice2d, x_axis, y_axis):
        return go.Heatmap(
            z=slice2d,
            x=x_axis,
            y=y_axis,
            zauto=False,            # <- verhindert Autoscale am Trace
            coloraxis="coloraxis",  # <- Skala kommt aus Layout
            hovertemplate=f"{title_prefix}: %{{z}}<br>x=%{{x}}<br>y=%{{y}}<extra></extra>",
        )

    fig = go.Figure()

    # Initial: XY
    fig.add_trace(heatmap_trace(V[z0, :, :], x, y))

    # Globale Farbskala fixieren (DAS ist der entscheidende Fix)
    coloraxis = dict(
        cmin=cmin,
        cmax=cmax,
        cauto = False,
        colorscale=colorscale,
        colorbar=dict(title=title_prefix),
    )
    coloraxis["cmid"] = 0
    if cmid is not None:
        coloraxis["cmid"] = cmid

    fig.update_layout(
        coloraxis=dict(
        cmin=cmin,
        cmax=cmax,
        cauto=False,          # <- ABSOLUT notwendig
        colorscale=colorscale,
        cmid=0,               # <- für Vorzeichenfelder (optional, aber empfohlen)
        colorbar=dict(title=title_prefix),
    ),
        width=950,
        height=750,
        title=f"XY-Schnitt bei z={z[z0]:.6g}",
        xaxis_title="x",
        yaxis_title="y",
        margin=dict(l=10, r=10, t=60, b=10),
    )

    # Slider-Steps
    def steps_xy():
        steps = []
        for k in range(Nz):
            steps.append(dict(
                method="update",
                args=[
                    {"z": [V[k, :, :]], "x": [x], "y": [y]},
                    {"title": f"XY-Schnitt bei z={z[k]:.6g}",
                     "xaxis": {"title": "x"},
                     "yaxis": {"title": "y"}}
                ],
                label=str(k)
            ))
        return steps

    def steps_xz():
        steps = []
        for k in range(Ny):
            # XZ: (Nz, Nx) -> y-Achse ist z
            steps.append(dict(
                method="update",
                args=[
                    {"z": [V[:, k, :]], "x": [x], "y": [z]},
                    {"title": f"XZ-Schnitt bei y={y[k]:.6g}",
                     "xaxis": {"title": "x"},
                     "yaxis": {"title": "z"}}
                ],
                label=str(k)
            ))
        return steps

    def steps_yz():
        steps = []
        for k in range(Nx):
            # YZ: (Nz, Ny) -> x-Achse ist y, y-Achse ist z
            steps.append(dict(
                method="update",
                args=[
                    {"z": [V[:, :, k]], "x": [y], "y": [z]},
                    {"title": f"YZ-Schnitt bei x={x[k]:.6g}",
                     "xaxis": {"title": "y"},
                     "yaxis": {"title": "z"}}
                ],
                label=str(k)
            ))
        return steps

    slider_xy = dict(active=z0, currentvalue={"prefix": "z-Index: "}, steps=steps_xy())
    slider_xz = dict(active=y0, currentvalue={"prefix": "y-Index: "}, steps=steps_xz())
    slider_yz = dict(active=x0, currentvalue={"prefix": "x-Index: "}, steps=steps_yz())

    # Dropdown: setzt Modus + initiales Slice + passenden Slider
    fig.update_layout(
        updatemenus=[dict(
            type="dropdown",
            x=0.02,
            y=1.12,
            buttons=[
                dict(
                    label="XY (z-Schnitt)",
                    method="update",
                    args=[
                        {"z": [V[z0, :, :]], "x": [x], "y": [y]},
                        {"sliders": [slider_xy],
                         "title": f"XY-Schnitt bei z={z[z0]:.6g}",
                         "xaxis": {"title": "x"},
                         "yaxis": {"title": "y"}}
                    ],
                ),
                dict(
                    label="XZ (y-Schnitt)",
                    method="update",
                    args=[
                        {"z": [V[:, y0, :]], "x": [x], "y": [z]},
                        {"sliders": [slider_xz],
                         "title": f"XZ-Schnitt bei y={y[y0]:.6g}",
                         "xaxis": {"title": "x"},
                         "yaxis": {"title": "z"}}
                    ],
                ),
                dict(
                    label="YZ (x-Schnitt)",
                    method="update",
                    args=[
                        {"z": [V[:, :, x0]], "x": [y], "y": [z]},
                        {"sliders": [slider_yz],
                         "title": f"YZ-Schnitt bei x={x[x0]:.6g}",
                         "xaxis": {"title": "y"},
                         "yaxis": {"title": "z"}}
                    ],
                ),
            ],
        )],
        sliders=[slider_xy],
    )

    fig.show()
    return fig

if __name__ == '__main__':
    cell = GTEM(3.009, 1.5, 0.536, 5.9, Zc=50)
    results = cell.evaluate_function_on_points(cell.points, cell.e0y, max_m=1000, chunk_size=20000)

    # kubisches Gitter
    x, y, z, X, Y, Z = build_cubic_grid(cell, Nx=120, Ny=120, Nz=120)

    # Maske: außerhalb NaN
    mask = inside_pyramid_mask(cell, X, Y, Z)

    # Werte berechnen (nur innen)
    V = evaluate_on_cubic_grid(cell, X, Y, Z, mask, max_m=100, chunk_size=20000)

    #fig = plotly_slicer_grid(x, y, z, V, colorscale="RdBu", symmetric_about_zero=False, q_high=0.99, renderer="browser")
    fig = plotly_slicer_grid(x, y, z, V, colorscale="plasma", symmetric_about_zero=False, q_high=0.99, renderer="browser")
