"""Gera as fontes embutidas nos cards (rodar só quando mudar fonte ou peso).

Baixa Inter e Inter Tight (variáveis) do google/fonts, fixa os pesos usados,
corta para Latin-1 + alguns símbolos e salva WOFF em fonts/.
Uso: python scripts/build_fonts.py
"""

import io
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"

SOURCES = {
    "inter": f"{BASE}/inter/Inter%5Bopsz,wght%5D.ttf",
    "inter-tight": f"{BASE}/intertight/InterTight%5Bwght%5D.ttf",
}

# (arquivo de saída, fonte, eixos)
TARGETS = [
    ("inter-400.woff", "inter", {"wght": 400, "opsz": 14}),
    ("inter-600.woff", "inter", {"wght": 600, "opsz": 14}),
    ("inter-tight-600.woff", "inter-tight", {"wght": 600}),
]

# Latin-1 (cobre acentos do português) + seta, ponto médio, travessão, estrela.
UNICODES = list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) + [
    0x2014, 0x2013, 0x2022, 0x2192, 0x2197, 0x2605, 0x2026,
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = {k: urllib.request.urlopen(u).read() for k, u in SOURCES.items()}
    for name, src, axes in TARGETS:
        font = TTFont(io.BytesIO(raw[src]))
        font = instancer.instantiateVariableFont(font, axes)
        opts = subset.Options()
        opts.flavor = "woff"
        opts.layout_features = ["kern", "liga", "calt", "tnum", "cv11", "ss01"]
        opts.name_IDs = ["*"]
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=UNICODES)
        sub.subset(font)
        font.flavor = "woff"
        font.save(OUT / name)
        print(name, (OUT / name).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
