#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASMORRA DOS NÚMEROS
Roguelike voxel 3D isométrico: o herói enfrenta inimigos resolvendo contas.
O herói pode andar sozinho (automático) ou ser controlado por você (manual).
Precisa de Python 3 + pygame (pip install pygame). Tecla C abre as configurações.
"""
import heapq
import json
import math
import os
import time
import random
import struct
import sys
import threading
import traceback

import pygame

W, H = 960, 640
TW, TH, ZH = 60, 30, 30       # largura/altura do tile e altura de 1 voxel
N = 9                         # sala N x N
WALL_H = 3
OX, OY = W // 2, 178
FPS = 60
PLAT_X, PLAT_H = 4.0, 1.5     # plataforma (2º andar) das salas duplas
HEAL_EVERY = 3                # a vida só é restaurada a cada 3 andares
MAX_HEARTS = 6                # limite de vidas (carta Coração aumenta a vida máxima)
HERO_SCALE = 1.35             # escala com que o herói é desenhado (zumbi e esqueleto usam a mesma)

# ------------------------------------------------------------- configurações
try:
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "masmorra_config.json")
except NameError:
    CONFIG_PATH = "masmorra_config.json"
DEFAULT_CFG = {
    "mode": "auto",        # "auto" = o herói anda sozinho | "manual" = você controla (WASD / setas)
    "speed": 1.0,          # velocidade do herói (0.6 .. 1.6)
    "music": True,
    "music_vol": 1.0,      # 0.0 .. 1.0
    "sfx": True,           # efeitos sonoros
    "shake": True,         # tremor de tela nos golpes
}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, dv in DEFAULT_CFG.items():
                v = data.get(k)
                if isinstance(dv, bool):
                    if isinstance(v, bool):
                        cfg[k] = v
                elif isinstance(dv, float):
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        cfg[k] = float(v)
                elif isinstance(v, str):
                    cfg[k] = v
    except Exception:
        pass
    if cfg["mode"] not in ("auto", "manual"):
        cfg["mode"] = "auto"
    cfg["speed"] = min(1.6, max(0.6, cfg["speed"]))
    cfg["music_vol"] = min(1.0, max(0.0, cfg["music_vol"]))
    return cfg


def save_cfg(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ----------------------------------------------------------------- utilidades
def shade(c, f):
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))


def mix(c, t, other=(255, 255, 255)):
    t = max(0.0, min(1.0, t))
    return (int(c[0] + (other[0] - c[0]) * t),
            int(c[1] + (other[1] - c[1]) * t),
            int(c[2] + (other[2] - c[2]) * t))


def proj(x, y, z, cam=(0, 0)):
    return (OX + cam[0] + (x - y) * TW / 2,
            OY + cam[1] + (x + y) * TH / 2 - z * ZH)


def stair_h(x):
    """Altura do degrau k (0..4) da escada das salas duplas: 1.25, 1.0, 0.75, 0.5, 0.25."""
    return 1.25 - 0.25 * max(0, min(4, int((x - PLAT_X) / 0.2)))


def ground(x, y, duplo):
    """Altura do chão em (x, y). Salas duplas têm plataforma + escada de 5 degraus."""
    if not duplo:
        return 0.0
    if x < PLAT_X:
        return PLAT_H
    if 3.0 <= y <= 5.0 and x < PLAT_X + 1.0:
        return stair_h(x)
    return 0.0


_TEX = random.Random(1234)


def draw_box(surf, x, y, z, w, d, h, color, cam=(0, 0), outline=True, g=0.0, tex=0.0, bevel=False, ao=False):
    """Voxel/caixa com 3 faces visíveis (topo, esquerda, direita).
    g > 0 desenha a grade de mini-voxels sobre as faces.
    tex > 0 dá a cada mini-voxel um tom levemente diferente (pedra); bevel realça as quinas;
    ao escurece a base das faces laterais (oclusão ambiente)."""
    p = lambda a, b, c: proj(a, b, c, cam)
    ct, cl, cr = shade(color, 1.15), shade(color, 0.82), shade(color, 0.60)
    top = [p(x, y, z + h), p(x + w, y, z + h), p(x + w, y + d, z + h), p(x, y + d, z + h)]
    left = [p(x, y + d, z), p(x + w, y + d, z), p(x + w, y + d, z + h), p(x, y + d, z + h)]
    right = [p(x + w, y, z), p(x + w, y + d, z), p(x + w, y + d, z + h), p(x + w, y, z + h)]
    nx = ny = nz = 1
    if g > 0:
        nx, ny, nz = max(1, int(round(w / g))), max(1, int(round(d / g))), max(1, int(round(h / g)))
    sx_, sy_, sz_ = w / nx, d / ny, h / nz
    if tex > 0 and g > 0:
        rnd = _TEX.random
        zt = z + h
        for i in range(nx):
            for j in range(ny):
                q = [p(x + i * sx_, y + j * sy_, zt), p(x + (i + 1) * sx_, y + j * sy_, zt),
                     p(x + (i + 1) * sx_, y + (j + 1) * sy_, zt), p(x + i * sx_, y + (j + 1) * sy_, zt)]
                pygame.draw.polygon(surf, shade(ct, 1 + (rnd() * 2 - 1) * tex), q)
        for i in range(nx):
            for k in range(nz):
                q = [p(x + i * sx_, y + d, z + k * sz_), p(x + (i + 1) * sx_, y + d, z + k * sz_),
                     p(x + (i + 1) * sx_, y + d, z + (k + 1) * sz_), p(x + i * sx_, y + d, z + (k + 1) * sz_)]
                pygame.draw.polygon(surf, shade(cl, 1 + (rnd() * 2 - 1) * tex), q)
        for j in range(ny):
            for k in range(nz):
                q = [p(x + w, y + j * sy_, z + k * sz_), p(x + w, y + (j + 1) * sy_, z + k * sz_),
                     p(x + w, y + (j + 1) * sy_, z + (k + 1) * sz_), p(x + w, y + j * sy_, z + (k + 1) * sz_)]
                pygame.draw.polygon(surf, shade(cr, 1 + (rnd() * 2 - 1) * tex), q)
    else:
        pygame.draw.polygon(surf, ct, top)
        pygame.draw.polygon(surf, cl, left)
        pygame.draw.polygon(surf, cr, right)
    if g > 0:
        k_ = 0.93 if tex > 0 else 0.90
        lt, ll, lr = shade(ct, k_), shade(cl, k_), shade(cr, k_)
        for i in range(1, nx):
            xx = x + i * sx_
            pygame.draw.line(surf, lt, p(xx, y, z + h), p(xx, y + d, z + h))
            pygame.draw.line(surf, ll, p(xx, y + d, z), p(xx, y + d, z + h))
        for j in range(1, ny):
            yy = y + j * sy_
            pygame.draw.line(surf, lt, p(x, yy, z + h), p(x + w, yy, z + h))
            pygame.draw.line(surf, lr, p(x + w, yy, z), p(x + w, yy, z + h))
        for k in range(1, nz):
            zz = z + k * sz_
            pygame.draw.line(surf, ll, p(x, y + d, zz), p(x + w, y + d, zz))
            pygame.draw.line(surf, lr, p(x + w, y, zz), p(x + w, y + d, zz))
    if ao and h > 0.3:
        band = min(0.2, h * 0.3)
        pygame.draw.polygon(surf, shade(cl, 0.80), [p(x, y + d, z), p(x + w, y + d, z), p(x + w, y + d, z + band), p(x, y + d, z + band)])
        pygame.draw.polygon(surf, shade(cr, 0.80), [p(x + w, y, z), p(x + w, y + d, z), p(x + w, y + d, z + band), p(x + w, y, z + band)])
    if bevel:
        pygame.draw.line(surf, mix(ct, 0.30), p(x, y + d, z + h), p(x + w, y + d, z + h), 2)
        pygame.draw.line(surf, mix(ct, 0.16), p(x + w, y, z + h), p(x + w, y + d, z + h), 2)
        pygame.draw.line(surf, mix(cl, 0.14), p(x + w, y + d, z), p(x + w, y + d, z + h))
    if outline:
        e = shade(color, 0.36)
        for poly in (top, left, right):
            pygame.draw.polygon(surf, e, poly, 1)


def wbox(surf, ax, v, a, la, z, h, t, color, off=0.0, g=0.0, cam=(0, 0), **kw):
    """Caixa colada na parede. ax='x': parede em x=0 (corre ao longo de y); ax='y': parede em y=0.
    v+a = início ao longo da parede, la = comprimento, t = espessura, off = distância da parede."""
    if ax == "x":
        draw_box(surf, off, v + a, z, t, la, h, color, cam, g=g, **kw)
    else:
        draw_box(surf, v + a, off, z, la, t, h, color, cam, g=g, **kw)


# ------------------------------------------------------------------ paletas
PALS = [  # chão A, chão B, parede A, parede B, fundo, bandeira
    ((124, 114, 104), (106, 97, 90), (96, 90, 104), (80, 74, 88), (18, 16, 26), (170, 40, 50)),
    ((74, 126, 86), (62, 108, 74), (88, 104, 92), (72, 88, 76), (10, 22, 18), (200, 150, 40)),
    ((134, 86, 74), (112, 70, 62), (120, 64, 60), (100, 54, 52), (30, 12, 12), (240, 170, 40)),
    ((134, 174, 206), (114, 154, 188), (124, 154, 184), (104, 134, 170), (12, 20, 36), (60, 110, 220)),
    ((114, 84, 136), (98, 70, 118), (94, 70, 114), (80, 58, 100), (22, 12, 32), (230, 90, 200)),
]


def build_room(pal, duplo, seed, lay=None):
    fa, fb, wa, wb, _, ban = pal
    rng = random.Random(seed)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rock = shade(fb, 0.46)

    # ilha flutuante: camadas de rocha irregular sob o piso
    for layer, (z0, lo, hi, keep) in enumerate(((-1.25, -1, N, 0.80), (-1.9, 1, N - 1, 0.72), (-2.5, 2, N - 2, 0.65))):
        for x in range(lo, hi):
            for y in range(lo, hi):
                if rng.random() > keep and layer > 0:
                    continue
                if layer == 0 and (x == N - 1 or y == N - 1) and rng.random() < 0.3:
                    continue
                draw_box(s, x, y, z0, 1, 1, 0.65, shade(rock, 0.92 - 0.1 * layer + rng.uniform(-0.04, 0.04)),
                         g=0.34, tex=0.07)

    # piso: ladrilhos com variação, sombra junto às paredes, rachaduras e musgo
    for x in range(-1, N):
        for y in range(-1, N):
            if x < 0 or y < 0:
                c = shade(wa, 0.55)
            else:
                c = shade(fa if (x + y) % 2 == 0 else fb, rng.uniform(0.95, 1.05))
                if x == 0 or y == 0:
                    c = shade(c, 0.84)
                elif x == 1 or y == 1:
                    c = shade(c, 0.93)
            draw_box(s, x, y, -0.6, 1, 1, 0.55, c, g=0.2, tex=0.05, bevel=True)
            if x >= 0 and y >= 0 and rng.random() < 0.13:
                px_, py_ = rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8)
                for _ in range(3):
                    qx = max(0.05, min(0.95, px_ + rng.uniform(-0.28, 0.28)))
                    qy = max(0.05, min(0.95, py_ + rng.uniform(-0.28, 0.28)))
                    pygame.draw.line(s, shade(c, 0.62), proj(x + px_, y + py_, -0.05), proj(x + qx, y + qy, -0.05))
                    px_, py_ = qx, qy

    # paredes: pedra com variação, base musgosa, cornija no topo e rodapé
    for x in range(-1, N):
        for y in range(-1, N):
            if x < 0 or y < 0:
                for z in range(WALL_H):
                    c = shade(wa if (x + y + z) % 2 == 0 else wb, rng.uniform(0.94, 1.06))
                    if z == 0:
                        c = shade(c, 0.88)
                        if rng.random() < 0.2:
                            c = mix(c, 0.3, (58, 112, 58))
                    draw_box(s, x, y, z, 1, 1, 1, c, g=0.2, tex=0.05, ao=(z == 0))
                draw_box(s, x, y, WALL_H, 1, 1, 0.14, mix(wa, 0.14), g=0.25, tex=0.04, bevel=True)
    for i in range(N):
        zx = ground(0.1, i + 0.5, duplo)
        zy = ground(i + 0.5, 0.1, duplo)
        draw_box(s, 0, i, zx, 0.16, 1, 0.2, shade(wa, 0.72), g=0.1, tex=0.04, bevel=True)
        draw_box(s, i, 0, zy, 1, 0.16, 0.2, shade(wa, 0.72), g=0.1, tex=0.04, bevel=True)

    if duplo:
        # plataforma (2º andar) + escada de 5 degraus + guarda-corpo, ordenados de trás pra frente
        dl = []

        def add(x, y, z, w, d, h, c, **kw):
            dl.append((x + w / 2 + y + d / 2, z, (x, y, z, w, d, h, c), kw))

        for x in range(int(PLAT_X)):
            for y in range(N):
                c = shade(fa if (x + y) % 2 == 0 else fb, 0.92)
                add(x, y, 0, 1, 1, PLAT_H, c, g=0.2, tex=0.05, bevel=True, ao=True)
        stone = shade(wb, 0.9)
        for k in range(5):
            x0, hk = PLAT_X + 0.2 * k, 1.25 - 0.25 * k
            add(x0, 2.86, 0, 0.2, 0.14, hk + 0.22, stone, g=0.1, tex=0.04, bevel=True)
            add(x0, 3.0, 0, 0.2, 2.0, hk, mix(fa, 0.08 if k % 2 else 0.0), g=0.2, tex=0.05, bevel=True)
            add(x0, 5.0, 0, 0.2, 0.14, hk + 0.22, stone, g=0.1, tex=0.04, bevel=True)
        for yy in (2.80, 5.06):
            add(PLAT_X - 0.1, yy, PLAT_H, 0.16, 0.16, 0.62, (150, 108, 60), g=0.08, bevel=True)
            add(PLAT_X + 0.9, yy + 0.0, 0.0, 0.16, 0.16, 0.62, (150, 108, 60), g=0.08, bevel=True)
        for y in range(N):
            if 3 <= y <= 4:
                continue
            add(PLAT_X - 0.16, y + 0.42, PLAT_H, 0.12, 0.14, 0.52, (120, 84, 50), g=0.08, bevel=True)
            add(PLAT_X - 0.14, y, PLAT_H + 0.40, 0.08, 1.0, 0.07, (160, 118, 66), bevel=True)
        dl.sort(key=lambda it: (round(it[0], 3), it[1]))
        for _, _, args, kw in dl:
            draw_box(s, *args, **kw)
    elif rng.random() < 0.6:
        # tapete retangular (só em salas planas)
        horiz = rng.random() < 0.5
        rw, rd = (3, 2) if horiz else (2, 3)
        rx, ry = rng.randint(2, N - rw - 1), rng.randint(2, N - rd - 1)
        base = shade(ban, 0.62)
        draw_box(s, rx, ry, -0.05, rw, rd, 0.04, base, outline=False, g=0.25, tex=0.04)
        draw_box(s, rx + 0.18, ry + 0.18, -0.01, rw - 0.36, rd - 0.36, 0.03, shade(ban, 0.85), outline=False, g=0.25, tex=0.04)
        draw_box(s, rx + 0.34, ry + 0.34, 0.02, rw - 0.68, rd - 0.68, 0.02, (222, 188, 90), outline=False, g=0.25, tex=0.03)
        draw_box(s, rx + 0.46, ry + 0.46, 0.04, rw - 0.92, rd - 0.92, 0.02, shade(ban, 0.7), outline=False, g=0.25, tex=0.04)

    # bandeiras nas paredes (posições sorteadas por andar)
    gold = (240, 205, 80)
    for ax, v in (lay["banners"] if lay else [("x", 4.0), ("y", 4.0)]):
        z0 = ground(0.1, v + 0.5, duplo) if ax == "x" else ground(v + 0.5, 0.1, duplo)
        bz = z0 + 0.55
        wbox(s, ax, v, 0.0, 1.0, bz, 0.95, 0.07, ban, g=0.2, tex=0.04)
        wbox(s, ax, v, -0.05, 1.10, bz + 0.95, 0.07, 0.11, (150, 110, 52), g=0.1)
        wbox(s, ax, v, -0.08, 0.10, bz + 0.92, 0.13, 0.13, gold, g=0.05)
        wbox(s, ax, v, 0.98, 0.10, bz + 0.92, 0.13, 0.13, gold, g=0.05)
        wbox(s, ax, v, 0.34, 0.32, bz + 0.5, 0.10, 0.10, gold, off=0.0, outline=False)
        wbox(s, ax, v, 0.45, 0.10, bz + 0.34, 0.42, 0.10, gold, off=0.0, outline=False)
        for fa_ in (0.08, 0.45, 0.82):
            wbox(s, ax, v, fa_, 0.10, bz - 0.10, 0.10, 0.06, gold, g=0.05, outline=False)

    # deco solta: pedrinhas com sombra e tufos de musgo em voxels
    rub = []
    for _ in range(26):
        x, y = rng.uniform(0.25, N - 0.7), rng.uniform(0.25, N - 0.7)
        if duplo and 2.9 < x < 5.4 and 2.5 < y < 5.5:
            continue
        kind = rng.choice(["stone", "stone", "moss"])
        rub.append((x + y, x, y, rng.uniform(0.08, 0.22), kind))
    rub.sort()
    for _, x, y, sz, kind in rub:
        gz = ground(x, y, duplo)
        if kind == "moss":
            for _ in range(rng.randint(3, 6)):
                mx, my = x + rng.uniform(-0.18, 0.18), y + rng.uniform(-0.18, 0.18)
                mh = rng.uniform(0.03, 0.08)
                draw_box(s, mx, my, gz, 0.1, 0.1, mh, shade((70, 130, 70), rng.uniform(0.8, 1.2)), outline=False)
        else:
            draw_box(s, x, y, gz, sz, sz, sz * 0.8, shade(fa, 0.6 + rng.random() * 0.3), g=0)
            draw_box(s, x + sz * 0.15, y + sz * 0.15, gz + sz * 0.8, sz * 0.55, sz * 0.55, sz * 0.3,
                     shade(fa, 0.8 + rng.random() * 0.2), outline=False)
    return s


# ------------------------------------------------------------- poço de escada
def draw_stairwell(scr, sx, sy, gz, cam, t, pal, glows=None):
    """Poço com degraus de voxel descendo, borda de pedra, gemas pulsantes e seta flutuante."""
    wa = pal[2]
    a, rim = 0.62, 0.16
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    P = lambda x, y, z: proj(x, y, z, cam)
    pygame.draw.polygon(scr, (6, 8, 18), [P(sx - a, sy - a, gz), P(sx + a, sy - a, gz), P(sx + a, sy + a, gz), P(sx - a, sy + a, gz)])
    bw = 0.14
    stone = shade(wa, 1.0)
    # paredes de trás (a face interna fica visível)
    draw_box(scr, sx - a, sy - a, gz - 0.6, bw, 2 * a, 0.6 + rim, stone, cam, g=0.2, bevel=True)
    draw_box(scr, sx - a + bw, sy - a, gz - 0.6, 2 * a - bw, bw, 0.6 + rim, shade(stone, 0.95), cam, g=0.2, bevel=True)
    # fundo brilhante + degraus descendo em direção à frente
    glow_c = mix((24, 60, 140), 0.25 + 0.35 * pulse, (90, 190, 255))
    pygame.draw.polygon(scr, glow_c, [P(sx - a + bw, sy - a + bw, gz - 0.55), P(sx + a - bw, sy - a + bw, gz - 0.55),
                                      P(sx + a - bw, sy + a - bw, gz - 0.55), P(sx - a + bw, sy + a - bw, gz - 0.55)])
    inner = 2 * a - 2 * bw
    for k in range(5):
        top = gz - 0.07 - 0.12 * k
        col = shade(wa, 0.95 - 0.09 * k)
        draw_box(scr, sx - a + bw, sy - a + bw + k * 0.19, gz - 0.58, inner, 0.19, top - (gz - 0.58), col, cam, g=0.19)
    if glows:
        gi = glows[min(len(glows) - 1, int(pulse * len(glows)))]
        gp = P(sx, sy, gz - 0.3)
        scr.blit(gi, (gp[0] - gi.get_width() // 2, gp[1] - gi.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)
    # bordas da frente
    draw_box(scr, sx + a - bw, sy - a, gz, bw, 2 * a, rim, stone, cam, g=0.2, bevel=True)
    draw_box(scr, sx - a, sy + a - bw, gz, 2 * a - bw, bw, rim, shade(stone, 0.95), cam, g=0.2, bevel=True)
    gem = mix((50, 130, 255), 0.55 * pulse)
    for cx_, cy_ in ((sx - a, sy - a), (sx + a - 0.12, sy - a), (sx - a, sy + a - 0.12), (sx + a - 0.12, sy + a - 0.12)):
        draw_box(scr, cx_, cy_, gz + rim, 0.12, 0.12, 0.1, gem, cam, outline=False)
    # seta ▼ flutuante
    bob = 0.08 * math.sin(t * 4)
    ac = mix((70, 150, 255), 0.3 + 0.3 * pulse)
    for i, (wd, zz) in enumerate(((0.34, 0.0), (0.24, 0.1), (0.14, 0.2))):
        draw_box(scr, sx - wd / 2, sy - wd / 2, gz + 1.0 + zz + bob, wd, wd, 0.09, ac, cam, outline=False)
    draw_box(scr, sx - 0.06, sy - 0.06, gz + 1.32 + bob, 0.12, 0.12, 0.2, ac, cam, outline=False)


def make_glow(r, col):
    s = pygame.Surface((2 * r, 2 * r))
    s.fill((0, 0, 0))
    for i in range(r, 0, -2):
        k = (1 - i / r) ** 2
        pygame.draw.circle(s, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (r, r), i)
    return s


def make_vignette():
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(60):
        a = int(140 * (1 - i / 60) ** 2)
        pygame.draw.rect(v, (0, 0, 0, a), (i * 3, i * 2, W - i * 6, H - i * 4), 3)
    return v


# -------------------------------------------------------------- personagens
WHITE, DARK = (250, 250, 255), (26, 24, 36)


def parts_player(t, moving, hero=None):
    hero = hero or "knight"
    sw = math.sin(t * 10) if moving else 0.0
    l1, l2 = max(0, sw) * 0.08, max(0, -sw) * 0.08
    b = abs(sw) * 0.03 if moving else math.sin(t * 3) * 0.01
    arm = sw * 0.07
    steel, steelD = (196, 202, 216), (140, 148, 168)
    blue, blueD = (64, 104, 206), (44, 72, 150)
    gold, skin, brown, red = (240, 200, 70), (244, 206, 164), (110, 72, 44), (214, 52, 60)
    if hero == "ranger":
        blue, blueD, steel, steelD = (120, 180, 110), (82, 134, 78), (170, 200, 180), (110, 150, 128)
        red = (130, 210, 140)
    elif hero == "mage":
        blue, blueD, steel, steelD = (170, 130, 255), (120, 90, 196), (220, 206, 244), (158, 126, 204)
        red = (175, 120, 255)
    elif hero == "guardian":
        blue, blueD, steel, steelD = (240, 170, 110), (164, 118, 70), (210, 188, 150), (152, 116, 80)
        red = (248, 142, 92)
    return [
        (-0.16, -0.09, l1, 0.14, 0.19, 0.10, brown), (0.02, -0.09, l2, 0.14, 0.19, 0.10, brown),
        (-0.14, -0.07, 0.10 + l1, 0.10, 0.14, 0.18, steelD), (0.04, -0.07, 0.10 + l2, 0.10, 0.14, 0.18, steelD),
        (-0.16, -0.15, 0.22 + b, 0.32, 0.04, 0.36, red),
        (-0.18, -0.12, 0.28, 0.36, 0.24, 0.06, brown),
        (-0.035, 0.12, 0.285, 0.07, 0.02, 0.05, gold), (0.18, -0.035, 0.285, 0.02, 0.07, 0.05, gold),
        (-0.17, -0.11, 0.34 + b, 0.34, 0.22, 0.24, blue),
        (-0.17, -0.11, 0.34 + b, 0.34, 0.22, 0.04, blueD),
        (-0.04, 0.11, 0.42 + b, 0.08, 0.02, 0.11, gold), (0.17, -0.04, 0.42 + b, 0.02, 0.08, 0.11, gold),
        (-0.27, -0.10, 0.50 + b, 0.12, 0.20, 0.08, steel), (0.15, -0.10, 0.50 + b, 0.12, 0.20, 0.08, steel),
        (-0.25, -0.06, 0.30 + b - arm, 0.08, 0.12, 0.20, blueD), (0.17, -0.06, 0.30 + b + arm, 0.08, 0.12, 0.20, blueD),
        (-0.25, -0.05, 0.23 + b - arm, 0.08, 0.10, 0.07, skin), (0.17, -0.05, 0.23 + b + arm, 0.08, 0.10, 0.07, skin),
        (-0.32, -0.11, 0.20 + b - arm, 0.05, 0.22, 0.28, steel),
        (-0.275, -0.05, 0.28 + b - arm, 0.02, 0.10, 0.12, red),
        (0.20, -0.02, 0.31 + b + arm, 0.04, 0.04, 0.46, (236, 240, 250)),
        (0.16, -0.05, 0.28 + b + arm, 0.12, 0.10, 0.03, gold),
        (-0.14, -0.11, 0.60 + b, 0.28, 0.22, 0.22, skin),
        (-0.15, -0.12, 0.62 + b, 0.30, 0.05, 0.14, (120, 72, 40)),
        (-0.07, 0.11, 0.69 + b, 0.06, 0.02, 0.06, WHITE), (0.02, 0.11, 0.69 + b, 0.06, 0.02, 0.06, WHITE),
        (-0.05, 0.12, 0.70 + b, 0.03, 0.01, 0.04, DARK), (0.04, 0.12, 0.70 + b, 0.03, 0.01, 0.04, DARK),
        (0.14, -0.08, 0.69 + b, 0.02, 0.06, 0.06, WHITE), (0.14, 0.02, 0.69 + b, 0.02, 0.06, 0.06, WHITE),
        (0.15, -0.06, 0.70 + b, 0.01, 0.03, 0.04, DARK), (0.15, 0.04, 0.70 + b, 0.01, 0.03, 0.04, DARK),
        (-0.03, 0.11, 0.63 + b, 0.06, 0.02, 0.02, (190, 90, 80)),
        (-0.16, -0.13, 0.76 + b, 0.32, 0.26, 0.08, steel),
        (-0.16, -0.13, 0.66 + b, 0.03, 0.26, 0.10, steelD),
        (-0.03, -0.14, 0.84 + b, 0.06, 0.28, 0.08, red), (-0.03, -0.14, 0.80 + b, 0.06, 0.06, 0.06, red),
    ]


def parts_enemy(kind, t):
    if kind == "slime":
        sq = 1 + 0.10 * math.sin(t * 4)
        h1 = 0.30 / sq
        col, colL = (70, 200, 100), (130, 235, 150)
        return [
            (-0.36, -0.36, 0, 0.72, 0.72, h1, col), (-0.31, -0.31, h1, 0.62, 0.62, 0.12 / sq, col),
            (-0.22, -0.22, h1 + 0.12 / sq, 0.44, 0.44, 0.10 / sq, colL), (-0.14, -0.14, h1 + 0.22 / sq, 0.10, 0.10, 0.04, WHITE),
            (-0.02, -0.26, 0.10, 0.10, 0.10, 0.10, (40, 150, 80)), (-0.20, 0.36, 0.12, 0.14, 0.02, 0.16, WHITE), (0.06, 0.36, 0.12, 0.14, 0.02, 0.16, WHITE),
            (-0.15, 0.37, 0.14, 0.07, 0.01, 0.10, DARK), (0.11, 0.37, 0.14, 0.07, 0.01, 0.10, DARK), (-0.06, 0.36, 0.04, 0.12, 0.02, 0.04, DARK),
            (0.36, -0.20, 0.12, 0.02, 0.14, 0.16, WHITE), (0.36, 0.06, 0.12, 0.02, 0.14, 0.16, WHITE), (0.37, -0.15, 0.14, 0.01, 0.07, 0.10, DARK), (0.37, 0.11, 0.14, 0.01, 0.07, 0.10, DARK), (0.36, -0.06, 0.04, 0.02, 0.12, 0.04, DARK),
        ]
    if kind == "goblin":
        skin = (118, 198, 104)
        cloth = (56, 96, 64)
        metal = (170, 140, 76)
        arm = math.sin(t * 6) * 0.05
        return [
            (-0.18, -0.08, 0.00, 0.12, 0.12, 0.08, cloth), (0.06, -0.08, 0.00, 0.12, 0.12, 0.08, cloth),
            (-0.14, -0.10, 0.08, 0.28, 0.20, 0.22, skin), (-0.18, -0.12, 0.30, 0.40, 0.22, 0.07, cloth),
            (-0.21, -0.14, 0.36 - arm, 0.05, 0.08, 0.22, skin), (0.17, -0.14, 0.36 + arm, 0.05, 0.08, 0.22, skin),
            (-0.20, 0.05, 0.36, 0.08, 0.02, 0.18, metal), (0.12, 0.05, 0.36, 0.08, 0.02, 0.18, metal),
            (-0.10, -0.12, 0.54, 0.20, 0.18, 0.16, skin), (-0.15, -0.10, 0.66, 0.30, 0.20, 0.06, (90, 130, 58)),
            (-0.08, 0.11, 0.72, 0.06, 0.02, 0.08, DARK), (0.02, 0.11, 0.72, 0.06, 0.02, 0.08, DARK),
            (-0.05, 0.13, 0.74, 0.03, 0.01, 0.04, (255, 85, 72)), (0.04, 0.13, 0.74, 0.03, 0.01, 0.04, (255, 85, 72)),
            (0.18, -0.10, 0.66, 0.05, 0.06, 0.06, metal), (0.18, 0.03, 0.66, 0.05, 0.06, 0.06, metal),
            (0.18, 0.00, 0.28, 0.04, 0.04, 0.34, metal),
        ]
    if kind == "bat":
        wing = (102, 118, 150)
        body = (92, 90, 122)
        eye = (255, 240, 160)
        return [
            (-0.38, -0.08, 0.14, 0.14, 0.22, 0.06, wing), (-0.18, -0.32, 0.20, 0.18, 0.12, 0.06, wing),
            (0.24, -0.08, 0.14, 0.14, 0.22, 0.06, wing), (0.04, -0.32, 0.20, 0.18, 0.12, 0.06, wing),
            (-0.12, -0.03, 0.12, 0.24, 0.18, 0.16, body), (-0.06, 0.12, 0.20, 0.05, 0.02, 0.08, eye), (0.02, 0.12, 0.20, 0.05, 0.02, 0.08, eye),
            (-0.02, -0.04, 0.30, 0.04, 0.08, 0.06, (230, 210, 255)),
            (-0.06, -0.20, 0.12, 0.12, 0.02, 0.16, wing), (-0.02, -0.20, 0.12, 0.12, 0.02, 0.16, wing), (0.06, -0.20, 0.12, 0.12, 0.02, 0.16, wing),
        ]
    if kind == "skeleton":
        bone, boneD, brown = (236, 234, 218), (192, 190, 176), (130, 90, 54)
        arm = math.sin(t * 3) * 0.02
        parts = [(-0.14, -0.07, 0, 0.12, 0.16, 0.05, boneD), (0.02, -0.07, 0, 0.12, 0.16, 0.05, boneD), (-0.10, -0.03, 0.05, 0.04, 0.06, 0.25, bone), (0.06, -0.03, 0.05, 0.04, 0.06, 0.25, bone), (-0.11, -0.04, 0.17, 0.06, 0.08, 0.05, boneD), (0.05, -0.04, 0.17, 0.06, 0.08, 0.05, boneD), (-0.15, -0.08, 0.30, 0.30, 0.16, 0.07, boneD), (-0.025, -0.03, 0.37, 0.05, 0.06, 0.25, bone)]
        for i in range(3):
            parts.append((-0.16 + 0.01 * i, -0.08, 0.38 + i * 0.075, 0.32 - 0.02 * i, 0.16, 0.045, bone))
        parts += [(-0.18, -0.07, 0.60, 0.36, 0.10, 0.04, boneD), (-0.22, -0.04, 0.34 + arm, 0.04, 0.06, 0.28, bone), (0.18, -0.04, 0.34 - arm, 0.04, 0.06, 0.28, bone), (-0.14, -0.11, 0.66, 0.28, 0.22, 0.20, bone), (-0.11, -0.09, 0.62, 0.22, 0.18, 0.05, boneD), (-0.09, 0.11, 0.75, 0.07, 0.02, 0.07, DARK), (0.02, 0.11, 0.75, 0.07, 0.02, 0.07, DARK), (-0.07, 0.115, 0.77, 0.03, 0.01, 0.03, (255, 70, 70)), (0.04, 0.115, 0.77, 0.03, 0.01, 0.03, (255, 70, 70)), (0.14, -0.09, 0.75, 0.02, 0.07, 0.07, DARK), (0.14, 0.02, 0.75, 0.02, 0.07, 0.07, DARK), (-0.02, 0.11, 0.71, 0.04, 0.02, 0.04, DARK), (-0.08, 0.11, 0.65, 0.04, 0.02, 0.03, DARK), (-0.04, 0.11, 0.65, 0.04, 0.02, 0.03, WHITE), (0.00, 0.11, 0.65, 0.04, 0.02, 0.03, DARK), (0.04, 0.11, 0.65, 0.04, 0.02, 0.03, WHITE), (0.20, 0.0, 0.34 - arm, 0.035, 0.035, 0.42, (150, 150, 165)), (0.17, -0.03, 0.31 - arm, 0.10, 0.09, 0.03, brown), (-0.28, -0.10, 0.28 + arm, 0.05, 0.20, 0.22, brown), (-0.235, -0.02, 0.32 + arm, 0.02, 0.04, 0.14, (120, 120, 130)), (-0.235, -0.06, 0.37 + arm, 0.02, 0.12, 0.04, (120, 120, 130))]
        return parts
    if kind == "orc":
        skin, skinD = (104, 164, 76), (76, 126, 56)
        leather, metal, bone = (110, 74, 44), (130, 136, 150), (240, 238, 224)
        arm = math.sin(t * 3) * 0.03
        return [(-0.20, -0.10, 0, 0.16, 0.22, 0.10, leather), (0.04, -0.10, 0, 0.16, 0.22, 0.10, leather), (-0.18, -0.08, 0.10, 0.13, 0.17, 0.18, (82, 58, 40)), (0.05, -0.08, 0.10, 0.13, 0.17, 0.18, (82, 58, 40)), (-0.24, -0.15, 0.28, 0.48, 0.30, 0.07, leather), (-0.05, 0.15, 0.285, 0.10, 0.02, 0.07, bone), (0.24, -0.05, 0.285, 0.02, 0.10, 0.07, bone), (-0.27, -0.15, 0.35, 0.54, 0.30, 0.32, skin), (-0.18, 0.15, 0.36, 0.08, 0.02, 0.28, leather), (0.27, -0.12, 0.36, 0.02, 0.10, 0.28, leather), (-0.20, 0.15, 0.55, 0.16, 0.02, 0.07, skinD), (0.04, 0.15, 0.55, 0.16, 0.02, 0.07, skinD), (-0.39, -0.12, 0.60, 0.15, 0.24, 0.10, metal), (0.24, -0.12, 0.60, 0.15, 0.24, 0.10, metal), (-0.35, -0.03, 0.70, 0.05, 0.05, 0.08, bone), (0.30, -0.03, 0.70, 0.05, 0.05, 0.08, bone), (-0.37, -0.08, 0.36 - arm, 0.11, 0.16, 0.26, skin), (0.26, -0.08, 0.36 + arm, 0.11, 0.16, 0.26, skin), (-0.37, -0.07, 0.29 - arm, 0.11, 0.14, 0.08, skinD), (0.26, -0.07, 0.29 + arm, 0.11, 0.14, 0.08, skinD), (-0.17, -0.13, 0.70, 0.34, 0.26, 0.22, skin), (-0.16, -0.12, 0.66, 0.32, 0.24, 0.06, skinD), (-0.17, 0.13, 0.83, 0.34, 0.02, 0.04, skinD), (-0.11, 0.13, 0.78, 0.07, 0.02, 0.05, (255, 230, 60)), (0.04, 0.13, 0.78, 0.07, 0.02, 0.05, (255, 230, 60)), (-0.09, 0.135, 0.79, 0.03, 0.01, 0.03, (200, 30, 30)), (0.06, 0.135, 0.79, 0.03, 0.01, 0.03, (200, 30, 30)), (0.17, -0.11, 0.78, 0.02, 0.07, 0.05, (255, 230, 60)), (0.17, 0.04, 0.78, 0.02, 0.07, 0.05, (255, 230, 60)), (-0.11, 0.13, 0.67, 0.04, 0.02, 0.07, bone), (0.07, 0.13, 0.67, 0.04, 0.02, 0.07, bone), (0.17, -0.10, 0.67, 0.02, 0.04, 0.07, bone), (0.17, 0.06, 0.67, 0.02, 0.04, 0.07, bone), (-0.03, -0.13, 0.92, 0.06, 0.26, 0.08, DARK), (-0.03, -0.10, 0.98, 0.06, 0.18, 0.06, DARK), (0.35, 0.08, 0.20 + arm, 0.05, 0.05, 0.64, leather), (0.30, 0.04, 0.66 + arm, 0.14, 0.13, 0.14, metal), (0.44, 0.05, 0.67 + arm, 0.03, 0.11, 0.12, (210, 215, 225))]
    if kind == "wolfman":
        fur, furD, furL = (162, 148, 146), (124, 108, 102), (198, 178, 164)
        claw = (224, 214, 190)
        return [(-0.25, -0.12, 0.0, 0.20, 0.18, 0.12, furD), (0.05, -0.12, 0.0, 0.20, 0.18, 0.12, furD), (-0.20, -0.15, 0.12, 0.42, 0.28, 0.26, fur), (-0.18, -0.18, 0.38, 0.38, 0.24, 0.14, furL), (-0.28, -0.04, 0.42, 0.12, 0.12, 0.28, fur), (0.16, -0.04, 0.42, 0.12, 0.12, 0.28, fur), (-0.32, -0.12, 0.22, 0.10, 0.14, 0.30, fur), (0.22, -0.12, 0.22, 0.10, 0.14, 0.30, fur), (-0.18, 0.16, 0.54, 0.08, 0.02, 0.12, claw), (0.10, 0.16, 0.54, 0.08, 0.02, 0.12, claw), (-0.12, 0.16, 0.66, 0.21, 0.18, 0.18, furL), (-0.10, 0.15, 0.82, 0.16, 0.14, 0.06, (90, 30, 30)), (0.06, 0.15, 0.80, 0.04, 0.02, 0.12, (255, 210, 100)), (0.18, -0.04, 0.74, 0.06, 0.06, 0.08, claw), (0.18, 0.08, 0.74, 0.06, 0.06, 0.08, claw), (-0.26, 0.06, 0.74, 0.06, 0.06, 0.08, claw), (-0.26, -0.08, 0.74, 0.06, 0.06, 0.08, claw)]
    if kind == "ghost":
        z0 = 0.30 + 0.06 * math.sin(t * 3)
        c, cD, glow = (208, 228, 255), (150, 180, 235), (120, 235, 255)
        parts = []
        for i in range(4):
            h = 0.10 + 0.05 * math.sin(t * 5 + i * 1.6)
            parts.append((-0.24 + i * 0.12, -0.20, z0 - h, 0.12, 0.40, h, cD if i % 2 else c))
        parts += [(-0.24, -0.20, z0, 0.48, 0.40, 0.40, c), (-0.20, -0.17, z0 + 0.40, 0.40, 0.34, 0.14, c), (-0.14, -0.12, z0 + 0.54, 0.28, 0.24, 0.08, (230, 244, 255)), (-0.32, -0.08, z0 + 0.16 + 0.04 * math.sin(t * 4), 0.08, 0.16, 0.10, cD), (0.24, -0.08, z0 + 0.16 - 0.04 * math.sin(t * 4), 0.08, 0.16, 0.10, cD), (-0.14, 0.20, z0 + 0.30, 0.10, 0.02, 0.14, DARK), (0.04, 0.20, z0 + 0.30, 0.10, 0.02, 0.14, DARK), (-0.12, 0.21, z0 + 0.34, 0.05, 0.01, 0.07, glow), (0.06, 0.21, z0 + 0.34, 0.05, 0.01, 0.07, glow), (0.24, -0.14, z0 + 0.30, 0.02, 0.10, 0.14, DARK), (0.24, 0.04, z0 + 0.30, 0.02, 0.10, 0.14, DARK), (0.25, -0.12, z0 + 0.34, 0.01, 0.05, 0.07, glow), (0.25, 0.06, z0 + 0.34, 0.01, 0.05, 0.07, glow), (-0.05, 0.20, z0 + 0.16, 0.10, 0.02, 0.08, DARK), (0.24, -0.05, z0 + 0.16, 0.02, 0.10, 0.08, DARK)]
        for i in range(3):
            a = t * 2 + i * 2.1
            parts.append((math.cos(a) * 0.40 - 0.03, math.sin(a) * 0.40 - 0.03, z0 + 0.3 + 0.2 * math.sin(t * 3 + i), 0.06, 0.06, 0.06, glow))
        return parts
    if kind == "golem":
        rock, rockD, moss, rune = (142, 142, 154), (106, 106, 122), (80, 142, 76), (90, 230, 255)
        arm = math.sin(t * 2.5) * 0.04
        return [(-0.32, -0.18, 0, 0.26, 0.34, 0.14, rockD), (0.06, -0.18, 0, 0.26, 0.34, 0.14, rockD), (-0.28, -0.14, 0.14, 0.20, 0.26, 0.24, rock), (0.08, -0.14, 0.14, 0.20, 0.26, 0.24, rock), (-0.30, -0.18, 0.38, 0.60, 0.36, 0.10, rockD), (-0.42, -0.26, 0.48, 0.84, 0.52, 0.50, rock), (-0.10, 0.26, 0.62, 0.20, 0.02, 0.04, rune), (-0.02, 0.26, 0.54, 0.04, 0.02, 0.20, rune), (0.42, -0.10, 0.62, 0.02, 0.20, 0.04, rune), (0.42, -0.02, 0.54, 0.02, 0.04, 0.20, rune), (-0.36, -0.20, 0.98, 0.30, 0.22, 0.04, moss), (0.10, 0.0, 0.98, 0.26, 0.20, 0.04, moss), (-0.58, -0.20, 0.82, 0.22, 0.40, 0.18, rockD), (0.36, -0.20, 0.82, 0.22, 0.40, 0.18, rockD), (-0.58, -0.14, 0.34 - arm, 0.20, 0.28, 0.48, rock), (0.38, -0.14, 0.34 + arm, 0.20, 0.28, 0.48, rock), (-0.62, -0.18, 0.18 - arm, 0.28, 0.36, 0.18, rockD), (0.34, -0.18, 0.18 + arm, 0.28, 0.36, 0.18, rockD), (-0.18, -0.16, 0.98, 0.36, 0.32, 0.26, rock), (-0.12, 0.16, 1.08, 0.08, 0.02, 0.06, (255, 220, 60)), (0.04, 0.16, 1.08, 0.08, 0.02, 0.06, (255, 220, 60)), (0.18, -0.12, 1.08, 0.02, 0.08, 0.06, (255, 220, 60)), (0.18, 0.04, 1.08, 0.02, 0.08, 0.06, (255, 220, 60)), (-0.06, 0.16, 1.00, 0.12, 0.02, 0.03, DARK), (-0.30, -0.26, 1.0, 0.10, 0.10, 0.32, rune), (-0.18, -0.22, 1.0, 0.08, 0.08, 0.22, rune)]
    if kind == "goblin_chief":
        body = (72, 140, 88)
        acc = (222, 180, 90)
        return [(-0.40, -0.10, 0.0, 0.16, 0.18, 0.12, (48, 74, 52)), (0.20, -0.10, 0.0, 0.16, 0.18, 0.12, (48, 74, 52)), (-0.32, -0.18, 0.12, 0.64, 0.38, 0.28, body), (-0.14, -0.18, 0.40, 0.24, 0.18, 0.12, acc), (-0.28, 0.12, 0.42, 0.08, 0.03, 0.24, (230, 170, 75)), (0.18, 0.12, 0.42, 0.08, 0.03, 0.24, (230, 170, 75)), (-0.18, 0.10, 0.55, 0.36, 0.26, 0.20, (90, 190, 110)), (-0.16, 0.09, 0.74, 0.30, 0.20, 0.12, (60, 116, 84)), (-0.12, 0.18, 0.80, 0.12, 0.02, 0.08, (255, 215, 90)), (0.04, 0.18, 0.80, 0.12, 0.02, 0.08, (255, 215, 90)), (0.18, -0.10, 0.64, 0.08, 0.08, 0.08, (255, 215, 90))]
    if kind == "werewolf":
        fur = (120, 110, 106)
        claw = (224, 214, 190)
        return [(-0.34, -0.18, 0.0, 0.28, 0.24, 0.18, fur), (0.06, -0.18, 0.0, 0.28, 0.24, 0.18, fur), (-0.28, -0.20, 0.18, 0.56, 0.34, 0.32, (170, 150, 140)), (-0.28, -0.06, 0.50, 0.12, 0.10, 0.28, fur), (0.20, -0.06, 0.50, 0.12, 0.10, 0.28, fur), (-0.18, 0.08, 0.64, 0.34, 0.22, 0.18, fur), (-0.12, 0.16, 0.80, 0.07, 0.02, 0.10, (255, 170, 110)), (0.04, 0.16, 0.80, 0.07, 0.02, 0.10, (255, 170, 110)), (0.24, -0.06, 0.62, 0.05, 0.06, 0.08, claw), (-0.32, -0.06, 0.62, 0.05, 0.06, 0.08, claw)]
    if kind == "bat_queen":
        wing = (162, 132, 255)
        body = (108, 96, 164)
        return [(-0.48, -0.12, 0.24, 0.18, 0.28, 0.08, wing), (0.30, -0.12, 0.24, 0.18, 0.28, 0.08, wing), (-0.40, -0.28, 0.18, 0.12, 0.14, 0.12, wing), (0.28, -0.28, 0.18, 0.12, 0.14, 0.12, wing), (-0.14, -0.08, 0.14, 0.28, 0.26, 0.18, body), (-0.12, 0.15, 0.28, 0.04, 0.02, 0.12, (255, 235, 140)), (0.06, 0.15, 0.28, 0.04, 0.02, 0.12, (255, 235, 140)), (-0.02, -0.06, 0.32, 0.04, 0.08, 0.08, (220, 210, 255))]
    if kind == "orc_chief":
        skin = (122, 176, 102)
        cloth = (95, 80, 60)
        metal = (188, 194, 210)
        return [(-0.35, -0.18, 0.0, 0.22, 0.20, 0.12, cloth), (0.12, -0.18, 0.0, 0.22, 0.20, 0.12, cloth), (-0.28, -0.16, 0.12, 0.58, 0.34, 0.30, skin), (-0.22, -0.22, 0.42, 0.42, 0.18, 0.20, cloth), (-0.26, 0.16, 0.50, 0.08, 0.02, 0.24, metal), (0.18, 0.16, 0.50, 0.08, 0.02, 0.24, metal), (-0.18, 0.10, 0.62, 0.36, 0.22, 0.22, skin), (-0.15, 0.12, 0.82, 0.28, 0.18, 0.08, (100, 80, 60)), (-0.05, 0.18, 0.90, 0.11, 0.02, 0.10, (255, 230, 90)), (0.05, 0.18, 0.90, 0.11, 0.02, 0.10, (255, 230, 90)), (0.30, 0.02, 0.28, 0.04, 0.08, 0.40, metal)]
    # dragão
    r, rD, rL = (196, 52, 56), (140, 36, 44), (228, 96, 86)
    belly, horn, yel = (240, 200, 110), (240, 226, 170), (255, 232, 70)
    fl = math.sin(t * 4) * 0.10
    fire = 0.5 + 0.5 * math.sin(t * 9)
    parts = []
    for (lx, ly) in [(-0.38, -0.30), (0.18, -0.30), (-0.38, 0.10), (0.18, 0.10)]:
        parts += [(lx, ly, 0.0, 0.20, 0.20, 0.10, rD), (lx + 0.02, ly + 0.02, 0.10, 0.16, 0.16, 0.22, r), (lx + 0.02, ly + 0.20, 0.0, 0.04, 0.03, 0.05, horn), (lx + 0.08, ly + 0.20, 0.0, 0.04, 0.03, 0.05, horn), (lx + 0.14, ly + 0.20, 0.0, 0.04, 0.03, 0.05, horn)]
    parts += [(-1.30, -0.05, 0.52, 0.24, 0.10, 0.09, rD), (-1.08, -0.07, 0.46, 0.28, 0.14, 0.12, rD), (-0.82, -0.09, 0.40, 0.32, 0.18, 0.16, r), (-0.52, -0.12, 0.36, 0.36, 0.24, 0.20, r), (-1.40, -0.03, 0.54, 0.12, 0.06, 0.07, horn), (-0.52, -0.34, 0.32, 1.02, 0.68, 0.46, r), (-0.46, 0.34, 0.34, 0.90, 0.02, 0.30, belly), (0.50, -0.28, 0.34, 0.02, 0.56, 0.30, belly), (-0.30, -0.50, 0.80 + fl, 0.55, 0.03, 0.42, (150, 40, 62)), (-0.30, 0.37, 0.80 + fl, 0.55, 0.03, 0.42, (160, 44, 66)), (-0.30, -0.52, 0.80 + fl, 0.06, 0.06, 0.58, rD), (-0.30, 0.34, 0.80 + fl, 0.06, 0.06, 0.58, rD), (0.22, -0.17, 0.60, 0.26, 0.34, 0.22, r), (0.30, -0.16, 0.78, 0.24, 0.32, 0.22, r), (0.34, -0.15, 0.96, 0.22, 0.30, 0.20, r), (0.30, -0.20, 1.12, 0.40, 0.40, 0.28, rL), (0.70, -0.14, 1.12, 0.22, 0.28, 0.18, rL), (0.66, -0.12, 1.06, 0.22, 0.24, 0.06, rD), (0.92, -0.10, 1.12, 0.02, 0.04, 0.05, horn), (0.92, 0.00, 1.12, 0.02, 0.04, 0.05, horn), (0.92, 0.07, 1.12, 0.02, 0.04, 0.05, horn), (0.92, -0.08, 1.25, 0.02, 0.04, 0.03, DARK), (0.92, 0.04, 1.25, 0.02, 0.04, 0.03, DARK), (0.92, -0.04, 1.14, 0.02, 0.10, 0.04, (255, int(130 + 90 * fire), 30)), (0.36, 0.20, 1.26, 0.08, 0.02, 0.07, yel), (0.52, 0.20, 1.26, 0.08, 0.02, 0.07, yel), (0.39, 0.205, 1.27, 0.03, 0.01, 0.05, DARK), (0.55, 0.205, 1.27, 0.03, 0.01, 0.05, DARK), (0.32, -0.20, 1.40, 0.06, 0.06, 0.18, horn), (0.32, 0.14, 1.40, 0.06, 0.06, 0.18, horn), (0.28, -0.20, 1.54, 0.04, 0.05, 0.10, horn), (0.28, 0.15, 1.54, 0.04, 0.05, 0.10, horn)]
    for i in range(5):
        parts.append((-0.44 + i * 0.2, -0.06, 0.78, 0.08, 0.12, 0.10 + 0.02 * (i % 2), horn))
    return parts


def _face(hw, hd, z, ec=WHITE, pc=DARK, sz=0.06):
    out = []
    for sx in (-1, 1):
        x = sx * hw * 0.5 - sz / 2
        out += [(x, hd, z, sz, 0.02, sz, ec), (x + 0.015, hd + 0.01, z + 0.01, sz * 0.5, 0.01, sz * 0.7, pc)]
    for sy in (-1, 1):
        y = sy * hd * 0.5 - sz / 2
        out += [(hw, y, z, 0.02, sz, sz, ec), (hw + 0.01, y + 0.015, z + 0.01, 0.01, sz * 0.5, sz * 0.7, pc)]
    return out


parts_player_old = parts_player


def parts_hero(hero, t, moving):
    hero = hero or "knight"
    if hero == "ranger":
        g, gD, lea = (74, 140, 84), (46, 96, 56), (128, 92, 58)
        sw = math.sin(t * 10) if moving else 0.0
        l1, l2 = max(0, sw) * 0.08, max(0, -sw) * 0.08
        b = abs(sw) * 0.03 if moving else math.sin(t * 3) * 0.01
        arm = sw * 0.07
        skin, brown = (244, 206, 164), (110, 72, 44)
        P = [(-0.16, -0.09, l1, 0.14, 0.19, 0.10, (92, 64, 40)), (0.02, -0.09, l2, 0.14, 0.19, 0.10, (92, 64, 40)),
             (-0.14, -0.07, 0.10 + l1, 0.10, 0.14, 0.18, (96, 124, 84)), (0.04, -0.07, 0.10 + l2, 0.10, 0.14, 0.18, (96, 124, 84)),
             (-0.19, -0.17, 0.26 + b, 0.38, 0.05, 0.40, g), (-0.17, -0.11, 0.34 + b, 0.34, 0.22, 0.24, (150, 170, 96)),
             (-0.17, 0.11, 0.42 + b, 0.34, 0.02, 0.04, lea), (-0.18, -0.12, 0.28, 0.36, 0.24, 0.06, lea),
             (0.02, -0.21, 0.40 + b, 0.11, 0.08, 0.32, lea), (0.04, -0.20, 0.72 + b, 0.02, 0.02, 0.09, (235, 235, 205)),
             (0.07, -0.20, 0.72 + b, 0.02, 0.02, 0.07, (235, 80, 70)),
             (-0.25, -0.06, 0.30 + b - arm, 0.08, 0.12, 0.20, g), (0.17, -0.06, 0.30 + b + arm, 0.08, 0.12, 0.20, g),
             (-0.25, -0.05, 0.23 + b - arm, 0.08, 0.10, 0.07, skin), (0.17, -0.05, 0.23 + b + arm, 0.08, 0.10, 0.07, skin),
             (-0.36, -0.03, 0.26 + b - arm, 0.04, 0.05, 0.12, lea), (-0.36, 0.01, 0.38 + b - arm, 0.04, 0.05, 0.10, brown),
             (-0.36, 0.05, 0.48 + b - arm, 0.04, 0.05, 0.10, brown), (-0.36, 0.09, 0.58 + b - arm, 0.04, 0.05, 0.08, brown),
             (-0.36, 0.01, 0.16 + b - arm, 0.04, 0.05, 0.10, brown), (-0.36, 0.05, 0.06 + b - arm, 0.04, 0.05, 0.10, brown),
             (-0.36, 0.09, 0.0 + b - arm, 0.04, 0.05, 0.07, brown), (-0.345, 0.12, 0.05, 0.01, 0.01, 0.57, (240, 240, 230)),
             (0.20, 0.0, 0.33 + b + arm, 0.03, 0.20, 0.03, (232, 222, 180)), (0.20, 0.20, 0.325 + b + arm, 0.03, 0.04, 0.04, (180, 190, 200)),
             (-0.14, -0.11, 0.60 + b, 0.28, 0.22, 0.20, skin), (-0.17, -0.14, 0.76 + b, 0.34, 0.30, 0.08, g), (-0.17, -0.15, 0.60 + b, 0.34, 0.05, 0.24, g),
             (-0.17, -0.11, 0.62 + b, 0.03, 0.22, 0.16, gD), (0.14, -0.11, 0.74 + b, 0.03, 0.22, 0.04, gD),
             (-0.05, -0.18, 0.84 + b, 0.10, 0.14, 0.07, gD), (-0.20, -0.02, 0.70 + b, 0.06, 0.04, 0.05, skin), (0.14, -0.02, 0.70 + b, 0.06, 0.04, 0.05, skin),
             (-0.03, 0.11, 0.63 + b, 0.06, 0.02, 0.02, (190, 90, 80))]
        return P + _face(0.14, 0.11, 0.68 + b, WHITE, (40, 120, 70))
    if hero == "mage":
        rb, rbD, hat = (140, 96, 220), (92, 60, 160), (70, 48, 130)
        hair = (214, 96, 80)
        sw = math.sin(t * 10) if moving else 0.0
        l1, l2 = max(0, sw) * 0.08, max(0, -sw) * 0.08
        b = abs(sw) * 0.03 if moving else math.sin(t * 3) * 0.01
        arm = sw * 0.07
        skin = (244, 206, 164)
        glow = (110, 220, 255)
        P = [(-0.12, 0.12, 0.0 + l1, 0.10, 0.10, 0.05, (110, 72, 44)), (0.02, 0.12, 0.0 + l2, 0.10, 0.10, 0.05, (110, 72, 44)),
             (-0.23, -0.16, 0.04, 0.46, 0.32, 0.24, rbD), (-0.20, -0.14, 0.26 + b, 0.40, 0.28, 0.10, rb),
             (-0.23, -0.16, 0.04, 0.46, 0.32, 0.03, (240, 200, 70)),
             (-0.17, -0.11, 0.34 + b, 0.34, 0.22, 0.24, rb), (-0.19, -0.13, 0.30 + b, 0.38, 0.26, 0.05, (240, 200, 70)),
             (-0.02, 0.12, 0.40 + b, 0.04, 0.02, 0.16, (240, 200, 70)),
             (-0.27, -0.07, 0.28 + b - arm, 0.11, 0.15, 0.22, rbD), (0.16, -0.07, 0.28 + b + arm, 0.11, 0.15, 0.22, rbD),
             (-0.25, -0.05, 0.22 + b - arm, 0.08, 0.10, 0.07, skin), (0.17, -0.05, 0.22 + b + arm, 0.08, 0.10, 0.07, skin),
             (-0.36, -0.06, 0.26 + b - arm, 0.07, 0.16, 0.20, (160, 50, 90)), (-0.355, -0.05, 0.30 + b - arm, 0.02, 0.14, 0.04, (240, 200, 70)),
             (0.23, -0.02, 0.05 + b + arm, 0.04, 0.04, 0.85, (110, 72, 44)), (0.20, -0.05, 0.88 + b + arm, 0.10, 0.10, 0.04, (240, 200, 70)),
             (0.19, -0.06, 0.92 + b + arm, 0.12, 0.12, 0.12, glow),
             (-0.15, -0.15, 0.36 + b, 0.30, 0.06, 0.42, hair), (-0.15, -0.09, 0.50 + b, 0.03, 0.18, 0.26, hair), (0.12, -0.09, 0.50 + b, 0.03, 0.18, 0.26, hair),
             (-0.13, -0.10, 0.60 + b, 0.26, 0.20, 0.18, skin),
             (-0.24, -0.20, 0.78 + b, 0.48, 0.40, 0.04, hat), (-0.15, -0.12, 0.82 + b, 0.30, 0.24, 0.10, rb),
             (-0.11, -0.08, 0.92 + b, 0.22, 0.16, 0.10, rb), (-0.07, -0.04, 1.02 + b, 0.14, 0.08, 0.10, rb),
             (-0.03, -0.03, 1.12 + b, 0.06, 0.05, 0.07, rbD), (-0.03, 0.125, 0.84 + b, 0.06, 0.01, 0.06, (240, 200, 70)),
             (-0.03, 0.10, 0.62 + b, 0.06, 0.02, 0.02, (210, 110, 120))]
        return P + _face(0.13, 0.10, 0.69 + b, WHITE, (90, 40, 150))
    if hero == "guardian":
        br, brD, st = (206, 134, 72), (150, 92, 50), (190, 192, 204)
        dk = (62, 50, 50)
        sw = math.sin(t * 10) if moving else 0.0
        l1, l2 = max(0, sw) * 0.08, max(0, -sw) * 0.08
        b = abs(sw) * 0.03 if moving else math.sin(t * 3) * 0.01
        arm = sw * 0.07
        P = [(-0.20, -0.10, l1, 0.18, 0.22, 0.12, dk), (0.02, -0.10, l2, 0.18, 0.22, 0.12, dk),
             (-0.18, -0.08, 0.12 + l1, 0.14, 0.16, 0.18, brD), (0.04, -0.08, 0.12 + l2, 0.14, 0.16, 0.18, brD),
             (-0.25, -0.15, 0.26, 0.50, 0.30, 0.06, dk), (-0.24, -0.14, 0.30 + b, 0.48, 0.28, 0.30, br),
             (-0.24, -0.14, 0.30 + b, 0.48, 0.28, 0.04, brD), (-0.06, 0.14, 0.42 + b, 0.12, 0.02, 0.12, (240, 200, 70)),
             (-0.24, 0.14, 0.52 + b, 0.48, 0.02, 0.04, (240, 200, 70)),
             (-0.42, -0.15, 0.54 + b, 0.19, 0.30, 0.12, st), (0.23, -0.15, 0.54 + b, 0.19, 0.30, 0.12, st),
             (-0.38, -0.05, 0.66 + b, 0.07, 0.07, 0.09, st), (0.27, -0.05, 0.66 + b, 0.07, 0.07, 0.09, st),
             (-0.36, -0.08, 0.28 + b - arm, 0.12, 0.16, 0.26, brD), (0.24, -0.08, 0.28 + b + arm, 0.12, 0.16, 0.26, brD),
             (-0.36, -0.08, 0.20 + b - arm, 0.12, 0.16, 0.08, st), (0.24, -0.08, 0.20 + b + arm, 0.12, 0.16, 0.08, st),
             (-0.52, -0.22, 0.06 + b - arm, 0.08, 0.44, 0.66, st), (-0.44, -0.18, 0.10 + b - arm, 0.02, 0.36, 0.58, brD),
             (-0.435, -0.08, 0.28 + b - arm, 0.02, 0.16, 0.22, (240, 200, 70)),
             (0.29, -0.02, 0.10 + b + arm, 0.05, 0.05, 0.64, (110, 72, 44)), (0.21, -0.09, 0.72 + b + arm, 0.20, 0.18, 0.16, st),
             (0.21, -0.09, 0.72 + b + arm, 0.20, 0.18, 0.03, brD),
             (-0.15, -0.12, 0.62 + b, 0.30, 0.24, 0.22, st), (-0.11, 0.12, 0.72 + b, 0.22, 0.02, 0.04, (255, 200, 60)),
             (0.15, -0.08, 0.72 + b, 0.02, 0.16, 0.04, (255, 200, 60)),
             (-0.24, -0.04, 0.80 + b, 0.09, 0.08, 0.06, (244, 206, 164)), (-0.30, -0.04, 0.86 + b, 0.07, 0.08, 0.09, (244, 206, 164)),
             (0.15, -0.04, 0.80 + b, 0.09, 0.08, 0.06, (244, 206, 164)), (0.23, -0.04, 0.86 + b, 0.07, 0.08, 0.09, (244, 206, 164)),
             (-0.03, -0.14, 0.84 + b, 0.06, 0.28, 0.07, (214, 52, 60))]
        return P
    return parts_player_old(t, moving, hero)


def parts_player_base(t, moving, hero=None):
    hero = hero or "knight"
    if hero in {"ranger", "mage", "guardian"}:
        return parts_hero(hero, t, moving)
    return parts_player_old(t, moving, hero)


def hero_extras(hero, t, moving):
    """Detalhes animados extras (capa, cachecol, runas, orbes...)."""
    sw = math.sin(t * 10) if moving else 0.0
    b = abs(sw) * 0.03 if moving else math.sin(t * 3) * 0.01
    fl = 0.03 + (0.05 if moving else 0.0)
    gold = (240, 200, 70)
    P = []
    if hero == "knight":
        red = (214, 52, 60)
        for i in range(4):  # penacho do elmo
            sway = math.sin(t * 4 - i * 0.9) * 0.025 * (i + 1)
            P.append((-0.03 + sway, -0.17 - i * 0.07 - fl * i * 0.5, 0.84 + b - i * 0.035, 0.06, 0.08, 0.06, shade(red, 1.0 - i * 0.08)))
        P.append((-0.17, -0.14, 0.76 + b, 0.34, 0.28, 0.025, gold))
        for i in range(3):  # barra da capa balançando
            fo = math.sin(t * 5 - i * 0.7) * 0.03 + fl
            P.append((-0.16, -0.17 - fo * (i + 1), 0.20 - i * 0.07, 0.32, 0.04, 0.07, shade(red, 0.9 - i * 0.07)))
        if math.sin(t * 3.1) > 0.65:  # brilho na espada
            sz = 0.05 + 0.04 * math.sin(t * 20) ** 2
            P.append((0.19, -0.03, 0.80 + b, sz, sz, sz, (255, 255, 255)))
    elif hero == "ranger":
        for i in range(4):  # cachecol ao vento
            sway = math.sin(t * 5 - i) * 0.03 * (i + 1)
            P.append((0.0 + sway, -0.16 - i * 0.07 - fl * i * 0.4, 0.66 + b - i * 0.03, 0.07, 0.07, 0.05, (210, 84, 84)))
        for i in range(3):  # vaga-lumes
            a = t * 1.8 + i * 2.1
            P.append((math.cos(a) * 0.46 - 0.025, math.sin(a) * 0.46 - 0.025, 0.55 + 0.12 * math.sin(t * 3 + i * 2), 0.05, 0.05, 0.05, (190, 255, 170)))
    elif hero == "mage":
        glow = (110, 220, 255)
        for i in range(3):  # faíscas ao redor do orbe do cajado
            a = t * 3 + i * 2.09
            P.append((0.25 + math.cos(a) * 0.11 - 0.02, math.sin(a) * 0.11 - 0.02, 1.02 + 0.04 * math.sin(t * 4 + i), 0.04, 0.04, 0.04, glow))
        zb = 0.05 * math.sin(t * 2)  # grimório flutuante
        P.append((-0.56, -0.08, 0.55 + zb, 0.18, 0.16, 0.05, (150, 60, 70)))
        P.append((-0.55, -0.07, 0.60 + zb, 0.16, 0.14, 0.02, WHITE))
        pul = 0.5 + 0.5 * math.sin(t * 5)
        P.append((-0.49, -0.02, 0.68 + zb + 0.03 * pul, 0.04, 0.04, 0.04, mix(glow, 0.4 * pul)))
        sway = math.sin(t * 3) * 0.03  # ponta do chapéu
        P.append((0.0 + sway, -0.03, 1.19, 0.05, 0.05, 0.05, (92, 60, 160)))
        P.append((0.03 + sway * 2, -0.03, 1.23, 0.05, 0.05, 0.04, (92, 60, 160)))
    elif hero == "guardian":
        for i in range(6):  # anel de orbes dourados
            a = t * 2.2 + i * math.tau / 6
            P.append((math.cos(a) * 0.52 - 0.03, math.sin(a) * 0.52 - 0.03, 0.04 + 0.03 * math.sin(t * 4 + i), 0.06, 0.06, 0.06, gold))
        pul = 0.5 + 0.5 * math.sin(t * 4)
        P.append((-0.445, -0.04, 0.40, 0.02, 0.08, 0.10, mix(gold, 0.5 * pul)))
    return P


def parts_player(t, moving, hero=None):
    hero = hero or "knight"
    return parts_player_base(t, moving, hero) + hero_extras(hero, t, moving)


# ============================================================ HERÓIS V3 (voxel macio)
# Estilo: voxels gordinhos e pastel, sombras frias, luz quente no topo, quinas com brilho,
# sem contorno preto. Cabeçona + corpinho (chibi), olhos com brilho e bochechas.
SOFT_SHADOW = (26, 44, 78)
WARM_LIGHT = (255, 248, 232)


def tshade(c, f):
    """Sombreamento 'macio': luz quente nas faces claras, sombra azulada nas escuras."""
    if f >= 1.0:
        return mix(c, min(0.5, (f - 1.0) * 1.5), WARM_LIGHT)
    return mix(shade(c, f), (1.0 - f) * 0.30, SOFT_SHADOW)


def draw_box_soft(surf, x, y, z, w, d, h, color, cam=(0, 0)):
    """Voxel no estilo macio: sem contorno escuro, com oclusão na base e brilho nas quinas."""
    p = lambda a, b, c: proj(a, b, c, cam)
    ct, cl, cr = tshade(color, 1.16), tshade(color, 0.84), tshade(color, 0.64)
    top = [p(x, y, z + h), p(x + w, y, z + h), p(x + w, y + d, z + h), p(x, y + d, z + h)]
    left = [p(x, y + d, z), p(x + w, y + d, z), p(x + w, y + d, z + h), p(x, y + d, z + h)]
    right = [p(x + w, y, z), p(x + w, y + d, z), p(x + w, y + d, z + h), p(x + w, y, z + h)]
    pygame.draw.polygon(surf, ct, top)
    pygame.draw.polygon(surf, cl, left)
    pygame.draw.polygon(surf, cr, right)
    if h > 0.11:  # oclusão ambiente na base das faces laterais
        band = min(0.10, h * 0.30)
        pygame.draw.polygon(surf, tshade(cl, 0.88), [p(x, y + d, z), p(x + w, y + d, z), p(x + w, y + d, z + band), p(x, y + d, z + band)])
        pygame.draw.polygon(surf, tshade(cr, 0.88), [p(x + w, y, z), p(x + w, y + d, z), p(x + w, y + d, z + band), p(x + w, y, z + band)])
    if max(w, d, h) > 0.075:  # brilho nas quinas (como nos blocos da referência)
        pygame.draw.line(surf, mix(ct, 0.50, WARM_LIGHT), p(x, y + d, z + h), p(x + w, y + d, z + h))
        pygame.draw.line(surf, mix(ct, 0.30, WARM_LIGHT), p(x + w, y, z + h), p(x + w, y + d, z + h))
        pygame.draw.line(surf, mix(cl, 0.22, WARM_LIGHT), p(x + w, y + d, z), p(x + w, y + d, z + h))


class _P(list):
    """Lista de voxels com construtor por centro: b(cx, cy, z, w, d, h, cor)."""

    def b(self, cx, cy, z, w, d, h, c):
        self.append((cx - w / 2, cy - d / 2, z, w, d, h, c))

    def wrap(self, cx, cy, w, d, z, h, c, t=0.016):
        """Faixa que contorna as duas faces visíveis (+x e +y) de uma caixa w x d, sem cruzar o volume."""
        self.append((cx + w / 2 - 0.004, cy - d / 2, z, t + 0.004, d + t, h, c))
        self.append((cx - w / 2, cy + d / 2 - 0.004, z, w, t + 0.004, h, c))


_BLEND = {}


def _gait(t, moving, face, key):
    """Ciclo de caminhada: pernas e braços balançam NA DIREÇÃO do movimento, corpo sobe e
    desce, leve balanço lateral; transição suave entre parado e andando; pisca de olhos."""
    fx, fy = face if face else (0.7071, 0.7071)
    n = math.hypot(fx, fy) or 1.0
    fx, fy = fx / n, fy / n
    m = _BLEND.get(key, 0.0)
    m += ((1.0 if moving else 0.0) - m) * 0.22
    if abs(m - (1.0 if moving else 0.0)) < 0.01:
        m = 1.0 if moving else 0.0
    _BLEND[key] = m
    ph = t * 10.0
    s, c = math.sin(ph), math.cos(ph)
    k = math.sin(t * 3.0)
    L, A = 0.12 * m, 0.10 * m
    g = {"f": (fx, fy), "m": m}
    g["bob"] = 0.045 * abs(c) * m + 0.010 * k * (1 - m)
    g["head"] = 0.014 * math.sin(ph * 2 + 0.8) * m + 0.008 * math.sin(t * 3.0 - 0.7) * (1 - m)
    g["sway"] = (-fy * 0.018 * s * m, fx * 0.018 * s * m)
    g["lA"] = (fx * s * L, fy * s * L, max(0.0, c) * 0.09 * m)
    g["lB"] = (-fx * s * L, -fy * s * L, max(0.0, -c) * 0.09 * m)
    g["aA"] = (-fx * s * A, -fy * s * A, 0.012 * math.sin(t * 3.0 + 1.0) * (1 - m))
    g["aB"] = (fx * s * A, fy * s * A, -0.012 * math.sin(t * 3.0 + 1.0) * (1 - m))
    tx, ty = -fx, -fy
    dot = (tx + ty) * 0.7071
    if dot > 0:   # andando "de costas": o vento vai para o lado, não para cima do corpo
        tx -= dot * 0.7071 * 1.15
        ty -= dot * 0.7071 * 1.15
    tl = math.hypot(tx, ty)
    if tl < 0.3:
        tx, ty = -0.45, -0.45
    else:
        tx, ty = tx / tl, ty / tl
    g["tx"], g["ty"] = tx, ty
    g["blink"] = 1.0 if (t % 3.7) < 0.12 else 0.0
    g["trail"] = 0.35 + 0.65 * m          # intensidade de capas/plumas ao vento
    return g


def _legs(P, g, boot, pant, sep=0.085, w=0.13):
    fx, fy = g["f"]
    for side, o in ((1, g["lA"]), (-1, g["lB"])):
        cx, cy = sep * side + o[0], -sep * side + o[1]
        P.b(cx, cy, o[2] + 0.06, w * 0.92, w * 0.92, 0.075, pant)
        P.b(cx + fx * 0.035, cy + fy * 0.035, o[2], w + 0.012, w + 0.012, 0.065, boot)


def _arm(P, g, side, cx0, sleeve, hand, extra=(0.0, 0.0, 0.0), w=0.095, z0=0.20, sh=0.13):
    """Braço: manga + mão. side=+1 -> lado A (direita da tela), -1 -> lado B."""
    o = g["aA"] if side > 0 else g["aB"]
    ox, oy, oz = o[0] + extra[0], o[1] + extra[1], o[2] + extra[2]
    b = g["bob"]
    P.b(side * cx0 + ox * 0.5, -side * cx0 + oy * 0.5, z0 + 0.075 + oz * 0.5 + b, w, w, sh, sleeve)
    P.b(side * cx0 + ox, -side * cx0 + oy, z0 + oz + b, w + 0.012, w + 0.012, 0.085, hand)
    return (side * cx0 + ox, -side * cx0 + oy, z0 + oz + b)


def _face3(P, cx, cy, hw, z, g, eye=(44, 46, 78), cheek=(255, 170, 164), mouth=(178, 86, 98),
           with_cheeks=True, with_mouth=True):
    """Rosto virado para a câmera: um olho em cada face visível perto da quina."""
    eh = 0.105 * (1.0 - 0.85 * g["blink"])
    ez = z + 0.17 + (0.105 - eh) / 2
    for face in (0, 1):
        def at(u, d_off, w, h, zz, col, dep=0.012):
            if face == 0:   # face +y (esquerda da tela): afastar da quina = -x
                P.b(cx + hw - u - w / 2, cy + hw + d_off, zz, w, dep, h, col)
            else:           # face +x (direita da tela): afastar da quina = -y
                P.b(cx + hw + d_off, cy + hw - u - w / 2, zz, dep, w, h, col)
        at(0.0925, 0.002, 0.075, eh, ez, eye)
        if g["blink"] < 0.5:
            at(0.070, 0.006, 0.030, 0.034, ez + eh - 0.045, WHITE, 0.014)
        if with_cheeks:
            at(0.155, 0.001, 0.07, 0.04, z + 0.095, cheek, 0.010)
        if with_mouth:
            at(0.03, 0.002, 0.05, 0.026, z + 0.045, mouth)


def _orbit(P, g, t, n, r, z, size, col, speed=2.0, wob=0.04):
    for i in range(n):
        a = t * speed + i * math.tau / n
        P.b(math.cos(a) * r, math.sin(a) * r, z + wob * math.sin(t * 3 + i * 2), size, size, size, col)


def _knight(t, moving, face, atk):
    g = _gait(t, moving, face, "knight")
    fx, fy = g["f"]
    b, hb = g["bob"], g["bob"] + g["head"]
    sx, sy = g["sway"]
    steel, steelD = (206, 218, 236), (150, 166, 196)
    blue, blueD = (98, 146, 226), (68, 106, 186)
    red, gold, skin = (232, 84, 90), (250, 214, 112), (252, 218, 184)
    boot = (122, 100, 92)
    P = _P()
    _legs(P, g, boot, steelD)
    # corpo
    P.b(sx, sy, 0.12 + b, 0.34, 0.32, 0.30, steel)
    P.b(sx + 0.166, sy + 0.06, 0.15 + b, 0.014, 0.20, 0.22, blue)
    P.b(sx + 0.06, sy + 0.166, 0.15 + b, 0.20, 0.014, 0.22, blue)
    P.wrap(sx, sy, 0.34, 0.32, 0.17 + b, 0.045, gold)
    P.b(sx + 0.178, sy + 0.17, 0.165 + b, 0.016, 0.05, 0.055, gold)
    # escudo (lado B)  e espada (lado A)
    hB = _arm(P, g, -1, 0.215, steelD, steel)
    hA = _arm(P, g, 1, 0.215, steelD, steel, extra=(fx * 0.16 * atk, fy * 0.16 * atk, 0.10 * atk))
    P.b(hB[0] - 0.01, hB[1] + 0.085, hB[2] - 0.02, 0.22, 0.05, 0.27, steel)
    P.b(hB[0] - 0.01, hB[1] + 0.115, hB[2] + 0.02, 0.13, 0.014, 0.17, blue)
    P.b(hB[0] - 0.01, hB[1] + 0.124, hB[2] + 0.07, 0.06, 0.012, 0.07, gold)
    P.b(hA[0], hA[1], hA[2] + 0.07, 0.05, 0.05, 0.07, (140, 100, 70))
    P.b(hA[0], hA[1], hA[2] + 0.14, 0.17, 0.05, 0.035, gold)
    lean = 0.04 + 0.30 * atk
    for i in range(5):
        k = i / 4.0
        P.b(hA[0] + fx * lean * k * k, hA[1] + fy * lean * k * k, hA[2] + 0.175 + i * 0.095, 0.05, 0.05, 0.105,
            (236, 242, 252) if i < 4 else (255, 255, 255))
    if math.sin(t * 3.1) > 0.7:
        sz = 0.05 + 0.04 * math.sin(t * 22) ** 2
        P.b(hA[0] + fx * lean, hA[1] + fy * lean, hA[2] + 0.66, sz, sz, sz, (255, 255, 255))
    # cabeça (capacete)
    hz = 0.42 + hb
    P.b(sx * 1.4, sy * 1.4, hz, 0.46, 0.46, 0.33, skin)
    P.wrap(sx * 1.4, sy * 1.4, 0.46, 0.46, hz + 0.285, 0.045, gold)
    P.b(sx * 1.4, sy * 1.4, hz + 0.33, 0.50, 0.50, 0.115, steel)
    P.b(sx * 1.4 + 0.235, sy * 1.4 - 0.16, hz + 0.04, 0.026, 0.07, 0.24, steel)
    P.b(sx * 1.4 - 0.16, sy * 1.4 + 0.235, hz + 0.04, 0.07, 0.026, 0.24, steel)
    _face3(P, sx * 1.4, sy * 1.4, 0.23, hz, g)
    # penacho vermelho ao vento (trás da cabeça)
    for i in range(5):
        wv = math.sin(t * 6 - i * 0.9) * 0.03 * g["trail"]
        P.b(sx * 1.4 + g["tx"] * (0.04 + 0.075 * i * (0.6 + 0.6 * g["trail"])) + wv * fy,
            sy * 1.4 + g["ty"] * (0.04 + 0.075 * i * (0.6 + 0.6 * g["trail"])) - wv * fx,
            hz + 0.46 + (0.0, 0.04, 0.05, 0.03, 0.0)[i], 0.075, 0.075, 0.075, shade(red, 1.0 - i * 0.06))
    # capa curtinha atrás do corpo
    for i in range(3):
        wv = math.sin(t * 5 - i * 0.8) * 0.035 * g["trail"]
        P.b(sx - 0.13 + g["tx"] * 0.07 * i * g["trail"] + wv * fy, sy - 0.13 + g["ty"] * 0.07 * i * g["trail"] - wv * fx,
            0.30 + b - i * 0.075, 0.26, 0.26, 0.08, shade(red, 0.95 - i * 0.07))
    return P


def _ranger(t, moving, face, atk):
    g = _gait(t, moving, face, "ranger")
    fx, fy = g["f"]
    b, hb = g["bob"], g["bob"] + g["head"]
    sx, sy = g["sway"]
    gr, grD = (122, 190, 120), (86, 150, 92)
    brown, leather = (146, 108, 80), (170, 128, 88)
    skin, red = (252, 218, 184), (238, 96, 96)
    P = _P()
    _legs(P, g, brown, (122, 150, 104))
    P.b(sx, sy, 0.12 + b, 0.33, 0.31, 0.27, gr)
    P.wrap(sx, sy, 0.33, 0.31, 0.17 + b, 0.045, leather)
    P.b(sx + 0.178, sy + 0.16, 0.165 + b, 0.016, 0.05, 0.055, (250, 214, 112))
    P.b(sx + 0.166, sy + 0.0, 0.25 + b, 0.014, 0.30, 0.05, grD)
    P.b(sx + 0.0, sy + 0.156, 0.25 + b, 0.30, 0.014, 0.05, grD)
    # aljava nas costas com flechas
    qx, qy = sx - fx * 0.17 - 0.03, sy - fy * 0.17 + 0.03
    P.b(qx, qy, 0.20 + b, 0.10, 0.09, 0.30, leather)
    for i, cc in enumerate(((238, 240, 220), red, (238, 240, 220))):
        P.b(qx + (i - 1) * 0.035, qy - 0.01, 0.50 + b + (i % 2) * 0.03, 0.03, 0.03, 0.07, cc)
    hB = _arm(P, g, -1, 0.215, gr, skin)
    hA = _arm(P, g, 1, 0.215, gr, skin, extra=(fx * 0.14 * atk, fy * 0.14 * atk, 0.08 * atk))
    # arco na mão B
    for i in range(9):
        zi = hB[2] - 0.12 + 0.07 * i
        bulge = 0.055 * (1 - ((i - 4) / 4.0) ** 2)
        P.b(hB[0], hB[1] + 0.06 + bulge, zi, 0.045, 0.045, 0.075, brown if i not in (0, 8) else (110, 80, 60))
    P.b(hB[0], hB[1] + 0.06, hB[2] - 0.10, 0.012, 0.012, 0.56, (250, 248, 238))
    # flecha na mão A durante o ataque
    if atk > 0.05:
        P.b(hA[0] + fx * 0.10 * atk, hA[1] + fy * 0.10 * atk, hA[2] + 0.07, 0.03, 0.03, 0.03, (238, 240, 220))
    # cabeça com capuz
    hz = 0.45 + hb
    P.b(sx * 1.4, sy * 1.4, hz, 0.46, 0.46, 0.31, skin)
    P.b(sx * 1.4, sy * 1.4, hz + 0.31, 0.51, 0.51, 0.13, gr)
    P.b(sx * 1.4 + 0.235, sy * 1.4 - 0.16, hz + 0.02, 0.028, 0.07, 0.30, grD)
    P.b(sx * 1.4 - 0.16, sy * 1.4 + 0.235, hz + 0.02, 0.07, 0.028, 0.30, grD)
    P.b(sx * 1.4 - fx * 0.13, sy * 1.4 - fy * 0.13, hz + 0.36, 0.30, 0.30, 0.07, grD)
    tw = math.sin(t * 5) * 0.03 * g["trail"]
    for i in range(3):   # ponta do capuz balançando
        P.b(sx * 1.4 - 0.17 + g["tx"] * 0.06 * i + tw * fy * i, sy * 1.4 - 0.17 + g["ty"] * 0.06 * i - tw * fx * i,
            hz + 0.40 - i * 0.04, 0.12 - i * 0.025, 0.12 - i * 0.025, 0.09, gr)
    P.b(sx * 1.4 + 0.10, sy * 1.4 + 0.10, hz + 0.43, 0.04, 0.04, 0.14, (238, 240, 220))   # pena
    P.b(sx * 1.4 + 0.10 - fx * 0.03, sy * 1.4 + 0.10 - fy * 0.03, hz + 0.50, 0.04, 0.04, 0.08, red)
    _face3(P, sx * 1.4, sy * 1.4, 0.23, hz, g, eye=(36, 56, 60), mouth=(170, 90, 90))
    # cachecol vermelho ao vento
    P.b(sx, sy, 0.39 + b, 0.37, 0.35, 0.06, red)
    for i in range(4):
        wv = math.sin(t * 6 - i) * 0.035 * g["trail"]
        P.b(sx - 0.17 + g["tx"] * (0.03 + 0.07 * i * (0.5 + 0.7 * g["trail"])) + wv * fy,
            sy - 0.17 + g["ty"] * (0.03 + 0.07 * i * (0.5 + 0.7 * g["trail"])) - wv * fx, 0.37 + b - i * 0.03, 0.08, 0.08, 0.07, shade(red, 1 - i * 0.07))
    _orbit(P, g, t, 3, 0.52, 0.55, 0.05, (200, 255, 180), 1.8, 0.05)
    return P


def _mage(t, moving, face, atk):
    g = _gait(t, moving, face, "mage")
    fx, fy = g["f"]
    b, hb = g["bob"], g["bob"] + g["head"]
    sx, sy = g["sway"]
    rb, rbD = (170, 132, 238), (126, 96, 196)
    hat, hatD = (112, 88, 190), (84, 64, 156)
    gold, skin, hair = (250, 214, 112), (252, 218, 184), (240, 126, 108)
    glow = (120, 226, 255)
    P = _P()
    for side, o in ((1, g["lA"]), (-1, g["lB"])):   # pés aparecendo sob a barra da túnica
        P.b(0.10 * side + o[0] + fx * 0.04, -0.10 * side + o[1] + fy * 0.04, o[2] * 0.8, 0.13, 0.13, 0.075, (130, 96, 84))
    tr = g["trail"]
    hemx, hemy = -fx * 0.025 * g["m"], -fy * 0.025 * g["m"]
    P.b(hemx, hemy, 0.075, 0.42, 0.40, 0.165, rbD)
    P.wrap(hemx, hemy, 0.42, 0.40, 0.075, 0.035, gold)
    P.b(sx * 0.6, sy * 0.6, 0.24 + b, 0.34, 0.32, 0.20, rb)
    P.wrap(sx * 0.6, sy * 0.6, 0.34, 0.32, 0.30 + b, 0.04, gold)
    P.b(sx * 0.6 + 0.172, sy * 0.6 + 0.06, 0.25 + b, 0.014, 0.12, 0.17, rbD)
    P.b(sx * 0.6 + 0.06, sy * 0.6 + 0.172, 0.25 + b, 0.12, 0.014, 0.17, rbD)
    hB = _arm(P, g, -1, 0.215, rbD, skin, w=0.115, sh=0.14)
    hA = _arm(P, g, 1, 0.215, rbD, skin, extra=(fx * 0.12 * atk, fy * 0.12 * atk, 0.10 * atk), w=0.115, sh=0.14)
    # cajado
    lean = 0.04 + 0.22 * atk
    for i in range(7):
        k = i / 6.0
        P.b(hA[0] + fx * lean * k * k, hA[1] + fy * lean * k * k, hA[2] - 0.12 + i * 0.13, 0.045, 0.045, 0.14, (150, 108, 78))
    ox, oy = hA[0] + fx * lean, hA[1] + fy * lean
    pul = 0.5 + 0.5 * math.sin(t * 5)
    P.b(ox, oy, hA[2] + 0.70, 0.17, 0.17, 0.035, gold)
    P.b(ox, oy, hA[2] + 0.735, 0.15, 0.15, 0.15, mix(glow, 0.25 * pul))
    P.b(ox, oy, hA[2] + 0.785, 0.06, 0.06, 0.06, (255, 255, 255))
    for i in range(3):
        a = t * 3 + i * 2.09
        P.b(ox + math.cos(a) * 0.14, oy + math.sin(a) * 0.14, hA[2] + 0.78 + 0.05 * math.sin(t * 4 + i), 0.04, 0.04, 0.04, glow)
    # grimório flutuante
    zb = 0.05 * math.sin(t * 2)
    bx, by = hB[0] - 0.07, hB[1] + 0.20
    P.b(bx, by, 0.50 + zb, 0.17, 0.05, 0.20, (200, 90, 110))
    P.b(bx, by + 0.03, 0.52 + zb, 0.13, 0.014, 0.16, (255, 248, 238))
    P.b(bx, by + 0.04, 0.58 + zb + 0.02 * pul, 0.035, 0.012, 0.035, mix(glow, 0.3 * pul))
    # cabeça
    hz = 0.42 + hb
    P.b(sx * 1.4, sy * 1.4, hz, 0.46, 0.46, 0.37, skin)
    P.b(sx * 1.4 + 0.235, sy * 1.4 - 0.15, hz + 0.02, 0.026, 0.09, 0.30, hair)
    P.b(sx * 1.4 - 0.15, sy * 1.4 + 0.235, hz + 0.02, 0.09, 0.026, 0.30, hair)
    P.b(sx * 1.4 + 0.235, sy * 1.4 + 0.14, hz + 0.31, 0.026, 0.10, 0.09, hair)             # franja
    P.b(sx * 1.4 + 0.14, sy * 1.4 + 0.235, hz + 0.31, 0.10, 0.026, 0.09, hair)
    _face3(P, sx * 1.4, sy * 1.4, 0.23, hz, g, eye=(70, 40, 110), mouth=(196, 96, 120))
    # chapéu pontudo com ponta curvada
    P.b(sx * 1.4, sy * 1.4, hz + 0.37, 0.66, 0.66, 0.05, hatD)
    P.b(sx * 1.4, sy * 1.4, hz + 0.42, 0.46, 0.46, 0.05, gold)
    sw_ = math.sin(t * 3.0) * 0.02 + math.sin(t * 6) * 0.015 * g["m"]
    for i, (wd, hh) in enumerate(((0.40, 0.11), (0.32, 0.11), (0.24, 0.11), (0.16, 0.10), (0.10, 0.09))):
        k = i / 4.0
        P.b(sx * 1.4 - fx * 0.05 * k * 1.4 + sw_ * k * fy, sy * 1.4 - fy * 0.05 * k * 1.4 - sw_ * k * fx,
            hz + 0.47 + i * 0.105, wd, wd, hh, hat if i % 2 == 0 else mix(hat, 0.06))
    P.b(sx * 1.4 + 0.0, sy * 1.4 + 0.205, hz + 0.50, 0.10, 0.02, 0.10, gold)   # estrela
    P.b(sx * 1.4 + 0.205, sy * 1.4 + 0.0, hz + 0.50, 0.02, 0.10, 0.10, gold)
    return P


def _guardian(t, moving, face, atk):
    g = _gait(t, moving, face, "guardian")
    fx, fy = g["f"]
    b, hb = g["bob"], g["bob"] + g["head"]
    sx, sy = g["sway"]
    br, brD = (238, 168, 104), (190, 120, 72)
    steel, steelD = (214, 218, 230), (156, 162, 184)
    gold, skin, cream = (250, 214, 112), (250, 208, 170), (246, 238, 218)
    dk = (112, 82, 76)
    P = _P()
    _legs(P, g, dk, brD, sep=0.10, w=0.155)
    P.b(sx, sy, 0.12 + b, 0.40, 0.37, 0.32, br)
    P.wrap(sx, sy, 0.40, 0.37, 0.17 + b, 0.05, gold)
    P.b(sx + 0.20, sy + 0.19, 0.16 + b, 0.016, 0.09, 0.07, steel)
    P.b(sx + 0.19, sy + 0.20, 0.16 + b, 0.09, 0.016, 0.07, steel)
    P.b(sx + 0.201, sy + 0.05, 0.27 + b, 0.014, 0.17, 0.15, brD)    # emblema do peito
    P.b(sx + 0.05, sy + 0.191, 0.27 + b, 0.17, 0.014, 0.15, brD)
    P.b(sx + 0.209, sy + 0.05, 0.31 + b, 0.014, 0.07, 0.07, gold)
    P.b(sx + 0.05, sy + 0.199, 0.31 + b, 0.07, 0.014, 0.07, gold)
    hB = _arm(P, g, -1, 0.255, brD, steel, w=0.12, sh=0.14)
    hA = _arm(P, g, 1, 0.255, brD, steel, extra=(fx * 0.14 * atk, fy * 0.14 * atk, 0.09 * atk), w=0.12, sh=0.14)
    for side in (1, -1):   # ombreiras grandes
        o = g["aA"] if side > 0 else g["aB"]
        P.b(side * 0.25 + o[0] * 0.2, -side * 0.25 + o[1] * 0.2, 0.34 + b, 0.17, 0.17, 0.12, steel)
        P.b(side * 0.25 + o[0] * 0.2, -side * 0.25 + o[1] * 0.2, 0.44 + b, 0.13, 0.13, 0.04, gold)
    # escudo-torre
    P.b(hB[0] - 0.02, hB[1] + 0.10, hB[2] - 0.14, 0.34, 0.06, 0.50, steel)
    P.b(hB[0] - 0.02, hB[1] + 0.135, hB[2] - 0.10, 0.27, 0.014, 0.42, br)
    P.b(hB[0] - 0.02, hB[1] + 0.145, hB[2] + 0.02, 0.12, 0.012, 0.15, gold)
    # martelo
    lean = 0.04 + 0.30 * atk
    for i in range(4):
        k = i / 3.0
        P.b(hA[0] + fx * lean * k * k, hA[1] + fy * lean * k * k, hA[2] - 0.02 + i * 0.12, 0.05, 0.05, 0.13, (150, 108, 78))
    P.b(hA[0] + fx * lean, hA[1] + fy * lean, hA[2] + 0.385, 0.23, 0.18, 0.035, gold)
    P.b(hA[0] + fx * lean, hA[1] + fy * lean, hA[2] + 0.42, 0.22, 0.17, 0.15, steel)
    # cabeça (elmo com chifres e barba)
    hz = 0.44 + hb
    P.b(sx * 1.4, sy * 1.4, hz, 0.48, 0.46, 0.31, skin)
    P.wrap(sx * 1.4, sy * 1.4, 0.48, 0.46, hz + 0.265, 0.045, gold)
    P.b(sx * 1.4, sy * 1.4, hz + 0.31, 0.52, 0.50, 0.12, steel)
    P.b(sx * 1.4 + 0.245, sy * 1.4 - 0.16, hz + 0.04, 0.028, 0.07, 0.22, steel)
    P.b(sx * 1.4 - 0.16, sy * 1.4 + 0.235, hz + 0.04, 0.07, 0.028, 0.22, steel)
    for side in (1, -1):
        hx, hy = sx * 1.4 + side * 0.27, sy * 1.4 - side * 0.26
        P.b(hx, hy, hz + 0.36, 0.09, 0.09, 0.08, cream)
        P.b(hx + side * 0.04, hy - side * 0.04, hz + 0.43, 0.065, 0.065, 0.08, cream)
    P.b(sx * 1.4, sy * 1.4 + 0.236, hz + 0.0, 0.48, 0.016, 0.13, cream)   # barba
    P.b(sx * 1.4 + 0.246, sy * 1.4, hz + 0.0, 0.016, 0.46, 0.13, cream)
    P.b(sx * 1.4 + 0.246, sy * 1.4 + 0.0, hz - 0.04, 0.016, 0.20, 0.06, cream)
    _face3(P, sx * 1.4 + 0.01, sy * 1.4, 0.23, hz, g, eye=(60, 44, 52), with_cheeks=False, with_mouth=False)
    _orbit(P, g, t, 3, 0.58, 0.12, 0.06, gold, 2.0, 0.04)
    return P


def _rogue(t, moving, face, atk):
    """Ladino: capuz azul-noite, máscara vermelha com rabo ao vento, cinto com facas e duas adagas."""
    g = _gait(t, moving, face, "rogue")
    fx, fy = g["f"]
    b, hb = g["bob"], g["bob"] + g["head"]
    sx, sy = g["sway"]
    cloth, clothD = (84, 90, 132), (56, 60, 96)
    hood, hoodD = (66, 72, 116), (44, 48, 82)
    red, redD = (242, 96, 124), (188, 60, 92)
    steel, steelL = (208, 218, 236), (248, 252, 255)
    gold, skin = (250, 214, 112), (252, 218, 184)
    boot, leather, glove = (78, 62, 78), (156, 112, 82), (96, 76, 92)
    P = _P()
    _legs(P, g, boot, clothD, sep=0.08, w=0.12)
    # corpo magrinho: túnica, cinto vermelho com fivela, facas e bolsinha
    P.b(sx, sy, 0.12 + b, 0.31, 0.29, 0.30, cloth)
    P.wrap(sx, sy, 0.31, 0.29, 0.17 + b, 0.045, red)
    P.b(sx + 0.163, sy + 0.12, 0.165 + b, 0.016, 0.05, 0.055, gold)
    P.b(sx + 0.162, sy - 0.06, 0.24 + b, 0.014, 0.16, 0.05, clothD)            # gola/faixa lateral
    P.b(sx + 0.05, sy + 0.153, 0.24 + b, 0.16, 0.014, 0.05, clothD)
    for i in range(3):                                                           # cabos de facas de arremesso
        P.b(sx - 0.08 + 0.065 * i, sy + 0.153, 0.215 + b, 0.03, 0.014, 0.07, steel if i != 1 else leather)
    P.b(sx + 0.162, sy - 0.07, 0.15 + b, 0.014, 0.09, 0.08, leather)             # bolsinha no quadril
    # capa curta escura (forro vermelho na ponta), balançando atrás
    for i in range(4):
        wv = math.sin(t * 5 - i * 0.8) * 0.035 * g["trail"]
        col = shade(clothD, 0.95 - i * 0.06) if i < 3 else redD
        P.b(sx - 0.13 + g["tx"] * 0.07 * i * g["trail"] + wv * fy, sy - 0.13 + g["ty"] * 0.07 * i * g["trail"] - wv * fx,
            0.31 + b - i * 0.07, 0.25, 0.25, 0.075, col)
    # braços: B (esquerda da tela) estoca para a frente, A (direita) segura a adaga em pé
    hB = _arm(P, g, -1, 0.205, clothD, glove, extra=(fx * 0.12 * atk, fy * 0.12 * atk, 0.05 * atk))
    hA = _arm(P, g, 1, 0.205, clothD, glove, extra=(fx * 0.17 * atk, fy * 0.17 * atk, 0.10 * atk))
    lean = 0.03 + 0.26 * atk
    P.b(hA[0], hA[1], hA[2] + 0.07, 0.045, 0.045, 0.07, leather)                 # adaga A
    P.b(hA[0], hA[1], hA[2] + 0.125, 0.13, 0.045, 0.03, gold)
    for i in range(4):
        k = i / 3.0
        P.b(hA[0] + fx * lean * k * k, hA[1] + fy * lean * k * k, hA[2] + 0.155 + i * 0.075,
            0.05 - 0.008 * i, 0.04, 0.08, steel if i < 3 else steelL)
    P.b(hB[0], hB[1], hB[2] + 0.065, 0.05, 0.05, 0.06, leather)                  # adaga B (apontada para frente)
    P.b(hB[0] + fx * 0.04 - fy * 0.05, hB[1] + fy * 0.04 + fx * 0.05, hB[2] + 0.075, 0.035, 0.035, 0.035, gold)
    P.b(hB[0] + fx * 0.04 + fy * 0.05, hB[1] + fy * 0.04 - fx * 0.05, hB[2] + 0.075, 0.035, 0.035, 0.035, gold)
    for i in range(4):
        P.b(hB[0] + fx * (0.07 + 0.07 * i), hB[1] + fy * (0.07 + 0.07 * i), hB[2] + 0.075 + 0.012 * i,
            0.06 - 0.008 * i, 0.06 - 0.008 * i, 0.045, steel if i < 3 else steelL)
    # cabeça: máscara vermelha embaixo, olhos de pele em cima, capuz com sombra na testa
    hz = 0.42 + hb
    hx, hy = sx * 1.4, sy * 1.4
    P.b(hx, hy, hz, 0.47, 0.47, 0.14, red)
    P.b(hx, hy, hz + 0.14, 0.46, 0.46, 0.18, skin)
    P.b(hx, hy, hz + 0.32, 0.52, 0.52, 0.14, hood)
    P.wrap(hx, hy, 0.46, 0.46, hz + 0.285, 0.04, hoodD, 0.03)                    # testa sombreada
    P.b(hx + 0.235, hy - 0.16, hz + 0.02, 0.028, 0.07, 0.30, hoodD)              # laterais do capuz
    P.b(hx - 0.16, hy + 0.235, hz + 0.02, 0.07, 0.028, 0.30, hoodD)
    P.b(hx + 0.19, hy + 0.19, hz + 0.38, 0.05, 0.05, 0.05, gold)                 # gema na frente do capuz
    _face3(P, hx, hy, 0.23, hz, g, eye=(92, 30, 78), with_cheeks=False, with_mouth=False)
    tw = math.sin(t * 5) * 0.03 * g["trail"]
    for i in range(3):                                                           # ponta do capuz balançando
        P.b(hx - 0.17 + g["tx"] * 0.06 * i + tw * fy * i, hy - 0.17 + g["ty"] * 0.06 * i - tw * fx * i,
            hz + 0.40 - i * 0.04, 0.12 - 0.025 * i, 0.12 - 0.025 * i, 0.09, hood)
    for i in range(5):                                                           # rabo da máscara ao vento
        wv = math.sin(t * 6 - i) * 0.04 * g["trail"]
        P.b(hx - 0.17 + g["tx"] * (0.03 + 0.08 * i * (0.5 + 0.7 * g["trail"])) + wv * fy,
            hy - 0.17 + g["ty"] * (0.03 + 0.08 * i * (0.5 + 0.7 * g["trail"])) - wv * fx,
            hz + 0.06 - i * 0.025, 0.08, 0.08, 0.07, shade(red, 1.0 - i * 0.07))
    _orbit(P, g, t, 2, 0.52, 0.52, 0.045, (255, 150, 180), 2.4, 0.05)
    return P


_HERO_BUILDERS = {"knight": _knight, "ranger": _ranger, "mage": _mage, "guardian": _guardian, "rogue": _rogue}


def parts_player(t, moving, hero=None, face=None, atk=0.0):
    return list(_HERO_BUILDERS.get(hero or "knight", _knight)(t, moving, face, atk))


def draw_pedestal(surf, cx, cy, s, col, glow=0.0):
    """Pedestal de pedra pastel com 'X' no topo e juntas de tijolo (referência visual)."""
    cam = (cx - OX, cy - OY)
    base = mix(col, 0.55, (176, 214, 220))
    draw_box_soft(surf, -0.50 * s, -0.50 * s, -0.20 * s, 1.0 * s, 1.0 * s, 0.20 * s, base, cam)
    p = lambda a, b, c: proj(a * s, b * s, c * s, cam)
    top = tshade(base, 1.16)
    mark = mix(top, 0.20 + 0.25 * glow, WARM_LIGHT)
    for q in (((-0.34, -0.06), (0.34, -0.06), (0.34, 0.06), (-0.34, 0.06)),
              ((-0.06, -0.34), (0.06, -0.34), (0.06, 0.34), (-0.06, 0.34))):
        pygame.draw.polygon(surf, mark, [p(a, b, 0.0) for a, b in q])
    jl = tshade(base, 0.74)
    pygame.draw.line(surf, jl, p(-0.50, 0.50, -0.10), p(0.50, 0.50, -0.10))
    pygame.draw.line(surf, tshade(base, 0.54), p(0.50, -0.50, -0.10), p(0.50, 0.50, -0.10))
    pygame.draw.line(surf, jl, p(0.0, 0.50, -0.20), p(0.0, 0.50, -0.10))
    pygame.draw.line(surf, tshade(base, 0.54), p(0.50, 0.0, -0.20), p(0.50, 0.0, -0.10))


# ---------------------------------------------------------------- ordem de desenho exata
_ORDER_CACHE = {}


def _exact_order(boxes, eps):
    """Ordena caixas alinhadas aos eixos de trás para frente (exato quando há um plano
    separador entre elas). boxes: (x, y, z, w, d, h, ...)."""
    n = len(boxes)
    mn = [(b[0], b[1], b[2]) for b in boxes]
    mx = [(b[0] + b[3], b[1] + b[4], b[2] + b[5]) for b in boxes]
    key = [(round(b[0] + b[3] / 2 + b[1] + b[4] / 2, 4), b[2]) for b in boxes]
    after = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        ix0, iy0, iz0 = mn[i]
        ix1, iy1, iz1 = mx[i]
        for j in range(i + 1, n):
            jx0, jy0, jz0 = mn[j]
            jx1, jy1, jz1 = mx[j]
            j_front = jx0 >= ix1 - eps or jy0 >= iy1 - eps or jz0 >= iz1 - eps
            i_front = ix0 >= jx1 - eps or iy0 >= jy1 - eps or iz0 >= jz1 - eps
            if j_front and not i_front:
                after[i].append(j)
                indeg[j] += 1
            elif i_front and not j_front:
                after[j].append(i)
                indeg[i] += 1
    heap = [(key[i], i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    out = []
    done = [False] * n
    while len(out) < n:
        if heap:
            _, i = heapq.heappop(heap)
            if done[i]:
                continue
        else:   # ciclo: solta a peça com menos pendências (desempate pela chave simples)
            i = min((i for i in range(n) if not done[i]), key=lambda i: (indeg[i], key[i]))
        done[i] = True
        out.append(i)
        for j in after[i]:
            if not done[j]:
                indeg[j] -= 1
                if indeg[j] <= 0:
                    heapq.heappush(heap, (key[j], j))
    return out


def world_parts(parts, x, y, z, s=1.0, flash=0.0):
    out = []
    for dx, dy, dz, w, d, h, c in parts:
        if flash > 0:
            c = mix(c, min(1, flash * 3))
        out.append((x + dx * s, y + dy * s, z + dz * s, w * s, d * s, h * s, c))
    return out


def draw_world_parts(surf, wparts, cam, key, eps):
    """Desenha as peças de um herói com ordem exata (recalculada ~15x/s e guardada em cache)."""
    now = time.perf_counter()
    ent = _ORDER_CACHE.get(key)
    if ent is None or ent[1] != len(wparts) or now - ent[2] > 0.066:
        ent = (_exact_order(wparts, eps), len(wparts), now)
        _ORDER_CACHE[key] = ent
    for i in ent[0]:
        x, y, z, w, d, h, c = wparts[i]
        draw_box_soft(surf, x, y, z, w, d, h, c, cam)


def _exact_order_dir(boxes, eps, dx, dy):
    """Igual a _exact_order, mas para uma câmera olhando de (dx, dy) no espaço do modelo.
    Serve para o herói girado: o modelo fica alinhado aos eixos e só a câmera 'gira'."""
    n = len(boxes)
    sx = 1 if dx > 1e-6 else (-1 if dx < -1e-6 else 0)
    sy = 1 if dy > 1e-6 else (-1 if dy < -1e-6 else 0)
    x0 = [b[0] for b in boxes]
    y0 = [b[1] for b in boxes]
    z0 = [b[2] for b in boxes]
    x1 = [b[0] + b[3] for b in boxes]
    y1 = [b[1] + b[4] for b in boxes]
    z1 = [b[2] + b[5] for b in boxes]
    key = [(round((x0[i] + x1[i]) * 0.5 * dx + (y0[i] + y1[i]) * 0.5 * dy, 4), z0[i]) for i in range(n)]
    after = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            j_front = ((sx > 0 and x0[j] >= x1[i] - eps) or (sx < 0 and x1[j] <= x0[i] + eps) or
                       (sy > 0 and y0[j] >= y1[i] - eps) or (sy < 0 and y1[j] <= y0[i] + eps) or
                       z0[j] >= z1[i] - eps)
            i_front = ((sx > 0 and x0[i] >= x1[j] - eps) or (sx < 0 and x1[i] <= x0[j] + eps) or
                       (sy > 0 and y0[i] >= y1[j] - eps) or (sy < 0 and y1[i] <= y0[j] + eps) or
                       z0[i] >= z1[j] - eps)
            if j_front and not i_front:
                after[i].append(j)
                indeg[j] += 1
            elif i_front and not j_front:
                after[j].append(i)
                indeg[i] += 1
    heap = [(key[i], i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    out = []
    done = [False] * n
    while len(out) < n:
        if heap:
            _, i = heapq.heappop(heap)
            if done[i]:
                continue
        else:   # ciclo: solta a peça com menos pendências
            i = min((i for i in range(n) if not done[i]), key=lambda i: (indeg[i], key[i]))
        done[i] = True
        out.append(i)
        for j in after[i]:
            if not done[j]:
                indeg[j] -= 1
                if indeg[j] <= 0:
                    heapq.heappush(heap, (key[j], j))
    return out


def draw_box_rot(surf, cx, cy, z, w, d, h, color, ang, cam=(0, 0), fx=False):
    """Voxel macio GIRADO `ang` rad em torno do eixo vertical (centro cx, cy). Só desenha as faces voltadas
    para a câmera; a cor de cada face vem da direção dela (mesma luz do draw_box_soft).
    fx=True (criaturas): faces grandes ganham miolo mais claro no topo e faixa de luz na borda
    superior das laterais, o que tira o aspecto chapado de 'tijolo' e dá volume de almofada."""
    ca, sa = math.cos(ang), math.sin(ang)
    ux, uy, vx, vy = ca * w / 2, sa * w / 2, -sa * d / 2, ca * d / 2
    cs = ((cx - ux - vx, cy - uy - vy), (cx + ux - vx, cy + uy - vy),
          (cx + ux + vx, cy + uy + vy), (cx - ux + vx, cy - uy + vy))
    nrm = ((sa, -ca), (ca, sa), (-sa, ca), (-ca, -sa))
    ct = tshade(color, 1.16)
    pygame.draw.polygon(surf, ct, [proj(a, b, z + h, cam) for a, b in cs])
    big = max(w, d, h) > 0.075
    if fx and w > 0.16 and d > 0.16:   # miolo do topo mais claro (volume de almofada)
        k = 0.64
        pygame.draw.polygon(surf, mix(ct, 0.13, WARM_LIGHT),
                            [proj(cx + (a - cx) * k, cy + (b - cy) * k, z + h, cam) for a, b in cs])
    if fx and w > 0.27 and d > 0.27:   # juntas de mini-voxels no topo (criaturas grandes não ficam com "pixel gigante")
        lt = shade(ct, 0.935)
        nu, nv = min(6, int(w / 0.14)), min(6, int(d / 0.14))
        for k in range(1, nu):
            f = k / nu
            pa = (cs[0][0] + (cs[1][0] - cs[0][0]) * f, cs[0][1] + (cs[1][1] - cs[0][1]) * f)
            pb = (cs[3][0] + (cs[2][0] - cs[3][0]) * f, cs[3][1] + (cs[2][1] - cs[3][1]) * f)
            pygame.draw.line(surf, lt, proj(pa[0], pa[1], z + h, cam), proj(pb[0], pb[1], z + h, cam))
        for k in range(1, nv):
            f = k / nv
            pa = (cs[0][0] + (cs[3][0] - cs[0][0]) * f, cs[0][1] + (cs[3][1] - cs[0][1]) * f)
            pb = (cs[1][0] + (cs[2][0] - cs[1][0]) * f, cs[1][1] + (cs[2][1] - cs[1][1]) * f)
            pygame.draw.line(surf, lt, proj(pa[0], pa[1], z + h, cam), proj(pb[0], pb[1], z + h, cam))
    vis = [False] * 4
    for i in range(4):
        nx, ny = nrm[i]
        if nx + ny <= 1e-4:
            continue
        vis[i] = True
        (ax, ay), (bx, by) = cs[i], cs[(i + 1) % 4]
        cf = tshade(color, 0.74 + 0.10 * (ny - nx))
        pygame.draw.polygon(surf, cf, [proj(ax, ay, z, cam), proj(bx, by, z, cam),
                                       proj(bx, by, z + h, cam), proj(ax, ay, z + h, cam)])
        if h > 0.11:   # oclusão ambiente na base
            band = min(0.10, h * 0.30)
            pygame.draw.polygon(surf, tshade(cf, 0.88), [proj(ax, ay, z, cam), proj(bx, by, z, cam),
                                                         proj(bx, by, z + band, cam), proj(ax, ay, z + band, cam)])
        if fx:   # juntas de mini-voxels nas laterais grandes
            L = math.hypot(bx - ax, by - ay)
            if L > 0.27 and h > 0.27:
                sc = shade(cf, 0.925)
                nu, nz = min(6, int(L / 0.14)), min(6, int(h / 0.14))
                for k in range(1, nu):
                    f = k / nu
                    xx, yy = ax + (bx - ax) * f, ay + (by - ay) * f
                    pygame.draw.line(surf, sc, proj(xx, yy, z, cam), proj(xx, yy, z + h, cam))
                for k in range(1, nz):
                    zz = z + h * k / nz
                    pygame.draw.line(surf, sc, proj(ax, ay, zz, cam), proj(bx, by, zz, cam))
        if fx and h > 0.20 and max(w, d) > 0.14:   # faixa de luz logo abaixo da borda de cima
            top_b = min(0.09, h * 0.22)
            pygame.draw.polygon(surf, mix(cf, 0.09, WARM_LIGHT),
                                [proj(ax, ay, z + h - top_b, cam), proj(bx, by, z + h - top_b, cam),
                                 proj(bx, by, z + h, cam), proj(ax, ay, z + h, cam)])
        if big:   # brilho na quina de cima
            k = 0.30 + 0.20 * max(0.0, min(1.0, (ny - nx + 1.0) / 2.0))
            pygame.draw.line(surf, mix(ct, k, WARM_LIGHT), proj(ax, ay, z + h, cam), proj(bx, by, z + h, cam))
    if big:   # brilho na quina vertical mais próxima da câmera
        cf = tshade(color, 0.84)
        for i in range(4):
            if vis[i] and vis[(i - 1) % 4]:
                ax, ay = cs[i]
                pygame.draw.line(surf, mix(cf, 0.22, WARM_LIGHT), proj(ax, ay, z, cam), proj(ax, ay, z + h, cam))


_FOE_SURF = {}
FOE_OUTLINE_BASE = (16, 14, 34)


def _foe_sprite(w, h):
    """Folha transparente reaproveitada (tamanhos em múltiplos de 16 para o cache funcionar)."""
    s = _FOE_SURF.get((w, h))
    if s is None:
        if len(_FOE_SURF) > 48:
            _FOE_SURF.clear()
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        _FOE_SURF[(w, h)] = s
    s.fill((0, 0, 0, 0))
    return s


_FOE_R = {}


def foe_shadow_r(kind):
    """Raio da sombra no chão proporcional ao corpo real da criatura (antes era fixo: 0.38)."""
    v = _FOE_R.get(kind)
    if v is None:
        try:
            ps = parts_enemy(kind, 0.0)
            zlow = [p for p in ps if p[2] < 0.3] or ps
            r = max(max(abs(p[0]), abs(p[0] + p[3]), abs(p[1]), abs(p[1] + p[4])) for p in zlow)
            v = max(0.38, min(1.0, r * 0.82))
        except Exception:
            v = 0.38
        _FOE_R[kind] = v
    return v


def foe_outline_color(kind):
    """Contorno 'seletivo': a cor da própria criatura bem escurecida e puxada para o azul-noite."""
    base = ENEMY_COLOR.get(kind, (120, 120, 120))
    return mix(shade(base, 0.30), 0.45, FOE_OUTLINE_BASE)


def draw_foe(surf, parts, ox, oy, oz, ang, cam, key, eps, kind="", elite=False, thick=1):
    """Desenha uma criatura: renderiza o modelo numa folha transparente, gera a silhueta
    e cola o contorno (1 px; 2 px nos chefões; dourado pulsante nos elites) antes do sprite.
    O contorno separa a criatura do chão e dá leitura mesmo quando a cor é parecida com o bioma."""
    r = zt = 0.0
    for x, y, z, w, d, h, c in parts:
        r = max(r, abs(x), abs(x + w), abs(y), abs(y + d))
        zt = max(zt, z + h)
    half_w = r * TW
    up, down = zt * ZH + r * TH, r * TH
    sw = (int(2 * half_w) + 14 + 15) // 16 * 16
    sh = (int(up + down) + 14 + 15) // 16 * 16
    ax, ay = sw // 2, sh - int(down) - 6
    spr = _foe_sprite(sw, sh)
    draw_hero_rot(spr, parts, 0.0, 0.0, 0.0, ang, (ax - OX, ay - OY), key, eps, 1e9, True)
    p0 = proj(ox, oy, oz, cam)
    bx, by = int(round(p0[0])) - ax, int(round(p0[1])) - ay
    if elite:
        pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 5.0)
        col, al = mix((255, 196, 60), 0.25 * pulse), 150 + int(105 * pulse)
        thick = max(thick, 2)
    else:
        col, al = foe_outline_color(kind), 215
    sil = spr.copy()
    sil.fill((0, 0, 0, al), special_flags=pygame.BLEND_RGBA_MULT)               # RGB -> 0, alpha escalado
    sil.fill((col[0], col[1], col[2], 0), special_flags=pygame.BLEND_RGBA_ADD)  # pinta a silhueta
    offs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if thick >= 2:
        offs += [(-1, -1), (1, -1), (-1, 1), (1, 1), (-2, 0), (2, 0), (0, -2), (0, 2)]
    for dx, dy in offs:
        surf.blit(sil, (bx + dx, by + dy))
    surf.blit(spr, (bx, by))


def scale_parts(parts, s, flash=0.0):
    """Escala os voxels do modelo (sem mover para o mundo): o giro é feito na hora de desenhar."""
    out = []
    for dx, dy, dz, w, d, h, c in parts:
        if flash > 0:
            c = mix(c, min(1, flash * 3))
        out.append((dx * s, dy * s, dz * s, w * s, d * s, h * s, c))
    return out


def draw_hero_rot(surf, parts, ox, oy, oz, ang, cam, key, eps=0.008, ttl=0.066, fx=False):
    """Desenha o herói girado `ang` rad (em torno do pé, em ox, oy, oz), peças em ordem exata de profundidade."""
    ca, sa = math.cos(ang), math.sin(ang)
    now = time.perf_counter()
    ent = _ORDER_CACHE.get(key)
    if ent is None or ent[1] != len(parts) or now - ent[2] > ttl:
        ent = (_exact_order_dir(parts, eps, ca + sa, ca - sa), len(parts), now)   # câmera no espaço do modelo
        _ORDER_CACHE[key] = ent
    for i in ent[0]:
        mx, my, mz, w, d, h, c = parts[i]
        qx, qy = mx + w / 2, my + d / 2
        draw_box_rot(surf, ox + qx * ca - qy * sa, oy + qx * sa + qy * ca, oz + mz, w, d, h, c, ang, cam, fx)


def _kobold(t):
    c, cD, bel, horn = (206, 92, 60), (150, 60, 44), (240, 200, 120), (240, 230, 190)
    arm = math.sin(t * 6) * 0.04
    P = [(-0.12, -0.06, 0, 0.09, 0.12, 0.05, cD), (0.03, -0.06, 0, 0.09, 0.12, 0.05, cD),
         (-0.10, -0.04, 0.05, 0.07, 0.08, 0.14, c), (0.03, -0.04, 0.05, 0.07, 0.08, 0.14, c),
         (-0.04, -0.28, 0.10, 0.08, 0.20, 0.06, c), (-0.03, -0.42, 0.14, 0.06, 0.14, 0.05, cD),
         (-0.14, -0.09, 0.18, 0.28, 0.18, 0.22, c), (-0.09, 0.09, 0.20, 0.18, 0.02, 0.16, bel),
         (-0.20, -0.04, 0.22 + arm, 0.06, 0.08, 0.14, c), (0.14, -0.04, 0.22 - arm, 0.06, 0.08, 0.14, c),
         (-0.13, -0.10, 0.40, 0.26, 0.22, 0.16, c), (-0.08, 0.12, 0.42, 0.16, 0.10, 0.08, mix(c, 0.25)),
         (-0.06, 0.22, 0.46, 0.03, 0.02, 0.03, DARK), (0.03, 0.22, 0.46, 0.03, 0.02, 0.03, DARK),
         (-0.10, -0.06, 0.56, 0.04, 0.04, 0.09, horn), (0.06, -0.06, 0.56, 0.04, 0.04, 0.09, horn),
         (0.20, 0.02, 0.05, 0.03, 0.03, 0.62, (120, 84, 50)), (0.19, 0.01, 0.67, 0.05, 0.05, 0.09, (200, 206, 216))]
    return P + _face(0.13, 0.11, 0.50, (255, 230, 60), DARK, 0.05)


def _gnoll(t):
    fur, spot, mane = (180, 144, 88), (110, 76, 46), (88, 58, 38)
    arm = math.sin(t * 5) * 0.04
    P = [(-0.16, -0.08, 0, 0.12, 0.16, 0.28, fur), (0.04, -0.08, 0, 0.12, 0.16, 0.28, fur),
         (-0.17, -0.09, 0, 0.14, 0.18, 0.05, spot), (0.03, -0.09, 0, 0.14, 0.18, 0.05, spot),
         (-0.18, -0.10, 0.26, 0.36, 0.20, 0.06, (150, 44, 44)), (-0.18, -0.10, 0.32, 0.36, 0.22, 0.26, fur),
         (-0.10, 0.12, 0.40, 0.05, 0.02, 0.05, spot), (0.04, 0.12, 0.48, 0.05, 0.02, 0.05, spot), (-0.18, 0.12, 0.44, 0.36, 0.02, 0.04, (120, 84, 50)),
         (-0.27, -0.06, 0.32 + arm, 0.09, 0.12, 0.26, fur), (0.18, -0.06, 0.32 - arm, 0.09, 0.12, 0.26, fur),
         (-0.12, -0.10, 0.60, 0.24, 0.20, 0.18, fur), (-0.07, 0.10, 0.62, 0.14, 0.14, 0.08, (70, 50, 40)),
         (-0.05, 0.24, 0.62, 0.10, 0.02, 0.03, WHITE), (-0.14, -0.04, 0.77, 0.06, 0.04, 0.09, spot), (0.08, -0.04, 0.77, 0.06, 0.04, 0.09, spot),
         (-0.04, -0.14, 0.62, 0.08, 0.10, 0.24, mane), (0.28, 0.0, 0.05, 0.03, 0.03, 0.88, (120, 84, 50)),
         (0.265, -0.015, 0.93, 0.06, 0.06, 0.12, (230, 226, 210))]
    return P + _face(0.12, 0.10, 0.70, (255, 220, 60), (160, 30, 30), 0.05)


def _zombie(t):
    sk, sD, rag = (122, 152, 112), (90, 118, 84), (92, 78, 60)
    sway = math.sin(t * 2) * 0.03
    P = [(-0.14, -0.07, 0, 0.12, 0.14, 0.30, (80, 70, 64)), (0.02, -0.07, 0, 0.12, 0.14, 0.24 + math.sin(t * 3) * 0.02, rag),
         (-0.17, -0.10, 0.30, 0.34, 0.20, 0.28, sk), (-0.17, 0.10, 0.34, 0.34, 0.02, 0.18, rag),
         (-0.08, 0.105, 0.40, 0.06, 0.01, 0.06, (170, 50, 50)),
         (-0.26, -0.02, 0.48 + sway, 0.08, 0.34, 0.08, sk), (0.18, -0.02, 0.50 - sway, 0.08, 0.34, 0.08, sk),
         (-0.26, 0.32, 0.46 + sway, 0.08, 0.06, 0.10, sD), (0.18, 0.32, 0.48 - sway, 0.08, 0.06, 0.10, sD),
         (-0.11, -0.08, 0.60, 0.26, 0.22, 0.20, sk), (-0.10, -0.08, 0.80, 0.10, 0.12, 0.04, (60, 60, 50)),
         (-0.05, 0.14, 0.62, 0.10, 0.02, 0.04, DARK), (-0.03, 0.14, 0.60, 0.06, 0.02, 0.03, (230, 230, 210))]
    return P + _face(0.15, 0.12, 0.70, (255, 240, 120), (150, 20, 20), 0.06)


def _ogre(t):
    sk, sD, cl = (204, 164, 112), (160, 124, 82), (120, 80, 50)
    arm = math.sin(t * 3) * 0.04
    P = [(-0.24, -0.12, 0, 0.20, 0.24, 0.26, sD), (0.04, -0.12, 0, 0.20, 0.24, 0.26, sD),
         (-0.32, -0.19, 0.20, 0.64, 0.38, 0.08, cl), (-0.30, -0.18, 0.28, 0.60, 0.36, 0.30, sk), (-0.04, 0.18, 0.40, 0.08, 0.02, 0.05, sD),
         (-0.34, -0.18, 0.56, 0.68, 0.34, 0.24, sk), (-0.50, -0.12, 0.30 + arm, 0.16, 0.22, 0.50, sk), (0.34, -0.12, 0.30 - arm, 0.16, 0.22, 0.50, sk),
         (-0.52, -0.13, 0.22 + arm, 0.20, 0.24, 0.12, sD), (0.32, -0.13, 0.22 - arm, 0.20, 0.24, 0.12, sD),
         (-0.16, -0.12, 0.80, 0.32, 0.28, 0.22, sk), (-0.12, 0.16, 0.82, 0.05, 0.03, 0.08, (240, 236, 210)), (0.07, 0.16, 0.82, 0.05, 0.03, 0.08, (240, 236, 210)),
         (-0.12, 0.16, 0.93, 0.24, 0.02, 0.04, DARK), (-0.03, 0.16, 0.86, 0.06, 0.04, 0.06, sD), (-0.16, -0.12, 0.99, 0.32, 0.28, 0.04, (70, 50, 40)),
         (0.40, 0.0, 0.15 - arm, 0.07, 0.07, 0.55, (120, 84, 50)), (0.34, -0.06, 0.65 - arm, 0.20, 0.20, 0.30, (110, 76, 46)),
         (0.31, 0.04, 0.78 - arm, 0.04, 0.04, 0.05, (200, 206, 216)), (0.46, 0.14, 0.72 - arm, 0.04, 0.04, 0.05, (200, 206, 216))]
    return P + _face(0.16, 0.14, 0.88, (255, 230, 80), (150, 20, 20), 0.05)


def _owlbear(t):
    fur, dk, fea, beak = (124, 86, 58), (84, 58, 40), (232, 222, 200), (242, 172, 52)
    arm = math.sin(t * 3) * 0.04
    P = []
    for (lx, ly) in [(-0.36, -0.34), (0.16, -0.34), (-0.36, 0.08), (0.16, 0.08)]:
        P.append((lx, ly, 0, 0.20, 0.22, 0.26, dk))
    P += [(-0.40, -0.36, 0.24, 0.80, 0.74, 0.46, fur), (-0.30, -0.30, 0.70, 0.60, 0.56, 0.10, dk),
          (-0.44, 0.38, 0.30, 0.88, 0.02, 0.30, mix(fur, 0.15)),
          (-0.46, 0.24, 0.42 + arm, 0.14, 0.24, 0.14, fur), (0.32, 0.24, 0.42 - arm, 0.14, 0.24, 0.14, fur),
          (-0.46, 0.48, 0.42 + arm, 0.04, 0.06, 0.06, (236, 232, 210)), (-0.38, 0.48, 0.42 + arm, 0.04, 0.06, 0.06, (236, 232, 210)),
          (0.32, 0.48, 0.42 - arm, 0.04, 0.06, 0.06, (236, 232, 210)), (0.40, 0.48, 0.42 - arm, 0.04, 0.06, 0.06, (236, 232, 210)),
          (-0.22, 0.10, 0.64, 0.44, 0.34, 0.34, fea), (-0.22, 0.10, 0.90, 0.44, 0.34, 0.08, fur),
          (-0.22, 0.12, 1.00, 0.07, 0.07, 0.09, fur), (0.15, 0.12, 1.00, 0.07, 0.07, 0.09, fur),
          (-0.06, 0.44, 0.64, 0.12, 0.12, 0.14, beak), (-0.04, 0.55, 0.62, 0.08, 0.04, 0.08, (200, 120, 40)),
          (-0.16, 0.44, 0.78, 0.11, 0.02, 0.11, (255, 220, 40)), (0.05, 0.44, 0.78, 0.11, 0.02, 0.11, (255, 220, 40)),
          (-0.12, 0.45, 0.80, 0.04, 0.01, 0.07, DARK), (0.09, 0.45, 0.80, 0.04, 0.01, 0.07, DARK),
          (0.22, 0.16, 0.78, 0.02, 0.12, 0.11, (255, 220, 40)), (0.23, 0.20, 0.80, 0.01, 0.05, 0.07, DARK)]
    return P


def _cube(t):
    w = 0.03 * math.sin(t * 3)
    out, inn = (120, 232, 190), (84, 196, 160)
    return [(-0.38, -0.38, 0.0, 0.76, 0.76, 0.76 + w, out), (-0.30, -0.30, 0.06, 0.60, 0.60, 0.62 + w, inn),
            (0.0, 0.08, 0.28 + w, 0.14, 0.14, 0.14, (236, 234, 220)), (0.02, 0.10, 0.34 + w, 0.03, 0.02, 0.03, DARK), (0.09, 0.10, 0.34 + w, 0.03, 0.02, 0.03, DARK),
            (0.14, 0.14, 0.18 + 0.03 * math.sin(t * 4), 0.07, 0.07, 0.04, (250, 206, 70)), (0.02, 0.22, 0.46 + w, 0.06, 0.06, 0.04, (250, 206, 70)),
            (0.10, 0.02, 0.38 + w, 0.05, 0.34, 0.03, (200, 206, 216)),
            (-0.38, -0.38, 0.76 + w, 0.76, 0.76, 0.03, (196, 255, 232))]


def _mimic(t):
    wood, lid, band, tongue = (150, 96, 50), (178, 118, 62), (76, 76, 88), (214, 70, 90)
    o = 0.10 * (1 + math.sin(t * 4)) * 0.5 + 0.04
    P = [(-0.36, -0.26, 0, 0.12, 0.12, 0.10, (110, 74, 40)), (0.24, -0.26, 0, 0.12, 0.12, 0.10, (110, 74, 40)),
         (-0.36, 0.14, 0, 0.12, 0.12, 0.10, (110, 74, 40)), (0.24, 0.14, 0, 0.12, 0.12, 0.10, (110, 74, 40)),
         (-0.40, -0.28, 0.10, 0.80, 0.56, 0.30, wood), (-0.41, -0.29, 0.10, 0.82, 0.58, 0.04, band), (-0.41, -0.29, 0.34, 0.82, 0.58, 0.04, band),
         (-0.36, -0.24, 0.38, 0.72, 0.48, 0.03, (96, 20, 36)),
         (-0.40, -0.30, 0.40, 0.80, 0.10, 0.30 + o, lid), (-0.40, -0.30, 0.70 + o, 0.80, 0.42, 0.08, lid), (-0.41, -0.31, 0.70 + o, 0.82, 0.44, 0.03, band),
         (-0.12, 0.10, 0.41, 0.24, 0.36, 0.04, tongue)]
    for i in range(6):
        x = -0.34 + i * 0.12
        P.append((x, 0.20, 0.41, 0.06, 0.06, 0.10, WHITE))
        P.append((x, 0.06, 0.62 + o, 0.06, 0.06, 0.08, WHITE))
    P += [(0.40, -0.10, 0.20, 0.02, 0.16, 0.10, (245, 205, 70)), (-0.08, 0.14, 0.78 + o, 0.16, 0.02, 0.10, WHITE), (-0.03, 0.15, 0.80 + o, 0.06, 0.01, 0.07, (200, 40, 40))]
    return P


def _troll(t):
    sk, sD, hair = (100, 148, 98), (72, 108, 72), (66, 104, 60)
    arm = math.sin(t * 3) * 0.04
    P = [(-0.22, -0.10, 0, 0.18, 0.22, 0.32, sD), (0.04, -0.10, 0, 0.18, 0.22, 0.32, sD),
         (-0.28, -0.17, 0.26, 0.56, 0.36, 0.08, (112, 80, 50)), (-0.28, -0.16, 0.32, 0.56, 0.34, 0.36, sk),
         (-0.20, 0.18, 0.40, 0.40, 0.02, 0.20, mix(sk, 0.18)), (0.0, 0.18, 0.50, 0.05, 0.02, 0.05, sD), (-0.14, 0.18, 0.44, 0.05, 0.02, 0.05, sD),
         (-0.44, -0.10, 0.14 - arm, 0.14, 0.18, 0.56, sk), (0.30, -0.10, 0.14 + arm, 0.14, 0.18, 0.56, sk),
         (-0.46, -0.10, 0.02 - arm, 0.18, 0.22, 0.14, sD), (0.28, -0.10, 0.02 + arm, 0.18, 0.22, 0.14, sD),
         (-0.14, 0.04, 0.68, 0.30, 0.30, 0.22, sk), (-0.14, 0.04, 0.90, 0.30, 0.30, 0.05, hair),
         (-0.03, 0.34, 0.74, 0.08, 0.08, 0.10, mix(sk, 0.25)), (-0.10, 0.34, 0.68, 0.04, 0.03, 0.07, (240, 236, 210)), (0.06, 0.34, 0.68, 0.04, 0.03, 0.07, (240, 236, 210)),
         (-0.18, 0.10, 0.76, 0.05, 0.04, 0.07, sk), (0.16, 0.10, 0.76, 0.05, 0.04, 0.07, sk)]
    return P + _face(0.15, 0.17, 0.80, (255, 70, 40), DARK, 0.06)


def _goblin_king(t):
    P = list(parts_enemy_old("goblin", t))
    gold, red = (244, 204, 70), (150, 30, 40)
    P += [(-0.24, -0.20, 0.10, 0.48, 0.04, 0.55, red), (-0.20, -0.12, 0.50, 0.40, 0.24, 0.05, (232, 232, 222)),
          (-0.13, -0.10, 0.72, 0.26, 0.18, 0.04, gold), (-0.13, -0.10, 0.76, 0.05, 0.05, 0.08, gold), (0.08, -0.10, 0.76, 0.05, 0.05, 0.08, gold),
          (-0.13, 0.03, 0.76, 0.05, 0.05, 0.08, gold), (0.08, 0.03, 0.76, 0.05, 0.05, 0.08, gold), (-0.03, 0.08, 0.73, 0.05, 0.02, 0.05, (230, 50, 60)),
          (0.24, 0.02, 0.10, 0.05, 0.05, 0.52, (120, 84, 50)), (0.18, -0.04, 0.60, 0.17, 0.17, 0.19, (110, 76, 46)),
          (0.16, 0.06, 0.72, 0.04, 0.04, 0.05, (200, 206, 216)), (0.34, -0.04, 0.68, 0.04, 0.04, 0.05, (200, 206, 216))]
    return P


def _beholder(t):
    z0 = 0.55 + 0.05 * math.sin(t * 2)
    col, colD = (164, 70, 124), (120, 48, 92)
    P = []
    for i, wd in enumerate((0.36, 0.52, 0.64, 0.72, 0.72, 0.64, 0.52, 0.36)):
        P.append((-wd / 2, -wd / 2, z0 + i * 0.09, wd, wd, 0.09, col if i % 2 else colD))
    P += [(-0.15, 0.36, z0 + 0.26, 0.30, 0.03, 0.24, WHITE), (-0.09, 0.38, z0 + 0.30, 0.18, 0.02, 0.16, (80, 220, 90)), (-0.04, 0.395, z0 + 0.34, 0.08, 0.01, 0.09, DARK),
          (0.36, -0.15, z0 + 0.26, 0.03, 0.30, 0.24, WHITE), (0.38, -0.09, z0 + 0.30, 0.02, 0.18, 0.16, (80, 220, 90)), (0.395, -0.04, z0 + 0.34, 0.01, 0.08, 0.09, DARK),
          (-0.26, 0.35, z0 + 0.04, 0.52, 0.03, 0.12, (70, 10, 30))]
    for i in range(6):
        P.append((-0.24 + i * 0.09, 0.36, z0 + 0.12, 0.05, 0.03, 0.05, WHITE))
    cols = [(255, 70, 70), (70, 140, 255), (255, 220, 60), (120, 255, 120), (255, 120, 255), (120, 255, 255), (255, 160, 60)]
    ztop0 = z0 + 0.72
    for i in range(7):
        a = i / 7 * math.tau
        wob = math.sin(t * 3 + i * 1.3) * 0.04
        ca, sa = math.cos(a), math.sin(a)
        for k in range(3):
            P.append((ca * (0.14 + 0.07 * k) + wob * k - 0.03, sa * (0.14 + 0.07 * k) + wob * k - 0.03, ztop0 - 0.05 + k * 0.11, 0.06, 0.06, 0.12, colD))
        ex, ey, ez = ca * 0.35 + wob * 3 - 0.06, sa * 0.35 + wob * 3 - 0.06, ztop0 + 0.30
        P += [(ex, ey, ez, 0.12, 0.12, 0.12, WHITE), (ex + 0.03, ey + 0.12, ez + 0.03, 0.06, 0.02, 0.06, cols[i]), (ex + 0.12, ey + 0.03, ez + 0.03, 0.02, 0.06, 0.06, cols[i])]
    return P


def _minotaur(t):
    fur, dk, sk, bone = (112, 72, 50), (70, 46, 34), (152, 98, 68), (240, 232, 208)
    arm = math.sin(t * 3) * 0.04
    P = [(-0.26, -0.12, 0, 0.20, 0.24, 0.08, (40, 30, 30)), (0.06, -0.12, 0, 0.20, 0.24, 0.08, (40, 30, 30)),
         (-0.24, -0.10, 0.08, 0.18, 0.20, 0.30, fur), (0.06, -0.10, 0.08, 0.18, 0.20, 0.30, fur),
         (-0.28, -0.14, 0.34, 0.56, 0.30, 0.08, (150, 40, 40)), (-0.32, -0.16, 0.42, 0.64, 0.32, 0.34, sk),
         (-0.20, 0.16, 0.50, 0.40, 0.02, 0.20, fur), (-0.20, 0.17, 0.60, 0.40, 0.01, 0.02, dk),
         (-0.46, -0.14, 0.66, 0.16, 0.28, 0.14, sk), (0.30, -0.14, 0.66, 0.16, 0.28, 0.14, sk),
         (-0.46, -0.10, 0.30 + arm, 0.14, 0.22, 0.40, sk), (0.32, -0.10, 0.30 - arm, 0.14, 0.22, 0.40, sk),
         (-0.47, -0.11, 0.34 + arm, 0.16, 0.24, 0.08, (222, 182, 70)), (0.31, -0.11, 0.34 - arm, 0.16, 0.24, 0.08, (222, 182, 70)),
         (-0.18, -0.14, 0.78, 0.36, 0.30, 0.26, fur), (-0.10, 0.16, 0.80, 0.20, 0.14, 0.14, (192, 142, 122)),
         (-0.06, 0.30, 0.84, 0.04, 0.02, 0.04, DARK), (0.02, 0.30, 0.84, 0.04, 0.02, 0.04, DARK), (-0.04, 0.31, 0.80, 0.08, 0.02, 0.03, (240, 200, 70)),
         (-0.30, -0.06, 0.98, 0.14, 0.06, 0.06, bone), (-0.38, -0.06, 1.04, 0.10, 0.06, 0.06, bone), (-0.40, -0.06, 1.10, 0.06, 0.06, 0.09, bone),
         (0.16, -0.06, 0.98, 0.14, 0.06, 0.06, bone), (0.28, -0.06, 1.04, 0.10, 0.06, 0.06, bone), (0.34, -0.06, 1.10, 0.06, 0.06, 0.09, bone),
         (0.42, 0.0, 0.10 - arm, 0.06, 0.06, 0.92, (120, 84, 50)), (0.46, -0.10, 0.88 - arm, 0.12, 0.26, 0.20, (200, 206, 216)),
         (0.58, -0.08, 0.92 - arm, 0.04, 0.22, 0.12, (240, 244, 250)), (0.32, -0.10, 0.88 - arm, 0.10, 0.26, 0.20, (150, 156, 170))]
    return P + _face(0.18, 0.14, 0.92, (255, 70, 40), DARK, 0.06)


def _lich(t):
    z0 = 0.12 + 0.05 * math.sin(t * 2)
    robe, robeD, bone, boneD = (82, 50, 124), (50, 30, 80), (238, 234, 214), (190, 186, 170)
    gold, glow = (244, 204, 70), (120, 255, 130)
    arm = math.sin(t * 2.5) * 0.04
    P = [(-0.26, -0.20, z0, 0.52, 0.40, 0.12, robeD), (-0.24, -0.18, z0 + 0.12, 0.48, 0.36, 0.14, robe),
         (-0.20, -0.14, z0 + 0.26, 0.40, 0.28, 0.30, robe), (-0.10, 0.14, z0 + 0.30, 0.20, 0.02, 0.22, (20, 10, 30))]
    for i in range(4):
        P.append((-0.24 + i * 0.13, -0.18, z0 - 0.08, 0.10, 0.34, 0.08, robeD if i % 2 else robe))
        P.append((-0.10, 0.15, z0 + 0.32 + i * 0.05, 0.20, 0.01, 0.025, bone))
    P += [(-0.26, -0.18, z0 + 0.56, 0.52, 0.36, 0.08, robeD),
          (-0.32, -0.08, z0 + 0.30 + arm, 0.10, 0.14, 0.26, robe), (0.22, -0.08, z0 + 0.30 - arm, 0.10, 0.14, 0.26, robe),
          (-0.32, -0.07, z0 + 0.24 + arm, 0.10, 0.12, 0.06, bone), (0.22, -0.07, z0 + 0.24 - arm, 0.10, 0.12, 0.06, bone),
          (-0.14, -0.11, z0 + 0.66, 0.28, 0.22, 0.22, bone), (-0.10, -0.08, z0 + 0.60, 0.20, 0.16, 0.06, boneD),
          (-0.10, 0.11, z0 + 0.76, 0.08, 0.02, 0.08, DARK), (0.02, 0.11, z0 + 0.76, 0.08, 0.02, 0.08, DARK),
          (-0.08, 0.115, z0 + 0.78, 0.04, 0.01, 0.04, glow), (0.04, 0.115, z0 + 0.78, 0.04, 0.01, 0.04, glow),
          (0.14, -0.09, z0 + 0.76, 0.02, 0.08, 0.08, DARK), (0.14, 0.01, z0 + 0.76, 0.02, 0.08, 0.08, DARK),
          (0.145, -0.07, z0 + 0.78, 0.01, 0.04, 0.04, glow), (0.145, 0.03, z0 + 0.78, 0.01, 0.04, 0.04, glow),
          (-0.02, 0.11, z0 + 0.70, 0.04, 0.02, 0.04, DARK),
          (-0.15, -0.12, z0 + 0.88, 0.30, 0.24, 0.04, gold), (-0.15, -0.12, z0 + 0.92, 0.04, 0.04, 0.08, gold), (0.11, -0.12, z0 + 0.92, 0.04, 0.04, 0.08, gold),
          (-0.15, 0.08, z0 + 0.92, 0.04, 0.04, 0.08, gold), (0.11, 0.08, z0 + 0.92, 0.04, 0.04, 0.08, gold), (-0.02, 0.12, z0 + 0.88, 0.04, 0.02, 0.04, glow),
          (0.30, 0.0, z0, 0.04, 0.04, 0.95, (60, 50, 60)), (0.26, -0.04, z0 + 0.95, 0.12, 0.12, 0.12, bone),
          (0.28, 0.08, z0 + 1.0, 0.03, 0.02, 0.04, glow), (0.38, 0.0, z0 + 1.0, 0.02, 0.03, 0.04, glow)]
    for i in range(3):
        a = t * 1.5 + i * 2.09
        P.append((math.cos(a) * 0.45 - 0.05, math.sin(a) * 0.45 - 0.05, z0 + 0.5 + 0.1 * math.sin(t * 3 + i), 0.10, 0.10, 0.10, glow))
    return P


def _mind_flayer(t):
    sk, skD = (156, 112, 196), (112, 78, 152)
    robe, robeD, gold = (66, 34, 100), (42, 22, 68), (244, 204, 70)
    arm = math.sin(t * 2.5) * 0.04
    P = [(-0.24, -0.16, 0.0, 0.48, 0.32, 0.14, robeD), (-0.22, -0.14, 0.14, 0.44, 0.28, 0.22, robe),
         (-0.20, -0.12, 0.36, 0.40, 0.24, 0.26, robe), (-0.04, 0.12, 0.40, 0.08, 0.02, 0.16, gold), (-0.20, 0.12, 0.58, 0.40, 0.02, 0.03, gold),
         (-0.28, -0.20, 0.60, 0.56, 0.06, 0.42, robeD), (-0.28, -0.20, 0.60, 0.06, 0.36, 0.34, robeD),
         (-0.30, -0.06, 0.34 + arm, 0.10, 0.14, 0.26, robe), (0.20, -0.06, 0.34 - arm, 0.10, 0.14, 0.26, robe),
         (-0.30, -0.05, 0.26 + arm, 0.08, 0.10, 0.08, sk), (0.20, -0.05, 0.26 - arm, 0.08, 0.10, 0.08, sk),
         (-0.14, -0.11, 0.62, 0.28, 0.22, 0.24, sk), (-0.12, -0.10, 0.86, 0.24, 0.20, 0.06, skD),
         (-0.10, 0.11, 0.66, 0.20, 0.02, 0.04, (60, 20, 70)),
         (0.28, 0.05, 0.62 + 0.05 * math.sin(t * 3), 0.10, 0.10, 0.10, (255, 130, 255))]
    for i in range(4):
        w = math.sin(t * 3 + i) * 0.02
        for k in range(4):
            P.append((-0.10 + i * 0.07, 0.11 + k * 0.025 + w * k, 0.58 - k * 0.08, 0.05, 0.05, 0.09, skD if k % 2 else sk))
    return P + _face(0.14, 0.11, 0.76, (255, 255, 255), (200, 200, 255), 0.06)


NEW_PARTS = {"kobold": _kobold, "gnoll": _gnoll, "zombie": _zombie, "ogre": _ogre, "owlbear": _owlbear,
             "gelatinous_cube": _cube, "mimic": _mimic, "troll": _troll, "goblin_king": _goblin_king,
             "beholder": _beholder, "minotaur": _minotaur, "lich": _lich, "mind_flayer": _mind_flayer}


parts_enemy_old = parts_enemy


def parts_enemy(kind, t):
    if kind in NEW_PARTS:
        return NEW_PARTS[kind](t)
    return parts_enemy_old(kind, t)


def pose_parts(parts, sx=1.0, sy=1.0, sz=1.0, lean=(0.0, 0.0)):
    """Squash/stretch e inclinação aplicados a todos os voxels."""
    return [(dx * sx + lean[0] * dz, dy * sy + lean[1] * dz, dz * sz, w * sx, d * sy, h * sz, c)
            for dx, dy, dz, w, d, h, c in parts]


def draw_parts_iso(surf, parts, ox, oy, s=1.0, soft=False, key=None):
    cam = (ox - OX, oy - OY)
    if soft:
        draw_world_parts(surf, world_parts(parts, 0.0, 0.0, 0.0, s), cam, ("menu", key), 0.008 * s)
        return
    items = []
    for dx, dy, dz, w, d, h, c in parts:
        x, y, z = dx * s, dy * s, dz * s
        items.append((x + w * s / 2 + y + d * s / 2, z, (x, y, z, w * s, d * s, h * s, c)))
    items.sort(key=lambda i: (round(i[0], 3), i[1]))
    for _, _, (x, y, z, w, d, h, c) in items:
        draw_box(surf, x, y, z, w, d, h, c, cam, True, 0.0)


ENEMY_NAMES = {"slime": "Gosma Verde", "goblin": "Goblin", "bat": "Morcego Gigante", "skeleton": "Esqueleto", "orc": "Orc Bravo",
               "wolfman": "Lobisomem", "ghost": "Fantasma", "golem": "Golem de Pedra",
               "kobold": "Kobold", "gnoll": "Gnoll", "zombie": "Zumbi", "ogre": "Ogro", "owlbear": "Urso-Coruja",
               "gelatinous_cube": "Cubo Gelatinoso", "mimic": "Mímico", "troll": "Troll",
               "goblin_king": "REI GOBLIN GIGANTE", "dragon": "DRAGÃO VERMELHO", "beholder": "BEHOLDER",
               "minotaur": "MINOTAURO", "lich": "LICH", "mind_flayer": "DEVORADOR DE MENTES",
               "goblin_chief": "CHEFE GOBLIN", "werewolf": "LOBISOMEM ALFA", "bat_queen": "RAINHA MORCEGO", "orc_chief": "CHEFE ORC"}
ENEMY_COLOR = {"slime": (80, 200, 90), "goblin": (90, 176, 108), "bat": (102, 118, 150), "skeleton": (230, 230, 214), "orc": (96, 156, 74),
               "wolfman": (150, 116, 100), "ghost": (200, 222, 255), "golem": (140, 140, 150),
               "kobold": (206, 92, 60), "gnoll": (180, 144, 88), "zombie": (122, 152, 112), "ogre": (204, 164, 112),
               "owlbear": (124, 86, 58), "gelatinous_cube": (120, 232, 190), "mimic": (150, 96, 50), "troll": (100, 148, 98),
               "goblin_king": (110, 200, 110), "dragon": (200, 60, 50), "beholder": (164, 70, 124),
               "minotaur": (112, 72, 50), "lich": (130, 90, 190), "mind_flayer": (156, 112, 196),
               "goblin_chief": (72, 140, 88), "werewolf": (120, 110, 106), "bat_queen": (162, 132, 255), "orc_chief": (122, 176, 102)}
ENEMY_SCALE = {"dragon": 1.5, "golem": 1.2, "orc": 1.1, "ogre": 1.3, "owlbear": 1.2, "troll": 1.3, "gelatinous_cube": 1.1,
               "goblin_king": 2.0, "beholder": 1.35, "minotaur": 1.5, "lich": 1.3, "mind_flayer": 1.3}
TIERS = [["slime", "kobold", "goblin", "bat"],
         ["skeleton", "zombie", "gnoll", "wolfman"],
         ["orc", "ghost", "mimic", "gelatinous_cube"],
         ["ogre", "owlbear", "troll", "golem"]]
REG_KINDS = [k for tier_ in TIERS for k in tier_]
BOSS_KINDS = ["goblin_chief", "dragon", "werewolf", "bat_queen", "orc_chief", "goblin_king", "beholder", "minotaur", "lich", "mind_flayer"]


# ======================================================================================
# PACOTE DE MONSTROS v3 (inspirado em Dungeons & Dragons)
# Sprites reconstruídos com mais camadas, sombreamento, animação e detalhes.
# Cada função devolve voxels (x, y, z, w, d, h, cor) no mesmo formato do resto do jogo.
# ======================================================================================
def m_eyes(P, hw, hd, z, ec=WHITE, pc=DARK, sz=0.055):
    P.extend(_face(hw, hd, z, ec, pc, sz))


def m_ring(P, cx, cy, z, rx, ry, n, size, c, t, speed=2.0, bob=0.03):
    for i in range(n):
        a = t * speed + i * math.tau / n
        P.b(cx + math.cos(a) * rx, cy + math.sin(a) * ry, z + bob * math.sin(t * 3 + i), size, size, size, c)


def m_flame(P, cx, cy, z, t, w=0.10, n=3, seed=0):
    cols = ((255, 90, 30), (255, 170, 40), (255, 235, 120))
    for i in range(n):
        f = 0.5 + 0.5 * math.sin(t * 9 + seed + i * 1.7)
        s = w * (1 - 0.25 * i)
        P.b(cx + 0.02 * math.sin(t * 7 + i + seed), cy + 0.02 * math.cos(t * 6 + i), z + i * 0.07 * (0.7 + f * 0.6),
            s, s, 0.08 + 0.05 * f, cols[min(i, 2)])


def m_legs2(P, sw, x, w, d, hf, hs, hk, c, cD, foot):
    """Duas pernas (pé, canela, coxa) que balançam com sw."""
    for s, off in ((-1, sw), (1, -sw)):
        l = max(0.0, off) * 0.05
        P.b(s * x, 0.015, l, w * 1.15, d * 1.4, hf, foot)
        P.b(s * x, 0.0, hf + l, w, d, hs, c)
        P.b(s * x, 0.0, hf + hs + l, w * 1.1, d * 1.05, hk, cD)



def m_wing(P, side, cx, cy, z, n, step, flap, c, cD, bone=None, span=0.07, thick=0.03, droop=0.0):
    """Asa de membrana contínua que sai para os lados (perpendicular à direção do olhar).
    flap = quanto as pontas sobem/descem; bone = cor dos ossos (dedos)."""
    ux, uy = -side * 0.7071, side * 0.7071
    fx, fy = 0.7071, 0.7071
    bone = bone or cD
    for i in range(n):
        r = 0.08 + i * step
        lift = flap * (i / max(1, n - 1)) - droop * (i / max(1, n - 1)) ** 2
        w = span * (1.15 - 0.55 * i / n)
        rows = (-1.0, 0.0, 1.0) if i < n - 2 else (0.0,)
        for rw in rows:
            off = rw * w * 0.95 - (0.03 * i if rw < 0 else 0.0) * 0.0
            px = cx + ux * r + fx * off
            py = cy + uy * r + fy * off
            P.b(px, py, z + lift, w * 1.25, w * 1.25, thick, c if rw else cD)
        P.b(cx + ux * r, cy + uy * r, z + lift + thick * 0.9, 0.035, 0.035, 0.022, bone)

# ------------------------------------------------------------------ TIER 0
def m_ooze(t):
    """Gosma Ácida: pilha de camadas gelatinosas com bolhas, crânio engolido e pingos."""
    sq = 1 + 0.09 * math.sin(t * 4)
    k, wk = 1 / sq, math.sqrt(sq)
    c, cL, cD = (78, 204, 104), (170, 248, 176), (36, 134, 70)
    P = _P()
    z = 0.0
    prof = [(1.00, 0.10), (1.14, 0.10), (1.10, 0.10), (0.96, 0.09), (0.78, 0.08), (0.52, 0.06)]
    for i, (f, h) in enumerate(prof):
        col = cL if i == len(prof) - 1 else (mix(c, 0.10) if i % 2 else c)
        P.b(0, 0, z, 0.62 * f * wk, 0.62 * f * wk, h * k, col)
        z += h * k
    P.b(0.30, 0.30, 0.00, 0.10, 0.10, 0.04, cD)
    P.b(-0.32, 0.20, 0.00, 0.12, 0.08, 0.03, cD)
    P.b(0.20, -0.30, 0.00, 0.08, 0.10, 0.03, cD)
    P.b(0.22, 0.22, 0.10, 0.15, 0.15, 0.14, (238, 234, 216))
    P.b(0.30, 0.30, 0.12, 0.03, 0.03, 0.05, DARK)
    P.b(0.17, 0.30, 0.12, 0.03, 0.03, 0.05, DARK)
    P.b(0.33, 0.13, 0.04, 0.05, 0.05, 0.03, (250, 206, 70))
    for i in range(4):
        u = (t * 0.30 + i * 0.27) % 1.0
        P.b(-0.16 + 0.12 * i - 0.1, -0.12 + 0.06 * i, 0.12 + u * 0.34, 0.05, 0.05, 0.05, mix(c, 0.65))
    P.b(-0.10, -0.10, z - 0.03, 0.14, 0.10, 0.03, WHITE)
    m_eyes(P, 0.345, 0.345, 0.27, WHITE, DARK, 0.075)
    P.b(0.04, 0.345, 0.17, 0.12, 0.02, 0.04, (30, 100, 56))
    return P


def m_kobold(t):
    c, cD, cL = (214, 98, 62), (150, 62, 44), (242, 150, 104)
    bel, horn, leath = (246, 208, 128), (244, 236, 200), (122, 84, 52)
    sw, wag = math.sin(t * 6), math.sin(t * 5)
    P = _P()
    m_legs2(P, sw, 0.07, 0.07, 0.08, 0.05, 0.09, 0.06, c, cD, cD)
    for i in range(6):
        P.b(-0.12 - 0.07 * i + wag * 0.02 * i, -0.12 - 0.07 * i - wag * 0.02 * i, 0.12 + 0.015 * i,
            0.08 - 0.01 * i, 0.08 - 0.01 * i, 0.07 - 0.008 * i, cD if i % 2 else c)
    P.b(0, 0, 0.20, 0.25, 0.19, 0.20, c)
    P.b(0, 0.098, 0.20, 0.15, 0.02, 0.17, bel)
    P.b(0.128, 0, 0.20, 0.02, 0.11, 0.17, bel)
    P.b(0, 0, 0.32, 0.27, 0.21, 0.08, leath)
    P.b(0, 0, 0.20, 0.27, 0.21, 0.03, (80, 56, 36))
    P.b(0.13, 0.11, 0.20, 0.04, 0.04, 0.04, (250, 206, 70))
    P.b(-0.17, 0, 0.22 + sw * 0.03, 0.06, 0.07, 0.16, c)
    P.b(0.17, 0, 0.22 - sw * 0.03, 0.06, 0.07, 0.16, c)
    P.b(0.17, 0.02, 0.19 - sw * 0.03, 0.07, 0.08, 0.05, cL)
    P.b(0.17, 0.10, 0.20 - sw * 0.03, 0.025, 0.14, 0.025, (206, 212, 224))
    P.b(0.17, 0.02, 0.22 - sw * 0.03, 0.05, 0.05, 0.03, leath)
    P.b(0, 0, 0.42, 0.25, 0.21, 0.15, c)
    P.b(0.07, 0.07, 0.44, 0.16, 0.16, 0.08, cL)
    P.b(0.14, 0.14, 0.50, 0.03, 0.03, 0.03, DARK)
    P.b(0.14, 0.08, 0.50, 0.03, 0.03, 0.03, DARK)
    P.b(0.08, 0.14, 0.50, 0.03, 0.03, 0.03, DARK)
    for sx in (-0.07, 0.07):
        P.b(sx, -0.06, 0.56, 0.04, 0.04, 0.10, horn)
    for i in range(3):
        P.b(-0.10 - 0.02 * i, -0.10 - 0.02 * i, 0.54 - 0.04 * i, 0.04, 0.10, 0.05, cD)
    m_eyes(P, 0.125, 0.105, 0.50, (255, 226, 60), DARK, 0.05)
    P.b(0.10, 0.155, 0.43, 0.02, 0.01, 0.03, WHITE)
    return P


# ------------------------------------------------------------------ helpers "chibi" (mesmas proporções do herói)
def _fat(P, cx, cy, hw):
    """Desenha na quina frontal de uma caixa quadrada (faces +x e +y).
    face 0 = +y (esquerda da tela), face 1 = +x (direita da tela); u = distância da quina."""
    def at(face, u, d_off, w, h, zz, col, dep=0.012):
        if face == 0:
            P.b(cx + hw - u - w / 2, cy + hw + d_off, zz, w, dep, h, col)
        else:
            P.b(cx + hw + d_off, cy + hw - u - w / 2, zz, dep, w, h, col)
    return at


def _c_legs(P, sw, boot, pant, sep=0.085, w=0.13, hl=0.075, hb=0.065, lift=0.06, toe=0.03):
    """Duas pernas curtinhas (bota + calça) no mesmo layout do herói."""
    for s, off in ((1, sw), (-1, -sw)):
        l = max(0.0, off) * lift
        cx, cy = sep * s, -sep * s
        P.b(cx, cy, hb - 0.005 + l, w * 0.9, w * 0.9, hl, pant)
        P.b(cx + toe, cy + toe, l, w + 0.02, w + 0.02, hb, boot)


def m_goblin(t):
    """Goblin: baixinho, orelhões pontudos, nariz grande, colete de couro, adaga e saquinho de moedas."""
    sk, skD, skL = (128, 206, 98), (86, 150, 64), (170, 230, 132)
    lea, leaD, cloth = (168, 118, 70), (104, 70, 44), (190, 70, 64)
    metal, gold = (206, 212, 226), (250, 208, 90)
    sw = math.sin(t * 7)
    arm = math.sin(t * 6) * 0.04
    b = abs(math.sin(t * 7)) * 0.012
    P = _P()
    _c_legs(P, sw, leaD, skD, sep=0.08, w=0.12, hl=0.07, hb=0.06)
    # tanga / saia de pano
    P.b(0.0, 0.0, 0.085, 0.29, 0.27, 0.05, cloth)
    P.b(0.12, 0.12, 0.035, 0.09, 0.09, 0.08, cloth)
    P.b(0.12, 0.12, 0.035, 0.09, 0.09, 0.025, shade(cloth, 0.75))
    # tronco: pele + colete de couro
    P.b(0.0, 0.0, 0.11 + b, 0.30, 0.28, 0.26, sk)
    P.b(0.0, 0.0, 0.11 + b, 0.325, 0.30, 0.20, lea)
    P.wrap(0.0, 0.0, 0.325, 0.30, 0.11 + b, 0.04, leaD)
    P.b(0.17, 0.15, 0.13 + b, 0.02, 0.05, 0.05, gold)                       # fivela
    for i in range(3):                                                        # costuras do colete
        P.b(0.164, 0.02 - 0.06 * i, 0.20 + b, 0.014, 0.03, 0.09, shade(lea, 1.25))
        P.b(-0.02 - 0.06 * i + 0.04, 0.152, 0.20 + b, 0.03, 0.014, 0.09, shade(lea, 1.25))
    P.b(0.0, 0.0, 0.31 + b, 0.30, 0.28, 0.05, sk)                           # ombros
    # saquinho de moedas no quadril
    P.b(0.19, -0.13, 0.10 + b, 0.10, 0.10, 0.10, leaD)
    P.b(0.19, -0.13, 0.19 + b, 0.07, 0.07, 0.03, lea)
    P.b(0.245, -0.13, 0.13 + b, 0.014, 0.04, 0.04, gold)
    # braço A (direita da tela): adaga
    ax, ay = 0.19 + arm * 0.7, -0.19 + arm * 0.7
    P.b(ax * 0.97, ay * 0.97, 0.24 + b, 0.085, 0.085, 0.14, sk)
    P.b(ax, ay, 0.19 + b, 0.095, 0.095, 0.075, skD)
    P.b(ax, ay, 0.255 + b, 0.05, 0.05, 0.06, leaD)
    P.b(ax, ay, 0.31 + b, 0.15, 0.05, 0.03, gold)
    for i in range(5):
        P.b(ax + 0.012 * i, ay + 0.012 * i, 0.34 + b + 0.065 * i, 0.05 - 0.006 * i, 0.04, 0.07, metal if i else shade(metal, 0.8))
    # braço B (esquerda da tela): segura uma moeda
    bx, by = -0.19 - arm * 0.7, 0.19 - arm * 0.7
    P.b(bx * 0.97, by * 0.97, 0.24 + b, 0.085, 0.085, 0.14, sk)
    P.b(bx, by, 0.19 + b, 0.095, 0.095, 0.075, skD)
    P.b(bx, by, 0.265 + b + 0.01 * math.sin(t * 5), 0.07, 0.07, 0.015, gold)
    # cabeça grande
    hz = 0.34 + b
    P.b(0.0, 0.0, hz, 0.44, 0.44, 0.30, sk)
    P.b(0.0, 0.0, hz, 0.44, 0.44, 0.04, skD)                                 # queixo sombreado
    P.wrap(0.0, 0.0, 0.44, 0.44, hz + 0.20, 0.04, skD, 0.03)                 # sobrancelha pesada
    # nariz grande e pontudo na quina
    P.b(0.215, 0.215, hz + 0.075, 0.085, 0.085, 0.085, skL)
    P.b(0.262, 0.262, hz + 0.075, 0.05, 0.05, 0.05, skD)
    # orelhões pontudos (um de cada lado), apontando para cima e para fora
    for sgn in (1, -1):
        for i in range(3):
            ex = 0.21 * sgn + 0.05 * sgn * i
            ey = -0.21 * sgn - 0.05 * sgn * i
            sz = 0.10 - 0.022 * i
            P.b(ex, ey, hz + 0.13 + 0.06 * i, sz, sz, 0.075 - 0.01 * i, sk if i < 2 else skL)
        P.b(0.215 * sgn + 0.02 * sgn, -0.215 * sgn - 0.02 * sgn, hz + 0.14, 0.045, 0.045, 0.05, mix(sk, 0.35, (230, 120, 130)))
    at = _fat(P, 0.0, 0.0, 0.22)
    blink = (t % 3.3) < 0.1
    eh = 0.10 * (0.2 if blink else 1.0)
    for face in (0, 1):
        at(face, 0.125, 0.003, 0.095, eh, hz + 0.14, (255, 226, 70), 0.014)
        if not blink:
            at(face, 0.10, 0.008, 0.045, 0.075, hz + 0.152, (188, 30, 30), 0.012)
            at(face, 0.092, 0.012, 0.022, 0.03, hz + 0.19, WHITE, 0.012)
        at(face, 0.095, 0.006, 0.15, 0.028, hz + 0.245, skD, 0.012)          # sobrancelha brava
        at(face, 0.07, 0.002, 0.15, 0.04, hz + 0.045, (82, 32, 40), 0.012)   # boca
        at(face, 0.085, 0.006, 0.032, 0.05, hz + 0.058, WHITE, 0.012)        # presas
        at(face, 0.17, 0.006, 0.032, 0.05, hz + 0.058, WHITE, 0.012)
    # boné de couro curto com pena
    P.b(0.0, 0.0, hz + 0.27, 0.46, 0.46, 0.045, lea)
    P.b(0.0, 0.0, hz + 0.315, 0.36, 0.36, 0.04, leaD)
    P.b(-0.15, -0.15, hz + 0.33 + 0.01 * math.sin(t * 6), 0.05, 0.05, 0.09, (240, 240, 235))
    P.b(-0.18, -0.18, hz + 0.39 + 0.015 * math.sin(t * 6), 0.045, 0.045, 0.06, cloth)
    return P


def m_skeleton(t):
    """Esqueleto guerreiro: crânio grande, costelas, elmo enferrujado, espada velha e escudo de madeira."""
    bone, boneD, boneS = (246, 242, 224), (198, 192, 170), (150, 144, 126)
    dark = (34, 28, 42)
    rust, rustD = (166, 124, 88), (116, 84, 60)
    cloth = (176, 58, 64)
    steel, wood, woodD, gold = (196, 204, 218), (134, 92, 56), (96, 64, 40), (232, 184, 84)
    sw = math.sin(t * 5)
    arm = math.sin(t * 3) * 0.035
    b = math.sin(t * 3) * 0.008
    P = _P()
    # pernas de osso
    for s, off in ((1, sw), (-1, -sw)):
        l = max(0.0, off) * 0.05
        cx, cy = 0.085 * s, -0.085 * s
        P.b(cx + 0.03, cy + 0.03, l, 0.15, 0.15, 0.045, boneD)
        P.b(cx, cy, 0.04 + l, 0.075, 0.075, 0.07, bone)
        P.b(cx, cy, 0.10 + l, 0.105, 0.105, 0.04, boneD)
    # bacia
    P.b(0.0, 0.0, 0.13 + b, 0.31, 0.25, 0.065, boneD)
    P.b(0.0, 0.0, 0.17 + b, 0.28, 0.22, 0.03, bone)
    # caixa torácica: núcleo escuro + costelas por fora
    P.b(0.0, 0.0, 0.19 + b, 0.26, 0.22, 0.24, dark)
    for i in range(4):
        w_ = 0.31 - 0.012 * i
        P.wrap(0.0, 0.0, w_, 0.27 - 0.012 * i, 0.205 + b + 0.056 * i, 0.034, bone, 0.034)
    P.b(0.152, 0.138, 0.20 + b, 0.04, 0.04, 0.22, boneD)                       # esterno na quina
    P.b(0.0, 0.0, 0.405 + b, 0.40, 0.14, 0.04, bone)                           # clavículas
    P.b(0.0, 0.0, 0.405 + b, 0.14, 0.40, 0.04, bone)
    # lenço rasgado no pescoço
    P.wrap(0.0, 0.0, 0.25, 0.21, 0.38 + b, 0.05, cloth, 0.03)
    P.b(0.14, 0.12, 0.30 + b, 0.04, 0.04, 0.09, cloth)
    P.b(0.14, 0.12, 0.27 + b, 0.03, 0.03, 0.04, shade(cloth, 0.7))
    # braço A (direita da tela): espada enferrujada
    ax, ay = 0.215 + arm * 0.7, -0.215 + arm * 0.7
    P.b(ax, ay, 0.395 + b, 0.095, 0.095, 0.09, boneD)                           # ombro
    P.b(ax, ay, 0.285 + b, 0.058, 0.058, 0.11, bone)                            # úmero
    P.b(ax, ay, 0.22 + b, 0.052, 0.052, 0.07, bone)                             # antebraço
    P.b(ax, ay, 0.165 + b, 0.085, 0.085, 0.06, boneD)                           # mão
    P.b(ax, ay, 0.19 + b, 0.05, 0.05, 0.07, woodD)
    P.b(ax, ay, 0.25 + b, 0.15, 0.05, 0.03, gold)
    for i in range(6):
        P.b(ax + 0.012 * i, ay + 0.012 * i, 0.28 + b + 0.07 * i, 0.055, 0.04, 0.075,
            rust if i < 2 else (steel if i < 5 else (236, 240, 250)))
    # braço B (esquerda da tela): escudo de madeira
    bx, by = -0.215 - arm * 0.7, 0.215 - arm * 0.7
    P.b(bx, by, 0.395 + b, 0.095, 0.095, 0.09, boneD)
    P.b(bx, by, 0.285 + b, 0.058, 0.058, 0.11, bone)
    P.b(bx, by, 0.22 + b, 0.052, 0.052, 0.07, bone)
    P.b(bx, by, 0.165 + b, 0.085, 0.085, 0.06, boneD)
    P.b(bx - 0.01, by + 0.09, 0.15 + b, 0.25, 0.045, 0.29, steel)
    P.b(bx - 0.01, by + 0.113, 0.17 + b, 0.20, 0.03, 0.25, wood)
    P.b(bx - 0.01, by + 0.113, 0.21 + b, 0.20, 0.032, 0.03, woodD)
    P.b(bx - 0.01, by + 0.113, 0.28 + b, 0.20, 0.032, 0.03, woodD)
    P.b(bx - 0.01, by + 0.132, 0.245 + b, 0.075, 0.03, 0.075, gold)
    # crânio
    hz = 0.42 + b
    P.b(0.0, 0.0, hz + 0.09, 0.46, 0.46, 0.25, bone)
    P.b(0.0, 0.0, hz, 0.40, 0.40, 0.095, boneD)                                 # mandíbula
    P.b(0.0, 0.0, hz + 0.34, 0.40, 0.40, 0.012, boneS)
    at = _fat(P, 0.0, 0.0, 0.23)
    aj = _fat(P, 0.0, 0.0, 0.20)
    for face in (0, 1):
        at(face, 0.115, 0.003, 0.115, 0.125, hz + 0.145, dark, 0.016)             # órbita
        at(face, 0.095, 0.010, 0.05, 0.06, hz + 0.165, (255, 70, 56), 0.014)      # olho em brasa
        at(face, 0.088, 0.014, 0.02, 0.025, hz + 0.205, (255, 214, 190), 0.012)
        at(face, 0.0, 0.003, 0.04, 0.05, hz + 0.105, dark, 0.014)                 # buraco do nariz
        for k in range(4):                                                         # dentes
            aj(face, 0.012 + 0.045 * k, 0.004, 0.034, 0.05, hz + 0.03, WHITE if k % 2 == 0 else boneD, 0.012)
        aj(face, 0.0, 0.002, 0.18, 0.012, hz + 0.075, dark, 0.012)                # fenda da boca
    at(1, 0.20, 0.004, 0.014, 0.09, hz + 0.20, boneS, 0.012)                      # rachaduras
    at(1, 0.185, 0.004, 0.04, 0.012, hz + 0.255, boneS, 0.012)
    at(0, 0.03, 0.004, 0.014, 0.07, hz + 0.20, boneS, 0.012)
    # elmo velho e enferrujado
    P.b(0.0, 0.0, hz + 0.275, 0.50, 0.50, 0.07, rust)
    P.b(0.0, 0.0, hz + 0.335, 0.42, 0.42, 0.065, rustD)
    P.b(0.0, 0.0, hz + 0.395, 0.06, 0.06, 0.06, rust)
    P.b(0.15, 0.15, hz + 0.275, 0.06, 0.06, 0.07, rustD)                          # amassado
    for i in range(3):                                                             # tirinha de pano ao vento
        wv = math.sin(t * 5 - i * 0.9) * 0.03
        P.b(-0.20 - 0.06 * i + wv, -0.20 - 0.06 * i - wv, hz + 0.31 - 0.03 * i, 0.07, 0.07, 0.055, shade(cloth, 1.0 - 0.1 * i))
    return P


def m_zombie(t):
    """Zumbi: pele esverdeada, farrapos, braços esticados para a frente, olho saltado e boca ensanguentada."""
    sk, skD, skL = (150, 186, 128), (104, 142, 92), (182, 214, 154)
    rag, ragD, ragL = (170, 142, 106), (112, 88, 64), (214, 190, 152)
    pant, pantD = (82, 96, 146), (56, 66, 108)
    blood, bone, hair = (160, 34, 42), (234, 226, 200), (62, 72, 50)
    sw = math.sin(t * 2.6)
    sway = math.sin(t * 2.2) * 0.022
    b = math.sin(t * 2.2) * 0.012
    P = _P()
    # pernas: uma bota/pé descalço arrastando
    for s, off in ((1, sw), (-1, -sw)):
        l = max(0.0, off) * 0.045
        cx, cy = 0.085 * s, -0.085 * s
        P.b(cx, cy, 0.06 + l, 0.12, 0.12, 0.075 if s > 0 else 0.055, pant if s > 0 else pantD)
        P.b(cx + 0.03, cy + 0.03, l, 0.15, 0.15, 0.065, skD if s > 0 else ragD)
    P.b(0.085 + 0.02, -0.085 + 0.02, 0.095, 0.125, 0.125, 0.025, shade(pant, 0.7))   # barra rasgada
    P.b(-0.085, 0.085 + 0.05, 0.015, 0.04, 0.05, 0.03, skL)                          # dedos do pé
    # tronco rasgado
    P.b(0.0, 0.0, 0.12 + b, 0.34, 0.32, 0.30, rag)
    P.b(0.0, 0.0, 0.12 + b, 0.35, 0.33, 0.05, ragD)
    at = _fat(P, 0.0, 0.0, 0.165)
    at(1, 0.07, 0.004, 0.13, 0.13, 0.20 + b, skD, 0.016)                              # rasgo mostrando a pele
    for k in range(3):
        at(1, 0.085 + 0.035 * k, 0.010, 0.014, 0.10, 0.215 + b, bone, 0.012)           # costelas à mostra
    at(1, 0.07, 0.011, 0.13, 0.025, 0.20 + b, blood, 0.012)
    at(0, 0.03, 0.004, 0.10, 0.07, 0.30 + b, ragL, 0.014)                              # remendo
    at(0, 0.12, 0.004, 0.10, 0.12, 0.17 + b, blood, 0.010)                             # mancha de sangue
    for i, hh in enumerate((0.05, 0.03, 0.06, 0.035)):                                 # barra esfarrapada
        P.b(0.16 - 0.095 * i * 0.7, 0.15 - 0.0, 0.12 + b - hh * 0.5, 0.07, 0.03, hh, ragD)
    P.wrap(0.0, 0.0, 0.34, 0.32, 0.17 + b, 0.035, (96, 72, 50))                         # cordão na cintura
    P.b(0.175, 0.16, 0.17 + b, 0.03, 0.04, 0.05, (96, 72, 50))
    # braços esticados para a frente (+x,+y), balançando
    for side, ph in ((1, 0.0), (-1, 2.2)):
        sx0, sy0 = 0.215 * side, -0.215 * side
        up = math.sin(t * 2.6 + ph) * 0.03
        P.b(sx0, sy0, 0.285 + b, 0.105, 0.105, 0.12, rag)                              # manga rasgada
        for i in range(1, 5):
            col = rag if i == 1 else (skD if i == 2 else sk)
            P.b(sx0 + 0.065 * i, sy0 + 0.065 * i, 0.31 + b + up + 0.006 * i, 0.095, 0.095, 0.09 if i < 4 else 0.08, col)
        hx, hy, hz_ = sx0 + 0.30, sy0 + 0.30, 0.315 + b + up
        for k in (-1, 0, 1):                                                           # dedos
            P.b(hx + 0.03 + k * 0.026, hy + 0.03 - k * 0.026, hz_ + 0.01, 0.03, 0.03, 0.03, skL)
        P.b(sx0 + 0.13, sy0 + 0.13, 0.405 + b + up, 0.03, 0.03, 0.025, bone if side > 0 else blood)   # osso exposto / sangue
    # cabeça
    hx_, hy_ = 0.03 + sway, 0.03 + sway
    hz = 0.42 + b
    P.b(hx_, hy_, hz, 0.46, 0.44, 0.33, sk)
    P.b(hx_, hy_, hz, 0.46, 0.44, 0.04, skD)
    atH = _fat(P, hx_, hy_, 0.22)
    # olho esquerdo da tela: fundo e fundo escuro; olho direito: grande e saltado
    atH(0, 0.095, 0.003, 0.11, 0.07, hz + 0.135, (80, 70, 90), 0.014)                  # olheira
    atH(0, 0.105, 0.006, 0.08, 0.075, hz + 0.18, (255, 248, 140), 0.014)
    atH(0, 0.09, 0.010, 0.04, 0.05, hz + 0.19, (170, 24, 24), 0.012)
    atH(1, 0.09, 0.003, 0.11, 0.07, hz + 0.135, (80, 70, 90), 0.014)
    atH(1, 0.10, 0.008, 0.10, 0.11, hz + 0.165, (255, 248, 140), 0.016)
    atH(1, 0.085, 0.014, 0.05, 0.07, hz + 0.185, (170, 24, 24), 0.014)
    atH(1, 0.078, 0.018, 0.022, 0.03, hz + 0.225, WHITE, 0.012)
    for face in (0, 1):
        atH(face, 0.05, 0.003, 0.17, 0.06, hz + 0.04, (74, 26, 34), 0.012)            # boca aberta
        atH(face, 0.07, 0.007, 0.035, 0.03, hz + 0.075, (222, 214, 190), 0.012)        # dentes tortos
        atH(face, 0.125, 0.007, 0.035, 0.025, hz + 0.075, (210, 200, 172), 0.012)
        atH(face, 0.09, 0.008, 0.03, 0.05, hz + 0.0, blood, 0.012)                     # baba de sangue
        atH(face, 0.0, 0.002, 0.04, 0.05, hz + 0.115, skD, 0.012)                      # nariz podre
    # cabelo ralo, curativo e crânio exposto
    P.b(hx_, hy_, hz + 0.31, 0.46, 0.44, 0.03, skD)
    P.b(hx_ - 0.10, hy_ - 0.06, hz + 0.34, 0.10, 0.10, 0.07, hair)
    P.b(hx_ + 0.05 + 0.1 * 0, hy_ - 0.12, hz + 0.34, 0.06, 0.06, 0.09 + 0.01 * math.sin(t * 3), hair)
    P.b(hx_ - 0.14, hy_ + 0.08, hz + 0.34, 0.07, 0.07, 0.06, hair)
    P.b(hx_ + 0.12, hy_ + 0.10, hz + 0.34, 0.12, 0.10, 0.035, bone)                   # crânio à mostra
    P.wrap(hx_, hy_, 0.46, 0.44, hz + 0.235, 0.05, ragL, 0.03)                          # atadura na testa
    P.b(hx_ - 0.24, hy_ - 0.20, hz + 0.235, 0.05, 0.05, 0.10 + 0.01 * math.sin(t * 4), ragL)
    return P


def m_bat(t):
    """Morcego Gigante v4: tronco peludo com peito claro, orelhões, presas, garras e asas em 'V'
    (a ponta sobe e desce no bater) com membrana grossa e ossos mais claros na borda."""
    wing, wingD, bone = (124, 118, 186), (72, 64, 126), (196, 188, 232)
    fur, furL, furD = (98, 90, 132), (138, 128, 172), (60, 54, 90)
    eye, pink = (255, 226, 110), (240, 170, 200)
    fl = math.sin(t * 9)
    z0 = 0.34 + 0.05 * math.sin(t * 3 + 1.0)
    P = _P()
    P.b(0, 0, z0, 0.26, 0.24, 0.22, fur)                      # tronco
    P.b(0.07, 0.07, z0 + 0.03, 0.16, 0.16, 0.15, furL)        # peito claro
    P.b(-0.11, -0.11, z0, 0.14, 0.14, 0.14, furD)             # traseira
    for sd in (-1, 1):                                        # pezinhos com garras
        fx, fy = -0.03 + sd * 0.05, -0.03 - sd * 0.05
        P.b(fx, fy, z0 - 0.09, 0.045, 0.045, 0.10, furD)
        P.b(fx + 0.02, fy + 0.02, z0 - 0.11, 0.03, 0.03, 0.03, (230, 224, 210))
    P.b(0, 0, z0 + 0.22, 0.26, 0.24, 0.18, fur)               # cabeça
    P.b(0.10, 0.10, z0 + 0.25, 0.10, 0.10, 0.07, furL)        # focinho
    P.b(0.152, 0.152, z0 + 0.285, 0.035, 0.035, 0.03, (44, 30, 52))   # nariz
    P.b(0.152, 0.075, z0 + 0.235, 0.022, 0.022, 0.05, WHITE)  # presas
    P.b(0.075, 0.152, z0 + 0.235, 0.022, 0.022, 0.05, WHITE)
    for sd in (-1, 1):                                        # orelhões pontudos
        ex, ey = -0.03 + sd * 0.062, -0.03 - sd * 0.062
        P.b(ex, ey, z0 + 0.39, 0.075, 0.075, 0.17, fur)
        P.b(ex + 0.012, ey + 0.012, z0 + 0.42, 0.045, 0.045, 0.11, pink)
        P.b(ex, ey, z0 + 0.56, 0.04, 0.04, 0.05, furD)
    for side in (1, -1):
        m_wing(P, side, 0, 0, z0 + 0.10, 7, 0.095, 0.10 + 0.24 * fl, wing, wingD, bone, 0.10, 0.042, 0.06)
    m_eyes(P, 0.13, 0.12, z0 + 0.30, eye, (170, 30, 40), 0.055)
    return P


def m_stirge(t):
    """Estirge v4: mosquito gigante - olhos compostos vermelhos, tromba longa com ponta de sangue,
    abdômen listrado que balança, seis perninhas e dois pares de asas translúcidas batendo rápido."""
    fl = math.sin(t * 24)
    z0 = 0.44 + 0.06 * math.sin(t * 3)
    c, cD, cL, wing = (178, 84, 62), (104, 46, 42), (216, 130, 96), (232, 226, 246)
    sway = 0.02 * math.sin(t * 3)
    P = _P()
    P.b(0, 0, z0, 0.22, 0.20, 0.20, c)                        # tórax
    P.b(0.05, 0.05, z0 + 0.04, 0.14, 0.14, 0.13, cL)          # dorso claro
    for i in range(4):                                        # abdômen listrado em curva descendente
        k = 0.11 + 0.075 * i
        P.b(-k - sway * i, -k + sway * i, z0 - 0.02 - 0.035 * i, 0.17 - 0.025 * i, 0.15 - 0.025 * i, 0.14 - 0.012 * i,
            cD if i % 2 else c)
    P.b(0.03, 0.03, z0 + 0.19, 0.20, 0.18, 0.15, c)           # cabeça
    for sd in (-1, 1):                                        # olhões compostos
        P.b(0.03 + sd * 0.085, 0.03 - sd * 0.085, z0 + 0.22, 0.075, 0.075, 0.085, (232, 60, 56))
        P.b(0.03 + sd * 0.085 + 0.02, 0.03 - sd * 0.085 + 0.02, z0 + 0.26, 0.025, 0.025, 0.03, (255, 200, 190))
    for i in range(6):                                        # tromba comprida
        P.b(0.13 + 0.05 * i, 0.13 + 0.05 * i, z0 + 0.22 - 0.022 * i, 0.05 - 0.0035 * i, 0.05 - 0.0035 * i, 0.045,
            (236, 228, 214) if i < 5 else (255, 70, 64))
    for k in range(3):                                        # perninhas pendentes
        for sd in (-1, 1):
            P.b(-0.03 + 0.05 * k + sd * 0.07, 0.03 - 0.05 * k - sd * 0.07, z0 - 0.17, 0.022, 0.022, 0.19, cD)
    for side, base in ((1, 0.20), (-1, 0.20)):                # dois pares de asas (cima grande, baixo pequeno)
        m_wing(P, side, -0.03, -0.03, z0 + 0.19, 5, 0.085, 0.10 + fl * 0.16, wing, mix(wing, 0.0, ), (150, 140, 180), 0.065, 0.03, 0.0)
        m_wing(P, side, -0.08, -0.08, z0 + 0.14, 3, 0.07, 0.04 - fl * 0.12, mix(wing, 0.1, (180, 170, 210)), wing, (150, 140, 180), 0.045, 0.026, 0.0)
    return P


# ------------------------------------------------------------------ TIER 1
def m_gnoll(t):
    fur, spot, mane, bone = (190, 150, 90), (112, 78, 46), (80, 52, 34), (236, 230, 212)
    sw, arm = math.sin(t * 6), math.sin(t * 5) * 0.04
    P = _P()
    m_legs2(P, sw, 0.09, 0.10, 0.12, 0.05, 0.14, 0.10, fur, spot, spot)
    P.b(0, 0, 0.28, 0.38, 0.22, 0.06, (150, 44, 44))
    P.b(0, 0, 0.32, 0.38, 0.24, 0.26, fur)
    for i in range(3):
        P.b(0.0, 0.13, 0.36 + 0.07 * i, 0.30 - 0.04 * i, 0.02, 0.035, bone)
    P.b(0.19, 0.0, 0.40, 0.02, 0.12, 0.05, spot)
    P.b(-0.06, 0.12, 0.50, 0.05, 0.02, 0.05, spot)
    P.b(0.0, 0, 0.56, 0.42, 0.26, 0.06, (110, 80, 54))
    P.b(-0.24, 0.0, 0.34 + arm, 0.09, 0.12, 0.26, fur)
    P.b(0.24, 0.0, 0.34 - arm, 0.09, 0.12, 0.26, fur)
    P.b(0.24, 0.03, 0.30 - arm, 0.10, 0.13, 0.05, spot)
    P.b(0.24, 0.10, 0.10 - arm, 0.04, 0.04, 0.44, (120, 84, 50))
    P.b(0.24, 0.10, 0.52 - arm, 0.06, 0.06, 0.14, (196, 202, 214))
    P.b(0.24, 0.10, 0.64 - arm, 0.035, 0.035, 0.06, (230, 236, 244))
    P.b(0, -0.02, 0.62, 0.26, 0.22, 0.17, fur)
    P.b(0.08, 0.08, 0.62, 0.17, 0.17, 0.09, (96, 66, 46))
    P.b(0.15, 0.15, 0.68, 0.06, 0.06, 0.04, DARK)
    P.b(0.10, 0.10, 0.61, 0.15, 0.02, 0.02, WHITE)
    for sx in (-0.10, 0.10):
        P.b(sx, -0.05, 0.78, 0.07, 0.04, 0.10, spot)
    for i in range(5):
        P.b(-0.06 - 0.02 * i, -0.10 - 0.02 * i, 0.82 - 0.04 * i, 0.06, 0.06, 0.12 - 0.01 * i, mane)
    P.b(0.02, 0.06, 0.74, 0.04, 0.04, 0.04, spot)
    m_eyes(P, 0.13, 0.11, 0.70, (255, 220, 60), (160, 30, 30), 0.05)
    return P


def m_wolfman(t):
    """Lobisomem: grandão, corcunda, focinho comprido, juba, garras enormes e rabo peludo."""
    fur, furD, furL = (132, 116, 108), (84, 72, 70), (186, 168, 148)
    belly, claw, pants = (214, 198, 172), (240, 232, 206), (96, 72, 58)
    eye, tongue = (255, 214, 60), (206, 70, 84)
    sw = math.sin(t * 6)
    arm = math.sin(t * 5) * 0.045
    b = abs(math.sin(t * 3)) * 0.014
    breathe = math.sin(t * 3) * 0.012
    P = _P()
    # pernas fortes com patas grandes e garras
    for s, off in ((1, sw), (-1, -sw)):
        l = max(0.0, off) * 0.05
        cx, cy = 0.095 * s, -0.095 * s
        P.b(cx + 0.04, cy + 0.04, l, 0.18, 0.18, 0.06, furD)
        for k in (-1, 0, 1):
            P.b(cx + 0.13 + 0.0, cy + 0.13 - 0.0 + 0.045 * k * 0, l, 0.03, 0.03, 0.03, claw) if k == 0 else None
        P.b(cx, cy, 0.055 + l, 0.14, 0.14, 0.085, fur)
    P.b(0.0, 0.0, 0.10, 0.36, 0.32, 0.07, pants)                              # calça rasgada
    P.b(0.17, 0.15, 0.06, 0.07, 0.07, 0.07, pants)
    P.b(0.0, 0.0, 0.07, 0.30, 0.28, 0.04, furD)
    # peito largo, barriga clara e costas peludas
    P.b(0.0, 0.0, 0.15 + b, 0.38, 0.34, 0.20, fur)
    P.b(0.0, 0.0, 0.32 + b + breathe, 0.44, 0.38, 0.17, furD)
    at = _fat(P, 0.0, 0.0, 0.17)
    at(0, 0.03, 0.004, 0.20, 0.17, 0.17 + b, belly, 0.014)
    at(1, 0.03, 0.004, 0.20, 0.17, 0.17 + b, belly, 0.014)
    for k in range(3):                                                        # pelos do peito
        P.b(0.20 - 0.04 * k, 0.20 - 0.04 * k, 0.30 + b - 0.0 * k, 0.07, 0.07, 0.10, furL)
    P.wrap(0.0, 0.0, 0.40, 0.35, 0.28 + b, 0.04, pants, 0.02)
    # braços longos com garras
    for side, ph in ((1, 0.0), (-1, math.pi)):
        a = math.sin(t * 5 + ph) * 0.045
        ax, ay = 0.27 * side + a * 0.7, -0.27 * side + a * 0.7
        P.b(ax, ay, 0.40 + b, 0.15, 0.15, 0.10, furD)                         # ombro
        P.b(ax, ay, 0.26 + b, 0.12, 0.12, 0.16, fur)
        P.b(ax, ay, 0.17 + b, 0.14, 0.14, 0.10, furD)                         # punho
        for k in (-1, 0, 1):
            P.b(ax + 0.03 + 0.0, ay + 0.03 + 0.04 * k * 0.7 - 0.0, 0.10 + b, 0.03, 0.03, 0.08, claw)
        for k in (-1, 1):
            P.b(ax + 0.05 * k * 0.7 + 0.05, ay - 0.05 * k * 0.7 + 0.05, 0.11 + b, 0.03, 0.03, 0.07, claw)
    # rabo peludo (atrás)
    for i in range(5):
        wv = math.sin(t * 4 - i * 0.8) * 0.03
        P.b(-0.20 - 0.06 * i + wv, -0.20 - 0.06 * i - wv, 0.20 + 0.035 * i + b, 0.12 - 0.012 * i, 0.12 - 0.012 * i, 0.11,
            furL if i == 4 else (fur if i % 2 else furD))
    # juba em volta do pescoço
    P.b(0.0, 0.0, 0.46 + b, 0.46, 0.42, 0.07, furL)
    P.wrap(0.0, 0.0, 0.46, 0.42, 0.46 + b, 0.07, furL, 0.04)
    # cabeça de lobo
    hz = 0.50 + b
    P.b(0.0, 0.0, hz, 0.40, 0.40, 0.30, fur)
    P.b(0.0, 0.0, hz + 0.26, 0.40, 0.40, 0.045, furD)
    # focinho comprido na quina + mandíbula aberta
    P.b(0.255, 0.255, hz + 0.075, 0.17, 0.17, 0.13, furL)
    P.b(0.255, 0.255, hz + 0.19, 0.15, 0.15, 0.03, fur)
    P.b(0.355, 0.355, hz + 0.14, 0.065, 0.065, 0.065, (28, 24, 32))          # nariz
    jaw = 0.5 + 0.5 * math.sin(t * 3)
    P.b(0.245, 0.245, hz + 0.0 - 0.02 * jaw, 0.15, 0.15, 0.045, furD)
    P.b(0.255, 0.255, hz + 0.05 - 0.01 * jaw, 0.12, 0.12, 0.03, (84, 24, 34))
    P.b(0.285, 0.285, hz + 0.045, 0.05, 0.05, 0.02, tongue)
    atM = _fat(P, 0.255, 0.255, 0.085)
    for face in (0, 1):
        for k in (0, 1):
            atM(face, 0.01 + 0.075 * k, 0.012, 0.025, 0.05, hz + 0.058, WHITE, 0.012)        # presas
            atM(face, 0.04 + 0.05 * k, 0.012, 0.02, 0.035, hz + 0.047 - 0.02 * jaw, WHITE, 0.012)
    # olhos amarelos com pupila de fenda e sobrancelha brava
    ah = _fat(P, 0.0, 0.0, 0.20)
    for face in (0, 1):
        ah(face, 0.075, 0.004, 0.09, 0.09, hz + 0.145, eye, 0.016)
        ah(face, 0.105, 0.010, 0.02, 0.09, hz + 0.145, DARK, 0.014)
        ah(face, 0.06, 0.008, 0.13, 0.03, hz + 0.235, furD, 0.014)
    # orelhas pontudas
    for sgn in (1, -1):
        ex, ey = 0.12 * sgn + 0.09, -0.12 * sgn + 0.09
        P.b(0.15 * sgn - 0.02, -0.15 * sgn - 0.02, hz + 0.30, 0.11, 0.11, 0.08, furD)
        P.b(0.15 * sgn - 0.02, -0.15 * sgn - 0.02, hz + 0.37, 0.08, 0.08, 0.07, fur)
        P.b(0.15 * sgn - 0.02, -0.15 * sgn - 0.02, hz + 0.43, 0.045, 0.045, 0.05, furD)
        P.b(0.15 * sgn - 0.005, -0.15 * sgn - 0.005, hz + 0.31, 0.04, 0.04, 0.07, (222, 140, 150))
    return P


# ------------------------------------------------------------------ utilidades de quadrúpedes
def dp(a, s=0.0):
    """Quadrúpedes ficam de perfil: 'a' = ao longo do corpo (+x é a frente), 's' = para o lado (+y mostra o flanco)."""
    return (a, s)


def m_quad(P, t, c, cD, cL, body_len=0.52, bw=0.26, bh=0.24, lh=0.20, lw=0.08, legs=None, walk=6.0, foot=None):
    legs = legs or ((-0.22, -0.11), (-0.22, 0.11), (0.22, -0.11), (0.22, 0.11))
    for i, (a, s) in enumerate(legs):
        sw = math.sin(t * walk + (0.0 if ((a > 0) == (s > 0)) else math.pi) + i * 0.4)
        l = max(0.0, sw) * 0.06
        x, y = dp(a, s)
        P.b(x, y, l, lw * 1.35, lw * 1.35, 0.04, foot or cD)
        P.b(x, y, 0.04 + l, lw, lw, lh - 0.04, cD)
        P.b(x, y, lh - 0.04 + l, lw * 1.45, lw * 1.45, 0.10, c)
    n = 3
    for k in range(n):
        a = -body_len / 2 + body_len * k / (n - 1)
        x, y = dp(a)
        P.b(x, y, lh + 0.04, bw, bw, bh, c)
        P.b(x, y, lh + 0.04 + bh - 0.01, bw * 0.78, bw * 0.78, 0.04, cL)


# ------------------------------------------------------------------ TIER 2
def m_orc(t):
    skin, skinD, leath = (108, 168, 80), (74, 124, 56), (112, 76, 46)
    metal, metalL, bone, red = (138, 144, 158), (196, 202, 216), (240, 238, 224), (196, 44, 44)
    sw, arm = math.sin(t * 5), math.sin(t * 3) * 0.03
    P = _P()
    m_legs2(P, sw, 0.12, 0.14, 0.16, 0.06, 0.13, 0.10, (88, 62, 42), leath, (58, 42, 30))
    P.b(0, 0, 0.30, 0.52, 0.34, 0.07, leath)
    P.b(0.26, 0.06, 0.28, 0.06, 0.07, 0.08, bone)
    P.b(0.06, 0.17, 0.28, 0.07, 0.06, 0.08, bone)
    P.b(0, 0, 0.37, 0.56, 0.36, 0.30, skin)
    P.b(0, 0.185, 0.40, 0.36, 0.02, 0.24, metal)
    P.b(0.285, 0, 0.40, 0.02, 0.22, 0.24, metal)
    for i in range(3):
        P.b(0, 0.195, 0.44 + 0.07 * i, 0.30, 0.01, 0.025, metalL)
    P.b(-0.10, 0.20, 0.50, 0.03, 0.02, 0.17, leath)
    P.b(0.10, 0.20, 0.50, 0.03, 0.02, 0.17, leath)
    for s_ in (-1, 1):
        P.b(s_ * 0.38, 0, 0.62, 0.18, 0.30, 0.09, metal)
        P.b(s_ * 0.38, 0, 0.70, 0.07, 0.07, 0.10, bone)
        P.b(s_ * 0.38, -0.01, 0.34 - s_ * arm, 0.12, 0.16, 0.28, skin)
        P.b(s_ * 0.38, 0.0, 0.28 - s_ * arm, 0.14, 0.18, 0.08, skinD)
    P.b(0, 0, 0.67, 0.36, 0.30, 0.20, skin)
    P.b(0.10, 0.10, 0.67, 0.20, 0.20, 0.08, skinD)
    P.b(0.17, 0.20, 0.72, 0.035, 0.035, 0.09, bone)
    P.b(0.20, 0.17, 0.72, 0.035, 0.035, 0.09, bone)
    P.b(0.0, 0.16, 0.76, 0.22, 0.01, 0.03, red)
    P.b(0, 0, 0.84, 0.38, 0.32, 0.06, metal)
    P.b(0, 0, 0.90, 0.20, 0.18, 0.05, metalL)
    for s_ in (-1, 1):
        P.b(s_ * 0.22, 0, 0.88, 0.05, 0.05, 0.14, bone)
        P.b(s_ * 0.27, 0, 1.00, 0.04, 0.04, 0.07, bone)
    P.b(0.50, 0.16, 0.08 - arm, 0.05, 0.05, 0.84, leath)
    P.b(0.50, 0.16, 0.74 - arm, 0.05, 0.30, 0.24, (180, 186, 202))
    P.b(0.50, 0.32, 0.78 - arm, 0.05, 0.05, 0.16, metalL)
    P.b(0.50, 0.00, 0.82 - arm, 0.06, 0.08, 0.09, metal)
    m_eyes(P, 0.185, 0.155, 0.76, (255, 232, 60), (200, 30, 30), 0.06)
    return P


def m_ghost(t):
    """Espectro encapuzado, com cauda de névoa, correntes e luzes fantasmas."""
    z0 = 0.30 + 0.06 * math.sin(t * 3)
    c, cD, cL, glow = (206, 226, 255), (140, 170, 228), (238, 248, 255), (120, 236, 255)
    sw = math.sin(t * 2) * 0.02
    P = _P()
    for i in range(6):
        a = i * math.tau / 6
        h = 0.14 + 0.08 * math.sin(t * 5 + i * 1.4)
        P.b(math.cos(a) * 0.17, math.sin(a) * 0.17, z0 - h, 0.12, 0.12, h, cD if i % 2 else c)
        P.b(math.cos(a) * 0.17, math.sin(a) * 0.17, z0 - h - 0.07, 0.07, 0.07, 0.07, mix(c, 0.5))
    for i, (wd, h) in enumerate([(0.48, 0.14), (0.46, 0.14), (0.42, 0.12), (0.40, 0.12), (0.36, 0.10)]):
        P.b(sw * i * 0.3, 0, z0 + sum(x[1] for x in [(0.48, 0.14), (0.46, 0.14), (0.42, 0.12), (0.40, 0.12), (0.36, 0.10)][:i]), wd, wd * 0.9, h, c if i % 2 == 0 else mix(c, 0.1))
    zt = z0 + 0.62
    P.b(sw, 0, zt, 0.40, 0.36, 0.14, c)
    P.b(sw, 0, zt + 0.14, 0.30, 0.28, 0.08, cL)
    P.b(sw, 0, zt + 0.22, 0.16, 0.16, 0.05, cL)
    P.b(0, 0.185, zt + 0.02, 0.24, 0.02, 0.16, (14, 18, 40))
    P.b(0.205, 0, zt + 0.02, 0.02, 0.22, 0.16, (14, 18, 40))
    m_eyes(P, 0.15, 0.13, zt + 0.07, glow, (255, 255, 255), 0.055)
    for s_ in (1, -1):
        r = math.sin(t * 4 + s_) * 0.04
        P.b(0.30 * s_ * 0.9, 0.04, z0 + 0.30 + r, 0.10, 0.28, 0.10, cD)
        for k in range(3):
            P.b(0.30 * s_ * 0.9 + (k - 1) * 0.03, 0.22, z0 + 0.28 + r, 0.02, 0.10, 0.03, cL)
    for i in range(5):
        P.b(0.02 + 0.07 * (i % 2), 0.20 + 0.0, z0 + 0.42 - 0.06 * i, 0.06, 0.02, 0.05, (120, 126, 150))
    m_ring(P, 0, 0, z0 + 0.40, 0.46, 0.46, 3, 0.07, glow, t, 2.0, 0.06)
    return P


def m_mimic(t):
    wood, woodD, lid, band = (156, 100, 52), (108, 68, 36), (186, 124, 66), (92, 92, 108)
    tongue, gold = (222, 72, 98), (252, 210, 72)
    o = 0.18 * (0.5 + 0.5 * math.sin(t * 4)) + 0.04
    hop = max(0.0, math.sin(t * 4)) * 0.03
    P = _P()
    for sx, sy in ((-0.30, -0.20), (0.30, -0.20), (-0.30, 0.20), (0.30, 0.20)):
        P.b(sx, sy, hop, 0.12, 0.12, 0.12, woodD)
        P.b(sx, sy, 0.0, 0.14, 0.14, 0.03, (70, 46, 26))
    P.b(0, 0, 0.12 + hop, 0.80, 0.56, 0.30, wood)
    P.b(0, 0, 0.12 + hop, 0.82, 0.58, 0.04, band)
    P.b(0, 0, 0.38 + hop, 0.82, 0.58, 0.04, band)
    for s_ in (-0.26, 0.26):
        P.b(s_, 0, 0.12 + hop, 0.06, 0.58, 0.30, band)
    P.b(0, 0.295, 0.22 + hop, 0.12, 0.02, 0.14, gold)
    P.b(0.415, 0, 0.22 + hop, 0.02, 0.12, 0.14, gold)
    P.b(0, 0.31, 0.26 + hop, 0.03, 0.01, 0.06, DARK)
    P.b(0, 0, 0.42 + hop, 0.72, 0.48, 0.03, (104, 22, 42))
    for i in range(5):
        P.b(-0.26 + 0.11 * i, -0.04 + 0.05 * (i % 3), 0.45 + hop, 0.06, 0.06, 0.03, gold)
    P.b(0.10, 0.10, 0.45 + hop, 0.22, 0.34, 0.04, tongue)
    P.b(0.10, 0.28, 0.46 + hop, 0.12, 0.10, 0.04, mix(tongue, 0.2))
    for i in range(6):
        P.b(-0.30 + i * 0.12, 0.28, 0.45 + hop, 0.055, 0.05, 0.11, WHITE)
        P.b(0.40, -0.22 + i * 0.09, 0.45 + hop, 0.05, 0.055, 0.11, WHITE)
    P.b(0, -0.20, 0.44 + hop, 0.82, 0.12, 0.30 + o, lid)
    P.b(0, -0.06, 0.74 + hop + o, 0.82, 0.44, 0.08, lid)
    P.b(0, -0.06, 0.74 + hop + o, 0.84, 0.46, 0.03, band)
    for i in range(6):
        P.b(-0.30 + i * 0.12, 0.14, 0.64 + hop + o, 0.055, 0.05, 0.10, WHITE)
        P.b(0.38, -0.20 + i * 0.09, 0.64 + hop + o, 0.05, 0.055, 0.10, WHITE)
    for sx in (-0.18, 0.18):
        P.b(sx, -0.06, 0.82 + hop + o, 0.05, 0.05, 0.10, woodD)
        P.b(sx, -0.06, 0.92 + hop + o, 0.13, 0.13, 0.13, WHITE)
        P.b(sx + 0.05, 0.02, 0.95 + hop + o, 0.05, 0.03, 0.07, (200, 40, 40))
    return P


def m_cube(t):
    w = 0.03 * math.sin(t * 3)
    out, inn, hl = (118, 232, 188), (76, 190, 156), (200, 255, 236)
    bone, gold, steel = (238, 234, 218), (252, 208, 72), (200, 206, 216)
    P = _P()
    P.b(0, 0, 0, 0.80, 0.80, 0.80 + w, out)
    P.b(0, 0, 0.04, 0.66, 0.66, 0.66 + w, inn)
    P.b(0, 0, 0.78 + w, 0.80, 0.80, 0.03, hl)
    for i in range(4):
        a = i * math.pi / 2 + t * 0.5
        P.b(math.cos(a) * 0.28, math.sin(a) * 0.28, 0.80 + w, 0.10, 0.10, 0.04 + 0.03 * math.sin(t * 4 + i), hl)
    P.b(0.30, 0.0, 0.36 + w, 0.16, 0.16, 0.16, bone)
    P.b(0.40, 0.04, 0.38 + w, 0.03, 0.03, 0.05, DARK)
    P.b(0.40, -0.04, 0.38 + w, 0.03, 0.03, 0.05, DARK)
    P.b(0.40, 0.0, 0.31 + w, 0.03, 0.06, 0.03, DARK)
    P.b(0.06, 0.40, 0.20 + w, 0.20, 0.03, 0.04, bone)
    P.b(0.06, 0.40, 0.28 + w, 0.20, 0.03, 0.04, bone)
    P.b(0.06, 0.40, 0.36 + w, 0.16, 0.03, 0.04, bone)
    P.b(-0.22, 0.40, 0.54 + w, 0.18, 0.03, 0.06, steel)
    P.b(-0.22, 0.40, 0.60 + w, 0.04, 0.03, 0.14, (196, 120, 60))
    for (x, y, z) in ((0.40, 0.22, 0.20), (0.40, -0.22, 0.52), (0.18, 0.40, 0.62), (0.40, 0.14, 0.62), (-0.04, 0.40, 0.10)):
        P.b(x, y, z + w, 0.07, 0.07, 0.04, gold)
    P.b(0.0, -0.10, 0.70 + w, 0.03, 0.03, 0.22, steel)
    P.b(0.0, -0.10, 0.88 + w, 0.10, 0.03, 0.03, (196, 120, 60))
    P.b(-0.18, -0.18, 0.40 + w, 0.18, 0.18, 0.10, bone)
    for i in range(3):
        P.b(0.44, 0.28 - 0.14 * i, 0.0, 0.06, 0.08, 0.04 + 0.03 * math.sin(t * 3 + i), out)
    return P


def m_rust(t):
    """Monstro da Ferrugem: tatu-farejador com antenas que enferrujam metal."""
    c, cD, cL, plate = (196, 116, 64), (132, 76, 44), (232, 160, 94), (158, 90, 52)
    ant = (250, 226, 196)
    P = _P()
    m_quad(P, t, c, cD, cL, 0.56, 0.34, 0.24, 0.14, 0.09, ((-0.24, -0.15), (-0.24, 0.15), (0.24, -0.15), (0.24, 0.15)), 5.0)
    for k in range(5):
        a = -0.30 + 0.15 * k
        P.b(a, 0, 0.44, 0.17, 0.36 - 0.01 * k, 0.05, plate if k % 2 else cD)
        P.b(a, 0, 0.49, 0.06, 0.06, 0.06, (224, 142, 82))
    P.b(0.52, 0, 0.22, 0.26, 0.26, 0.24, c)
    P.b(0.68, 0, 0.22, 0.12, 0.20, 0.14, cL)
    P.b(0.75, 0.07, 0.28, 0.03, 0.03, 0.04, DARK)
    P.b(0.75, -0.07, 0.28, 0.03, 0.03, 0.04, DARK)
    P.b(0.52, 0, 0.46, 0.22, 0.24, 0.04, plate)
    m_eyes(P, 0.66, 0.12, 0.36, (255, 240, 200), DARK, 0.045)
    for s_ in (-1, 1):
        sw_ = math.sin(t * 4 + s_) * 0.05
        for k in range(7):
            P.b(0.58 + 0.07 * k, 0.10 * s_ + sw_ * k * 0.4, 0.46 + 0.05 * k - 0.004 * k * k, 0.07, 0.05, 0.05, ant if k < 5 else (252, 170, 150))
        for k in range(5):
            P.b(0.58 + 0.07 * 6 + 0.04 * math.sin(k + t * 3), 0.10 * s_ + sw_ * 2.4 + 0.04 * math.cos(k * 1.3 + t * 3), 0.74 + 0.03 * k, 0.04, 0.04, 0.04, ant)
    for k in range(3):
        P.b(-0.36 - 0.12 * k, 0, 0.28 + 0.03 * k, 0.14, 0.14, 0.10, cD)
    P.b(-0.74, 0, 0.36, 0.06, 0.30, 0.06, (120, 70, 44))
    P.b(-0.74, 0, 0.36, 0.07, 0.07, 0.20 + 0.04 * math.sin(t * 6), (90, 56, 36))
    return P

def m_harpy(t):
    skin, hair, feat, featD, gold = (238, 196, 160), (120, 70, 150), (150, 100, 70), (100, 66, 46), (252, 210, 90)
    fl = math.sin(t * 8)
    z0 = 0.32 + 0.05 * math.sin(t * 4)
    P = _P()
    for s_ in (-1, 1):
        P.b(s_ * 0.07, 0, z0 - 0.02, 0.07, 0.07, 0.20, featD)
        for k in (-1, 0, 1):
            x, y = (s_ * 0.07 + 0.03 * k, 0.07)
            P.b(x, y, z0 - 0.04, 0.025, 0.07, 0.025, gold)
    P.b(0, 0, z0 + 0.12, 0.26, 0.20, 0.22, feat)
    for k in range(4):
        P.b(-0.10 + 0.07 * k, -0.04, z0 + 0.04 - 0.01 * k, 0.07, 0.05, 0.12, featD if k % 2 else feat)
    P.b(0, 0.0, z0 + 0.22, 0.26, 0.20, 0.14, skin)
    P.b(0, 0.105, z0 + 0.24, 0.26, 0.02, 0.06, (188, 80, 120))
    P.b(0.135, 0, z0 + 0.24, 0.02, 0.20, 0.06, (188, 80, 120))
    P.b(0, 0, z0 + 0.36, 0.22, 0.20, 0.18, skin)
    P.b(0, -0.05, z0 + 0.38, 0.26, 0.14, 0.22, hair)
    P.b(0.0, 0, z0 + 0.52, 0.26, 0.24, 0.05, hair)
    for k in range(3):
        P.b(-0.12 - 0.02 * k, -0.10 - 0.02 * k, z0 + 0.50 - 0.09 * k, 0.07, 0.07, 0.10, hair)
    P.b(0.08, 0.10, z0 + 0.40, 0.05, 0.03, 0.04, (252, 190, 60))
    m_eyes(P, 0.115, 0.105, z0 + 0.43, (255, 230, 80), (120, 20, 40), 0.045)
    for s_ in (1, -1):
        m_wing(P, s_, 0, -0.02, z0 + 0.28, 7, 0.115, fl * 0.20 + 0.04, feat, featD, (222, 190, 120), 0.09, 0.035, 0.10)
    return P


def m_displacer(t):
    c, cD, cL, glow = (46, 70, 104), (26, 40, 66), (84, 120, 164), (140, 220, 255)
    P = _P()
    legs6 = ((-0.32, -0.12), (-0.32, 0.12), (0.0, -0.12), (0.0, 0.12), (0.30, -0.12), (0.30, 0.12))
    m_quad(P, t, c, cD, cL, 0.72, 0.28, 0.22, 0.17, 0.075, legs6, 7.0, foot=(200, 210, 224))
    P.b(0.58, 0, 0.26, 0.28, 0.28, 0.24, c)
    P.b(0.74, 0, 0.26, 0.14, 0.22, 0.12, cL)
    P.b(0.82, 0, 0.30, 0.03, 0.05, 0.03, DARK)
    P.b(0.58, -0.10, 0.52, 0.05, 0.05, 0.08, cD)
    P.b(0.58, 0.10, 0.52, 0.05, 0.05, 0.08, cD)
    P.b(0.74, 0.07, 0.24, 0.02, 0.02, 0.05, WHITE)
    P.b(0.74, -0.07, 0.24, 0.02, 0.02, 0.05, WHITE)
    m_eyes(P, 0.72, 0.12, 0.40, (120, 255, 190), DARK, 0.045)
    for k in range(7):
        P.b(-0.40 - 0.09 * k, 0.04 * math.sin(t * 4 + k), 0.42 + 0.03 * k * (1 + 0.6 * math.sin(t * 3)), 0.10 - 0.008 * k, 0.09 - 0.008 * k, 0.07, cD)
    for s_ in (-1, 1):
        for k in range(7):
            sd = 0.20 * s_ + 0.05 * math.sin(t * 3 + k * 0.7 + s_) * (k / 3)
            P.b(0.30 + 0.09 * k, sd, 0.44 + 0.07 * math.sin(k * 0.55 + t * 2 + s_) + 0.02 * k, 0.09, 0.06, 0.06, cL if k % 2 else c)
        P.b(0.30 + 0.09 * 6 + 0.06, 0.20 * s_, 0.44 + 0.07 * math.sin(6 * 0.55 + t * 2 + s_) + 0.14, 0.09, 0.09, 0.06, glow)
    for k in range(4):
        P.b(-0.30 + 0.30 * k, -0.34 + 0.04 * math.sin(t * 5 + k), 0.22 + 0.12 * (k % 2), 0.16, 0.08, 0.12, mix(c, 0.55, (200, 230, 255)))
    return P

# ------------------------------------------------------------------ TIER 3
def m_ogre(t):
    sk, skD, cl, bone = (208, 168, 116), (162, 124, 84), (120, 80, 50), (240, 236, 212)
    sw, arm = math.sin(t * 3), math.sin(t * 3) * 0.04
    P = _P()
    m_legs2(P, sw * 0.7, 0.14, 0.18, 0.20, 0.08, 0.14, 0.08, skD, skD, (96, 70, 50))
    P.b(0, 0, 0.30, 0.64, 0.44, 0.10, cl)
    P.b(0.0, 0.23, 0.14, 0.18, 0.02, 0.20, cl)
    P.b(0.0, 0.245, 0.14, 0.05, 0.02, 0.06, bone)
    P.b(0, 0, 0.36, 0.66, 0.46, 0.32, sk)
    P.b(0, 0.24, 0.40, 0.44, 0.02, 0.20, mix(sk, 0.15))
    P.b(0.0, 0.25, 0.46, 0.06, 0.02, 0.05, skD)
    P.b(0, 0, 0.66, 0.74, 0.44, 0.24, sk)
    for i in range(6):
        a = math.pi * (i / 5)
        P.b(math.cos(a) * 0.22, 0.24, 0.76 - math.sin(a) * 0.09, 0.05, 0.03, 0.05, bone)
    P.b(-0.46, 0.0, 0.38 + arm, 0.18, 0.24, 0.52, sk)
    P.b(0.46, 0.0, 0.38 - arm, 0.18, 0.24, 0.52, sk)
    P.b(-0.46, 0.0, 0.28 + arm, 0.22, 0.26, 0.12, skD)
    P.b(0.46, 0.0, 0.28 - arm, 0.22, 0.26, 0.12, skD)
    P.b(0, 0.02, 0.90, 0.36, 0.30, 0.22, sk)
    P.b(0.10, 0.12, 0.90, 0.20, 0.20, 0.09, skD)
    P.b(0.14, 0.24, 0.96, 0.04, 0.04, 0.08, bone)
    P.b(0.22, 0.14, 0.96, 0.04, 0.04, 0.08, bone)
    P.b(0.12, 0.22, 1.00, 0.05, 0.03, 0.05, mix(sk, 0.1))
    P.b(0, -0.02, 1.12, 0.38, 0.32, 0.05, (70, 50, 40))
    P.b(0.10, -0.10, 1.17, 0.05, 0.05, 0.07, (70, 50, 40))
    P.b(-0.10, 0.0, 1.17, 0.05, 0.05, 0.07, (70, 50, 40))
    m_eyes(P, 0.185, 0.155, 1.00, (255, 230, 70), (150, 20, 20), 0.055)
    P.b(0.50, 0.16, 0.10 - arm, 0.09, 0.09, 0.62, (120, 86, 52))
    P.b(0.50, 0.16, 0.70 - arm, 0.22, 0.22, 0.34, (110, 78, 48))
    for (x, y, z) in ((0.38, 0.16, 0.90), (0.50, 0.28, 0.86), (0.62, 0.16, 0.80), (0.50, 0.04, 1.02), (0.50, 0.28, 1.00)):
        P.b(x, y, z - arm, 0.05, 0.05, 0.06, (206, 212, 224))
    return P


def m_owlbear(t):
    fur, dk, fea, feaD, beak = (126, 88, 60), (84, 58, 40), (236, 226, 204), (196, 176, 150), (246, 176, 54)
    arm = math.sin(t * 3) * 0.04
    P = _P()
    for (lx, ly) in [(-0.34, -0.34), (0.16, -0.34), (-0.34, 0.12), (0.16, 0.12)]:
        P.b(lx + 0.10, ly + 0.10, 0, 0.24, 0.24, 0.10, dk)
        P.b(lx + 0.10, ly + 0.10, 0.10, 0.20, 0.20, 0.16, fur)
    P.b(0, 0, 0.26, 0.84, 0.76, 0.46, fur)
    P.b(0, 0, 0.72, 0.64, 0.58, 0.12, dk)
    P.b(0.0, 0.40, 0.30, 0.80, 0.03, 0.30, mix(fur, 0.15))
    for i in range(4):
        P.b(-0.30 + i * 0.20, 0.42, 0.34 + 0.04 * (i % 2), 0.10, 0.03, 0.10, feaD)
    for s_ in (-1, 1):
        P.b(s_ * 0.46, 0.20, 0.44 + s_ * arm, 0.16, 0.30, 0.18, fur)
        for k in (-1, 0, 1):
            P.b(s_ * 0.46 + 0.05 * k, 0.40, 0.42 + s_ * arm, 0.035, 0.08, 0.05, (240, 236, 214))
    P.b(0, 0.12, 0.66, 0.50, 0.40, 0.36, fea)
    P.b(0, 0.12, 0.92, 0.50, 0.40, 0.10, fur)
    for k in range(4):
        P.b(-0.20 + 0.13 * k, 0.12, 1.00, 0.08, 0.08, 0.10 + 0.03 * (k % 2), fur if k % 2 else dk)
    P.b(-0.22, 0.14, 1.04, 0.07, 0.07, 0.13, dk)
    P.b(0.22, 0.14, 1.04, 0.07, 0.07, 0.13, dk)
    P.b(0.08, 0.48, 0.64, 0.14, 0.14, 0.15, beak)
    P.b(0.10, 0.60, 0.62, 0.08, 0.06, 0.09, (200, 120, 40))
    P.b(0.0, 0.45, 0.70, 0.40, 0.02, 0.18, feaD)
    P.b(0.45, 0.0, 0.70, 0.02, 0.40, 0.18, feaD)
    P.b(0.12, 0.45, 0.80, 0.12, 0.02, 0.12, (255, 224, 40))
    P.b(-0.10, 0.45, 0.80, 0.12, 0.02, 0.12, (255, 224, 40))
    P.b(0.45, 0.14, 0.80, 0.02, 0.12, 0.12, (255, 224, 40))
    P.b(0.14, 0.45, 0.83, 0.05, 0.02, 0.07, DARK)
    P.b(-0.08, 0.45, 0.83, 0.05, 0.02, 0.07, DARK)
    P.b(0.45, 0.16, 0.83, 0.02, 0.05, 0.07, DARK)
    P.b(-0.30, -0.30, 0.42, 0.14, 0.14, 0.14, dk)
    return P


def m_troll(t):
    sk, skD, hair, claw = (104, 152, 100), (70, 106, 70), (60, 98, 56), (230, 226, 200)
    sw, arm = math.sin(t * 3), math.sin(t * 3) * 0.05
    P = _P()
    m_legs2(P, sw * 0.6, 0.12, 0.17, 0.19, 0.07, 0.15, 0.10, skD, skD, (90, 70, 54))
    P.b(0.04, 0.04, 0.32, 0.52, 0.36, 0.08, (112, 80, 50))
    P.b(0.04, 0.04, 0.38, 0.54, 0.38, 0.34, sk)
    P.b(0.04, 0.24, 0.44, 0.38, 0.02, 0.20, mix(sk, 0.18))
    P.b(0.04, 0.245, 0.52, 0.05, 0.02, 0.05, skD)
    for i in range(5):
        P.b(-0.10 - 0.04 * i, -0.10 - 0.03 * i, 0.58 + 0.03 * i, 0.12, 0.12, 0.10, hair if i % 2 else mix(hair, 0.15))
    P.b(0.04, 0.04, 0.70, 0.46, 0.32, 0.14, sk)
    for s_ in (-1, 1):
        P.b(s_ * 0.40 + 0.04, 0.12, 0.20 - s_ * arm, 0.14, 0.18, 0.54, sk)
        P.b(s_ * 0.40 + 0.04, 0.14, 0.04 - s_ * arm, 0.18, 0.22, 0.14, skD)
        for k in (-1, 0, 1):
            P.b(s_ * 0.40 + 0.04 + 0.05 * k, 0.26, 0.04 - s_ * arm, 0.03, 0.07, 0.05, claw)
    P.b(0.06, 0.12, 0.80, 0.32, 0.30, 0.24, sk)
    P.b(0.06, 0.12, 1.02, 0.32, 0.30, 0.05, hair)
    P.b(0.10, 0.34, 0.86, 0.10, 0.10, 0.14, mix(sk, 0.22))
    P.b(0.10, 0.34, 0.80, 0.10, 0.04, 0.05, skD)
    P.b(0.06, 0.30, 0.76, 0.18, 0.03, 0.04, (30, 16, 20))
    for k in (-1, 1):
        P.b(0.06 + 0.07 * k, 0.32, 0.77, 0.03, 0.02, 0.05, WHITE)
    for s_ in (-1, 1):
        P.b(0.06 + s_ * 0.19, 0.14, 0.92, 0.07, 0.04, 0.07, sk)
    P.b(0.24, 0.10, 0.96, 0.03, 0.03, 0.03, skD)
    P.b(0.16, 0.30, 0.96, 0.03, 0.03, 0.03, skD)
    m_eyes(P, 0.20, 0.28, 0.90, (255, 70, 40), DARK, 0.05)
    for i in range(3):
        u = (t * 0.6 + i * 0.33) % 1.0
        P.b(0.24 + 0.1 * math.sin(i * 2.1), 0.2 + 0.1 * math.cos(i * 1.7), 0.50 + u * 0.4, 0.03, 0.03, 0.03, (150, 255, 150))
    return P


def m_golem(t):
    rock, rockD, rockL, moss = (146, 146, 158), (104, 104, 120), (178, 178, 190), (84, 146, 80)
    rune = (90, 232, 255)
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    core = mix((70, 200, 255), pulse * 0.6)
    arm = math.sin(t * 2.5) * 0.04
    P = _P()
    for s_ in (-1, 1):
        P.b(s_ * 0.20, 0, 0, 0.28, 0.36, 0.16, rockD)
        P.b(s_ * 0.20, 0, 0.16, 0.22, 0.28, 0.24, rock)
    P.b(0, 0, 0.38, 0.68, 0.42, 0.10, rockD)
    P.b(0, 0, 0.48, 0.92, 0.56, 0.52, rock)
    P.b(0, 0, 0.98, 0.84, 0.50, 0.08, rockL)
    P.b(0.0, 0.29, 0.58, 0.30, 0.02, 0.28, (30, 60, 80))
    P.b(0.0, 0.30, 0.64, 0.18, 0.02, 0.16, core)
    P.b(0.47, 0.0, 0.58, 0.02, 0.28, 0.28, (30, 60, 80))
    P.b(0.48, 0.0, 0.64, 0.02, 0.16, 0.16, core)
    for (x, y, z, w, d, h) in ((-0.30, 0.29, 0.80, 0.16, 0.02, 0.03), (0.30, 0.29, 0.54, 0.03, 0.02, 0.16), (0.47, -0.18, 0.86, 0.02, 0.14, 0.03), (0.47, 0.18, 0.52, 0.02, 0.03, 0.16)):
        P.b(x, y, z, w, d, h, mix(rune, 0.0))
    P.b(-0.30, 0.29, 0.60, 0.02, 0.02, 0.18, (40, 40, 50))
    P.b(0.20, 0.29, 0.90, 0.14, 0.02, 0.02, (50, 50, 60))
    for s_ in (-1, 1):
        P.b(s_ * 0.60, 0, 0.84, 0.24, 0.42, 0.20, rockD)
        P.b(s_ * 0.60, 0, 0.34 - s_ * arm, 0.22, 0.30, 0.52, rock)
        P.b(s_ * 0.62, 0, 0.18 - s_ * arm, 0.30, 0.38, 0.18, rockD)
        P.b(s_ * 0.62, 0.16, 0.16 - s_ * arm, 0.08, 0.06, 0.08, rockL)
    P.b(-0.30, -0.02, 1.02, 0.34, 0.26, 0.05, moss)
    P.b(0.26, 0.10, 1.02, 0.18, 0.16, 0.04, moss)
    P.b(0, 0.02, 1.06, 0.40, 0.34, 0.26, rock)
    P.b(0, 0.02, 1.30, 0.34, 0.28, 0.04, rockL)
    P.b(0.0, 0.20, 1.12, 0.30, 0.02, 0.06, DARK)
    P.b(0.21, 0.02, 1.12, 0.02, 0.26, 0.06, DARK)
    m_eyes(P, 0.20, 0.17, 1.14, (255, 224, 70), (255, 120, 40), 0.055)
    return P


def m_gargoyle(t):
    st, stD, stL, red = (122, 126, 140), (84, 88, 104), (160, 164, 178), (255, 70, 60)
    fl = math.sin(t * 5)
    z0 = 0.05 + 0.04 * math.sin(t * 5) * 0.5
    P = _P()
    for s_ in (-1, 1):
        P.b(s_ * 0.12, 0.02, z0, 0.14, 0.20, 0.10, stD)
        P.b(s_ * 0.12, 0.0, z0 + 0.10, 0.13, 0.14, 0.14, st)
        for k in (-1, 0, 1):
            P.b(s_ * 0.12 + 0.04 * k, 0.12, z0, 0.03, 0.06, 0.04, stL)
    P.b(0, 0, z0 + 0.24, 0.34, 0.26, 0.18, st)
    P.b(0.04, 0.04, z0 + 0.40, 0.36, 0.28, 0.20, stL)
    P.b(0.0, 0.15, z0 + 0.28, 0.20, 0.02, 0.14, stD)
    for s_ in (-1, 1):
        P.b(s_ * 0.24, 0.12, z0 + 0.18, 0.09, 0.22, 0.09, st)
        P.b(s_ * 0.24, 0.26, z0 + 0.16, 0.10, 0.07, 0.07, stD)
        for k in (-1, 0, 1):
            P.b(s_ * 0.24 + 0.03 * k, 0.31, z0 + 0.14, 0.02, 0.05, 0.03, stL)
    P.b(0.08, 0.10, z0 + 0.60, 0.26, 0.24, 0.20, st)
    P.b(0.16, 0.20, z0 + 0.60, 0.16, 0.14, 0.09, stD)
    for s_ in (-1, 1):
        P.b(0.08 + s_ * 0.10, 0.08, z0 + 0.80, 0.05, 0.05, 0.14, stL)
    P.b(0.26, 0.28, z0 + 0.60, 0.03, 0.03, 0.06, WHITE)
    P.b(0.16, 0.30, z0 + 0.60, 0.03, 0.03, 0.06, WHITE)
    m_eyes(P, 0.21, 0.19, z0 + 0.72, red, (255, 220, 120), 0.05)
    for k in range(5):
        a = -0.2 - 0.09 * k
        x, y = dp(a, 0.05 * math.sin(t * 3 + k))
        P.b(x, y, z0 + 0.12 + 0.02 * k, 0.09 - 0.012 * k, 0.09 - 0.012 * k, 0.07, stD)
    for s_ in (1, -1):
        m_wing(P, s_, 0, -0.04, z0 + 0.50, 5, 0.11, fl * 0.12 + 0.34, stD, st, stL, 0.08, 0.04, 0.0)
    return P


def m_basilisk(t):
    c, cD, cL, crest, gl = (112, 126, 60), (72, 86, 40), (160, 174, 98), (200, 70, 60), (190, 255, 90)
    P = _P()
    legs8 = ((-0.34, -0.17), (-0.34, 0.17), (-0.12, -0.17), (-0.12, 0.17), (0.10, -0.17), (0.10, 0.17), (0.32, -0.17), (0.32, 0.17))
    m_quad(P, t, c, cD, cL, 0.76, 0.30, 0.20, 0.13, 0.07, legs8, 7.0)
    for k in range(6):
        P.b(-0.34 + 0.17 * k, 0, 0.40, 0.09, 0.06, 0.08 + 0.03 * (k % 2), crest)
    P.b(0.56, 0, 0.26, 0.28, 0.28, 0.22, c)
    P.b(0.72, 0, 0.26, 0.14, 0.22, 0.12, cL)
    P.b(0.80, 0.06, 0.32, 0.03, 0.03, 0.04, DARK)
    P.b(0.80, -0.06, 0.32, 0.03, 0.03, 0.04, DARK)
    P.b(0.74, 0, 0.26, 0.13, 0.20, 0.03, (170, 60, 60))
    P.b(0.56, 0, 0.48, 0.20, 0.30, 0.05, crest)
    for s_ in (-1, 1):
        P.b(0.54, 0.16 * s_, 0.50, 0.05, 0.05, 0.10, crest)
    glow = 0.5 + 0.5 * math.sin(t * 5)
    m_eyes(P, 0.70, 0.145, 0.40, mix(gl, glow * 0.3), (60, 80, 20), 0.065)
    for k in range(8):
        P.b(-0.44 - 0.10 * k, 0.07 * math.sin(t * 3 + k * 0.7), 0.20 - 0.012 * k, 0.20 - 0.022 * k, 0.22 - 0.025 * k, 0.12, cD if k % 2 else c)
    for k in range(3):
        P.b(0.88 + 0.05 * k, 0.12 * (k - 1), 0.04, 0.08, 0.08, 0.05 + 0.03 * k, (164, 164, 172))
    return P

def m_hellhound(t):
    c, cD, cL, ember = (54, 34, 38), (30, 20, 24), (96, 54, 54), (255, 110, 40)
    P = _P()
    m_quad(P, t, c, cD, cL, 0.66, 0.30, 0.24, 0.22, 0.09, None, 8.0, foot=(72, 40, 40))
    for k in range(5):
        P.b(-0.26 + 0.14 * k, 0.16, 0.34 + 0.10 * (k % 2), 0.05, 0.03, 0.05, ember)
    P.b(0.52, 0, 0.42, 0.30, 0.30, 0.26, c)
    P.b(0.68, 0, 0.42, 0.14, 0.22, 0.13, cL)
    P.b(0.76, 0.07, 0.50, 0.03, 0.03, 0.04, DARK)
    P.b(0.76, -0.07, 0.50, 0.03, 0.03, 0.04, DARK)
    P.b(0.69, 0.0, 0.42, 0.12, 0.20, 0.025, (255, 60, 40))
    for k in (-1, 1):
        P.b(0.70, 0.08 * k, 0.43, 0.025, 0.02, 0.05, WHITE)
        P.b(0.46, 0.12 * k, 0.68, 0.06, 0.06, 0.13, cD)
    P.b(0.40, 0, 0.60, 0.10, 0.34, 0.05, (160, 160, 168))
    for k in (-1, 1):
        P.b(0.40, 0.17 * k, 0.64, 0.04, 0.04, 0.07, (210, 210, 220))
    m_eyes(P, 0.66, 0.15, 0.56, (255, 200, 60), (255, 60, 30), 0.055)
    m_flame(P, 0.50, 0, 0.68, t, 0.13, 3, 0.0)
    m_flame(P, 0.26, 0, 0.62, t, 0.15, 3, 1.3)
    m_flame(P, 0.02, 0, 0.60, t, 0.15, 3, 2.1)
    for k in range(5):
        m_flame(P, -0.40 - 0.07 * k, 0, 0.40 + 0.05 * k, t, 0.09, 2, 3.0 + k)
    return P


# ------------------------------------------------------------------ CHEFES
def m_wingy(P, side, rx, rz, n, step, flap, c, cD, bone, span=0.16, thick=0.035, sweep=0.12, droop=0.0):
    """Asa de dragão/demônio que sai pelos lados (eixo y) e é varrida para trás."""
    for i in range(n):
        r = 0.22 + step * i
        u = i / max(1, n - 1)
        lift = flap * u - droop * u * u
        x = rx - sweep * i
        w = span * (1.25 - 0.55 * i / n)
        for rw in ((-1.0, 0.0, 1.0) if i < n - 2 else (0.0,)):
            P.b(x + rw * w * 0.9, side * r, rz + lift, w * 1.2, step * 1.3, thick, c if rw else cD)
        P.b(x, side * r, rz + lift + thick * 0.9, 0.045, step * 1.15, 0.03, bone)
    for f in (0.35, 0.62, 0.9):
        for i in range(int(n * f), n):
            u = i / max(1, n - 1)
            P.b(rx - sweep * i - 0.10 * (i - n * f), side * (0.22 + step * i), rz + flap * u - droop * u * u + 0.03, 0.04, 0.05, 0.025, bone)


def m_dragon(t):
    r, rD, rL = (204, 52, 56), (138, 34, 44), (236, 104, 90)
    belly, horn, yel, gold = (246, 208, 122), (246, 232, 180), (255, 234, 70), (252, 210, 72)
    fl = math.sin(t * 3.2)
    jaw = 0.5 + 0.5 * math.sin(t * 2.2)
    P = _P()
    for (lx, ly) in [(-0.46, -0.30), (-0.46, 0.30), (0.32, -0.28), (0.32, 0.28)]:
        P.b(lx, ly, 0, 0.28, 0.22, 0.08, rD)
        P.b(lx, ly, 0.08, 0.20, 0.18, 0.20, r)
        P.b(lx, ly, 0.28, 0.26, 0.22, 0.16, rD)
        for k in (-1, 0, 1):
            P.b(lx + 0.15, ly + 0.07 * k, 0.0, 0.07, 0.04, 0.06, horn)
    P.b(-0.05, 0, 0.32, 1.20, 0.66, 0.44, r)
    P.b(-0.05, 0, 0.64, 1.04, 0.54, 0.10, rL)
    P.b(-0.05, 0.345, 0.34, 1.06, 0.02, 0.34, belly)
    for i in range(7):
        P.b(-0.50 + 0.17 * i, 0.355, 0.34, 0.02, 0.01, 0.34, (214, 160, 84))
    P.b(0.57, 0, 0.36, 0.02, 0.44, 0.30, belly)
    for i in range(8):
        P.b(-0.56 + 0.16 * i, 0, 0.74, 0.07, 0.07, 0.12 + 0.04 * (i % 2), horn)
    for i in range(5):
        u = i / 4
        P.b(0.56 + 0.12 * i, 0.03 * math.sin(t * 2 + i), 0.52 + 0.17 * i, 0.36 - 0.03 * i, 0.34 - 0.03 * i, 0.22, r if i % 2 else rL)
        P.b(0.56 + 0.12 * i + 0.12, 0, 0.52 + 0.17 * i, 0.02, 0.24, 0.20, belly)
    hz = 1.32
    P.b(1.12, 0, hz, 0.38, 0.34, 0.26, rL)
    P.b(1.30, 0, hz + 0.03, 0.24, 0.26, 0.12, rL)
    P.b(1.30, 0, hz - 0.10 * jaw - 0.02, 0.22, 0.24, 0.06, rD)
    P.b(1.44, 0.09, hz + 0.11, 0.03, 0.04, 0.03, DARK)
    P.b(1.44, -0.09, hz + 0.11, 0.03, 0.04, 0.03, DARK)
    for k in range(4):
        P.b(1.24 + 0.06 * k, 0.12, hz + 0.0, 0.03, 0.025, 0.05, WHITE)
        P.b(1.24 + 0.06 * k, 0.12, hz - 0.06 * jaw, 0.03, 0.025, 0.05, WHITE)
    P.b(1.12, 0, hz + 0.24, 0.24, 0.36, 0.04, rD)
    for s_ in (-1, 1):
        P.b(1.02, s_ * 0.13, hz + 0.24, 0.06, 0.06, 0.18, horn)
        P.b(0.94, s_ * 0.13, hz + 0.40, 0.05, 0.05, 0.12, horn)
        P.b(1.14, s_ * 0.19, hz + 0.10, 0.10, 0.04, 0.16, rD)
    m_eyes(P, 1.28, 0.175, hz + 0.16, yel, DARK, 0.065)
    if jaw > 0.55:
        for i in range(5):
            f = 0.5 + 0.5 * math.sin(t * 10 + i * 1.5)
            P.b(1.52 + 0.17 * i, 0.02 * math.sin(t * 8 + i), hz + 0.0 - 0.01 * i, 0.12 + 0.05 * i, 0.10 + 0.05 * i, 0.07 + 0.03 * i,
                ((255, 235, 120), (255, 180, 50), (255, 100, 30), (230, 60, 30), (200, 50, 40))[i] if f > 0.3 else (255, 120, 40))
    for i in range(9):
        u = i / 8
        P.b(-0.68 - 0.15 * i, 0.12 * math.sin(t * 2 + i * 0.6) * u, 0.44 - 0.03 * i, 0.42 - 0.04 * i, 0.34 - 0.03 * i, 0.30 - 0.025 * i, r if i % 2 else rD)
        if i % 2 == 0:
            P.b(-0.68 - 0.15 * i, 0.12 * math.sin(t * 2 + i * 0.6) * u, 0.74 - 0.05 * i, 0.05, 0.05, 0.08, horn)
    P.b(-2.14, 0.12 * math.sin(t * 2 + 9 * 0.6), 0.40, 0.14, 0.26, 0.10, horn)
    for s_ in (-1, 1):
        m_wingy(P, s_, 0.20, 0.80, 7, 0.15, fl * 0.34 + 0.20, (160, 40, 66), (190, 52, 76), horn, 0.20, 0.04, 0.14, 0.10)
    for (x, y) in ((0.7, 0.55), (0.9, 0.40), (0.55, 0.62), (0.2, 0.62), (1.0, 0.55)):
        P.b(x, y, 0.0, 0.08, 0.08, 0.03, gold)
    return P


def m_goblin_chief(t):
    sk, skD, armor, armorL = (96, 170, 92), (66, 126, 66), (126, 94, 66), (176, 140, 96)
    metal, metalL, red, gold, leath = (150, 156, 170), (210, 216, 228), (176, 40, 44), (240, 200, 80), (110, 76, 46)
    sw, arm = math.sin(t * 4), math.sin(t * 3) * 0.04
    P = _P()
    m_legs2(P, sw, 0.13, 0.15, 0.17, 0.07, 0.14, 0.10, (74, 54, 42), armor, (52, 40, 30))
    P.b(0, 0, 0.30, 0.60, 0.42, 0.10, armor)
    P.b(0, 0.225, 0.18, 0.40, 0.02, 0.14, armorL)
    P.b(0.315, 0, 0.18, 0.02, 0.30, 0.14, armorL)
    P.b(0, 0, 0.40, 0.64, 0.44, 0.30, armor)
    P.b(0, 0.23, 0.42, 0.44, 0.02, 0.24, metal)
    P.b(0.325, 0, 0.42, 0.02, 0.28, 0.24, metal)
    for i in range(3):
        P.b(0, 0.24, 0.46 + 0.07 * i, 0.36, 0.01, 0.025, metalL)
    P.b(0.06, 0.245, 0.50, 0.10, 0.01, 0.22, red)
    P.b(0, 0.24, 0.36, 0.60, 0.01, 0.04, gold)
    for s_ in (-1, 1):
        P.b(s_ * 0.42, 0, 0.66, 0.22, 0.34, 0.10, metal)
        P.b(s_ * 0.42, 0, 0.76, 0.06, 0.06, 0.15, metalL)
        P.b(s_ * 0.42, -0.01, 0.36 - s_ * arm, 0.13, 0.17, 0.30, sk)
        P.b(s_ * 0.42, 0, 0.30 - s_ * arm, 0.15, 0.19, 0.08, metal)
    P.b(-0.46, 0.20, 0.30 + arm, 0.30, 0.05, 0.42, metal)
    P.b(-0.46, 0.235, 0.34 + arm, 0.20, 0.02, 0.34, armorL)
    P.b(-0.46, 0.255, 0.46 + arm, 0.10, 0.02, 0.10, gold)
    P.b(0.52, 0.14, 0.10 - arm, 0.05, 0.05, 0.64, leath)
    P.b(0.52, 0.14, 0.74 - arm, 0.20, 0.20, 0.20, metal)
    for (dx, dy, dz) in ((0.14, 0, 0.10), (-0.14, 0, 0.10), (0, 0.14, 0.10), (0, -0.14, 0.10), (0, 0, 0.22)):
        P.b(0.52 + dx, 0.14 + dy, 0.74 + dz - arm, 0.05, 0.05, 0.06, metalL)
    P.b(0, 0, 0.70, 0.42, 0.36, 0.24, sk)
    P.b(0.12, 0.12, 0.70, 0.20, 0.20, 0.09, skD)
    P.b(0.30, 0.04, 0.80, 0.16, 0.05, 0.07, sk)
    P.b(0.04, 0.30, 0.80, 0.05, 0.16, 0.07, sk)
    P.b(0.14, 0.22, 0.73, 0.04, 0.03, 0.06, WHITE)
    P.b(0.22, 0.14, 0.73, 0.03, 0.04, 0.06, WHITE)
    P.b(0, 0, 0.90, 0.46, 0.40, 0.08, metal)
    P.b(0, 0, 0.98, 0.10, 0.36, 0.12, red)
    P.b(-0.03, 0, 1.10, 0.08, 0.30, 0.06, red)
    m_eyes(P, 0.215, 0.185, 0.80, gold, (180, 30, 30), 0.06)
    return P


def m_werewolf(t):
    fur, furD, furL, claw = (126, 114, 110), (84, 74, 72), (182, 160, 146), (232, 222, 198)
    pants = (92, 78, 62)
    sw, arm = math.sin(t * 5), math.sin(t * 4) * 0.05
    how = 0.5 + 0.5 * math.sin(t * 1.6)
    P = _P()
    for s_, off in ((-1, sw), (1, -sw)):
        l = max(0, off) * 0.06
        P.b(s_ * 0.14, 0.03, l, 0.18, 0.28, 0.07, furD)
        P.b(s_ * 0.14, 0, 0.07 + l, 0.15, 0.15, 0.15, fur)
        P.b(s_ * 0.14, 0, 0.22 + l, 0.20, 0.20, 0.14, pants)
        for k in (-1, 0, 1):
            P.b(s_ * 0.14 + 0.05 * k, 0.18, l, 0.025, 0.07, 0.03, claw)
    P.b(0.04, 0.04, 0.36, 0.52, 0.40, 0.18, pants)
    P.b(0.06, 0.06, 0.52, 0.62, 0.46, 0.26, fur)
    P.b(0.10, 0.10, 0.76, 0.66, 0.46, 0.14, furL)
    P.b(0.20, 0.24, 0.56, 0.20, 0.03, 0.26, furL)
    for i in range(6):
        P.b(-0.20 - 0.02 * i, -0.20 - 0.02 * i, 0.60 + 0.07 * i, 0.12, 0.12, 0.09, furD)
    for s_ in (-1, 1):
        P.b(s_ * 0.44 + 0.05, 0.12, 0.40 + s_ * arm, 0.14, 0.16, 0.40, fur)
        P.b(s_ * 0.44 + 0.05, 0.16, 0.30 + s_ * arm, 0.16, 0.20, 0.10, furD)
        for k in (-1, 0, 1):
            P.b(s_ * 0.44 + 0.05 + 0.05 * k, 0.28, 0.28 + s_ * arm, 0.03, 0.09, 0.04, claw)
        P.b(s_ * 0.44 + 0.05, 0.10, 0.80, 0.18, 0.28, 0.08, furD)
    for i in range(6):
        P.b(-0.34 - 0.10 * i, -0.34 - 0.10 * i, 0.46 + 0.05 * i + math.sin(t * 3 + i) * 0.04, 0.14 - 0.012 * i, 0.14 - 0.012 * i, 0.12, furD if i % 2 else fur)
    hz = 0.92 + 0.04 * how
    P.b(0.18, 0.18, hz, 0.32, 0.30, 0.24, furL)
    P.b(0.34, 0.34, hz - 0.01, 0.20, 0.20, 0.12, furL)
    P.b(0.34, 0.34, hz - 0.10 * (0.4 + how * 0.6), 0.18, 0.18, 0.05, (96, 30, 36))
    P.b(0.44, 0.44, hz + 0.08, 0.05, 0.05, 0.05, DARK)
    for k in range(3):
        P.b(0.30 + 0.05 * k, 0.45, hz + 0.0, 0.025, 0.02, 0.06, WHITE)
        P.b(0.45, 0.30 + 0.05 * k, hz + 0.0, 0.02, 0.025, 0.06, WHITE)
    for s_ in (-1, 1):
        P.b(0.18 + s_ * 0.13, 0.12, hz + 0.24, 0.06, 0.06, 0.14, furD)
    P.b(0.18, 0.18, hz + 0.22, 0.28, 0.26, 0.06, furD)
    m_eyes(P, 0.34, 0.33, hz + 0.14, (255, 150, 90), (120, 20, 20), 0.06)
    return P


def m_bat_queen(t):
    wing, wingD, skin, cape, gold = (176, 146, 255), (96, 66, 176), (226, 206, 236), (96, 52, 140), (252, 210, 90)
    fl = math.sin(t * 5)
    z0 = 0.30 + 0.07 * math.sin(t * 2.5)
    P = _P()
    for i in range(6):
        P.b(0, 0, z0 - 0.04 - 0.05 * i + 0.0, 0.26 - 0.03 * i, 0.22 - 0.025 * i, 0.07, cape if i % 2 else (70, 36, 108))
    P.b(0, 0, z0 + 0.20, 0.34, 0.26, 0.30, cape)
    P.b(0, 0.14, z0 + 0.24, 0.20, 0.02, 0.22, (50, 24, 80))
    P.b(0.18, 0, z0 + 0.24, 0.02, 0.16, 0.22, (50, 24, 80))
    P.b(0.02, 0.15, z0 + 0.36, 0.06, 0.02, 0.06, gold)
    P.b(0, 0, z0 + 0.50, 0.30, 0.24, 0.08, (60, 30, 90))
    for s_ in (-1, 1):
        P.b(s_ * 0.24, 0.04, z0 + 0.22 + 0.03 * math.sin(t * 3 + s_), 0.09, 0.12, 0.26, skin)
        for k in (-1, 0, 1):
            P.b(s_ * 0.24 + 0.03 * k, 0.12, z0 + 0.18, 0.02, 0.06, 0.04, (60, 30, 90))
    P.b(0, 0, z0 + 0.58, 0.28, 0.24, 0.22, skin)
    P.b(0, 0, z0 + 0.74, 0.30, 0.26, 0.08, (60, 40, 110))
    P.b(0.10, 0.10, z0 + 0.60, 0.12, 0.12, 0.07, mix(skin, 0, ))
    for s_ in (-1, 1):
        P.b(s_ * 0.11, -0.02, z0 + 0.80, 0.07, 0.06, 0.20, (60, 40, 110))
        P.b(s_ * 0.11, -0.02, z0 + 0.84, 0.04, 0.04, 0.12, (230, 170, 220))
    P.b(0, 0, z0 + 0.82, 0.26, 0.22, 0.04, gold)
    for k in range(4):
        P.b(-0.10 + 0.067 * k, 0, z0 + 0.86, 0.04, 0.04, 0.08 + 0.03 * (k % 2), gold)
    P.b(0.05, 0.13, z0 + 0.60, 0.02, 0.01, 0.06, WHITE)
    P.b(0.12, 0.07, z0 + 0.60, 0.01, 0.02, 0.06, WHITE)
    m_eyes(P, 0.14, 0.125, z0 + 0.68, (255, 120, 150), DARK, 0.05)
    for s_ in (1, -1):
        m_wing(P, s_, 0, -0.02, z0 + 0.34, 9, 0.14, fl * 0.26 + 0.10, wing, wingD, (60, 30, 110), 0.11, 0.04, 0.16)
    m_ring(P, 0, 0, z0 + 0.50, 0.70, 0.70, 4, 0.08, (255, 160, 220), t, 1.6, 0.07)
    return P


def m_orc_chief(t):
    skin, skinD, plate, plateL = (116, 176, 98), (80, 132, 66), (86, 90, 104), (150, 156, 172)
    leath, bone, red, gold = (104, 72, 44), (242, 240, 226), (176, 40, 40), (240, 200, 80)
    sw, arm = math.sin(t * 3.5), math.sin(t * 3) * 0.04
    P = _P()
    m_legs2(P, sw, 0.14, 0.17, 0.19, 0.08, 0.14, 0.10, plate, plateL, (50, 44, 40))
    P.b(0, 0, 0.32, 0.66, 0.46, 0.10, leath)
    for i in range(4):
        P.b(-0.24 + 0.16 * i, 0.245, 0.30, 0.07, 0.04, 0.09, bone)
    P.b(0.345, 0.0, 0.30, 0.05, 0.07, 0.09, bone)
    P.b(0, 0, 0.42, 0.72, 0.50, 0.34, plate)
    P.b(0, 0.26, 0.46, 0.50, 0.02, 0.26, plateL)
    P.b(0.37, 0, 0.46, 0.02, 0.30, 0.26, plateL)
    P.b(0.0, 0.27, 0.58, 0.14, 0.02, 0.14, red)
    for i in range(3):
        P.b(0, 0.28, 0.46 + 0.08 * i, 0.46, 0.01, 0.02, plate)
    for s_ in (-1, 1):
        P.b(s_ * 0.48, 0, 0.74, 0.26, 0.38, 0.12, plateL)
        for k in range(3):
            P.b(s_ * 0.48, -0.10 + 0.10 * k, 0.86, 0.06, 0.06, 0.12, bone)
        P.b(s_ * 0.50, 0, 0.40 - s_ * arm, 0.16, 0.20, 0.36, skin)
        P.b(s_ * 0.50, 0, 0.32 - s_ * arm, 0.20, 0.24, 0.10, plate)
    P.b(0, 0, 0.78, 0.40, 0.34, 0.22, skin)
    P.b(0.12, 0.12, 0.78, 0.22, 0.22, 0.09, skinD)
    P.b(0.20, 0.26, 0.82, 0.04, 0.04, 0.12, bone)
    P.b(0.26, 0.20, 0.82, 0.04, 0.04, 0.12, bone)
    P.b(0.0, 0.18, 0.88, 0.26, 0.01, 0.03, red)
    P.b(0, 0, 0.98, 0.44, 0.38, 0.08, plate)
    P.b(0, 0, 1.06, 0.20, 0.20, 0.06, plateL)
    for s_ in (-1, 1):
        P.b(s_ * 0.26, 0, 0.98, 0.06, 0.06, 0.14, bone)
        P.b(s_ * 0.31, 0, 1.12, 0.05, 0.05, 0.10, bone)
    P.b(-0.30, -0.30, 0.50, 0.04, 0.04, 0.80, leath)
    P.b(-0.30, -0.30, 1.28, 0.16, 0.12, 0.14, bone)
    P.b(-0.30, -0.30, 1.40, 0.06, 0.06, 0.08, red)
    P.b(0.58, 0.22, 0.10 - arm, 0.06, 0.06, 1.00, leath)
    P.b(0.58, 0.22, 0.90 - arm, 0.08, 0.40, 0.30, (186, 192, 208))
    P.b(0.58, 0.46, 0.94 - arm, 0.08, 0.10, 0.22, (230, 236, 246))
    P.b(0.58, -0.02, 1.00 - arm, 0.10, 0.10, 0.10, plate)
    m_eyes(P, 0.215, 0.185, 0.88, (255, 232, 60), (200, 30, 30), 0.065)
    return P


def m_goblin_king(t):
    sk, skD, gold, red, fur = (118, 204, 106), (84, 150, 72), (246, 206, 72), (160, 30, 44), (236, 232, 222)
    leath = (116, 80, 48)
    sw, arm = math.sin(t * 3.5), math.sin(t * 3) * 0.04
    P = _P()
    m_legs2(P, sw * 0.7, 0.13, 0.15, 0.17, 0.07, 0.12, 0.08, skD, (96, 70, 48), (60, 44, 34))
    P.b(0, 0, 0.26, 0.62, 0.46, 0.34, sk)
    P.b(0, 0.245, 0.30, 0.42, 0.02, 0.26, mix(sk, 0.2))
    P.b(0, 0, 0.58, 0.66, 0.48, 0.14, red)
    P.b(0, 0.255, 0.60, 0.66, 0.02, 0.04, gold)
    for i in range(5):
        a = math.pi * (0.15 + 0.7 * i / 4)
        P.b(0.33 * math.cos(a) * 0.9, 0.255, 0.58 - 0.09 * math.sin(a) + 0.04, 0.05, 0.03, 0.05, gold)
    P.b(-0.10, 0.28, 0.46, 0.10, 0.02, 0.10, gold)
    P.b(0, 0, 0.72, 0.84, 0.50, 0.12, fur)
    for i in range(7):
        P.b(-0.34 + 0.115 * i, 0.26, 0.72, 0.06, 0.03, 0.06, (60, 30, 36))
    for s_ in (-1, 1):
        P.b(s_ * 0.44, 0, 0.30 - s_ * arm, 0.14, 0.18, 0.46, sk)
        P.b(s_ * 0.44, 0, 0.30 - s_ * arm, 0.17, 0.21, 0.06, gold)
        P.b(s_ * 0.44, 0, 0.22 - s_ * arm, 0.16, 0.20, 0.08, skD)
    P.b(0.50, 0.14, 0.08 - arm, 0.06, 0.06, 0.86, gold)
    P.b(0.50, 0.14, 0.92 - arm, 0.20, 0.20, 0.20, (180, 40, 60))
    for (dx, dy, dz) in ((0.12, 0, 0.08), (-0.12, 0, 0.08), (0, 0.12, 0.08), (0, -0.12, 0.08), (0, 0, 0.20)):
        P.b(0.50 + dx, 0.14 + dy, 0.92 + dz - arm, 0.06, 0.06, 0.06, gold)
    P.b(0, 0, 0.84, 0.46, 0.38, 0.28, sk)
    P.b(0.13, 0.13, 0.84, 0.22, 0.22, 0.10, skD)
    P.b(0.32, 0.04, 0.96, 0.18, 0.05, 0.07, sk)
    P.b(0.04, 0.32, 0.96, 0.05, 0.18, 0.07, sk)
    P.b(0.16, 0.24, 0.87, 0.04, 0.03, 0.07, WHITE)
    P.b(0.24, 0.16, 0.87, 0.03, 0.04, 0.07, WHITE)
    P.b(0.12, 0.24, 0.96, 0.08, 0.03, 0.08, mix(sk, 0.3))
    P.b(0, 0, 1.12, 0.40, 0.34, 0.06, gold)
    for (dx, dy) in ((-0.15, -0.12), (0.15, -0.12), (-0.15, 0.12), (0.15, 0.12), (0, 0)):
        P.b(dx, dy, 1.18, 0.07, 0.07, 0.14, gold)
    P.b(0.0, 0.18, 1.14, 0.08, 0.03, 0.05, (230, 50, 60))
    m_eyes(P, 0.235, 0.195, 0.98, (255, 220, 60), (180, 30, 30), 0.065)
    return P


def m_beholder(t):
    col, colD, colL = (166, 70, 126), (118, 46, 92), (200, 100, 160)
    z0 = 0.62 + 0.06 * math.sin(t * 2)
    P = _P()
    prof = [0.40, 0.58, 0.72, 0.80, 0.84, 0.80, 0.72, 0.58, 0.40]
    z = z0
    for i, wd in enumerate(prof):
        P.b(0, 0, z, wd, wd, 0.085, colL if i == len(prof) - 1 else (col if i % 2 else colD))
        z += 0.085
    zc = z0 + 0.30
    P.b(0, 0.44, zc, 0.40, 0.02, 0.36, WHITE)
    P.b(0.44, 0, zc, 0.02, 0.40, 0.36, WHITE)
    pu = 0.5 + 0.5 * math.sin(t * 2.5)
    iris = mix((70, 220, 90), pu * 0.4)
    P.b(0, 0.455, zc + 0.04, 0.26, 0.02, 0.26, iris)
    P.b(0.455, 0, zc + 0.04, 0.02, 0.26, 0.26, iris)
    P.b(0, 0.47, zc + 0.10, 0.10, 0.02, 0.14, DARK)
    P.b(0.47, 0, zc + 0.10, 0.02, 0.10, 0.14, DARK)
    P.b(0.06, 0.475, zc + 0.20, 0.03, 0.01, 0.03, WHITE)
    P.b(0.475, 0.06, zc + 0.20, 0.01, 0.03, 0.03, WHITE)
    P.b(0, 0.40, z0 + 0.04, 0.58, 0.04, 0.14, (70, 10, 36))
    P.b(0.40, 0, z0 + 0.04, 0.04, 0.58, 0.14, (70, 10, 36))
    for i in range(8):
        P.b(-0.26 + 0.075 * i, 0.425, z0 + 0.12, 0.045, 0.03, 0.06, WHITE)
        P.b(-0.26 + 0.075 * i, 0.425, z0 + 0.02, 0.045, 0.03, 0.05, WHITE)
        P.b(0.425, -0.26 + 0.075 * i, z0 + 0.12, 0.03, 0.045, 0.06, WHITE)
    cols = [(255, 70, 70), (70, 140, 255), (255, 220, 60), (120, 255, 120), (255, 120, 255), (120, 255, 255), (255, 160, 60), (190, 120, 255), (255, 255, 255), (60, 255, 190)]
    ztop = z0 + 0.76
    for i in range(10):
        a = i / 10 * math.tau
        wob = math.sin(t * 3 + i * 1.3) * 0.05
        ca, sa = math.cos(a), math.sin(a)
        for k in range(4):
            r_ = 0.12 + 0.09 * k
            P.b(ca * r_ + wob * k * 0.6, sa * r_ + wob * k * 0.4, ztop - 0.04 + k * 0.10, 0.07 - 0.005 * k, 0.07 - 0.005 * k, 0.12, colD if k % 2 else col)
        ex, ey, ez = ca * 0.46 + wob * 2.4, sa * 0.46 + wob * 1.6, ztop + 0.34
        P.b(ex, ey, ez, 0.14, 0.14, 0.14, WHITE)
        P.b(ex + 0.04, ey + 0.07, ez + 0.03, 0.07, 0.02, 0.07, cols[i])
        P.b(ex + 0.07, ey + 0.04, ez + 0.03, 0.02, 0.07, 0.07, cols[i])
    return P


def m_minotaur(t):
    fur, dk, sk, bone = (116, 74, 52), (70, 46, 34), (156, 100, 70), (242, 234, 210)
    gold, steel = (226, 186, 72), (206, 212, 224)
    sw, arm = math.sin(t * 3), math.sin(t * 3) * 0.04
    P = _P()
    m_legs2(P, sw * 0.8, 0.13, 0.16, 0.19, 0.08, 0.20, 0.12, fur, fur, (40, 30, 30))
    P.b(0, 0, 0.40, 0.58, 0.40, 0.10, (150, 40, 40))
    P.b(0, 0.215, 0.24, 0.30, 0.02, 0.20, (130, 30, 34))
    P.b(0, 0, 0.50, 0.72, 0.46, 0.36, sk)
    P.b(0, 0.24, 0.54, 0.46, 0.02, 0.22, fur)
    for i in range(3):
        P.b(-0.10 + 0.10 * i, 0.26, 0.60 + 0.03 * (i % 2), 0.04, 0.02, 0.10, dk)
    P.b(0, 0, 0.84, 0.82, 0.50, 0.14, sk)
    for s_ in (-1, 1):
        P.b(s_ * 0.50, 0, 0.88, 0.20, 0.34, 0.14, sk)
        P.b(s_ * 0.50, 0, 0.44 - s_ * arm, 0.18, 0.22, 0.46, sk)
        P.b(s_ * 0.50, 0, 0.44 - s_ * arm, 0.20, 0.24, 0.08, gold)
        P.b(s_ * 0.50, 0, 0.36 - s_ * arm, 0.22, 0.26, 0.10, dk)
    P.b(0.0, 0.20, 0.96, 0.50, 0.02, 0.06, gold)
    for i in range(5):
        P.b(-0.20 + 0.10 * i, 0.22, 0.92 - 0.03 * math.sin(i), 0.06, 0.03, 0.06, steel)
    P.b(0, 0.02, 0.98, 0.40, 0.34, 0.30, fur)
    P.b(0.12, 0.17, 0.98, 0.22, 0.20, 0.16, (196, 146, 126))
    P.b(0.24, 0.27, 1.02, 0.05, 0.05, 0.05, DARK)
    P.b(0.14, 0.31, 1.02, 0.05, 0.03, 0.05, DARK)
    P.b(0.17, 0.30, 0.96, 0.10, 0.04, 0.03, gold)
    P.b(0.17, 0.30, 0.90, 0.07, 0.03, 0.07, gold)
    for s_ in (-1, 1):
        P.b(s_ * 0.24, 0.0, 1.14, 0.14, 0.07, 0.07, bone)
        P.b(s_ * 0.34, 0.0, 1.18, 0.12, 0.07, 0.07, bone)
        P.b(s_ * 0.42, 0.0, 1.24, 0.07, 0.07, 0.12, bone)
        P.b(s_ * 0.40, 0.0, 1.34, 0.05, 0.05, 0.08, (212, 204, 180))
        P.b(s_ * 0.36, 0.0, 0.98, 0.12, 0.05, 0.10, fur)
    m_eyes(P, 0.20, 0.18, 1.08, (255, 80, 40), DARK, 0.065)
    P.b(0.62, 0.20, 0.10 - arm, 0.07, 0.07, 1.00, (122, 86, 52))
    P.b(0.62, 0.20, 1.06 - arm, 0.10, 0.18, 0.04, steel)
    for s_ in (-1, 1):
        P.b(0.62, 0.20 + s_ * 0.24, 0.94 - arm, 0.10, 0.28, 0.34, steel)
        P.b(0.62, 0.20 + s_ * 0.34, 0.98 - arm, 0.08, 0.06, 0.26, (244, 248, 252))
    return P


def m_lich(t):
    z0 = 0.14 + 0.05 * math.sin(t * 2)
    robe, robeD, bone, boneD = (86, 52, 130), (50, 30, 82), (240, 236, 216), (192, 188, 172)
    gold, glow = (246, 206, 72), (130, 255, 140)
    arm = math.sin(t * 2.5) * 0.04
    P = _P()
    for i in range(7):
        a = i * math.tau / 7
        P.b(math.cos(a) * 0.22, math.sin(a) * 0.20, z0 - 0.12 - 0.04 * math.sin(t * 4 + i), 0.12, 0.12, 0.14, robeD if i % 2 else robe)
    for i, (wd, h) in enumerate([(0.56, 0.14), (0.52, 0.16), (0.46, 0.18), (0.40, 0.16), (0.36, 0.12)]):
        P.b(0, 0, z0 + sum(x[1] for x in [(0.56, 0.14), (0.52, 0.16), (0.46, 0.18), (0.40, 0.16), (0.36, 0.12)][:i]), wd, wd * 0.82, h, robe if i % 2 == 0 else robeD)
    P.b(0, 0.17, z0 + 0.34, 0.20, 0.02, 0.26, (20, 10, 30))
    for i in range(5):
        P.b(0, 0.185, z0 + 0.36 + i * 0.05, 0.18 - 0.01 * i, 0.01, 0.025, bone)
    P.b(0, 0, z0 + 0.76, 0.56, 0.38, 0.08, robeD)
    P.b(0, 0.20, z0 + 0.40, 0.30, 0.02, 0.05, gold)
    for s_ in (-1, 1):
        P.b(s_ * 0.34, 0.04, z0 + 0.34 + s_ * arm, 0.10, 0.16, 0.34, robe)
        P.b(s_ * 0.34, 0.06, z0 + 0.26 + s_ * arm, 0.10, 0.12, 0.08, bone)
        for k in (-1, 0, 1):
            P.b(s_ * 0.34 + 0.03 * k, 0.14, z0 + 0.24 + s_ * arm, 0.02, 0.06, 0.03, bone)
        m_flame(P, s_ * 0.34, 0.18, z0 + 0.30 + s_ * arm, t, 0.08, 2, s_)
    P.b(0, 0, z0 + 0.84, 0.30, 0.24, 0.24, bone)
    P.b(0.05, 0.05, z0 + 0.80, 0.22, 0.18, 0.06, boneD)
    P.b(0, 0.125, z0 + 0.84, 0.18, 0.02, 0.05, DARK)
    for k in range(4):
        P.b(-0.06 + 0.04 * k, 0.13, z0 + 0.82, 0.025, 0.02, 0.03, WHITE if k % 2 else boneD)
    m_eyes(P, 0.15, 0.125, z0 + 0.92, glow, (200, 255, 210), 0.065)
    P.b(0, 0, z0 + 1.08, 0.34, 0.28, 0.04, gold)
    for (dx, dy) in ((-0.15, -0.12), (0.15, -0.12), (-0.15, 0.12), (0.15, 0.12), (0, 0.13), (0.14, 0)):
        P.b(dx, dy, z0 + 1.12, 0.05, 0.05, 0.10, gold)
    P.b(0.0, 0.14, z0 + 1.10, 0.05, 0.03, 0.05, glow)
    P.b(0.40, 0.14, z0 - 0.04, 0.05, 0.05, 1.10, (66, 52, 64))
    P.b(0.40, 0.14, z0 + 1.06, 0.14, 0.14, 0.14, bone)
    P.b(0.40, 0.22, z0 + 1.10, 0.04, 0.02, 0.05, glow)
    P.b(0.46, 0.14, z0 + 1.10, 0.02, 0.04, 0.05, glow)
    m_flame(P, 0.40, 0.14, z0 + 1.20, t, 0.10, 3, 1.0)
    m_ring(P, 0, 0, z0 + 0.60, 0.52, 0.52, 3, 0.09, glow, t, 1.5, 0.08)
    ph = 0.5 + 0.5 * math.sin(t * 3)
    P.b(-0.44, 0.34, z0 + 0.70 + 0.06 * math.sin(t * 2), 0.12, 0.12, 0.12, mix((60, 220, 90), ph * 0.4))
    for i in range(8):
        a = i * math.tau / 8 + t * 0.4
        P.b(math.cos(a) * 0.62, math.sin(a) * 0.62, 0.0, 0.07, 0.07, 0.02, glow)
    return P


def m_mind_flayer(t):
    sk, skD = (160, 112, 202), (112, 78, 154)
    robe, robeD, gold = (68, 34, 104), (42, 22, 70), (246, 206, 72)
    arm = math.sin(t * 2.5) * 0.04
    P = _P()
    for i in range(6):
        a = i * math.tau / 6
        P.b(math.cos(a) * 0.22, math.sin(a) * 0.20, -0.02 + 0.03 * math.sin(t * 3 + i), 0.14, 0.14, 0.10, robeD if i % 2 else robe)
    for i, (wd, h) in enumerate([(0.54, 0.14), (0.50, 0.16), (0.44, 0.18), (0.40, 0.16)]):
        P.b(0, 0, 0.08 + sum(x[1] for x in [(0.54, 0.14), (0.50, 0.16), (0.44, 0.18), (0.40, 0.16)][:i]), wd, wd * 0.8, h, robe if i % 2 == 0 else robeD)
    P.b(0, 0.18, 0.28, 0.08, 0.02, 0.18, gold)
    P.b(0, 0.18, 0.54, 0.40, 0.02, 0.03, gold)
    P.b(0, 0, 0.72, 0.52, 0.34, 0.08, robeD)
    P.b(0, -0.12, 0.76, 0.62, 0.10, 0.50, robeD)
    P.b(-0.30, 0.0, 0.76, 0.10, 0.34, 0.40, robeD)
    P.b(0.30, -0.02, 0.76, 0.06, 0.30, 0.34, robeD)
    P.b(0, -0.14, 1.10, 0.70, 0.08, 0.16, robe)
    for s_ in (-1, 1):
        P.b(s_ * 0.34, 0.04, 0.32 + s_ * arm, 0.10, 0.16, 0.34, robe)
        P.b(s_ * 0.34, 0.06, 0.24 + s_ * arm, 0.10, 0.12, 0.09, sk)
        for k in (-1, 0, 1):
            P.b(s_ * 0.34 + 0.03 * k, 0.14, 0.22 + s_ * arm, 0.02, 0.07, 0.03, skD)
    P.b(0, 0, 0.82, 0.30, 0.24, 0.26, sk)
    P.b(0, 0, 1.06, 0.26, 0.22, 0.06, skD)
    P.b(0, 0.125, 0.88, 0.22, 0.02, 0.05, (60, 20, 70))
    P.b(0.145, 0, 0.88, 0.02, 0.18, 0.05, (60, 20, 70))
    m_eyes(P, 0.16, 0.13, 0.96, (255, 255, 255), (200, 200, 255), 0.07)
    for i in range(4):
        sw_ = math.sin(t * 3 + i * 1.1) * 0.03
        for k in range(5):
            P.b(-0.11 + 0.073 * i + sw_ * k * 0.6, 0.14 + 0.03 * k + sw_ * k * 0.4, 0.80 - k * 0.075, 0.06 - 0.004 * k, 0.06 - 0.004 * k, 0.09, skD if k % 2 else sk)
    P.b(0.42, 0.14, 0.00, 0.05, 0.05, 1.04, (80, 60, 100))
    ph = 0.5 + 0.5 * math.sin(t * 3)
    P.b(0.42, 0.14, 1.04, 0.16, 0.16, 0.16, mix((255, 130, 255), ph * 0.4))
    P.b(0.42, 0.14, 1.20, 0.07, 0.07, 0.07, gold)
    m_ring(P, 0.42, 0.14, 1.12, 0.22, 0.22, 3, 0.05, (255, 170, 255), t, 3.0, 0.03)
    m_ring(P, 0, 0, 0.9, 0.56, 0.56, 4, 0.05, (200, 150, 255), t, -1.5, 0.05)
    return P


# ------------------------------------------------------------------ registro dos monstros v3
MONSTERS_V3 = {
    "slime": m_ooze, "kobold": m_kobold, "goblin": m_goblin, "bat": m_bat, "stirge": m_stirge,
    "skeleton": m_skeleton, "zombie": m_zombie, "gnoll": m_gnoll, "wolfman": m_wolfman,
    "orc": m_orc, "ghost": m_ghost, "mimic": m_mimic, "gelatinous_cube": m_cube, "rust_monster": m_rust,
    "harpy": m_harpy, "displacer_beast": m_displacer, "ogre": m_ogre, "owlbear": m_owlbear, "troll": m_troll,
    "golem": m_golem, "gargoyle": m_gargoyle, "basilisk": m_basilisk, "hell_hound": m_hellhound,
    "dragon": m_dragon, "goblin_chief": m_goblin_chief, "werewolf": m_werewolf, "bat_queen": m_bat_queen,
    "orc_chief": m_orc_chief, "goblin_king": m_goblin_king, "beholder": m_beholder, "minotaur": m_minotaur,
    "lich": m_lich, "mind_flayer": m_mind_flayer}
NEW_PARTS.update(MONSTERS_V3)
ENEMY_NAMES.update({"slime": "Gosma Ácida", "stirge": "Estirge", "rust_monster": "Monstro da Ferrugem", "harpy": "Harpia",
                    "displacer_beast": "Fera Deslocadora", "gargoyle": "Gárgula", "basilisk": "Basilisco", "hell_hound": "Cão Infernal"})
ENEMY_COLOR.update({"stirge": (178, 84, 62), "rust_monster": (196, 116, 64), "harpy": (150, 100, 70), "displacer_beast": (46, 70, 104),
                    "gargoyle": (122, 126, 140), "basilisk": (112, 126, 60), "hell_hound": (255, 110, 40)})
ENEMY_SCALE.update({"wolfman": 1.75, "zombie": HERO_SCALE, "skeleton": HERO_SCALE, "goblin": 1.12})   # zumbi/esqueleto = tamanho do herói
ENEMY_SCALE.update({"stirge": 0.95, "rust_monster": 1.1, "harpy": 1.1, "displacer_beast": 1.2, "gargoyle": 1.1, "basilisk": 1.2,
                    "hell_hound": 1.2, "goblin_chief": 1.5, "werewolf": 1.5, "bat_queen": 1.4, "orc_chief": 1.4})
# --- tamanhos visuais v4: os bichos pequenos eram ~50% do herói e sumiam no cenário.
# STOP_SCALE guarda a escala ANTIGA só para calcular a distância de parada do herói (combate igual ao de antes).
STOP_SCALE = {k: ENEMY_SCALE.get(k, 1.0) for k in
              ("slime", "kobold", "goblin", "bat", "stirge", "gnoll", "ghost", "mimic", "rust_monster",
               "displacer_beast", "basilisk", "gargoyle")}
ENEMY_SCALE.update({"slime": 1.45, "kobold": 1.45, "goblin": 1.25, "bat": 1.3, "stirge": 1.3, "gnoll": 1.4,
                    "ghost": 1.15, "mimic": 1.15, "rust_monster": 1.2, "displacer_beast": 1.3,
                    "basilisk": 1.35, "gargoyle": 1.2})
# --- os GRANDES precisam ser claramente maiores que o herói (altura final dele = 1.38):
# orc 1.65 | wolfman 1.9 | ogro 2.2 | urso-coruja 1.9 | troll 2.1 | golem 2.2 | cubo 1.5 | cão infernal (comprido) 1.45
ENEMY_SCALE.update({"orc": 1.7, "wolfman": 1.9, "ogre": 1.8, "owlbear": 1.6, "troll": 1.95, "golem": 1.65,
                    "gelatinous_cube": 1.55, "hell_hound": 1.45, "gargoyle": 1.3,
                    "goblin_chief": 1.75, "werewolf": 1.75, "bat_queen": 1.5, "orc_chief": 1.5,
                    "minotaur": 1.6, "lich": 1.5, "mind_flayer": 1.6})
TIERS[:] = [["slime", "kobold", "goblin", "bat", "stirge"],
            ["skeleton", "zombie", "gnoll", "wolfman"],
            ["orc", "ghost", "mimic", "gelatinous_cube", "rust_monster", "harpy", "displacer_beast"],
            ["ogre", "owlbear", "troll", "golem", "gargoyle", "basilisk", "hell_hound"]]
REG_KINDS[:] = [k for tier_ in TIERS for k in tier_]


def regular_pool(f):
    pool = list(TIERS[0])
    for i, start in ((1, 3), (2, 6), (3, 9)):
        if f >= start:
            pool += TIERS[i]
    return pool


HEROES = [
    # hp = vidas iniciais | crit = chance de crítico | damage = bônus de dano base
    {"id": "knight", "name": "Cavaleiro", "title": "Equilíbrio de ferro", "hp": 4, "crit": 0.15, "damage": 1, "color": (118, 157, 255)},
    {"id": "ranger", "name": "Arquera", "title": "Flecha certeira", "hp": 3, "crit": 0.40, "damage": 0, "color": (120, 220, 140)},
    {"id": "mage", "name": "Maga", "title": "Luz arcana", "hp": 3, "crit": 0.08, "damage": 3, "color": (178, 130, 255)},
    {"id": "guardian", "name": "Guardião", "title": "Vigor da muralha", "hp": 5, "crit": 0.06, "damage": 0, "color": (255, 165, 105)},
    # Ladino: a MENOR vida (2), dano médio (2) e o MAIOR crítico (60%) -> canhão de vidro
    {"id": "rogue", "name": "Ladino", "title": "Golpe nas sombras", "hp": 2, "crit": 0.60, "damage": 2, "color": (242, 96, 124)},
]


def kind_for(f):
    if f % 5 == 0:
        return BOSS_KINDS[(f // 5 - 1) % len(BOSS_KINDS)]
    return REG_KINDS[(f - 1) % len(REG_KINDS)]


def is_duplo(f):
    return f >= 3 and f % 5 != 0 and f % 3 == 0


# ------------------------------------------------- geração procedural de andares
DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
BLOCK_OFF = {"crate": (0.2, 0.2), "barrel": (0.22, 0.22), "pillar": (0.25, 0.25), "rock": (0.2, 0.25)}
SOFT_OFF = {"bones": (0.25, 0.3), "chest": (0.19, 0.29)}


def cell_of(x, y):
    return int(math.floor(x)), int(math.floor(y))


def walkable(c, duplo, blocked):
    i, j = c
    if not (0 <= i < N and 0 <= j < N) or c in blocked:
        return False
    if duplo and i == 4 and not (3 <= j <= 4):   # só a rampa liga os dois andares
        return False
    return True


def find_cells(a, b, duplo, blocked):
    """A* na grade N x N (8 direções, sem cortar quina). Devolve lista de células ou None."""
    if not walkable(a, duplo, blocked) or not walkable(b, duplo, blocked):
        return None

    def h(c):
        dx, dy = abs(c[0] - b[0]), abs(c[1] - b[1])
        return max(dx, dy) + 0.414 * min(dx, dy)

    heap = [(h(a), 0.0, a)]
    g, came = {a: 0.0}, {a: None}
    while heap:
        _, cg, cur = heapq.heappop(heap)
        if cur == b:
            break
        if cg > g.get(cur, 1e9):
            continue
        for di, dj in DIRS8:
            n = (cur[0] + di, cur[1] + dj)
            if not walkable(n, duplo, blocked):
                continue
            if di and dj and not (walkable((cur[0] + di, cur[1]), duplo, blocked)
                                  and walkable((cur[0], cur[1] + dj), duplo, blocked)):
                continue
            ng = cg + (1.414 if di and dj else 1.0)
            if ng < g.get(n, 1e9):
                g[n], came[n] = ng, cur
                heapq.heappush(heap, (ng + h(n), ng, n))
    if b not in came:
        return None
    out, c = [], b
    while c is not None:
        out.append(c)
        c = came[c]
    return out[::-1]


def clear_line(p, q, duplo, blocked, r=0.22):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = max(1, int(math.hypot(dx, dy) / 0.1))
    for k in range(n + 1):
        x, y = p[0] + dx * k / n, p[1] + dy * k / n
        for ox in (-r, r):
            for oy in (-r, r):
                if not walkable(cell_of(x + ox, y + oy), duplo, blocked):
                    return False
    return True


HERO_R = 0.34                  # raio de colisão do herói (círculo no chão)
HERO_FRONT = math.pi / 4       # os modelos dos heróis são construídos olhando para (+1, +1)
# frente de cada monstro no modelo: bípedes olham para (+1,+1); quadrúpedes e dragão, para +x.
# Mímico, cubo, urso-coruja e beholder não giram.
QUAD_FRONT = {"rust_monster", "displacer_beast", "gargoyle", "basilisk", "hell_hound", "dragon"}
NO_TURN = {"mimic", "gelatinous_cube", "owlbear", "beholder"}


def foe_front(kind):
    return 0.0 if kind in QUAD_FRONT else HERO_FRONT
SOLID_KINDS = ("crate", "barrel", "pillar", "rock", "chest")   # decorações que não dá pra atravessar


def angle_diff(a, b):
    """Diferença angular a - b normalizada em [-pi, pi)."""
    return (a - b + math.pi) % math.tau - math.pi


def circle_hits(x, y, r, solids):
    for x0, y0, x1, y1 in solids:
        qx = x0 if x < x0 else (x1 if x > x1 else x)
        qy = y0 if y < y0 else (y1 if y > y1 else y)
        if (x - qx) * (x - qx) + (y - qy) * (y - qy) < r * r - 1e-9:
            return True
    return False


def push_out(x, y, r, solids, rounds=3):
    """Empurra o círculo (x, y, r) para fora das caixas sólidas e das bordas da sala.
    Como só remove a parte do movimento que entra no objeto, o herói DESLIZA pelas quinas."""
    for _ in range(rounds):
        x = min(max(x, r), N - r)
        y = min(max(y, r), N - r)
        moved = False
        for x0, y0, x1, y1 in solids:
            if not (x0 - r < x < x1 + r and y0 - r < y < y1 + r):
                continue
            qx = x0 if x < x0 else (x1 if x > x1 else x)
            qy = y0 if y < y0 else (y1 if y > y1 else y)
            dx, dy = x - qx, y - qy
            d2 = dx * dx + dy * dy
            if d2 >= r * r - 1e-9:
                continue
            if d2 > 1e-9:
                d = math.sqrt(d2)
                x, y = qx + dx / d * r, qy + dy / d * r
            else:   # centro dentro da caixa: sai pelo lado mais próximo
                l, rt, tp, bt = x - x0, x1 - x, y - y0, y1 - y
                m = min(l, rt, tp, bt)
                if m == l:
                    x = x0 - r
                elif m == rt:
                    x = x1 + r
                elif m == tp:
                    y = y0 - r
                else:
                    y = y1 + r
            moved = True
        if not moved:
            break
    return min(max(x, r), N - r), min(max(y, r), N - r)


def segment_clear(p, q, solids, r=HERO_R, step=0.07):
    """True se um círculo de raio r consegue ir de p até q sem encostar em nada sólido nem sair da sala."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = max(1, int(math.hypot(dx, dy) / step))
    lo, hi = r - 1e-6, N - r + 1e-6
    for k in range(n + 1):
        x, y = p[0] + dx * k / n, p[1] + dy * k / n
        if x < lo or y < lo or x > hi or y > hi or circle_hits(x, y, r, solids):
            return False
    return True


def smooth_path(pts, duplo, blocked, solids=None):
    """Puxa o caminho esticado: o herói anda em linha reta sempre que dá.
    Com `solids`, o atalho só vale se o herói inteiro (círculo) passa sem encostar em nada."""
    if solids is None:
        ok = lambda p, q: clear_line(p, q, duplo, blocked)
    else:
        ok = lambda p, q: segment_clear(p, q, solids)
    out, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not ok(pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return out


def wchoice(rng, weights):
    r = rng.uniform(0, sum(weights.values()))
    k = None
    for k, w in weights.items():
        r -= w
        if r <= 0:
            break
    return k


def jitter_pal(pal, rng):
    d = [rng.randint(-12, 12) for _ in range(3)]
    f = rng.uniform(0.92, 1.1)
    out = []
    for idx, c in enumerate(pal):
        if idx < 4:
            out.append(tuple(max(0, min(255, int(c[k] * f + d[k]))) for k in range(3)))
        else:
            out.append(c)
    return tuple(out)


def pick_kind(rng, f, avoid=(), bonus=0):
    """Inimigo comum sorteado; o tier mais novo tem peso dobrado. bonus=1 -> um tier acima (elite)."""
    idx = 0
    for i, start in ((1, 3), (2, 6), (3, 9)):
        if f >= start:
            idx = i
    pool = regular_pool(f + 3 * bonus) + TIERS[min(3, idx + bonus)]
    pool2 = [k for k in pool if k not in avoid] or pool
    return rng.choice(pool2)


def gen_floor(f, rng, prev=None, boss_bag=None):
    """Gera um andar inteiro (função pura: só depende de f, rng e do andar anterior)."""
    prev = prev or {}
    boss_bag = boss_bag if boss_bag is not None else []
    avoid = set(prev.get("kinds", ()))

    # ---- tipo de sala
    if f % 5 == 0:
        room = "boss"
    elif f == 1:
        room = "normal"
    else:
        w = {"normal": 50, "swarm": 14, "tesouro": 8}
        if f >= 3:
            w["duplo"] = 16
        if f >= 4:
            w["elite"] = 11
        if prev.get("room") == "boss":
            w["tesouro"] = 30            # respiro depois do chefe
        if prev.get("room") == "tesouro":
            del w["tesouro"]
        if prev.get("room") == "duplo":
            w.pop("duplo", None)
        room = wchoice(rng, w)
    duplo = room == "duplo"

    # ---- bioma
    pi = rng.choice([i for i in range(len(PALS)) if i != prev.get("pal")])
    pal = jitter_pal(PALS[pi], rng)

    def cc(c, jit=0.0):
        return (c[0] + 0.5 + rng.uniform(-jit, jit), c[1] + 0.5 + rng.uniform(-jit, jit))

    def far_cells(cells, taken, mind):
        cells = list(cells)
        rng.shuffle(cells)
        best, bd = cells[0], -1.0
        for c in cells:
            d = min((math.hypot(c[0] - t[0], c[1] - t[1]) for t in taken), default=99.0)
            if d >= mind:
                return c
            if d > bd:
                best, bd = c, d
        return best

    # ---- entrada do herói (perto das paredes do fundo)
    if duplo:
        sc = (rng.choice([1, 2]), rng.randint(1, 7))
    elif rng.random() < 0.5:
        sc = (rng.randint(1, 2), rng.randint(1, 7))
    else:
        sc = (rng.randint(1, 7), rng.randint(1, 2))

    # ---- inimigos
    foes, foe_cells = [], []
    allc = [(i, j) for i in range(2, N) for j in range(2, N)]
    if room == "duplo":
        k1 = pick_kind(rng, f, avoid)
        k2 = pick_kind(rng, f, avoid | {k1})
        c1 = far_cells([(i, j) for i in (1, 2) for j in range(1, 9)], [sc], 3.5)
        c2 = far_cells([(i, j) for i in (6, 7, 8) for j in range(1, 9)], [], 0)
        foe_cells = [c1, c2]
        foes = [dict(kind=k1, hpmul=0.75, elite=False), dict(kind=k2, hpmul=0.75, elite=False)]
    elif room == "swarm":
        n = 2 if (f < 8 or rng.random() < 0.6) else 3
        for _ in range(n):
            foes.append(dict(kind=pick_kind(rng, f, set()), hpmul=0.55, elite=False))
    elif room == "elite":
        foes = [dict(kind=pick_kind(rng, f, avoid, bonus=1), hpmul=1.5, elite=True)]
    elif room == "boss":
        if not boss_bag:
            boss_bag.extend(rng.sample(BOSS_KINDS, len(BOSS_KINDS)))
        foes = [dict(kind=boss_bag.pop(), hpmul=1.0, elite=False)]
    elif room == "normal":
        foes = [dict(kind=pick_kind(rng, f, avoid), hpmul=1.0, elite=False)]
    if not duplo:
        for k in range(len(foes)):
            foe_cells.append(far_cells(allc, [sc] + foe_cells, 4.0 if k == 0 else 2.8))

    # ---- escada de descida
    if duplo:
        stc = far_cells([(i, j) for i in (6, 7, 8) for j in range(1, 9)], [foe_cells[1]], 2.6)
    else:
        stc = far_cells([(i, j) for i in range(1, N) for j in range(1, N)], [sc] + foe_cells, 3.2)

    # ---- baú do tesouro (colado no herói)
    chest = None
    if room == "tesouro":
        chest = (min(N - 1, sc[0] + 1), sc[1]) if sc[0] <= sc[1] else (sc[0], min(N - 1, sc[1] + 1))

    # ---- obstáculos (sempre deixando caminho livre até tudo)
    reserve = set()
    for c in [sc, stc] + foe_cells + ([chest] if chest else []):
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                reserve.add((c[0] + di, c[1] + dj))
    arche = rng.choice(["aberta", "pilares"]) if room == "boss" else \
        rng.choice(["aberta", "pilares", "entulho", "caixas", "caixas"])
    cand = [(i, j) for i in range(N) for j in range(N)]
    rng.shuffle(cand)
    if arche == "pilares":
        oi, oj = rng.randint(0, 2), rng.randint(0, 2)
        cand = [c for c in cand if (c[0] + oi) % 3 == 0 and (c[1] + oj) % 3 == 0]
        kinds, want = ["pillar"], rng.randint(3, 6)
    elif arche == "entulho":
        kinds, want = ["rock", "rock", "pillar"], rng.randint(4, 7)
    elif arche == "caixas":
        mid = rng.choice(cand)
        cand.sort(key=lambda c: math.hypot(c[0] - mid[0], c[1] - mid[1]) + rng.uniform(0, 1.6))
        kinds, want = ["crate", "barrel"], rng.randint(4, 8)
    else:
        kinds, want = ["rock", "crate", "barrel", "pillar"], rng.randint(1, 3)
    targets = foe_cells + [stc]
    blocked, decor = set(), []
    for c in cand:
        if len(blocked) >= want:
            break
        if c in reserve or (duplo and 3 <= c[0] <= 5):
            continue
        trial = blocked | {c}
        if all(find_cells(sc, t, duplo, trial) for t in targets):
            blocked = trial
            kd = rng.choice(kinds)
            ox, oy = BLOCK_OFF[kd]
            decor.append((c[0] + ox, c[1] + oy, kd))

    # ---- decoração solta (fora do caminho)
    pcells, last = set(), sc
    for t in targets:
        pcells.update(find_cells(last, t, duplo, blocked) or [])
        last = t
    free = [c for c in cand if c not in blocked and c not in pcells and c not in reserve
            and not (duplo and 3 <= c[0] <= 5)]
    rng.shuffle(free)
    for c in free[:rng.randint(2, 5)]:
        kd = "chest" if rng.random() < 0.25 else "bones"
        ox, oy = SOFT_OFF[kd]
        decor.append((c[0] + ox, c[1] + oy, kd))
    if chest:
        ox, oy = SOFT_OFF["chest"]
        decor.append((chest[0] + ox, chest[1] + oy, "chest"))

    # ---- bandeiras e tochas nas paredes
    def spread(count, lo, hi, gap, avoid_iv=()):
        out = []
        for _ in range(80):
            if len(out) >= count:
                break
            v = round(rng.uniform(lo, hi) * 2) / 2
            if all(abs(v - o) >= gap for o in out) and not any(a <= v <= b for a, b in avoid_iv):
                out.append(v)
        return out

    banners, torches = [], []
    for ax in ("x", "y"):
        bv = spread(rng.choice([0, 1, 1, 2]), 0.8, 6.8, 2.6)
        banners += [(ax, v) for v in bv]
        torches += [(ax, v) for v in spread(rng.choice([2, 2, 3]), 1.2, 7.6, 2.2, [(b - 0.4, b + 1.4) for b in bv])]

    names = {"boss": None, "elite": "INIMIGO ELITE! (recompensa extra)", "tesouro": "SALA DO TESOURO!",
             "duplo": "MASMORRA DE 2 ANDARES!", "swarm": f"EMBOSCADA! {len(foes)} INIMIGOS!", "normal": ""}
    if room == "boss":
        k = foes[0]["kind"]
        banner = "CUIDADO! UM DRAGÃO!" if k == "dragon" else f"CHEFE: {ENEMY_NAMES.get(k, k)}!"
    else:
        banner = names[room]

    sp = cc(sc)
    for fo, c in zip(foes, foe_cells):
        fo["x"], fo["y"] = cc(c, 0.15)
    return dict(room=room, duplo=duplo, pal_idx=pi, pal=pal, spawn=sp, foes=foes, stairs=cc(stc),
                decor=decor, blocked=blocked, torches=torches, banners=banners, banner=banner,
                arche=arche)


# ------------------------------------------------------------------ cartas
CARDS = {
    "espada": ("Espada Afiada", "+2 de dano em cada acerto", (130, 160, 230)),
    "escudo": ("Escudo", "Recebe -1 de dano quando erra", (80, 130, 240)),
    "coracao": ("Coração", "+8 de vida máxima e cura 8", (235, 80, 110)),
    "foco": ("Foco", "+1 de bônus por acerto seguido", (250, 190, 60)),
    "trevo": ("Trevo da Sorte", "+20% de chance de errar sem dano", (70, 200, 110)),
}

# arte pixel 12x12 dos ícones das cartas
ICON_ART = {
    "coracao": ([
        "............",
        ".kkk....kkk.",
        "kRRRk..kRRRk",
        "kRwRRkkRRRRk",
        "kRwRRRRRRRRk",
        "kRRRRRRRRRRk",
        ".kRRRRRRRRk.",
        "..kRRRRRRk..",
        "...kRRRRk...",
        "....kRRk....",
        ".....kk.....",
        "............"],
        {"k": (80, 15, 35), "R": (236, 70, 100), "w": (255, 205, 215)}),
    "espada": ([
        ".....kk.....",
        "....kWWk....",
        "....kWwk....",
        "....kWwk....",
        "....kWwk....",
        "....kWwk....",
        "....kWwk....",
        "..kkkkkkkk..",
        "..kGGGGGGk..",
        "...kkBBkk...",
        "....kBBk....",
        "....kkkk...."],
        {"k": (30, 34, 60), "W": (232, 238, 250), "w": (160, 172, 200), "G": (245, 205, 70), "B": (130, 84, 46)}),
    "escudo": ([
        ".kkkkkkkkkk.",
        "kBBBBWWBBBBk",
        "kBwBBWWBBBBk",
        "kBBBBWWBBBBk",
        "kWWWWWWWWWWk",
        "kWWWWWWWWWWk",
        "kBBBBWWBBBBk",
        ".kBBBWWBBBk.",
        ".kBBBWWBBBk.",
        "..kBBWWBBk..",
        "...kBWWBk...",
        "....kkkk...."],
        {"k": (20, 30, 70), "B": (70, 116, 230), "w": (150, 190, 255), "W": (240, 242, 252)}),
    "foco": ([
        "....kkkk....",
        "..kkOOOOkk..",
        ".kOOkkkkOOk.",
        ".kOkYYYYkOk.",
        "kOkYYkkYYkOk",
        "kOkYkRRkYkOk",
        "kOkYkRRkYkOk",
        "kOkYYkkYYkOk",
        ".kOkYYYYkOk.",
        ".kOOkkkkOOk.",
        "..kkOOOOkk..",
        "....kkkk...."],
        {"k": (70, 40, 10), "O": (250, 168, 50), "Y": (255, 232, 110), "R": (232, 60, 60)}),
    "trevo": ([
        "..kkk..kkk..",
        ".kGGGkkGGGk.",
        "kGgGGGGGGGGk",
        "kGGGGkkGGGGk",
        ".kkGGGGGGkk.",
        ".kGGGkkGGGk.",
        "kGGGGGGGGGGk",
        "kGGGGkkGGGGk",
        ".kGGkkkkGGk.",
        ".....kBk....",
        "......Bk....",
        ".....kk....."],
        {"k": (10, 60, 30), "G": (70, 200, 100), "g": (170, 252, 180), "B": (120, 86, 44)}),
}


# ------------------------------------------------------ fonte do título (estilo D&D)
# 1) arquivo .ttf/.otf na pasta do jogo (ou em ./fonts) cujo nome contenha uma destas palavras;
# 2) fonte instalada no sistema, na ordem abaixo (as primeiras são as mais parecidas com a do D&D);
# 3) fonte padrão do pygame.
TITLE_FONT_FILES = ("mookmania", "modesto", "dungeon", "dnd", "titulo", "title")
TITLE_FONT_SYS = ("mookmania", "modestocondensed", "modestocaps", "modesto", "cinzeldecorative", "cinzel", "trajanpro",
                  "trajan", "optimustitling", "papyrus", "palatinolinotype", "bookantiqua", "georgia")


def find_title_font():
    base = os.path.dirname(os.path.abspath(__file__))
    for folder in (base, os.path.join(base, "fonts")):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for key in TITLE_FONT_FILES:
            for n in names:
                if n.lower().endswith((".ttf", ".otf")) and key in n.lower():
                    return os.path.join(folder, n)
    for name in TITLE_FONT_SYS:
        try:
            p = pygame.font.match_font(name, bold=True) or pygame.font.match_font(name)
        except Exception:
            p = None
        if p:
            return p
    return None


def wrap(font, text, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------- contas
def tier(floor):
    add_max = 10 if floor <= 2 else 20 if floor <= 4 else 40 if floor <= 6 else 70 if floor <= 9 else 100
    mul_max = 0 if floor < 4 else 5 if floor <= 5 else 7 if floor <= 7 else 9 if floor <= 9 else 10 if floor < 15 else 12
    div_max = 0 if floor < 7 else min(mul_max, 12)
    return add_max, mul_max, div_max


def make_question(floor):
    add_max, mul_max, div_max = tier(floor)
    ops, wts = ["+", "-"], [3, 3]
    if mul_max:
        ops.append("×"); wts.append(3 if floor < 7 else 4)
    if div_max:
        ops.append("÷"); wts.append(3)
    op = random.choices(ops, wts)[0]
    if op == "+":
        a, b = random.randint(1, add_max), random.randint(1, add_max)
        ans = a + b
    elif op == "-":
        a, b = random.randint(1, add_max), random.randint(1, add_max)
        if b > a:
            a, b = b, a
        ans = a - b
    elif op == "×":
        a, b = random.randint(2, mul_max), random.randint(2, mul_max)
        ans = a * b
    else:
        b, q = random.randint(2, div_max), random.randint(2, div_max)
        a, ans = b * q, q
    cands = {ans + d for d in (1, 2, 3, -1, -2, -3, 10, -10)}
    if op == "×":
        cands |= {a * (b + 1), a * (b - 1), ans + a}
    if op == "÷":
        cands |= {ans + 1, ans - 1, b}
    cands = [c for c in cands if c >= 0 and c != ans]
    wrong = random.choice(cands)
    opts = [ans, wrong]
    random.shuffle(opts)
    return f"{a} {op} {b} = ?", ans, opts


# ------------------------------------------------------------------- sons
def tone(freq, dur, vol=0.25, slide=0.0):
    n = int(22050 * dur)
    buf = bytearray()
    for i in range(n):
        t = i / 22050
        f = freq + slide * i / n
        v = int(32767 * vol * math.sin(2 * math.pi * f * t) * (1 - i / n))
        buf += struct.pack("<h", v)
    return pygame.mixer.Sound(buffer=bytes(buf))


def build_adventure_theme():
    notes = [261.63, 329.63, 392.00, 329.63, 392.00, 493.88, 523.25, 493.88, 392.00, 329.63, 293.66, 329.63]
    seq = []
    for note in notes:
        seq.append((note, 0.17))
        seq.append((0, 0.05))
    return seq


# ================================================================== TRILHA SONORA
# Trilha "Aventura Medieval" gerada por código (100% offline, sem arquivos de áudio):
# alaúde em arpejo, baixo "oom-pah", flauta com vibrato, tambor, pandeiro e zumbido de gaita-de-foles.
# Ré dórico, 132 BPM, 16 compassos (~29 s) em loop contínuo.
SR = 22050
BPM = 132
_NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _midi(name):
    n = name[0]
    acc = 0
    rest = name[1:]
    if rest[0] == "#":
        acc, rest = 1, rest[1:]
    elif rest[0] == "b":
        acc, rest = -1, rest[1:]
    return 12 * (int(rest) + 1) + _NOTE_BASE[n] + acc


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


MEDIEVAL_MELODY = [
    "D4 - F4 A4 A4 - G4 F4", "E4 - G4 C5 C5 - G4 E4", "D4 - F4 A4 D5 - C5 A4", "A4 - C5 A4 E4 - - .",
    "D4 - F4 A4 A4 - G4 F4", "E4 - G4 C5 E5 - D5 C5", "D5 - Bb4 G4 Bb4 - D5 -", "C#5 - E5 A4 C#5 - - .",
    "A4 - C5 F5 F5 - E5 C5", "G4 - C5 E5 G5 - E5 C5", "F5 - E5 D5 A4 - D5 F5", "E5 - C5 A4 E5 - - .",
    "A4 - C5 F5 A5 - G5 F5", "E5 - G5 E5 C5 - E5 G5", "A4 - C#5 E5 A5 - E5 C#5", "D5 - A4 - D4 - - .",
]
# (baixo, tríade) de cada compasso
_CH = {"Dm": ("D2", ("D3", "F3", "A3")), "C": ("C2", ("C3", "E3", "G3")), "Gm": ("G2", ("G3", "Bb3", "D4")),
       "Am": ("A2", ("A3", "C4", "E4")), "A": ("A2", ("A3", "C#4", "E4")), "F": ("F2", ("F3", "A3", "C4"))}
MEDIEVAL_CHORDS = ["Dm", "C", "Dm", "Am", "Dm", "C", "Gm", "A", "F", "C", "Dm", "Am", "F", "C", "A", "Dm"]


def build_medieval_track(pause=None):
    """Devolve bytes PCM 16-bit mono (22050 Hz) prontos para pygame.mixer.Sound(buffer=...)."""
    rnd = random.Random(7)
    sin, exp, tau = math.sin, math.exp, math.tau
    eighth = 60.0 / BPM / 2.0
    bars = len(MEDIEVAL_MELODY)
    N = int(bars * 8 * eighth * SR)
    TAIL = SR
    master = [0.0] * (N + TAIL)
    cache = {}

    def mix(wave, t0, gain):
        a = int(t0 * SR)
        b = min(len(master), a + len(wave))
        if b <= a:
            return
        seg = master[a:b]
        master[a:b] = [x + y * gain for x, y in zip(seg, wave)]
        if pause:
            pause()

    def wave(kind, f, d):
        key = (kind, round(f, 2), round(d, 3))
        w = cache.get(key)
        if w is not None:
            return w
        n = int(d * SR)
        out = [0.0] * n
        if kind == "pluck":          # alaúde: ataque seco, harmônicos que morrem rápido
            for i in range(n):
                t = i / SR
                e = min(1.0, t * 400) * exp(-t * 5.5)
                out[i] = e * (sin(tau * f * t) + 0.45 * exp(-t * 4) * sin(tau * f * 2 * t) + 0.2 * exp(-t * 8) * sin(tau * f * 3 * t))
        elif kind == "flute":        # flauta: vibrato suave depois do ataque + um pouco de sopro
            for i in range(n):
                t = i / SR
                att = min(1.0, t / 0.035)
                rel = min(1.0, (d - t) / 0.07)
                vib = 1 + 0.004 * sin(tau * 5.4 * t) * min(1.0, t / 0.25)
                ph = tau * f * vib * t
                out[i] = att * rel * (sin(ph) + 0.28 * sin(2 * ph) + 0.08 * sin(3 * ph) + 0.03 * (rnd.random() * 2 - 1))
        elif kind == "bass":         # baixo macio, quase triangular
            for i in range(n):
                t = i / SR
                e = min(1.0, t * 300) * exp(-t * 3.2)
                out[i] = e * (sin(tau * f * t) + 0.3 * sin(tau * f * 3 * t) / 3 + 0.12 * sin(tau * f * 2 * t))
        elif kind == "drone":        # zumbido de gaita: quinta justa bem baixinha
            for i in range(n):
                t = i / SR
                e = min(1.0, t / 0.08) * min(1.0, (d - t) / 0.2)
                out[i] = e * (sin(tau * f * t) + 0.6 * sin(tau * f * 1.5 * t) + 0.25 * sin(tau * f * 2 * t))
        elif kind == "kick":
            ph = 0.0
            for i in range(n):
                t = i / SR
                ph += tau * (48 + 90 * exp(-t * 28)) / SR
                out[i] = sin(ph) * exp(-t * 11) * min(1.0, t * 800)
        elif kind == "snare":        # tambor de mão / pandeiro
            for i in range(n):
                t = i / SR
                out[i] = (0.75 * (rnd.random() * 2 - 1) * exp(-t * 26) + 0.5 * sin(tau * 190 * t) * exp(-t * 30))
        elif kind == "shaker":
            prev = 0.0
            for i in range(n):
                t = i / SR
                r = rnd.random() * 2 - 1
                out[i] = (r - prev) * exp(-t * 70)
                prev = r
        cache[key] = out
        return out

    # drone contínuo (Ré + Lá) por compasso
    for bar in range(bars):
        t0 = bar * 8 * eighth
        mix(wave("drone", _hz(_midi("D2")), 8 * eighth + 0.1), t0, 0.05)
    for bar in range(bars):
        base = bar * 8 * eighth
        bass, tri = _CH[MEDIEVAL_CHORDS[bar]]
        bm = _midi(bass)
        for i in range(8):
            t0 = base + i * eighth
            # baixo oom-pah
            if i in (0, 4):
                mix(wave("bass", _hz(bm), eighth * 2.2), t0, 0.40)
            elif i in (2, 6):
                mix(wave("bass", _hz(bm + 7), eighth * 1.6), t0, 0.22)
            # alaúde arpejando a tríade
            order = (0, 2, 1, 2, 0, 2, 1, 2)[i]
            mix(wave("pluck", _hz(_midi(tri[order])), eighth * 3.0), t0, 0.15 if i % 2 else 0.19)
            # percussão
            if i in (0, 4):
                mix(wave("kick", 0, 0.26), t0, 0.62)
            if i in (2, 6):
                mix(wave("snare", 0, 0.13), t0, 0.22)
            mix(wave("shaker", 0, 0.06), t0 + (eighth * 0.0), 0.05 if i % 2 == 0 else 0.032)
            if bar % 4 == 3 and i >= 6:      # pequena virada no fim de cada 4 compassos
                mix(wave("snare", 0, 0.13), t0 + eighth * 0.5, 0.16)
        # melodia na flauta (o '-' prolonga a nota, o '.' é pausa)
        toks = MEDIEVAL_MELODY[bar].split()
        i = 0
        while i < 8:
            tk = toks[i]
            if tk in (".", "-"):
                i += 1
                continue
            j = i + 1
            while j < 8 and toks[j] == "-":
                j += 1
            d = (j - i) * eighth * 0.96
            m = _midi(tk)
            mix(wave("flute", _hz(m), d), base + i * eighth, 0.30 if bar < 8 else 0.33)
            if bar >= 8:     # na segunda metade entra uma segunda flauta uma oitava abaixo
                mix(wave("flute", _hz(m - 12), d), base + i * eighth, 0.10)
            i = j
    # fecha o loop: a cauda do final soa por cima do começo
    for i in range(TAIL):
        master[i] += master[N + i]
    master = master[:N]
    peak = max(max(master), -min(master)) or 1.0
    k = 0.80 * 32767 / peak
    return struct.pack("<%dh" % len(master), *[int(x * k) for x in master])


TORCHES = [("x", 2.5), ("x", 6.5), ("y", 2.5), ("y", 6.5)]


# -------------------------------------------------------------------- jogo
class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption("Masmorra dos Números")
        self.clock = pygame.time.Clock()
        self.fonts = {}
        self.icons = {}
        self.sounds = {}
        self.hero_index = 0
        self.hero = HEROES[self.hero_index]
        self.music_channel = None
        self.music_sound = None
        self.cfg = load_cfg()
        self.music_on = self.cfg["music"]
        self.settings_open = False
        self.set_sel = 0
        self.fs = False
        self.ui_t = 0.0
        self._music_box = {}
        try:
            pygame.mixer.set_reserved(1)       # canal 0 é só da trilha; os efeitos usam os outros
        except Exception:
            pass
        # a trilha é sintetizada em segundo plano para o jogo abrir na hora
        def _make_music(box=self._music_box):
            try:
                box["data"] = build_medieval_track(lambda: time.sleep(0.001))
            except Exception:
                traceback.print_exc()
        threading.Thread(target=_make_music, daemon=True).start()
        try:
            self.sounds = {
                "ok": tone(660, 0.18, 0.2, 400), "bad": tone(200, 0.3, 0.25, -100),
                "hit": tone(140, 0.15, 0.3, -60), "card": tone(500, 0.35, 0.2, 500),
                "fall": tone(400, 0.6, 0.2, -300), "crit": tone(900, 0.18, 0.22, 600),
            }
        except Exception:
            self.sounds = {}
        self.vig = make_vignette()
        self.glow = [make_glow(110, (70, 40, 12)), make_glow(120, (90, 52, 16))]
        self.stair_glow = [make_glow(120, (10, 26, 70)), make_glow(125, (18, 44, 110)), make_glow(130, (28, 64, 150))]
        self.best = 1
        self.t = 0.0
        self.shake = 0.0
        self.cam = (0, 0)
        self.particles, self.floaters = [], []
        self.banner, self.banner_t = "", 0.0
        self.score = 0
        self.transition = None
        self.new_run(title=True)

    # ---------------------------------------------------------- utilidades
    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        return self.fonts[size]

    def title_font(self, size):
        """Fonte do título do menu (estilo Dungeons & Dragons); cai na padrão se nada for encontrado."""
        if not hasattr(self, "_title_path"):
            self._title_path = find_title_font()
            print(f"[masmorra] fonte do título: {self._title_path or 'padrão do pygame'}")
        key = ("title", size)
        if key not in self.fonts:
            try:
                self.fonts[key] = pygame.font.Font(self._title_path, size)
            except Exception:
                self.fonts[key] = pygame.font.Font(None, size)
        return self.fonts[key]

    def text(self, s, size, color, pos, center=True, shadow=True):
        f = self.font(size)
        if shadow:
            sh = f.render(s, True, (0, 0, 0))
            r = sh.get_rect(center=(pos[0] + 2, pos[1] + 2)) if center else sh.get_rect(topleft=(pos[0] + 2, pos[1] + 2))
            self.screen.blit(sh, r)
        img = f.render(s, True, color)
        r = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
        self.screen.blit(img, r)

    def play(self, name):
        if self.cfg.get("sfx", True) and name in self.sounds:
            self.sounds[name].play()

    def icon(self, k, size):
        key = (k, size)
        if key not in self.icons:
            grid, pal = ICON_ART[k]
            base = pygame.Surface((12, 12), pygame.SRCALPHA)
            for r, row in enumerate(grid):
                for c, ch in enumerate(row):
                    if ch in pal:
                        base.set_at((c, r), pal[ch])
            self.icons[key] = pygame.transform.scale(base, (size, size))
        return self.icons[key]

    # ------------------------------------------------------------ estado
    def new_run(self, title=False):
        self.hero = HEROES[self.hero_index]
        self.floor = 1
        seed = getattr(self, "forced_seed", None)
        self.forced_seed = None
        self.run_seed = seed if seed is not None else random.randrange(1, 1 << 30)
        self.prev, self.boss_bag = {}, []
        print(f"[masmorra] semente da partida: {self.run_seed}")
        self.maxhp = self.hero["hp"]
        self.hp = self.maxhp
        self.cards = {k: 0 for k in CARDS}
        self.streak = 0
        self.mistakes = 0
        self.score = 0
        self.transition = None
        self.new_floor()
        if title:
            self.phase = "title"
            self.pz = ground(self.px, self.py, self.duplo)

    def make_foe(self, kind, x, y, hpmul=1.0, elite=False):
        f = self.floor
        boss = kind in BOSS_KINDS
        mhp = int((12 + 5 * f) * (1.8 if boss else 1.0) * hpmul)
        s = ENEMY_SCALE.get(kind, 1.0) * (1.15 if elite else 1.0)
        return {"kind": kind, "x": x, "y": y, "z": ground(x, y, self.duplo), "hp": mhp, "maxhp": mhp,
                "flash": 0.0, "scale": 1.0, "s": s, "boss": boss, "elite": elite,
                "stop": 1.3 + (STOP_SCALE.get(kind, ENEMY_SCALE.get(kind, 1.0)) * (1.15 if elite else 1.0) - 1) * 1.4}

    def start_transition(self, kind="dark", duration=1.1):
        self.transition = {"kind": kind, "time": 0.0, "duration": duration}

    def advance_floor(self):
        self.floor = max(1, self.floor + 1)
        self.best = max(self.best, self.floor)
        self.score += 50 + self.floor * 12
        self.new_floor()
        if self.floor % HEAL_EVERY == 0 and self.hp < self.maxhp:   # cura só a cada 3 andares
            self.hp = self.maxhp
            self.float_text("Vida restaurada! ♥", self.px, self.py, self.pz + 1.8, (120, 255, 140))

    def new_floor(self):
        f = self.floor
        rng = random.Random(self.run_seed * 1000003 + f * 7919)
        lay = gen_floor(f, rng, self.prev, self.boss_bag)
        self.lay = lay
        self.prev = {"room": lay["room"], "pal": lay["pal_idx"], "kinds": [s["kind"] for s in lay["foes"]]}
        self.pal = lay["pal"]
        self.duplo = lay["duplo"]
        self.room_kind = lay["room"]
        self.blocked = lay["blocked"]
        self.torches = lay["torches"]
        self.decor = lay["decor"]
        self.room = build_room(self.pal, self.duplo, rng.randrange(1 << 30), lay)
        self.foes = [self.make_foe(s["kind"], s["x"], s["y"], s["hpmul"], s["elite"]) for s in lay["foes"]]
        # sólidos: o que o herói não atravessa (decoração grande, baús, beira da plataforma)
        self.solids = self.build_solids()
        self.pblocked = set(self.blocked) | {cell_of(x, y) for (x, y, k) in self.decor if k == "chest"}
        self.banner, self.banner_t = lay["banner"], (3.0 if lay["banner"] else 0.0)
        self.cur = 0
        self.enemy = self.foes[0] if self.foes else None
        self.waypoints = []
        self.px, self.py = lay["spawn"]
        self.pz = ground(self.px, self.py, self.duplo) + 5.0
        self.pscale, self.pflash = 1.0, 0.0
        self.lunge = 0.0
        self.elunge = 0.0
        self.stairs = None
        self.moving = False
        self.land_t = 0.0
        self.dust_t = 0.0
        self.flash_t = 0.0
        if self.foes:   # nasce já olhando para o primeiro inimigo
            self.hd = math.atan2(self.foes[0]["y"] - self.py, self.foes[0]["x"] - self.px)
        else:
            self.hd = HERO_FRONT
        self.face = (math.cos(self.hd), math.sin(self.hd))
        self.turn_v = self.spd = self.stuck_t = 0.0
        self.steered = False
        self.phase = "arrive"
        self.pt = 0.0
        self.dtm = 0.0
        self.particles.clear()
        self.floaters.clear()
        self.sel = None
        self.question = None

    def find_path(self, src, dst, target=None):
        """Caminho (A* + suavização) até dst desviando de obstáculos e de outros inimigos vivos."""
        a, b = cell_of(*src), cell_of(*dst)
        soft = {cell_of(fo["x"], fo["y"]) for fo in self.foes if fo["hp"] > 0 and fo is not target}
        foe_boxes = [(fo["x"] - 0.45 * fo["s"], fo["y"] - 0.45 * fo["s"], fo["x"] + 0.45 * fo["s"], fo["y"] + 0.45 * fo["s"])
                     for fo in self.foes if fo["hp"] > 0 and fo is not target]
        for blk, extra in ((self.pblocked | soft, foe_boxes), (self.pblocked, []), (set(self.blocked), [])):
            blk = set(blk)
            blk.discard(a)
            blk.discard(b)
            cells = find_cells(a, b, self.duplo, blk)
            if cells:
                pts = [src] + [(i + 0.5, j + 0.5) for i, j in cells[1:-1]] + [dst]
                return smooth_path(pts, self.duplo, blk, self.solids + extra)[1:-1]
        return []

    # ------------------------------------------------- colisão e giro do herói
    def decor_rect(self, x, y, kind):
        """Pegada no chão (x0, y0, x1, y1) de uma decoração, calculada a partir dos próprios voxels dela."""
        ps = self.decor_parts(kind)
        return (x + min(p[0] for p in ps), y + min(p[1] for p in ps),
                x + max(p[0] + p[3] for p in ps), y + max(p[1] + p[4] for p in ps))

    def build_solids(self):
        out = [self.decor_rect(x, y, k) for (x, y, k) in self.decor if k in SOLID_KINDS]
        if self.duplo:
            for j in range(N):
                if not 3 <= j <= 4:     # fora da rampa: faixa do desnível + guarda-corpo da plataforma
                    out.append((PLAT_X - 0.16, j, PLAT_X + 1.0, j + 1.0))
        return out

    def turn_to(self, goal, dt, rate):
        """Gira suavemente o herói (self.hd) em direção ao ângulo `goal`."""
        d = angle_diff(goal, self.hd)
        self.hd = (self.hd + d * (1.0 - math.exp(-rate * dt)) + math.pi) % math.tau - math.pi

    def steer(self, tx, ty, dt, speed, limit=None):
        """Anda em direção a (tx, ty): primeiro vira o corpo, acelera aos poucos, e nunca entra em nada sólido."""
        dx, dy = tx - self.px, ty - self.py
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return 0.0
        speed *= self.cfg["speed"]
        self.steered = True
        goal = math.atan2(dy, dx)
        self.turn_to(goal, dt, 16.0)
        align = max(0.0, math.cos(angle_diff(goal, self.hd)))      # de costas pro alvo: quase parado, só girando
        self.spd += (speed - self.spd) * min(1.0, dt * 12.0)       # acelera/freia suave
        step = self.spd * dt * (0.25 + 0.75 * align)
        step = min(step, dist if limit is None else max(0.0, limit))
        ox, oy = self.px, self.py
        self.px, self.py = push_out(ox + dx / dist * step, oy + dy / dist * step, HERO_R, self.solids)
        moved = math.hypot(self.px - ox, self.py - oy)
        if step > 1e-4 and moved < step * 0.35:     # encostou e não sai do lugar
            self.stuck_t += dt
        else:
            self.stuck_t = max(0.0, self.stuck_t - dt)
        return moved

    # ---- modo manual e configurações
    SET_ROWS = ("mode", "speed", "music", "music_vol", "sfx", "shake", "fs", "reset", "menu", "back")

    def set_keys(self):
        return [k for k in self.SET_ROWS if not (k == "menu" and self.phase == "title")]

    def manual(self):
        return self.cfg["mode"] == "manual"

    def move_input(self):
        k = pygame.key.get_pressed()
        sx = int(bool(k[pygame.K_RIGHT] or k[pygame.K_d])) - int(bool(k[pygame.K_LEFT] or k[pygame.K_a]))
        sy = int(bool(k[pygame.K_DOWN] or k[pygame.K_s])) - int(bool(k[pygame.K_UP] or k[pygame.K_w]))
        wx, wy = sx + sy, sy - sx
        n = math.hypot(wx, wy)
        return (wx / n, wy / n) if n else (0.0, 0.0)

    def foe_solids(self):
        out = []
        for fo in self.foes:
            if fo["hp"] > 0 and fo["scale"] > 0.02:
                h = max(0.2, min(0.42 * fo["s"], (fo["stop"] - HERO_R - 0.12) / 1.42))
                out.append((fo["x"] - h, fo["y"] - h, fo["x"] + h, fo["y"] + h))
        return out

    def drive(self, dx, dy, dt, speed):
        if dx == 0 and dy == 0:
            return 0.0
        self.steered = True
        goal = math.atan2(dy, dx)
        self.turn_to(goal, dt, 22.0)
        align = max(0.0, math.cos(angle_diff(goal, self.hd)))
        self.spd += (speed * self.cfg["speed"] - self.spd) * min(1.0, dt * 12.0)
        step = self.spd * dt * (0.5 + 0.5 * align)
        ox, oy = self.px, self.py
        self.px, self.py = push_out(ox + dx * step, oy + dy * step, HERO_R, self.solids + self.foe_solids())
        return math.hypot(self.px - ox, self.py - oy)

    def walk_manual(self, dt):
        dx, dy = self.move_input()
        moved = self.drive(dx, dy, dt, 3.2)
        self.moving = moved > 1e-4
        best, bd = None, 1e9
        for i, fo in enumerate(self.foes):
            if fo["hp"] > 0 and fo["scale"] > 0.02:
                d = math.hypot(fo["x"] - self.px, fo["y"] - self.py)
                if d < bd:
                    best, bd = i, d
        if best is None:
            self.give_card()
            return
        self.cur, self.enemy = best, self.foes[best]
        if bd <= self.enemy["stop"] + 0.02:      # encostou num inimigo: começa a conta
            self.moving = False
            self.start_quiz()

    def stairs_manual(self, dt):
        dx, dy = self.move_input()
        moved = self.drive(dx, dy, dt, 3.4)
        self.moving = moved > 1e-4
        sx, sy = self.stairs
        if math.hypot(sx - self.px, sy - self.py) < 0.38:      # entrou no poço da escada
            self.moving = False
            self.phase = "descend"
            self.dt_ = 0.0
            self.play("fall")

    def sync_mode(self):
        if self.phase == "walk" and self.enemy is not None:
            self.waypoints = [] if self.manual() else self.find_path((self.px, self.py), (self.enemy["x"], self.enemy["y"]), self.enemy)
        elif self.phase == "stairs" and self.stairs:
            self.waypoints = [] if self.manual() else self.find_path((self.px, self.py), self.stairs)

    def set_mode(self, mode):
        self.cfg["mode"] = mode
        save_cfg(self.cfg)
        self.sync_mode()

    def cycle_mode(self):
        self.set_mode("auto" if self.manual() else "manual")
        if self.phase != "title":
            self.banner = "MODO MANUAL: você controla!" if self.manual() else "MODO AUTOMÁTICO"
            self.banner_t = 1.8

    def toggle_music(self):
        self.music_on = not self.music_on
        self.cfg["music"] = self.music_on
        save_cfg(self.cfg)

    def toggle_fs(self):
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass
        self.fs = not self.fs

    def open_settings(self):
        self.settings_open = True
        self.set_sel = 0

    def close_settings(self):
        self.settings_open = False
        save_cfg(self.cfg)
        self.sync_mode()

    def settings_change(self, row, d):
        c = self.cfg
        if row == "mode":
            self.set_mode("manual" if c["mode"] == "auto" else "auto")
        elif row == "speed":
            if d:
                c["speed"] = round(min(1.6, max(0.6, c["speed"] + 0.1 * d)), 2)
        elif row == "music":
            self.toggle_music()
        elif row == "music_vol":
            if d:
                c["music_vol"] = round(min(1.0, max(0.0, c["music_vol"] + 0.1 * d)), 2)
        elif row == "sfx":
            c["sfx"] = not c["sfx"]
            if c["sfx"]:
                self.play("ok")
        elif row == "shake":
            c["shake"] = not c["shake"]
        elif row == "fs":
            self.toggle_fs()
        elif row == "reset" and d == 0:
            self.cfg = dict(DEFAULT_CFG)
            self.music_on = self.cfg["music"]
            self.sync_mode()
        elif row == "menu" and d == 0:
            self.settings_open = False
            save_cfg(self.cfg)
            self.back_to_menu()
            return
        elif row == "back" and d == 0:
            self.close_settings()
            return
        save_cfg(self.cfg)

    def settings_key(self, key):
        if key == pygame.K_F11:
            self.toggle_fs()
            return
        if key in (pygame.K_ESCAPE, pygame.K_c):
            self.close_settings()
            return
        keys = self.set_keys()
        n = len(keys)
        row = keys[min(self.set_sel, n - 1)]
        if key in (pygame.K_UP, pygame.K_w):
            self.set_sel = (self.set_sel - 1) % n
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.set_sel = (self.set_sel + 1) % n
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.settings_change(row, -1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.settings_change(row, 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.settings_change(row, 0)

    def draw_badges(self, title=False):
        man = self.manual()
        if title:
            pills = [(pygame.Rect(14, 14, 214, 32), f"MOVER: {'MANUAL' if man else 'AUTOMÁTICO'}  [T]"),
                     (pygame.Rect(14, 52, 214, 32), "CONFIGURAÇÕES  [C]")]
        else:
            pills = [(pygame.Rect(W - 150, 134, 138, 32), f"{'MANUAL' if man else 'AUTO'}  [T]"),
                     (pygame.Rect(W - 150, 172, 138, 32), "CONFIG  [C]")]
        for i, (r, s) in enumerate(pills):
            base = (24, 84, 60) if (i == 0 and man) else (34, 40, 84)
            edge = (130, 240, 180) if (i == 0 and man) else (150, 165, 230)
            self.rrect(r, (*base, 225), 14, 2, (*edge, 255))
            self.text(s, 21, (240, 246, 255), r.center, shadow=False)

    def draw_settings(self):
        scr, c = self.screen, self.cfg
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((4, 6, 16, 195))
        scr.blit(dim, (0, 0))
        pw, ph = 720, 520
        panel = pygame.Rect((W - pw) // 2, 30, pw, ph)
        self.rrect(panel.inflate(14, 14), (120, 140, 220, 40), 34)
        self.rrect(panel, (14, 16, 38, 250), 28, 4, (150, 170, 230, 255))
        self.text("CONFIGURAÇÕES", 56, (255, 224, 120), (W // 2, panel.y + 44))
        gold, green, red = (255, 226, 130), (120, 240, 170), (230, 130, 130)

        def onoff(v, on="LIGADO", off="DESLIGADO"):
            return (on, green) if v else (off, red)

        rows = [
            ("mode", "Movimento do herói", "MANUAL (você controla)" if self.manual() else "AUTOMÁTICO", gold, None),
            ("speed", "Velocidade do herói", f"{int(round(c['speed'] * 100))}%", gold, (c["speed"] - 0.6) / 1.0),
            ("music", "Música  [N]", *onoff(self.music_on), None),
            ("music_vol", "Volume da música", f"{int(round(c['music_vol'] * 100))}%", gold, c["music_vol"]),
            ("sfx", "Efeitos sonoros", *onoff(c["sfx"]), None),
            ("shake", "Tremor de tela", *onoff(c["shake"]), None),
            ("fs", "Tela cheia  [F11]", *onoff(self.fs, "SIM", "NÃO"), None),
            ("reset", "Restaurar padrões", "ENTER", (200, 205, 235), None),
            ("menu", "Voltar ao menu", "ENTER", (200, 205, 235), None),
            ("back", "Voltar ao jogo" if self.phase != "title" else "Voltar", "ENTER", (200, 205, 235), None),
        ]
        rows = [r_ for r_ in rows if r_[0] in self.set_keys()]
        y0 = panel.y + 92
        for i, (key, label, val, col, frac) in enumerate(rows):
            r = pygame.Rect(panel.x + 24, y0 + i * 38, pw - 48, 34)
            sel = i == self.set_sel
            if sel:
                self.rrect(r, (70, 84, 160, 235), 14, 2, (190, 205, 255, 255))
            else:
                self.rrect(r, (24, 28, 56, 170), 14)
            self.text(label, 27, (255, 255, 255) if sel else (205, 210, 230), (r.x + 16, r.y + 8), center=False, shadow=False)
            cy = r.centery
            adj = key not in ("reset", "menu", "back")
            if frac is not None:
                bx = r.x + 350
                bar = pygame.Rect(bx, cy - 5, 160, 10)
                pygame.draw.rect(scr, (30, 30, 52), bar, border_radius=5)
                pygame.draw.rect(scr, col, (bar.x, bar.y, int(bar.w * max(0.0, min(1.0, frac))), bar.h), border_radius=5)
                pygame.draw.rect(scr, (210, 215, 240), bar, 1, border_radius=5)
                self.text(val, 25, col, (bar.right + 34, cy), center=False, shadow=False)
                lx, rx = bar.x - 16, bar.right + 16
            else:
                cx = r.x + 440
                self.text(val, 27, col, (cx, cy), shadow=False)
                half = self.font(27).size(val)[0] // 2
                lx, rx = cx - half - 18, cx + half + 18
            if sel and adj:
                pygame.draw.polygon(scr, (255, 232, 150), [(lx - 5, cy), (lx + 5, cy - 8), (lx + 5, cy + 8)])
                pygame.draw.polygon(scr, (255, 232, 150), [(rx + 5, cy), (rx - 5, cy - 8), (rx - 5, cy + 8)])
        self.text("↑ ↓ escolher     ← → mudar     ENTER alternar     C / ESC voltar", 21, (225, 230, 250),
                  (W // 2, panel.bottom - 22), shadow=False)

    # -------------------------------------------------------------- lógica
    def dmg_value(self):
        c = self.cards
        return 5 + self.floor + self.hero["damage"] + min(self.streak, 5) * (1 + c["foco"]) + 2 * c["espada"]

    def start_quiz(self):
        txt, ans, opts = make_question(self.floor)
        self.question, self.answer, self.options = txt, ans, opts
        self.phase = "quiz"
        self.sel = None

    def answer_q(self, idx):
        if self.phase != "quiz":
            return
        self.sel = idx
        self.correct = self.options[idx] == self.answer
        self.phase = "resolve"
        self.rt = 0.0
        self.applied = False

    def spawn(self, x, y, z, color, n, power=2.2):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1.0) * power
            self.particles.append({"x": x, "y": y, "z": z, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                                   "vz": random.uniform(1.5, 4.0), "life": random.uniform(0.6, 1.2),
                                   "c": color, "s": random.uniform(0.06, 0.13), "gz": z})

    def float_text(self, s, x, y, z, color):
        px, py = proj(x, y, z)
        self.floaters.append({"s": s, "x": px, "y": py, "life": 1.2, "c": color})

    def apply_result(self):
        e = self.enemy
        if self.correct:
            self.streak += 1
            crit = random.random() < self.hero["crit"]
            dmg = self.dmg_value() * (2 if crit else 1)
            e["hp"] = max(0, e["hp"] - dmg)
            e["flash"] = 1.0 if crit else 0.85
            if crit:
                self.flash_t = 0.22
            self.shake = 9 if crit else 7
            self.spawn(e["x"], e["y"], e["z"] + 0.5, (255, 255, 255), 18)
            self.float_text(f"-{dmg}", e["x"], e["y"], e["z"] + 1.4 * e["s"], (255, 230, 80))
            if crit:
                self.float_text("CRIT!", e["x"], e["y"], e["z"] + 1.9 * e["s"], (255, 255, 255))
                self.play("crit")
            else:
                self.play("hit")
            if self.streak >= 2:
                self.float_text(f"Sequência x{self.streak}!", self.px, self.py, self.pz + 1.8, (120, 255, 160))
            self.score += 18 + self.floor * 10 + (2 if crit else 0)
        else:
            self.streak = 0
            chance = min(0.2 * self.cards["trevo"], 0.8)
            if random.random() < chance:
                self.float_text("Sorte! Sem dano", self.px, self.py, self.pz + 1.4, (120, 255, 140))
                self.play("ok")
            else:
                self.mistakes += 1
                self.hp = max(0, self.hp - 1)
                self.pflash = 0.3
                self.shake = 9
                self.spawn(self.px, self.py, self.pz + 0.5, (230, 70, 70), 12)
                self.float_text("-1 ♥", self.px, self.py, self.pz + 1.4, (255, 90, 90))
                self.play("bad")
                if self.hp <= 0:
                    self.best = max(self.best, self.floor)
                    self.phase = "dead"
                    self.dtm = 0.0

    def treasure_room(self):
        self.give_card()

    def give_card(self):
        if getattr(self, "room_kind", "") == "elite":
            self.score += 120
        k = random.choice(list(CARDS))
        self.cards[k] += 1
        self.new_card = k
        if k == "coracao":
            self.maxhp = min(MAX_HEARTS, self.maxhp + 1)
        self.ct = 0.0
        self.enemy = None
        self.phase = "card"
        self.score += 80
        self.play("card")

    def respawn(self):
        self.phase = "title"
        self.banner, self.banner_t = "", 0.0

    # -------------------------------------------------------------- update
    def music_tick(self):
        """Toca a trilha em loop: começa quando fica pronta, abaixa no Game Over, N liga/desliga."""
        try:
            if self.music_sound is None:
                data = self._music_box.get("data")
                if data is None or not pygame.mixer.get_init():
                    return
                self.music_sound = pygame.mixer.Sound(buffer=data)
                self.music_channel = pygame.mixer.Channel(0)
                self.music_channel.set_volume(0.0)
                self.music_channel.play(self.music_sound, loops=-1)
                self.music_channel.set_volume(0.0)
            want = 0.0 if not self.music_on else (0.22 if self.phase == "gameover" else 0.55) * self.cfg["music_vol"]
            cur = self.music_channel.get_volume()
            self.music_channel.set_volume(cur + (want - cur) * 0.08)
        except Exception:
            pass

    def turn_foes(self, dt):
        """Os monstros giram suavemente para ficar de frente para o jogador."""
        for e in self.foes:
            if e["kind"] in NO_TURN:
                continue
            goal = math.atan2(self.py - e["y"], self.px - e["x"])
            cur = e.get("hd")
            if cur is None:
                e["hd"] = goal
                continue
            d = angle_diff(goal, cur)
            e["hd"] = (cur + d * (1.0 - math.exp(-7.0 * dt)) + math.pi) % math.tau - math.pi

    def update(self, dt):
        self.t += dt
        self.turn_foes(dt)
        self.banner_t = max(0, self.banner_t - dt)
        self.shake = max(0, self.shake - dt * 25)
        self.cam = (random.uniform(-1, 1) * self.shake, random.uniform(-1, 1) * self.shake) if (self.shake > 0.3 and self.cfg["shake"]) else (0, 0)

        if self.transition is not None:
            self.transition["time"] += dt
            if self.transition["time"] >= self.transition["duration"]:
                kind = self.transition["kind"]
                self.transition = None
                if kind == "dark":
                    self.advance_floor()
                elif kind == "red":
                    self.phase = "gameover"
            return

        if self.phase not in ("card", "stairs", "descend", "gameover", "title", "dead") and self.enemy is None:
            self.enemy = self.foes[self.cur] if self.foes and self.cur < len(self.foes) else (self.foes[-1] if self.foes else None)

        for fo in self.foes:
            fo["flash"] = max(0, fo["flash"] - dt)
        e = self.enemy
        self.pflash = max(0, self.pflash - dt)
        self.land_t = max(0.0, getattr(self, "land_t", 0.0) - dt)
        self.flash_t = max(0.0, getattr(self, "flash_t", 0.0) - dt)
        for p in self.particles:
            p["life"] -= dt
            p["vz"] -= 12 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["z"] += p["vz"] * dt
            gz = ground(p["x"], p["y"], self.duplo)
            if p["z"] < gz:
                p["z"] = gz
                p["vz"] *= -0.35
                p["vx"] *= 0.6
                p["vy"] *= 0.6
        self.particles = [p for p in self.particles if p["life"] > 0]
        for f in self.floaters:
            f["life"] -= dt
            f["y"] -= 38 * dt
        self.floaters = [f for f in self.floaters if f["life"] > 0]

        ph = self.phase
        self.moving = False
        self.steered = False
        hd0 = self.hd
        gnd = ground(self.px, self.py, self.duplo)
        if ph == "arrive":
            self.pt += dt
            k = min(1, self.pt / 0.7)
            self.pz = gnd + 5.0 * (1 - k) ** 2
            if k >= 1:
                self.pz = gnd
                self.shake = 5
                self.spawn(self.px, self.py, gnd + 0.1, (200, 200, 200), 8, 1.5)
                self.land_t = 0.3
                if not self.foes:
                    self.treasure_room()
                else:
                    self.waypoints = [] if self.manual() else self.find_path((self.px, self.py), (e["x"], e["y"]), e)
                    self.phase = "walk"
        else:
            self.pz += (gnd - self.pz) * min(1.0, dt * 15)

        if ph == "walk" and self.manual():
            self.walk_manual(dt)
        elif ph == "walk":
            self.moving = True
            if self.waypoints:
                wx, wy = self.waypoints[0]
                if math.hypot(wx - self.px, wy - self.py) < 0.12:
                    self.waypoints.pop(0)
                else:
                    self.steer(wx, wy, dt, 3.0)
            else:
                dist = math.hypot(e["x"] - self.px, e["y"] - self.py)
                if dist <= e["stop"]:
                    self.moving = False
                    self.start_quiz()
                else:   # reta final: desacelera chegando perto do inimigo
                    self.steer(e["x"], e["y"], dt, min(3.0, 1.1 + (dist - e["stop"]) * 3.0), limit=dist - (e["stop"] - 0.05))
            if self.phase == "walk" and self.stuck_t > 0.7:     # segurança: nunca trava a partida
                self.stuck_t = 0.0
                if self.waypoints:
                    self.px, self.py = self.waypoints.pop(0)
                else:
                    self.moving = False
                    self.start_quiz()
        elif ph == "resolve":
            self.rt += dt
            k = min(self.rt / 0.5, 1)
            amount = math.sin(k * math.pi) * 0.55
            if self.correct:
                self.lunge = amount
            else:
                self.elunge = amount
            if self.rt >= 0.25 and not self.applied:
                self.applied = True
                self.apply_result()
            if self.rt >= 1.1:
                self.lunge = self.elunge = 0
                if e["hp"] <= 0:
                    self.phase = "killed"
                    self.kt = 0.0
                    self.spawn(e["x"], e["y"], e["z"] + 0.6, ENEMY_COLOR[e["kind"]], 40, 3.2)
                    self.play("fall")
                elif self.hp <= 0:
                    self.best = max(self.best, self.floor)
                    self.phase = "dead"
                    self.dtm = 0.0
                else:
                    self.start_quiz()
        elif ph == "killed":
            self.kt += dt
            e["scale"] = max(0.0, 1 - self.kt / 0.5)
            if self.kt >= 0.9:
                e["scale"] = 0.0
                alive = [i for i, f_ in enumerate(self.foes) if f_["hp"] > 0]
                if alive:
                    self.cur = next((i for i in alive if i > self.cur), alive[0])
                    self.enemy = self.foes[self.cur]
                    self.waypoints = [] if self.manual() else self.find_path((self.px, self.py), (self.enemy["x"], self.enemy["y"]), self.enemy)
                    self.phase = "walk"
                else:
                    self.give_card()
        elif ph == "card":
            self.ct += dt
            if self.ct > 3.4:
                self.continue_after_card()
        elif ph == "stairs" and self.manual():
            self.stairs_manual(dt)
        elif ph == "stairs":
            self.moving = True
            sx, sy = self.waypoints[0] if self.waypoints else self.stairs
            dist = math.hypot(sx - self.px, sy - self.py)
            if self.waypoints and dist < 0.12:
                self.waypoints.pop(0)
            elif dist < 0.1 or (self.stuck_t > 0.7 and not self.waypoints and dist < 1.0):
                self.moving = False
                self.phase = "descend"
                self.dt_ = 0.0
                self.stuck_t = 0.0
                self.play("fall")
            else:
                self.steer(sx, sy, dt, 3.2)
                if self.stuck_t > 0.7:      # segurança: nunca trava a partida
                    self.stuck_t = 0.0
                    if self.waypoints:
                        self.px, self.py = self.waypoints.pop(0)
        elif ph == "descend":
            if self.stairs:      # puxa o herói para o centro do poço (importa no modo manual)
                k_ = min(1.0, dt * 8.0)
                self.px += (self.stairs[0] - self.px) * k_
                self.py += (self.stairs[1] - self.py) * k_
            self.dt_ += dt
            self.pscale = max(0.0, 1 - self.dt_ / 0.7)
            if self.dt_ >= 1.0:
                self.start_transition("dark")
        elif ph == "dead":
            self.dtm += dt
            if self.dtm >= 0.8:
                self.start_transition("red")

        if not self.steered:    # parado: encara o inimigo na conta, e a câmera na hora da carta
            self.spd += (0.0 - self.spd) * min(1.0, dt * 14.0)
            goal = None
            if ph in ("quiz", "resolve", "killed") and e is not None:
                goal = math.atan2(e["y"] - self.py, e["x"] - self.px)
            elif ph == "card":
                goal = HERO_FRONT
            if goal is not None:
                self.turn_to(goal, dt, 9.0)
        self.turn_v += (angle_diff(self.hd, hd0) / max(dt, 1e-3) - self.turn_v) * min(1.0, dt * 10.0)
        self.face = (math.cos(self.hd), math.sin(self.hd))
        if self.moving:
            self.dust_t -= dt
            if self.dust_t <= 0:
                self.dust_t = 0.16
                self.spawn_dust(self.px - self.face[0] * 0.15, self.py - self.face[1] * 0.15, gnd)

    def spawn_dust(self, x, y, z):
        for _ in range(2):
            self.particles.append({"x": x + random.uniform(-0.08, 0.08), "y": y + random.uniform(-0.08, 0.08), "z": z + 0.03,
                                   "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(-0.3, 0.3),
                                   "vz": random.uniform(0.6, 1.3), "life": random.uniform(0.35, 0.55),
                                   "c": (206, 198, 184), "s": random.uniform(0.06, 0.11), "gz": z})

    def continue_after_card(self):
        self.enemy = None
        self.stairs = self.lay["stairs"]
        self.waypoints = [] if self.manual() else self.find_path((self.px, self.py), self.stairs)
        self.phase = "stairs"

    # ------------------------------------------------------------- desenho
    def place(self, items, parts, x, y, z, s=1.0, flash=0.0, g=0.1):
        for (dx, dy, dz, w, d, h, c) in parts:
            if flash > 0:
                c = mix(c, min(1, flash * 3))
            X, Y, Z = x + dx * s, y + dy * s, z + dz * s
            items.append(((X + w * s / 2) + (Y + d * s / 2), Z, (X, Y, Z, w * s, d * s, h * s, c, True, g * s)))

    def decor_parts(self, kind):
        if kind == "crate":
            return [(0, 0, 0, 0.6, 0.6, 0.6, (160, 112, 64)), (-0.01, -0.01, 0.54, 0.62, 0.62, 0.06, (190, 140, 84)),
                    (-0.01, -0.01, 0, 0.62, 0.62, 0.05, (100, 70, 40)), (0.2, 0.6, 0.15, 0.2, 0.02, 0.3, (120, 84, 48)),
                    (0.6, 0.2, 0.15, 0.02, 0.2, 0.3, (120, 84, 48))]
        if kind == "barrel":
            return [(0.05, 0.05, 0, 0.5, 0.5, 0.7, (136, 92, 54)), (0.03, 0.03, 0.12, 0.54, 0.54, 0.07, (74, 74, 86)),
                    (0.03, 0.03, 0.46, 0.54, 0.54, 0.07, (74, 74, 86)), (0.08, 0.08, 0.70, 0.44, 0.44, 0.04, (170, 120, 70))]
        if kind == "chest":
            return [(0, 0, 0, 0.62, 0.42, 0.28, (140, 90, 48)), (-0.01, -0.01, 0.28, 0.64, 0.44, 0.14, (170, 112, 60)),
                    (0.26, 0.42, 0.18, 0.10, 0.03, 0.12, (245, 205, 70)), (0.62, 0.16, 0.18, 0.03, 0.10, 0.12, (245, 205, 70)),
                    (-0.01, -0.01, 0.0, 0.64, 0.44, 0.04, (80, 80, 92))]
        if kind == "pillar":
            return [(0.0, 0.0, 0, 0.5, 0.5, 0.16, (96, 94, 108)), (0.08, 0.08, 0.16, 0.34, 0.34, 1.35, (132, 128, 144)),
                    (0.0, 0.0, 1.51, 0.5, 0.5, 0.16, (110, 108, 122))]
        if kind == "rock":
            return [(0.0, 0.05, 0, 0.6, 0.5, 0.32, (104, 102, 114)), (0.1, 0.12, 0.32, 0.4, 0.3, 0.2, (122, 120, 132)),
                    (0.5, 0.0, 0, 0.14, 0.14, 0.12, (96, 94, 106))]
        return [(0.0, 0.1, 0, 0.3, 0.1, 0.07, (225, 225, 210)), (0.2, 0.3, 0, 0.1, 0.3, 0.07, (215, 215, 200)),
                (0.35, 0.0, 0, 0.12, 0.12, 0.12, (236, 236, 220)), (0.36, 0.01, 0.06, 0.03, 0.03, 0.04, DARK)]

    def draw_scene(self):
        scr = self.screen
        cam = self.cam
        scr.fill(self.pal[4])
        scr.blit(self.room, (int(cam[0]), int(cam[1])))
        duplo = self.duplo

        # escada de descida (poço de voxels)
        if self.stairs:
            sx, sy = self.stairs
            draw_stairwell(scr, sx, sy, ground(sx, sy, duplo), cam, self.t, self.pal, self.stair_glow)

        # tochas
        for i, (ax, v) in enumerate(self.torches):
            fl = 0.5 + 0.5 * math.sin(self.t * 9 + i * 2.1) * math.sin(self.t * 5.3 + i)
            base = ground(0.1, v, duplo) if ax == "x" else ground(v, 0.1, duplo)
            zb = base + 0.9
            fcol = (255, 170 + int(60 * fl), 40)
            wa = self.pal[2]
            wbox(scr, ax, v, -0.2, 0.4, zb - 0.1, 0.55, 0.04, shade(wa, 0.62), g=0.1, cam=cam)
            wbox(scr, ax, v, -0.05, 0.1, zb, 0.1, 0.14, (70, 56, 44), off=0.04, cam=cam)
            wbox(scr, ax, v, -0.1, 0.2, zb + 0.1, 0.25, 0.14, (96, 70, 44), off=0.02, g=0.1, cam=cam)
            wbox(scr, ax, v, -0.08, 0.16, zb + 0.35, 0.15 + 0.1 * fl, 0.12, fcol, off=0.03, cam=cam)
            wbox(scr, ax, v, -0.04, 0.08, zb + 0.37, 0.08 + 0.1 * fl, 0.06, (255, 238, 160), off=0.06, cam=cam, outline=False)
            gp = proj(0.05, v, zb + 0.5, cam) if ax == "x" else proj(v, 0.05, zb + 0.5, cam)
            g = self.glow[1 if fl > 0.5 else 0]
            scr.blit(g, (gp[0] - g.get_width() // 2, gp[1] - g.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)

        # sombras
        sh = pygame.Surface((W, H), pygame.SRCALPHA)
        shadows = [(self.px, self.py, ground(self.px, self.py, duplo), 0.34 * self.pscale)]
        for e in self.foes:
            if e["scale"] > 0:
                shadows.append((e["x"], e["y"], e["z"], foe_shadow_r(e["kind"]) * e["s"] * e["scale"]))
        for (x, y, z0, r) in shadows:
            z0 += 0.02
            for rk, ak in ((1.18, 46), (0.88, 74), (0.58, 104)):
                rr = r * rk
                pts = [proj(x - rr, y, z0, cam), proj(x, y - rr, z0, cam), proj(x + rr, y, z0, cam), proj(x, y + rr, z0, cam)]
                pygame.draw.polygon(sh, (8, 16, 34, ak), pts)
        for (x, y, kind) in self.decor:
            z0 = ground(x, y, duplo) + 0.02
            pts = [proj(x - 0.1, y - 0.1, z0, cam), proj(x + 0.7, y - 0.1, z0, cam),
                   proj(x + 0.7, y + 0.7, z0, cam), proj(x - 0.1, y + 0.7, z0, cam)]
            pygame.draw.polygon(sh, (0, 0, 0, 70), pts)
        for e in self.foes:     # anel pulsante no chão: dourado = elite, vermelho = chefe
            if e["scale"] > 0.3 and (e.get("elite") or e.get("boss")):
                pl = 0.5 + 0.5 * math.sin(self.t * 4 + e["x"])
                rr = foe_shadow_r(e["kind"]) * e["s"] * e["scale"] * (1.45 + 0.06 * pl)
                z0 = e["z"] + 0.03
                rc = (255, 70, 60) if e.get("boss") else (255, 196, 60)
                pts = [proj(e["x"] - rr, e["y"], z0, cam), proj(e["x"], e["y"] - rr, z0, cam),
                       proj(e["x"] + rr, e["y"], z0, cam), proj(e["x"], e["y"] + rr, z0, cam)]
                pygame.draw.polygon(sh, rc + (int(70 + 80 * pl),), pts, 3)
                pygame.draw.polygon(sh, rc + (int(20 + 25 * pl),), pts)
        scr.blit(sh, (0, 0))
        if self.pscale > 0.02:
            hid = self.hero["id"]
            if not hasattr(self, "hero_glows"):
                self.hero_glows = {}
            if hid not in self.hero_glows:
                self.hero_glows[hid] = make_glow(70, tuple(int(c * 0.30) for c in self.hero["color"]))
            gimg = self.hero_glows[hid]
            gp = proj(self.px, self.py, ground(self.px, self.py, duplo) + 0.05, cam)
            scr.blit(gimg, (gp[0] - 70, gp[1] - 70), special_flags=pygame.BLEND_RGB_ADD)

        # objetos ordenados (algoritmo do pintor)
        items = []
        objs = []   # caixas (x0, y0, x1, y1, chave mín., chave máx.) de tudo que o herói pode ficar na frente/atrás
        for (x, y, kind) in self.decor:
            n0 = len(items)
            self.place(items, self.decor_parts(kind), x, y, ground(x, y, duplo), g=0.15)
            if kind in SOLID_KINDS:
                ks = [it[0] for it in items[n0:]]
                objs.append((*self.decor_rect(x, y, kind), min(ks), max(ks)))
        for e in self.foes:
            if e["scale"] > 0.02:
                ep = parts_enemy(e["kind"], self.t)
                ex, ey = e["x"], e["y"]
                if e is self.enemy and self.elunge:
                    dx, dy = self.px - ex, self.py - ey
                    L = math.hypot(dx, dy) or 1
                    ex += dx / L * self.elunge
                    ey += dy / L * self.elunge
                fl = min(1.0, e["flash"])
                if fl > 0:
                    dxe, dye = ex - self.px, ey - self.py
                    Le = math.hypot(dxe, dye) or 1
                    ep = pose_parts(ep, 1 + 0.08 * fl, 1 + 0.08 * fl, 1 - 0.14 * fl, (dxe / Le * 0.2 * fl, dye / Le * 0.2 * fl))
                else:
                    ep = pose_parts(ep, 1.0, 1.0, 1 + 0.012 * math.sin(self.t * 3 + e["x"]))
                es = e["s"] * e["scale"]
                rr = 0.38 * es
                if e["kind"] in NO_TURN:
                    n0 = len(items)
                    self.place(items, ep, ex, ey, e["z"], es, e["flash"])
                    ks = [it[0] for it in items[n0:]]
                    objs.append((ex - rr, ey - rr, ex + rr, ey + rr, min(ks), max(ks)))
                else:
                    # gira o monstro para o jogador (mesmo desenho girado do herói)
                    ang_e = e.get("hd", foe_front(e["kind"])) - foe_front(e["kind"])
                    fkey = ex + ey
                    lo, hi = -1e9, 1e9
                    for (ox0, oy0, ox1, oy1, kmin, kmax) in objs:
                        in_front = ex - rr >= ox1 - 1e-6 or ey - rr >= oy1 - 1e-6
                        behind = ox0 >= ex + rr - 1e-6 or oy0 >= ey + rr - 1e-6
                        if in_front and not behind:
                            lo = max(lo, kmax)
                        elif behind and not in_front:
                            hi = min(hi, kmin)
                    if lo < hi:
                        fkey = min(max(fkey, lo + 0.002), hi - 0.002)
                    ckey = ("foe", id(e), int(math.floor(ang_e / 0.2)), e["kind"], bool(e.get("elite")))
                    items.append((fkey, e["z"], (ex, ey, e["z"], es, ang_e, ckey,
                                                 scale_parts(ep, es, e["flash"]), "foe", 0.0)))
                    objs.append((ex - rr, ey - rr, ex + rr, ey + rr, fkey, fkey))
        if self.pscale > 0.02:
            atk_ = min(1.0, self.lunge / 0.55) if (self.lunge and self.enemy is not None) else 0.0
            # o modelo é montado olhando para (+1,+1); girar = desenhar com `ang` (heading do herói)
            pp = parts_player(self.t, self.moving, self.hero["id"], (0.7071, 0.7071), atk_)
            px, py = self.px, self.py
            ph_ = self.phase
            sx = sy = sz = 1.0
            lean = [0.0, 0.0]       # inclinação no espaço do modelo (frente = (+1,+1))
            zoff = 0.0
            dxn = dyn = 0.0
            ang = self.hd - HERO_FRONT
            ca_, sa_ = math.cos(ang), math.sin(ang)
            if self.moving:
                bank = max(-1.0, min(1.0, self.turn_v / 10.0)) * 0.06     # inclina para dentro da curva
                lean = [0.0707 - bank * 0.7071, 0.0707 + bank * 0.7071]
            else:
                sz = 1 + 0.015 * math.sin(self.t * 3)
            if self.lunge and self.enemy is not None:
                dx, dy = self.enemy["x"] - px, self.enemy["y"] - py
                L = math.hypot(dx, dy) or 1
                dxn, dyn = dx / L, dy / L
                px += dxn * self.lunge
                py += dyn * self.lunge
                k = min(1.0, self.lunge / 0.55)
                lx, ly = dxn * 0.30 * k, dyn * 0.30 * k
                lean = [lx * ca_ + ly * sa_, -lx * sa_ + ly * ca_]       # mundo -> espaço do modelo
                sz, sx, sy = 1 - 0.06 * k, 1 + 0.04 * k, 1 + 0.04 * k
            if self.land_t > 0:
                k = self.land_t / 0.3
                sz, sx, sy = 1 - 0.24 * k, 1 + 0.14 * k, 1 + 0.14 * k
            if ph_ == "arrive":
                sz, sx, sy = 1.14, 0.94, 0.94
            if self.pflash > 0:
                px += math.sin(self.t * 80) * 0.04 * (self.pflash / 0.3)
                sz *= 0.95
            if ph_ == "killed" or (ph_ == "card" and self.ct < 1.6):
                zoff = abs(math.sin(self.t * 7)) * 0.12
            if ph_ in ("dead", "gameover"):
                k = min(1.0, self.dtm / 0.8)
                sz, sx, sy = max(0.12, 1 - 0.88 * k), 1 + 0.5 * k, 1 + 0.5 * k
            pp = pose_parts(pp, sx, sy, sz, tuple(lean))
            hs_ = self.pscale * HERO_SCALE
            # ordem de desenho em relação a caixas, barris, pilares... e inimigos: separa por eixo (nunca "atravessa" visualmente)
            hkey = px + py
            lo, hi = -1e9, 1e9
            hx0, hy0, hx1, hy1 = px - HERO_R, py - HERO_R, px + HERO_R, py + HERO_R
            for (ox0, oy0, ox1, oy1, kmin, kmax) in objs:
                in_front = hx0 >= ox1 - 1e-6 or hy0 >= oy1 - 1e-6
                behind = ox0 >= hx1 - 1e-6 or oy0 >= hy1 - 1e-6
                if in_front and not behind:
                    lo = max(lo, kmax)
                elif behind and not in_front:
                    hi = min(hi, kmin)
            if lo < hi:
                hkey = min(max(hkey, lo + 0.002), hi - 0.002)
            items.append((hkey, self.pz + zoff, (px, py, self.pz + zoff, hs_, ang, 0.0,
                                                  scale_parts(pp, hs_, self.pflash), "hero", 0.0)))
            if self.lunge > 0.01 and dxn:  # rastro do golpe
                kk0 = min(1.0, self.rt / 0.5)
                perp = (-dyn, dxn)
                for j in range(9):
                    kk = kk0 - j * 0.045
                    if kk <= 0:
                        continue
                    th = -1.2 + 2.4 * min(1.0, kk)
                    bx = px + dxn * 0.62 + perp[0] * math.sin(th) * 0.6
                    by = py + dyn * 0.62 + perp[1] * math.sin(th) * 0.6
                    bz = self.pz + 0.58 + math.cos(th) * 0.38
                    sq = 0.20 * (1 - j / 10)
                    col = mix(self.hero["color"], max(0.0, 0.8 - j * 0.08))
                    items.append((bx + by + sq, bz, (bx - sq / 2, by - sq / 2, bz, sq, sq, sq, col, False, 0.0)))
        for p in self.particles:
            s = p["s"]
            items.append((p["x"] + p["y"] + s, p["z"], (p["x"], p["y"], p["z"], s, s, s, p["c"], False, 0.0)))

        items.sort(key=lambda i: (round(i[0], 3), i[1]))
        for _, _, (x, y, z, w, d, h, c, o, g) in items:
            if g > 0 and (w < 2 * g and d < 2 * g and h < 2 * g):
                g = 0.0
            if o == "foe":     # w = escala, d = ângulo de giro, h = chave de cache (..., tipo, elite)
                # folha transparente + contorno; ordem guardada por faixa de ângulo (monstros grandes ficam leves)
                draw_foe(scr, c, x, y, z, d, cam, h, 0.008 * w, h[3], h[4], 2 if w >= 1.6 else 1)
                continue
            if o == "hero":    # w = escala, d = ângulo de giro
                draw_hero_rot(scr, c, x, y, z, d, cam, ("game", self.hero["id"], int(math.floor(d / 0.2)), self.moving, self.lunge > 0.01), 0.008 * w)
                continue
            draw_box(scr, x, y, z, w, d, h, c, cam, o, g)

        scr.blit(self.vig, (0, 0))

    # ------------------------------------------------------------ cartas UI
    def card_frame(self, rect, k, big=True):
        scr = self.screen
        nm, desc, col = CARDS[k]
        rad = 16 if big else 7
        pygame.draw.rect(scr, (22, 20, 38), rect, border_radius=rad)
        inner = rect.inflate(-10, -10) if big else rect.inflate(-4, -4)
        if inner.w < 4 or inner.h < 4:
            return
        gs = pygame.Surface(inner.size, pygame.SRCALPHA)
        for yy in range(inner.h):
            gs.fill(mix(shade(col, 0.60), yy / max(1, inner.h) * 0.9, (20, 18, 40)), (0, yy, inner.w, 1))
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=max(3, rad - 6))
        gs.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        scr.blit(gs, inner.topleft)
        pulse = 0.5 + 0.5 * math.sin(self.t * 4)
        pygame.draw.rect(scr, mix(col, 0.25 * pulse if big else 0.0), rect, 4 if big else 2, border_radius=rad)
        pygame.draw.rect(scr, mix(col, 0.55), inner, 1, border_radius=max(3, rad - 6))
        cx = rect.centerx
        if big:
            cy = rect.y + int(rect.h * 0.36)
            isz = int(rect.w * 0.52)
            pygame.draw.circle(scr, shade(col, 0.35), (cx, cy), int(isz * 0.78))
            pygame.draw.circle(scr, mix(col, 0.3), (cx, cy), int(isz * 0.78), 3)
            pygame.draw.circle(scr, shade(col, 0.55), (cx, cy), int(isz * 0.64), 1)
            scr.blit(self.icon(k, isz), (cx - isz // 2, cy - isz // 2 + int(3 * math.sin(self.t * 3))))
            for (sx, sy) in ((rect.x + 14, rect.y + 14), (rect.right - 14, rect.y + 14),
                             (rect.x + 14, rect.bottom - 14), (rect.right - 14, rect.bottom - 14)):
                pygame.draw.polygon(scr, (245, 205, 90), [(sx, sy - 6), (sx + 6, sy), (sx, sy + 6), (sx - 6, sy)])
        else:
            isz = int(rect.w * 0.66)
            scr.blit(self.icon(k, isz), (cx - isz // 2, rect.centery - isz // 2))

    def draw_card(self):
        scr = self.screen
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        scr.blit(ov, (0, 0))
        k = self.new_card
        nm, desc, col = CARDS[k]
        grow = min(1, self.ct / 0.35)
        w, h = int(250 * grow), int(340 * grow)
        r = pygame.Rect(0, 0, max(40, w), max(56, h))
        r.center = (W // 2, H // 2 - 10)
        if grow < 1:
            self.card_frame(r, k, big=True)
            return
        self.card_frame(r, k, big=True)
        rb = pygame.Rect(r.x + 16, r.y + int(r.h * 0.66), r.w - 32, 34)
        pygame.draw.rect(scr, shade(col, 0.45), rb, border_radius=8)
        pygame.draw.rect(scr, mix(col, 0.4), rb, 2, border_radius=8)
        self.text(nm, 30, (255, 255, 255), rb.center)
        f = self.font(23)
        for i, ln in enumerate(wrap(f, desc, r.w - 36)):
            self.text(ln, 23, (225, 230, 245), (r.centerx, rb.bottom + 20 + i * 22))
        self.text("NOVA CARTA!", 40, (255, 235, 150), (W // 2, r.y - 28))
        self.text(f"Você tem x{self.cards[k]}", 24, (160, 255, 190), (W // 2, r.bottom + 22))
        self.text("ENTER para continuar", 24, (225, 225, 240), (W // 2, r.bottom + 48))

    def bar(self, x, y, w, h, frac, color, label):
        pygame.draw.rect(self.screen, (20, 20, 30), (x - 2, y - 2, w + 4, h + 4), border_radius=6)
        pygame.draw.rect(self.screen, (60, 30, 30), (x, y, w, h), border_radius=5)
        if frac > 0:
            pygame.draw.rect(self.screen, color, (x, y, int(w * frac), h), border_radius=5)
        self.text(label, 24, (255, 255, 255), (x + w // 2, y + h // 2))

    def heart_img(self, full):
        key = ("heart", full)
        if key not in self.icons:
            im = self.icon("coracao", 30).copy()
            if not full:
                im.fill((60, 60, 72, 255), special_flags=pygame.BLEND_RGB_MULT)
                im.set_alpha(150)
            self.icons[key] = im
        return self.icons[key]

    def hp_color(self, frac):
        if frac > 0.5:
            return mix((240, 210, 60), (frac - 0.5) * 2, (90, 214, 104))
        return mix((226, 64, 64), frac * 2, (240, 210, 60))

    def draw_hud(self):
        scr, t = self.screen, self.t
        boss = self.enemy is not None and self.enemy.get("boss")
        self.rrect(pygame.Rect(12, 10, W - 24, 70), (12, 14, 30, 214), 18, 2, (110, 138, 176, 255))
        self.rrect(pygame.Rect(16, 13, W - 32, 22), (255, 255, 255, 12), 14)

        # vida
        beat = 1 + (0.12 * abs(math.sin(t * 6)) if self.hp == 1 else 0)
        for i in range(self.maxhp):
            im = self.heart_img(i < self.hp)
            if i < self.hp and beat != 1:
                sz = int(30 * beat)
                im = pygame.transform.smoothscale(im, (sz, sz))
            scr.blit(im, (26 + i * 32 - (im.get_width() - 30) // 2, 16 - (im.get_height() - 30) // 2))
        nxt = (self.floor // HEAL_EVERY + 1) * HEAL_EVERY
        self.text(f"CURA NO ANDAR {nxt}", 17, (150, 255, 180), (28, 59), center=False, shadow=False)

        # pontos
        self.text("PONTOS", 17, (190, 196, 220), (228, 18), center=False, shadow=False)
        self.text(str(self.score), 34, (255, 224, 120), (228, 36), center=False)

        # andar
        badge = pygame.Rect(0, 0, 210, 54)
        badge.center = (W // 2 - 30, 44)
        bc = (255, 110, 90) if boss else (255, 214, 110)
        self.rrect(badge.inflate(10, 10), (*bc, 34), 22)
        self.rrect(badge, (22, 18, 38, 245), 18, 3, (*bc, 255))
        self.text(f"ANDAR {self.floor}", 40, mix(bc, 0.35), badge.center)

        # inimigo
        e = self.enemy
        if e is not None and (e["scale"] > 0.02 or self.phase in ("quiz", "resolve", "walk", "arrive")):
            name = ("ELITE " if e.get("elite") else "") + ENEMY_NAMES.get(e["kind"], e["kind"])
            hx, hw = W - 300, 270
            frac = max(0.0, e["hp"] / max(1, e["maxhp"]))
            self.text(name, 22, (255, 120, 110) if e.get("boss") else ((255, 180, 80) if e.get("elite") else (255, 240, 220)), (hx, 15), center=False)
            bar = pygame.Rect(hx, 38, hw, 22)
            pygame.draw.rect(scr, (16, 12, 22), bar.inflate(4, 4), border_radius=12)
            pygame.draw.rect(scr, (66, 36, 44), bar, border_radius=10)
            if frac > 0:
                fw = max(12, int(hw * frac))
                pygame.draw.rect(scr, self.hp_color(frac), (bar.x, bar.y, fw, bar.h), border_radius=10)
                pygame.draw.rect(scr, (255, 255, 255, 60), (bar.x + 5, bar.y + 3, max(2, fw - 10), 4), border_radius=3)
                pygame.draw.rect(scr, (255, 255, 255), (bar.x, bar.y, fw, bar.h), 1, border_radius=10)
            self.text(f"{e['hp']}/{e['maxhp']}", 20, (255, 255, 255), bar.center)

        # cartas
        owned = [(k, n) for k, n in self.cards.items() if n]
        if owned:
            ph = 38 + len(owned) * 34
            panel = pygame.Rect(16, 90, 236, ph)
            self.rrect(panel, (12, 14, 28, 205), 16, 2, (126, 144, 178, 255))
            self.text("CARTAS", 20, (220, 222, 236), (panel.x + 16, panel.y + 10), center=False)
            for row, (k, n) in enumerate(owned):
                y = panel.y + 36 + row * 34
                self.card_frame(pygame.Rect(panel.x + 12, y, 28, 28), k, big=False)
                self.text(CARDS[k][0], 20, CARDS[k][2], (panel.x + 50, y + 4), center=False)
                im = self.font(24).render(f"x{n}", True, (255, 255, 255))
                scr.blit(im, (panel.right - 14 - im.get_width(), y + 5))

        if self.banner_t > 0:
            a = min(1.0, self.banner_t)
            sur = self.font(46).render(self.banner, True, (255, 255, 255))
            pill = pygame.Rect(0, 0, sur.get_width() + 50, 58)
            pill.center = (W // 2, 120)
            self.rrect(pill, (90, 16, 24, int(210 * a)), 28, 3, (255, 130, 100, int(255 * a)))
            self.text(self.banner, 46, mix((255, 150, 110), 0.25 * (1 - a)), pill.center)
        for f in self.floaters:
            self.text(f["s"], 40, f["c"], (f["x"], f["y"]))

    # ---------------------------------------------------- botão: voltar ao menu
    def menu_btn_rect(self):
        return pygame.Rect(W - 150, 88, 138, 40)

    def draw_menu_button(self):
        r = self.menu_btn_rect()
        hover = False
        base = (176, 60, 70) if hover else (96, 34, 52)
        edge = (255, 170, 150) if hover else (230, 120, 120)
        self.rrect(r.inflate(8, 8), (*edge, 46 if hover else 24), 20)
        self.rrect(r, (*base, 238), 16, 3, (*edge, 255))
        # ícone de casinha
        cx, cy = r.x + 26, r.centery
        pygame.draw.polygon(self.screen, (255, 236, 220), [(cx - 11, cy), (cx, cy - 11), (cx + 11, cy)])
        pygame.draw.rect(self.screen, (255, 236, 220), (cx - 7, cy, 14, 10))
        pygame.draw.rect(self.screen, base, (cx - 2, cy + 3, 4, 7))
        self.text("MENU  [M]", 22, (255, 244, 232), (r.x + 86, r.centery))

    def back_to_menu(self):
        """Volta para a tela de título (a próxima partida começa do zero ao apertar ENTER)."""
        self.transition = None
        self.phase = "title"
        self.banner, self.banner_t = "", 0.0
        self.particles.clear()
        self.floaters.clear()
        self.flash_t = 0

    def draw_panel(self):
        scr, t = self.screen, self.t
        top = H - 165
        pan = pygame.Surface((W, 165), pygame.SRCALPHA)
        for yy in range(165):
            pygame.draw.line(pan, (10 + yy // 14, 10 + yy // 16, 26 + yy // 9, 228), (0, yy), (W, yy))
        scr.blit(pan, (0, top))
        pygame.draw.line(scr, (130, 130, 200), (0, top), (W, top), 2)
        pygame.draw.line(scr, (50, 50, 96), (0, top + 3), (W, top + 3), 1)
        if self.phase in ("quiz", "resolve"):
            self.rrect(pygame.Rect(18, top + 10, 230, 34), (60, 46, 10, 220), 17, 2, (255, 214, 100, 255))
            self.text(f"Dano ao acertar: {self.dmg_value()}", 23, (255, 232, 130), (133, top + 27))
            sq = pygame.Rect(W - 248, top + 10, 230, 34)
            self.rrect(sq, (10, 54, 34, 220), 17, 2, (120, 240, 170, 255))
            self.text("Seq.", 21, (150, 255, 190), (sq.x + 34, sq.centery), shadow=False)
            for i in range(5):
                on = i < min(self.streak, 5)
                c = (255, 190, 60) if on else (34, 70, 54)
                pygame.draw.circle(scr, c, (sq.x + 76 + i * 22, sq.centery), 7)
                pygame.draw.circle(scr, (10, 30, 20), (sq.x + 76 + i * 22, sq.centery), 7, 1)
            qs = self.font(70).render(self.question, True, (255, 255, 255))
            qr = pygame.Rect(0, 0, qs.get_width() + 60, 62)
            qr.center = (W // 2, top + 40)
            self.rrect(qr, (30, 30, 70, 200), 24, 2, (150, 156, 230, 255))
            self.text(self.question, 66, (255, 255, 255), qr.center)
            for i in range(2):
                x = W // 2 - 290 + i * 310
                r = pygame.Rect(x, top + 80, 270, 72)
                col, edge = (58, 66, 128), (214, 220, 255)
                if self.phase == "resolve":
                    if self.options[i] == self.answer:
                        col, edge = (36, 150, 76), (170, 255, 200)
                    elif i == self.sel:
                        col, edge = (176, 50, 54), (255, 170, 170)
                    else:
                        col, edge = (36, 38, 66), (110, 114, 150)
                else:
                    edge = mix(edge, 0.0 + 0.0)
                self.rrect(r.inflate(0, 6).move(0, 4), (0, 0, 0, 90), 18)
                self.rrect(r, (*col, 255), 18)
                self.rrect(pygame.Rect(r.x + 6, r.y + 5, r.w - 12, r.h // 2 - 4), (255, 255, 255, 30), 12)
                pygame.draw.rect(scr, edge, r, 3, border_radius=18)
                chip = (r.x + 36, r.centery)
                pygame.draw.circle(scr, shade(col, 0.5), chip, 22)
                pygame.draw.circle(scr, edge, chip, 22, 2)
                self.text(str(i + 1), 34, (255, 255, 255), chip)
                self.text(str(self.options[i]), 60, (255, 255, 255), (r.centerx + 22, r.centery))
        else:
            msg = {"arrive": "Descendo para a masmorra...", "walk": "O herói avança sozinho até o inimigo...",
                   "killed": "Inimigo derrotado!", "stairs": "Indo para a escada...",
                   "descend": "Descendo mais fundo...", "dead": "O herói desmaiou..."}.get(self.phase, "")
            if self.manual():
                msg = {"walk": "Mova o herói até um inimigo  (WASD / setas)", "stairs": "Vá até a escada para descer!"}.get(self.phase, msg)
            dots = "." * (int(t * 3) % 4)
            self.text(msg.rstrip(".") + (dots if msg.endswith("...") else ""), 36, (230, 230, 245), (W // 2, top + 82))

    # ---------------------------------------------------------- MENU / TÍTULO
    def build_title_art(self):
        rng = random.Random(7)
        # céu
        sky = pygame.Surface((W, H))
        for y in range(H):
            sky.fill(mix((8, 10, 30), (y / H) ** 1.5, (104, 54, 98)), (0, y, W, 1))
        gl = make_glow(380, (86, 40, 44))
        sky.blit(gl, (W // 2 - 380, 470 - 380), special_flags=pygame.BLEND_RGB_ADD)
        mg = make_glow(150, (60, 54, 40))
        sky.blit(mg, (W - 170 - 150, 110 - 150), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(sky, (252, 240, 208), (W - 170, 110), 44)
        for cx, cy, cr in ((-14, -8, 9), (10, 12, 7), (-6, 18, 5), (16, -14, 4)):
            pygame.draw.circle(sky, (226, 212, 180), (W - 170 + cx, 110 + cy), cr)
        self.title_sky = sky
        self.title_stars = [(rng.randint(0, W), rng.randint(0, 330), rng.choice([1, 1, 2, 2, 3]), rng.uniform(0, 6.28)) for _ in range(90)]

        # paisagem (transparente)
        land = pygame.Surface((W, H), pygame.SRCALPHA)

        def ridge(base, colour, amp, ph):
            pts = [(0, H)]
            for x in range(0, W + 20, 20):
                y = base - (amp * 0.55 * math.sin(x * 0.011 + ph) + amp * 0.3 * math.sin(x * 0.027 + ph * 2) + amp * 0.15 * math.sin(x * 0.05 + ph * 3))
                pts.append((x, y))
            pts.append((W, H))
            pygame.draw.polygon(land, colour, pts)

        ridge(H - 215, (42, 30, 70), 110, 1.0)
        ridge(H - 150, (30, 26, 56), 90, 2.3)
        self.title_windows = []

        def tower(x, w, h, base, col):
            top = base - h
            pygame.draw.rect(land, col, (x, top, w, h + 40))
            pygame.draw.rect(land, shade(col, 1.25), (x + w - 8, top, 8, h + 40))
            for i in range(0, w, 14):
                pygame.draw.rect(land, col, (x + i, top - 10, 9, 10))
            pygame.draw.polygon(land, (66, 34, 76), [(x - 6, top - 10), (x + w + 6, top - 10), (x + w // 2, top - 62)])
            pygame.draw.line(land, (200, 190, 220), (x + w // 2, top - 62), (x + w // 2, top - 82), 2)
            pygame.draw.polygon(land, (200, 50, 70), [(x + w // 2, top - 82), (x + w // 2 + 16, top - 76), (x + w // 2, top - 70)])
            for wy in range(top + 24, base - 10, 44):
                self.title_windows.append((x + w // 2 - 4, wy))

        tower(40, 70, 200, H - 120, (36, 32, 62))
        tower(124, 46, 130, H - 112, (32, 28, 56))
        tower(W - 120, 76, 250, H - 112, (36, 32, 62))
        tower(W - 186, 44, 140, H - 108, (32, 28, 56))
        ridge(H - 80, (16, 22, 34), 60, 4.1)
        for x in range(-10, W + 20, 30):
            h = rng.randint(46, 96)
            b = H + 6
            for k in range(3):
                pygame.draw.polygon(land, (9, 16, 20), [(x - 20 + k * 3, b - k * h // 3), (x + 20 - k * 3, b - k * h // 3), (x, b - h // 2 - k * h // 3)])
        self.title_land = land

        # título em degradê com contorno (cache)
        def grad_text(s, size, c1, c2, outline=4, with_base=False):
            f = self.title_font(size)
            while size > 24 and f.size(s)[0] > W - 80:      # fontes largas: ajusta para caber na tela
                size -= 4
                f = self.title_font(size)
            txt = f.render(s, True, (255, 255, 255))
            w, h = txt.get_size()
            out = pygame.Surface((w + outline * 2 + 8, h + outline * 2 + 14), pygame.SRCALPHA)
            ink = f.render(s, True, (24, 12, 40))
            for ox in range(-outline, outline + 1):
                for oy in range(-outline, outline + 1):
                    if ox * ox + oy * oy <= outline * outline + 1:
                        out.blit(ink, (outline + 4 + ox, outline + 4 + oy))
            out.blit(f.render(s, True, (10, 6, 20)), (outline + 4, outline + 10))
            g = pygame.Surface((w, h), pygame.SRCALPHA)
            for yy in range(h):
                g.fill(mix(c1, yy / max(1, h - 1), c2), (0, yy, w, 1))
            g.blit(txt, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            out.blit(g, (outline + 4, outline + 4))
            if with_base:
                return out, outline + 4 + txt.get_bounding_rect().bottom
            return out


        def red_cap(ch, size, outline=6):
            """Letra capitular no estilo do 'D' do logo de D&D: vermelha em degradê, contorno preto grosso,
            brilho de metal na borda de cima e sombra projetada. Devolve (imagem recortada, linha de base)."""
            f = self.title_font(size)
            txt = f.render(ch, True, (255, 255, 255))
            w, h = txt.get_size()
            bb = txt.get_bounding_rect()
            pad = outline + 12
            out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
            ink = f.render(ch, True, (22, 4, 10))
            for ox in range(-outline, outline + 1):
                for oy in range(-outline, outline + 1):
                    if ox * ox + oy * oy <= outline * outline + 1:
                        out.blit(ink, (pad + ox, pad + oy))
            out.blit(ink, (pad, pad + outline + 4))                                  # sombra
            out.blit(f.render(ch, True, (255, 228, 216)), (pad - 1, pad - 2))        # brilho de metal
            g = pygame.Surface((w, h), pygame.SRCALPHA)
            span = max(1, bb.height - 1)
            for yy in range(h):
                k = min(1.0, max(0.0, (yy - bb.top) / span))
                col = (mix((255, 118, 100), k / 0.5, (212, 30, 46)) if k < 0.5
                       else mix((212, 30, 46), (k - 0.5) / 0.5, (116, 8, 26)))
                g.fill(col, (0, yy, w, 1))
            g.blit(txt, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            out.blit(g, (pad, pad))
            r = out.get_bounding_rect()
            return out.subsurface(r).copy(), pad + bb.bottom - r.top

        def make_title1(word, size):
            """'M' grande e vermelho (como o D do logo) + resto da palavra, com um rabo em lâmina por baixo."""
            while True:
                m_img, m_gb = red_cap(word[0], int(size * 1.34))
                r_img, r_gb = grad_text(word[1:], size, (255, 244, 170), (240, 140, 40), with_base=True)
                rc = r_img.get_bounding_rect()
                r_gb -= rc.top
                r_img = r_img.subsurface(rc).copy()
                gap = -int(size * 0.05)
                m_w = m_img.get_width()
                tw = m_w + gap + r_img.get_width()
                if (m_gb <= 90 and tw <= W - 70) or size <= 40:
                    break
                size -= 4
            cv = pygame.Surface((tw, m_gb + 32), pygame.SRCALPHA)
            x0, x1 = int(m_w * 0.35), tw - 3
            up, lo, up2, lo2 = [], [], [], []
            for i in range(41):                                                      # rabo: lâmina que afina até a ponta
                u = i / 40
                x = x0 + (x1 - x0) * u
                yc = m_gb + 9 + 4 * math.sin(u * math.pi)
                th = 15 * (1 - u) ** 1.2
                up.append((x, yc - th / 2))
                lo.append((x, yc + th / 2))
                up2.append((x, yc - th / 2 - 3))
                lo2.append((x, yc + th / 2 + 3))
            pygame.draw.polygon(cv, (22, 4, 10), up2 + lo2[::-1])
            pygame.draw.polygon(cv, (196, 28, 46), up + lo[::-1])
            pygame.draw.lines(cv, (255, 150, 130), False, up[:34], 1)
            cv.blit(r_img, (m_w + gap, m_gb - r_gb))
            cv.blit(m_img, (0, 0))
            return cv, m_gb

        self.title_l1, self.title_l1_base = make_title1("MASMORRA", 118)
        self.title_l2 = grad_text("DOS NÚMEROS", 62, (190, 235, 255), (110, 140, 255), 3)
        self.title_syms = []
        for i, sym in enumerate("+-×÷=?+×÷-+×÷=?"):
            self.title_syms.append((sym, rng.randint(20, W - 20), rng.uniform(10, 28), rng.randint(34, 70), rng.random()))
        self.title_sym_img = {}
        for sym, _, _, size, _ in self.title_syms:
            if (sym, size) not in self.title_sym_img:
                im = self.font(size).render(sym, True, (190, 180, 255)).convert_alpha()
                im.fill((255, 255, 255, 46), special_flags=pygame.BLEND_RGBA_MULT)
                self.title_sym_img[(sym, size)] = im
        self.title_glows = {h["id"]: make_glow(96, tuple(int(c * 0.42) for c in h["color"])) for h in HEROES}

    def rrect(self, rect, color, radius=14, border=0, bcolor=None):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
        if border and bcolor:
            pygame.draw.rect(s, bcolor, s.get_rect(), border, border_radius=radius)
        self.screen.blit(s, rect.topleft)

    def draw_title(self):
        if not hasattr(self, "title_sky"):
            self.build_title_art()
        scr, t = self.screen, self.t
        scr.blit(self.title_sky, (0, 0))
        for (x, y, r, ph) in self.title_stars:
            v = int(120 + 135 * (0.5 + 0.5 * math.sin(t * 2 + ph)))
            pygame.draw.circle(scr, (v, v, min(255, v + 15)), (x, y), r)
        for sym, x0, spd, size, ph in self.title_syms:
            y = (H + 60) - ((t * spd + ph * (H + 120)) % (H + 120))
            x = x0 + 18 * math.sin(t * 0.7 + ph * 6)
            im = self.title_sym_img[(sym, size)]
            scr.blit(pygame.transform.rotate(im, 12 * math.sin(t * 0.8 + ph * 9)), (x, y))
        scr.blit(self.title_land, (0, 0))
        for i, (wx, wy) in enumerate(self.title_windows):
            fl = 0.75 + 0.25 * math.sin(t * 6 + i * 1.7)
            pygame.draw.rect(scr, (int(255 * fl), int(190 * fl), 70), (wx, wy, 8, 14), border_radius=3)
        for i in range(36):  # brasas
            x = (i * 97 + math.sin(t * 0.8 + i) * 30 + t * (6 + i % 5 * 3)) % W
            y = H - ((t * (22 + i % 7 * 7) + i * 53) % (H + 20))
            k = 0.5 + 0.5 * math.sin(t * 5 + i)
            pygame.draw.circle(scr, (255, int(140 + 90 * k), 60), (int(x), int(y)), 1 + i % 3 // 2)

        # título
        bob = math.sin(t * 1.6) * 4
        scr.blit(self.title_l1, (W // 2 - self.title_l1.get_width() // 2, 96 + int(bob) - self.title_l1_base))
        scr.blit(self.title_l2, self.title_l2.get_rect(center=(W // 2, 130 + bob * 0.6)))
        if self.best > 1:
            self.rrect(pygame.Rect(W - 190, 14, 176, 34), (12, 12, 28, 190), 17, 2, (240, 200, 90))
            self.text(f"Recorde: andar {self.best}", 24, (255, 232, 150), (W - 102, 31))

        # cartas dos heróis
        nh = len(HEROES)
        gap = 22 if nh <= 4 else 12
        cw, ch = min(190, (W - 112 - gap * (nh - 1)) // nh), 312     # as cartas encolhem para caber todos os heróis
        x0 = (W - (nh * cw + (nh - 1) * gap)) // 2
        crit_max = max(h["crit"] for h in HEROES)
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        for idx, hero in enumerate(HEROES):
            sel = idx == self.hero_index
            col = hero["color"]
            r = pygame.Rect(x0 + idx * (cw + gap), 178 - (16 if sel else 0), cw, ch)
            if sel:
                for k in range(3, 0, -1):
                    self.rrect(r.inflate(k * 8, k * 8), (*col, 26 * (4 - k)), 22 + k * 3)
            self.rrect(r, (14, 14, 34, 232 if sel else 190), 20)
            inner = r.inflate(-8, -8)
            hdr = pygame.Rect(inner.x, inner.y, inner.w, 200)
            self.rrect(hdr, (*shade(col, 0.30), 255 if sel else 170), 16)
            g = self.title_glows[hero["id"]]
            scr.blit(g, (r.centerx - 96, r.y + 112 - 96), special_flags=pygame.BLEND_RGB_ADD) if sel else None
            # pedestal
            pcx, pcy = r.centerx, r.y + 172
            pygame.draw.ellipse(scr, (10, 12, 26), (pcx - 66, pcy + 4, 132, 36))
            draw_pedestal(scr, pcx, pcy + 6, 1.55, col, pulse if sel else 0.0)
            self.draw_hero_iso(hero["id"], pcx, pcy + 6, 2.7, sel)
            pygame.draw.rect(scr, mix(col, 0.3 * pulse) if sel else shade(col, 0.5), r, 4 if sel else 2, border_radius=20)
            if not sel:
                self.rrect(r, (0, 0, 8, 80), 20)
            # textos
            ty = r.y + 214
            small = cw < 180
            self.text(hero["name"], 30 if small else 34, (255, 255, 255) if sel else (190, 192, 210), (r.centerx, ty))
            self.text(hero["title"], 18 if small else 21, col if sel else shade(col, 0.7), (r.centerx, ty + 24))
            for j, (lab, frac) in enumerate((("VIDA", hero["hp"] / 6), ("CRÍT", hero["crit"] / crit_max), ("DANO", (hero["damage"] + 1) / 4))):
                by = ty + 44 + j * 17
                self.text(lab, 17, (200, 205, 230), (r.x + 16, by), center=False, shadow=False)
                bar = pygame.Rect(r.x + 64, by + 3, cw - 84, 9)
                pygame.draw.rect(scr, (30, 30, 52), bar, border_radius=5)
                pygame.draw.rect(scr, col if sel else shade(col, 0.6), (bar.x, bar.y, int(bar.w * min(1, frac)), bar.h), border_radius=5)

        # setas
        for d in (-1, 1):
            ax = 30 if d < 0 else W - 30
            off = int(5 * math.sin(t * 5)) * d
            pygame.draw.polygon(scr, (255, 232, 150), [(ax + off + d * 12, 330 - 18), (ax + off + d * 12, 330 + 18), (ax + off - d * 12, 330)])

        # botão iniciar
        sc = 1 + 0.04 * math.sin(t * 4)
        bw, bh = int(400 * sc), int(58 * sc)
        br = pygame.Rect(0, 0, bw, bh)
        br.center = (W // 2, 532)
        self.rrect(br.inflate(14, 14), (255, 200, 70, int(40 + 40 * pulse)), 34)
        for yy in range(br.h):
            pygame.draw.line(scr, mix((255, 214, 90), yy / br.h, (230, 120, 40)), (br.x + 20, br.y + yy), (br.right - 20, br.y + yy))
        pygame.draw.rect(scr, (255, 214, 90), (br.x, br.y, 40, br.h), border_top_left_radius=29, border_bottom_left_radius=29)
        pygame.draw.rect(scr, (230, 120, 40), (br.right - 40, br.y, 40, br.h), border_top_right_radius=29, border_bottom_right_radius=29)
        pygame.draw.rect(scr, (255, 248, 210), br, 3, border_radius=29)
        pygame.draw.polygon(scr, (60, 28, 10), [(br.x + 34, br.centery - 10), (br.x + 34, br.centery + 10), (br.x + 52, br.centery)])
        self.text("COMEÇAR AVENTURA", 38, (60, 28, 10), (br.centerx + 10, br.centery), shadow=False)
        self.rrect(pygame.Rect(W // 2 - 440, 580, 880, 34), (8, 8, 22, 170), 17)
        self.text("← →  herói     ENTER  jogar     C  configurações     T  auto/manual     F11  tela cheia     ESC  sair", 20, (200, 210, 235), (W // 2, 597), shadow=False)

    def draw_hero_iso(self, hid, cx, cy, s, active):
        parts = parts_player(self.t, active, hid, (0.7071, 0.7071), 0.0)
        draw_parts_iso(self.screen, parts, cx, cy, s, soft=True, key=hid)

    def draw_transition(self):
        if self.transition is None:
            return
        t = min(1.0, self.transition["time"] / self.transition["duration"])
        cover = pygame.Surface((W, H), pygame.SRCALPHA)
        color = (10, 12, 18) if self.transition["kind"] == "dark" else (150, 18, 18)
        for i in range(16):
            radius = 100 + i * 54 + t * 380
            cx = W // 2 + (i % 3 - 1) * 110
            cy = H + i * 18 - (t * (H + 140))
            alpha = 130 + int(t * 100)
            pygame.draw.circle(cover, (color[0], color[1], color[2], alpha), (cx, int(cy)), int(radius))
        self.screen.blit(cover, (0, 0))

    def draw(self):
        self.draw_main()
        if self.settings_open:
            self.draw_settings()

    def draw_main(self):
        if self.phase == "title":
            self.draw_title()
            self.draw_badges(True)
            self.draw_transition()
            return
        self.draw_scene()
        ph = self.phase
        self.draw_hud()
        self.draw_panel()
        if ph == "card":
            self.draw_card()
        if ph == "descend":
            a = int(255 * min(1, max(0, (self.dt_ - 0.4) / 0.6)))
            ov = pygame.Surface((W, H))
            ov.fill((0, 0, 0))
            ov.set_alpha(a)
            self.screen.blit(ov, (0, 0))
        if ph == "gameover":
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((20, 0, 0, 190))
            self.screen.blit(ov, (0, 0))
            box = pygame.Rect(0, 0, 560, 360)
            box.center = (W // 2, H // 2)
            pulse = 0.5 + 0.5 * math.sin(self.t * 4)
            self.rrect(box.inflate(16, 16), (200, 40, 40, 50), 34)
            self.rrect(box, (18, 10, 24, 245), 28, 4, (220, 70, 70, 255))
            self.text("GAME OVER", 96, (255, 110, 110), (W // 2, box.y + 70))
            pygame.draw.line(self.screen, (120, 50, 60), (box.x + 60, box.y + 128), (box.right - 60, box.y + 128), 2)
            self.text("PONTUAÇÃO", 22, (190, 180, 200), (W // 2, box.y + 156), shadow=False)
            self.text(str(self.score), 64, (255, 224, 120), (W // 2, box.y + 195))
            self.text(f"Andar alcançado: {self.floor}   •   Melhor andar: {self.best}", 26, (240, 240, 255), (W // 2, box.y + 250))
            if self.floor >= self.best and self.floor > 1:
                self.text("NOVO RECORDE!", 30, mix((255, 214, 90), pulse * 0.5), (W // 2, box.y + 285))
            self.text("ENTER  para voltar ao menu", 28, mix((200, 205, 235), pulse * 0.6), (W // 2, box.bottom - 30))
        if getattr(self, "flash_t", 0) > 0:
            fo = pygame.Surface((W, H), pygame.SRCALPHA)
            fo.fill((255, 255, 255, int(110 * self.flash_t / 0.22)))
            self.screen.blit(fo, (0, 0))
        self.draw_menu_button()
        self.draw_badges()
        self.draw_transition()

    # ------------------------------------------------------------- entrada
    def handle_key(self, key):
        if self.settings_open:
            self.settings_key(key)
            return
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if key == pygame.K_F11:
            self.toggle_fs()
            return
        ph = self.phase
        go = key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if key == pygame.K_n:
            self.toggle_music()
            return
        if key == pygame.K_c:
            self.open_settings()
            return
        if key == pygame.K_t:
            self.cycle_mode()
            return
        if key == pygame.K_m and ph != "title":
            self.back_to_menu()
            return
        if ph == "title":
            if key in (pygame.K_LEFT, pygame.K_a):
                self.hero_index = (self.hero_index - 1) % len(HEROES)
                self.hero = HEROES[self.hero_index]
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.hero_index = (self.hero_index + 1) % len(HEROES)
                self.hero = HEROES[self.hero_index]
            elif go:
                self.new_run()
        elif ph == "quiz":
            if key in (pygame.K_1, pygame.K_KP1, pygame.K_LEFT, pygame.K_a):
                self.answer_q(0)
            elif key in (pygame.K_2, pygame.K_KP2, pygame.K_RIGHT, pygame.K_d):
                self.answer_q(1)
        elif ph == "card" and go and self.ct > 0.5:
            self.continue_after_card()
        elif ph == "gameover" and go:
            self.transition = None
            self.phase = "title"
            self.banner, self.banner_t = "", 0.0
            self.particles.clear()
            self.floaters.clear()

    def run(self):
        while True:
            try:
                dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
                self.ui_t += dt
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.type == pygame.KEYDOWN:
                        self.handle_key(ev.key)
                self.music_tick()
                try:
                    if self.phase != "title":
                        if not self.settings_open:      # configurações pausam a partida
                            self.update(dt)
                    else:
                        self.t += dt
                except Exception:
                    # erro na lógica: mostra no console e segue sem sair da partida
                    traceback.print_exc()
                    self.errs = getattr(self, "errs", 0) + 1
                    if self.errs > 30:
                        self.errs = 0
                        self.phase = "title"
                        self.new_run(title=True)
                try:
                    self.draw()
                except Exception:
                    # erro só de desenho: pula o frame, o estado do jogo não muda
                    if not getattr(self, "draw_err", False):
                        traceback.print_exc()
                        self.draw_err = True
                pygame.display.flip()
            except Exception:
                traceback.print_exc()


if __name__ == "__main__":
    g = Game()
    if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit():
        g.forced_seed = int(sys.argv[1])
        g.new_run(title=True)
    g.run()