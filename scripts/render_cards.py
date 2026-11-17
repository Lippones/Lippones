"""Gera os cards SVG animados do README do perfil.

Lê dados do GitHub (GraphQL), mede texto com as fontes de fonts/ e escreve
cards/*.svg. Sem JS: animação só com <style> embutido no SVG.

Uso:
  python scripts/render_cards.py           # cards animados
  STATIC=1 python scripts/render_cards.py  # estado final, sem animação (preview)
Token: GH_TOKEN ou GITHUB_TOKEN; sem eles tenta `gh auth token`.
"""

from __future__ import annotations

import base64
import datetime as dt
import html
import json
import os
import re
import subprocess
import urllib.request
from collections import OrderedDict
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards"
FONTS = ROOT / "fonts"
DATA = ROOT / "data"
ICONS = ROOT / "assets" / "icons"

USER = "Lippones"
STATIC = os.environ.get("STATIC") == "1"

# ---------------------------------------------------------------- conteúdo
# Texto vem do lippe.dev. Edite aqui e rode o script de novo.

HERO = {
    "name": "Filipe Vieira",
    "role": "Desenvolvedor mobile e full-stack",
    "now": "Tech Lead Mobile e Backoffice na Inbazz",
    "site": "lippe.dev",
    "place": "Minas Gerais, BR",
}

TILES = [
    ("linkedin", "LinkedIn", "/in/filipe-vieira-dev"),
    ("instagram", "Instagram", "@filipev.silva"),
    ("portfolio", "Portfólio", "lippe.dev"),
]

ABOUT_BODY = [
    "Olá! 👋 Sou **Filipe Vieira**, **desenvolvedor mobile e full-stack** com 4 "
    "anos de experiência, hoje **Tech Lead de Mobile e Backoffice na Inbazz**. "
    "Sou bacharel em **Sistemas de Informação**.",
    "Na Inbazz, reconstruí sozinho o app dos creators, de FlutterFlow para "
    "**React Native**, sem tirar o app antigo do ar até o novo assumir. Antes "
    "foram três anos como full-stack na **bttis**, com TypeScript, React, Next, "
    "Nest e Docker, e antes disso dois anos de frontend.",
    "Meu foco é **React Native**, **TypeScript**, **Next.js** e **NestJS**, e "
    "gosto de ir até a API quando o app precisa. Fora do trabalho, desenvolvo "
    "produtos **micro SaaS** e projetos paralelos experimentais.",
]
ABOUT_FACTS = [
    ("Experiência", "4 anos"),
    ("Principal", "React Native · Expo"),
    ("Também", "TypeScript · NestJS · Next.js"),
    ("Infra", "Postgres · Docker · CI/CD"),
    ("Formação", "Sistemas de Informação"),
    ("Idiomas", "Português · Inglês"),
]

CAREER = [
    ("2026 —", "Inbazz", True,
     "Tech lead de mobile e backoffice. Reconstruí sozinho o app dos creators "
     "e hoje respondo por ele e pelo backoffice, no back e no front."),
    ("2023 — 2026", "bttis", False,
     "Desenvolvedor full-stack. React e Next com TypeScript no front, Nest e "
     "Express no back, Docker para subir tudo."),
    ("2021 — 2023", "Frontend", False,
     "JavaScript, React e muitas horas fora do horário. A obsessão por como "
     "as coisas parecem e reagem começou aqui."),
]

# (nome, slug do simple-icons ou None)
STACK = [
    ("React Native", "react"), ("Expo", "expo"), ("TypeScript", "typescript"),
    ("React", "react"), ("Next.js", "nextdotjs"), ("Node.js", "nodedotjs"),
    ("NestJS", "nestjs"), ("Fastify", "fastify"), ("Elysia", None),
    ("tRPC", "trpc"), ("Zod", "zod"), ("Prisma", "prisma"),
    ("PostgreSQL", "postgresql"), ("Redis", "redis"), ("BullMQ", None),
    ("Trigger.dev", None), ("Tailwind CSS", "tailwindcss"),
    ("Docker", "docker"), ("AWS", None), ("Vercel", "vercel"),
    ("GitHub Actions", "githubactions"),
]
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@15.0.0/icons/{}.svg"

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez"]

# ---------------------------------------------------------------- visual

BG = "#191919"
LINE = "#2a2a2a"
FG = "#f5f5f5"
SOFT = "#d6d6d6"
MUTED = "#a3a3a3"
DIM = "#6b6b6b"
HEAT = ["#222222", "#3a3a3a", "#6b6b6b", "#a8a8a8", "#f5f5f5"]

FONT_FILES = {
    "r": ("Inter", 400, "inter-400.woff"),
    "b": ("Inter", 600, "inter-600.woff"),
    "d": ("Inter Tight", 600, "inter-tight-600.woff"),
}

BASE_CSS = f"""
text{{font-family:Inter,system-ui,sans-serif;font-feature-settings:'cv11','ss01'}}
.r{{font-weight:400}}.b{{font-weight:600}}
.d{{font-family:'Inter Tight',Inter,sans-serif;font-weight:600}}
.fg{{fill:{FG}}}.so{{fill:{SOFT}}}.mu{{fill:{MUTED}}}.dim{{fill:{DIM}}}
.up{{text-transform:uppercase;letter-spacing:.06em}}
.tn{{font-feature-settings:'tnum','cv11','ss01'}}
"""

ANIM_CSS = """
.rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
@keyframes rise{from{opacity:0;transform:translateY(16px)}}
.fade{animation:fade .7s ease both}
@keyframes fade{from{opacity:0}}
.pop{animation:pop .5s cubic-bezier(.3,1.5,.5,1) both;transform-box:fill-box;transform-origin:center}
@keyframes pop{from{opacity:0;transform:scale(.2)}}
.grow{animation:grow .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box;transform-origin:50% 100%}
@keyframes grow{from{transform:scaleY(0)}}
.wipe{animation:wipe 1.1s cubic-bezier(.6,0,.2,1) both;transform-box:fill-box;transform-origin:0 50%}
@keyframes wipe{from{transform:scaleX(0)}}
.swing{animation:swing 1s cubic-bezier(.3,1.4,.5,1) both;transform-box:fill-box;transform-origin:50% 100%}
@keyframes swing{from{opacity:0;transform:translateY(34px) rotate(-5deg)}}
.cf{animation-name:show;animation-timing-function:step-end;animation-fill-mode:none}
.cl{animation-name:hide;animation-timing-function:step-end;animation-fill-mode:none}
@keyframes show{0%,100%{opacity:1}}
@keyframes hide{0%,100%{opacity:0}}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def delay(ms: float) -> str:
    return f' style="animation-delay:{ms:.0f}ms"'


# ---------------------------------------------------------------- fontes

class Metrics:
    def __init__(self, path: Path):
        font = TTFont(path)
        self.upm = font["head"].unitsPerEm
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]

    def width(self, s: str, size: float, tracking: float = 0) -> float:
        w = 0.0
        for ch in s:
            glyph = self.cmap.get(ord(ch))
            w += self.hmtx[glyph][0] / self.upm * size if glyph else size * 1.15
            w += tracking * size
        return w


M = {k: Metrics(FONTS / f) for k, (_, _, f) in FONT_FILES.items()}
_B64 = {k: base64.b64encode((FONTS / f).read_bytes()).decode()
        for k, (_, _, f) in FONT_FILES.items()}


def font_css(keys: str) -> str:
    out = []
    for k in keys:
        family, weight, _ = FONT_FILES[k]
        out.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{_B64[k]}) format('woff')}}"
        )
    return "".join(out)


def svg(w: int, h: int, body: str, fonts: str, title: str) -> str:
    css = font_css(fonts) + BASE_CSS + ("" if STATIC else ANIM_CSS)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><style>{css}</style>{body}</svg>\n"
    )


def frame(w: int, h: int, extra: str = "") -> str:
    return (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" '
            f'fill="{BG}" stroke="{LINE}"{extra}/>')


def heading(label: str, x: float, y: float, w: float, start: float = 0) -> str:
    return (
        f'<text x="{x}" y="{y}" class="r dim up" font-size="13">{esc(label)}</text>'
        f'<rect x="{x}" y="{y + 16}" width="{w}" height="1" fill="{LINE}" '
        f'class="wipe"{delay(start)}/>'
    )


# ---------------------------------------------------------------- texto

GLUE = "\x00"


def wrap(words: list[tuple[str, str]], size: float, max_w: float,
         space_key: str = "r") -> list[list[tuple[str, str]]]:
    """words = [(texto, chave_fonte)] -> linhas que cabem em max_w."""
    space = M[space_key].width(" ", size)
    lines, cur, cur_w = [], [], 0.0
    for text, key in words:
        glued = text.startswith(GLUE)
        text = text.lstrip(GLUE)
        ww = M[key].width(text, size)
        add = ww if not cur else (0 if glued else space) + ww
        if cur and cur_w + add > max_w:
            lines.append(cur)
            cur, cur_w = [(text, key)], ww
        else:
            cur.append(((GLUE if glued and cur else "") + text, key))
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def rich_words(s: str, normal: str = "r", bold: str = "b") -> list[tuple[str, str]]:
    out, prev_part = [], ""
    for i, part in enumerate(re.split(r"\*\*", s)):
        key = bold if i % 2 else normal
        words = part.split()
        if words and out and not part[0].isspace() and not prev_part[-1:].isspace():
            words[0] = GLUE + words[0]  # cola na palavra anterior, sem espaço
        out += [(w, key) for w in words]
        prev_part = part
    return out


def line_svg(line: list[tuple[str, str]], x: float, y: float, size: float,
             classes: dict[str, str], extra: str = "") -> str:
    spans, prev = [], None
    for text, key in line:
        glued = text.startswith(GLUE)
        piece = esc(text.lstrip(GLUE))
        if prev is not None and not glued:
            piece = " " + piece
        if key == prev and spans:
            spans[-1][1] += piece
        else:
            spans.append([key, piece])
        prev = key
    inner = "".join(f'<tspan class="{classes[k]}">{t}</tspan>' for k, t in spans)
    return f'<text x="{x}" y="{y}" font-size="{size}"{extra}>{inner}</text>'


def truncate_lines(text: str, size: float, max_w: float, max_lines: int,
                   key: str = "r") -> list[str]:
    lines = wrap([(w, key) for w in text.split()], size, max_w, key)
    out = [" ".join(t for t, _ in ln) for ln in lines]
    if len(out) > max_lines:
        out = out[:max_lines]
        last = out[-1]
        while M[key].width(last + "…", size) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        out[-1] = last.rstrip(",.;:") + "…"
    return out


def counter(x: float, y: float, value: int, cls: str, size: float,
            start: float, anchor: str = "start") -> str:
    attrs = f'x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"'
    if STATIC or value <= 0:
        return f'<text {attrs} class="{cls}">{value}</text>'
    frames, step = 18, 50
    out = []
    for i in range(frames):
        v = round(value * (1 - (1 - i / frames) ** 3))
        out.append(
            f'<text {attrs} class="{cls} cf" opacity="0" '
            f'style="animation-delay:{start + i * step:.0f}ms;'
            f'animation-duration:{step}ms">{v}</text>'
        )
    out.append(f'<text {attrs} class="{cls} cl" '
               f'style="animation-duration:{start + frames * step:.0f}ms">'
               f"{value}</text>")
    return "".join(out)


# ---------------------------------------------------------------- dados

QUERY = """
query($login:String!){user(login:$login){
  contributionsCollection{contributionCalendar{totalContributions
    weeks{contributionDays{date contributionCount}}}}
  repositories(privacy:PUBLIC,ownerAffiliations:OWNER){totalCount}
  pinnedItems(first:4,types:REPOSITORY){nodes{... on Repository{
    name description url stargazerCount forkCount
    primaryLanguage{name color}}}}
}}"""


def token() -> str | None:
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def load_data() -> dict:
    cache = DATA / "github.json"
    tok = token()
    if tok:
        try:
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=json.dumps({"query": QUERY,
                                 "variables": {"login": USER}}).encode(),
                headers={"Authorization": f"bearer {tok}",
                         "Content-Type": "application/json"},
            )
            payload = json.load(urllib.request.urlopen(req, timeout=30))
            if payload.get("data", {}).get("user"):
                DATA.mkdir(exist_ok=True)
                cache.write_text(json.dumps(payload["data"]["user"], indent=1))
                return payload["data"]["user"]
            print("GraphQL sem dados:", payload.get("errors"))
        except Exception as exc:  # cai no cache
            print("falha ao buscar dados, usando cache:", exc)
    return json.loads(cache.read_text())


def icon_path(slug: str | None) -> str | None:
    if not slug:
        return None
    ICONS.mkdir(parents=True, exist_ok=True)
    f = ICONS / f"{slug}.svg"
    if not f.exists():
        try:
            f.write_bytes(urllib.request.urlopen(SIMPLE_ICONS.format(slug),
                                                 timeout=20).read())
        except Exception:
            return None
    m = re.search(r'<path d="([^"]+)"', f.read_text())
    return m.group(1) if m else None


# ---------------------------------------------------------------- cards

PIXELS = {
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "V": ["#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."],
}


def card_hero() -> str:
    W, H, P = 1000, 330, 56
    b = [frame(W, H)]
    b.append(f'<g class="fade"{delay(0)}>'
             f'<text x="{P}" y="62" font-size="14" class="r mu">{esc(HERO["site"])}</text>'
             f'<text x="{W - P}" y="62" font-size="14" class="r mu" '
             f'text-anchor="end">{esc(HERO["place"])}</text></g>')

    # nome: camada escura sobe, camada clara entra num wipe por cima
    size, track = 84, -0.035
    name_w = M["d"].width(HERO["name"], size, track)
    ny = 182
    b.append(f'<defs><clipPath id="nameclip"><rect x="{P - 4}" y="{ny - size}" '
             f'width="{name_w + 12}" height="{size + 24}" class="wipe"'
             f'{delay(450)}/></clipPath></defs>')
    nm = (f'font-size="{size}" letter-spacing="{track}em" x="{P - 3}" y="{ny}"')
    b.append(f'<g class="rise"{delay(80)}>'
             f'<text {nm} class="d" fill="#333333">{esc(HERO["name"])}</text>'
             f'<text {nm} class="d fg" clip-path="url(#nameclip)">'
             f'{esc(HERO["name"])}</text></g>')

    b.append(f'<text x="{P}" y="232" font-size="26" class="d mu rise" '
             f'letter-spacing="-0.02em"{delay(650)}>{esc(HERO["role"])}</text>')

    # "digitando" a linha de agora, letra por letra
    x, size, start = P, 17, 1100
    b.append(f'<circle cx="{P + 4}" cy="{278}" r="4" fill="{FG}" class="pop"'
             f'{delay(start - 150)}/>')
    x = P + 18
    for i, ch in enumerate(HERO["now"]):
        if ch != " ":
            b.append(f'<text x="{x:.1f}" y="284" font-size="{size}" class="r so fade" '
                     f'style="animation-delay:{start + i * 26}ms;animation-duration:.15s">'
                     f"{esc(ch)}</text>")
        x += M["r"].width(ch, size)
    end = start + len(HERO["now"]) * 26
    b.append(f'<g class="fade"{delay(end)}><rect x="{x + 3:.1f}" y="270" width="2" '
             f'height="18" fill="{FG}" class="blink"/></g>')

    # monograma FV em pixels, no espírito do gráfico de contribuições
    cell, step = 13, 17
    gx0 = W - P - (11 * step - (step - cell))
    gy0 = 112
    for li, letter in enumerate("FV"):
        for r, row in enumerate(PIXELS[letter]):
            for c, on in enumerate(row):
                col = li * 6 + c
                shade = FG if on == "#" else "#212121"
                b.append(f'<rect x="{gx0 + col * step}" y="{gy0 + r * step}" '
                         f'width="{cell}" height="{cell}" rx="3" fill="{shade}" '
                         f'class="pop"{delay(300 + (r + col) * 45)}/>')
    return svg(W, H, "".join(b), "rd",
               f'{HERO["name"]}: {HERO["role"]}. {HERO["now"]}.')


def card_tile(i: int, key: str, title: str, handle: str) -> str:
    W, H = 330, 150
    b = [f'<g class="swing"{delay(250 + i * 140)}>', frame(W, H),
         f'<text x="26" y="40" font-size="13" class="r dim tn">0{i + 1}</text>',
         f'<text x="{W - 26}" y="42" font-size="20" class="r mu" '
         f'text-anchor="end">↗</text>',
         f'<text x="25" y="102" font-size="32" letter-spacing="-0.03em" '
         f'class="d fg">{esc(title)}</text>',
         f'<text x="26" y="128" font-size="14" class="r mu">{esc(handle)}</text>',
         "</g>"]
    return svg(W, H, "".join(b), "rd", f"{title}: {handle}")


def card_about() -> str:
    W, P = 1000, 56
    col_w = 560
    side_x = P + col_w + 56
    b = []
    y = 62
    head = heading("Sobre", P, y, W - 2 * P, 100)
    y += 50
    rows, n = [], 0
    for para in ABOUT_BODY:
        for ln in wrap(rich_words(para), 17, col_w):
            rows.append(line_svg(ln, P, y, 17, {"r": "r mu", "b": "b fg"},
                                 f' class="rise"{delay(200 + n * 70)}'))
            y += 29
            n += 1
        y += 14
    text_bottom = y

    fy = 124 - 20
    facts = []
    for k, (label, value) in enumerate(ABOUT_FACTS):
        d_ = delay(500 + k * 90)
        facts.append(
            f'<g class="rise"{d_}>'
            f'<text x="{side_x}" y="{fy}" font-size="12" class="r dim up">{esc(label)}</text>'
            f'<text x="{side_x}" y="{fy + 22}" font-size="15" class="r so">{esc(value)}</text>'
            f'<rect x="{side_x}" y="{fy + 38}" width="{W - P - side_x}" height="1" fill="{LINE}"/>'
            "</g>")
        fy += 58
    H = int(max(text_bottom, fy) + 22)
    b = [frame(W, H), head] + rows + facts
    alt = " ".join(p.replace("**", "") for p in ABOUT_BODY)
    return svg(W, H, "".join(b), "rbd", alt)


def card_career() -> str:
    W, P = 1000, 56
    b = []
    y = 62
    b.append(heading("Carreira", P, y, W - 2 * P, 100))
    y += 66
    tx = P + 200
    for i, (period, name, current, desc) in enumerate(CAREER):
        st = 250 + i * 160
        lines = truncate_lines(desc, 15, W - P - tx, 3)
        dot = (f'<circle cx="{P + 5}" cy="{y - 5}" r="5" fill="{FG}"/>'
               f'<circle cx="{P + 5}" cy="{y - 5}" r="9" fill="none" stroke="{FG}" '
               f'stroke-opacity=".35"/>' if current else
               f'<circle cx="{P + 5}" cy="{y - 5}" r="4" fill="{DIM}"/>')
        g = [f'<g class="rise"{delay(st)}>', dot,
             f'<text x="{P + 26}" y="{y}" font-size="14" class="r tn '
             f'{"so" if current else "mu"}">{esc(period)}</text>',
             f'<text x="{tx}" y="{y + 1}" font-size="22" letter-spacing="-0.02em" '
             f'class="d {"fg" if current else "so"}">{esc(name)}</text>']
        ly = y + 28
        for ln in lines:
            g.append(f'<text x="{tx}" y="{ly}" font-size="15" class="r mu">{esc(ln)}</text>')
            ly += 24
        g.append("</g>")
        b.append("".join(g))
        nxt = ly + 26
        if i < len(CAREER) - 1:
            b.append(f'<rect x="{P + 4.5}" y="{y + 12}" width="1" height="{nxt - y - 34}" '
                     f'fill="{LINE}" class="grow"{delay(st + 200)}/>')
        y = nxt
    H = int(y - 8)
    return svg(W, H, frame(W, H) + "".join(b), "rd",
               "Carreira: " + "; ".join(f"{p} {n}" for p, n, _, _ in CAREER))


def card_stack() -> str:
    W, P = 1000, 56
    b = []
    y = 62
    head = heading("Stack", P, y, W - 2 * P, 100)
    y += 46
    ch, gap, isz, fs = 42, 10, 18, 15
    x = P
    chips = []
    for i, (name, slug) in enumerate(STACK):
        d = icon_path(slug)
        tw = M["r"].width(name, fs)
        cw = 16 + (isz + 10 if d else 18) + tw + 18
        if x + cw > W - P:
            x, y = P, y + ch + gap
        icon = (f'<path transform="translate({x + 16},{y + (ch - isz) / 2}) '
                f'scale({isz / 24})" d="{d}" fill="{SOFT}"/>' if d else
                f'<rect x="{x + 17}" y="{y + ch / 2 - 4}" width="8" height="8" '
                f'rx="2" fill="{DIM}"/>')
        tx = x + 16 + (isz + 10 if d else 18)
        chips.append(
            f'<g class="pop"{delay(250 + i * 40)}>'
            f'<rect x="{x}" y="{y}" width="{cw:.1f}" height="{ch}" rx="21" '
            f'fill="#1f1f1f" stroke="{LINE}"/>{icon}'
            f'<text x="{tx:.1f}" y="{y + ch / 2 + 5.3}" font-size="{fs}" '
            f'class="r so">{esc(name)}</text></g>')
        x += cw + gap
    H = int(y + ch + 40)
    b = [frame(W, H), head] + chips
    return svg(W, H, "".join(b), "rd", "Stack: " + ", ".join(n for n, _ in STACK))


def calendar_days(user: dict) -> list[tuple[dt.date, int]]:
    cal = user["contributionsCollection"]["contributionCalendar"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"] for d in w["contributionDays"]]


def card_activity(user: dict) -> str:
    W, H, P = 1000, 340, 56
    days = calendar_days(user)
    total = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    active = sum(1 for _, c in days if c)
    public = user["repositories"]["totalCount"]

    last = days[-1][0]
    months: OrderedDict[tuple[int, int], int] = OrderedDict()
    y_, m_ = last.year, last.month
    keys = []
    for _ in range(12):
        keys.append((y_, m_))
        m_ -= 1
        if m_ == 0:
            y_, m_ = y_ - 1, 12
    for k in reversed(keys):
        months[k] = 0
    for d, c in days:
        if (d.year, d.month) in months:
            months[(d.year, d.month)] += c
    best_key = max(months, key=lambda k: months[k])
    best = months[best_key]

    b = [frame(W, H), heading("Atividade · últimos 12 meses", P, 62, W - 2 * P, 100)]
    stats = [
        (total, "contribuições"),
        (best, f"no melhor mês ({MONTHS[best_key[1] - 1]})"),
        (active, "dias com commit"),
        (public, "repositórios públicos"),
    ]
    for i, (val, label) in enumerate(stats):
        sx = P + (i % 2) * 200
        sy = 160 + (i // 2) * 104
        st = 300 + i * 120
        b.append(f'<g class="rise"{delay(st)}>'
                 + counter(sx - 2, sy, val, "d fg tn", 46, st + 150)
                 + f'<text x="{sx}" y="{sy + 26}" font-size="13" class="r mu">'
                 f"{esc(label)}</text></g>")

    bx0, bx1, base, top = 500, W - P, 272, 128
    n = len(months)
    gap = 10
    bw = (bx1 - bx0 - gap * (n - 1)) / n
    peak = max(best, 1)
    for i, ((yy, mm), c) in enumerate(months.items()):
        x = bx0 + i * (bw + gap)
        h = max(3, (base - top) * c / peak)
        is_best = (yy, mm) == best_key
        b.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" '
                 f'height="{h:.1f}" rx="4" fill="{FG if is_best else "#3a3a3a"}" '
                 f'class="grow"{delay(400 + i * 60)}/>')
        b.append(f'<text x="{x + bw / 2:.1f}" y="{base + 24}" font-size="12" '
                 f'text-anchor="middle" class="r {"fg" if is_best else "dim"}">'
                 f"{MONTHS[mm - 1]}</text>")
        if is_best:
            b.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 10:.1f}" '
                     f'font-size="13" text-anchor="middle" class="b fg tn fade"'
                     f'{delay(400 + i * 60 + 700)}>{c}</text>')
    alt = (f"{total} contribuições nos últimos 12 meses em {active} dias; "
           f"melhor mês: {MONTHS[best_key[1] - 1]} com {best}.")
    return svg(W, H, "".join(b), "rbd", alt)


def card_heatmap(user: dict) -> str:
    W = 1000
    cal = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    nweeks = len(cal)
    step = min(17.4, (W - 76) / nweeks)
    cell = step - 3.4
    x0 = (W - (nweeks * step - (step - cell))) / 2
    y0 = 58
    counts = sorted(c for w in cal for d in w["contributionDays"]
                    if (c := d["contributionCount"]) > 0)

    def level(c: int) -> int:
        if c == 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (0.25, 0.5, 0.75)]
        return 1 + sum(c > t for t in q)

    b = []
    last_month = None
    for wi, week in enumerate(cal):
        first = dt.date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and wi < nweeks - 2:
            if last_month is not None or first.day <= 7:
                b.append(f'<text x="{x0 + wi * step:.1f}" y="{y0 - 14}" font-size="12" '
                         f'class="r dim">{MONTHS[first.month - 1]}</text>')
            last_month = first.month
        for d in week["contributionDays"]:
            wd = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7  # dom = 0
            lv = level(d["contributionCount"])
            b.append(f'<rect x="{x0 + wi * step:.1f}" y="{y0 + wd * step:.1f}" '
                     f'width="{cell:.1f}" height="{cell:.1f}" rx="3" fill="{HEAT[lv]}" '
                     f'class="pop"{delay(150 + wi * 14 + wd * 10)}/>')
    gy = y0 + 7 * step + 30
    lx = W - x0 - (5 * step - 3.4) - 36
    b.append(f'<g class="fade"{delay(1000)}>'
             f'<text x="{lx - 10:.1f}" y="{gy + cell - 2:.1f}" font-size="12" '
             f'text-anchor="end" class="r dim">menos</text>')
    for i, c in enumerate(HEAT):
        b.append(f'<rect x="{lx + i * step:.1f}" y="{gy:.1f}" width="{cell:.1f}" '
                 f'height="{cell:.1f}" rx="3" fill="{c}"/>')
    b.append(f'<text x="{lx + 5 * step + 7:.1f}" y="{gy + cell - 2:.1f}" '
             f'font-size="12" class="r dim">mais</text></g>')
    H = int(gy + cell + 30)
    return svg(W, H, frame(W, H) + "".join(b), "r", "Gráfico de contribuições")


def card_repo(i: int, repo: dict) -> str:
    W, H, P = 490, 196, 28
    lang = repo.get("primaryLanguage") or {}
    desc = truncate_lines(repo.get("description") or "Sem descrição.", 14.5,
                          W - 2 * P, 3)
    b = [f'<g class="rise"{delay(150 + i * 120)}>', frame(W, H),
         f'<text x="{P - 1}" y="56" font-size="23" letter-spacing="-0.02em" '
         f'class="d fg">{esc(repo["name"])}</text>',
         f'<text x="{W - P}" y="54" font-size="18" class="r mu" '
         f'text-anchor="end">↗</text>']
    y = 88
    for ln in desc:
        b.append(f'<text x="{P}" y="{y}" font-size="14.5" class="r mu">{esc(ln)}</text>')
        y += 23
    fy = H - 26
    x = P
    if lang:
        b.append(f'<circle cx="{x + 5}" cy="{fy - 4.5}" r="5" '
                 f'fill="{lang.get("color") or MUTED}"/>')
        b.append(f'<text x="{x + 16}" y="{fy}" font-size="13" class="r so">'
                 f'{esc(lang["name"])}</text>')
        x += 16 + M["r"].width(lang["name"], 13) + 22
    b.append(f'<text x="{x}" y="{fy}" font-size="13" class="r so tn">'
             f'★ {repo["stargazerCount"]}</text>')
    b.append("</g>")
    return svg(W, H, "".join(b), "rd", f'{repo["name"]}: {repo.get("description") or ""}')


# ---------------------------------------------------------------- main

def main() -> None:
    CARDS.mkdir(exist_ok=True)
    user = load_data()
    out = {
        "hero.svg": card_hero(),
        "about.svg": card_about(),
        "career.svg": card_career(),
        "stack.svg": card_stack(),
        "activity.svg": card_activity(user),
        "heatmap.svg": card_heatmap(user),
    }
    for i, (key, title, handle) in enumerate(TILES):
        out[f"tile-{key}.svg"] = card_tile(i, key, title, handle)
    repos = [r for r in user["pinnedItems"]["nodes"] if r][:4]
    for f in CARDS.glob("repo-*.svg"):
        f.unlink()
    for i, repo in enumerate(repos):
        out[f"repo-{i + 1}.svg"] = card_repo(i, repo)
    for name, content in out.items():
        (CARDS / name).write_text(content)
        print(f"{name:22} {len(content) // 1024:4} KB")
    (ROOT / "README.md").write_text(readme(repos))


LINKS = {
    "linkedin": "https://www.linkedin.com/in/filipe-vieira-dev/",
    "instagram": "https://instagram.com/filipev.silva",
    "portfolio": "https://www.lippe.dev",
}


def readme(repos: list[dict]) -> str:
    """O README é gerado: edite aqui, não no README.md."""
    def img(f: str, w: str, alt: str) -> str:
        return f'<img src="./cards/{f}" width="{w}" alt="{esc(alt)}" />'

    tiles = "\n".join(
        f'  <a href="{LINKS[k]}">{img(f"tile-{k}.svg", "32.5%", t)}</a>'
        for k, t, _ in TILES)
    repo_rows = "\n".join(
        f'  <a href="{r["url"]}">{img(f"repo-{i + 1}.svg", "49.5%", r["name"])}</a>'
        for i, r in enumerate(repos))
    about_alt = "Sobre: " + ABOUT_BODY[0].replace("**", "")
    return f"""<!-- Gerado por scripts/render_cards.py. Não edite à mão. -->
<a href="{LINKS["portfolio"]}">{img("hero.svg", "100%", f'{HERO["name"]}, {HERO["role"]}')}</a>

<p>
{tiles}
</p>

{img("about.svg", "100%", about_alt)}

{img("career.svg", "100%", "Carreira")}

{img("stack.svg", "100%", "Stack")}

{img("activity.svg", "100%", "Atividade no GitHub")}

{img("heatmap.svg", "100%", "Gráfico de contribuições")}

<p>
{repo_rows}
</p>
"""


if __name__ == "__main__":
    main()
