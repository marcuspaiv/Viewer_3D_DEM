# dem_rotacao_video.py
"""
Vídeo MP4 de rotação 360° de qualquer DEM em CRS projetado (metros).

Para usar:
  1. Atualize DEM_PATH com o caminho do seu .tif
  2. Defina CLIP_BBOX se quiser recortar (no CRS do DEM), ou deixe None
  3. Ajuste EXAGERO conforme a escala do relevo (ver guia abaixo)
  4. python dem_rotacao_video.py

Pré-requisito: pip install imageio-ffmpeg
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
# Mude isto para cada novo DEM:

DEM_PATH    = r"D:\caminho\para\seu\DEM.tif"
CLIP_BBOX   = None          # ou (xmin, ymin, xmax, ymax) no CRS do DEM
EXAGERO     = 2.5           # ver guia abaixo
OUT_VIDEO   = None          # None → outputs/<nome_do_DEM>_rotacao.mp4

# Guia rápido do EXAGERO:
#   Relevo forte em área pequena (cordilheiras, cânions)   → 1.0–1.5
#   Relevo moderado em área média (chapadas, planaltos)    → 2.0–3.0
#   Relevo discreto em área grande (planícies, bacias)     → 3.5–6.0

# ======================== AJUSTES OPCIONAIS =========================

RESOLUCAO   = [1920, 1080]
FATOR_REDUC = 2
SIGMA_SUAVE = 1.2

N_FRAMES    = 720           # frames de uma volta completa
FPS         = 30            # → 24 s a 720 frames
ELEV_ANGLE  = 30            # graus da câmera acima do plano
DIST_FACTOR = 1.8           # raio da órbita (× maior dimensão do mesh)
QUALITY     = 8             # 0–10, qualidade de compressão H.264

# ============================ EXECUÇÃO =============================

src = rasterio.open(DEM_PATH)

# Aviso se o DEM estiver em coordenadas geográficas
if src.crs and src.crs.is_geographic:
    print("AVISO: o DEM está em coordenadas geográficas (lat/lon).")
    print("       O script assume CRS projetado (metros).")
    print("       Reprojete o DEM para UTM antes de rodar, ou o relevo sairá quase plano.\n")

# Nome de saída automático
if OUT_VIDEO is None:
    OUT_VIDEO = f"outputs/{Path(DEM_PATH).stem}_rotacao.mp4"
Path("outputs").mkdir(exist_ok=True)

# Leitura (recorte ou raster inteiro)
if CLIP_BBOX is not None:
    window = from_bounds(*CLIP_BBOX, transform=src.transform)
    z = src.read(1, window=window).astype(np.float32)
    clip_transform = src.window_transform(window)
else:
    z = src.read(1).astype(np.float32)
    clip_transform = src.transform

# Tratamento de nodata
if src.nodata is not None:
    z[z == src.nodata] = np.nan
z = np.nan_to_num(z, nan=np.nanmean(z))

# Clipe por percentil (robusto contra outliers extremos, preserva a faixa real)
p_lo, p_hi = np.percentile(z, [0.5, 99.5])
z = np.clip(z, p_lo, p_hi)
z = np.flipud(z)

# Suavização + decimação
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
z_c   = (elev_min_real + elev_max_real) / 2.0 * EXAGERO

# Diagnóstico
print(f"DEM:      {Path(DEM_PATH).name}")
print(f"  CRS:    {src.crs}")
print(f"  Área:   {x_max/1000:.1f} × {y_max/1000:.1f} km")
print(f"  Eleva.: {elev_min_real:.0f} a {elev_max_real:.0f} m")
print(f"  Exag.:  {EXAGERO}×")
print(f"  Saída:  {OUT_VIDEO}\n")

# Plotter
plotter = pv.Plotter(off_screen=True, window_size=RESOLUCAO)
plotter.set_background("#0a1424", top="#1c3a5e")

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

# Iluminação fixa NW
plotter.remove_all_lights()
luz = pv.Light(
    position=(-x_max, y_max * 2, y_max * 1.5),
    focal_point=(x_c, y_c, 0),
    intensity=0.95,
    light_type='scene light',
)
luz_amb = pv.Light(light_type='headlight', intensity=0.30)
plotter.add_light(luz)
plotter.add_light(luz_amb)

# Animação
focal_point = (x_c, y_c, z_c)
R = max(x_max, y_max) * DIST_FACTOR
elev_rad = np.radians(ELEV_ANGLE)

plotter.camera_position = [
    (focal_point[0], focal_point[1] - R * np.cos(elev_rad), focal_point[2] + R * np.sin(elev_rad)),
    focal_point,
    (0, 0, 1),
]
plotter.show(auto_close=False)
plotter.open_movie(OUT_VIDEO, framerate=FPS, quality=QUALITY)

print(f"Renderizando {N_FRAMES} frames a {RESOLUCAO[0]}x{RESOLUCAO[1]}...")
for i in range(N_FRAMES):
    azim_rad = np.radians((i / N_FRAMES) * 360.0)
    eye = (
        focal_point[0] + R * np.cos(elev_rad) * np.sin(azim_rad),
        focal_point[1] - R * np.cos(elev_rad) * np.cos(azim_rad),
        focal_point[2] + R * np.sin(elev_rad),
    )
    plotter.camera_position = [eye, focal_point, (0, 0, 1)]
    plotter.write_frame()
    if (i + 1) % 60 == 0:
        print(f"  {i + 1}/{N_FRAMES} frames")

plotter.close()
print(f"\nVídeo gerado: {OUT_VIDEO}")
print(f"Duração: {N_FRAMES / FPS:.1f} s  ·  {FPS} fps")