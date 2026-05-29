# view_3d.py
"""
Visualizador interativo do modelo 3D — não salva arquivos.

Controles:
  Mouse esquerdo (arrastar)  → rotacionar
  Scroll                      → zoom
  Mouse do meio + arrastar    → pan (mover câmera)
  R                            → resetar câmera
  Q ou Esc                     → fechar janela
"""

import rasterio
import numpy as np
from scipy.ndimage import gaussian_filter
from rasterio.windows import from_bounds

import vtkmodules.vtkFiltersGeneral   # noqa: F401
import vtkmodules.vtkFiltersCore      # noqa: F401

import pyvista as pv

# ----------------------------- CONFIG -----------------------------

DEM_PATH = r"D:\MARCUS\PRJ_GEOPROCESSAMENTO\PROJETOS\PRJ002_MAPA DE DECLIVIDADE BACIA DO ARARIPE\DATA_PRJ002\reprojetado_MDE_chapadadoararipe_raster_copernicus_global_DSM_30m.tif"
CLIP_BBOX   = (301_000, 9_141_000, 501_000, 9_221_000)
FATOR_REDUC = 2
EXAGERO     = 2.5
SIGMA_SUAVE = 1.2
ELEV_MIN    = 0
ELEV_MAX    = 1200

# ----------------------------- DADOS ------------------------------

src = rasterio.open(DEM_PATH)
window = from_bounds(*CLIP_BBOX, transform=src.transform)
z = src.read(1, window=window).astype(np.float32)
clip_transform = src.window_transform(window)
clip_height, clip_width = z.shape

if src.nodata is not None:
    z[z == src.nodata] = np.nan
z = np.nan_to_num(z, nan=np.nanmean(z))
z = np.clip(z, ELEV_MIN, ELEV_MAX)
z = np.flipud(z)

z_suave = gaussian_filter(z, sigma=SIGMA_SUAVE)
z_dec   = z_suave[::FATOR_REDUC, ::FATOR_REDUC]
z_vis   = z_dec * EXAGERO
z_cores = z[::FATOR_REDUC, ::FATOR_REDUC]

nrows, ncols = z_vis.shape
res_x = float(clip_transform[0])
res_y = abs(float(clip_transform[4]))

x = (np.arange(ncols) * res_x * FATOR_REDUC).astype(np.float32)
y = (np.arange(nrows) * res_y * FATOR_REDUC).astype(np.float32)
xx, yy = np.meshgrid(x, y)
grid = pv.StructuredGrid(xx, yy, z_vis)

elev_min_real = float(z.min())
elev_max_real = float(z.max())

# ----------------------------- VIEWER INTERATIVO ------------------
# Sem off_screen → abre janela com mouse/teclado

plotter = pv.Plotter(window_size=[1600, 1000])
plotter.set_background("#ffffff", top="#c8d4e0")

plotter.add_mesh(
    grid,
    scalars=z_cores.ravel(order="F"),
    cmap="terrain",
    clim=[elev_min_real, elev_max_real],
    smooth_shading=True,
    show_edges=False,
    lighting=True,
    scalar_bar_args={
        "title": "Elevação (m)",
        "title_font_size": 16,
        "label_font_size": 13,
        "shadow": False,
        "n_labels": 6,
        "vertical": True,
        "position_x": 0.88,
        "position_y": 0.15,
        "width": 0.04,
        "height": 0.65,
        "color": "black",
    },
)

plotter.enable_lightkit()

plotter.add_text(
    "Chapada do Araripe — Modelo 3D Interativo",
    position="upper_edge",
    font_size=14,
    color="black",
)
plotter.add_text(
    "Mouse esq: rotacionar   ·   Scroll: zoom   ·   Q ou Esc: sair",
    position="lower_edge",
    font_size=10,
    color="#555555",
)

# Câmera inicial obliqua a partir do Sul
x_max = float(ncols * res_x * FATOR_REDUC)
y_max = float(nrows * res_y * FATOR_REDUC)
plotter.camera_position = [
    (x_max / 2,           -y_max * 0.55, y_max * 0.50),
    (x_max / 2,            y_max * 0.55, elev_max_real * EXAGERO * 0.5),
    (0, 0, 1),
]

plotter.show()  # janela interativa