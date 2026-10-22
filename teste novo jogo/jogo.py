# -*- coding: utf-8 -*-
"""
PINDORAMA - Raízes do Brasil
Cenário 1: A Chegada (Litoral do Brasil, c. 1550) - você é um(a) indígena do litoral.

Estilo "HD-2D": sprites pixel art em um mundo em blocos, visto de cima em ângulo,
com desfoque de profundidade (tilt-shift), luz quente e vinheta.

Requisitos:  pip install pygame
Executar:    python pindorama.py

Controles
  Setas / WASD ... andar          E / Espaço / Enter ... falar / avançar
  Setas / 1-4 ..... escolher       Tab / J ... diário      Esc ... pausa
"""
import math
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
W, H = 1280, 720          # janela
IW, IH = 320, 180         # resolução interna (pixel art)
SC = W // IW              # escala = 4
TS = 16                   # tamanho do tile
MW, MH = 56, 38           # mapa em tiles
FPS = 60

OUTLINE = (32, 22, 56)


def shade(c, d):
    return tuple(max(0, min(255, v + d)) for v in c[:3])


def clamp(v, a, b):
    return max(a, min(b, v))


# ----------------------------------------------------------------------------
# Protagonistas (4): 2 mulheres e 2 homens, peles pardas ou negras
# ----------------------------------------------------------------------------
HEROES = [
    dict(id="ousada", nome="Jaci", genero="f", titulo="A Destemida", pele="Pele parda",
         desc="Impulsiva e corajosa. Fala o que pensa e enfrenta o perigo de frente. "
              "Conquista respeito pela ousadia, mas também provoca tensão.",
         p=dict(skin=(176, 112, 74), hair=(24, 18, 22), style="bob", top=None,
                paint=(196, 44, 34), skirt=(214, 172, 92), headwear="band",
                hw=[(200, 40, 40), (245, 205, 60), (230, 80, 50)])),
    dict(id="sabia", nome="Araci", genero="f", titulo="A Sábia", pele="Pele negra",
         desc="Observadora e diplomática. Escuta antes de falar e procura acordos "
              "justos. Enxerga os dois lados de qualquer conversa.",
         p=dict(skin=(112, 68, 46), hair=(18, 14, 18), style="long", top=(240, 236, 222),
                paint=None, facepaint=(245, 245, 235), skirt=(176, 84, 60),
                headwear="band", hw=[(70, 150, 200), (240, 240, 240), (60, 170, 120)],
                extra="maraca")),
    dict(id="astuto", nome="Kauã", genero="m", titulo="O Astuto", pele="Pele parda",
         desc="Esperto e irônico. Lê as intenções dos outros e negocia com malícia. "
              "Os mais velhos nem sempre confiam em suas manhas.",
         p=dict(skin=(152, 94, 62), hair=(20, 16, 20), style="short", top=None,
                paint=(26, 26, 44), skirt=(122, 152, 72), headwear="band",
                hw=[(240, 200, 50), (250, 120, 40), (240, 240, 240)])),
    dict(id="protetor", nome="Ubiratã", genero="m", titulo="O Protetor", pele="Pele negra",
         desc="Calmo, forte e leal. Coloca a aldeia acima de tudo e protege os mais "
              "frágeis. Desconfia de estranhos e fala pouco.",
         p=dict(skin=(100, 60, 42), hair=(14, 12, 16), style="short", top=None,
                paint=(236, 236, 228), skirt=(92, 66, 44), headwear="band",
                hw=[(60, 160, 80), (240, 210, 70), (200, 60, 50)], extra="bow")),
]

TRAIT_NAMES = {"ousada": "Destemida", "sabia": "Sábia", "astuto": "Astuto", "protetor": "Protetor"}

# ----------------------------------------------------------------------------
# Sprites de personagens (pixel art gerada por código)
# ----------------------------------------------------------------------------
CW, CHH = 18, 30      # canvas do personagem (antes do contorno)


def make_char(p, d, f):
    """Desenha um personagem 16x22 (dentro de um canvas com margem)."""
    if d == "left":
        s = make_char(p, "right", f)
        return pygame.transform.flip(s, True, False)
    s = pygame.Surface((CW, CHH), pygame.SRCALPHA)

    def R(x, y, w, h, c):
        pygame.draw.rect(s, c, (x + 1, y + 5, w, h))

    skin = p["skin"]
    sk2 = shade(skin, -28)
    hair = p["hair"]
    dark = (30, 20, 28)
    la = lb = aa = ab = 0
    if f == 1:
        la, aa, ab = -1, 1, -1
    elif f == 2:
        lb, aa, ab = -1, -1, 1
    legc = p.get("legs") or skin
    shoes = p.get("shoes")
    top = p.get("top")
    paint = p.get("paint")
    skirt = p.get("skirt")
    sleeve = p.get("sleeve")
    armc = sleeve or skin
    style = p.get("style", "short")
    side = d == "right"
    extra = p.get("extra")
    wood = (112, 78, 48)

    # pernas
    R(5, 16, 3, 6 + la, legc)
    R(8, 16, 3, 6 + lb, legc)
    if shoes:
        R(5, 21 + la, 3, 1, shoes)
        R(8, 21 + lb, 3, 1, shoes)
    else:
        R(5, 21 + la, 3, 1, sk2)
        R(8, 21 + lb, 3, 1, sk2)
    # torso
    if side:
        R(5, 8, 7, 7, top or skin)
    else:
        R(4, 8, 8, 7, top or skin)
    if top:
        R(4 if not side else 5, 12, 8 if not side else 7, 1, shade(top, -45))
    elif paint and not side:
        R(5, 9, 1, 5, paint)
        R(10, 9, 1, 5, paint)
        R(7, 10, 2, 1, paint)
        R(6, 12, 4, 1, paint)
    elif paint and side:
        R(6, 9, 1, 5, paint)
        R(8, 11, 3, 1, paint)
    if p.get("ruff"):
        R(5, 8, 6, 1, (245, 245, 238))
    # saia / tanga
    if skirt:
        if side:
            R(4, 14, 9, 4, skirt)
            R(4, 17, 9, 1, shade(skirt, -38))
        else:
            R(4, 14, 8, 4, skirt)
            R(4, 17, 8, 1, shade(skirt, -38))
            R(6, 14, 1, 3, shade(skirt, 22))
            R(9, 14, 1, 3, shade(skirt, 22))
    # braços
    if side:
        R(6, 9 + aa, 3, 5, shade(armc, -16))
        R(6, 14 + aa, 3, 1, sk2)
    else:
        R(3, 9 + aa, 1, 5, armc)
        R(12, 9 + ab, 1, 5, armc)
        if sleeve:
            R(3, 14 + aa, 1, 1, skin)
            R(12, 14 + ab, 1, 1, skin)
    # extras
    if extra == "staff":
        R(13 if not side else 11, 3, 1, 20, wood)
        R(12 if not side else 10, 2, 3, 2, shade(wood, 30))
    elif extra == "bow" and not side:
        R(13, 6, 1, 15, wood)
        R(14, 7, 1, 13, (230, 226, 210))
    elif extra == "bow" and side:
        R(3, 6, 1, 15, wood)
    elif extra == "maraca":
        if not side:
            R(13, 13 + ab, 2, 3, (205, 70, 56))
            R(13, 16 + ab, 1, 2, wood)
        else:
            R(10, 13 + aa, 2, 3, (205, 70, 56))
    # cabeça
    if side:
        R(5, 2, 7, 7, skin)
        R(5, 8, 7, 1, sk2)
        if style != "bald":
            R(4, 1, 8, 3, hair)
            back = {"long": 9, "bob": 6, "short": 3}.get(style, 3)
            R(4, 3, 3, back, hair)
        R(9, 5, 1, 2, dark)
        R(12, 6, 1, 1, skin)
        R(10, 8, 2, 1, shade(skin, -50))
    elif d == "up":
        R(5, 2, 6, 7, skin)
        hh = {"long": 11, "bob": 8, "short": 6, "bald": 0}.get(style, 6)
        if hh:
            R(4, 1, 8, hh, hair)
        else:
            R(4, 1, 8, 8, skin)
    else:
        R(5, 2, 6, 7, skin)
        R(5, 8, 6, 1, sk2)
        if style != "bald":
            R(4, 1, 8, 2, hair)
            R(5, 3, 6, 1, hair)
            sh = {"long": 9, "bob": 6, "short": 3}.get(style, 3)
            R(4, 2, 1, sh, hair)
            R(11, 2, 1, sh, hair)
        R(6, 5, 1, 2, dark)
        R(9, 5, 1, 2, dark)
        R(7, 8, 2, 1, shade(skin, -55))
        fp = p.get("facepaint")
        if fp:
            R(5, 4, 6, 1, fp)
            R(5, 7, 1, 1, fp)
            R(10, 7, 1, 1, fp)
    # adereços de cabeça
    hw = p.get("headwear")
    c = p.get("hw") or [(200, 40, 40), (240, 200, 60), (60, 160, 80)]
    if hw == "band":
        R(4, 3, 8, 1, c[0])
        R(10, 0, 1, 3, c[1])
        R(11, 1, 1, 2, c[2])
        R(9, 1, 1, 2, c[2])
    elif hw == "cocar":
        R(3, 0, 10, 2, c[0])
        R(2, -2, 12, 2, c[1])
        R(4, -3, 8, 1, c[2])
        R(3, 2, 1, 2, c[1])
        R(12, 2, 1, 2, c[1])
    elif hw == "morion":
        steel = c[0]
        R(4, 0, 8, 3, steel)
        R(3, 3, 10, 1, shade(steel, -35))
        R(7, -1, 2, 1, steel)
        R(4, 0, 8, 1, shade(steel, 35))
    elif hw == "hat":
        R(2, 2, 12, 1, c[0])
        R(4, -1, 8, 3, c[0])
        R(4, 1, 8, 1, shade(c[0], 30))
        R(10, -3, 3, 2, (240, 238, 230))
    return s


def outlined(s, col=OUTLINE):
    w, h = s.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(s).to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(s, (1, 1))
    return out


ANCHOR = (10, 27)


def make_actor(p):
    frames = {}
    k = p.get("scale", 1.0)
    for d in ("down", "up", "left", "right"):
        lst = []
        for f in (0, 1, 2):
            sp = outlined(make_char(p, d, f))
            if k != 1.0:
                sp = pygame.transform.scale(sp, (int(sp.get_width() * k), int(sp.get_height() * k)))
            lst.append(sp)
        frames[d] = lst
    return frames, (int(ANCHOR[0] * k), int(ANCHOR[1] * k))


# ----------------------------------------------------------------------------
# Sprites do cenário (blocos / "voxels")
# ----------------------------------------------------------------------------
def make_shadow(spr, squash=0.42, shear=0.55, alpha=78):
    w, h = spr.get_size()
    sil = pygame.mask.from_surface(spr).to_surface(setcolor=(18, 10, 50, alpha), unsetcolor=(0, 0, 0, 0))
    sh = max(3, int(h * squash))
    sq = pygame.transform.scale(pygame.transform.flip(sil, False, True), (w, sh))
    out = pygame.Surface((w + int(sh * shear) + 2, sh), pygame.SRCALPHA)
    for r in range(sh):
        out.blit(sq, (int(r * shear), r), (0, r, w, 1))
    return out


def tree_sprite(kind, seed):
    r = random.Random(seed)
    s = pygame.Surface((42, 52), pygame.SRCALPHA)
    leaf = {0: (54, 116, 60), 1: (78, 148, 66), 2: (238, 190, 44), 3: (44, 98, 62)}[kind]
    pygame.draw.rect(s, (96, 64, 44), (18, 30, 6, 22))
    pygame.draw.rect(s, (122, 86, 56), (18, 30, 2, 22))
    pygame.draw.rect(s, (70, 46, 34), (22, 30, 2, 22))
    pygame.draw.rect(s, (70, 46, 34), (14, 50, 14, 2))
    layers = [(3, 19, 36, 16), (7, 9, 28, 17), (12, 1, 18, 14)]
    for i, (x, y, w, h) in enumerate(layers):
        pygame.draw.rect(s, shade(leaf, -16 + i * 4), (x, y, w, h))
        pygame.draw.rect(s, shade(leaf, 26 + i * 4), (x, y, w, max(3, h // 3)))
        pygame.draw.rect(s, shade(leaf, -42), (x, y + h - 2, w, 2))
        pygame.draw.rect(s, shade(leaf, -26), (x + w - 3, y + 3, 3, h - 3))
        for _ in range(w // 2):
            px, py = x + r.randrange(w), y + r.randrange(h)
            s.set_at((px, py), shade(leaf, r.choice((-30, 18, 34))))
    return s


def palm_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((46, 62), pygame.SRCALPHA)
    pts = [(22, 62), (23, 48), (25, 36), (24, 22)]
    for i in range(len(pts) - 1):
        pygame.draw.line(s, (136, 100, 62), pts[i], pts[i + 1], 3)
        pygame.draw.line(s, (96, 68, 44), (pts[i][0] + 2, pts[i][1]), (pts[i + 1][0] + 2, pts[i + 1][1]), 1)
    for y in range(26, 60, 5):
        pygame.draw.line(s, (88, 62, 40), (21 + (62 - y) // 14, y), (26 + (62 - y) // 14, y), 1)
    top = (24, 21)
    green = (64, 146, 72)
    for ang, ln in ((-170, 20), (-140, 22), (-105, 18), (-75, 18), (-40, 22), (-10, 20), (20, 14), (160, 14)):
        a = math.radians(ang)
        mid = (top[0] + math.cos(a) * ln * 0.6, top[1] + math.sin(a) * ln * 0.6 - 4)
        end = (top[0] + math.cos(a) * ln, top[1] + math.sin(a) * ln * 0.5 + 6)
        pygame.draw.line(s, shade(green, r.choice((-12, 0, 14))), top, mid, 2)
        pygame.draw.line(s, shade(green, -20), mid, end, 2)
    pygame.draw.rect(s, (110, 80, 44), (22, 22, 4, 4))
    pygame.draw.rect(s, (90, 62, 36), (20, 24, 3, 3))
    return s


def oca_sprite(seed):
    r = random.Random(seed)
    w, h = 78, 66
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (124, 86, 54), (4, 48, w - 8, 18))
    for x in range(6, w - 6, 4):
        pygame.draw.rect(s, (92, 62, 40), (x, 48, 1, 18))
    pygame.draw.rect(s, (70, 46, 32), (4, 63, w - 8, 3))
    pygame.draw.rect(s, (38, 26, 24), (w // 2 - 7, 51, 14, 15))
    pygame.draw.rect(s, (86, 58, 38), (w // 2 - 7, 51, 14, 2))
    thatch = (190, 152, 74)
    for k in range(6):
        lw = w - 2 * k * 5
        lx = k * 5
        ly = 42 - k * 7
        lh = 12
        front = shade(thatch, -22 + k * 5)
        pygame.draw.rect(s, front, (lx, ly, lw, lh))
        pygame.draw.rect(s, shade(thatch, 30 + k * 3), (lx, ly, lw, 3))
        for _ in range(lw // 3):
            px = lx + r.randrange(lw)
            py = ly + 4 + r.randrange(lh - 4)
            pygame.draw.rect(s, shade(front, -34), (px, py, 1, 3))
        for _ in range(lw // 5):
            px = lx + r.randrange(lw)
            s.set_at((px, ly + 5 + r.randrange(lh - 5)), shade(front, 24))
        pygame.draw.rect(s, shade(front, -40), (lx, ly + lh - 1, lw, 1))
    pygame.draw.rect(s, (96, 64, 40), (w // 2 - 1, 0, 2, 7))
    pygame.draw.rect(s, (220, 60, 50), (w // 2 + 1, 1, 3, 2))
    return s


def ship_sprite():
    s = pygame.Surface((110, 96), pygame.SRCALPHA)
    pygame.draw.rect(s, (92, 60, 40), (8, 70, 94, 14))
    pygame.draw.rect(s, (126, 86, 54), (12, 62, 88, 10))
    pygame.draw.rect(s, (214, 176, 98), (10, 58, 92, 5))
    pygame.draw.rect(s, (62, 40, 30), (14, 82, 80, 4))
    pygame.draw.rect(s, (126, 86, 54), (2, 64, 10, 8))
    pygame.draw.rect(s, (92, 60, 40), (96, 52, 12, 14))
    for x in range(18, 96, 12):
        pygame.draw.rect(s, (36, 26, 24), (x, 66, 5, 4))
    for mx, top, sw in ((30, 8, 38), (70, 16, 32)):
        pygame.draw.rect(s, (86, 58, 38), (mx, top, 3, 52))
        pygame.draw.rect(s, (88, 58, 40), (mx - sw // 2 + 2, top + 4, sw, 2))
        pygame.draw.rect(s, (238, 234, 218), (mx - sw // 2 + 3, top + 6, sw - 2, 26))
        pygame.draw.rect(s, (206, 202, 186), (mx - sw // 2 + 3, top + 24, sw - 2, 8))
        pygame.draw.rect(s, (196, 30, 40), (mx - 1, top + 10, 4, 18))
        pygame.draw.rect(s, (196, 30, 40), (mx - 8, top + 15, 18, 4))
        pygame.draw.rect(s, (200, 40, 50), (mx + 3, top - 4, 8, 4))
    return s


def canoe_sprite(col=(124, 84, 50), w=40):
    s = pygame.Surface((w, 12), pygame.SRCALPHA)
    pygame.draw.rect(s, shade(col, -30), (2, 6, w - 4, 6))
    pygame.draw.rect(s, col, (0, 3, w, 6))
    pygame.draw.rect(s, shade(col, 34), (3, 2, w - 6, 2))
    pygame.draw.rect(s, shade(col, -48), (6, 5, w - 12, 2))
    pygame.draw.rect(s, shade(col, -30), (0, 2, 3, 3))
    pygame.draw.rect(s, shade(col, -30), (w - 3, 2, 3, 3))
    return s


def jirau_sprite():
    s = pygame.Surface((34, 28), pygame.SRCALPHA)
    wood = (110, 76, 46)
    for x in (2, 29):
        pygame.draw.rect(s, wood, (x, 8, 3, 20))
    pygame.draw.rect(s, shade(wood, 22), (0, 8, 34, 3))
    pygame.draw.rect(s, shade(wood, -10), (0, 14, 34, 2))
    for x in range(5, 28, 5):
        pygame.draw.rect(s, (200, 96, 70), (x, 11, 3, 8))
        pygame.draw.rect(s, (150, 62, 46), (x, 17, 3, 2))
    return s


def totem_sprite():
    s = pygame.Surface((20, 52), pygame.SRCALPHA)
    pygame.draw.rect(s, (104, 70, 44), (7, 8, 6, 44))
    for y, c in ((14, (196, 44, 34)), (26, (26, 26, 40)), (38, (236, 220, 180))):
        pygame.draw.rect(s, c, (7, y, 6, 6))
    for x, y, c in ((2, 4, (60, 160, 200)), (14, 2, (240, 200, 60)), (5, 0, (210, 50, 40)), (10, 6, (60, 170, 90))):
        pygame.draw.rect(s, c, (x, y, 3, 10))
    return s


def pot_sprite():
    s = pygame.Surface((22, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (176, 100, 62), (4, 4, 14, 11))
    pygame.draw.rect(s, (206, 130, 84), (4, 4, 14, 3))
    pygame.draw.rect(s, (130, 70, 46), (15, 6, 3, 9))
    pygame.draw.rect(s, (226, 214, 176), (6, 3, 10, 2))
    return s


def bush_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((22, 14), pygame.SRCALPHA)
    pygame.draw.rect(s, (52, 120, 58), (1, 5, 20, 9))
    pygame.draw.rect(s, (74, 150, 70), (3, 2, 16, 6))
    pygame.draw.rect(s, (96, 172, 84), (3, 2, 16, 2))
    for _ in range(4):
        s.set_at((r.randrange(2, 20), r.randrange(3, 13)), r.choice(((240, 90, 120), (250, 220, 80))))
    return s


def fire_frames():
    fr = []
    r = random.Random(5)
    for _ in range(8):
        s = pygame.Surface((22, 22), pygame.SRCALPHA)
        for k in range(8):
            a = k * math.pi / 4
            px, py = int(11 + 8 * math.cos(a)), int(17 + 4 * math.sin(a))
            pygame.draw.rect(s, (120, 120, 130), (px - 1, py - 1, 3, 3))
            pygame.draw.rect(s, (168, 168, 176), (px - 1, py - 1, 3, 1))
        pygame.draw.line(s, (96, 60, 36), (6, 19), (16, 15), 2)
        pygame.draw.line(s, (112, 72, 42), (6, 15), (16, 19), 2)
        for fx, fh, col in ((11, 13, (236, 66, 30)), (8, 9, (255, 140, 40)),
                            (14, 10, (255, 140, 40)), (11, 8, (255, 222, 96))):
            h = fh + r.randint(-2, 3)
            pygame.draw.polygon(s, col, [(fx - 3, 16), (fx, 16 - h), (fx + 3, 16)])
        fr.append(s)
    return fr


def make_glow(strength):
    s = pygame.Surface((90, 90))
    s.fill((0, 0, 0))
    for rad in range(44, 0, -2):
        k = (1 - rad / 44.0) ** 2
        pygame.draw.circle(s, (int(90 * k * strength), int(52 * k * strength), int(14 * k * strength)), (45, 45), rad)
    return s


# ----------------------------------------------------------------------------
# Mapa
# ----------------------------------------------------------------------------
def shore(y):
    return 9 + int(round(2 * math.sin(y * 0.45) + 1.5 * math.sin(y * 0.17 + 1)))


TILE_COL = {0: (70, 150, 192), 1: (224, 198, 142), 2: (100, 160, 72),
            3: (180, 134, 90), 4: (70, 124, 62), 5: (132, 88, 58)}


def build_tiles():
    tiles = [[2] * MW for _ in range(MH)]
    rnd = random.Random(3)
    for y in range(MH):
        sx = shore(y)
        for x in range(MW):
            if x < sx:
                t = 0
            elif x < sx + 4:
                t = 1
            else:
                edge = min(x - (sx + 4), 46 - x, y - 5, 32 - y)
                if edge < 0:
                    t = 4
                elif edge < 2 and rnd.random() < 0.5:
                    t = 4
                else:
                    t = 2
                if ((x - 31) / 8.0) ** 2 + ((y - 19) / 5.0) ** 2 < 1.0:
                    t = 3
                if 36 <= x <= 45 and 25 <= y <= 30:
                    t = 5
            tiles[y][x] = t
    for y in (19, 20):
        for x in range(shore(y) + 4, 24):
            tiles[y][x] = 3
    return tiles


def build_ground(tiles):
    g = pygame.Surface((MW * TS, MH * TS))
    r = random.Random(11)
    for y in range(MH):
        for x in range(MW):
            t = tiles[y][x]
            c = TILE_COL[t]
            if t == 0:
                c = shade(c, -int((shore(y) - x) * 3))
            c = shade(c, r.randint(-6, 6))
            g.fill(c, (x * TS, y * TS, TS, TS))
            for _ in range(6):
                px, py = x * TS + r.randrange(TS), y * TS + r.randrange(TS)
                g.set_at((px, py), shade(c, r.choice((-18, 14))))
            if t in (2, 4) and r.random() < 0.4:
                px, py = x * TS + r.randrange(2, TS - 2), y * TS + r.randrange(3, TS - 1)
                g.fill(shade(c, 28), (px, py - 2, 1, 3))
                g.fill(shade(c, 18), (px + 1, py - 1, 1, 2))
            if t == 2 and r.random() < 0.06:
                px, py = x * TS + r.randrange(2, TS - 3), y * TS + r.randrange(2, TS - 3)
                g.fill(r.choice(((250, 230, 90), (240, 110, 150), (250, 250, 240))), (px, py, 2, 2))
            if t == 3 and r.random() < 0.3:
                px, py = x * TS + r.randrange(2, TS - 4), y * TS + r.randrange(2, TS - 3)
                g.fill(shade(c, -22), (px, py, 3, 2))
            if t == 5:
                g.fill(shade(c, -24), (x * TS + 1, y * TS + 5, TS - 2, 2))
                g.fill(shade(c, -24), (x * TS + 1, y * TS + 12, TS - 2, 2))
                if (x + y) % 2 == 0:
                    g.fill((78, 146, 62), (x * TS + 6, y * TS + 1, 3, 6))
                    g.fill((118, 184, 84), (x * TS + 4, y * TS, 7, 2))
    for y in range(MH):
        x = shore(y) - 1
        g.fill((226, 244, 250), (x * TS + TS - 3, y * TS, 3, TS))
        g.fill((176, 220, 238), (x * TS + TS - 7, y * TS, 4, TS))
        g.fill((204, 176, 120), ((x + 1) * TS, y * TS, 3, TS))
    return g


def build_minimap(tiles):
    m = pygame.Surface((MW * 2, MH * 2))
    cols = {0: (96, 150, 214), 1: (232, 214, 160), 2: (118, 176, 96),
            3: (196, 150, 110), 4: (72, 130, 84), 5: (150, 102, 70)}
    for y in range(MH):
        for x in range(MW):
            m.fill(cols[tiles[y][x]], (x * 2, y * 2, 2, 2))
    return m


# ----------------------------------------------------------------------------
# Objetos e atores
# ----------------------------------------------------------------------------
_shadow_cache = {}


class Obj:
    def __init__(self, spr, x, y, col=None, frames=None, fps=8, bob=0.0, shadow=True):
        self.frames = frames or [spr]
        self.x, self.y = x, y
        self.col = col
        self.fps = fps
        self.bob = bob
        self.shadow = None
        if shadow:
            key = id(self.frames[0])
            if key not in _shadow_cache:
                _shadow_cache[key] = make_shadow(self.frames[0])
            self.shadow = _shadow_cache[key]

    def surf(self, t):
        return self.frames[int(t * self.fps) % len(self.frames)]


class NPC:
    def __init__(self, cfg):
        self.id = cfg["id"]
        self.name = cfg["name"]
        self.dlg = cfg["dlg"]
        self.x = cfg["pos"][0] * TS + 8
        self.y = cfg["pos"][1] * TS + 14
        self.face = cfg.get("face", "down")
        self.frames, self.anchor = make_actor(cfg["p"])
        self.quest = cfg.get("quest", False)
        self.hop = cfg["p"].get("scale", 1.0) < 1.0
        self.rect = pygame.Rect(int(self.x) - 5, int(self.y) - 5, 10, 5)
        self.talked = False


NPC_DEFS = [
    dict(id="iane", name="Kunhã Ianê", dlg="iane", pos=(34, 23), face="down", quest=True,
         p=dict(skin=(150, 96, 64), hair=(206, 206, 210), style="long", top=(236, 230, 214),
                skirt=(150, 92, 60), headwear=None, extra="staff")),
    dict(id="jurema", name="Pajé Jurema", dlg="jurema", pos=(27, 14), face="down", quest=True,
         p=dict(skin=(122, 76, 52), hair=(20, 16, 20), style="long", top=None,
                paint=(240, 240, 232), skirt=(170, 44, 52), headwear="cocar",
                hw=[(60, 150, 200), (240, 200, 60), (220, 60, 50)], extra="maraca")),
    dict(id="pira", name="Morubixaba Pirá", dlg="pira", pos=(31, 16), face="down", quest=True,
         p=dict(skin=(140, 88, 58), hair=(18, 14, 18), style="short", top=None,
                paint=(196, 44, 34), skirt=(232, 228, 214), headwear="cocar",
                hw=[(222, 52, 40), (250, 202, 52), (44, 144, 72)])),
    dict(id="potira", name="Potira", dlg="potira", pos=(29, 21), face="right",
         p=dict(skin=(164, 104, 70), hair=(18, 14, 18), style="long", top=None,
                skirt=(212, 190, 122), headwear="band", scale=0.76,
                hw=[(240, 100, 140), (250, 220, 80), (250, 250, 250)])),
]


def beach_defs():
    bx = lambda y: (shore(y) + 2)
    return [
        dict(id="diogo", name="Diogo", dlg="beach", pos=(bx(18), 18), face="right", quest=True,
             p=dict(skin=(172, 118, 82), hair=(40, 28, 22), style="short", top=(206, 196, 164),
                    sleeve=(206, 196, 164), legs=(112, 92, 70), shoes=(70, 50, 38),
                    headwear="hat", hw=[(96, 74, 52)])),
        dict(id="fernao", name="Fernão", dlg="beach", pos=(bx(20), 20), face="right", quest=True,
             p=dict(skin=(224, 180, 146), hair=(96, 54, 32), style="short", top=(150, 30, 42),
                    sleeve=(150, 30, 42), legs=(40, 40, 72), shoes=(60, 40, 30), ruff=True,
                    headwear="hat", hw=[(30, 30, 42)])),
        dict(id="marujo", name="Marujo", dlg="marujo", pos=(bx(23), 23), face="right",
             p=dict(skin=(208, 164, 128), hair=(120, 90, 60), style="short", top=(214, 208, 192),
                    sleeve=(214, 208, 192), legs=(70, 92, 122), shoes=(60, 44, 34),
                    headwear="morion", hw=[(158, 162, 174)])),
    ]


# ----------------------------------------------------------------------------
# Diálogos - a personalidade do protagonista muda falas e opções
# ----------------------------------------------------------------------------
def D(sp, text, ch=None, nxt=None, fx=None, flag=None, end=None, setv=None):
    return dict(sp=sp, text=text, ch=ch, nxt=nxt, fx=fx or {}, flag=flag, end=end, set=setv or {})


def C(text, nxt, fx=None, setv=None):
    return dict(text=text, nxt=nxt, fx=fx or {}, set=setv or {})


DLG = {
    # ------------------------------------------------------------------ Ianê
    "iane": {
        "start": D("Kunhã Ianê",
                   "{Filho}, o mar trouxe uma casa que flutua. Cheira a ferro e a fumaça estranha... "
                   "Meu coração anda inquieto, {nome}.",
                   ch=[C({"ousada": "Eu mesma vou até a praia. Quero olhar nos olhos desses estrangeiros.",
                          "sabia": "O que os antigos contam sobre gente que vem do mar, Ianê?",
                          "astuto": "Se eles querem algo, vão mostrar o preço. Vou observar antes de falar.",
                          "protetor": "Fique tranquila, Ianê. Eu monto guarda. Ninguém toca na aldeia."},
                         "p_{trait}"),
                       C("Me conte o que sabe sobre eles.", "info")]),
        "p_ousada": D("Kunhã Ianê", "A coragem é uma flecha, {nome}: serve a quem sabe mirar. "
                      "Pinte o rosto com urucum e deixe o respeito caminhar na sua frente.",
                      nxt="info", fx={"aldeia": 6}),
        "p_sabia": D("Kunhã Ianê", "Dizem que eles virão trazendo espelhos e febres. Que escutar vale mais "
                     "que falar. Você tem o dom de ouvir, {nome}.", nxt="info", fx={"aldeia": 4}),
        "p_astuto": D("Kunhã Ianê", "Olhos de gavião... Mas cuidado: quem brinca com a mentira, um dia a vê "
                      "voltar contra a própria aldeia.", nxt="info", fx={"aldeia": 2}),
        "p_protetor": D("Kunhã Ianê", "Seu braço protege, {nome}. Mas lembre: nem todo perigo chega armado. "
                        "Alguns chegam sorrindo.", nxt="info", fx={"aldeia": 5}),
        "info": D("Kunhã Ianê", "Falam outra língua e carregam paus que cospem fogo. Procuram o ibirapitanga, "
                  "a árvore que sangra vermelho. Eles a chamam de pau-brasil.", nxt="fim"),
        "fim": D("Kunhã Ianê", "Ouça também o morubixaba Pirá e a pajé Jurema. A aldeia decide junta, {nome}.",
                 flag="iane"),
        "again": D("Kunhã Ianê", "Vá, {nome}. Os espíritos acompanham quem escuta."),
    },
    # ---------------------------------------------------------------- Jurema
    "jurema": {
        "start": D("Pajé Jurema",
                   "Sonhei com o mar sangrando e uma cruz vermelha nas velas. Anhangá caminha entre nós, {nome}. "
                   "Diga: o que seu coração sente diante do navio?",
                   ch=[C({"ousada": "Raiva. Eles chegam sem pedir licença à terra.",
                          "sabia": "Curiosidade. Quero entender o que eles realmente querem.",
                          "astuto": "Dúvida. Nem tudo que brilha é presente.",
                          "protetor": "Preocupação com as crianças e os anciãos da aldeia."}, "p_{trait}"),
                       C("Ainda não sei o que sinto.", "p_neutro")]),
        "p_ousada": D("Pajé Jurema", "A raiva aquece, mas queima o próprio ninho. Respire, {nome}. "
                      "Use a força quando o espírito pedir, não antes.", nxt="fim", fx={"aldeia": 3}),
        "p_sabia": D("Pajé Jurema", "Quem pergunta caminha com Tupã ao lado. Leve este colar de sementes: "
                     "ele lembra que a palavra também é uma arma.", nxt="fim", fx={"aldeia": 6}),
        "p_astuto": D("Pajé Jurema", "A dúvida é boa guardiã. Mas não confunda esperteza com sabedoria, {nome}.",
                      nxt="fim", fx={"aldeia": 2}),
        "p_protetor": D("Pajé Jurema", "O cuidado é o chão firme da aldeia. Os espíritos sorriem para quem protege.",
                        nxt="fim", fx={"aldeia": 6}),
        "p_neutro": D("Pajé Jurema", "Está certo. Sentir devagar também é um caminho.", nxt="fim"),
        "fim": D("Pajé Jurema", "Toda troca cobra uma dívida. Nem tudo se vende, nem tudo se guarda: "
                 "procure o equilíbrio e a mata lhe responderá.", flag="jurema"),
        "again": D("Pajé Jurema", "A fumaça do petim já mostrou o que tinha de mostrar. Agora é com você."),
    },
    # ------------------------------------------------------------------ Pirá
    "pira": {
        "start": D("Morubixaba Pirá",
                   "O conselho se reuniu em volta do fogo. Uns querem trocar com os estrangeiros: machados de "
                   "ferro cortam melhor que pedra. Outros querem expulsá-los. E você, {nome}? Como falaria pela aldeia?",
                   ch=[C({"ousada": "Mostrarei força: eles precisam saber que esta terra tem dono.",
                          "sabia": "Proponho trocas justas, regras claras e testemunhas dos dois lados.",
                          "astuto": "Aceitamos os machados, mas guardamos o que eles mais querem para barganhar.",
                          "protetor": "Recebemos os visitantes com cautela, com guerreiros vigiando as ocas."},
                         "p_{trait}"),
                       C("Prefiro ouvir o conselho antes de falar.", "p_ouvir")]),
        "p_ousada": D("Pirá", "Vozes firmes são ouvidas. Só não confunda coragem com pressa.", nxt="fim",
                      fx={"aldeia": 3}, setv={"postura": "firme"}),
        "p_sabia": D("Pirá", "Palavra bem pesada vale mais que mil flechas. Que seja um acordo.", nxt="fim",
                     fx={"aldeia": 5}, setv={"postura": "acordo"}),
        "p_astuto": D("Pirá", "Manha também é arma. Mas olhe bem nos olhos de quem você engana.", nxt="fim",
                      fx={"aldeia": 2}, setv={"postura": "barganha"}),
        "p_protetor": D("Pirá", "Cuidar dos nossos vem antes de qualquer troca. Faz sentido.", nxt="fim",
                        fx={"aldeia": 5}, setv={"postura": "cautela"}),
        "p_ouvir": D("Pirá", "Humildade é boa, mas a aldeia precisa de voz. Vá e fale com o coração.", nxt="fim"),
        "fim": D("Morubixaba Pirá", "Vá à praia. Diogo, o língua, traduzirá. Leve a palavra da aldeia, {nome}.",
                 flag="pira"),
        "again": D("Morubixaba Pirá", "A praia espera, {nome}. Fale por todos nós."),
    },
    # ---------------------------------------------------------------- Potira
    "potira": {
        "start": D("Potira", "{nome}! Os marinheiros têm uns espelhos que roubam o rosto da gente! "
                   "Você vai até lá?",
                   ch=[C({"ousada": "Claro! E se algum deles te assustar, eu enfrento.",
                          "sabia": "Vou. E depois te conto a lenda do Boitatá, a cobra de fogo.",
                          "astuto": "Vou, e talvez traga um espelho para você... se a troca valer a pena.",
                          "protetor": "Fique perto dos adultos, Potira. Eu volto logo."}, "p_{trait}"),
                       C("Volte para perto da sua mãe, pequena.", "p_mae")]),
        "p_ousada": D("Potira", "Eba! Você é a mais corajosa da aldeia!", fx={"aldeia": 2}),
        "p_sabia": D("Potira", "Conta de novo a parte do fogo que anda pelo campo!", fx={"aldeia": 3}),
        "p_astuto": D("Potira", "Hihi! Você é esperta... quer dizer, esperto!", fx={"aldeia": 1}),
        "p_protetor": D("Potira", "Eu fico quietinha! Mas volta logo, tá?", fx={"aldeia": 3}),
        "p_mae": D("Potira", "Tá bom... mas depois me conta tudo!"),
        "again": D("Potira", "Será que o espelho mostra quem a gente é por dentro?"),
    },
    # ---------------------------------------------------------------- Marujo
    "marujo": {
        "start": D("Marujo", "Alto lá! Nem mais um passo, gente da terra!",
                   ch=[C({"ousada": "Dê um passo para trás você, marujo. Esta praia é MINHA.",
                          "sabia": "(Mostrar as mãos abertas.) Paz. Só quero falar com o seu capitão.",
                          "astuto": "Bela faca. Quanto vale? O seu capitão gosta de quem negocia, não é?",
                          "protetor": "(Cruzar os braços e encarar em silêncio.)"}, "p_{trait}")]),
        "p_ousada": D("Marujo", "O marujo engole em seco e recua meio passo. Um camarada ri baixinho do susto.",
                      fx={"tensao": 6, "aldeia": 3}),
        "p_sabia": D("Marujo", "Hum... Fique aí. Diogo! O intérprete que venha!", fx={"tensao": -4}),
        "p_astuto": D("Marujo", "Eh? Fale com o capitão, ele é quem manda nos negócios!", fx={"tensao": -2}),
        "p_protetor": D("Marujo", "Ele percebe que você não vai se mover. Chama o intérprete, nervoso.",
                        fx={"tensao": 3, "aldeia": 3}),
        "again": D("Marujo", "Fale com o capitão, rápido!"),
    },
    # ------------------------------------------------------------ Praia
    "beach": {
        "wait": D("Diogo", "Os seus ainda não falaram em conselho? Volte quando tiver a palavra da aldeia, {nome}. "
                  "Procure Ianê, Jurema e Pirá."),
        "start": D("Diogo", "Paz, parente! Sou Diogo, filho de português com gente da terra. Falo pelos dois "
                   "lados. Este é Fernão, capitão-mercador.", nxt="fernao"),
        "fernao": D("Fernão (via Diogo)", "Trazemos machados de ferro, facas, espelhos e pano. Queremos toras de "
                    "ibirapitanga para encher o navio. Em troca, a amizade do rei de Portugal.", nxt="offer"),
        "offer": D("Diogo", "E então, {nome}? O que a aldeia responde?",
                   ch=[C({"ousada": "Esta terra não é de rei algum. Troquem, mas pelas nossas regras e com respeito.",
                          "sabia": "Proponho um acordo: poucas toras, entregues aos poucos, e Diogo como testemunha.",
                          "astuto": "Aceito os machados agora. As toras... mostro as árvores só depois de ver o ferro.",
                          "protetor": "Aceitamos visitas, mas ninguém dorme na aldeia e as armas ficam no navio."},
                         "o_{trait}"),
                       C("Aceitamos tudo o que pedem.", "o_aceita"),
                       C("Vão embora. Esta praia não é de vocês.", "o_recusa")]),
        "o_ousada": D("Fernão", "Fernão rói a barba, encara você por um longo instante e estende a mão: "
                      "'Gente de palavra firme. Seja como dizem.'", fx={"aldeia": 6, "tensao": 8}, end="firme"),
        "o_sabia": D("Diogo", "Diogo sorri: 'Boa proposta, parente. Poucas toras, aos poucos, e eu entre vocês.' "
                     "Fernão assente, aliviado.", fx={"aldeia": 8, "tensao": -10}, end="acordo"),
        "o_astuto": D("Fernão", "Fernão ri e bate no ombro de Diogo: 'Esse sabe negociar! Os machados primeiro.' "
                      "Mas seus olhos medem você com desconfiança.", fx={"aldeia": 4, "tensao": 2}, end="barganha"),
        "o_protetor": D("Fernão", "Fernão franze a testa, mas concorda: 'Armas no navio, ninguém dorme em terra. "
                        "Que seja.'", fx={"aldeia": 7, "tensao": 3}, end="cautela"),
        "o_aceita": D("Fernão", "Fernão sorri largo: 'Bom negócio!' Diogo, porém, desvia o olhar, preocupado.",
                      fx={"aldeia": -12, "tensao": -8}, end="aceita"),
        "o_recusa": D("Fernão", "Diogo hesita ao traduzir. Fernão fecha a cara: 'Voltaremos, e com mais homens.'",
                      fx={"aldeia": 2, "tensao": 25}, end="recusa"),
        "again": D("Diogo", "Estamos às ordens, parente."),
    },
}

ENDINGS = {
    "firme": "Fernão aceitou as condições entre dentes. As trocas começaram sob o olhar atento dos guerreiros: "
             "machados de ferro por toras, cada fardo contado diante do conselho. Por ora, a aldeia negocia de "
             "cabeça erguida - mas o respeito, sozinho, não detém navios maiores.",
    "acordo": "O acordo foi selado com palavras, presentes e uma testemunha de cada lado. Poucas toras, entregues "
              "aos poucos. Diogo passou a viver entre os dois mundos, e a paz durou mais do que muitos esperavam.",
    "barganha": "Os machados chegaram primeiro, afiados e brilhantes. As toras vieram depois, no ritmo que a aldeia "
                "escolheu. Fernão sorriu, mas anotou cada truque. Quem joga com esperteza precisa lembrar que "
                "o outro lado também aprende o jogo.",
    "cautela": "Ninguém dormiu em terra e as armas ficaram no navio. As trocas foram lentas, vigiadas, e a aldeia "
               "dormiu em paz - com um olho aberto. A cautela protegeu os seus, mas fez da amizade algo distante.",
    "aceita": "Os machados brilhavam, os espelhos encantavam, e as árvores caíam depressa demais. A aldeia ganhou "
              "ferro e perdeu a mata. Diogo, em silêncio, foi o único a perceber o preço que ainda viria.",
    "recusa": "Fernão partiu levando a ameaça no olhar. A praia ficou vazia, e a aldeia, em alerta. Outros navios "
              "virão, com mais homens e menos paciência. A decisão ecoará pelas gerações que ainda não nasceram.",
}

TRAIT_LINE = {
    "ousada": "A coragem de {nome} virou história contada em volta do fogo.",
    "sabia": "A sabedoria de {nome} fez o conselho ouvir antes de agir.",
    "astuto": "A astúcia de {nome} abriu portas - e criou segredos.",
    "protetor": "A lealdade de {nome} fez cada criança dormir mais tranquila.",
}


# ----------------------------------------------------------------------------
# Utilidades de texto
# ----------------------------------------------------------------------------
def wrap(text, font, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= maxw:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------
# Jogo
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Pindorama - Raízes do Brasil")
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.f_title = pygame.font.Font(None, 150)
        self.f_big = pygame.font.Font(None, 56)
        self.f_med = pygame.font.Font(None, 36)
        self.f_txt = pygame.font.Font(None, 32)
        self.f_ch = pygame.font.Font(None, 29)
        self.f_sm = pygame.font.Font(None, 24)
        self.f_xs = pygame.font.Font(None, 20)

        self.frame = pygame.Surface((IW, IH)).convert()
        self.tiles = build_tiles()
        self.ground = build_ground(self.tiles)
        self.mini = build_minimap(self.tiles)
        self.build_world()
        self.hero_actors = [make_actor(h["p"]) for h in HEROES]
        self.glow = [make_glow(1.0), make_glow(0.82)]
        self.build_overlays()

        self.state = "title"
        self.t = 0.0
        self.menu_i = 0
        self.sel = 0
        self.cam = [0.0, 0.0]
        self.intro_t = 0.0
        self.message = ""
        self.ending = None
        self.reset_play(0)

    # -------------------------------------------------------------- mundo
    def build_world(self):
        self.objs = []
        self.colliders = []
        r = random.Random(21)

        def add(o):
            self.objs.append(o)
            if o.col is not None:
                self.colliders.append(o.col)

        oca_variants = [oca_sprite(i) for i in range(3)]
        for i, (tx, ty) in enumerate(((24, 12), (32, 11), (40, 14), (42, 21), (23, 26), (31, 28))):
            spr = oca_variants[i % 3]
            x, y = tx * TS, ty * TS
            add(Obj(spr, x, y, col=pygame.Rect(x - 36, y - 20, 72, 20)))
        # fogueira, mastro, jiraus, potes
        self.fire = Obj(None, 31 * TS + 8, 19 * TS + 14, frames=fire_frames(), fps=9,
                        col=pygame.Rect(31 * TS, 19 * TS + 8, 16, 6), shadow=False)
        add(self.fire)
        add(Obj(totem_sprite(), 27 * TS + 8, 16 * TS + 6, col=pygame.Rect(27 * TS + 4, 16 * TS, 8, 6)))
        add(Obj(jirau_sprite(), 36 * TS, 22 * TS, col=pygame.Rect(36 * TS - 16, 22 * TS - 6, 32, 6)))
        add(Obj(pot_sprite(), 35 * TS + 4, 24 * TS + 2, col=pygame.Rect(35 * TS - 4, 24 * TS - 4, 14, 6)))
        add(Obj(pot_sprite(), 33 * TS + 2, 24 * TS + 6))
        # praia: canoas, bote, navio
        canoe = canoe_sprite()
        add(Obj(canoe, (shore(14) + 2) * TS, 14 * TS + 8, col=pygame.Rect((shore(14) + 2) * TS - 18, 14 * TS + 2, 36, 6)))
        add(Obj(canoe, (shore(16) + 1) * TS, 16 * TS + 12, col=pygame.Rect((shore(16) + 1) * TS - 18, 16 * TS + 6, 36, 6)))
        add(Obj(canoe_sprite((150, 112, 72), 46), (shore(23) + 1) * TS, 25 * TS + 4,
                col=pygame.Rect((shore(23) + 1) * TS - 22, 25 * TS - 2, 44, 6)))
        self.ship = Obj(ship_sprite(), 3 * TS, 19 * TS, shadow=False, bob=1.5)
        self.objs.append(self.ship)
        # palmeiras na praia
        palms = [palm_sprite(i) for i in range(3)]
        for ty in range(3, MH - 2, 3):
            if 16 <= ty <= 23:
                continue
            x = (shore(ty) + 4) * TS + 6
            y = ty * TS + 14
            add(Obj(palms[ty % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))
        # árvores
        trees = [tree_sprite(k, 100 + k * 7 + v) for k in (0, 1, 3) for v in range(2)]
        ipes = [tree_sprite(2, 300 + v) for v in range(2)]
        placed = []
        for ty in range(1, MH):
            for tx in range(MW):
                t = self.tiles[ty][tx]
                if t not in (2, 4):
                    continue
                inner = 21 <= tx <= 47 and 8 <= ty <= 33
                prob = 0.30 if t == 4 else 0.035
                if inner and t != 4:
                    continue
                if inner and not (tx > 46 or ty > 32):
                    continue
                if r.random() > prob:
                    continue
                x = tx * TS + r.randint(2, 14)
                y = ty * TS + r.randint(8, 16)
                if any(abs(x - px) < 20 and abs(y - py) < 12 for px, py in placed):
                    continue
                placed.append((x, y))
                spr = r.choice(ipes) if r.random() < 0.07 else r.choice(trees)
                add(Obj(spr, x, y, col=pygame.Rect(x - 4, y - 5, 8, 5)))
        bush = [bush_sprite(i) for i in range(3)]
        for i in range(34):
            tx, ty = r.randint(14, 54), r.randint(6, 33)
            if self.tiles[ty][tx] in (2, 4) and not (22 <= tx <= 40 and 11 <= ty <= 29):
                add(Obj(bush[i % 3], tx * TS + 8, ty * TS + 14, shadow=False))
        # NPCs
        self.npcs = [NPC(d) for d in NPC_DEFS + beach_defs()]
        for n in self.npcs:
            self.colliders.append(n.rect)
        self.npc_shadow = pygame.Surface((14, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(self.npc_shadow, (18, 10, 50, 90), (0, 0, 14, 6))
        # partículas (pólen)
        self.motes = [[r.random() * IW, r.random() * IH, r.uniform(2, 7), r.uniform(0, 6.28)] for _ in range(28)]

    def build_overlays(self):
        self.vig = pygame.Surface((IW, IH), pygame.SRCALPHA)
        for y in range(IH):
            for x in range(IW):
                dx, dy = (x - IW / 2) / (IW / 2), (y - IH / 2) / (IH / 2)
                d = math.sqrt(dx * dx * 0.8 + dy * dy)
                a = int(clamp((d - 0.62) * 230, 0, 150))
                if a:
                    self.vig.set_at((x, y), (20, 8, 40, a))
        self.tint = pygame.Surface((IW, IH))
        self.tint.fill((255, 240, 216))

    def reset_play(self, hero_i):
        self.hero_i = hero_i
        self.hero = HEROES[hero_i]
        self.frames, self.anchor = self.hero_actors[hero_i]
        self.px, self.py = 26.0 * TS, 21.0 * TS
        self.dir = "right"
        self.anim = 0.0
        self.moving = False
        self.aldeia = 55
        self.tensao = 20
        self.flags = set()
        self.vars = {}
        self.dl = None
        for n in self.npcs:
            n.talked = False
        self.cam = [self.px - IW / 2, self.py - IH / 2]
        self.hint_t = 0.0

    # --------------------------------------------------------- colisão
    def blocked(self, rect):
        if rect.left < 0 or rect.top < 0 or rect.right > MW * TS or rect.bottom > MH * TS:
            return True
        for qx, qy in ((rect.left, rect.top), (rect.right - 1, rect.top),
                       (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1)):
            if self.tiles[qy // TS][qx // TS] == 0:
                return True
        return rect.collidelist(self.colliders) != -1

    # ----------------------------------------------------------- diálogo
    def fmt(self, s):
        h = self.hero
        f = h["genero"] == "f"
        return s.format(nome=h["nome"], Filho="Minha filha" if f else "Meu filho",
                        filho="filha" if f else "filho", trait=h["id"])

    def resolve(self, v):
        if isinstance(v, dict):
            v = v[self.hero["id"]]
        return self.fmt(v)

    def start_dialogue(self, npc):
        did = npc.dlg
        tree = DLG[did]
        if did == "beach":
            ready = sum(1 for k in ("iane", "jurema", "pira") if k in self.flags) >= 2
            key = "start" if ready else "wait"
        else:
            key = "again" if npc.talked else "start"
        npc.face = {"left": "right", "right": "left", "up": "down", "down": "up"}[self.dir]
        self.dl = dict(npc=npc, tree=tree, key=key, shown=0.0, idx=0, node=None)
        self.enter_node(key)
        self.state = "dialogue"

    def apply(self, fx, setv):
        for k, v in fx.items():
            if k == "aldeia":
                self.aldeia = clamp(self.aldeia + v, 0, 100)
            elif k == "tensao":
                self.tensao = clamp(self.tensao + v, 0, 100)
        self.vars.update(setv)

    def enter_node(self, key):
        dl = self.dl
        node = dl["tree"][key]
        dl["key"] = key
        dl["node"] = node
        dl["shown"] = 0.0
        dl["idx"] = 0
        self.apply(node["fx"], node["set"])
        if node["flag"]:
            self.flags.add(node["flag"])
        dl["text"] = self.fmt(node["text"])
        dl["choices"] = None
        if node["ch"]:
            dl["choices"] = [dict(text=self.resolve(c["text"]), nxt=self.fmt(c["nxt"]),
                                  fx=c["fx"], set=c["set"]) for c in node["ch"]]
        sp = node["sp"]
        dl["speaker"] = sp

    def dialogue_advance(self):
        dl = self.dl
        full = len(dl["text"])
        if dl["shown"] < full:
            dl["shown"] = float(full)
            return
        if dl["choices"]:
            c = dl["choices"][dl["idx"]]
            self.apply(c["fx"], c["set"])
            self.enter_node(c["nxt"])
            return
        node = dl["node"]
        if node["nxt"]:
            self.enter_node(self.fmt(node["nxt"]))
            return
        # fim da conversa
        if dl["key"] != "wait":
            for n in self.npcs:
                if n.dlg == dl["npc"].dlg:
                    n.talked = True
        end = node["end"]
        self.dl = None
        if end:
            self.begin_ending(end)
        else:
            self.state = "play"

    def begin_ending(self, outcome):
        bonus = 0
        extra = ""
        if self.vars.get("postura") == outcome:
            bonus = 8
            extra = "Sua palavra honrou o que o conselho de Pirá havia decidido. "
        self.aldeia = clamp(self.aldeia + bonus, 0, 100)
        h = self.hero
        txt = ENDINGS[outcome] + "\n\n" + extra + TRAIT_LINE[h["id"]].format(nome=h["nome"])
        if self.aldeia >= 70:
            txt += " A aldeia canta o seu nome na roda do fogo."
        elif self.aldeia < 40:
            txt += " Mas a aldeia ficou dividida, e os murmúrios não cessam."
        if self.tensao >= 60:
            txt += " No ar, porém, há faíscas: o navio guarda mais arcabuzes do que parece."
        elif self.tensao <= 15:
            txt += " Por ora, reina uma calma incomum na praia."
        self.ending = dict(text=txt, t=0.0)
        self.state = "ending"

    # --------------------------------------------------------- objetivos
    def objective(self):
        c = sum(1 for k in ("iane", "jurema", "pira") if k in self.flags)
        if c < 2:
            return "Ouça a aldeia: fale com Ianê, Jurema e Pirá (%d/3)" % c
        return "Vá à praia e responda aos portugueses"

    # ------------------------------------------------------------- loop
    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.t += dt
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    self.on_key(e.key)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def on_key(self, k):
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        up = (pygame.K_UP, pygame.K_w)
        dn = (pygame.K_DOWN, pygame.K_s)
        lf = (pygame.K_LEFT, pygame.K_a)
        rt = (pygame.K_RIGHT, pygame.K_d)
        st = self.state
        if st == "title":
            if k in up or k in dn:
                self.menu_i = 1 - self.menu_i
            elif k in yes:
                if self.menu_i == 0:
                    self.state = "select"
                else:
                    pygame.quit()
                    sys.exit()
        elif st == "select":
            if k in lf:
                self.sel = (self.sel - 1) % 4
            elif k in rt:
                self.sel = (self.sel + 1) % 4
            elif k in yes:
                self.reset_play(self.sel)
                self.state = "intro"
                self.intro_t = 0.0
            elif k == pygame.K_ESCAPE:
                self.state = "title"
        elif st == "intro":
            if k in yes or k == pygame.K_ESCAPE:
                self.state = "play"
        elif st == "play":
            if k in yes:
                n = self.near_npc()
                if n:
                    self.start_dialogue(n)
            elif k in (pygame.K_TAB, pygame.K_j):
                self.state = "journal"
            elif k == pygame.K_ESCAPE:
                self.state = "pause"
        elif st == "journal":
            if k in (pygame.K_TAB, pygame.K_j, pygame.K_ESCAPE) or k in yes:
                self.state = "play"
        elif st == "pause":
            if k == pygame.K_ESCAPE or k in yes:
                self.state = "play"
            elif k == pygame.K_q:
                self.state = "title"
        elif st == "dialogue":
            dl = self.dl
            if dl["choices"] and dl["shown"] >= len(dl["text"]):
                if k in up:
                    dl["idx"] = (dl["idx"] - 1) % len(dl["choices"])
                    return
                if k in dn:
                    dl["idx"] = (dl["idx"] + 1) % len(dl["choices"])
                    return
                if pygame.K_1 <= k <= pygame.K_4:
                    i = k - pygame.K_1
                    if i < len(dl["choices"]):
                        dl["idx"] = i
                        self.dialogue_advance()
                    return
            if k in yes:
                self.dialogue_advance()
        elif st == "ending":
            if k in yes and self.ending["t"] > 1.5:
                self.state = "title"

    def near_npc(self):
        best, bd = None, 26.0
        for n in self.npcs:
            d = math.hypot(n.x - self.px, n.y - self.py)
            if d < bd:
                best, bd = n, d
        return best

    # ----------------------------------------------------------- update
    def update(self, dt):
        if self.state == "play":
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            self.moving = bool(dx or dy)
            if self.moving:
                n = math.hypot(dx, dy)
                vx, vy = dx / n * 58 * dt, dy / n * 58 * dt
                nx = self.px + vx
                if not self.blocked(pygame.Rect(int(nx) - 4, int(self.py) - 4, 8, 4)):
                    self.px = nx
                ny = self.py + vy
                if not self.blocked(pygame.Rect(int(self.px) - 4, int(ny) - 4, 8, 4)):
                    self.py = ny
                if dx:
                    self.dir = "right" if dx > 0 else "left"
                else:
                    self.dir = "down" if dy > 0 else "up"
                self.anim += dt
            else:
                self.anim = 0.0
        elif self.state == "dialogue":
            dl = self.dl
            dl["shown"] = min(float(len(dl["text"])), dl["shown"] + dt * 60)
        elif self.state == "ending":
            self.ending["t"] += dt
        elif self.state == "intro":
            self.intro_t += dt
        # câmera
        if self.state in ("title", "select"):
            tx = 27 * TS + math.sin(self.t * 0.15) * 150 - IW / 2
            ty = 18 * TS + math.sin(self.t * 0.11) * 40 - IH / 2
            self.cam[0] += (tx - self.cam[0]) * 0.03
            self.cam[1] += (ty - self.cam[1]) * 0.03
        else:
            tx, ty = self.px - IW / 2, self.py - IH / 2 - 6
            self.cam[0] += (tx - self.cam[0]) * 0.14
            self.cam[1] += (ty - self.cam[1]) * 0.14
        self.cam[0] = clamp(self.cam[0], 0, MW * TS - IW)
        self.cam[1] = clamp(self.cam[1], 0, MH * TS - IH)

    # ------------------------------------------------------------ render
    def render_world(self):
        f = self.frame
        cx, cy = int(self.cam[0]), int(self.cam[1])
        t = self.t
        f.blit(self.ground, (0, 0), (cx, cy, IW, IH))
        # água animada
        for ty in range(cy // TS, min(MH, (cy + IH) // TS + 1)):
            sx = shore(ty)
            for tx in range(cx // TS, min(sx, (cx + IW) // TS + 1)):
                hsh = (tx * 7 + ty * 13) % 11
                v = math.sin(t * 1.6 + hsh)
                if v > 0.55:
                    px, py = tx * TS + 3 + hsh % 6 - cx, ty * TS + 5 + (hsh * 3) % 8 - cy
                    pygame.draw.rect(f, (190, 228, 244), (px, py, 5 + int(v * 3), 1))
            # espuma pulsando
            fx = sx * TS - 4 + int(math.sin(t * 1.8 + ty) * 1.5) - cx
            if -4 < fx < IW:
                pygame.draw.rect(f, (240, 250, 252), (fx, ty * TS - cy, 2, TS))
        # coleta
        vis = []
        for o in self.objs:
            spr = o.surf(t)
            w, h = spr.get_size()
            by = o.y + (math.sin(t * 1.3) * o.bob if o.bob else 0)
            px, py = int(o.x - w // 2 - cx), int(by - h - cy)
            if px + w < -30 or px > IW + 30 or py + h < -30 or py > IH + 30:
                continue
            vis.append((o.y, spr, px, py, o))
        # sombras
        for _, spr, px, py, o in vis:
            if o.shadow is not None:
                f.blit(o.shadow, (px + 2, py + spr.get_height() - 1))
        for n in self.npcs:
            f.blit(self.npc_shadow, (int(n.x - 7 - cx), int(n.y - 4 - cy)))
        f.blit(self.npc_shadow, (int(self.px - 7 - cx), int(self.py - 4 - cy)))
        # atores
        for n in self.npcs:
            fr = n.frames[n.face][0]
            hop = int(abs(math.sin(t * 5 + n.x)) * 2) if n.hop and self.state != "dialogue" else 0
            px, py = int(n.x - n.anchor[0] - cx), int(n.y - n.anchor[1] - cy - hop)
            vis.append((n.y, fr, px, py, None))
        seq = [0, 1, 0, 2]
        pf = seq[int(self.anim * 8) % 4] if self.moving else 0
        sp = self.frames[self.dir][pf]
        vis.append((self.py, sp, int(self.px - self.anchor[0] - cx), int(self.py - self.anchor[1] - cy), None))
        vis.sort(key=lambda v: v[0])
        for _, spr, px, py, _o in vis:
            f.blit(spr, (px, py))
        # brilho da fogueira
        gx, gy = int(self.fire.x - 45 - cx), int(self.fire.y - 18 - 45 - cy)
        f.blit(self.glow[int(t * 9) % 2], (gx, gy), special_flags=pygame.BLEND_RGB_ADD)
        # pólen / partículas
        for m in self.motes:
            x = (m[0] + t * m[2]) % IW
            y = (m[1] + math.sin(t * 0.8 + m[3]) * 14 + t * 1.5) % IH
            f.set_at((int(x), int(y)), (255, 244, 190))

    def post_fx(self):
        f = self.frame
        small = pygame.transform.smoothscale(f, (IW // 3, IH // 3))
        blur = pygame.transform.smoothscale(small, (IW, IH))
        for i in range(10):
            a = int(255 * (1 - i / 10.0))
            blur.set_alpha(a)
            f.blit(blur, (0, i * 4), (0, i * 4, IW, 4))
            f.blit(blur, (0, IH - (i + 1) * 4), (0, IH - (i + 1) * 4, IW, 4))
        f.blit(self.tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        f.blit(self.vig, (0, 0))

    # -------------------------------------------------------- UI helpers
    def text(self, s, font, col, pos, center=False, shadow=True, right=False):
        img = font.render(s, True, col)
        r = img.get_rect()
        if center:
            r.center = pos
        elif right:
            r.topright = pos
        else:
            r.topleft = pos
        if shadow:
            sh = font.render(s, True, (20, 12, 40))
            self.screen.blit(sh, (r.x + 2, r.y + 2))
        self.screen.blit(img, r)
        return r

    def text_outline(self, s, font, col, oc, pos, w=4):
        img = font.render(s, True, col)
        oi = font.render(s, True, oc)
        r = img.get_rect(center=pos)
        for dx in range(-w, w + 1, 2):
            for dy in range(-w, w + 1, 2):
                self.screen.blit(oi, (r.x + dx, r.y + dy))
        self.screen.blit(img, r)

    def panel(self, rect, alpha=215, border=(255, 255, 255)):
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, (24, 18, 54, alpha), (0, 0, rect[2], rect[3]), border_radius=16)
        self.screen.blit(s, (rect[0], rect[1]))
        pygame.draw.rect(self.screen, border, rect, 3, border_radius=16)

    def draw_sprite_big(self, spr, pos, scale):
        big = pygame.transform.scale(spr, (spr.get_width() * scale, spr.get_height() * scale))
        self.screen.blit(big, pos)

    # --------------------------------------------------------------- HUD
    def draw_hud(self):
        s = self.screen
        # faixa do local
        pygame.draw.polygon(s, (22, 20, 54), [(430, 0), (850, 0), (826, 40), (454, 40)])
        pygame.draw.polygon(s, (255, 255, 255), [(430, 0), (850, 0), (826, 40), (454, 40)], 2)
        self.text("Aldeia Ibiraçu - Pindorama, c. 1550", self.f_med, (255, 255, 255), (640, 20), center=True)
        # objetivo
        self.panel((18, 52, 480, 38), 170)
        self.text(self.objective(), self.f_sm, (255, 236, 170), (32, 62))
        # balão com barras + minimapa
        tab = pygame.Rect(890, 566, 290, 88)
        pygame.draw.rect(s, (20, 14, 40), tab.inflate(8, 8), border_radius=12)
        pygame.draw.rect(s, (255, 255, 255), tab, border_radius=10)
        cc, rr = (1196, 620), 66
        pygame.draw.circle(s, (20, 14, 40), cc, rr + 5)
        pygame.draw.circle(s, (255, 255, 255), cc, rr)
        for i, (lab, val, col) in enumerate((("Vínculo com a aldeia", self.aldeia, (66, 190, 150)),
                                              ("Tensão com os navegantes", self.tensao, (190, 30, 70)))):
            y = 574 + i * 38
            self.text(lab, self.f_xs, (40, 30, 70), (904, y), shadow=False)
            pygame.draw.rect(s, (20, 14, 40), (902, y + 16, 208, 14))
            pygame.draw.rect(s, (60, 50, 80), (904, y + 18, 204, 10))
            pygame.draw.rect(s, col, (904, y + 18, int(204 * val / 100), 10))
        # minimapa circular
        px_, py_ = int(self.px / TS * 2), int(self.py / TS * 2)
        crop = pygame.Surface((64, 64))
        crop.fill((96, 150, 214))
        crop.blit(self.mini, (32 - px_, 32 - py_))
        pygame.draw.rect(crop, (230, 40, 40), (30, 30, 4, 4))
        for n in self.npcs:
            if n.quest and not n.talked:
                nx, ny = int(n.x / TS * 2) - px_ + 32, int(n.y / TS * 2) - py_ + 32
                if 0 <= nx < 63 and 0 <= ny < 63:
                    crop.fill((255, 240, 80), (nx, ny, 3, 3))
        big = pygame.transform.scale(crop, (120, 120)).convert_alpha()
        mask = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (60, 60), 58)
        big.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(big, (cc[0] - 60, cc[1] - 60))

    def draw_bubbles(self):
        cx, cy = int(self.cam[0]), int(self.cam[1])
        near = self.near_npc() if self.state == "play" else None
        ready = sum(1 for k in ("iane", "jurema", "pira") if k in self.flags) >= 2
        for n in self.npcs:
            show_q = False
            if n.quest:
                if n.dlg == "beach":
                    show_q = ready and not n.talked
                else:
                    show_q = not n.talked
            if not show_q and n is not near:
                continue
            fr = n.frames[n.face][0]
            sx = int((n.x - cx) * SC)
            sy = int((n.y - n.anchor[1] - cy) * SC) - 22 + int(math.sin(self.t * 4) * 4)
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H:
                continue
            if n is near:
                pygame.draw.circle(self.screen, (20, 14, 40), (sx, sy), 24)
                pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), 21)
                self.text("E", self.f_big, (40, 150, 110), (sx, sy), center=True, shadow=False)
            else:
                pygame.draw.circle(self.screen, (20, 14, 40), (sx, sy), 24)
                pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), 21)
                self.text("?", self.f_big, (40, 190, 120), (sx, sy), center=True, shadow=False)

    # --------------------------------------------------------- diálogo UI
    def draw_dialogue(self):
        dl = self.dl
        s = self.screen
        box = (50, 396, 1180, 312)
        self.panel(box, 232)
        sp = dl["speaker"]
        name = self.hero["nome"] if sp == "HERO" else sp
        tw = self.f_med.size(name)[0] + 50
        pygame.draw.rect(s, (255, 214, 120), (86, 366, tw, 44), border_radius=12)
        pygame.draw.rect(s, (24, 18, 54), (86, 366, tw, 44), 3, border_radius=12)
        self.text(name, self.f_med, (40, 24, 20), (111, 376), shadow=False)
        # retrato
        sprite = None
        for n in self.npcs:
            if sp.startswith(n.name) or sp.startswith(n.name.split()[-1]):
                sprite = n.frames["down"][0]
                break
        if sprite is None:
            sprite = self.frames["down"][0]
        self.draw_sprite_big(sprite, (96, 430), 7 if sprite.get_height() > 30 else 6)
        # texto
        txt = dl["text"][:int(dl["shown"])]
        lines = wrap(txt, self.f_txt, 900)
        y = 424
        for ln in lines:
            self.text(ln, self.f_txt, (255, 255, 255), (300, y), shadow=False)
            y += 30
        full = dl["shown"] >= len(dl["text"])
        if dl["choices"] and full:
            y += 12
            for i, c in enumerate(dl["choices"]):
                sel = i == dl["idx"]
                ls = wrap("%d. %s" % (i + 1, c["text"]), self.f_ch, 880)
                hh = 26 * len(ls) + 6
                if sel:
                    pygame.draw.rect(s, (255, 214, 120), (292, y - 2, 906, hh), border_radius=8)
                for ln in ls:
                    self.text(ln, self.f_ch, (40, 24, 20) if sel else (255, 236, 190), (302, y + 1), shadow=False)
                    y += 26
                y += 8
        elif full:
            self.text("[E] continuar", self.f_xs, (255, 214, 120), (1196, 678), right=True, shadow=False)

    # ----------------------------------------------------------- telas
    def draw_title(self):
        s = self.screen
        if not hasattr(self, "title_shade"):
            self.title_shade = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(H):
                a = int(120 - 90 * (i / H)) if i < H // 2 else int(40 + 140 * ((i - H / 2) / (H / 2)))
                pygame.draw.line(self.title_shade, (18, 10, 40, a), (0, i), (W, i))
        s.blit(self.title_shade, (0, 0))
        self.text_outline("PINDORAMA", self.f_title, (255, 255, 255), (222, 74, 150), (640, 190), 6)
        self.text("Raízes do Brasil", self.f_big, (255, 226, 150), (640, 290), center=True)
        for i, lab in enumerate(("Novo Jogo", "Sair")):
            col = (255, 214, 120) if i == self.menu_i else (235, 235, 245)
            r = pygame.Rect(0, 0, 380, 64)
            r.center = (640, 430 + i * 84)
            if i == self.menu_i:
                pygame.draw.rect(s, (24, 18, 54), r, border_radius=16)
                pygame.draw.rect(s, (255, 214, 120), r, 4, border_radius=16)
            self.text(lab, self.f_big, col, r.center, center=True)
        self.text("Cenário 1: A Chegada   |   Cenário 2 e 3: em breve", self.f_sm, (230, 230, 245), (640, 650), center=True)
        self.text("Setas + Enter", self.f_xs, (200, 200, 220), (640, 680), center=True)

    def draw_select(self):
        s = self.screen
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((14, 8, 36, 175))
        s.blit(ov, (0, 0))
        self.text("Escolha quem você será", self.f_big, (255, 255, 255), (640, 48), center=True)
        self.text("Nesta época, o(a) protagonista é um(a) indígena do litoral. A personalidade muda falas e opções.",
                  self.f_sm, (255, 226, 150), (640, 88), center=True)
        for i, h in enumerate(HEROES):
            x = 40 + i * 304
            sel = i == self.sel
            y = 120 if sel else 140
            rect = (x, y, 286, 520 if sel else 490)
            self.panel(rect, 235, (255, 214, 120) if sel else (150, 150, 190))
            spr = self.hero_actors[i][0]["down"][0]
            self.draw_sprite_big(spr, (x + 143 - spr.get_width() * 3, y + 24), 6)
            self.text(h["nome"], self.f_big, (255, 255, 255), (x + 143, y + 250), center=True)
            self.text(h["titulo"], self.f_med, (255, 214, 120), (x + 143, y + 284), center=True)
            self.text(h["pele"] + " - " + ("Mulher" if h["genero"] == "f" else "Homem"), self.f_xs,
                      (210, 210, 235), (x + 143, y + 312), center=True)
            yy = y + 336
            for ln in wrap(h["desc"], self.f_sm, 250):
                self.text(ln, self.f_sm, (240, 240, 250), (x + 18, yy), shadow=False)
                yy += 22
        self.text("<  >  escolher        Enter confirmar        Esc voltar", self.f_sm, (230, 230, 245), (640, 692), center=True)

    def draw_intro(self):
        s = self.screen
        s.fill((10, 6, 24))
        a = clamp(self.intro_t / 1.5, 0, 1)
        lines = ["CENÁRIO 1 - A CHEGADA", "Litoral do Brasil, c. 1550", "",
                 "Há milhares de luas esta terra se chama Pindorama.",
                 "Hoje, o mar trouxe uma casa que flutua.",
                 "Os anciãos se reúnem. Os navegantes esperam na praia.",
                 "", "Você é %s, %s." % (self.hero["nome"], self.hero["titulo"].lower()),
                 "Suas escolhas serão guiadas pelo seu jeito de ser.", "", "[Enter]"]
        y = 130
        for i, ln in enumerate(lines):
            col = (255, 214, 120) if i < 2 else (235, 235, 245)
            c = tuple(int(v * a) for v in col)
            self.text(ln, self.f_big if i == 0 else self.f_med, c, (640, y), center=True, shadow=False)
            y += 64 if i == 0 else 46

    def draw_journal(self):
        self.panel((160, 90, 960, 540), 240)
        h = self.hero
        self.text("Diário de %s - %s" % (h["nome"], h["titulo"]), self.f_big, (255, 255, 255), (200, 116))
        y = 190
        for ln in wrap(h["desc"], self.f_txt, 880):
            self.text(ln, self.f_txt, (235, 235, 245), (200, y), shadow=False)
            y += 30
        y += 14
        self.text("Vínculo com a aldeia: %d / 100" % self.aldeia, self.f_med, (110, 230, 190), (200, y))
        self.text("Tensão com os navegantes: %d / 100" % self.tensao, self.f_med, (255, 120, 150), (200, y + 40))
        y += 100
        names = (("iane", "Kunhã Ianê (anciã)"), ("jurema", "Pajé Jurema"), ("pira", "Morubixaba Pirá"))
        self.text("Conselhos da aldeia:", self.f_med, (255, 214, 120), (200, y))
        for i, (k, lab) in enumerate(names):
            mark = "[x] " if k in self.flags else "[ ] "
            self.text(mark + lab, self.f_txt, (240, 240, 250), (220, y + 38 + i * 30), shadow=False)
        self.text("Objetivo: " + self.objective(), self.f_sm, (255, 236, 170), (200, 570))

    def draw_ending(self):
        s = self.screen
        a = clamp(self.ending["t"] / 1.5, 0, 1)
        s.fill((10, 6, 24))
        col = lambda c: tuple(int(v * a) for v in c)
        self.text("FIM DO CENÁRIO 1", self.f_big, col((255, 214, 120)), (640, 80), center=True, shadow=False)
        y = 150
        for ln in wrap(self.ending["text"], self.f_txt, 980):
            self.text(ln, self.f_txt, col((240, 240, 250)), (150, y), shadow=False)
            y += 32
        y += 24
        self.text("Vínculo com a aldeia: %d" % self.aldeia, self.f_med, col((110, 230, 190)), (150, y), shadow=False)
        self.text("Tensão com os navegantes: %d" % self.tensao, self.f_med, col((255, 120, 150)), (150, y + 40), shadow=False)
        self.text("Próximos: Cenário 2 e Cenário 3 (em breve)", self.f_sm, col((200, 200, 225)), (640, 640), center=True, shadow=False)
        if self.ending["t"] > 1.5:
            self.text("[Enter] voltar ao menu", self.f_sm, (255, 214, 120), (640, 680), center=True, shadow=False)

    def draw_pause(self):
        self.panel((420, 250, 440, 200), 235)
        self.text("PAUSA", self.f_big, (255, 255, 255), (640, 296), center=True)
        self.text("Esc / Enter: continuar", self.f_txt, (235, 235, 245), (640, 360), center=True)
        self.text("Q: voltar ao menu", self.f_txt, (235, 235, 245), (640, 396), center=True)

    # -------------------------------------------------------------- draw
    def draw(self):
        st = self.state
        if st in ("intro", "ending"):
            if st == "intro":
                self.draw_intro()
            else:
                self.draw_ending()
            return
        self.render_world()
        self.post_fx()
        pygame.transform.scale(self.frame, (W, H), self.screen)
        if st == "title":
            self.draw_title()
        elif st == "select":
            self.draw_select()
        else:
            self.draw_hud()
            self.draw_bubbles()
            if st == "dialogue":
                self.draw_dialogue()
            elif st == "journal":
                self.draw_journal()
            elif st == "pause":
                self.draw_pause()
            elif st == "play":
                self.text("Tab: diário    Esc: pausa", self.f_xs, (255, 255, 255), (W - 18, 12), right=True)


if __name__ == "__main__":
    Game().run()