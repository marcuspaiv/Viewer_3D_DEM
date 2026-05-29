# v5b_compose.py
"""
Composição da vista cenital. Como é projeção ortogonal, o frame
de coordenadas UTM volta — desta vez geometricamente correto.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Polygon, Rectangle
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize
from matplotlib import cm
from datetime import datetime

# ----------------------------- INPUT ------------------------------

cena = mpimg.imread("outputs/araripe_top_down_scene.png")
meta = np.load("outputs/araripe_top_down_meta.npz")

x0, x1 = float(meta["x_utm0"]), float(meta["x_utm1"])
y0, y1 = float(meta["y_utm0"]), float(meta["y_utm1"])
emin, emax = float(meta["elev_min"]), float(meta["elev_max"])

OUT_FINAL = "outputs/araripe_mapa_cenital.png"

# ----------------------------- LAYOUT -----------------------------

fig = plt.figure(figsize=(16.5, 7.5), dpi=300)
fig.patch.set_facecolor("white")

# Calcula altura do ax_mapa para coincidir com o aspecto do DEM.
# Resultado: a borda do frame (com ticks UTM) toca exatamente as bordas
# da imagem do terreno, como em mapa cartográfico convencional.
dem_aspect = (x1 - x0) / (y1 - y0)
ax_width   = 0.78
ax_height  = (ax_width * fig.get_figwidth()) / (dem_aspect * fig.get_figheight())
ax_top = 0.84
ax_bottom  = ax_top - ax_height
ax_mapa = fig.add_axes([0.04, ax_bottom, ax_width, ax_height])
ax_mapa.imshow(cena, aspect="auto")
ax_mapa.set_xticks([])
ax_mapa.set_yticks([])
for s in ax_mapa.spines.values():
    s.set_color("black")
    s.set_linewidth(1.5)

# ------- Frame UTM com ticks (válido em projeção ortogonal) -------
n_ticks_x = 7
n_ticks_y = 5
x_ticks_utm = np.linspace(x0, x1, n_ticks_x)
y_ticks_utm = np.linspace(y0, y1, n_ticks_y)

ax_frame = fig.add_axes(ax_mapa.get_position(), frameon=False)
ax_frame.set_xlim(x0, x1)
ax_frame.set_ylim(y0, y1)
ax_frame.set_xticks(x_ticks_utm)
ax_frame.set_yticks(y_ticks_utm)
ax_frame.set_xticklabels([f"{int(v)}" for v in x_ticks_utm], fontsize=9)
ax_frame.set_yticklabels([f"{int(v)}" for v in y_ticks_utm], fontsize=9)
ax_frame.tick_params(direction="out", length=6, width=1, colors="black",
                     top=True, right=True, labeltop=False, labelright=False)
ax_frame.patch.set_alpha(0)

# ----------------------------- TÍTULO -----------------------------
fig.text(0.04, 0.93,
         "MODELO DIGITAL DE ELEVAÇÃO — CHAPADA DO ARARIPE",
         fontsize=20, fontweight="bold", color="#1a1a1a")
fig.text(0.04, 0.88,
         "Vista cenital  ·  Projeção ortogonal  ·  SIRGAS 2000 / UTM 24S",
         fontsize=10.5, color="#444444", style="italic")

# ----------------------------- BARRA DE ELEVAÇÃO ------------------
ax_cbar = fig.add_axes([0.86, ax_bottom + 0.03, 0.018, ax_height - 0.06])
norm = Normalize(vmin=emin, vmax=emax)
cb = ColorbarBase(ax_cbar, cmap=cm.terrain, norm=norm, orientation="vertical")
cb.set_label("Elevação (m)", fontsize=10, labelpad=8)
cb.ax.tick_params(labelsize=9)
cb.outline.set_linewidth(0.8)

# ----------------------------- ROSA DOS VENTOS --------------------
ax_norte = fig.add_axes([0.86, 0.86, 0.055, 0.06])
ax_norte.set_xlim(-1, 1); ax_norte.set_ylim(-1, 1)
ax_norte.axis("off")
seta_preta = Polygon([(0, 0.85), (-0.25, -0.55), (0, -0.25)],
                     closed=True, facecolor="black", edgecolor="black")
seta_branca = Polygon([(0, 0.85), (0.25, -0.55), (0, -0.25)],
                      closed=True, facecolor="white", edgecolor="black", linewidth=0.8)
ax_norte.add_patch(seta_preta)
ax_norte.add_patch(seta_branca)
ax_norte.text(0, -0.85, "N", ha="center", va="center", fontsize=14, fontweight="bold")

# ----------------------------- ESCALA GRÁFICA ---------------------
# Agora é escala REAL (sem perspectiva)
extensao_m = x1 - x0
escala_alvo = extensao_m / 4
candidatos = [1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5]
escala_m = min(candidatos, key=lambda v: abs(v - escala_alvo))
escala_km = escala_m / 1000

ax_esc = fig.add_axes([0.855, 0.05, 0.13, 0.04])
ax_esc.set_xlim(0, 4); ax_esc.set_ylim(0, 1)
ax_esc.axis("off")
for i in range(4):
    cor = "black" if i % 2 == 0 else "white"
    ax_esc.add_patch(Rectangle((i, 0.4), 1, 0.18,
                               facecolor=cor, edgecolor="black", linewidth=0.8))
for i, v in enumerate([0, escala_km/2, escala_km, escala_km*1.5, escala_km*2]):
    ax_esc.text(i, 0.30, f"{v:.0f}", ha="center", va="top", fontsize=8)
ax_esc.text(2, 0.78, "Escala (km)",
            ha="center", fontsize=8.5, style="italic", color="#444")

# ----------------------------- ESCALA NUMÉRICA ---------------------
# 1 cm no papel/tela = X cm no terreno  →  "1 : X"
# Assume a figura sendo apresentada no tamanho nominal (16,5 × 11,7 polegadas)
ax_pos        = ax_mapa.get_position()
map_width_cm  = fig.get_figwidth() * 2.54 * ax_pos.width   # cm na figura
real_width_cm = (x1 - x0) * 100                            # cm no terreno
escala_ratio  = round(real_width_cm / map_width_cm)

fig.text(0.92, 0.115, f"Escala  1 : {escala_ratio}",
         ha="center", fontsize=10, fontweight="bold", color="#222")

# ----------------------------- METADADOS --------------------------
metadados = (
    "FONTE   Copernicus Global DSM 30 m\n"
    "PROJ.   SIRGAS 2000 / UTM 24S  (EPSG:31984)\n"
    "DATUM   SIRGAS 2000\n"
    "RESOL.  30 × 30 m\n"
    f"ELEV.   {emin:.0f} – {emax:.0f} m\n"
    "PROJ.   Ortogonal cenital\n"
    f"DATA    {datetime.now().strftime('%m / %Y')}\n"
    "AUTOR   M. Paiva — Geologia"
)
fig.text(0.04, 0.005, metadados,
         fontsize=6.5, family="monospace",
         color="#222", verticalalignment="bottom", horizontalalignment="left",
         bbox=dict(boxstyle="round,pad=0.55", facecolor="#f5f5f5",
                   edgecolor="#888", linewidth=0.8))

fig.text(0.98, 0.025,
         "Processado em Python  ·  rasterio + pyvista + matplotlib",
         fontsize=7.5, color="#666", ha="right", style="italic",
         verticalalignment="bottom")

plt.savefig(OUT_FINAL, dpi=300, bbox_inches="tight", facecolor="white")
plt.close()
print(f"Mapa cenital: {OUT_FINAL}")