# render_cenital.py
"""
Vista cenital (top-down) do DEM em projeção ortogonal — imagem PNG.

Câmera fixa diretamente acima do centro do DEM, projeção paralela
ativada (sem perspectiva), eixo Y como 'up vector' → Norte no topo
e Leste à direita. Resultado: plan view com hillshading, sem moldura.

Para usar:
  1. Atualize DEM_PATH com o caminho do seu .tif
  2. Defina CLIP_BBOX se quiser recortar (no CRS do DEM), ou deixe None
  3. Ajuste EXAGERO conforme a escala do relevo (ver guia abaixo)
  4. python render_cenital.py
"""

from pathlib import Path
import rasterio
import numpy as np
from scipy.ndimage import gaussian_filter
from rasterio.windows import from_bounds

import vtkmodules.vtkFiltersGeneral   # noqa: F401
import vtkmodules.vtkFiltersCore      # noqa: F401

import pyvista as pv

# ====================== CONFIGURAÇÃO PRINCIPAL ======================

DEM_PATH    = r"D:\caminho\para\seu\DEM.tif"
CLIP_BBOX   = None          # ou (xmin, ymin, xmax, ymax) no CRS do DEM
EXAGERO     = 2.5           # ver guia abaixo
OUT_IMAGE   = None          # None → outputs/<nome_do_DEM>_cenital.png

# Guia rápido do EXAGERO:
#   Relevo forte em área pequena (cordilheiras, cânions)   → 1.0–1.5
#   Relevo moderado em área média (chapadas, planaltos)    → 2.0–3.0
#   Relevo discreto em área grande (planícies, bacias)     → 3.5–6.0

# ======================== AJUSTES OPCIONAIS =========================

RESOLUCAO_LARGURA = 3200    # altura é calculada pelo aspecto do DEM
FATOR_REDUC = 2
SIGMA_SUAVE = 1.2

# ============================ EXECUÇÃO =============================

src = rasterio.open(DEM_PATH)

if src.crs and src.crs.is_geographic:
    print("AVISO: o DEM está em coordenadas geográficas (lat/lon).")
    print("       O script assume CRS projetado (metros).")
    print("       Reprojete o DEM para UTM antes de rodar.\n")

if OUT_IMAGE is None:
    OUT_IMAGE = f"outputs/{Path(DEM_PATH).stem}_cenital.png"
Path("outputs").mkdir(exist_ok=True)

if CLIP_BBOX is not None:
    window = from_bounds(*CLIP_BBOX, transform=src.transform)
    z = src.read(1, window=window).astype(np.float32)
    clip_transform = src.window_transform(window)
else:
    z = src.read(1).astype(np.float32)
    clip_transform = src.transform

if src.nodata is not None:
    z[z == src.nodata] = np.nan
z = np.nan_to_num(z, nan=np.nanmean(z))

p_lo, p_hi = np.percentile(z, [0.5, 99.5])
z = np.clip(z, p_lo, p_hi)
z = np.flipud(z)  # Norte no topo

z_suave = gaussian_filter(z, sigma=SIGMA_SUAVE)
z_dec   = z_suave[::FATOR_REDUC, ::FATOR_REDUC]
z_vis   = z_dec * EXAGERO
z_cores = z[::FATOR_REDUC, ::FATOR_REDUC]

nrows, ncols = z_vis.shape
res_x = float(clip_transform[0])
res_y = abs(float(clip_transform[4]))

elev_min_real = float(z.min())
elev_max_real = float(z.max())

x = (np.arange(ncols) * res_x * FATOR_REDUC).astype(np.float32)
y = (np.arange(nrows) * res_y * FATOR_REDUC).astype(np.float32)
xx, yy = np.meshgrid(x, y)
grid = pv.StructuredGrid(xx, yy, z_vis)

x_max = float(ncols * res_x * FATOR_REDUC)
y_max = float(nrows * res_y * FATOR_REDUC)
x_c   = x_max / 2.0
y_c   = y_max / 2.0

# Resolução com aspecto idêntico ao DEM (sem áreas brancas no PNG)
dem_aspect = x_max / y_max
RESOLUCAO  = [RESOLUCAO_LARGURA, int(RESOLUCAO_LARGURA / dem_aspect)]

print(f"DEM:      {Path(DEM_PATH).name}")
print(f"  CRS:    {src.crs}")
print(f"  Área:   {x_max/1000:.1f} × {y_max/1000:.1f} km")
print(f"  Eleva.: {elev_min_real:.0f} a {elev_max_real:.0f} m")
print(f"  Exag.:  {EXAGERO}×")
print(f"  Saída:  {OUT_IMAGE}\n")

plotter = pv.Plotter(off_screen=True, window_size=RESOLUCAO)
plotter.set_background("white")

plotter.add_mesh(
    grid,
    scalars=z_cores.ravel(order="F"),
    cmap="terrain",
    clim=[elev_min_real, elev_max_real],
    smooth_shading=True,
    show_edges=False,
    lighting=True,
    show_scalar_bar=False,
)

# Iluminação fixa NW (mesmo padrão do vídeo de rotação)
plotter.remove_all_lights()
luz = pv.Light(
    position=(-x_max, y_max * 2, y_max * 1.5),
    focal_point=(x_c, y_c, 0),
    intensity=0.9,
    light_type='scene light',
)
luz_amb = pv.Light(light_type='headlight', intensity=0.35)
plotter.add_light(luz)
plotter.add_light(luz_amb)

# Câmera top-down ortogonal
plotter.camera_position = [
    (x_c, y_c, y_max * 1.8),    # eye: acima do centro
    (x_c, y_c, 0),               # focal: centro no nível do solo
    (0, 1, 0),                   # up: Norte no topo, Leste à direita
]
plotter.camera.parallel_projection = True
plotter.camera.parallel_scale = y_max / 2

plotter.show(auto_close=False)
plotter.screenshot(OUT_IMAGE, transparent_background=False)
plotter.close()

print(f"Vista cenital: {OUT_IMAGE}")