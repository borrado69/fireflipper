# -*- coding: utf-8 -*-
"""
AGENTE ROSSO - Operação Verdade (Rio de Janeiro, 1970)
Você é o Agente Rosso, um porco espião de uma rede clandestina.
Sua missão: percorrer o Rio de Janeiro, conversar com as pessoas, reunir provas dos abusos da ditadura
militar e entregar o dossiê a uma correspondente estrangeira.

Visual: pixel art cartunesca ao entardecer - paralelepípedos coloridos, prédios de tijolo
com janelas acesas, letreiros de néon, postes com brilho, personagens "chibi" com contorno,
profundidade de campo (tilt-shift), bloom de luz, vinheta e partículas flutuando.

Requisitos:  pip install pygame
Executar:    python ditadura.py

Controles
  Setas / WASD ... andar          E / Espaço / Enter ... falar / avançar
  Setas / 1-4 ..... escolher       Tab / J ... diário      Esc ... pausa      F11 ... tela cheia
  Shift ... correr          Puzzles: setas / 1-4 / 0-9, Enter confirma, Esc sai

Observação: todos os personagens são fictícios (arquétipos de pessoas reais da época).
"""
import math
import random
import sys
import textwrap

import pygame

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
W, H = 1280, 720          # janela
IW, IH = 320, 180         # resolução interna (pixel art)
SC = W // IW              # escala = 4
TS = 16                   # tamanho do tile
MW, MH = 112, 92          # mapa em tiles (o Rio: praia, Forte, Centro, Lapa, Praça XV, parque e morro)
OX, OY = 24, 18           # deslocamento da praça central original dentro do mapa novo
AV0, AV1 = 24, 34         # avenida Atlântica: tiles x de 24 a 33
BEACH_E = 20              # fim da areia; daqui até a avenida fica o calçadão
FPS = 60

PIXEL_TEXT = True         # True = texto "pixelado" (grosso); False = texto suave

OUTLINE = (34, 18, 52)
SHADOW_TINT = (58, 28, 104)
LIGHT_TINT = (255, 236, 190)


def shade(c, d):
    return tuple(max(0, min(255, v + d)) for v in c[:3])


def clamp(v, a, b):
    return max(a, min(b, v))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tone(c, k):
    """k < 0 escurece puxando para o roxo; k > 0 clareia puxando para o creme quente."""
    if k < 0:
        return mix(c, SHADOW_TINT, min(1.0, -k))
    return mix(c, LIGHT_TINT, min(1.0, k))


# ----------------------------------------------------------------------------
# Protagonista: Agente Rosso, o porco espião
# ----------------------------------------------------------------------------
HERO = dict(nome="Agente Rosso", titulo="Porco Espião",
            desc="Um porco de sobretudo e óculos escuros, a serviço de uma rede clandestina de "
                 "informação. Curioso, discreto e teimoso: quer mostrar ao mundo o que a ditadura esconde.",
            p=dict(pig=True))

TESTIMONIES = ("cida", "tavares", "zeca", "lucia", "dom", "nelson")
PROBLEMS = (("cida", "Desaparecimentos forçados (Dona Cida)"),
            ("tavares", "Censura à imprensa (Tavares)"),
            ("zeca", "Censura às artes (Zeca)"),
            ("lucia", "Repressão estudantil e AI-5 (Lúcia)"),
            ("dom", "Tortura e perseguição (Dom Aurélio)"),
            ("nelson", "Arrocho salarial e greves proibidas (Seu Nelson)"))
NEEDED = 3                # testemunhos necessários para a entrega final
TIME_LIMIT = 15 * 60      # cada final dura no máximo 15 minutos (a Central corta a linha no prazo)
RUN_MULT = 1.6            # Shift = correr

# ----------------------------------------------------------------------------
# Mini fonte 3x5 para letreiros (maiúsculas, sem acentos)
# ----------------------------------------------------------------------------
GLYPHS = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"), "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"), "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"), "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"), "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"), "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"), "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#.#", "###", "###", "#.#", "#.#"), "N": ("###", "#.#", "#.#", "#.#", "#.#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."), "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "##.", ".##"), "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."), "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"), "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#.#", "#.#", "###", "###", "#.#"), "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."), "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"), "1": (".#.", "##.", ".#.", ".#.", "###"),
    "7": ("###", "..#", ".#.", ".#.", ".#."), "9": ("###", "#.#", "###", "..#", "###"),
    "!": (".#.", ".#.", ".#.", "...", ".#."), "-": ("...", "...", "###", "...", "..."),
    ".": ("...", "...", "...", "...", ".#."), "&": (".#.", "#.#", ".#.", "#.#", ".##"),
}


def tiny_width(text):
    w = 0
    for ch in text.upper():
        w += 4 if ch in GLYPHS else 2
    return max(0, w - 1)


def draw_tiny(s, text, x, y, col, shadow=None):
    for pas in ((0, 1) if shadow else (1,)):
        cx = x
        for ch in text.upper():
            g = GLYPHS.get(ch)
            if g is None:
                cx += 2
                continue
            for ry, row in enumerate(g):
                for rx, v in enumerate(row):
                    if v == "#":
                        if pas == 0:
                            s.set_at((cx + rx, y + ry + 1), shadow)
                        else:
                            s.set_at((cx + rx, y + ry), col)
            cx += 4


# ----------------------------------------------------------------------------
# Sprites de personagens (pixel art gerada por código)
# ----------------------------------------------------------------------------
CW, CHH = 18, 30      # canvas do personagem (antes do contorno)


def make_pig(d, f):
    """Agente Rosso: porco de sobretudo, chapéu e óculos escuros."""
    s = pygame.Surface((CW, CHH), pygame.SRCALPHA)

    def R(x, y, w, h, c):
        pygame.draw.rect(s, c, (x + 1, y + 5, w, h))

    def P(x, y, c):
        s.set_at((x + 1, y + 5), c)

    pink, pk_hi, pk_lo, pk_dk = (250, 170, 188), (255, 214, 220), (222, 124, 152), (176, 82, 116)
    hoof = (110, 54, 84)
    coat = (176, 138, 96)
    coat_hi, coat_lo, coat_dk = tone(coat, .28), tone(coat, -.28), tone(coat, -.5)
    hat, band = (62, 46, 78), (214, 62, 66)
    lens, glint = (22, 14, 30), (130, 190, 230)
    la = lb = aa = ab = 0
    if f == 1:
        la, aa, ab = -1, 1, -1
    elif f == 2:
        lb, aa, ab = -1, -1, 1

    def legs(x1, x2):
        R(x1, 17, 2, 3 + la, pink)
        R(x2, 17, 2, 3 + lb, pink)
        R(x1 - 1, 20 + la, 3, 2, hoof)
        R(x2 - 1, 20 + lb, 3, 2, hoof)
        R(x1 - 1, 20 + la, 3, 1, tone(hoof, .25))

    def hat_on(face_shadow=True):
        R(4, -2, 8, 3, hat)
        R(4, -2, 8, 1, tone(hat, .3))
        R(4, 1, 8, 1, band)
        R(2, 2, 12, 1, tone(hat, .12))
        if face_shadow:
            R(3, 3, 10, 1, tone(pink, -.45))

    if d == "down":
        legs(5, 9)
        # sobretudo
        R(4, 10, 8, 8, coat)
        R(4, 10, 1, 8, coat_hi)
        R(11, 10, 1, 8, coat_lo)
        R(4, 17, 8, 1, coat_dk)
        R(4, 13, 8, 1, coat_dk)
        R(7, 13, 2, 1, (238, 196, 80))        # fivela
        R(7, 10, 2, 3, (246, 242, 232))       # camisa
        R(7, 11, 2, 2, band)                  # gravata
        R(5, 10, 2, 3, coat_hi)
        R(9, 10, 2, 3, coat_hi)               # lapelas
        # braços
        R(2, 10 + aa, 2, 5, coat)
        R(12, 10 + ab, 2, 5, coat_lo)
        R(2, 15 + aa, 2, 1, pink)
        R(12, 15 + ab, 2, 1, pink)
        # orelhas e cabeça
        R(2, 3, 2, 3, pk_lo)
        R(12, 3, 2, 3, pk_lo)
        R(3, 2, 10, 7, pink)
        R(4, 9, 8, 1, pk_lo)
        R(4, 2, 3, 1, pk_hi)
        # óculos escuros
        R(4, 4, 8, 1, lens)
        R(4, 5, 3, 2, lens)
        R(9, 5, 3, 2, lens)
        P(5, 5, glint)
        P(10, 5, glint)
        # focinho
        R(6, 7, 4, 3, pk_hi)
        P(7, 8, pk_dk)
        P(8, 8, pk_dk)
        R(6, 9, 4, 1, pk_lo)
        P(4, 7, mix(pink, (255, 120, 140), .6))
        P(11, 7, mix(pink, (255, 120, 140), .6))
        hat_on()
    elif d == "up":
        legs(5, 9)
        R(4, 10, 8, 8, coat)
        R(4, 10, 1, 8, coat_hi)
        R(11, 10, 1, 8, coat_lo)
        R(4, 17, 8, 1, coat_dk)
        R(4, 13, 8, 1, coat_dk)
        R(7, 14, 1, 4, coat_dk)               # abertura traseira
        R(4, 10, 8, 1, coat_hi)
        # rabinho enrolado
        P(7, 17, pk_lo)
        P(8, 16, pk_lo)
        P(9, 17, pk_lo)
        R(2, 10 + aa, 2, 5, coat)
        R(12, 10 + ab, 2, 5, coat_lo)
        R(2, 15 + aa, 2, 1, pink)
        R(12, 15 + ab, 2, 1, pink)
        R(2, 3, 2, 3, pk_lo)
        R(12, 3, 2, 3, pk_lo)
        R(3, 2, 10, 7, pink)
        R(4, 9, 8, 1, pk_lo)
        R(4, 3, 8, 1, pk_lo)
        hat_on(False)
    else:  # lado direito
        legs(5, 8)
        R(4, 10, 8, 8, coat)
        R(4, 10, 8, 1, coat_hi)
        R(4, 13, 8, 1, coat_dk)
        R(4, 17, 8, 1, coat_dk)
        R(11, 10, 1, 8, coat_lo)
        R(8, 13, 2, 1, (238, 196, 80))
        # rabinho
        P(3, 14, pk_lo)
        P(2, 13, pk_lo)
        P(2, 12, pk_lo)
        P(3, 11, pk_lo)
        # braço da frente
        R(6, 10 + aa, 3, 5, coat_lo)
        R(6, 10 + aa, 3, 1, coat)
        R(6, 15 + aa, 3, 1, pink)
        # cabeça de lado
        R(3, 2, 9, 7, pink)
        R(4, 9, 7, 1, pk_lo)
        R(4, 2, 3, 1, pk_hi)
        R(5, 3, 3, 4, pk_lo)                  # orelha caída
        R(5, 3, 1, 1, pk_dk)
        # focinho
        R(11, 5, 4, 4, pk_hi)
        R(14, 6, 1, 2, pk_dk)
        R(11, 8, 4, 1, pk_lo)
        # óculos
        R(8, 4, 5, 1, lens)
        R(9, 5, 3, 2, lens)
        P(9, 5, glint)
        R(5, 4, 3, 1, lens)
        P(9, 8, mix(pink, (255, 120, 140), .6))
        hat_on()
    return s


def make_char(p, d, f):
    """Desenha um personagem chibi (dentro de um canvas com margem)."""
    if d == "left":
        s = make_char(p, "right", f)
        return pygame.transform.flip(s, True, False)
    if p.get("pig"):
        return make_pig(d, f)
    s = pygame.Surface((CW, CHH), pygame.SRCALPHA)

    def R(x, y, w, h, c):
        pygame.draw.rect(s, c, (x + 1, y + 5, w, h))

    def P(x, y, c):
        s.set_at((x + 1, y + 5), c)

    skin = p["skin"]
    sk_hi, sk_lo = tone(skin, .22), tone(skin, -.24)
    hair = p["hair"]
    h_hi, h_lo = tone(hair, .34), tone(hair, -.38)
    dark = (30, 18, 32)
    blush = mix(skin, (255, 110, 120), .5)
    mouth = mix(skin, (150, 50, 64), .6)
    la = lb = aa = ab = 0
    if f == 1:
        la, aa, ab = -1, 1, -1
    elif f == 2:
        lb, aa, ab = -1, -1, 1
    legc = p.get("legs") or skin
    shoes = p.get("shoes") or tone(skin, -.4)
    top = p.get("top") or skin
    skirt = p.get("skirt")
    armc = p.get("sleeve") or skin
    style = p.get("style", "short")
    side = d == "right"

    # ---- pernas
    lx1, lx2 = (5, 8)
    R(lx1, 17, 3, 3 + la, legc)
    R(lx2, 17, 3, 3 + lb, legc)
    R(lx1, 17, 1, 3 + la, tone(legc, .18))
    R(lx2 + 2, 17, 1, 3 + lb, tone(legc, -.25))
    R(lx1 - 1, 20 + la, 4, 1, shoes)
    R(lx1 - 1, 21 + la, 4, 1, tone(shoes, -.4))
    R(lx2, 20 + lb, 4, 1, shoes)
    R(lx2, 21 + lb, 4, 1, tone(shoes, -.4))
    R(lx1, 20 + la, 2, 1, tone(shoes, .3))

    # ---- tronco
    bx, bw = (5, 7) if side else (4, 8)
    R(bx, 10, bw, 7, top)
    R(bx, 10, 1, 7, tone(top, .2))
    R(bx + bw - 1, 10, 1, 7, tone(top, -.22))
    R(bx, 16, bw, 1, tone(top, -.35))
    if not side:
        R(6, 10, 4, 1, tone(top, .38))
        if p.get("buttons", True) and d == "down":
            for yy in (12, 14):
                P(7, yy, tone(top, -.3))
    if p.get("ruff"):
        R(6, 10, 4, 1, (246, 244, 236))
        R(7, 11, 2, 1, (246, 244, 236))
    if skirt:
        sw = 9 if side else 10
        sx = 4 if side else 3
        R(sx, 14, sw, 4, skirt)
        R(sx, 14, sw, 1, tone(skirt, .25))
        R(sx, 17, sw, 1, tone(skirt, -.4))
        for k in range(sx + 2, sx + sw - 1, 3):
            R(k, 15, 1, 2, tone(skirt, -.24))

    # ---- cabelo longo / bob caindo atrás (lado e costas) são desenhados junto da cabeça
    def hair_fall(hh):
        return {"long": 12, "bob": 8, "tail": 9, "bun": 5, "short": 5}.get(hh, 5)

    # ---- braços
    if side:
        R(6, 10 + aa, 3, 5, tone(armc, -.14))
        R(6, 10 + aa, 3, 1, armc)
        R(6, 15 + aa, 3, 1, skin)
    else:
        R(2, 10 + aa, 2, 5, armc)
        R(12, 10 + ab, 2, 5, tone(armc, -.2))
        R(2, 10 + aa, 1, 5, tone(armc, .15))
        R(2, 15 + aa, 2, 1, skin)
        R(12, 15 + ab, 2, 1, sk_lo)

    # ---- cabeça
    if side:
        R(4, 2, 8, 7, skin)
        R(5, 9, 6, 1, sk_lo)
        R(12, 6, 1, 2, skin)
        P(12, 7, sk_lo)
        R(9, 5, 1, 2, dark)
        P(8, 7, blush)
        P(10, 8, mouth)
        R(6, 5, 2, 2, sk_lo)
        if style != "bald":
            R(4, 0, 8, 1, hair)
            R(3, 1, 9, 2, hair)
            R(8, 3, 4, 1, hair)
            R(3, 3, 4, hair_fall(style) - 1, hair)
            R(4, 1, 4, 1, h_hi)
            R(3, hair_fall(style) + 1, 4, 1, h_lo)
            if style == "tail":
                R(2, 4, 2, 6, hair)
                R(2, 9, 2, 1, h_lo)
            if style == "bun":
                R(3, -2, 4, 3, hair)
                R(3, -2, 2, 1, h_hi)
            if style == "long":
                R(3, 3, 4, 10, hair)
                R(3, 12, 4, 1, h_lo)
        else:
            R(5, 2, 4, 1, sk_hi)
    elif d == "up":
        R(4, 2, 8, 7, skin)
        R(5, 9, 6, 1, sk_lo)
        if style == "bald":
            R(5, 2, 4, 1, sk_hi)
            R(2, 5, 2, 2, sk_lo)
            R(12, 5, 2, 2, sk_lo)
        else:
            hl = {"long": 13, "bob": 9, "tail": 8, "bun": 8, "short": 7}.get(style, 7)
            R(3, 1, 10, hl, hair)
            R(4, 0, 8, 1, hair)
            R(4, 1, 5, 1, h_hi)
            R(3, hl, 10, 1, h_lo)
            if style == "tail":
                R(6, hl, 4, 4, hair)
                R(6, hl + 3, 4, 1, h_lo)
            if style == "bun":
                R(5, -2, 6, 3, hair)
                R(5, -2, 3, 1, h_hi)
    else:
        R(3, 2, 10, 7, skin)
        R(4, 9, 8, 1, sk_lo)
        R(3, 2, 10, 1, sk_hi)
        R(2, 5, 1, 2, sk_lo)
        R(13, 5, 1, 2, sk_lo)
        # olhos
        R(5, 5, 1, 2, dark)
        R(10, 5, 1, 2, dark)
        P(5, 5, (250, 244, 240))
        P(10, 5, (250, 244, 240))
        P(5, 6, dark)
        P(10, 6, dark)
        R(4, 7, 1, 1, blush)
        R(11, 7, 1, 1, blush)
        R(7, 8, 2, 1, mouth)
        if style != "bald":
            R(4, 0, 8, 1, hair)
            R(3, 1, 10, 2, hair)
            R(3, 3, 4, 1, hair)
            R(9, 3, 4, 1, hair)
            R(5, 3, 1, 1, h_lo)
            R(10, 3, 1, 1, h_lo)
            fall = hair_fall(style)
            R(3, 3, 1, fall - 1, hair)
            R(12, 3, 1, fall - 1, hair)
            if style in ("long", "bob", "tail"):
                R(2, 3, 2, fall + (1 if style == "long" else 0), hair)
                R(12, 3, 2, fall + (1 if style == "long" else 0), hair)
                R(2, 3 + fall, 2, 1, h_lo)
                R(12, 3 + fall, 2, 1, h_lo)
            if style == "bun":
                R(5, -2, 6, 3, hair)
                R(5, -2, 3, 1, h_hi)
            R(5, 1, 4, 1, h_hi)
        else:
            R(5, 2, 4, 1, sk_hi)
    # ---- detalhes de rosto
    if p.get("glasses") and d != "up":
        gl = (50, 36, 40)
        if side:
            R(8, 4, 4, 1, gl)
            R(8, 7, 4, 1, gl)
            R(8, 5, 1, 2, gl)
            R(11, 5, 1, 2, gl)
            R(5, 5, 3, 1, gl)
        else:
            for gx in (4, 9):
                R(gx, 4, 3, 1, gl)
                R(gx, 7, 3, 1, gl)
                R(gx, 5, 1, 2, gl)
                R(gx + 2, 5, 1, 2, gl)
            R(7, 5, 2, 1, gl)
    if p.get("beard") and d != "up":
        if side:
            R(7, 7, 5, 3, hair)
            P(10, 8, mouth)
        else:
            R(4, 7, 8, 3, hair)
            R(3, 6, 1, 3, hair)
            R(12, 6, 1, 3, hair)
            R(7, 8, 2, 1, mouth)
    # ---- adereços de cabeça
    hw = p.get("headwear")
    c = (p.get("hw") or [(60, 60, 70)])[0]
    if hw == "morion":      # capacete de operário
        R(4, -2, 8, 4, c)
        R(5, -3, 6, 1, c)
        R(3, 2, 10, 2, tone(c, -.2))
        R(4, -2, 8, 1, tone(c, .4))
        R(7, -3, 2, 5, tone(c, .3))
        R(3, 3, 10, 1, tone(skin, -.4))
    elif hw == "hat":       # chapéu / quepe
        R(4, -2, 8, 3, c)
        R(4, -2, 8, 1, tone(c, .3))
        R(4, 1, 8, 1, tone(c, -.35))
        R(1, 2, 14, 1, tone(c, .12))
        R(2, 3, 12, 1, tone(c, -.5) if d != "up" else tone(c, -.3))
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
# Sprites do cenário
# ----------------------------------------------------------------------------
def make_shadow(spr, squash=0.42, shear=0.55, alpha=78):
    w, h = spr.get_size()
    sil = pygame.mask.from_surface(spr).to_surface(setcolor=(30, 12, 64, alpha), unsetcolor=(0, 0, 0, 0))
    sh = max(3, int(h * squash))
    sq = pygame.transform.scale(pygame.transform.flip(sil, False, True), (w, sh))
    out = pygame.Surface((w + int(sh * shear) + 2, sh), pygame.SRCALPHA)
    for r in range(sh):
        out.blit(sq, (int(r * shear), r), (0, r, w, 1))
    return out


def overlay(s, rect, rgba):
    """Pinta um retângulo semitransparente sobre um sprite."""
    o = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    o.fill(rgba)
    s.blit(o, (rect[0], rect[1]))


def brick_wall(s, rect, base, r, bw=8, bh=4):
    x0, y0, w, h = rect
    mortar = tone(base, -.34)
    for row in range((h + bh - 1) // bh):
        off = 0 if row % 2 == 0 else bw // 2
        y = y0 + row * bh
        hh = min(bh, y0 + h - y)
        for bx in range(-bw, w + bw, bw):
            x = x0 + bx + off
            x1, x2 = max(x, x0), min(x + bw, x0 + w)
            if x2 <= x1:
                continue
            c = tone(shade(base, r.randint(-11, 11)), r.uniform(-.03, .06))
            pygame.draw.rect(s, c, (x1, y, x2 - x1, hh))
            pygame.draw.rect(s, tone(c, .16), (x1, y, x2 - x1, 1))
            pygame.draw.rect(s, mortar, (x1, y + hh - 1, x2 - x1, 1))
            if x + bw <= x0 + w:
                pygame.draw.rect(s, mortar, (x + bw - 1, y, 1, hh))


def roof_tiles(s, rect, base, r):
    x0, y0, w, h = rect
    for row in range(h // 4 + 1):
        off = 0 if row % 2 == 0 else 3
        y = y0 + row * 4
        hh = min(4, y0 + h - y)
        if hh <= 0:
            break
        for bx in range(-6, w + 6, 6):
            x = x0 + bx + off
            x1, x2 = max(x, x0), min(x + 6, x0 + w)
            if x2 <= x1:
                continue
            c = tone(shade(base, r.randint(-9, 9)), r.uniform(-.02, .05))
            pygame.draw.rect(s, c, (x1, y, x2 - x1, hh))
            pygame.draw.rect(s, tone(c, .25), (x1, y, x2 - x1, 1))
            pygame.draw.rect(s, tone(c, -.42), (x1, y + hh - 1, x2 - x1, 1))
            pygame.draw.rect(s, tone(c, -.2), (x2 - 1, y, 1, hh))


def window(s, x, y, w, h, lit, r, frame=(246, 230, 204), curtain=None, shutter=None, flowers=False):
    if shutter:
        for sx in (x - 4, x + w + 1):
            pygame.draw.rect(s, shutter, (sx, y, 3, h))
            for yy in range(y + 1, y + h, 2):
                pygame.draw.rect(s, tone(shutter, -.3), (sx, yy, 3, 1))
            pygame.draw.rect(s, tone(shutter, .25), (sx, y, 1, h))
    pygame.draw.rect(s, tone(frame, -.55), (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, frame, (x, y, w, h))
    gx, gy, gw, gh = x + 1, y + 1, w - 2, h - 2
    if lit:
        for i in range(gh):
            pygame.draw.rect(s, mix((255, 236, 150), (255, 150, 74), i / max(1, gh - 1)), (gx, gy + i, gw, 1))
        if curtain:
            pygame.draw.rect(s, curtain, (gx, gy, 2, gh))
            pygame.draw.rect(s, curtain, (gx + gw - 2, gy, 2, gh))
            pygame.draw.rect(s, tone(curtain, -.3), (gx + 1, gy, 1, gh))
        if r.random() < .5:   # silhueta de planta / pessoa
            pygame.draw.rect(s, (120, 60, 56), (gx + gw // 2 - 1, gy + gh - 4, 3, 4))
    else:
        for i in range(gh):
            pygame.draw.rect(s, mix((110, 132, 186), (58, 62, 110), i / max(1, gh - 1)), (gx, gy + i, gw, 1))
        pygame.draw.line(s, (180, 206, 236), (gx + 1, gy + gh - 2), (gx + 3, gy + 1), 1)
    pygame.draw.rect(s, frame, (gx + gw // 2, gy, 1, gh))
    pygame.draw.rect(s, frame, (gx, gy + gh // 2, gw, 1))
    pygame.draw.rect(s, tone(frame, .15), (x - 2, y + h, w + 4, 2))
    pygame.draw.rect(s, tone(frame, -.5), (x - 2, y + h + 2, w + 4, 1))
    if flowers:
        for k in range(w // 2):
            cc = r.choice(((236, 70, 110), (255, 200, 60), (250, 120, 170), (120, 190, 110)))
            s.set_at((x + 1 + k * 2, y + h - 1), cc)
            s.set_at((x + 1 + k * 2, y + h - 2), (60, 130, 80))
        pygame.draw.rect(s, (150, 76, 60), (x - 1, y + h - 1, w + 2, 1))


def awning(s, x, y, w, h, c1, c2):
    st = 4
    for i in range(0, w, st):
        c = c1 if (i // st) % 2 == 0 else c2
        pygame.draw.rect(s, c, (x + i, y, min(st, w - i), h))
        pygame.draw.rect(s, tone(c, .25), (x + i, y, min(st, w - i), 1))
        pygame.draw.rect(s, c, (x + i + 1, y + h, 2, 1))
        pygame.draw.rect(s, tone(c, -.35), (x + i + 1, y + h + 1, 2, 1))
        pygame.draw.rect(s, tone(c, -.3), (x + i, y + h - 1, min(st, w - i), 1))


def door(s, x, y, w, h, col, glass=True, open_light=False):
    pygame.draw.rect(s, tone(col, -.6), (x - 1, y - 1, w + 2, h + 1))
    pygame.draw.rect(s, col, (x, y, w, h))
    pygame.draw.rect(s, tone(col, .2), (x, y, 1, h))
    pygame.draw.rect(s, tone(col, -.25), (x + w - 1, y, 1, h))
    if open_light:
        for i in range(h):
            pygame.draw.rect(s, mix((255, 214, 120), (200, 90, 70), i / h), (x + 1, y + 1 + i, w - 2, 1))
        pygame.draw.rect(s, (80, 36, 56), (x + w // 2 - 1, y + h - 8, 3, 8))
        pygame.draw.rect(s, (80, 36, 56), (x + w // 2 - 1, y + h - 10, 3, 2))
    elif glass:
        pygame.draw.rect(s, (255, 220, 130), (x + 2, y + 3, w - 4, h // 2 - 2))
        pygame.draw.rect(s, tone(col, -.4), (x + w // 2, y + 3, 1, h // 2 - 2))
        pygame.draw.rect(s, (255, 244, 190), (x + 2, y + 3, w - 4, 1))
    pygame.draw.rect(s, (250, 210, 90), (x + w - 3, y + h // 2 + 2, 1, 2))


def neon_text(s, text, x, y, col, k=2):
    """Letreiro de néon: letras ampliadas k vezes, com miolo claro."""
    cx = x
    core = tone(col, .75)
    for ch in text.upper():
        g = GLYPHS.get(ch)
        if g is None:
            cx += 2 * k
            continue
        for ry, row in enumerate(g):
            for rx, v in enumerate(row):
                if v == "#":
                    pygame.draw.rect(s, tone(col, -.35), (cx + rx * k - 1, y + ry * k - 1, k + 2, k + 2))
        for ry, row in enumerate(g):
            for rx, v in enumerate(row):
                if v == "#":
                    pygame.draw.rect(s, col, (cx + rx * k, y + ry * k, k, k))
                    pygame.draw.rect(s, core, (cx + rx * k, y + ry * k, max(1, k - 1), max(1, k - 1)))
        cx += 4 * k


def pig_neon():
    """Porquinho de néon (placa de açougue)."""
    s = pygame.Surface((34, 22), pygame.SRCALPHA)
    pink, hi, lo = (244, 118, 142), (255, 196, 206), (186, 66, 104)
    pygame.draw.ellipse(s, lo, (2, 4, 24, 14))
    pygame.draw.ellipse(s, pink, (3, 4, 22, 12))
    pygame.draw.circle(s, pink, (26, 10), 6)
    pygame.draw.rect(s, hi, (29, 10, 5, 4))
    s.set_at((31, 11), lo)
    s.set_at((32, 11), lo)
    pygame.draw.polygon(s, lo, [(22, 3), (27, 1), (27, 6)])
    pygame.draw.polygon(s, pink, [(23, 4), (26, 2), (26, 5)])
    s.set_at((27, 8), (30, 14, 30))
    for lx in (6, 10, 18, 22):
        pygame.draw.rect(s, lo, (lx, 16, 3, 5))
        pygame.draw.rect(s, pink, (lx, 16, 2, 4))
    for pts in (((9, 5), (8, 15)), ((15, 4), (14, 16)), ((20, 5), (21, 15)), ((4, 9), (24, 10))):
        pygame.draw.line(s, hi, pts[0], pts[1], 1)
    for p_ in ((2, 7), (1, 6), (1, 8), (2, 9)):
        s.set_at(p_, hi)
    return s


def poster(s, x, y, w, h, col, bars=True, text=None):
    pygame.draw.rect(s, tone(col, -.5), (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, col, (x, y, w, h))
    pygame.draw.rect(s, tone(col, .3), (x, y, w, 1))
    if text:
        draw_tiny(s, text, x + (w - tiny_width(text)) // 2, y + h // 2 - 2, (30, 90, 50))
    elif bars:
        for yy in range(y + 2, y + h - 2, 3):
            pygame.draw.rect(s, (30, 20, 34), (x + 1, yy, w - 2, 2))


BW_, BH_ = 96, 96


def building_sprite(kind, seed):
    """Prédio de tijolo ao entardecer. Devolve (sprite, luzes) - luzes em coords do sprite."""
    r = random.Random(seed)
    w, h = BW_, BH_
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    cfg = {
        "acougue": dict(wall=(190, 80, 98), roof=(164, 70, 78)),
        "bar": dict(wall=(128, 60, 114), roof=(70, 140, 150)),
        "padaria": dict(wall=(66, 136, 142), roof=(206, 130, 70)),
        "hotel": dict(wall=(220, 166, 96), roof=(150, 76, 74)),
        "farmacia": dict(wall=(106, 168, 140), roof=(146, 70, 90)),
        "sobrado": dict(wall=(204, 112, 92), roof=(112, 76, 126)),
        **EXTRA_CFG,
    }[kind]
    wall, roofc = cfg["wall"], cfg["roof"]
    # telhado
    pygame.draw.rect(s, tone(roofc, -.5), (0, 3, w, 20))
    roof_tiles(s, (1, 2, w - 2, 19), roofc, r)
    pygame.draw.rect(s, tone(roofc, .35), (1, 2, w - 2, 1))
    pygame.draw.rect(s, tone(roofc, -.55), (0, 20, w, 3))
    # parede
    brick_wall(s, (3, 23, w - 6, h - 23), wall, r)
    overlay(s, (w - 14, 23, 11, h - 23), (50, 20, 90, 60))
    overlay(s, (3, 23, w - 6, 3), (40, 10, 70, 70))
    pygame.draw.rect(s, tone(wall, .35), (2, 24, w - 4, 2))
    pygame.draw.rect(s, tone(wall, -.55), (2, 26, w - 4, 1))
    pygame.draw.rect(s, tone(wall, -.6), (2, h - 4, w - 4, 4))
    # cano de descida
    pygame.draw.rect(s, (112, 112, 134), (w - 9, 26, 3, h - 30))
    pygame.draw.rect(s, (176, 176, 196), (w - 9, 26, 1, h - 30))
    for yy in range(34, h - 8, 22):
        pygame.draw.rect(s, (70, 70, 92), (w - 10, yy, 5, 1))
    cw_ = (96, 150, 190)
    sh_ = (70, 150, 120)

    def win(x, y, lit=None, **k):
        lit = (r.random() < .72) if lit is None else lit
        window(s, x, y, 14, 17, lit, r, **k)
        if lit:
            lights.append((x + 7, y + 8, 24, (112, 66, 20), 0))

    if kind == "acougue":
        win(8, 31, True, curtain=(200, 60, 80))
        win(74 - 2, 31, True, curtain=(200, 60, 80))
        # placa com porquinho de néon
        pygame.draw.rect(s, (30, 22, 56), (28, 28, 40, 25))
        pygame.draw.rect(s, (255, 150, 170), (28, 28, 40, 25), 1)
        pg = pig_neon()
        s.blit(pg, (31, 31))
        lights.append((48, 41, 38, (150, 40, 80), 1))
        awning(s, 5, 57, w - 10, 7, (210, 56, 64), (250, 240, 226))
        # vitrine
        pygame.draw.rect(s, (62, 30, 56), (7, 66, 52, 20))
        for i in range(18):
            pygame.draw.rect(s, mix((255, 226, 150), (255, 170, 100), i / 18), (8, 67 + i, 50, 1))
        for lx in (12, 24, 36, 48):     # linguiças e presuntos
            pygame.draw.rect(s, (160, 40, 48), (lx, 67, 1, 6))
            pygame.draw.ellipse(s, (200, 60, 70), (lx - 2, 72, 6, 8))
            pygame.draw.rect(s, (255, 150, 150), (lx - 1, 73, 1, 3))
        pygame.draw.rect(s, (96, 54, 48), (8, 82, 50, 4))
        pygame.draw.rect(s, (255, 244, 220), (7, 66, 52, 1))
        pygame.draw.rect(s, (255, 255, 255), (10, 68, 1, 6))
        door(s, 66, 64, 17, h - 68, (126, 68, 64))
        lights.append((33, 78, 34, (128, 76, 24), 0))
        poster(s, 86, 60, 6, 9, (240, 224, 130))
    elif kind == "bar":
        win(8, 31, True, curtain=(60, 150, 160))
        win(41, 31, r.random() < .5, curtain=(60, 150, 160))
        win(74 - 2, 31, True, curtain=(60, 150, 160))
        pygame.draw.rect(s, (24, 18, 48), (34, 53, 30, 12))
        pygame.draw.rect(s, (110, 250, 236), (34, 53, 30, 12), 1)
        neon_text(s, "BAR", 40, 56, (110, 240, 236), 2)
        lights.append((49, 59, 34, (30, 120, 120), 1))
        awning(s, 5, 65, 24, 5, (120, 40, 60), (240, 214, 170))
        door(s, 36, 68, 18, h - 72, (86, 50, 78), glass=False, open_light=True)
        lights.append((45, 84, 30, (140, 84, 24), 0))
        pygame.draw.rect(s, (200, 236, 230), (7, 72, 24, 14))
        pygame.draw.rect(s, (255, 210, 130), (8, 73, 22, 12))
        pygame.draw.rect(s, (70, 36, 60), (9, 79, 3, 6))
        pygame.draw.rect(s, (70, 36, 60), (15, 77, 3, 8))
        pygame.draw.rect(s, (70, 36, 60), (21, 80, 3, 5))
        pygame.draw.rect(s, (255, 244, 200), (7, 72, 24, 1))
        window(s, 62, 72, 24, 14, True, r, frame=(240, 214, 190), curtain=(60, 150, 160))
        lights.append((74, 84, 28, (112, 66, 20), 0))
    elif kind == "padaria":
        win(8, 31, True, shutter=(246, 214, 120))
        win(41, 31, True, shutter=(246, 214, 120), flowers=True)
        win(74 - 4, 31, r.random() < .6, shutter=(246, 214, 120))
        pygame.draw.rect(s, (70, 40, 44), (16, 52, 64, 9))
        pygame.draw.rect(s, (255, 214, 130), (16, 52, 64, 9), 1)
        draw_tiny(s, "PADARIA", 48 - tiny_width("PADARIA") // 2, 54, (255, 236, 190))
        lights.append((48, 56, 30, (112, 66, 20), 1))
        awning(s, 5, 62, w - 10, 7, (250, 200, 70), (250, 244, 232))
        pygame.draw.rect(s, (62, 30, 50), (8, 72, 50, 14))
        for i in range(12):
            pygame.draw.rect(s, mix((255, 226, 150), (255, 176, 96), i / 12), (9, 73 + i, 48, 1))
        for bx in range(11, 54, 8):
            pygame.draw.ellipse(s, (196, 120, 56), (bx, 78, 7, 4))
            pygame.draw.rect(s, (236, 176, 96), (bx + 1, 78, 4, 1))
        pygame.draw.rect(s, (110, 66, 48), (8, 82, 50, 4))
        pygame.draw.rect(s, (255, 244, 210), (8, 72, 50, 1))
        door(s, 66, 70, 16, h - 74, (210, 130, 70))
        lights.append((33, 80, 32, (128, 76, 24), 0))
        poster(s, 84, 52, 6, 8, (250, 250, 240), text=None, bars=False)
    elif kind == "hotel":
        for bx in (8, 40, 72 - 2):
            door(s, bx + 1, 30, 12, 18, (246, 230, 204), glass=False)
            pygame.draw.rect(s, (255, 214, 120), (bx + 2, 31, 10, 16))
            pygame.draw.rect(s, (246, 230, 204), (bx + 6, 31, 1, 16))
            pygame.draw.rect(s, (200, 70, 80), (bx + 2, 31, 2, 16))
            pygame.draw.rect(s, (200, 70, 80), (bx + 10, 31, 2, 16))
            lights.append((bx + 7, 40, 24, (112, 66, 20), 0))
        pygame.draw.rect(s, (46, 38, 62), (4, 46, w - 12, 2))
        for bx in range(5, w - 9, 3):
            pygame.draw.rect(s, (46, 38, 62), (bx, 40, 1, 7))
        pygame.draw.rect(s, (46, 38, 62), (4, 39, w - 12, 1))
        pygame.draw.rect(s, tone(wall, .3), (4, 48, w - 12, 2))
        pygame.draw.rect(s, (36, 26, 60), (30, 52, 36, 10))
        pygame.draw.rect(s, (255, 214, 130), (30, 52, 36, 10), 1)
        draw_tiny(s, "HOTEL", 48 - tiny_width("HOTEL") // 2, 55, (255, 226, 160))
        lights.append((48, 57, 28, (100, 60, 20), 1))
        door(s, 38, 64, 20, h - 68, (100, 54, 56))
        pygame.draw.rect(s, (100, 54, 56), (47, 64, 1, h - 68))
        for lx in (12, 74 - 4):
            window(s, lx, 66, 12, 14, True, r, curtain=(200, 70, 80), flowers=True)
            lights.append((lx + 6, 74, 24, (112, 66, 20), 0))
        for lx in (30, 64):
            pygame.draw.rect(s, (60, 54, 70), (lx, 62, 2, 3))
            pygame.draw.rect(s, (255, 226, 140), (lx - 1, 65, 4, 5))
            lights.append((lx + 1, 67, 18, (130, 90, 30), 0))
    elif kind == "farmacia":
        win(8, 31, True, shutter=(70, 150, 120))
        win(74 - 4, 31, True, shutter=(70, 150, 120))
        pygame.draw.rect(s, (26, 30, 56), (32, 27, 32, 26))
        pygame.draw.rect(s, (130, 255, 170), (32, 27, 32, 26), 1)
        cx_, cy_ = 48, 36
        gcol = (110, 250, 150)
        pygame.draw.rect(s, tone(gcol, -.4), (cx_ - 3, cy_ - 7, 7, 15))
        pygame.draw.rect(s, tone(gcol, -.4), (cx_ - 7, cy_ - 3, 15, 7))
        pygame.draw.rect(s, gcol, (cx_ - 2, cy_ - 6, 5, 13))
        pygame.draw.rect(s, gcol, (cx_ - 6, cy_ - 2, 13, 5))
        pygame.draw.rect(s, tone(gcol, .7), (cx_ - 1, cy_ - 5, 3, 11))
        pygame.draw.rect(s, tone(gcol, .7), (cx_ - 5, cy_ - 1, 11, 3))
        draw_tiny(s, "FARMACIA", 48 - tiny_width("FARMACIA") // 2, 46, (200, 255, 214))
        lights.append((48, 38, 36, (30, 130, 70), 1))
        awning(s, 5, 56, w - 10, 6, (60, 170, 120), (250, 244, 232))
        pygame.draw.rect(s, (60, 36, 60), (8, 65, 46, 21))
        for i in range(19):
            pygame.draw.rect(s, mix((236, 255, 236), (190, 230, 200), i / 19), (9, 66 + i, 44, 1))
        for k in range(5):
            pygame.draw.rect(s, r.choice(((200, 70, 90), (70, 130, 200), (250, 200, 70))), (11 + k * 8, 74, 5, 8))
        pygame.draw.rect(s, (110, 66, 60), (9, 82, 44, 3))
        door(s, 62, 64, 17, h - 68, (96, 60, 64))
        lights.append((31, 78, 30, (70, 120, 90), 0))
        poster(s, 84, 62, 7, 10, (30, 170, 90), text=None, bars=True)
    elif kind in GENERIC:
        sign, scol, bcol, a1, a2, cur = GENERIC[kind]
        win(8, 31, True, curtain=cur)
        win(41, 31, r.random() < .7, curtain=cur)
        win(74 - 2, 31, True, curtain=cur)
        bw_ = tiny_width(sign) + 8
        bx_ = 48 - bw_ // 2
        pygame.draw.rect(s, tone(bcol, -.4), (bx_ - 1, 51, bw_ + 2, 11))
        pygame.draw.rect(s, bcol, (bx_, 52, bw_, 9))
        pygame.draw.rect(s, scol, (bx_, 52, bw_, 9), 1)
        draw_tiny(s, sign, bx_ + 4, 54, scol)
        lights.append((48, 57, 30, tuple(int(v * .45) for v in scol), 1))
        awning(s, 5, 63, w - 10, 6, a1, a2)
        pygame.draw.rect(s, (62, 34, 52), (8, 72, 48, 14))
        for i in range(12):
            pygame.draw.rect(s, mix((255, 230, 160), (255, 180, 110), i / 12), (9, 73 + i, 46, 1))
        for bx in range(11, 52, 9):
            pygame.draw.rect(s, r.choice(((200, 70, 80), (80, 150, 200), (250, 200, 70), (120, 190, 120))),
                             (bx, 77, 6, 7))
        pygame.draw.rect(s, (110, 66, 48), (8, 83, 48, 3))
        door(s, 64, 68, 17, h - 72, tone(bcol, .25))
        lights.append((32, 80, 30, (128, 76, 24), 0))
        poster(s, 84, 62, 6, 9, (240, 224, 130))
    else:  # sobrado
        win(8, 31, True, shutter=(216, 90, 110), flowers=True)
        win(41, 31, r.random() < .6, curtain=(250, 220, 220))
        win(74 - 4, 31, True, shutter=(216, 90, 110))
        # varal com roupas
        pygame.draw.line(s, (60, 40, 60), (6, 54), (88, 54), 1)
        for lx in range(12, 82, 9):
            cc = r.choice(((250, 240, 230), (240, 90, 100), (90, 160, 230), (250, 210, 70)))
            pygame.draw.rect(s, cc, (lx, 55, 5, 7))
            pygame.draw.rect(s, tone(cc, -.3), (lx, 61, 5, 1))
        window(s, 8, 68, 14, 14, True, r, curtain=(250, 220, 220), flowers=True)
        lights.append((15, 76, 24, (112, 66, 20), 0))
        door(s, 40, 64, 17, h - 68, (96, 150, 120))
        lights.append((48, 84, 28, (112, 66, 20), 0))
        pygame.draw.rect(s, (60, 36, 56), (66, 64, 16, 10))
        pygame.draw.rect(s, (130, 130, 150), (67, 65, 14, 8))
        for ax in range(68, 80, 2):
            pygame.draw.rect(s, (70, 70, 90), (ax, 66, 1, 6))
        poster(s, 28, 70, 8, 11, (250, 240, 120), text=None, bars=True)
        poster(s, 60, 76, 22, 10, (248, 226, 80), text="BRASIL", bars=False)
        pygame.draw.rect(s, (50, 150, 90), (60, 76, 22, 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def tree_sprite(kind, seed):
    r = random.Random(seed)
    s = pygame.Surface((48, 60), pygame.SRCALPHA)
    pal = {0: ((52, 122, 92), (78, 156, 108), (140, 204, 124)),
           1: ((72, 144, 74), (112, 182, 80), (184, 226, 112)),
           2: ((214, 150, 40), (244, 198, 64), (255, 238, 140)),
           3: ((40, 100, 84), (62, 130, 102), (110, 176, 124)),
           4: ((116, 72, 164), (160, 108, 206), (218, 176, 240))}
    base, mid, lite = pal[kind]
    tk = (112, 72, 68)
    pygame.draw.rect(s, tone(tk, -.3), (21, 34, 7, 24))
    pygame.draw.rect(s, tk, (21, 34, 5, 24))
    pygame.draw.rect(s, tone(tk, .3), (21, 34, 2, 24))
    pygame.draw.rect(s, tone(tk, -.3), (17, 56, 15, 3))
    pygame.draw.rect(s, tk, (18, 55, 3, 2))
    pygame.draw.rect(s, tk, (28, 55, 3, 2))
    clumps = [(24, 24, 15), (12, 29, 10), (36, 29, 10), (24, 11, 11), (15, 17, 9), (33, 17, 9)]
    for cx, cy, rad in clumps:
        pygame.draw.circle(s, tone(base, -.4), (cx, cy + 1), rad)
    for cx, cy, rad in clumps:
        pygame.draw.circle(s, base, (cx, cy - 1), rad - 1)
    for cx, cy, rad in clumps:
        pygame.draw.circle(s, mid, (cx - 1, cy - 3), max(2, rad - 4))
    for cx, cy, rad in clumps:
        pygame.draw.circle(s, lite, (cx - 3, cy - 6), max(2, rad - 8))
    for _ in range(70):
        px, py = r.randrange(48), r.randrange(60)
        if s.get_at((px, py))[3] > 0 and py < 44:
            s.set_at((px, py), r.choice((tone(base, -.25), mid, lite)))
    if kind in (2, 4):
        for _ in range(26):
            px, py = r.randrange(6, 42), r.randrange(4, 40)
            if s.get_at((px, py))[3] > 0:
                s.set_at((px, py), (255, 250, 220) if kind == 2 else (250, 220, 250))
    return s


def palm_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((50, 66), pygame.SRCALPHA)
    pts = [(24, 66), (25, 52), (27, 40), (26, 24)]
    for i in range(len(pts) - 1):
        pygame.draw.line(s, (150, 106, 76), pts[i], pts[i + 1], 4)
        pygame.draw.line(s, (186, 142, 100), (pts[i][0] - 1, pts[i][1]), (pts[i + 1][0] - 1, pts[i + 1][1]), 1)
        pygame.draw.line(s, (100, 66, 56), (pts[i][0] + 2, pts[i][1]), (pts[i + 1][0] + 2, pts[i + 1][1]), 1)
    for y in range(28, 64, 4):
        pygame.draw.line(s, (96, 62, 54), (22 + (66 - y) // 16, y), (28 + (66 - y) // 16, y), 1)
    top = (26, 23)
    green = (62, 150, 88)
    for ang, ln in ((-175, 22), (-145, 24), (-110, 20), (-70, 20), (-35, 24), (-5, 22), (25, 15), (155, 15)):
        a = math.radians(ang)
        mid_ = (top[0] + math.cos(a) * ln * 0.6, top[1] + math.sin(a) * ln * 0.6 - 5)
        end = (top[0] + math.cos(a) * ln, top[1] + math.sin(a) * ln * 0.5 + 7)
        pygame.draw.line(s, shade(green, r.choice((-8, 6, 20))), top, mid_, 3)
        pygame.draw.line(s, tone(green, -.25), mid_, end, 3)
        pygame.draw.line(s, tone(green, .35), (top[0], top[1] - 1), (mid_[0], mid_[1] - 1), 1)
    pygame.draw.circle(s, (130, 90, 60), (26, 25), 3)
    pygame.draw.circle(s, (170, 120, 76), (25, 24), 1)
    return s


def flag_frames():
    frs = []
    for ph in range(4):
        s = pygame.Surface((34, 50), pygame.SRCALPHA)
        pygame.draw.rect(s, (176, 150, 120), (3, 2, 2, 48))
        pygame.draw.circle(s, (250, 220, 90), (4, 2), 2)
        fl = pygame.Surface((26, 17), pygame.SRCALPHA)
        pygame.draw.rect(fl, (0, 156, 66), (0, 0, 26, 17))
        pygame.draw.polygon(fl, (255, 224, 30), [(13, 1), (24, 8), (13, 15), (2, 8)])
        pygame.draw.circle(fl, (36, 66, 170), (13, 8), 4)
        pygame.draw.line(fl, (240, 240, 250), (9, 7), (17, 8), 1)
        for x in range(26):
            dy = int(math.sin((x * 0.45) - ph * 1.6) * 1.6)
            s.blit(fl, (5 + x, 4 + dy), (x, 0, 1, 17))
        overlay(s, (5, 18, 26, 3), (30, 10, 50, 40))
        frs.append(s)
    return frs


def banca_sprite():
    s = pygame.Surface((46, 40), pygame.SRCALPHA)
    wood = (132, 86, 58)
    pygame.draw.rect(s, tone(wood, -.4), (3, 12, 40, 28))
    pygame.draw.rect(s, wood, (4, 12, 38, 26))
    pygame.draw.rect(s, tone(wood, .22), (4, 12, 2, 26))
    pygame.draw.rect(s, tone(wood, -.28), (4, 34, 38, 4))
    awning(s, 1, 3, 44, 8, (214, 56, 70), (250, 242, 228))
    pygame.draw.rect(s, (60, 40, 70), (3, 11, 1, 3))
    pygame.draw.rect(s, (60, 40, 70), (42, 11, 1, 3))
    pygame.draw.rect(s, (84, 50, 52), (6, 17, 34, 14))
    for i in range(5):
        x = 7 + i * 7
        c = (240, 236, 222) if i != 2 else (250, 214, 100)
        pygame.draw.rect(s, c, (x, 18, 6, 11))
        pygame.draw.rect(s, tone(c, -.2), (x + 5, 18, 1, 11))
        pygame.draw.rect(s, (28, 20, 32), (x + 1, 20, 4, 2))       # tarja de censura
        pygame.draw.rect(s, (28, 20, 32), (x + 1, 24, 4, 1))
        pygame.draw.rect(s, (28, 20, 32), (x + 1, 26, 3, 1))
    draw_tiny(s, "JORNAL", 23 - tiny_width("JORNAL") // 2, 31, (255, 236, 190))
    return s


def crate_sprite():
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    wood = (166, 118, 70)
    pygame.draw.rect(s, tone(wood, -.4), (1, 2, 16, 14))
    pygame.draw.rect(s, wood, (2, 3, 14, 12))
    pygame.draw.rect(s, tone(wood, .3), (2, 3, 14, 2))
    pygame.draw.rect(s, tone(wood, -.3), (2, 8, 14, 1))
    pygame.draw.rect(s, tone(wood, -.3), (8, 3, 1, 12))
    pygame.draw.rect(s, tone(wood, -.2), (2, 13, 14, 2))
    pygame.draw.rect(s, (230, 190, 90), (4, 6, 3, 2))
    return s


def barrel_sprite(col=(120, 72, 70)):
    s = pygame.Surface((16, 20), pygame.SRCALPHA)
    pygame.draw.ellipse(s, tone(col, -.4), (1, 2, 14, 17))
    pygame.draw.ellipse(s, col, (1, 2, 13, 16))
    pygame.draw.rect(s, tone(col, .25), (3, 4, 2, 13))
    for yy in (5, 13):
        pygame.draw.rect(s, (70, 70, 96), (2, yy, 12, 2))
        pygame.draw.rect(s, (150, 150, 176), (2, yy, 12, 1))
    pygame.draw.ellipse(s, tone(col, .35), (2, 1, 11, 4))
    return s


def bush_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((26, 16), pygame.SRCALPHA)
    pygame.draw.circle(s, (38, 100, 78), (8, 10), 6)
    pygame.draw.circle(s, (38, 100, 78), (17, 10), 6)
    pygame.draw.circle(s, (38, 100, 78), (12, 7), 6)
    pygame.draw.circle(s, (62, 140, 98), (8, 9), 5)
    pygame.draw.circle(s, (62, 140, 98), (17, 9), 5)
    pygame.draw.circle(s, (62, 140, 98), (12, 6), 5)
    pygame.draw.circle(s, (120, 200, 124), (10, 5), 2)
    pygame.draw.circle(s, (120, 200, 124), (6, 8), 1)
    for _ in range(6):
        s.set_at((r.randrange(4, 22), r.randrange(4, 14)), r.choice(((246, 90, 130), (255, 214, 80), (250, 150, 200))))
    return s


def lamp_sprite():
    s = pygame.Surface((26, 52), pygame.SRCALPHA)
    iron, iron_hi = (58, 50, 78), (120, 108, 150)
    pygame.draw.rect(s, iron, (11, 14, 4, 36))
    pygame.draw.rect(s, iron_hi, (11, 14, 1, 36))
    pygame.draw.rect(s, iron, (8, 44, 10, 6))
    pygame.draw.rect(s, iron_hi, (8, 44, 10, 1))
    pygame.draw.rect(s, iron, (9, 40, 8, 2))
    pygame.draw.rect(s, iron, (10, 6, 6, 3))
    pygame.draw.circle(s, iron, (13, 5), 3)
    pygame.draw.rect(s, iron_hi, (12, 3, 1, 2))
    pygame.draw.rect(s, iron, (3, 11, 20, 2))
    pygame.draw.rect(s, iron_hi, (3, 11, 20, 1))
    for lx in (3, 18):
        pygame.draw.rect(s, iron, (lx - 1, 12, 7, 2))
        pygame.draw.polygon(s, iron, [(lx - 1, 14), (lx + 5, 14), (lx + 2, 11)])
        pygame.draw.rect(s, (255, 232, 150), (lx, 15, 5, 7))
        pygame.draw.rect(s, (255, 252, 220), (lx + 1, 16, 3, 4))
        pygame.draw.rect(s, iron, (lx, 15, 1, 7))
        pygame.draw.rect(s, iron, (lx + 4, 15, 1, 7))
        pygame.draw.rect(s, iron, (lx - 1, 22, 7, 2))
    return s


def bench_sprite():
    s = pygame.Surface((28, 18), pygame.SRCALPHA)
    iron, wood = (62, 54, 84), (182, 112, 74)
    for bx in (3, 23):
        pygame.draw.rect(s, iron, (bx, 8, 2, 9))
        pygame.draw.rect(s, iron, (bx - 1, 16, 4, 1))
    for i, yy in enumerate((2, 5)):
        pygame.draw.rect(s, tone(wood, -.28), (2, yy + 1, 24, 2))
        pygame.draw.rect(s, wood, (2, yy, 24, 2))
        pygame.draw.rect(s, tone(wood, .3), (2, yy, 24, 1))
    for i, yy in enumerate((9, 12)):
        pygame.draw.rect(s, tone(wood, -.4), (2, yy + 1, 24, 2))
        pygame.draw.rect(s, tone(wood, -.08), (2, yy, 24, 2))
        pygame.draw.rect(s, tone(wood, .22), (2, yy, 24, 1))
    pygame.draw.rect(s, iron, (2, 1, 2, 12))
    pygame.draw.rect(s, iron, (24, 1, 2, 12))
    return s


def mailbox_sprite():
    s = pygame.Surface((12, 22), pygame.SRCALPHA)
    pygame.draw.rect(s, (70, 60, 84), (5, 12, 2, 10))
    pygame.draw.rect(s, (250, 204, 40), (1, 2, 10, 11))
    pygame.draw.rect(s, (252, 232, 120), (1, 2, 2, 11))
    pygame.draw.rect(s, (200, 150, 20), (9, 2, 2, 11))
    pygame.draw.rect(s, (40, 70, 160), (1, 2, 10, 2))
    pygame.draw.rect(s, (40, 30, 50), (3, 6, 6, 1))
    pygame.draw.rect(s, (40, 70, 160), (4, 9, 4, 2))
    return s


def planter_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((26, 16), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 62, 70), (1, 8, 24, 8))
    pygame.draw.rect(s, (160, 98, 90), (1, 8, 24, 2))
    pygame.draw.rect(s, (86, 46, 60), (1, 14, 24, 2))
    pygame.draw.rect(s, (52, 120, 82), (2, 3, 22, 6))
    for _ in range(14):
        c = r.choice(((246, 80, 120), (255, 210, 70), (250, 140, 200), (250, 250, 240), (240, 120, 60)))
        x, y = r.randrange(3, 23), r.randrange(1, 8)
        s.set_at((x, y), c)
        s.set_at((x + 1, y), tone(c, .3))
    pygame.draw.rect(s, (110, 190, 110), (4, 3, 4, 1))
    return s


def fusca_sprite(col, back=False):
    s = pygame.Surface((24, 22), pygame.SRCALPHA)
    dark = (30, 22, 40)
    pygame.draw.rect(s, tone(col, -.2), (6, 0, 12, 7))
    pygame.draw.circle(s, tone(col, -.2), (7, 3), 3)
    pygame.draw.circle(s, tone(col, -.2), (16, 3), 3)
    pygame.draw.rect(s, col, (6, 0, 12, 4))
    pygame.draw.rect(s, tone(col, .4), (7, 0, 10, 1))
    glass = (150, 206, 232)
    if back:
        pygame.draw.rect(s, tone(glass, -.25), (7, 2, 10, 4))
        pygame.draw.line(s, tone(glass, .5), (8, 5), (10, 2), 1)
    else:
        pygame.draw.rect(s, glass, (7, 2, 10, 5))
        pygame.draw.line(s, (240, 252, 255), (8, 5), (11, 2), 1)
        pygame.draw.rect(s, tone(col, -.3), (11, 2, 1, 5))
    pygame.draw.rect(s, tone(col, -.5), (2, 6, 20, 10))
    pygame.draw.rect(s, col, (2, 6, 20, 8))
    pygame.draw.circle(s, col, (4, 9), 3)
    pygame.draw.circle(s, col, (19, 9), 3)
    pygame.draw.rect(s, tone(col, .4), (3, 6, 18, 1))
    pygame.draw.rect(s, tone(col, -.3), (2, 12, 20, 2))
    if back:
        for tx in (3, 18):
            pygame.draw.rect(s, (230, 40, 50), (tx, 8, 3, 2))
            pygame.draw.rect(s, (255, 150, 150), (tx, 8, 1, 1))
        pygame.draw.rect(s, (250, 220, 90), (10, 10, 5, 2))
        pygame.draw.rect(s, (40, 30, 50), (11, 11, 3, 1))
    else:
        for hx in (4, 19):
            pygame.draw.circle(s, (255, 240, 170), (hx, 9), 2)
            pygame.draw.circle(s, (255, 255, 240), (hx, 9), 1)
        pygame.draw.rect(s, tone(col, -.3), (11, 8, 2, 3))
        pygame.draw.rect(s, (230, 230, 240), (10, 11, 4, 2))
    pygame.draw.rect(s, (200, 200, 216), (1, 14, 22, 2))
    pygame.draw.rect(s, (250, 250, 255), (1, 14, 22, 1))
    for wx in (2, 18):
        pygame.draw.rect(s, dark, (wx, 14, 4, 7))
        pygame.draw.rect(s, (90, 90, 110), (wx + 1, 16, 2, 3))
    return s


def truck_sprite():
    s = pygame.Surface((40, 36), pygame.SRCALPHA)
    od = (84, 104, 64)
    pygame.draw.rect(s, tone(od, -.3), (3, 0, 34, 10))
    pygame.draw.rect(s, tone(od, .1), (4, 0, 32, 8))
    for xx in range(6, 36, 6):
        pygame.draw.rect(s, tone(od, -.25), (xx, 1, 1, 8))
    pygame.draw.rect(s, tone(od, .3), (4, 0, 32, 1))
    pygame.draw.rect(s, tone(od, -.4), (2, 8, 36, 20))
    pygame.draw.rect(s, od, (2, 8, 36, 18))
    pygame.draw.rect(s, tone(od, .3), (2, 8, 36, 1))
    pygame.draw.rect(s, (170, 214, 232), (5, 10, 30, 8))
    pygame.draw.rect(s, tone(od, -.4), (19, 10, 2, 8))
    pygame.draw.line(s, (240, 252, 255), (7, 16), (11, 11), 1)
    pygame.draw.rect(s, tone(od, -.3), (2, 22, 36, 4))
    for hx in (4, 30):
        pygame.draw.rect(s, (255, 240, 170), (hx, 19, 6, 4))
        pygame.draw.rect(s, (255, 255, 240), (hx + 1, 20, 3, 2))
    for xx in range(12, 28, 3):
        pygame.draw.rect(s, (40, 50, 40), (xx, 20, 1, 5))
    pygame.draw.rect(s, (60, 60, 76), (3, 27, 34, 3))
    pygame.draw.rect(s, (120, 120, 140), (3, 27, 34, 1))
    for wx in (2, 30):
        pygame.draw.rect(s, (28, 22, 36), (wx, 25, 8, 11))
        pygame.draw.rect(s, (86, 86, 106), (wx + 2, 28, 4, 5))
    return s


def barrel_fire_frames():
    fr = []
    r = random.Random(5)
    for _ in range(8):
        s = pygame.Surface((24, 28), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 60, 80), (5, 15, 14, 12))
        pygame.draw.rect(s, (104, 106, 130), (5, 15, 14, 11))
        pygame.draw.rect(s, (156, 158, 182), (6, 15, 3, 11))
        pygame.draw.rect(s, (60, 60, 80), (5, 18, 14, 1))
        pygame.draw.rect(s, (60, 60, 80), (5, 23, 14, 1))
        pygame.draw.ellipse(s, (40, 36, 52), (5, 13, 14, 5))
        for fx, fh, col in ((12, 13, (236, 66, 40)), (8, 9, (255, 130, 40)),
                            (16, 10, (255, 130, 40)), (12, 8, (255, 224, 96)),
                            (10, 5, (255, 244, 170))):
            hh = fh + r.randint(-2, 3)
            pygame.draw.polygon(s, col, [(fx - 3, 15), (fx + r.randint(-1, 1), 15 - hh), (fx + 3, 15)])
        for _ in range(3):
            s.set_at((r.randrange(6, 18), r.randrange(0, 8)), (255, 210, 120))
        fr.append(s)
    return fr


def make_glow(col, rad):
    s = pygame.Surface((rad * 2, rad * 2))
    s.fill((0, 0, 0))
    for rr in range(rad, 0, -2):
        k = (1 - rr / float(rad)) ** 2
        pygame.draw.circle(s, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (rad, rad), rr)
    return s


# ----------------------------------------------------------------------------
# RIO DE JANEIRO - sprites novos (praia, morro, Lapa, Centro, parque) e tiles
# ----------------------------------------------------------------------------
EXTRA_CFG = {
    "botequim": dict(wall=(226, 168, 96), roof=(140, 70, 70)),
    "sorveteria": dict(wall=(244, 160, 186), roof=(96, 150, 170)),
    "livraria": dict(wall=(120, 150, 200), roof=(150, 86, 70)),
    "cinema": dict(wall=(96, 84, 150), roof=(180, 70, 90)),
    "banco": dict(wall=(214, 200, 170), roof=(100, 100, 120)),
    "mercado": dict(wall=(150, 196, 112), roof=(190, 100, 70)),
    "barbearia": dict(wall=(200, 90, 90), roof=(80, 100, 150)),
    "pensao": dict(wall=(230, 200, 120), roof=(130, 70, 100)),
    "colombo": dict(wall=(244, 226, 186), roof=(120, 150, 120)),
}

# tipo: (letreiro, cor da letra, cor da placa, toldo 1, toldo 2, cortina)
GENERIC = {
    "botequim": ("BOTEQUIM", (255, 226, 150), (74, 40, 44), (240, 190, 60), (250, 244, 232), (210, 90, 60)),
    "sorveteria": ("SORVETE", (255, 244, 250), (190, 70, 120), (250, 150, 190), (250, 244, 232), (250, 220, 230)),
    "livraria": ("LIVROS", (255, 236, 190), (46, 56, 96), (70, 110, 190), (250, 244, 232), (250, 230, 190)),
    "cinema": ("CINE", (255, 120, 150), (30, 20, 56), (200, 60, 90), (250, 214, 120), (180, 60, 90)),
    "banco": ("BANCO", (255, 236, 190), (50, 50, 66), (110, 110, 130), (230, 224, 214), (200, 200, 210)),
    "mercado": ("MERCADO", (255, 250, 210), (60, 110, 60), (90, 170, 80), (250, 244, 232), (250, 240, 190)),
    "barbearia": ("BARBEIRO", (255, 240, 220), (110, 36, 50), (220, 70, 80), (70, 110, 200), (230, 230, 240)),
    "pensao": ("PENSAO", (255, 236, 190), (80, 40, 70), (180, 90, 120), (250, 230, 190), (210, 120, 150)),
    "colombo": ("COLOMBO", (255, 226, 130), (96, 60, 40), (150, 40, 50), (250, 236, 200), (240, 210, 170)),
}


def _dome(s, cx, hw, top, base, light, dark, r, p=0.5):
    """Morro/pedra arredondado: colunas com gradiente (claro à esquerda, escuro à direita)."""
    for x in range(cx - hw, cx + hw + 1):
        u = (x - cx) / float(hw)
        y0 = int(base - (base - top) * max(0.0, 1 - u * u) ** p)
        k = (x - (cx - hw)) / float(2 * hw)
        c = mix(light, dark, clamp(k * 1.15 - 0.1, 0, 1))
        pygame.draw.line(s, c, (x, y0), (x, base))
        if 0 <= x < s.get_width():
            s.set_at((x, y0), tone(c, .35))
    for _ in range(int(hw * 1.6)):       # estrias da rocha
        x = r.randint(cx - hw + 4, cx + hw - 4)
        u = (x - cx) / float(hw)
        y0 = int(base - (base - top) * max(0.0, 1 - u * u) ** p)
        if y0 >= base - 8:
            continue
        y1 = r.randint(y0 + 4, base - 4)
        k = (x - (cx - hw)) / float(2 * hw)
        c = tone(mix(light, dark, clamp(k * 1.15 - 0.1, 0, 1)), -.18)
        pygame.draw.line(s, c, (x, y1), (x, min(base - 1, y1 + r.randint(5, 14))))


def _veg(s, x0, x1, y0, y1, r, n, col=(62, 128, 90)):
    """Manchas de mata atlântica."""
    for _ in range(n):
        x, y = r.randint(x0, x1), r.randint(y0, y1)
        rad = r.randint(3, 6)
        c = shade(col, r.randint(-12, 12))
        pygame.draw.circle(s, tone(c, -.35), (x, y + 1), rad)
        pygame.draw.circle(s, c, (x, y), rad - 1)
        pygame.draw.circle(s, tone(c, .35), (x - 1, y - 2), max(1, rad - 3))


def pao_acucar_sprite():
    """Pão de Açúcar e o Morro da Urca, com o bondinho no cabo."""
    r = random.Random(7)
    s = pygame.Surface((170, 152), pygame.SRCALPHA)
    _dome(s, 118, 50, 12, 150, (214, 190, 196), (120, 92, 128), r, 0.42)
    _veg(s, 80, 156, 126, 148, r, 14)
    _veg(s, 100, 130, 10, 22, r, 3)
    _dome(s, 40, 40, 92, 150, (196, 172, 184), (126, 100, 138), r, 0.6)
    _veg(s, 6, 74, 94, 108, r, 10)
    _veg(s, 2, 80, 130, 148, r, 14)
    pygame.draw.line(s, (60, 48, 72), (104, 18), (44, 92), 1)       # cabo
    pygame.draw.rect(s, (60, 48, 72), (73, 52, 8, 2))
    pygame.draw.rect(s, (226, 60, 60), (72, 54, 10, 6))              # bondinho
    pygame.draw.rect(s, (255, 226, 160), (74, 55, 6, 3))
    return s


def corcovado_sprite():
    """Corcovado coberto de floresta, com o Cristo Redentor no alto."""
    r = random.Random(11)
    s = pygame.Surface((114, 152), pygame.SRCALPHA)
    _dome(s, 57, 54, 44, 150, (104, 176, 108), (40, 96, 84), r, 0.5)
    _veg(s, 10, 104, 56, 146, r, 40, (52, 120, 84))
    cx, ty = 57, 44
    pygame.draw.rect(s, (214, 206, 196), (cx - 5, ty - 8, 10, 9))     # pedestal
    pygame.draw.rect(s, (250, 248, 244), (cx - 2, ty - 26, 5, 19))    # corpo
    pygame.draw.rect(s, (250, 248, 244), (cx - 14, ty - 23, 29, 3))   # braços abertos
    pygame.draw.rect(s, (250, 248, 244), (cx - 1, ty - 31, 3, 5))     # cabeça
    pygame.draw.rect(s, (206, 200, 214), (cx + 1, ty - 25, 2, 17))
    pygame.draw.rect(s, (206, 200, 214), (cx + 6, ty - 21, 9, 1))
    return s


def ilha_sprite(seed):
    r = random.Random(seed)
    s = pygame.Surface((64, 36), pygame.SRCALPHA)
    _dome(s, 32, 30, 6, 34, (190, 166, 178), (116, 92, 124), r, 0.6)
    _veg(s, 14, 50, 4, 14, r, 5)
    pygame.draw.ellipse(s, (250, 250, 255), (2, 30, 60, 5))
    return s


def veleiro_sprite(col):
    s = pygame.Surface((26, 30), pygame.SRCALPHA)
    pygame.draw.polygon(s, (250, 246, 236), [(12, 2), (12, 20), (3, 20)])
    pygame.draw.polygon(s, tone(col, .2), [(14, 5), (14, 20), (23, 20)])
    pygame.draw.polygon(s, (214, 206, 206), [(12, 2), (12, 20), (9, 20)])
    pygame.draw.rect(s, (96, 66, 56), (12, 1, 1, 22))
    pygame.draw.polygon(s, tone(col, -.25), [(1, 22), (25, 22), (21, 28), (5, 28)])
    pygame.draw.rect(s, (250, 246, 236), (3, 22, 20, 1))
    return s


def pedalinho_sprite(col):
    s = pygame.Surface((22, 20), pygame.SRCALPHA)
    pygame.draw.ellipse(s, tone(col, -.35), (1, 9, 20, 10))
    pygame.draw.ellipse(s, col, (1, 8, 19, 9))
    pygame.draw.rect(s, (250, 250, 250), (4, 6, 8, 3))
    pygame.draw.rect(s, (250, 250, 250), (15, 3, 3, 7))
    pygame.draw.circle(s, (250, 250, 250), (17, 3), 3)
    pygame.draw.rect(s, (250, 150, 50), (19, 3, 3, 2))
    s.set_at((17, 2), (30, 20, 30))
    pygame.draw.rect(s, tone(col, .4), (3, 9, 12, 1))
    return s


def guardasol_sprite(c1, c2):
    s = pygame.Surface((30, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(c2, -.2), (3, 25, 24, 6))
    pygame.draw.rect(s, c2, (3, 25, 24, 5))
    for xx in range(4, 26, 4):
        pygame.draw.rect(s, c1, (xx, 25, 2, 5))
    pygame.draw.rect(s, tone(c2, .4), (3, 25, 24, 1))
    pygame.draw.rect(s, (236, 230, 220), (14, 9, 2, 21))
    pygame.draw.ellipse(s, tone(c1, -.4), (1, 3, 28, 14))
    pygame.draw.ellipse(s, c1, (1, 2, 28, 13))
    for i in range(1, 7, 2):
        s.set_clip(pygame.Rect(1 + i * 4, 0, 4, 32))
        pygame.draw.ellipse(s, c2, (1, 2, 28, 13))
    s.set_clip(None)
    pygame.draw.ellipse(s, tone(c1, .45), (5, 3, 9, 3))
    return s


def quiosque_sprite(col):
    s = pygame.Surface((50, 46), pygame.SRCALPHA)
    pygame.draw.rect(s, (156, 110, 80), (3, 40, 44, 4))
    pygame.draw.rect(s, (196, 150, 108), (3, 40, 44, 1))
    pygame.draw.rect(s, (250, 232, 196), (6, 22, 38, 18))
    pygame.draw.rect(s, (214, 180, 150), (38, 22, 6, 18))
    pygame.draw.rect(s, (60, 36, 52), (10, 27, 17, 13))
    pygame.draw.rect(s, (255, 214, 130), (11, 28, 15, 6))
    pygame.draw.rect(s, (186, 120, 80), (10, 34, 17, 2))
    for xx in (13, 18, 23):
        pygame.draw.circle(s, (120, 170, 80), (xx, 32), 2)
    pygame.draw.rect(s, tone(col, -.4), (29, 26, 13, 9))
    pygame.draw.rect(s, col, (29, 26, 13, 8))
    draw_tiny(s, "COCO", 30, 28, (255, 244, 210))
    pygame.draw.polygon(s, (140, 100, 50), [(0, 24), (25, 3), (49, 24)])
    pygame.draw.polygon(s, (216, 170, 84), [(2, 23), (25, 5), (47, 23)])
    for k in range(8):
        pygame.draw.line(s, (170, 124, 60), (6 + k * 5, 22), (25 + (k - 4) * 2, 8), 1)
    pygame.draw.line(s, (240, 206, 120), (6, 22), (25, 6), 1)
    pygame.draw.rect(s, (140, 100, 50), (0, 23, 50, 2))
    for xx in (3, 45):
        pygame.draw.rect(s, (120, 84, 58), (xx, 25, 2, 16))
    return s


def salva_vidas_sprite():
    s = pygame.Surface((34, 56), pygame.SRCALPHA)
    wood = (186, 126, 84)
    for xx in (6, 26):
        pygame.draw.rect(s, tone(wood, -.35), (xx, 34, 3, 22))
        pygame.draw.rect(s, wood, (xx, 34, 2, 22))
    pygame.draw.line(s, tone(wood, -.2), (7, 54), (27, 36), 2)
    pygame.draw.line(s, tone(wood, -.2), (27, 54), (7, 36), 2)
    pygame.draw.rect(s, tone(wood, -.4), (3, 32, 28, 3))
    pygame.draw.rect(s, (250, 246, 238), (6, 14, 22, 18))
    pygame.draw.rect(s, (230, 70, 70), (6, 14, 22, 3))
    pygame.draw.rect(s, (120, 190, 226), (9, 19, 16, 8))
    pygame.draw.rect(s, (230, 250, 255), (9, 19, 16, 1))
    pygame.draw.rect(s, (210, 66, 70), (3, 10, 28, 5))
    pygame.draw.rect(s, (255, 130, 120), (3, 10, 28, 1))
    pygame.draw.rect(s, (120, 84, 60), (16, 0, 1, 11))
    pygame.draw.polygon(s, (240, 60, 50), [(17, 1), (26, 3), (17, 6)])
    for yy in range(37, 54, 4):
        pygame.draw.rect(s, wood, (14, yy, 6, 1))
    return s


def rede_volei_sprite():
    s = pygame.Surface((64, 30), pygame.SRCALPHA)
    for xx in (3, 59):
        pygame.draw.rect(s, (90, 70, 60), (xx, 4, 2, 26))
        pygame.draw.rect(s, (200, 180, 160), (xx, 4, 1, 26))
    pygame.draw.rect(s, (250, 250, 250), (3, 6, 58, 2))
    pygame.draw.rect(s, (250, 250, 250), (3, 15, 58, 1))
    for xx in range(5, 60, 3):
        pygame.draw.line(s, (226, 226, 238), (xx, 7), (xx, 15), 1)
    for yy in (10, 13):
        pygame.draw.line(s, (226, 226, 238), (3, yy), (61, yy), 1)
    return s


def gol_sprite():
    s = pygame.Surface((34, 24), pygame.SRCALPHA)
    for xx in range(5, 30, 3):
        pygame.draw.line(s, (206, 206, 222), (xx, 6), (xx, 22), 1)
    for yy in range(8, 22, 3):
        pygame.draw.line(s, (206, 206, 222), (4, yy), (30, yy), 1)
    pygame.draw.rect(s, (246, 246, 250), (2, 4, 2, 20))
    pygame.draw.rect(s, (246, 246, 250), (30, 4, 2, 20))
    pygame.draw.rect(s, (246, 246, 250), (2, 4, 30, 2))
    return s


def barraco_sprite(seed):
    """Casa do morro: laje, caixa d'água, vergalhões e parabólica."""
    r = random.Random(seed)
    cols = [(236, 128, 110), (248, 208, 96), (96, 170, 214), (130, 200, 130),
            (232, 150, 70), (190, 120, 200), (240, 240, 226), (84, 200, 190)]
    wall = r.choice(cols)
    floors = r.choice((1, 2, 2))
    w, hb = 36, 18 * floors + 4
    h = hb + 14
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    y0 = h - hb
    pygame.draw.rect(s, tone(wall, -.5), (0, y0, w, hb))
    pygame.draw.rect(s, wall, (1, y0, w - 2, hb - 1))
    pygame.draw.rect(s, tone(wall, .3), (1, y0, w - 2, 1))
    overlay(s, (w - 9, y0, 8, hb), (60, 24, 100, 55))
    for i in range(floors):
        fy = y0 + 4 + i * 18
        lit = r.random() < .7
        pygame.draw.rect(s, (70, 60, 90), (4, fy, 9, 9))
        pygame.draw.rect(s, (255, 226, 130) if lit else (120, 150, 200), (5, fy + 1, 7, 7))
        pygame.draw.rect(s, (70, 60, 90), (8, fy + 1, 1, 7))
        if floors == 2 and i == 0:
            pygame.draw.rect(s, (70, 60, 90), (22, fy + 1, 9, 8))
            pygame.draw.rect(s, tone(wall, .2), (23, fy + 2, 7, 6))
    pygame.draw.rect(s, (80, 56, 70), (20, h - 13, 9, 12))
    pygame.draw.rect(s, (130, 92, 90), (21, h - 12, 7, 10))
    pygame.draw.rect(s, (150, 146, 160), (0, y0 - 2, w, 3))      # laje
    pygame.draw.rect(s, (206, 202, 214), (0, y0 - 2, w, 1))
    if r.random() < .6:                                           # caixa d'água azul
        pygame.draw.rect(s, (40, 80, 150), (4, y0 - 10, 11, 9))
        pygame.draw.rect(s, (70, 120, 200), (4, y0 - 10, 10, 8))
        pygame.draw.rect(s, (160, 200, 250), (5, y0 - 9, 2, 6))
        pygame.draw.rect(s, (40, 80, 150), (3, y0 - 11, 13, 2))
    if r.random() < .5:                                           # antena parabólica
        pygame.draw.line(s, (90, 90, 110), (26, y0 - 2), (26, y0 - 9), 1)
        pygame.draw.ellipse(s, (226, 226, 234), (22, y0 - 12, 8, 5))
    for xx in (20, 24, 31):                                       # vergalhões esperando o próximo andar
        if r.random() < .6:
            pygame.draw.line(s, (96, 80, 90), (xx, y0 - 3), (xx, y0 - 8), 1)
    return s


def barraco70_sprite(seed):
    """Barraco da Rocinha em 1970: tabuas ou tijolo aparente, telhado de zinco com pedras, cano de fogao."""
    r = random.Random(seed * 31 + 7)
    paints = [(204, 160, 104), (160, 122, 88), (222, 190, 130), (126, 168, 156), (198, 116, 100),
              (226, 210, 158), (146, 158, 184), (180, 196, 126), (232, 150, 90), (214, 214, 200)]
    wall = r.choice(paints)
    floors = 2 if r.random() < .32 else 1
    w = r.choice((32, 34, 36))
    fh = 17
    bh = fh * floors + 2
    rh = 11
    h = rh + bh
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    yb = h - bh
    for f in range(floors):
        fy = yb + f * fh
        hh = fh + (2 if f == floors - 1 else 0)
        if f == floors - 1 and r.random() < .4:                      # terreo de tijolo aparente
            bc = (176, 98, 82)
            pygame.draw.rect(s, tone(bc, -.45), (0, fy, w, hh))
            pygame.draw.rect(s, bc, (1, fy, w - 2, hh - 1))
            for yy in range(fy + 2, fy + hh - 1, 3):
                pygame.draw.line(s, tone(bc, -.3), (1, yy), (w - 2, yy))
                for xx in range(2 + (yy // 3 % 2) * 3, w - 2, 6):
                    pygame.draw.line(s, tone(bc, -.3), (xx, yy), (xx, yy + 2))
        else:
            wc = tone(wall, -.08 * f)
            pygame.draw.rect(s, tone(wc, -.5), (0, fy, w, hh))
            pygame.draw.rect(s, wc, (1, fy, w - 2, hh - 1))
            for xx in range(3, w - 2, 3):                            # tabuas
                pygame.draw.line(s, tone(wc, -.22), (xx, fy), (xx, fy + hh - 2))
            for _ in range(2):                                       # remendos
                pygame.draw.rect(s, tone(wc, r.choice((-.3, .25))), (r.randrange(2, w - 8), fy + r.randrange(2, hh - 6), r.randint(3, 6), r.randint(3, 5)))
    zc = r.choice(((150, 156, 168), (164, 112, 90), (138, 144, 156), (176, 124, 98), (118, 128, 140)))
    pygame.draw.polygon(s, tone(zc, -.45), [(0, yb + 1), (4, 2), (w - 5, 2), (w - 1, yb + 1)])
    pygame.draw.polygon(s, zc, [(1, yb), (5, 3), (w - 6, 3), (w - 2, yb)])
    s.set_clip(pygame.Rect(5, 3, w - 10, yb - 3))
    for xx in range(4, w - 4, 3):                                    # chapas de zinco
        pygame.draw.line(s, tone(zc, .25), (xx, 3), (xx, yb))
        pygame.draw.line(s, tone(zc, -.2), (xx + 1, 3), (xx + 1, yb))
    s.set_clip(None)
    pygame.draw.rect(s, tone(zc, -.55), (0, yb, w, 2))
    for _ in range(r.randint(1, 3)):                                 # pedras segurando o zinco
        px_, py_ = r.randint(7, w - 12), r.randint(4, max(4, yb - 5))
        pygame.draw.ellipse(s, (110, 104, 116), (px_, py_, 5, 3))
        pygame.draw.ellipse(s, (172, 166, 178), (px_, py_, 4, 2))
    if r.random() < .5:                                              # cano do fogao
        cx_ = r.randint(w // 2, w - 8)
        pygame.draw.rect(s, (66, 60, 78), (cx_, 0, 2, 7))
        pygame.draw.rect(s, (110, 104, 124), (cx_ - 1, 0, 4, 1))
    pygame.draw.line(s, (40, 34, 50), (w - 4, 4), (w - 1, 1))        # gambiarra da luz
    dx = r.randint(4, w - 14)
    pygame.draw.rect(s, (70, 50, 48), (dx, h - 14, 8, 13))
    pygame.draw.rect(s, (126, 90, 72), (dx + 1, h - 13, 6, 11))
    s.set_at((dx + 6, h - 8), (240, 210, 120))
    wx = w - 13 if dx < w // 2 else 4
    pygame.draw.rect(s, (70, 60, 90), (wx, h - 16, 9, 8))
    pygame.draw.rect(s, (255, 226, 130) if r.random() < .7 else (120, 150, 200), (wx + 1, h - 15, 7, 6))
    pygame.draw.rect(s, tone(wall, -.35), (wx - 3 if wx > 6 else wx + 9, h - 16, 3, 8))
    if floors == 2:
        for wx2 in (4, w - 12):
            pygame.draw.rect(s, (70, 60, 90), (wx2, yb + 4, 8, 8))
            pygame.draw.rect(s, (255, 226, 130) if r.random() < .6 else (120, 150, 200), (wx2 + 1, yb + 5, 6, 6))
    if r.random() < .5:                                              # lata d'agua na porta
        pygame.draw.rect(s, (60, 90, 140), (max(0, dx - 5), h - 7, 4, 6))
        pygame.draw.rect(s, (110, 150, 200), (max(0, dx - 5), h - 7, 3, 5))
    overlay(s, (w - 7, yb, 6, bh), (60, 24, 100, 55))
    return s


def bica_sprite():
    """Bica d'agua publica: torneira de concreto e latas d'agua esperando a vez."""
    s = pygame.Surface((30, 26), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (96, 140, 190), (2, 20, 26, 6))
    pygame.draw.ellipse(s, (150, 190, 226), (5, 21, 14, 3))
    pygame.draw.rect(s, (112, 104, 118), (8, 8, 12, 15))
    pygame.draw.rect(s, (176, 168, 178), (9, 8, 10, 14))
    pygame.draw.rect(s, (214, 208, 214), (9, 8, 10, 2))
    pygame.draw.rect(s, (86, 86, 104), (13, 3, 3, 8))
    pygame.draw.rect(s, (86, 86, 104), (13, 3, 8, 2))
    pygame.draw.rect(s, (60, 60, 80), (19, 5, 2, 3))
    pygame.draw.line(s, (150, 200, 240), (20, 8), (20, 17))
    for cx_, cy_ in ((1, 14), (22, 15), (25, 19)):
        pygame.draw.rect(s, (110, 116, 132), (cx_, cy_, 5, 7))
        pygame.draw.rect(s, (190, 196, 210), (cx_, cy_, 4, 6))
        pygame.draw.rect(s, (230, 234, 244), (cx_ + 1, cy_, 1, 5))
    return s


def venda_sprite():
    """Venda/bar de madeira do largo da Rocinha, com toldo de lona e garrafas na prateleira."""
    w, h = 44, 42
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(s, (92, 98, 112), [(0, 14), (5, 2), (w - 6, 2), (w, 14)])
    pygame.draw.polygon(s, (150, 156, 168), [(1, 13), (6, 3), (w - 7, 3), (w - 1, 13)])
    for xx in range(8, w - 8, 3):
        pygame.draw.line(s, (186, 190, 200), (xx, 4), (xx, 12))
    pygame.draw.rect(s, (84, 56, 52), (1, 14, w - 2, h - 14))
    pygame.draw.rect(s, (176, 124, 88), (2, 14, w - 4, h - 15))
    for xx in range(4, w - 3, 3):
        pygame.draw.line(s, (140, 96, 70), (xx, 14), (xx, h - 2))
    pygame.draw.rect(s, (46, 30, 40), (8, 22, 28, 12))
    pygame.draw.rect(s, (252, 214, 120), (10, 24, 24, 8))
    for i, c in enumerate(((60, 160, 90), (220, 90, 70), (240, 200, 80), (90, 140, 210), (220, 90, 70))):
        pygame.draw.rect(s, c, (12 + i * 4, 26, 2, 5))
    pygame.draw.rect(s, (110, 74, 58), (6, 33, 32, 7))
    pygame.draw.rect(s, (200, 150, 104), (6, 33, 32, 2))
    for i in range(0, w, 6):
        pygame.draw.rect(s, (214, 70, 66) if (i // 6) % 2 == 0 else (246, 238, 226), (i, 14, 6, 6))
    pygame.draw.rect(s, (60, 30, 30), (13, 5, 18, 9))
    pygame.draw.rect(s, (240, 226, 190), (14, 6, 16, 7))
    draw_tiny(s, "BAR", 17, 7, (170, 40, 40))
    return s


def placa_sprite():
    """Placa de madeira na entrada do morro."""
    s = pygame.Surface((36, 30), pygame.SRCALPHA)
    pygame.draw.rect(s, (92, 62, 50), (5, 18, 3, 12))
    pygame.draw.rect(s, (92, 62, 50), (28, 18, 3, 12))
    pygame.draw.rect(s, (60, 50, 70), (0, 0, 36, 20))
    pygame.draw.rect(s, (240, 236, 220), (1, 1, 34, 18))
    draw_tiny(s, "ROCINHA", 4, 3, (190, 50, 50))
    draw_tiny(s, "1970", 10, 11, (70, 60, 90))
    return s


def barraca_sprite(c1, c2, r):
    """Barraca de feira com toldo listrado e frutas."""
    s = pygame.Surface((38, 36), pygame.SRCALPHA)
    pygame.draw.rect(s, (120, 80, 60), (3, 12, 2, 24))
    pygame.draw.rect(s, (120, 80, 60), (33, 12, 2, 24))
    pygame.draw.rect(s, (170, 118, 80), (3, 24, 32, 12))
    pygame.draw.rect(s, (214, 164, 112), (3, 24, 32, 2))
    pygame.draw.rect(s, (110, 70, 56), (3, 33, 32, 3))
    for i in range(6):
        c = r.choice(((236, 60, 60), (250, 200, 50), (130, 200, 80), (250, 140, 40), (200, 90, 160)))
        pygame.draw.circle(s, tone(c, -.3), (7 + i * 5, 23), 3)
        pygame.draw.circle(s, c, (7 + i * 5, 22), 3)
        s.set_at((6 + i * 5, 21), tone(c, .5))
    awning(s, 1, 3, 36, 9, c1, c2)
    return s


def onibus_sprite(col, back=False):
    s = pygame.Surface((30, 42), pygame.SRCALPHA)
    dark = (30, 22, 40)
    pygame.draw.rect(s, tone(col, -.35), (1, 0, 28, 22))
    pygame.draw.rect(s, tone(col, .1), (2, 0, 26, 20))
    pygame.draw.rect(s, tone(col, .45), (2, 0, 26, 1))
    for xx in (8, 15, 22):
        pygame.draw.rect(s, tone(col, -.15), (xx, 2, 1, 14))
    pygame.draw.rect(s, (236, 236, 244), (11, 6, 9, 5))
    pygame.draw.rect(s, tone(col, -.5), (0, 20, 30, 20))
    pygame.draw.rect(s, col, (0, 20, 30, 17))
    pygame.draw.rect(s, tone(col, .4), (1, 20, 28, 1))
    if back:
        pygame.draw.rect(s, (84, 116, 140), (3, 23, 24, 8))
        pygame.draw.line(s, (160, 200, 220), (5, 29), (9, 24), 1)
        for tx in (2, 24):
            pygame.draw.rect(s, (230, 40, 50), (tx, 33, 4, 3))
            pygame.draw.rect(s, (255, 150, 150), (tx, 33, 1, 1))
        pygame.draw.rect(s, (250, 220, 90), (12, 33, 7, 3))
    else:
        pygame.draw.rect(s, (150, 206, 232), (3, 22, 24, 10))
        pygame.draw.rect(s, (240, 252, 255), (4, 23, 8, 1))
        pygame.draw.rect(s, tone(col, -.3), (14, 22, 2, 10))
        pygame.draw.rect(s, (30, 24, 40), (6, 15, 18, 7))
        draw_tiny(s, "170", 9, 16, (255, 200, 60))
        for hx in (5, 24):
            pygame.draw.circle(s, (255, 240, 170), (hx, 34), 2)
            pygame.draw.circle(s, (255, 255, 240), (hx, 34), 1)
    pygame.draw.rect(s, (200, 200, 216), (2, 36, 26, 2))
    for wx in (1, 24):
        pygame.draw.rect(s, dark, (wx, 36, 5, 6))
        pygame.draw.rect(s, (90, 90, 110), (wx + 1, 38, 3, 3))
    return s


def bonde_sprite():
    """Bondinho amarelo de Santa Teresa (visto de lado, indo para a direita)."""
    s = pygame.Surface((60, 32), pygame.SRCALPHA)
    yel = (246, 200, 60)
    pygame.draw.line(s, (60, 60, 76), (34, 6), (42, 0), 1)
    pygame.draw.rect(s, (236, 230, 220), (2, 4, 56, 4))
    pygame.draw.rect(s, tone(yel, -.4), (2, 8, 56, 18))
    pygame.draw.rect(s, yel, (3, 8, 54, 16))
    pygame.draw.rect(s, (214, 56, 60), (3, 22, 54, 2))
    pygame.draw.rect(s, tone(yel, .4), (3, 8, 54, 1))
    pcol = ((210, 80, 90), (80, 130, 210), (120, 190, 120), (240, 240, 240))
    for i in range(4):
        x = 6 + i * 13
        pygame.draw.rect(s, (60, 40, 70), (x, 11, 10, 10))
        pygame.draw.rect(s, (255, 222, 150), (x + 1, 12, 8, 8))
        pygame.draw.circle(s, (206, 150, 110), (x + 5, 15), 2)
        pygame.draw.rect(s, pcol[i], (x + 3, 17, 4, 3))
        pygame.draw.rect(s, tone(yel, -.3), (x - 1, 10, 1, 12))
    pygame.draw.rect(s, (50, 44, 66), (1, 25, 58, 2))
    for wx in (6, 46):
        pygame.draw.rect(s, (28, 22, 36), (wx, 26, 8, 5))
        pygame.draw.rect(s, (90, 90, 110), (wx + 2, 27, 4, 3))
    return s


def arcos_sprite():
    """Um módulo dos Arcos da Lapa (64 px): dois andares de arcos e o trilho do bonde no topo."""
    w, h = 64, 86
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    st = (230, 218, 198)
    sd = tone(st, -.42)
    pygame.draw.rect(s, sd, (0, 8, w, h - 8))
    pygame.draw.rect(s, st, (1, 8, w - 2, h - 9))
    for yy in range(10, h, 6):
        pygame.draw.rect(s, tone(st, -.1), (1, yy, w - 2, 1))
    overlay(s, (w - 12, 8, 12, h - 8), (70, 30, 100, 50))
    pygame.draw.rect(s, (70, 66, 86), (0, 4, w, 2))
    for xx in range(2, w, 8):
        pygame.draw.rect(s, (70, 66, 86), (xx, 2, 1, 4))
    pygame.draw.rect(s, tone(st, .35), (0, 8, w, 1))
    pygame.draw.rect(s, tone(st, -.3), (0, 9, w, 1))

    def arch(cx, ytop, rad, ybot):
        pygame.draw.circle(s, sd, (cx, ytop), rad + 2)
        pygame.draw.rect(s, sd, (cx - rad - 2, ytop, 2 * rad + 4, ybot - ytop))
        pygame.draw.circle(s, (0, 0, 0, 0), (cx, ytop), rad)
        pygame.draw.rect(s, (0, 0, 0, 0), (cx - rad, ytop, 2 * rad, ybot - ytop))

    for k in range(4):
        arch(8 + k * 16, 26, 5, 40)
    pygame.draw.rect(s, tone(st, -.2), (0, 41, w, 3))
    for k in range(2):
        arch(16 + k * 32, 54, 9, h)
    return s


def igreja_sprite():
    """Igreja da Candelária (inspiração): fachada clara, duas torres e cúpula azul-esverdeada."""
    w, h = 124, 120
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    stone, stone_d = (238, 222, 190), (190, 164, 150)
    dome, dome_hi, gold = (74, 148, 156), (150, 216, 210), (250, 210, 90)
    pygame.draw.rect(s, tone(dome, -.45), (40, 26, 44, 20))
    pygame.draw.ellipse(s, tone(dome, -.45), (36, 6, 52, 44))
    pygame.draw.ellipse(s, dome, (37, 6, 50, 42))
    pygame.draw.ellipse(s, dome_hi, (42, 9, 16, 14))
    for xx in (50, 62, 74):
        pygame.draw.line(s, tone(dome, -.3), (xx, 10), (xx, 40), 1)
    pygame.draw.rect(s, stone, (57, 0, 10, 8))
    pygame.draw.rect(s, gold, (61, 0, 2, 3))
    for tx0 in (4, 90):
        pygame.draw.rect(s, stone_d, (tx0 - 1, 36, 32, h - 36))
        pygame.draw.rect(s, stone, (tx0, 36, 30, h - 37))
        overlay(s, (tx0 + 22, 36, 8, h - 37), (80, 40, 100, 45))
        pygame.draw.polygon(s, tone(dome, -.4), [(tx0 - 2, 36), (tx0 + 15, 14), (tx0 + 32, 36)])
        pygame.draw.polygon(s, dome, [(tx0, 36), (tx0 + 15, 16), (tx0 + 30, 36)])
        pygame.draw.polygon(s, dome_hi, [(tx0 + 3, 34), (tx0 + 14, 18), (tx0 + 14, 34)])
        pygame.draw.rect(s, gold, (tx0 + 14, 8, 2, 7))
        pygame.draw.rect(s, gold, (tx0 + 12, 10, 6, 2))
        pygame.draw.rect(s, (50, 36, 60), (tx0 + 10, 44, 10, 16))
        pygame.draw.circle(s, (50, 36, 60), (tx0 + 15, 44), 5)
        pygame.draw.rect(s, (255, 206, 120), (tx0 + 12, 48, 6, 8))
        pygame.draw.rect(s, (50, 36, 60), (tx0 + 11, 72, 8, 14))
        pygame.draw.circle(s, (50, 36, 60), (tx0 + 15, 72), 4)
        pygame.draw.rect(s, (255, 206, 120), (tx0 + 13, 74, 4, 9))
        lights.append((tx0 + 15, 78, 26, (112, 66, 20), 0))
    pygame.draw.rect(s, stone_d, (31, 52, 62, h - 52))
    pygame.draw.rect(s, stone, (32, 52, 60, h - 53))
    pygame.draw.polygon(s, stone_d, [(30, 54), (62, 36), (94, 54)])
    pygame.draw.polygon(s, stone, [(33, 53), (62, 39), (91, 53)])
    pygame.draw.circle(s, (80, 56, 70), (62, 47), 4)
    pygame.draw.circle(s, (255, 214, 130), (62, 47), 2)
    pygame.draw.rect(s, tone(stone, -.2), (32, 54, 60, 2))
    for cx_ in (36, 46, 78, 88):
        pygame.draw.rect(s, tone(stone, .2), (cx_, 58, 4, h - 62))
        pygame.draw.rect(s, tone(stone, -.3), (cx_ + 3, 58, 1, h - 62))
    pygame.draw.circle(s, (80, 56, 70), (62, 70), 8)
    pygame.draw.circle(s, (250, 200, 110), (62, 70), 6)
    pygame.draw.line(s, (80, 56, 70), (56, 70), (68, 70), 1)
    pygame.draw.line(s, (80, 56, 70), (62, 64), (62, 76), 1)
    pygame.draw.rect(s, (60, 36, 50), (52, 92, 20, h - 92))
    pygame.draw.circle(s, (60, 36, 50), (62, 92), 10)
    pygame.draw.rect(s, (255, 206, 120), (55, 95, 14, h - 95))
    pygame.draw.circle(s, (255, 206, 120), (62, 95), 7)
    pygame.draw.rect(s, (60, 36, 50), (61, 90, 2, h - 90))
    pygame.draw.rect(s, tone(stone, -.15), (40, h - 5, 44, 5))
    pygame.draw.rect(s, tone(stone, -.3), (36, h - 2, 52, 2))
    lights.append((62, 100, 34, (130, 86, 26), 0))
    lights.append((62, 70, 26, (110, 70, 20), 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def teatro_sprite():
    """Theatro Municipal (inspiração): cúpula verde e dourada, pórtico com colunas e pavilhões."""
    w, h = 140, 112
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    cream, cream_d = (240, 224, 188), (196, 168, 150)
    green, gold = (62, 138, 110), (250, 206, 84)
    pygame.draw.ellipse(s, tone(green, -.45), (48, 6, 44, 40))
    pygame.draw.ellipse(s, green, (49, 6, 42, 38))
    pygame.draw.ellipse(s, tone(green, .4), (54, 10, 14, 10))
    for xx in (56, 62, 70, 78, 84):
        pygame.draw.line(s, gold, (xx, 12), (xx, 40), 1)
    pygame.draw.rect(s, gold, (66, 0, 6, 8))
    pygame.draw.rect(s, cream_d, (5, 46, w - 10, h - 46))
    pygame.draw.rect(s, cream, (6, 46, w - 12, h - 47))
    overlay(s, (w - 16, 46, 10, h - 47), (80, 40, 100, 45))
    for px_ in (6, 100):
        pygame.draw.rect(s, cream_d, (px_ - 1, 34, 36, h - 34))
        pygame.draw.rect(s, cream, (px_, 34, 34, h - 35))
        pygame.draw.polygon(s, tone(green, -.4), [(px_ - 3, 36), (px_ + 17, 20), (px_ + 37, 36)])
        pygame.draw.polygon(s, green, [(px_ - 1, 36), (px_ + 17, 22), (px_ + 35, 36)])
        pygame.draw.rect(s, gold, (px_ + 16, 12, 2, 10))
        pygame.draw.circle(s, gold, (px_ + 17, 11), 3)
        for wx in (px_ + 5, px_ + 21):
            pygame.draw.rect(s, (50, 36, 60), (wx, 52, 8, 14))
            pygame.draw.circle(s, (50, 36, 60), (wx + 4, 52), 4)
            pygame.draw.rect(s, (255, 206, 120), (wx + 1, 55, 6, 9))
            lights.append((wx + 4, 60, 22, (112, 66, 20), 0))
    pygame.draw.rect(s, cream_d, (38, 46, 64, 6))
    pygame.draw.rect(s, (60, 40, 56), (46, 40, 48, 9))
    pygame.draw.rect(s, gold, (46, 40, 48, 9), 1)
    draw_tiny(s, "THEATRO", 70 - tiny_width("THEATRO") // 2, 42, (255, 226, 130))
    pygame.draw.rect(s, (60, 36, 50), (44, 62, 52, h - 62))
    for cx_ in range(46, 94, 10):
        pygame.draw.rect(s, tone(cream, .15), (cx_, 54, 5, h - 58))
        pygame.draw.rect(s, tone(cream, -.3), (cx_ + 4, 54, 1, h - 58))
    for dx_ in (51, 61, 71, 81):
        pygame.draw.rect(s, (255, 206, 120), (dx_, 72, 5, 24))
        pygame.draw.circle(s, (255, 206, 120), (dx_ + 2, 72), 2)
    pygame.draw.rect(s, tone(cream, -.1), (36, h - 6, 68, 6))
    pygame.draw.rect(s, tone(cream, -.25), (32, h - 3, 76, 3))
    pygame.draw.rect(s, (210, 50, 60), (8, 70, 3, 22))
    pygame.draw.rect(s, (210, 50, 60), (129, 70, 3, 22))
    lights.append((70, 88, 40, (140, 96, 30), 0))
    lights.append((70, 45, 34, (120, 80, 20), 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def _arch_window(s, x, y, w, h, lit=True, col=(50, 36, 60)):
    """Janela/porta de arco pleno (escura, com luz quente por dentro)."""
    pygame.draw.rect(s, col, (x, y, w, h))
    pygame.draw.circle(s, col, (x + w // 2, y), w // 2)
    if lit:
        pygame.draw.rect(s, (255, 206, 120), (x + 2, y + 1, w - 4, h - 2))
        pygame.draw.circle(s, (255, 206, 120), (x + w // 2, y + 1), max(1, w // 2 - 2))
        pygame.draw.rect(s, col, (x + w // 2, y - 2, 1, h + 2))


def paco_imperial_sprite():
    """Paço Imperial (Praça XV): casarão colonial de 1743, sede do governo no Brasil colônia e no Império."""
    w, h = 156, 92
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    r = random.Random(77)
    lights = []
    wall, wall_d, trim = (246, 234, 198), (196, 172, 150), (254, 250, 238)
    roof = (190, 92, 74)
    pygame.draw.polygon(s, tone(roof, -.45), [(2, 28), (24, 6), (w - 24, 6), (w - 2, 28)])
    roof_tiles(s, (24, 7, w - 48, 21), roof, r)
    pygame.draw.polygon(s, tone(roof, -.2), [(2, 28), (24, 7), (24, 28)])
    pygame.draw.polygon(s, tone(roof, -.35), [(w - 2, 28), (w - 24, 7), (w - 24, 28)])
    pygame.draw.rect(s, wall_d, (2, 27, w - 4, h - 27))
    pygame.draw.rect(s, wall, (3, 27, w - 6, h - 28))
    overlay(s, (w - 14, 27, 11, h - 28), (80, 40, 100, 45))
    pygame.draw.rect(s, trim, (2, 27, w - 4, 3))
    pygame.draw.rect(s, tone(wall, -.3), (2, 30, w - 4, 1))
    pygame.draw.rect(s, trim, (3, 54, w - 6, 2))
    pygame.draw.rect(s, tone(wall, -.3), (3, 56, w - 6, 1))
    cx = w // 2
    # frontão central e mastro com a bandeira do Brasil
    pygame.draw.polygon(s, wall_d, [(cx - 25, 28), (cx, 8), (cx + 25, 28)])
    pygame.draw.polygon(s, trim, [(cx - 22, 28), (cx, 11), (cx + 22, 28)])
    pygame.draw.circle(s, (80, 56, 70), (cx, 22), 3)
    pygame.draw.circle(s, (255, 214, 130), (cx, 22), 1)
    pygame.draw.rect(s, (90, 70, 84), (cx, 0, 1, 10))
    pygame.draw.rect(s, (40, 160, 80), (cx + 1, 0, 10, 7))
    pygame.draw.polygon(s, (250, 214, 60), [(cx + 6, 1), (cx + 10, 3), (cx + 6, 5), (cx + 2, 3)])
    pygame.draw.circle(s, (50, 70, 170), (cx + 6, 3), 1)
    # janelas: andar nobre com venezianas verdes e térreo em arco
    for x in range(10, w - 16, 18):
        if abs(x + 4 - cx) < 24:
            continue
        window(s, x, 36, 8, 14, r.random() < .8, r, frame=trim, shutter=(66, 130, 112))
        pygame.draw.rect(s, (60, 54, 70), (x - 2, 51, 12, 1))
        _arch_window(s, x, 66, 8, 14)
        lights.append((x + 4, 74, 22, (112, 66, 20), 0))
    # portal central com placa
    pygame.draw.rect(s, (60, 40, 56), (cx - 26, 38, 52, 9))
    pygame.draw.rect(s, (250, 206, 84), (cx - 26, 38, 52, 9), 1)
    draw_tiny(s, "PACO IMPERIAL", cx - tiny_width("PACO IMPERIAL") // 2, 40, (255, 226, 130))
    pygame.draw.rect(s, trim, (cx - 13, 56, 26, h - 62))
    _arch_window(s, cx - 10, 66, 20, h - 66, True, (60, 36, 50))
    pygame.draw.rect(s, (60, 36, 50), (cx, 62, 1, h - 62))
    for k in (-1, 1):
        pygame.draw.rect(s, tone(trim, -.12), (cx + k * 17 - 2, 58, 4, h - 64))
    pygame.draw.rect(s, tone(wall, -.2), (4, h - 5, w - 8, 5))
    pygame.draw.rect(s, tone(wall, -.35), (0, h - 2, w, 2))
    lights.append((cx, 80, 40, (140, 96, 30), 0))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def biblioteca_sprite():
    """Biblioteca Nacional (Cinelândia): palácio eclético com pórtico de colunas, frontão e cúpulas."""
    w, h = 148, 120
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    stone, stone_d = (230, 224, 206), (176, 166, 160)
    cop, gold = (96, 156, 134), (250, 210, 90)
    cx = w // 2
    for ex in (8, w - 30):                                        # cúpulas dos pavilhões
        pygame.draw.rect(s, tone(cop, -.45), (ex + 2, 40, 18, 12))
        pygame.draw.ellipse(s, tone(cop, -.45), (ex, 26, 22, 24))
        pygame.draw.ellipse(s, cop, (ex + 1, 26, 20, 22))
        pygame.draw.ellipse(s, tone(cop, .45), (ex + 4, 29, 6, 5))
        pygame.draw.rect(s, gold, (ex + 10, 20, 2, 7))
    for x0, x1 in ((4, 46), (w - 46, w - 4)):                      # alas laterais de dois andares
        pygame.draw.rect(s, stone_d, (x0 - 1, 50, x1 - x0 + 2, h - 50))
        pygame.draw.rect(s, stone, (x0, 50, x1 - x0, h - 51))
        pygame.draw.rect(s, tone(stone, .3), (x0, 50, x1 - x0, 3))
        pygame.draw.rect(s, tone(stone, -.25), (x0, 53, x1 - x0, 1))
        pygame.draw.rect(s, tone(stone, -.1), (x0, 78, x1 - x0, 2))
        for wx in range(x0 + 6, x1 - 8, 12):
            _arch_window(s, wx, 62, 6, 10)
            _arch_window(s, wx, 88, 6, 14)
            lights.append((wx + 3, 94, 20, (112, 66, 20), 0))
    overlay(s, (w - 14, 50, 10, h - 51), (80, 40, 100, 45))
    pygame.draw.rect(s, stone_d, (39, 40, 70, h - 40))             # corpo central
    pygame.draw.rect(s, stone, (40, 40, 68, h - 41))
    pygame.draw.polygon(s, stone_d, [(35, 42), (cx, 14), (113, 42)])
    pygame.draw.polygon(s, stone, [(39, 41), (cx, 18), (109, 41)])
    pygame.draw.polygon(s, tone(stone, -.12), [(50, 40), (cx, 24), (98, 40)])
    pygame.draw.rect(s, gold, (cx - 1, 6, 3, 8))                   # figura no ápice
    pygame.draw.circle(s, gold, (cx, 5), 3)
    pygame.draw.rect(s, (60, 40, 56), (cx - 24, 42, 48, 9))
    pygame.draw.rect(s, gold, (cx - 24, 42, 48, 9), 1)
    draw_tiny(s, "BIBLIOTECA", cx - tiny_width("BIBLIOTECA") // 2, 44, (255, 226, 130))
    pygame.draw.rect(s, (60, 36, 50), (46, 62, 56, h - 62))
    for cxx in range(46, 100, 11):                                  # seis colunas
        pygame.draw.rect(s, tone(stone, .2), (cxx, 54, 5, h - 58))
        pygame.draw.rect(s, tone(stone, -.3), (cxx + 4, 54, 1, h - 58))
        pygame.draw.rect(s, tone(stone, .3), (cxx - 1, 54, 7, 2))
    for dx_ in (53, 64, 75, 86):
        pygame.draw.rect(s, (255, 206, 120), (dx_, 78, 5, 24))
        pygame.draw.circle(s, (255, 206, 120), (dx_ + 2, 78), 2)
    pygame.draw.rect(s, tone(stone, -.1), (32, h - 8, 84, 4))
    pygame.draw.rect(s, tone(stone, -.25), (26, h - 4, 96, 4))
    lights.append((cx, 92, 42, (140, 96, 30), 0))
    lights.append((cx, 46, 30, (120, 80, 20), 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def palacio_tiradentes_sprite():
    """Palácio Tiradentes: neoclássico, cúpula verde sobre tambor e pórtico central."""
    w, h = 146, 112
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    stone, stone_d = (242, 238, 224), (186, 178, 172)
    slate, dome, gold = (112, 106, 130), (70, 148, 120), (250, 206, 84)
    cx = w // 2
    for x0, x1 in ((3, 52), (w - 52, w - 3)):                       # alas
        pygame.draw.rect(s, tone(slate, -.4), (x0 - 1, 44, x1 - x0 + 2, 10))
        pygame.draw.rect(s, slate, (x0, 45, x1 - x0, 8))
        pygame.draw.rect(s, stone_d, (x0 - 1, 52, x1 - x0 + 2, h - 52))
        pygame.draw.rect(s, stone, (x0, 52, x1 - x0, h - 53))
        pygame.draw.rect(s, tone(stone, -.2), (x0, 54, x1 - x0, 1))
        for wx in range(x0 + 6, x1 - 8, 13):
            window(s, wx, 60, 7, 12, True, random.Random(wx), frame=stone)
            _arch_window(s, wx, 86, 7, 16)
            lights.append((wx + 3, 94, 20, (112, 66, 20), 0))
    overlay(s, (w - 12, 52, 9, h - 53), (80, 40, 100, 45))
    pygame.draw.rect(s, tone(dome, -.45), (cx - 17, 26, 34, 24))     # tambor e cúpula
    pygame.draw.rect(s, stone, (cx - 16, 26, 32, 24))
    for wx in (cx - 12, cx - 2, cx + 8):
        _arch_window(s, wx, 33, 4, 12)
    pygame.draw.ellipse(s, tone(dome, -.45), (cx - 24, 4, 48, 40))
    pygame.draw.ellipse(s, dome, (cx - 23, 4, 46, 38))
    pygame.draw.ellipse(s, tone(dome, .45), (cx - 16, 8, 14, 10))
    for xx in (-12, -5, 2, 9, 16):
        pygame.draw.line(s, tone(dome, -.3), (cx + xx, 8), (cx + xx, 38), 1)
    pygame.draw.rect(s, stone, (cx - 3, 0, 6, 8))
    pygame.draw.rect(s, gold, (cx - 1, 0, 2, 3))
    pygame.draw.rect(s, stone_d, (cx - 33, 48, 66, h - 48))          # pórtico
    pygame.draw.rect(s, stone, (cx - 32, 48, 64, h - 49))
    pygame.draw.polygon(s, stone_d, [(cx - 36, 52), (cx, 38), (cx + 36, 52)])
    pygame.draw.polygon(s, stone, [(cx - 33, 51), (cx, 41), (cx + 33, 51)])
    pygame.draw.circle(s, (80, 56, 70), (cx, 47), 3)
    pygame.draw.circle(s, gold, (cx, 47), 1)
    pygame.draw.rect(s, (60, 36, 50), (cx - 26, 60, 52, h - 60))
    for k in range(5):
        xx = cx - 28 + k * 12
        pygame.draw.rect(s, tone(stone, .2), (xx, 56, 5, h - 62))
        pygame.draw.rect(s, tone(stone, -.3), (xx + 4, 56, 1, h - 62))
    for dx_ in (cx - 20, cx - 8, cx + 5, cx + 17):
        pygame.draw.rect(s, (255, 206, 120), (dx_, 76, 4, 22))
        pygame.draw.circle(s, (255, 206, 120), (dx_ + 2, 76), 2)
    for fx in (cx - 40, cx + 38):                                    # bandeiras
        pygame.draw.rect(s, (90, 70, 84), (fx, 34, 1, 18))
        pygame.draw.rect(s, (40, 160, 80), (fx + 1, 34, 8, 5))
        pygame.draw.rect(s, (250, 214, 60), (fx + 3, 35, 4, 3))
    pygame.draw.rect(s, tone(stone, -.1), (cx - 36, h - 8, 72, 4))
    pygame.draw.rect(s, tone(stone, -.25), (cx - 42, h - 4, 84, 4))
    lights.append((cx, 90, 40, (140, 96, 30), 0))
    lights.append((cx, 34, 28, (120, 80, 20), 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def real_gabinete_sprite():
    """Real Gabinete Português de Leitura: fachada neomanuelina de pedra, com estátuas e esfera armilar."""
    w, h = 100, 124
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    stone, stone_d = (238, 228, 206), (184, 170, 156)
    gold = (250, 206, 84)
    cx = w // 2
    pygame.draw.rect(s, stone_d, (11, 32, 78, h - 32))
    pygame.draw.rect(s, stone, (12, 32, 76, h - 33))
    overlay(s, (w - 18, 32, 10, h - 33), (80, 40, 100, 45))
    pygame.draw.polygon(s, stone_d, [(26, 34), (cx, 8), (74, 34)])      # empena central
    pygame.draw.polygon(s, stone, [(29, 33), (cx, 12), (71, 33)])
    pygame.draw.circle(s, gold, (cx, 5), 4, 1)                          # esfera armilar
    pygame.draw.circle(s, gold, (cx, 5), 1)
    pygame.draw.line(s, gold, (cx - 4, 5), (cx + 4, 5), 1)
    pygame.draw.circle(s, (80, 56, 70), (cx, 24), 6)                    # rosácea
    pygame.draw.circle(s, (250, 200, 110), (cx, 24), 4)
    for a in range(0, 360, 45):
        pygame.draw.line(s, (80, 56, 70), (cx, 24), (cx + int(5 * math.cos(math.radians(a))), 24 + int(5 * math.sin(math.radians(a)))), 1)
    for px_ in (12, 28, 44, 56, 72, 87):                                # pináculos
        pygame.draw.polygon(s, stone_d, [(px_ - 3, 34), (px_, 20 + (px_ % 7)), (px_ + 3, 34)])
        pygame.draw.polygon(s, stone, [(px_ - 2, 34), (px_, 22 + (px_ % 7)), (px_ + 2, 34)])
    for nx in (17, 31, 62, 76):                                         # nichos com as quatro estátuas
        pygame.draw.rect(s, (60, 46, 62), (nx, 44, 8, 18))
        pygame.draw.circle(s, (60, 46, 62), (nx + 4, 44), 4)
        pygame.draw.rect(s, (196, 188, 176), (nx + 2, 50, 4, 11))
        pygame.draw.circle(s, (206, 198, 186), (nx + 4, 48), 2)
    pygame.draw.rect(s, tone(stone, -.2), (12, 64, 76, 2))
    pygame.draw.rect(s, tone(stone, .25), (12, 66, 76, 1))
    pygame.draw.rect(s, (60, 40, 56), (cx - 26, 70, 52, 9))             # placa
    pygame.draw.rect(s, gold, (cx - 26, 70, 52, 9), 1)
    draw_tiny(s, "REAL GABINETE", cx - tiny_width("REAL GABINETE") // 2, 72, (255, 226, 130))
    for k in range(5):                                                  # moldura em arco com cordas
        pygame.draw.circle(s, gold if k % 2 == 0 else stone_d, (cx, 96), 17 - k, 1)
    pygame.draw.rect(s, stone, (cx - 12, 96, 24, h - 100))
    pygame.draw.rect(s, (60, 36, 50), (cx - 11, 96, 22, h - 96))
    pygame.draw.circle(s, (60, 36, 50), (cx, 96), 11)
    pygame.draw.rect(s, (255, 206, 120), (cx - 8, 98, 16, h - 104))
    pygame.draw.circle(s, (255, 206, 120), (cx, 98), 8)
    pygame.draw.rect(s, (60, 36, 50), (cx, 90, 1, h - 90))
    for wx in (19, 71):
        _arch_window(s, wx, 96, 9, 16)
        lights.append((wx + 4, 104, 20, (112, 66, 20), 0))
    pygame.draw.rect(s, tone(stone, -.15), (8, h - 6, 84, 6))
    pygame.draw.rect(s, tone(stone, -.3), (4, h - 2, 92, 2))
    lights.append((cx, 108, 34, (130, 86, 26), 0))
    lights.append((cx, 24, 22, (120, 80, 20), 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def forte_sprite():
    """Forte de Copacabana: fortaleza de pedra de 1914 sobre as rochas, com canhões e torre de vigia."""
    w, h = 132, 76
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    st, st_d = (208, 198, 184), (148, 138, 136)
    pygame.draw.polygon(s, tone(st, -.1), [(6, 36), (16, 24), (w - 16, 24), (w - 6, 36)])   # terraço
    pygame.draw.rect(s, st_d, (4, 34, w - 8, h - 34))
    pygame.draw.rect(s, st, (5, 34, w - 10, h - 35))
    for yy in range(38, h - 4, 6):
        pygame.draw.rect(s, tone(st, -.1), (5, yy, w - 10, 1))
    overlay(s, (w - 18, 34, 13, h - 35), (80, 40, 100, 50))
    pygame.draw.rect(s, tone(st, .3), (4, 34, w - 8, 2))
    for mx in range(6, w - 12, 10):                                  # ameias
        pygame.draw.rect(s, st_d, (mx - 1, 28, 8, 8))
        pygame.draw.rect(s, tone(st, .15), (mx, 28, 6, 7))
    for ex in (24, 54, 84):                                           # canhões
        pygame.draw.rect(s, (36, 32, 44), (ex, 38, 14, 4))
        pygame.draw.rect(s, (70, 64, 80), (ex, 38, 14, 1))
        pygame.draw.rect(s, (36, 32, 44), (ex - 2, 37, 4, 6))
    pygame.draw.rect(s, st_d, (10, 6, 28, 34))                        # torre de vigia
    pygame.draw.rect(s, tone(st, .08), (11, 6, 26, 33))
    pygame.draw.rect(s, tone(st, -.2), (9, 6, 30, 3))
    for mx in range(10, 36, 6):
        pygame.draw.rect(s, tone(st, .1), (mx, 2, 4, 5))
    _arch_window(s, 19, 16, 8, 12)
    pygame.draw.rect(s, (90, 70, 84), (36, 0, 1, 8))                   # mastro e bandeira
    pygame.draw.rect(s, (40, 160, 80), (37, 0, 10, 6))
    pygame.draw.polygon(s, (250, 214, 60), [(42, 1), (46, 3), (42, 5), (38, 3)])
    pygame.draw.rect(s, (60, 40, 56), (60, 44, 24, 9))                 # placa
    pygame.draw.rect(s, (250, 206, 84), (60, 44, 24, 9), 1)
    draw_tiny(s, "FORTE", 72 - tiny_width("FORTE") // 2, 46, (255, 226, 130))
    pygame.draw.rect(s, (60, 36, 50), (62, 54, 20, h - 54))             # portão em arco
    pygame.draw.circle(s, (60, 36, 50), (72, 54), 10)
    pygame.draw.rect(s, (255, 206, 120), (65, 57, 14, h - 57))
    pygame.draw.circle(s, (255, 206, 120), (72, 57), 7)
    pygame.draw.rect(s, (60, 36, 50), (71, 52, 2, h - 52))
    for ex in (20, 100):
        _arch_window(s, ex, 56, 7, 14)
        lights.append((ex + 3, 64, 18, (112, 66, 20), 0))
    lights.append((72, 64, 34, (130, 86, 26), 0))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def chafariz_frames():
    """Chafariz da Praça XV (inspirado no do Mestre Valentim): bacia de pedra com jato de água animado."""
    frames = []
    for f in range(3):
        s = pygame.Surface((46, 44), pygame.SRCALPHA)
        st, wt = (214, 204, 190), (150, 206, 236)
        pygame.draw.ellipse(s, tone(st, -.45), (1, 28, 44, 15))
        pygame.draw.ellipse(s, st, (2, 28, 42, 13))
        pygame.draw.ellipse(s, wt, (6, 30, 34, 8))
        pygame.draw.ellipse(s, tone(wt, .4), (10, 31, 12, 3))
        pygame.draw.rect(s, tone(st, -.1), (20, 16, 6, 18))
        pygame.draw.rect(s, tone(st, .25), (20, 16, 2, 18))
        pygame.draw.ellipse(s, tone(st, -.3), (12, 14, 22, 8))
        pygame.draw.ellipse(s, st, (13, 14, 20, 6))
        pygame.draw.ellipse(s, wt, (16, 15, 14, 3))
        pygame.draw.rect(s, st, (21, 4, 4, 12))
        pygame.draw.circle(s, tone(st, .2), (23, 4), 3)
        for k, ang in enumerate((-50, -25, 0, 25, 50)):
            a = math.radians(ang)
            for t_ in range(1, 7):
                px_ = 23 + int(math.sin(a) * t_ * 2.2)
                py_ = 12 + int(t_ * 1.6 - 5 * math.cos(a) * (1 - ((t_ + f) % 3) * 0.1))
                if 0 <= px_ < 46 and 0 <= py_ < 44:
                    s.set_at((px_, py_), tone(wt, .5) if (t_ + f + k) % 2 else wt)
        frames.append(s)
    return frames


# ---- tiles novos do chão ---------------------------------------------------
def shore_px(y):
    """Posição (px) da linha d'água na altura y: o litoral ondula."""
    return 10.5 * TS + 14 * math.sin(y * 0.021) + 7 * math.sin(y * 0.057 + 1.3)


def draw_beach_tile(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    edges = [shore_px(y0 + k) for k in range(TS)]
    if x0 + TS < min(edges) - 28:                         # mar aberto
        d = clamp((min(edges) - (x0 + 8)) / 150.0, 0, 1)
        c = mix((52, 140, 186), (28, 70, 134), d)
        g.fill(shade(c, rnd.randint(-4, 4)), (x0, y0, TS, TS))
        for _ in range(2):
            g.fill(tone(c, .22), (x0 + rnd.randrange(0, 11), y0 + rnd.randrange(0, 15), rnd.randrange(3, 7), 1))
        return
    if x0 > max(edges) + 24:                              # areia seca
        c = shade((238, 212, 168), rnd.randint(-5, 5))
        g.fill(c, (x0, y0, TS, TS))
        for _ in range(9):
            g.set_at((x0 + rnd.randrange(TS), y0 + rnd.randrange(TS)), tone(c, rnd.choice((-.14, .14))))
        if rnd.random() < .05:
            g.fill((252, 236, 226), (x0 + rnd.randrange(2, 12), y0 + rnd.randrange(2, 12), 2, 1))
        return
    for py in range(TS):                                  # faixa da arrebentação, pixel a pixel
        ex = edges[py]
        for px in range(TS):
            d = (x0 + px) - ex
            h = _hash(x0 + px, y0 + py, 3)
            if d < -26:
                c = mix((92, 206, 214), (40, 100, 154), clamp((-d - 26) / 120.0, 0, 1))
            elif d < -4:
                c = mix((112, 218, 216), (80, 190, 210), clamp((-d - 4) / 22.0, 0, 1))
            elif d < 1.5:
                c = (252, 250, 250) if h % 3 else (214, 244, 248)
            elif d < 7:
                c = (204, 168, 128)
            elif d < 14:
                c = mix((204, 168, 128), (238, 212, 168), (d - 7) / 7.0)
            else:
                c = (238, 212, 168)
            if d >= 14 and h % 23 == 0:
                c = tone(c, -.12)
            elif d >= 14 and h % 41 == 0:
                c = tone(c, .15)
            elif d < -4 and h % 37 == 0:
                c = tone(c, .2)
            g.set_at((x0 + px, y0 + py), c)


def draw_calcadao(g, tx, ty, rnd):
    """Calçadão de Copacabana: ondas de pedra portuguesa preta e branca."""
    x0, y0 = tx * TS, ty * TS
    for py in range(TS):
        wy = y0 + py
        wave = math.sin(wy * 2 * math.pi / 64.0) * 8
        for px in range(TS):
            wx = x0 + px - BEACH_E * TS
            band = int((wx + wave + 64) // 16) % 2
            h = _hash(x0 + px, wy, 5)
            c = (246, 238, 230) if band == 0 else (58, 48, 72)
            if (x0 + px) % 4 == 0 or wy % 4 == 0:
                c = tone(c, -.2) if band == 0 else tone(c, .22)
            elif h % 29 == 0:
                c = shade(c, -10)
            g.set_at((x0 + px, wy), c)


def draw_morro(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    c = shade((46, 98, 80), rnd.randint(-8, 6))
    g.fill(c, (x0, y0, TS, TS))
    for _ in range(4):
        px, py = x0 + rnd.randrange(0, 12), y0 + rnd.randrange(0, 12)
        w = rnd.randrange(3, 7)
        g.fill(tone(c, -.3), (px, py + 2, w, 2))
        g.fill(tone(c, .28), (px, py, w, 2))
    if rnd.random() < .3:
        px, py = x0 + rnd.randrange(0, 8), y0 + rnd.randrange(0, 8)
        pygame.draw.ellipse(g, (140, 118, 140), (px, py, 8, 5))
        pygame.draw.ellipse(g, (186, 164, 176), (px + 1, py, 6, 3))


def draw_degraus(g, tx, ty, rnd):
    """Escadaria de concreto do morro."""
    x0, y0 = tx * TS, ty * TS
    c = shade((186, 174, 176), rnd.randint(-5, 5))
    g.fill(c, (x0, y0, TS, TS))
    for k in range(4):
        yy = y0 + k * 4
        g.fill(tone(c, .3), (x0, yy, TS, 1))
        g.fill(tone(c, -.3), (x0, yy + 3, TS, 1))
    if rnd.random() < .2:
        g.fill((120, 150, 100), (x0 + rnd.randrange(12), y0 + rnd.randrange(14), 2, 2))


def draw_beco(g, tx, ty, rnd):
    """Beco da Rocinha: cimento gasto e terra batida, com remendos e poças de esgoto."""
    x0, y0 = tx * TS, ty * TS
    c = shade((178, 150, 126), rnd.randint(-6, 6))
    g.fill(c, (x0, y0, TS, TS))
    g.fill(tone(c, -.28), (x0, y0, TS, 2))
    g.fill(tone(c, .12), (x0, y0 + 2, TS, 1))
    for _ in range(7):
        g.fill(tone(c, rnd.choice((-.18, .18))), (x0 + rnd.randrange(TS - 2), y0 + rnd.randrange(3, TS - 1), rnd.randrange(1, 4), 1))
    if rnd.random() < .3:
        g.fill(tone(c, .2), (x0 + rnd.randrange(8), y0 + rnd.randrange(4, 10), rnd.randrange(4, 8), 3))
    if rnd.random() < .12:
        pygame.draw.ellipse(g, (96, 108, 128), (x0 + rnd.randrange(6), y0 + 9, 9, 4))
        pygame.draw.ellipse(g, (140, 156, 176), (x0 + rnd.randrange(6) + 2, y0 + 10, 4, 2))


def draw_telhados(g, tx, ty, rnd):
    """Chao sob os barracos (nao se anda): telhados de zinco, telha e lona vistos de cima."""
    x0, y0 = tx * TS, ty * TS
    g.fill((78, 60, 72), (x0, y0, TS, TS))
    roofs = ((150, 156, 168), (168, 108, 84), (132, 138, 150), (184, 120, 92), (120, 128, 140), (96, 140, 150),
             (176, 150, 110), (150, 100, 96))
    for i in range(2):
        for j in range(2):
            c = roofs[_hash(tx * 2 + i, ty * 2 + j, 3) % len(roofs)]
            bx, by = x0 + i * 8, y0 + j * 8
            g.fill(tone(c, -.35), (bx, by, 8, 8))
            g.fill(c, (bx, by, 7, 7))
            for k in range(1, 7, 2):
                g.fill(tone(c, .22), (bx + k, by, 1, 7))


def draw_water(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    c = shade((84, 160, 196), rnd.randint(-5, 5))
    g.fill(c, (x0, y0, TS, TS))
    for _ in range(3):
        g.fill(tone(c, .3), (x0 + rnd.randrange(0, 11), y0 + rnd.randrange(0, 15), rnd.randrange(3, 7), 1))
    g.fill(tone(c, -.15), (x0 + rnd.randrange(0, 12), y0 + rnd.randrange(0, 15), 4, 1))


def draw_pitch(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    c = (112, 176, 100) if (ty % 2 == 0) else (102, 166, 92)
    c = shade(c, rnd.randint(-4, 4))
    g.fill(c, (x0, y0, TS, TS))
    for _ in range(5):
        g.set_at((x0 + rnd.randrange(TS), y0 + rnd.randrange(TS)), tone(c, rnd.choice((-.2, .2))))


def draw_azulejo(g, tx, ty, rnd):
    """Escadaria Selarón: degraus de azulejos coloridos."""
    x0, y0 = tx * TS, ty * TS
    cols = ((240, 200, 60), (60, 150, 90), (50, 110, 190), (220, 70, 70), (250, 250, 240), (240, 140, 60))
    for i in range(4):
        for j in range(4):
            h = _hash(tx * 4 + i, ty * 4 + j, 9)
            c = cols[h % 6]
            bx, by = x0 + i * 4, y0 + j * 4
            g.fill(c, (bx, by, 4, 4))
            g.fill(tone(c, .3), (bx, by, 4, 1))
            g.fill(tone(c, -.3), (bx, by + 3, 4, 1))


TILE_DRAW = {6: draw_beach_tile, 7: draw_beach_tile, 8: draw_calcadao, 9: draw_morro,
             10: draw_degraus, 11: draw_water, 12: draw_pitch, 13: draw_azulejo, 15: draw_beco, 16: draw_telhados}
BLOCK_T = (0, 6, 9, 11, 16)   # tiles em que não se anda: avenida, mar, rocha, lagoa e telhados da Rocinha
CROSS_ROWS = ((7, 8), (19, 20), (37, 38), (58, 59), (77, 78))     # travessias de pedestre da avenida


def district(px, py):
    """Nome do bairro (para o letreiro do HUD) a partir da posição em pixels."""
    tx, ty = px / TS, py / TS
    if tx < BEACH_E:
        return "Forte de Copacabana" if ty >= 80 else "Praia de Copacabana"
    if tx < AV0:
        return "Calçadão de Copacabana"
    if tx < AV1 + 4:
        return "Avenida Atlântica"
    if tx >= 87:
        return "Favela da Rocinha"
    if ty < 9:
        return "Arcos da Lapa"
    if ty < 18:
        return "Largo da Carioca"
    if ty >= 75:
        return "Praça XV"
    if ty >= 61:
        return "Campinho de Pelada" if tx < 60 else "Lagoa"
    if ty >= 57:
        return "Feira Livre"
    if tx >= 71:
        return "Jardim Botânico"
    return "Praça Central"


# ----------------------------------------------------------------------------
# Mapa: o Rio de Janeiro - mar, praia, calçadão e avenida à esquerda; Centro e Lapa ao norte;
# a praça de paralelepípedos no meio; parque, lagoa e feira ao sul; e o morro com favela e Cristo à direita
# ----------------------------------------------------------------------------
def shore(y):
    return AV1


# ----------------------------------------------------------------------------
# Rocinha, 1970: um morro so, com becos estreitos (1 tile) em terracos, escadarias ligando um beco ao outro,
# um largo na entrada (bica d'agua e venda) e barracos de madeira e zinco em todo o resto
# ----------------------------------------------------------------------------
ROC_X0, ROC_X1 = 88, 108                  # colunas do morro (x1 exclusivo)
ROC_ROWS = tuple(range(20, 86, 5))        # linha de cada beco horizontal (as casas ficam na borda de cima)
ROC_LARGO = (88, 46, 93, 50)              # largo da entrada (x0, y0, x1, y1), entre os becos 45 e 50


def _roc_stairs():
    """Escadas e becos de ligacao entre dois becos: (x, y0, y1, largura, tile) por trecho."""
    r = random.Random(1970)
    segs = []
    n = len(ROC_ROWS)
    for k in range(n - 1):
        ya, yb = ROC_ROWS[k] + 1, ROC_ROWS[k + 1]
        if k == n - 2:                    # ultimo trecho: o resto e muro pichado
            cols = [(88, 2, 10), (91, 1, 15)]
        else:
            lo, hi = (89, 93) if k % 2 == 0 else (101, 105)
            if ROC_ROWS[k] == 45:         # abaixo do largo
                lo, hi = 99, 105
            x1 = r.randint(lo, hi)
            dmin = 4 if ROC_ROWS[k] == 45 else 6
            cand = [x for x in range(89, 107) if abs(x - (x1 + 1.0)) >= dmin and (ROC_ROWS[k] != 45 or x >= 96)]
            cols = [(x1, 2, 10), (r.choice(cand), 1, r.choice((10, 15)))]
        segs.append([(x, ya, yb, w, t) for x, w, t in cols])
    return segs


ROC_SEGS = _roc_stairs()
ROC_LOOPS = []                            # trajetos de pedestres: sobem uma escada e descem pela outra
for _k in (1, 3, 6, 8, 10, 12):
    _a, _b = ROC_SEGS[_k][0], ROC_SEGS[_k][1]
    _xa, _xb = (_a[0] + _a[3] / 2.0) * TS, (_b[0] + _b[3] / 2.0) * TS
    _ya, _yb = ROC_ROWS[_k] * TS + 11, ROC_ROWS[_k + 1] * TS + 11
    ROC_LOOPS.append([(_xa, _ya), (_xb, _ya), (_xb, _yb), (_xa, _yb)])

TILE_COL = {0: (92, 82, 110), 1: (228, 204, 182), 2: (92, 152, 100),
            3: (180, 132, 124), 4: (58, 114, 92), 5: (206, 178, 164)}

PLAZA_C = ((31 + OX) * TS + 8, (19 + OY) * TS + 8)      # centro da praça (px)
PLAZA_R = (128, 82)                       # raios (px)


def build_tiles():
    tiles = [[2] * MW for _ in range(MH)]
    rnd = random.Random(3)

    def fill(x0, y0, x1, y1, t):
        for yy in range(max(0, y0), min(MH, y1)):
            for xx in range(max(0, x0), min(MW, x1)):
                tiles[yy][xx] = t

    # litoral: mar, areia, calçadão, avenida e calçada
    for y in range(MH):
        sea = shore_px(y * TS + 8)
        for x in range(AV1 + 4):
            if x < BEACH_E:
                tiles[y][x] = 6 if (x * TS + 8) < sea else 7
            elif x < AV0:
                tiles[y][x] = 8
            elif x < AV1:
                tiles[y][x] = 0
            else:
                tiles[y][x] = 1
    # faixas de pedestres: únicos pontos onde se atravessa a avenida (tile 14 = asfalto transitável)
    for ya, yb in CROSS_ROWS:
        fill(AV0, ya, AV1, yb + 1, 14)
    # calçadas das ruas transversais
    for rect in ((83, 9, 84, 60), (86, 9, 87, 60), (38, 57, 84, 58), (38, 60, 87, 61), (38, 18, 84, 19),
                 (38, 21, 84, 22), (38, 5, 88, 7), (38, 9, 40, 18)):
        fill(rect[0], rect[1], rect[2], rect[3], 1)
    # morros ao fundo (Santa Teresa) e mata ao norte
    fill(AV1 + 4, 0, 88, 5, 4)
    # ruas de paralelepípedo: sob os Arcos, ligando a praça, no Catete e a avenida leste
    for rect in ((AV1, 7, 88, 9), (AV1, 19, 84, 21), (AV1, 58, 88, 60), (84, 7, 86, 61), (AV1, 37, 48, 39)):
        fill(rect[0], rect[1], rect[2], rect[3], 3)
    # Largo da Carioca (praça de pedra) com a escadaria colorida de azulejos
    fill(40, 9, 83, 18, 5)
    fill(80, 9, 83, 18, 13)
    # parque a leste da praça
    fill(71, 22, 83, 57, 4)
    # a praça central: grande elipse de paralelepípedos e o piso da banca
    for y in range(MH):
        for x in range(MW):
            dx, dy = (x - (33.5 + OX)) / 12.8, (y - (20.0 + OY)) / 11.8
            if abs(dx) ** 4 + abs(dy) ** 4 < 1.0 and tiles[y][x] == 2:
                tiles[y][x] = 3
    fill(60, 43, 70, 49, 5)
    # sul: campinho de pelada, ciclovia e lagoa
    fill(44, 62, 56, 74, 12)
    for y in range(MH):
        for x in range(60, 90):
            dx, dy = (x + 0.5 - 74) / 9.0, (y + 0.5 - 68) / 5.0
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                tiles[y][x] = 11
            elif d2 < 1.35:
                tiles[y][x] = 1
    # Centro histórico (Praça XV): calçada, rua de paralelepípedo, praça de pedra, cais e a Baía de Guanabara
    fill(AV1 + 4, 75, 88, 77, 1)
    fill(AV1, 77, 88, 79, 3)
    fill(AV1 + 4, 79, 88, MH - 4, 5)
    fill(AV1 + 4, MH - 4, 88, MH - 3, 1)
    fill(AV1 + 4, MH - 3, 88, MH, 11)
    # promontório do Forte de Copacabana: rochas voltadas para o mar e piso de pedra junto à areia
    for y in range(78, MH):
        for x in range(0, BEACH_E):
            dx, dy = (x + 0.5 - 11.5) / 8.0, (y + 0.5 - 86.5) / 5.6
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                tiles[y][x] = 9 if (d2 > 0.5 and x < 15) else 5
    # morro: mata e rochas ao fundo
    fill(88, 14, MW, MH, 4)
    fill(88, 0, MW, 14, 9)
    fill(MW - 4, 14, MW, MH, 9)
    fill(88, MH - 2, MW, MH, 9)
    # Rocinha (1970): barracos por todo o morro, becos estreitos em terracos e escadarias entre eles
    fill(ROC_X0, ROC_ROWS[0] - 4, ROC_X1, ROC_ROWS[-1] + 5, 16)
    for row in ROC_ROWS:
        fill(ROC_X0, row, ROC_X1, row + 1, 15)
    for seg in ROC_SEGS:
        for sx, sy0, sy1, sw, st in seg:
            fill(sx, sy0, sx + sw, sy1, st)
    fill(ROC_LARGO[0], ROC_LARGO[1], ROC_LARGO[2], ROC_LARGO[3], 5)
    return tiles


MORRO_ROWS = ROC_ROWS
LAGOA_C = (74, 68)
FEIRA_X = (41, 45, 54, 58, 62, 66)
BEACH_KIOSK_ROWS = (18, 31, 53, 66, 78)
LARGO_BASE = 15          # fileira de prédios do Largo da Carioca (linha da base)
SHOPS_BASE = 57          # fileira de lojas ao norte da rua do Catete
ARCOS_X0 = 42 * TS       # início dos Arcos da Lapa (px)
ARCOS_BASE = 7 * TS
ARCOS_N = 12


COBBLES = [(186, 134, 128), (174, 122, 124), (198, 148, 134), (160, 110, 120),
           (206, 158, 138), (150, 112, 132), (190, 150, 116), (170, 132, 146)]


def _hash(a, b, c=0):
    return ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xFFFFFF


def draw_cobble(g, tx, ty, rnd):
    mortar = (112, 76, 98)
    for row in range(4):
        grow = ty * 4 + row
        off = 0 if grow % 2 == 0 else 4
        y = ty * TS + row * 4
        k0 = (tx * TS - off) // 8
        for k in range(k0, k0 + 4):
            bx = k * 8 + off
            x1, x2 = max(bx, tx * TS), min(bx + 8, tx * TS + TS)
            if x2 <= x1:
                continue
            h = _hash(k, grow)
            c = COBBLES[h % len(COBBLES)]
            c = shade(c, (h >> 8) % 15 - 7)
            g.fill(c, (x1, y, x2 - x1, 4))
            g.fill(tone(c, .16), (x1, y, x2 - x1, 1))
            g.fill(mortar, (x1, y + 3, x2 - x1, 1))
            if bx + 7 >= x1 and bx + 7 < x2:
                g.fill(mortar, (bx + 7, y, 1, 4))
            if (h >> 16) % 5 == 0:
                g.set_at((x1 + (h >> 4) % max(1, x2 - x1), y + 1 + (h >> 12) % 2), tone(c, -.22))


def draw_sidewalk(g, tx, ty, rnd):
    c = shade((228, 204, 182), rnd.randint(-8, 6))
    x0, y0 = tx * TS, ty * TS
    g.fill(c, (x0, y0, TS, TS))
    g.fill(tone(c, .35), (x0, y0, TS, 1))
    g.fill(tone(c, .25), (x0, y0, 1, TS))
    g.fill((176, 150, 160), (x0, y0 + TS - 1, TS, 1))
    g.fill((176, 150, 160), (x0 + TS - 1, y0, 1, TS))
    g.fill(tone(c, -.12), (x0 + 1, y0 + TS - 2, TS - 2, 1))
    for _ in range(4):
        g.set_at((x0 + rnd.randrange(2, TS - 2), y0 + rnd.randrange(2, TS - 2)), tone(c, rnd.choice((-.2, .2))))
    if rnd.random() < .08:
        px, py = x0 + rnd.randrange(3, 10), y0 + rnd.randrange(3, 10)
        g.fill((150, 124, 140), (px, py, 3, 1))
        g.fill((150, 124, 140), (px + 2, py + 1, 2, 1))


def draw_road(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    c = shade(TILE_COL[0], rnd.randint(-5, 5))
    g.fill(c, (x0, y0, TS, TS))
    for _ in range(14):
        g.set_at((x0 + rnd.randrange(TS), y0 + rnd.randrange(TS)), tone(c, rnd.choice((-.2, .18))))
    if rnd.random() < .12:
        g.fill(tone(c, -.2), (x0 + rnd.randrange(0, 8), y0 + rnd.randrange(0, 12), rnd.randrange(3, 8), 1))
    if tx == AV0 + 5 and ty % 2 == 0:
        g.fill((246, 204, 70), (x0 + 5, y0 + 2, 2, 10))
        g.fill((246, 204, 70), (x0 + 9, y0 + 2, 2, 10))
    if tx == AV0 + 9:
        g.fill((234, 230, 240), (x0 + TS - 2, y0, 2, TS))
    if tx == AV0:
        g.fill((234, 230, 240), (x0, y0, 2, TS))


def draw_grass(g, tx, ty, rnd, forest=False):
    x0, y0 = tx * TS, ty * TS
    base = TILE_COL[4] if forest else TILE_COL[2]
    c = shade(base, rnd.randint(-6, 6))
    g.fill(c, (x0, y0, TS, TS))
    for _ in range(3):      # manchas
        px, py = x0 + rnd.randrange(0, 12), y0 + rnd.randrange(0, 13)
        g.fill(tone(c, -.12), (px, py, rnd.randrange(3, 6), 2))
        g.fill(tone(c, .1), (px + 1, py - 1, rnd.randrange(2, 4), 1))
    for _ in range(rnd.randrange(2, 5)):      # tufos
        px, py = x0 + rnd.randrange(1, TS - 1), y0 + rnd.randrange(3, TS - 1)
        g.fill(tone(c, -.3), (px, py, 1, 2))
        g.fill(tone(c, .22), (px, py - 1, 1, 2))
        g.fill(tone(c, .1), (px + 1, py, 1, 1))
        g.set_at((px - 1, py), tone(c, .3))
    if forest:
        for _ in range(2):
            g.set_at((x0 + rnd.randrange(TS), y0 + rnd.randrange(TS)),
                     rnd.choice(((220, 170, 70), (200, 100, 80), (230, 130, 150))))
    elif rnd.random() < .1:
        px, py = x0 + rnd.randrange(2, TS - 3), y0 + rnd.randrange(2, TS - 3)
        fc = rnd.choice(((255, 224, 90), (250, 130, 170), (250, 250, 240), (190, 150, 240)))
        g.fill(fc, (px, py, 2, 2))
        g.set_at((px, py), tone(fc, .5))
        g.set_at((px + 1, py + 2), (60, 130, 80))


def draw_slab(g, tx, ty, rnd):
    x0, y0 = tx * TS, ty * TS
    c = (206, 178, 164) if (tx + ty) % 2 == 0 else (194, 164, 156)
    c = shade(c, rnd.randint(-4, 4))
    g.fill(c, (x0, y0, TS, TS))
    g.fill(tone(c, .3), (x0, y0, TS, 1))
    g.fill(tone(c, .2), (x0, y0, 1, TS))
    g.fill(tone(c, -.35), (x0, y0 + TS - 1, TS, 1))
    g.fill(tone(c, -.35), (x0 + TS - 1, y0, 1, TS))
    g.fill(tone(c, .08), (x0 + 3, y0 + 3, TS - 6, TS - 6))
    for _ in range(3):
        g.set_at((x0 + rnd.randrange(2, TS - 2), y0 + rnd.randrange(2, TS - 2)), tone(c, -.2))


def draw_plaza(g):
    cx, cy = PLAZA_C
    rx, ry = PLAZA_R
    rings_pal = [(210, 150, 140), (228, 192, 160), (160, 108, 134), (200, 120, 124), (232, 204, 170)]
    for y in range(cy - ry - 1, cy + ry + 2):
        for x in range(cx - rx - 1, cx + rx + 2):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            rr2 = dx * dx + dy * dy
            if rr2 >= 1.0:
                continue
            rr = math.sqrt(rr2)
            th = math.atan2(dy, dx)
            if rr > 0.985:
                c = (118, 78, 106)
            elif rr > 0.93:
                c = (230, 200, 184) if rr < 0.965 else (206, 170, 160)
            elif rr > 0.88:
                seg = int((th + math.pi) / (2 * math.pi) * 72)
                c = (132, 78, 112) if seg % 2 == 0 else (150, 92, 126)
                if rr < 0.895:
                    c = (96, 56, 92)
            elif rr < 0.07:
                c = (246, 206, 110)
            elif rr < 0.12:
                c = (196, 72, 84)
            elif rr < 0.16:
                c = (240, 226, 196)
            else:
                rpx = rr * 100.0
                ring = int((rr - 0.16) / 0.72 * 12)
                rf = ((rr - 0.16) / 0.72 * 12) - ring
                segs = max(8, int(2 * math.pi * (0.16 + (ring + 0.5) * 0.06) * 100 / 10))
                sf = (th + math.pi) / (2 * math.pi) * segs
                seg = int(sf)
                base = rings_pal[ring % len(rings_pal)]
                h = _hash(ring, seg, 7)
                c = shade(base, (h >> 4) % 17 - 8)
                if rf < 0.14 or (sf - seg) < 0.07 * (4 + ring * 0.5) / 4.0:
                    c = tone(c, -.34)
                elif rf > 0.82:
                    c = tone(c, -.12)
                elif rf < 0.3:
                    c = tone(c, .12)
                # raios (rosa dos ventos)
                ang8 = abs(math.sin(th * 4))
                if ang8 < 0.07 and rr < 0.88:
                    c = tone((240, 214, 176), -.12 if (ring % 2) else 0)
            g.set_at((x, y), c)


def build_ground(tiles):
    g = pygame.Surface((MW * TS, MH * TS))
    rnd = random.Random(11)
    for y in range(MH):
        for x in range(MW):
            t = tiles[y][x]
            if t == 0:
                draw_road(g, x, y, rnd)
            elif t == 1:
                draw_sidewalk(g, x, y, rnd)
            elif t == 2:
                draw_grass(g, x, y, rnd)
            elif t == 3:
                draw_cobble(g, x, y, rnd)
            elif t == 4:
                draw_grass(g, x, y, rnd, True)
            elif t == 5:
                draw_slab(g, x, y, rnd)
            elif t == 14:
                draw_road(g, x, y, rnd)
            else:
                TILE_DRAW[t](g, x, y, rnd)
    # faixas de pedestres nas travessias da avenida
    for ya, yb in CROSS_ROWS:
        for y in (ya, yb):
            for x in range(AV0, AV1):
                for bar in range(0, TS, 6):
                    g.fill((238, 232, 244), (x * TS + bar, y * TS + 2 if y == ya else y * TS, 3, TS - 2))
    # meio-fio
    cross_y = set(rw for pr in CROSS_ROWS for rw in pr)
    for y in range(MH):
        if y in cross_y:
            continue
        x = shore(y)
        g.fill((84, 70, 98), (x * TS - 1, y * TS, 1, TS))
        g.fill((238, 232, 220), (x * TS, y * TS, 3, TS))
        g.fill((176, 150, 162), (x * TS + 3, y * TS, 1, TS))
        g.fill((238, 232, 220), (AV0 * TS - 3, y * TS, 3, TS))
        g.fill((84, 70, 98), (AV0 * TS, y * TS, 1, TS))
    # praça circular
    draw_plaza(g)
    # contorno de meio-fio onde o calçamento encontra a grama
    for y in range(MH):
        for x in range(MW):
            t = tiles[y][x]
            if t not in (1, 3, 5):
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < MW and 0 <= ny < MH and tiles[ny][nx] in (2, 4) and not (t == 1 and dx < 0):
                    x0, y0 = x * TS, y * TS
                    if dx < 0:
                        g.fill((232, 206, 192), (x0, y0, 3, TS)); g.fill((120, 84, 104), (x0 + 3, y0, 1, TS))
                    elif dx > 0:
                        g.fill((232, 206, 192), (x0 + TS - 3, y0, 3, TS)); g.fill((120, 84, 104), (x0 + TS - 4, y0, 1, TS))
                    elif dy < 0:
                        g.fill((232, 206, 192), (x0, y0, TS, 3)); g.fill((120, 84, 104), (x0, y0 + 3, TS, 1))
                    else:
                        g.fill((232, 206, 192), (x0, y0 + TS - 3, TS, 3)); g.fill((120, 84, 104), (x0, y0 + TS - 4, TS, 1))
    # decalques: poças, bueiros, papéis
    rr = random.Random(77)
    for _ in range(240):
        x, y = rr.randrange(MW), rr.randrange(MH)
        if tiles[y][x] not in (3, 1, 5, 0):
            continue
        px, py = x * TS + rr.randrange(2, 12), y * TS + rr.randrange(3, 12)
        if tiles[y][x] == 0 and rr.random() < .6:
            continue
        w = rr.randrange(9, 20)
        h = max(3, w // 3)
        pygame.draw.ellipse(g, (118, 112, 160), (px, py, w, h))
        pygame.draw.ellipse(g, (170, 182, 222), (px + 1, py + 1, w - 2, h - 2))
        g.fill((226, 236, 255), (px + 3, py + 1, max(2, w // 3), 1))
        g.set_at((px + w - 4, py + h - 2), (236, 190, 210))
    for mx, my in ((50, 32), (62, 46), (52, 47), (29, 24), (31, 48), (30, 62), (44, 20), (72, 20), (60, 59),
                   (70, 8), (50, 8), (85, 30), (85, 50), (29, 10), (28, 70)):
        cx, cy = mx * TS + 8, my * TS + 8
        pygame.draw.ellipse(g, (70, 52, 78), (cx - 7, cy - 4, 14, 8))
        pygame.draw.ellipse(g, (118, 98, 126), (cx - 6, cy - 4, 12, 7))
        pygame.draw.ellipse(g, (92, 74, 104), (cx - 5, cy - 3, 10, 5))
        for k in (-3, 0, 3):
            g.fill((60, 44, 70), (cx + k, cy - 2, 1, 4))
    for _ in range(160):
        x, y = rr.randrange(MW), rr.randrange(MH)
        if tiles[y][x] in (3, 1, 5):
            px, py = x * TS + rr.randrange(14), y * TS + rr.randrange(14)
            g.fill((246, 238, 226), (px, py, 3, 2))
            g.fill((160, 120, 140), (px, py + 2, 3, 1))
    # campinho de pelada: linhas do campo
    px0, py0, pw, ph = 44 * TS, 62 * TS, 12 * TS, 12 * TS
    wl = (240, 246, 236)
    pygame.draw.rect(g, wl, (px0 + 6, py0 + 6, pw - 12, ph - 12), 1)
    pygame.draw.line(g, wl, (px0 + 6, py0 + ph // 2), (px0 + pw - 6, py0 + ph // 2), 1)
    pygame.draw.circle(g, wl, (px0 + pw // 2, py0 + ph // 2), 22, 1)
    pygame.draw.rect(g, wl, (px0 + pw // 2 - 36, py0 + 6, 72, 34), 1)
    pygame.draw.rect(g, wl, (px0 + pw // 2 - 36, py0 + ph - 6 - 34, 72, 34), 1)
    return g


def build_minimap(tiles):
    m = pygame.Surface((MW * 2, MH * 2))
    cols = {0: (70, 62, 90), 1: (226, 204, 186), 2: (112, 176, 110),
            3: (196, 140, 134), 4: (62, 126, 100), 5: (214, 186, 170),
            6: (40, 100, 160), 7: (238, 212, 168), 8: (230, 224, 226), 9: (50, 98, 80),
            10: (190, 176, 178), 11: (84, 160, 196), 12: (110, 172, 98), 13: (230, 170, 70), 14: (70, 62, 90),
            15: (176, 150, 128), 16: (160, 108, 92)}
    for y in range(MH):
        for x in range(MW):
            m.fill(cols[tiles[y][x]], (x * 2, y * 2, 2, 2))
    return m


# ----------------------------------------------------------------------------
# Objetos e atores
# ----------------------------------------------------------------------------
_shadow_cache = {}


class Obj:
    def __init__(self, spr, x, y, col=None, frames=None, fps=8, bob=0.0, shadow=True, lights=None):
        self.frames = frames or [spr]
        self.x, self.y = x, y
        self.col = col
        self.fps = fps
        self.bob = bob
        self.lights = lights or []
        self.shadow = None
        if shadow:
            args = shadow if isinstance(shadow, tuple) else ()
            key = (id(self.frames[0]), args)
            if key not in _shadow_cache:
                _shadow_cache[key] = make_shadow(self.frames[0], *args)
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
        self.frames, self.anchor = cfg["actor"]() if cfg.get("actor") else make_actor(cfg["p"])
        self.quest = cfg.get("quest", False)
        self.hop = cfg["p"].get("scale", 1.0) < 1.0
        self.rect = pygame.Rect(int(self.x) - 5, int(self.y) - 5, 10, 5)
        self.talked = False
        self.home = (self.x, self.y)
        rt = NPC_ROUTES.get(self.id)
        self.stops = rt["stops"] if rt else []
        self.speed = rt["speed"] if rt else 0
        self.anim = random.random() * 3
        self.reset()

    def reset(self):
        self.x, self.y = self.home
        self.path = []
        self.moving = False
        self.talking = False
        self.chase = False
        self.repath = 0.0
        self.stuck = 0.0
        self.stop_i = 0
        self.wait = random.uniform(1.0, 6.0)
        self.rect.x, self.rect.y = int(self.x) - 5, int(self.y) - 5

    def frame(self):
        if self.moving:
            return self.frames[self.face][[0, 1, 0, 2][int(self.anim * 7) % 4]]
        return self.frames[self.face][0]

    def update(self, dt, g):
        """Rotina: espera num lugar, escolhe outro, acha o caminho e vai andando."""
        if (not self.stops and not self.chase) or self.talking:
            self.moving = False
            return
        if g.state == "play" and not self.chase and self.path:
            ddx, ddy = self.path[0][0] - self.x, self.path[0][1] - self.y
            pdx, pdy = g.px - self.x, g.py - self.y
            if math.hypot(pdx, pdy) < 15 and ddx * pdx + ddy * pdy > 0:
                self.moving = False      # o agente está no caminho: espera e, se demorar, desvia pelo lado
                self.stuck += dt
                if self.stuck > 1.2:
                    self.stuck = 0.0
                    dd = math.hypot(ddx, ddy) or 1.0
                    for sgn in (1, -1):
                        sx_, sy_ = self.x - ddy / dd * 16 * sgn, self.y + ddx / dd * 16 * sgn
                        if g.cell_free(sx_, sy_):
                            self.path.insert(0, (sx_, sy_))
                            break
                return
            self.stuck = 0.0
        speed = self.speed * (2.0 if self.chase else 1.0)
        if self.chase:
            self.repath -= dt
            if self.repath <= 0 or not self.path:
                self.path = g.find_path((self.x, self.y), (g.px, g.py))
                self.repath = 1.2
        elif not self.path:
            self.moving = False
            self.wait -= dt
            if self.wait <= 0:
                self.stop_i = random.choice([i for i in range(len(self.stops)) if i != self.stop_i])
                tx, ty, w0, w1 = self.stops[self.stop_i]
                self.path = g.find_path((self.x, self.y), (tx * TS + 8, ty * TS + 14))
                self.wait = random.uniform(w0, w1)
            return
        if not self.path:
            self.moving = False
            return
        tx, ty = self.path[0]
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 1.5:
            self.path.pop(0)
            return
        step = min(d, speed * dt)
        self.x += dx / d * step
        self.y += dy / d * step
        if abs(dx) > abs(dy):
            self.face = "right" if dx > 0 else "left"
        else:
            self.face = "down" if dy > 0 else "up"
        self.moving = True
        self.anim += dt
        self.rect.x, self.rect.y = int(self.x) - 5, int(self.y) - 5


NPC_DEFS = [
    dict(id="cida", name="Dona Cida", dlg="cida", pos=(58, 41), face="down", quest=True,
         p=dict(skin=(166, 114, 80), hair=(226, 224, 230), style="bun", top=(252, 250, 250),
                skirt=(112, 78, 140), shoes=(120, 70, 80))),
    dict(id="tavares", name="Tavares", dlg="tavares", pos=(62, 39), face="left", quest=True,
         p=dict(skin=(210, 164, 124), hair=(36, 26, 24), style="short", top=(240, 236, 224),
                sleeve=(240, 236, 224), legs=(112, 92, 76), shoes=(66, 46, 38), glasses=True,
                headwear="hat", hw=[(120, 90, 62)])),
    dict(id="zeca", name="Zeca", dlg="zeca", pos=(16, 40), face="down", quest=True,
         p=dict(skin=(124, 78, 52), hair=(24, 18, 22), style="long", top=(236, 148, 44),
                sleeve=(236, 148, 44), legs=(56, 78, 146), shoes=(86, 54, 40), beard=True)),
    dict(id="lucia", name="Lúcia", dlg="lucia", pos=(66, 16), face="down", quest=True,
         p=dict(skin=(174, 124, 88), hair=(30, 20, 28), style="tail", top=(214, 54, 66),
                sleeve=(214, 54, 66), legs=(66, 90, 150), shoes=(240, 236, 236))),
    dict(id="dom", name="Dom Aurélio", dlg="dom", pos=(51, 16), face="down", quest=True,
         p=dict(skin=(174, 118, 84), hair=(214, 214, 220), style="short", top=(40, 36, 52),
                sleeve=(40, 36, 52), legs=(40, 36, 52), shoes=(24, 20, 28), ruff=True)),
    dict(id="nelson", name="Seu Nelson", dlg="nelson", pos=(50, 62), face="up", quest=True,
         p=dict(skin=(146, 94, 62), hair=(24, 18, 22), style="short", top=(64, 98, 152),
                sleeve=(64, 98, 152), legs=(76, 76, 100), shoes=(96, 64, 44),
                headwear="morion", hw=[(246, 206, 56)])),
    dict(id="osmar", name="Seu Osmar", dlg="osmar", pos=(52, 32), face="down",
         p=dict(skin=(224, 184, 154), hair=(176, 176, 184), style="short", top=(98, 98, 116),
                sleeve=(98, 98, 116), legs=(76, 76, 90), shoes=(34, 30, 40), ruff=True, glasses=True,
                headwear="hat", hw=[(70, 66, 80)])),
    dict(id="brandao", name="Coronel Brandão", dlg="brandao", pos=(55, 34), face="down",
         p=dict(skin=(204, 154, 114), hair=(36, 30, 28), style="short", top=(92, 110, 66),
                sleeve=(92, 110, 66), legs=(78, 88, 56), shoes=(28, 22, 28), beard=True,
                headwear="hat", hw=[(92, 110, 66)])),
    dict(id="tiao", name="Tião", dlg="tiao", pos=(53, 39), face="right",
         p=dict(skin=(134, 88, 58), hair=(24, 18, 22), style="short", top=(244, 234, 104),
                sleeve=(244, 234, 104), legs=(66, 96, 150), shoes=(210, 210, 214),
                scale=0.76)),
    dict(id="helen", name="Helen Harper", dlg="helen", pos=(36, 38), face="right", quest=True,
         p=dict(skin=(236, 196, 168), hair=(222, 182, 92), style="bob", top=(84, 138, 180),
                sleeve=(84, 138, 180), legs=(64, 64, 88), shoes=(78, 56, 46))),
    # aliado fictício (arquétipo de professor/organizador da resistência civil)
    dict(id="mario", name="Professor Mário", dlg="mario", pos=(66, 42), face="down", quest=True,
         p=dict(skin=(190, 140, 104), hair=(190, 190, 198), style="short", top=(120, 84, 60),
                sleeve=(120, 84, 60), legs=(58, 62, 84), shoes=(40, 30, 34), glasses=True, beard=True,
                headwear="hat", hw=[(54, 66, 96)])),
]

# Pedestres de fundo (sem diálogo): só dão vida à cidade
WALKER_DEFS = [
    dict(skin=(190, 140, 104), hair=(40, 28, 24), style="short", top=(120, 170, 120), sleeve=(120, 170, 120),
         legs=(70, 70, 90), shoes=(50, 40, 40)),
    dict(skin=(150, 100, 70), hair=(30, 22, 26), style="long", top=(230, 120, 150), skirt=(80, 70, 130),
         shoes=(90, 50, 60)),
    dict(skin=(226, 184, 150), hair=(150, 90, 50), style="tail", top=(240, 200, 80), sleeve=(240, 200, 80),
         legs=(60, 100, 150), shoes=(230, 230, 230)),
    dict(skin=(120, 80, 56), hair=(20, 16, 20), style="short", top=(110, 70, 140), sleeve=(110, 70, 140),
         legs=(50, 56, 80), shoes=(30, 26, 36), headwear="hat", hw=[(70, 60, 90)]),
    dict(skin=(200, 150, 120), hair=(60, 40, 30), style="bob", top=(250, 250, 250), skirt=(214, 70, 80),
         shoes=(70, 50, 60), glasses=True),
    dict(skin=(214, 170, 140), hair=(120, 70, 40), style="short", top=(240, 120, 60), sleeve=(240, 120, 60),
         legs=(60, 70, 110), shoes=(40, 40, 50)),
    dict(skin=(150, 100, 70), hair=(30, 22, 26), style="bun", top=(90, 170, 210), skirt=(250, 230, 120),
         shoes=(120, 70, 60)),
    dict(skin=(214, 160, 120), hair=(50, 34, 28), style="short", top=(214, 160, 120), sleeve=(214, 160, 120),
         legs=(236, 84, 70), shoes=(214, 160, 120)),
    dict(skin=(190, 134, 100), hair=(40, 28, 24), style="long", top=(250, 200, 60), skirt=(70, 170, 190),
         shoes=(190, 134, 100)),
    dict(skin=(236, 196, 168), hair=(240, 230, 200), style="short", top=(70, 150, 110), sleeve=(70, 150, 110),
         legs=(220, 200, 160), shoes=(80, 60, 50), headwear="hat", hw=[(230, 210, 150)]),
    dict(skin=(150, 100, 70), hair=(24, 18, 22), style="short", top=(250, 220, 60), sleeve=(250, 220, 60),
         legs=(40, 110, 60), shoes=(240, 240, 240), scale=0.76),
    dict(skin=(214, 170, 140), hair=(120, 70, 40), style="short", top=(60, 120, 220), sleeve=(60, 120, 220),
         legs=(240, 240, 240), shoes=(50, 50, 60), scale=0.76),
]


# ----------------------------------------------------------------------------
# Diálogos
# ----------------------------------------------------------------------------
def D(sp, text, ch=None, nxt=None, fx=None, flag=None, end=None):
    return dict(sp=sp, text=text, ch=ch, nxt=nxt, fx=fx or {}, flag=flag, end=end)


def C(text, nxt, fx=None):
    return dict(text=text, nxt=nxt, fx=fx or {})


DLG = {
    # ------------------------------------------------------------------ Cida
    "cida": {
        "start": D("Dona Cida",
                   "Um porco que fala... Pois que seja. Hoje é melhor falar com bicho do que com as paredes. "
                   "Meu filho Paulo saiu para a faculdade numa manhã de 1970 e nunca mais voltou. "
                   "Na delegacia dizem que ele nunca esteve preso.",
                   ch=[C("Sinto muito, Dona Cida. Conte no seu tempo, eu escuto.", "emp"),
                       C("Preciso de datas, nomes e endereços. O que a senhora tem?", "dir"),
                       C("Fale baixo. Aqui as paredes têm ouvidos. Vamos ao banco da praça.", "cau")]),
        "emp": D("Dona Cida", "Ela aperta uma foto 3x4 contra o peito. 'Foram homens sem farda, num carro sem "
                 "placa. Ninguém assina nada, ninguém responde por nada.'", nxt="fim", fx={"evid": 8}),
        "dir": D("Dona Cida", "'Tenho o dia, a hora e a cor do carro. Já bati em quartéis, tribunais e igrejas. "
                 "Em todos me mandam esperar.'", nxt="fim", fx={"evid": 6, "susp": 4}),
        "cau": D("Dona Cida", "Ela olha para os lados e baixa a voz: 'Fizeram igual com a vizinha. Quem pergunta "
                 "demais vira suspeito.'", nxt="fim", fx={"evid": 5, "susp": -3}),
        "fim": D("Dona Cida", "Isso se chama desaparecimento forçado: a pessoa some, o Estado nega e a família "
                 "fica sem saber nem onde chorar. Leve a história do meu Paulo para fora do país, {nome}. "
                 "Escrevi atrás da foto o dia em que ele sumiu: 15 de março.",
                 flag="cida"),
        "again": D("Dona Cida", "Não deixe esquecerem o nome do meu filho."),
    },
    # --------------------------------------------------------------- Tavares
    "tavares": {
        "start": D("Tavares",
                   "Psiu! Jornalista de verdade escreve com um olho no papel e outro na porta. Tem um censor "
                   "dentro da redação todo dia, vetando o que sai. O que quer saber, {nome}?",
                   ch=[C("Como funciona a censura nos jornais?", "cens"),
                       C("O senhor tem cópia das ordens de censura?", "prova"),
                       C("Pode me indicar quem mais pode ajudar?", "rede")]),
        "cens": D("Tavares", "'Chega um bilhete da polícia com os temas proibidos: tortura, greve, crise. Onde "
                  "falta notícia, o jornal enche de receita de bolo, só para o leitor notar o buraco.'",
                  nxt="fim", fx={"evid": 8, "susp": 2}),
        "prova": D("Tavares", "Ele tira do bolso um papel dobrado: 'Guardei escondido. Se me pegam com isto, perco "
                   "o emprego... ou a liberdade.'", nxt="fim", fx={"evid": 10, "susp": 7}),
        "rede": D("Tavares", "'Fale com a estudante Lúcia, com Dom Aurélio e com Seu Nelson, o operário. Cada um "
                  "enxerga um pedaço da mesma coisa.'", nxt="fim", fx={"evid": 5, "susp": -2}),
        "fim": D("Tavares", "Sem imprensa livre, ninguém sabe o que acontece, e o governo diz que está tudo "
                 "ótimo. Mostre isso lá fora, {nome}.", flag="tavares"),
        "again": D("Tavares", "Escrevo o que posso. O resto, rezo para alguém contar."),
    },
    # ------------------------------------------------------------------ Zeca
    "zeca": {
        "start": D("Zeca",
                   "Boa noite, bicho! Sou o Zeca, compositor. Tenho vinte canções na gaveta, todas vetadas. "
                   "Para tocar uma música preciso mandar a letra antes para um funcionário que decide se pode. "
                   "Me diz: você é fã ou fiscal?",
                   ch=[C("Fã! Toca algo para mim.", "fa"),
                       C("Sou agente. Quero provas da censura nas artes.", "prova"),
                       C("Fiscal, nunca! Mas por que não toca no rádio?", "radio")]),
        "fa": D("Zeca", "'Posso tocar o que o censor deixa passar: amor, saudade... E o resto eu canto por "
                "metáfora. Todo mundo entende, e o censor não.'", nxt="fim", fx={"evid": 7, "susp": 1}),
        "prova": D("Zeca", "Ele arregala os olhos, depois ri nervoso: 'Tenho a carta do órgão de censura vetando "
                   "minha letra inteira, assinada e carimbada.'", nxt="fim", fx={"evid": 10, "susp": 6}),
        "radio": D("Zeca", "'Colegas meus tiveram que deixar o país: o exílio. Quem ficou canta de lado. A rádio "
                   "só toca o que o governo aprova.'", nxt="fim", fx={"evid": 6, "susp": -1}),
        "fim": D("Zeca", "Artista calado é governo feliz. Mas canção é bicho teimoso: sai por qualquer fresta. "
                 "Conte lá fora que no Brasil até música precisa de licença.", flag="zeca"),
        "again": D("Zeca", "Ainda estou compondo, bicho. Cada verso é um recado."),
    },
    # ----------------------------------------------------------------- Lúcia
    "lucia": {
        "start": D("Lúcia",
                   "Ei, cuidado! A entidade dos estudantes foi posta na ilegalidade. Quem protesta pode ser "
                   "expulso por decreto, e ainda preso. Eu estou escondida. Por que veio falar comigo, porco?",
                   ch=[C("Quero entender o que aconteceu com os estudantes.", "ent"),
                       C("Preciso de provas: panfletos, atas, decretos.", "prova"),
                       C("Você está segura? Posso levá-la para longe.", "prot")]),
        "ent": D("Lúcia", "'Fecharam centros acadêmicos e proibiram assembleias. O Decreto 477 permite expulsar "
                 "quem protestar. Tenho colegas presos e outros desaparecidos.'",
                 nxt="fim", fx={"evid": 7, "susp": 2}),
        "prova": D("Lúcia", "Ela tira de dentro de um caderno um panfleto roxo de mimeógrafo: 'Rodamos de "
                   "madrugada. Quem é pego com isto pega anos de cadeia.'", nxt="fim", fx={"evid": 9, "susp": 6}),
        "prot": D("Lúcia", "'Tenho um quarto emprestado e uma mala sempre pronta. Fugir não resolve, mas... "
                  "obrigada por perguntar.'", nxt="fim", fx={"evid": 4, "susp": -4}),
        "fim": D("Lúcia", "O AI-5 fechou o Congresso e acabou com as garantias de liberdade. Qualquer estudante "
                 "vira 'subversivo' num minuto. Conte isso pro mundo, {nome}.", flag="lucia"),
        "again": D("Lúcia", "Se me perguntarem, eu nunca falei com você. Nem com porco nenhum."),
    },
    # ------------------------------------------------------------------- Dom
    "dom": {
        "start": D("Dom Aurélio",
                   "Paz, meu filho... ou meu porquinho, perdão. Nossa igreja virou abrigo de quem foge e "
                   "ouvido de quem sofre. Sabemos que há presos torturados em porões, e o governo diz que é "
                   "invenção. O que o traz aqui, {nome}?",
                   ch=[C("Preciso de testemunhos sobre as prisões ilegais.", "test"),
                       C("Posso proteger quem está sendo perseguido?", "prot"),
                       C("O senhor não tem medo de falar assim?", "medo")]),
        "test": D("Dom Aurélio", "'Recebemos famílias toda semana. Cartas, nomes e datas ficam guardados na "
                  "sacristia. Quem pergunta pelos presos é chamado de comunista.'",
                  nxt="fim", fx={"evid": 9, "susp": 4}),
        "prot": D("Dom Aurélio", "'Há perseguidos escondidos nos fundos da paróquia. Ajudá-los a sair do país "
                  "é seguir o Evangelho, não só a lei.'", nxt="fim", fx={"evid": 6, "susp": -3}),
        "medo": D("Dom Aurélio", "'Tenho. Mas medo não é argumento. A Igreja não pode calar enquanto há gente "
                  "sofrendo no escuro.'", nxt="fim", fx={"evid": 5, "susp": 1}),
        "fim": D("Dom Aurélio", "Os porões existem, {nome}. Quem foi levado muitas vezes não aparece em lista "
                 "alguma. Que o mundo saiba, e que Deus nos perdoe pela demora.", flag="dom"),
        "again": D("Dom Aurélio", "Vá em paz e tome cuidado. A verdade tem pés lentos, mas chega."),
    },
    # ---------------------------------------------------------------- Nelson
    "nelson": {
        "start": D("Seu Nelson",
                   "Boa noite, bicho! Sou metalúrgico. O governo diz que a economia cresce como nunca, um "
                   "'milagre', mas o meu salário só encolhe. Greve é proibida e o sindicato tem interventor. "
                   "Quer mesmo ouvir um operário?",
                   ch=[C("Quero. Como é o dia a dia na fábrica?", "dia"),
                       C("Como o governo controla os sindicatos?", "sind"),
                       C("O 'milagre econômico' não ajuda os pobres?", "mir")]),
        "dia": D("Seu Nelson", "'Doze horas de máquina e um salário que não paga o feijão. Acidente demais, e ai "
                 "de quem reclamar: vira agitador.'", nxt="fim", fx={"evid": 8, "susp": 2}),
        "sind": D("Seu Nelson", "'Trocam a diretoria por interventores. Quem é eleito pelos companheiros é "
                  "cassado. O sindicato virou repartição.'", nxt="fim", fx={"evid": 7, "susp": 3}),
        "mir": D("Seu Nelson", "'O bolo cresceu, mas só quem tem a faca fica com fatia. A dívida externa sobe "
                 "e a gente aperta o cinto.'", nxt="fim", fx={"evid": 6, "susp": -1}),
        "fim": D("Seu Nelson", "Crescimento sem direitos não é milagre, é conta que sobra para o povo. "
                 "Conte isso a quem escuta lá fora.", flag="nelson"),
        "again": D("Seu Nelson", "Amanhã cedo, de novo a máquina. Mas a gente aguenta, bicho."),
    },
    # ----------------------------------------------------------------- Osmar
    "osmar": {
        "start": D("Seu Osmar",
                   "Parado aí! Documento. Ah, é um... porco? Nunca vi. Sou funcionário da Divisão de Censura: "
                   "eu leio, eu carimbo e protejo a moral e os bons costumes.",
                   ch=[C("Posso ver o que o senhor carimba?", "a"),
                       C("Parabéns pelo trabalho! O senhor deve ler muito.", "b"),
                       C("Saia da frente, burocrata.", "c")]),
        "a": D("Seu Osmar", "Osmar sorri e mostra uma pilha de matérias cobertas por tarjas pretas. 'Segurança "
               "nacional. O povo não precisa saber.' Você memoriza cada tema vetado.",
               nxt="fim", fx={"evid": 7, "susp": 5}),
        "b": D("Seu Osmar", "'Leio tudo, é verdade. Mas só eu posso ler. Aliás, o que um porco faz perguntando?' "
               "Você desconversa.", nxt="fim", fx={"evid": 3, "susp": 1}),
        "c": D("Seu Osmar", "'Ora! Insolente! Vou anotar sua descrição.' Ele rabisca algo e fecha a cara.",
               nxt="fim", fx={"susp": 12}),
        "fim": D("Seu Osmar", "Cuidado com o que fala por aqui, bicho. Nunca se sabe quem está ouvindo."),
        "again": D("Seu Osmar", "Ainda por aqui? Circule."),
    },
    # --------------------------------------------------------------- Brandão
    "brandao": {
        "start": D("Coronel Brandão",
                   "Alto lá! Que bicho é esse de sobretudo? Sou o Coronel Brandão, encarregado da ordem. Aqui "
                   "não há subversão: há progresso, estradas, usinas e a Copa do Mundo. Alguma queixa?",
                   ch=[C("Nenhuma, coronel. Só passeando pela praça.", "a"),
                       C("O senhor garante que ninguém foi preso sem processo?", "b"),
                       C("Belas obras, coronel! Fale-me mais do 'Brasil Grande'.", "c")]),
        "a": D("Coronel Brandão", "Ele estreita os olhos. 'Passeios demais chamam atenção. Circule.'",
               nxt="fim", fx={"susp": 3}),
        "b": D("Coronel Brandão", "O rosto dele endurece. 'Garanto que quem não deve não teme. Está insinuando "
               "alguma coisa?' A evasiva diz mais do que uma resposta.", nxt="fim", fx={"evid": 8, "susp": 15}),
        "c": D("Coronel Brandão", "Ele se anima e recita estradas, usinas e números oficiais. Você anota tudo "
               "para comparar depois com as histórias do povo.", nxt="fim", fx={"evid": 5, "susp": -2}),
        "fim": D("Coronel Brandão", "'Ame-o ou deixe-o', é o que eu digo. Boa noite, e fique longe de problemas."),
        "again": D("Coronel Brandão", "Ainda por aqui? Circule, cidadão... ou seja lá o que for."),
    },
    # ------------------------------------------------------------------ Tião
    "tiao": {
        "start": D("Tião",
                   "Moço-porco! Você é de circo? Todo mundo na rua fala baixinho, até minha mãe. Por quê? "
                   "É só na hora do jogo da Copa que todo mundo grita!",
                   ch=[C("Muita gente tem medo de falar, Tião. Mas isso pode mudar.", "a"),
                       C("Vai jogar bola, Tião. Depois eu te explico.", "b"),
                       C("O que você já ouviu na vizinhança?", "c")]),
        "a": D("Tião", "Tião fica pensativo. 'Minha mãe disse para eu não perguntar demais. Vou perguntar "
               "baixinho, então.'", fx={"evid": 2}),
        "b": D("Tião", "'Tá bom! Mas depois você me conta!'"),
        "c": D("Tião", "'Ouvi dizer que um moço sumiu do prédio ao lado. Mas é segredo!'",
               fx={"evid": 3, "susp": 2}),
        "again": D("Tião", "Aqui todo mundo torce pelo Brasil, até quem tem medo."),
    },
    # ----------------------------------------------------------------- Helen
    # ----------------------------------------------------------------- Mário (aliado)
    "mario": {
        "start": D("Professor Mário",
                   "Psiu, porco de sobretudo! Dei aula de história até um decreto me expulsar da faculdade. "
                   "Hoje coordeno uma rede de gente comum: aqui ninguém pega em armas, a nossa arma é a "
                   "informação. A Central falou de você. Está pronto, {nome}?",
                   ch=[C("Pronto. O que a rede precisa de mim?", "tarefas"),
                       C("Por que o senhor confia em mim?", "porque"),
                       C("Como evito a polícia?", "policia")]),
        "tarefas": D("Professor Mário",
                     "'A rede tem três linhas de ação: a da Igreja, a da Rádio e a da Imprensa. Cada uma tem "
                     "suas missões e termina de um jeito. Quando estiver pronto, volte a falar comigo e escolha "
                     "uma. Mas escolhida a linha, não há volta, e a Central só segura o prazo por quinze minutos.'",
                     nxt="fim", fx={"evid": 3}),
        "porque": D("Professor Mário",
                    "'Porque ninguém desconfia de um porco que passeia. E porque a rede julga as pessoas "
                    "pelo que fazem, não pelo que dizem.'", nxt="fim", fx={"susp": -2}),
        "policia": D("Professor Mário",
                     "'Com itens na mochila, fique longe do Coronel Brandão e do censor Osmar: a suspeita "
                     "sobe rápido. Segure Shift para andar mais depressa.'", nxt="fim"),
        "fim": D("Professor Mário",
                 "Escolha sua linha comigo e seja rápido: a Central só segura a linha por quinze minutos. Se travar em alguma "
                 "tarefa, volte aqui que eu dou uma dica.", flag="mario_ok"),
        "dica_rota": D("Professor Mário",
                       "Três linhas, {nome}, e quem entra numa vai até o fim dela: não dá para trocar no meio do "
                       "caminho. Qual você escolhe?",
                       ch=[C("Igreja: panfletos, Dom Aurélio e o cofre.", "conf_igreja"),
                           C("Rádio: a fita proibida e a voz do morro.", "conf_radio"),
                           C("Imprensa: negativos censurados e jornalistas.", "conf_imprensa"),
                           C("Ainda não decidi.", "rota_volta")]),
        "conf_igreja": D("Professor Mário",
                         "Linha da Igreja: panfletos na Feira, Dom Aurélio, Dona Cida e o cofre da sacristia. "
                         "É a mais longa, mas rende a prova mais pesada. Sem volta. Confirma?",
                         ch=[C("Confirmo. Sigo até o fim.", "rota_igreja", fx={"route": "igreja"}),
                             C("Deixe-me pensar.", "dica_rota")]),
        "conf_radio": D("Professor Mário",
                        "Linha da Rádio: a fita na gaveta do Largo, o estúdio do Zeca e depois a voz do Zeca e do "
                        "Tavares. Rápida e barulhenta. Sem volta. Confirma?",
                        ch=[C("Confirmo. Sigo até o fim.", "rota_radio", fx={"route": "radio"}),
                            C("Deixe-me pensar.", "dica_rota")]),
        "conf_imprensa": D("Professor Mário",
                           "Linha da Imprensa: Tavares, os negativos do arquivo e Seu Nelson. Arriscada com a "
                           "polícia por perto. Sem volta. Confirma?",
                           ch=[C("Confirmo. Sigo até o fim.", "rota_imprensa", fx={"route": "imprensa"}),
                               C("Deixe-me pensar.", "dica_rota")]),
        "rota_igreja": D("Professor Mário",
                         "Está feito: Linha da Igreja. Comece pela mochila na Feira Livre.", flag="rota_ok"),
        "rota_radio": D("Professor Mário",
                        "Está feito: Linha da Rádio. Comece pela gaveta do Largo da Carioca.", flag="rota_ok"),
        "rota_imprensa": D("Professor Mário",
                           "Está feito: Linha da Imprensa. Comece procurando o Tavares.", flag="rota_ok"),
        "rota_volta": D("Professor Mário",
                        "Pense rápido, {nome}: o relógio da Central não para."),
        "dica_r_zeca": D("Professor Mário",
                         "Zeca circula entre o Calçadão e a Av. Atlântica. Ouça a história dele."),
        "dica_r_tavares": D("Professor Mário",
                            "Tavares anda entre o Largo da Carioca e a Feira Livre. Ouça o que ele tem a dizer."),
        "dica_i_tavares": D("Professor Mário",
                            "Tavares anda entre o Largo da Carioca e a Feira Livre. Comece por ele."),
        "dica_i_pick": D("Professor Mário",
                         "A gaveta do arquivo fica no Largo da Carioca. Memorize os tons e repita com as teclas "
                         "1 a 4."),
        "dica_i_drop": D("Professor Mário",
                         "Leve os negativos ao Tavares. Cuidado com o censor Osmar."),
        "dica_i_nelson": D("Professor Mário",
                           "Seu Nelson circula perto da Feira e da zona operária. Ele só fala depois do Tavares."),
        "dica_a_pick": D("Professor Mário",
                         "A mochila está na Feira Livre, ao sul. Lá, gire o disco da cifra até o bilhete "
                         "fazer sentido."),
        "dica_a_drop": D("Professor Mário",
                         "O bilhete mandou entregar os panfletos a Dom Aurélio. Ele circula entre o Largo da "
                         "Carioca e a Praça."),
        "dica_b_pick": D("Professor Mário",
                         "A fita está numa gaveta no Largo da Carioca. Memorize os tons do orelhão e repita "
                         "na mesma ordem, com as teclas 1 a 4."),
        "dica_b_drop": D("Professor Mário",
                         "Leve a fita ao estúdio clandestino do Zeca, na Avenida Atlântica. Cuidado com as "
                         "patrulhas."),
        "dica_c_cida": D("Professor Mário",
                         "Para o cofre, fale primeiro com Dona Cida: a senha é uma data que só ela guarda."),
        "dica_c_pick": D("Professor Mário",
                         "A chave de ferro está escondida no Calçadão de Copacabana. Pegue-a e volte ao Largo."),
        "dica_c_cofre": D("Professor Mário",
                          "O cofre fica na sacristia, no Largo da Carioca. A senha tem quatro dígitos: dia e "
                          "mês, nessa ordem."),
        "dica_fim": D("Professor Mário",
                      "Missões da rede cumpridas, {nome}. Falta o dossiê chegar a Helen Harper. Depressa!"),
        "again": D("Professor Mário", "Siga em frente, agente. A rede confia em você."),
    },
    "helen": {
        "wait": D("Helen Harper",
                  "Sou Helen Harper, correspondente de um jornal estrangeiro. Sem provas, não publico nada. "
                  "Volte com pelo menos três testemunhos e as provas da sua linha de ação, {nome}: "
                  "desaparecidos, censura, estudantes, Igreja, operários."),
        "start": D("Helen Harper",
                   "Você reuniu depoimentos de gente de todos os lados. É um dossiê e tanto. Como quer levar "
                   "isso ao mundo, {nome}?",
                   ch=[C("Publique tudo, com nomes e provas, no exterior.", "tudo"),
                       C("Publique em capítulos, protegendo as fontes.", "partes"),
                       C("Imprimamos cópias para distribuir aqui mesmo.", "panf"),
                       C("Deixe para lá. É perigoso demais.", "silencio")]),
        "tudo": D("Helen Harper", "Ela arregala os olhos. 'Corajoso. Vão me expulsar do país, mas o mundo "
                  "vai ler.'", fx={"evid": 6, "susp": 20}, end="denuncia"),
        "partes": D("Helen Harper", "'Combinado. Cada capítulo mostra um pedaço da verdade e mantém as "
                    "pessoas seguras.'", fx={"evid": 5, "susp": -6}, end="partes"),
        "panf": D("Helen Harper", "'Arriscado, mas há muita gente esperando por isso.'",
                  fx={"evid": 3, "susp": 14}, end="panfleto"),
        "silencio": D("Helen Harper", "'Compreendo. Mas o silêncio também é uma escolha, {nome}.'",
                      fx={"evid": -10, "susp": -10}, end="silencio"),
        "semcontato": D("Helen Harper",
                        "Você carrega um dossiê e tanto, mas só entrego meu jornal a quem a Central confirmar. "
                        "Atenda a ligação deles num orelhão e volte aqui, {nome}."),
        "again": D("Helen Harper", "Estou escrevendo. Boa viagem, agente."),
    },
}

ENDINGS = {
    "denuncia": "O dossiê atravessou o oceano e foi parar nas primeiras páginas de jornais estrangeiros. "
                "O governo negou tudo e endureceu o tom, mas a pressão internacional cresceu e as denúncias "
                "de tortura e desaparecimentos passaram a ser difíceis de abafar.",
    "partes": "O dossiê saiu em capítulos, sem expor as fontes. Cada reportagem abriu uma fresta: a censura, os "
              "desaparecidos, os estudantes, os operários. Foi a soma de muitas resistências, de imprensa, "
              "Igreja, artistas e trabalhadores, que desgastou o regime aos poucos.",
    "panfleto": "As cópias mimeografadas circularam de mão em mão, em fábricas, faculdades e igrejas. Alguns "
                "foram presos por carregá-las, mas outros as copiaram de novo. Uma verdade escrita à mão "
                "é difícil de prender.",
    "silencio": "Você guardou o dossiê no fundo de uma gaveta. O medo é a ferramenta mais barata de qualquer "
                "ditadura, e naquela noite ele venceu. As histórias de Cida, Zeca, Lúcia e Nelson continuaram "
                "sem plateia.",
    "capturado": "A suspeita explodiu. Agentes cercaram a rua e levaram o Agente Rosso sob protestos de quem estava ao "
                 "redor. Mas as testemunhas que você reuniu guardaram cópias: a verdade não coube num único porco.",
}

# cenas curtas das missões (entregas e recompensas)
SCENES = {
    "a_dom": {
        "start": D("Dom Aurélio",
                   "Os panfletos! Que Deus abençoe as mãos que os trouxeram, {nome}. Cada folha é um nome "
                   "que alguém tentou apagar.", nxt="fim", fx={"evid": 5}),
        "fim": D("Dom Aurélio",
                 "Vou guardá-los na sacristia e distribuir entre as missas. Se alguém perguntar, nunca "
                 "vimos você.", fx={"evid": 3, "susp": 3}),
    },
    "b_zeca": {
        "start": D("Zeca (rádio pirata)",
                   "Chegou! Com esta fita a rádio do morro toca hoje à noite o que o censor vetou. "
                   "Canção é bicho teimoso, lembra?", nxt="fim", fx={"evid": 5}),
        "fim": D("Zeca (rádio pirata)",
                 "Cada acorde é um recado, {nome}. Agora some daqui antes que a patrulha apareça.",
                 fx={"evid": 3, "susp": 4}),
    },
    "i_tavares": {
        "start": D("Tavares",
                   "Os negativos! O censor Osmar mandou queimar tudo isso na redação, {nome}. Cada foto é uma "
                   "notícia que o país não pode ler.", nxt="fim", fx={"evid": 5}),
        "fim": D("Tavares",
                 "Vou revelar cópias no laboratório da gráfica, sem seu nome e sem o meu. Agora vá, antes que a "
                 "patrulha apareça.", fx={"evid": 3, "susp": 3}),
    },
    "c_cofre": {
        "start": D("Dom Aurélio (bilhete)",
                   "Dentro do cofre havia uma pasta: nomes de presos políticos e as datas em que foram "
                   "levados. Preso à capa, um bilhete: 'Leve a lista a quem possa mostrá-la ao mundo.'",
                   nxt="fim", fx={"evid": 6}),
        "fim": D("Dom Aurélio (bilhete)",
                 "Esta lista é a prova mais pesada que a rede já reuniu. Guarde-a bem, {nome}, e entregue "
                 "a Helen Harper.", fx={"evid": 4, "susp": 4}),
    },
}

ENDINGS["prazo"] = ("O prazo da Central chegou ao fim. A linha foi cortada, a janela de entrega se fechou e o "
                    "dossiê não chegou às mãos de Helen Harper a tempo. As provas ficaram guardadas pela rede, "
                    "à espera de outra chance. A verdade atrasou, mas não morreu.")

ENDINGS.update({
    "igreja_denuncia": "Com a lista dos presos da sacristia nas mãos da imprensa estrangeira, o regime não conseguiu mais negar os nomes. A Igreja de Dom Aurélio abriu as portas às famílias e a pressão internacional cresceu.",
    "igreja_partes": "Capítulo a capítulo, a lista da sacristia virou reportagem sem expor ninguém. Dom Aurélio leu os nomes nas missas, em voz baixa, e as famílias dos desaparecidos descobriram que não estavam sozinhas.",
    "igreja_panfleto": "Os panfletos de Dom Aurélio e as cópias da lista circularam pelas paróquias e filas de ônibus. Alguns foram presos por carregá-los, mas as missas seguintes estavam mais cheias.",
    "igreja_silencio": "A lista dos presos voltou ao cofre da sacristia e a chave voltou ao esconderijo. Dom Aurélio rezou por todos os nomes, em silêncio, esperando que alguém um dia tivesse coragem de lê-los em voz alta.",
    "igreja_prazo": "O prazo acabou antes que a lista da sacristia chegasse a Helen. Dom Aurélio guardou a pasta no cofre, à espera de outra chance. A verdade atrasou, mas não morreu.",
    "radio_denuncia": "A fita do Zeca e o dossiê chegaram juntos ao exterior: uma rádio estrangeira tocou a canção censurada. O regime negou tudo, mas a música já estava na boca do povo.",
    "radio_partes": "A rádio do morro tocou um pedaço da verdade a cada noite, em código, enquanto o dossiê saía em capítulos. Era impossível calar uma canção que ninguém sabia de onde vinha.",
    "radio_panfleto": "Fitas copiadas passaram de mão em mão e a canção proibida virou assobio de rua. Zeca mudou de morro três vezes, mas a fita continuou tocando.",
    "radio_silencio": "O transmissor do morro ficou mudo e a fita foi parar no fundo de uma gaveta. A canção continuou sendo cantada baixinho, em casa, sem plateia.",
    "radio_prazo": "O prazo acabou com a fita ainda no ar, mas sem o dossiê nas mãos de Helen. A rádio do morro seguiu tocando baixinho. A verdade atrasou, mas não morreu.",
    "imprensa_denuncia": "As fotos que o censor mandou vetar saíram na primeira página de jornais estrangeiros, ao lado dos depoimentos de Tavares e de Seu Nelson. O regime não soube explicar o que as imagens mostravam.",
    "imprensa_partes": "O jornal clandestino de Tavares publicou, edição por edição, o que o censor vetava, e a imprensa estrangeira repetiu. A censura virou notícia: cada coluna em branco mostrava o que faltava.",
    "imprensa_panfleto": "Os negativos viraram cartazes e boletins mimeografados em fábricas e faculdades. Tavares perdeu o emprego, mas as imagens já estavam coladas nos muros da cidade.",
    "imprensa_silencio": "Os negativos foram queimados na pia da gráfica para não sobrar prova. Tavares voltou a escrever só o que o censor deixava, e as fotos viveram apenas na memória de quem as viu.",
    "imprensa_prazo": "O prazo acabou com os negativos guardados e o dossiê longe de Helen. A redação clandestina guardou tudo para a próxima edição. A verdade atrasou, mas não morreu.",
})

ENDINGS["resistencia"] = ("Os cartazes, o baú, a gravação do quartel e o manifesto do muro formaram um dossiê "
                          "que ninguém esperava. Quando a verdade saiu do Rio, saiu com nomes, datas, vozes e provas, "
                          "e a cidade inteira amanheceu pichada: FORA DITADURA. O regime não conseguiu calar todo mundo.")

EPILOGO = ("A ditadura ainda duraria anos, mas em 1979 veio a Lei da Anistia, em 1984 milhões foram às ruas "
           "pelas Diretas Já e, em 1985, o país voltou a ter um presidente civil.")


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
# Fonte pixelada: desenha pequeno, sem suavização, e amplia por um fator inteiro
# ----------------------------------------------------------------------------
class PixFont:
    def __init__(self, base, k):
        self.k = k if PIXEL_TEXT else 1
        self.f = pygame.font.Font(None, base if PIXEL_TEXT else base * k)

    def size(self, s):
        w, h = self.f.size(s)
        return (w * self.k, h * self.k)

    def render(self, s, aa, col):
        if not PIXEL_TEXT:
            return self.f.render(s, True, col)
        img = self.f.render(s, False, col)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        if self.k == 1:
            return img
        return pygame.transform.scale(img, (img.get_width() * self.k, img.get_height() * self.k))


_WALKER_CACHE = {}


class Walker:
    """Pedestre de fundo: só anda pela cidade para dar vida ao cenário."""

    def __init__(self, cfg, path, speed, start=0):
        if id(cfg) not in _WALKER_CACHE:
            _WALKER_CACHE[id(cfg)] = make_actor(cfg)
        self.frames, self.anchor = _WALKER_CACHE[id(cfg)]
        self.path = path
        self.i = start % len(path)
        self.x, self.y = path[self.i]
        self.i = (self.i + 1) % len(path)
        self.speed = speed
        self.dir = "down"
        self.anim = random.random() * 3

    def update(self, dt):
        tx, ty = self.path[self.i]
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 2.0:
            self.i = (self.i + 1) % len(self.path)
            return
        self.x += dx / d * self.speed * dt
        self.y += dy / d * self.speed * dt
        if abs(dx) > abs(dy):
            self.dir = "right" if dx > 0 else "left"
        else:
            self.dir = "down" if dy > 0 else "up"
        self.anim += dt

    def frame(self):
        return self.frames[self.dir][[0, 1, 0, 2][int(self.anim * 7) % 4]]


class Voice:
    """Interlocutor invisível das ligações: só tem um retrato (o orelhão)."""

    def __init__(self, spr):
        self.frames = {"down": [spr]}
        self.anchor = (13, 38)
        self.talked = False
        self.talking = False
        self.name = "Central"


def orelhao_sprite():
    """Orelhão: a concha laranja de fibra dos telefones públicos brasileiros."""
    s = pygame.Surface((26, 40), pygame.SRCALPHA)
    org, org_d = (240, 126, 40), (166, 70, 28)
    pygame.draw.rect(s, (60, 56, 70), (7, 38, 12, 2))
    pygame.draw.rect(s, (96, 92, 108), (10, 28, 6, 11))
    pygame.draw.rect(s, (150, 146, 164), (10, 28, 2, 11))
    pygame.draw.ellipse(s, org_d, (1, 2, 24, 30))
    pygame.draw.ellipse(s, org, (1, 1, 23, 29))
    pygame.draw.ellipse(s, tone(org, .4), (4, 3, 8, 9))
    pygame.draw.rect(s, (250, 240, 220), (6, 5, 14, 8))
    pygame.draw.rect(s, (60, 40, 40), (6, 5, 14, 8), 1)
    draw_tiny(s, "TEL", 8, 7, (60, 40, 40))
    pygame.draw.ellipse(s, (50, 30, 44), (5, 14, 16, 17))
    pygame.draw.circle(s, (226, 226, 234), (13, 23), 5)
    pygame.draw.circle(s, (60, 44, 70), (13, 23), 2)
    for k in range(6):
        pygame.draw.rect(s, (60, 44, 70), (10 + k % 3 * 3, 19 + k // 3 * 8, 1, 1))
    pygame.draw.rect(s, (30, 26, 36), (7, 17, 2, 11))
    pygame.draw.rect(s, (200, 200, 214), (7, 17, 1, 11))
    return s


PHONE_TILES = ((36, 40), (75, 17), (21, 47), (49, 60))     # onde há orelhões: avenida, Largo, calçadão e feira
NPC_REQ = dict(lucia="tavares", dom="lucia", nelson="tavares")      # quem indica quem
NPC_NAMES = dict(tavares="Tavares", lucia="Lúcia")

# vida própria: cada pessoa circula entre lugares que fazem sentido para ela
# (tile x, tile y, espera mínima, espera máxima em segundos)
NPC_ROUTES = {
    "cida": dict(speed=13, stops=[(58, 41, 14, 26), (49, 17, 12, 20), (47, 61, 8, 14), (60, 35, 10, 18), (22, 45, 8, 14)]),
    "tavares": dict(speed=15, stops=[(62, 39, 12, 22), (59, 17, 14, 24), (41, 58, 8, 14), (66, 34, 8, 14), (36, 36, 6, 10)]),
    "zeca": dict(speed=16, stops=[(16, 40, 14, 26), (22, 45, 10, 18), (54, 43, 8, 14), (18, 55, 10, 18), (17, 27, 10, 18)]),
    "lucia": dict(speed=15, stops=[(66, 16, 12, 20), (43, 17, 10, 16), (56, 36, 8, 14), (64, 68, 10, 18), (77, 40, 8, 12)]),
    "dom": dict(speed=12, stops=[(51, 16, 14, 24), (60, 35, 10, 16), (77, 40, 10, 18), (46, 17, 8, 14)]),
    "nelson": dict(speed=14, stops=[(50, 62, 12, 20), (95, 35, 12, 20), (47, 61, 8, 14), (62, 45, 10, 16), (50, 68, 8, 14)]),
    "osmar": dict(speed=12, stops=[(52, 32, 10, 18), (60, 41, 8, 14), (70, 18, 10, 16), (44, 23, 8, 14)]),
    "brandao": dict(speed=14, stops=[(55, 34, 10, 16), (36, 30, 8, 12), (70, 18, 8, 14), (77, 45, 8, 12)]),
    "tiao": dict(speed=26, stops=[(53, 39, 4, 8), (50, 67, 6, 12), (66, 66, 4, 8), (60, 18, 4, 8), (22, 33, 4, 8)]),
    "helen": dict(speed=12, stops=[(36, 38, 14, 24), (59, 16, 14, 22), (66, 42, 10, 16), (36, 37, 10, 16)]),
    "mario": dict(speed=14, stops=[(66, 42, 14, 22), (60, 18, 10, 16), (77, 40, 10, 16), (36, 37, 8, 14), (62, 45, 8, 14)]),
}

# ----------------------------------------------------------------------------
# Missões de campo: pegar itens, decifrar códigos e levar tudo aos lugares certos
# ----------------------------------------------------------------------------
ITEMS = {
    "panfletos": dict(nome="Panfletos", cor=(190, 120, 240)),
    "fita": dict(nome="Fita cassete", cor=(255, 190, 70)),
    "chave": dict(nome="Chave de ferro", cor=(150, 220, 255)),
    "lista": dict(nome="Lista de presos", cor=(255, 120, 130)),
    "negativos": dict(nome="Negativos censurados", cor=(120, 220, 160)),
    "diario": dict(nome="Diário do Preso", cor=(214, 160, 110)),
    "gravacao": dict(nome="Gravação do quartel", cor=(130, 180, 255)),
    "manifesto": dict(nome="Manifesto do Muro", cor=(255, 232, 120)),
}

CIFRA_TEXT = "ENTREGUE A DOM AURELIO ANTES DA MEIA NOITE"
COFRE_CODE = (1, 5, 0, 3)           # 15 de março (DDMM): a data que Dona Cida guarda

# k = flag (esperar um testemunho/conversa) | pickup (pegar item, com puzzle opcional)
#     | puzzle (puzzle num ponto do mapa) | deliver (levar item a uma pessoa ou lugar)
# As tiles abaixo são paradas já usadas pelos NPCs, então sempre são caminháveis.
MISSION_STEPS = [
    dict(id="mario", k="flag", flag="mario_ok", npc="mario", label="Prof. Mário",
         obj="Fale com o Professor Mário, o contato da rede"),
    dict(id="rota", k="flag", flag="rota_ok", npc="mario", label="Escolher a linha",
         obj="Volte ao Professor Mário e escolha sua linha de ação (sem volta!)"),
    dict(id="a_pick", k="pickup", item="panfletos", tile=(41, 58), puzzle="cifra", label="Panfletos",
         obj="Missão 1: pegue os panfletos na Feira Livre e decifre o bilhete",
         msg="Bilhete decifrado: os panfletos vão para Dom Aurélio.", fx=dict(evid=3)),
    dict(id="a_drop", k="deliver", item="panfletos", take="panfletos", npc="dom", label="Dom Aurélio",
         scene="a_dom", obj="Missão 1: leve os panfletos a Dom Aurélio", msg="Missão 1 cumprida! (+Cr$ 30)",
         fx=dict(cash=30)),
    dict(id="b_pick", k="pickup", item="fita", tile=(59, 17), puzzle="toques", label="Gaveta trancada",
         obj="Missão 2: abra a gaveta no Largo da Carioca (código de toques)",
         msg="Gaveta aberta: a fita proibida está com você.", fx=dict(evid=3)),
    dict(id="b_drop", k="deliver", item="fita", take="fita", tile=(36, 36), scene_npc="zeca",
         label="Estúdio do Zeca", scene="b_zeca",
         obj="Missão 2: leve a fita ao estúdio clandestino, na Av. Atlântica", msg="Missão 2 cumprida! (+Cr$ 30)",
         fx=dict(cash=30)),
    dict(id="c_cida", k="flag", flag="cida", npc="cida", label="Dona Cida",
         obj="Missão 3: ouça Dona Cida, ela guarda a pista do cofre"),
    dict(id="c_pick", k="pickup", item="chave", tile=(22, 45), label="Chave escondida",
         obj="Missão 3: pegue a chave escondida no Calçadão", msg="Chave de ferro no bolso."),
    dict(id="c_cofre", k="puzzle", tile=(49, 17), puzzle="cofre", take="chave", give="lista", label="Cofre",
         obj="Missão 3: abra o cofre da sacristia, no Largo da Carioca",
         msg="Cofre aberto! Você tem a lista dos presos. (+Cr$ 50)", after=("dom", "c_cofre"),
         fx=dict(evid=4, cash=50)),
    # --- Linha da Rádio (depois de b_pick e b_drop)
    dict(id="r_zeca", k="flag", flag="zeca", npc="zeca", label="Ouvir o Zeca",
         obj="Linha da Rádio: ouça o Zeca, o músico censurado"),
    dict(id="r_tavares", k="flag", flag="tavares", npc="tavares", label="Ouvir o Tavares",
         obj="Linha da Rádio: ouça o Tavares, o jornalista, para a rádio ter a história completa"),
    # --- Linha da Imprensa
    dict(id="i_tavares", k="flag", flag="tavares", npc="tavares", label="Ouvir o Tavares",
         obj="Linha da Imprensa: ouça o Tavares, o jornalista censurado"),
    dict(id="i_pick", k="pickup", item="negativos", tile=(59, 17), puzzle="toques", label="Gaveta do arquivo",
         obj="Linha da Imprensa: abra a gaveta do arquivo no Largo (código de toques)",
         msg="Negativos censurados no bolso.", fx=dict(evid=3)),
    dict(id="i_drop", k="deliver", item="negativos", take="negativos", npc="tavares", label="Entregar negativos",
         scene="i_tavares", obj="Linha da Imprensa: leve os negativos ao Tavares", msg="Negativos entregues! (+Cr$ 30)",
         fx=dict(cash=30)),
    dict(id="i_nelson", k="flag", flag="nelson", npc="nelson", label="Ouvir o Seu Nelson",
         obj="Linha da Imprensa: ouça o Seu Nelson, o operário que a greve calou"),
]
STEP_DEFS = {st_["id"]: st_ for st_ in MISSION_STEPS}

# Linhas de ação: ao confirmar com o Professor Mário, a escolha trava até o final.
ROUTES = {
    "igreja": dict(nome="Linha da Igreja", steps=["a_pick", "a_drop", "c_cida", "c_pick", "c_cofre"]),
    "radio": dict(nome="Linha da Rádio", steps=["b_pick", "b_drop", "r_zeca", "r_tavares"]),
    "imprensa": dict(nome="Linha da Imprensa", steps=["i_tavares", "i_pick", "i_drop", "i_nelson"]),
}


# ----------------------------------------------------------------------------
# Favelas novas, pixação "FORA DITADURA", varais, pôsteres de revolução e SEGREDOS
# ----------------------------------------------------------------------------
def _spray_text(text, scale, col, edge=(20, 10, 20)):
    """Texto de pixação: fonte 3x5 ampliada, com contorno escuro."""
    base = pygame.Surface((tiny_width(text) + 2, 7), pygame.SRCALPHA)
    draw_tiny(base, text, 1, 1, col, shadow=edge)
    return pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))


def pixacao_sprite(seed=0, big=False):
    """Muro pichado com FORA DITADURA (big = duas linhas; senão uma linha só)."""
    r = random.Random(seed * 17 + 5)
    wc, brick = ((186, 92, 84), True) if seed % 3 == 0 else (((170, 166, 182), False) if seed % 3 == 1 else ((96, 150, 206), False))
    col = (255, 244, 230) if sum(wc) < 520 else (240, 50, 50)
    lines = ("FORA", "DITADURA") if big else ("FORA DITADURA",)
    rend = [_spray_text(t, 2, col) for t in lines]
    w = max(x.get_width() for x in rend) + 14
    h = sum(x.get_height() for x in rend) + 4 * (len(rend) - 1) + 16
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(wc, -.5), (0, 3, w, h - 3))
    pygame.draw.rect(s, wc, (1, 4, w - 2, h - 6))
    pygame.draw.rect(s, tone(wc, .35), (0, 0, w, 4))
    pygame.draw.rect(s, tone(wc, -.2), (0, 3, w, 1))
    if brick:
        for yy in range(7, h - 2, 4):
            pygame.draw.line(s, tone(wc, -.25), (1, yy), (w - 2, yy))
            for xx in range(2 + (yy // 4 % 2) * 4, w - 2, 8):
                pygame.draw.line(s, tone(wc, -.25), (xx, yy), (xx, yy + 3))
    for _ in range(3):                                    # rebocos caídos
        pygame.draw.rect(s, tone(wc, -.3), (r.randrange(2, w - 10), r.randrange(6, h - 6), r.randint(3, 7), r.randint(2, 4)))
    y = 8
    for tx in rend:
        x0 = (w - tx.get_width()) // 2
        s.blit(tx, (x0, y))
        for _ in range(5):                                # escorridos de tinta
            dx = x0 + r.randrange(2, max(3, tx.get_width() - 2))
            pygame.draw.line(s, col, (dx, y + tx.get_height() - 2), (dx, y + tx.get_height() + r.randint(1, 4)))
        y += tx.get_height() + 4
    return s


FIST = (".#.#.#.", "#######", "#######", "#######", ".######", "..####.", "..####.", "...###.")


def rev_poster_sprite(seed=0):
    """Tapume de madeira com cartazes de revolução colados (punho erguido, estrela, palavra de ordem)."""
    r = random.Random(seed + 40)
    w, h = 40, 44
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (70, 46, 60), (0, 2, w, h - 2))
    for x in range(0, w, 6):
        pygame.draw.rect(s, (96, 66, 78), (x + 1, 3, 4, h - 5))
    pygame.draw.rect(s, (46, 30, 44), (0, h - 2, w, 2))
    schemes = (((214, 52, 60), (255, 236, 150), "POVO"), ((26, 26, 38), (255, 80, 70), "VIVA"),
               ((240, 200, 72), (44, 22, 30), "FORA"), ((236, 236, 226), (200, 36, 48), "RUA"))
    bg, fg, word = schemes[seed % 4]
    pygame.draw.rect(s, tone(bg, -.45), (4, 5, 32, 33))
    pygame.draw.rect(s, bg, (5, 6, 30, 31))
    pygame.draw.rect(s, tone(bg, .3), (5, 6, 30, 1))
    for ry, row in enumerate(FIST):
        for rx, v in enumerate(row):
            if v == "#":
                pygame.draw.rect(s, fg, (14 + rx * 2, 9 + ry * 2, 2, 2))
    draw_tiny(s, word, 5 + (30 - tiny_width(word)) // 2, 29, fg, shadow=tone(bg, -.5))
    pygame.draw.polygon(s, tone(bg, .5), [(35, 6), (35, 12), (29, 6)])          # canto dobrado
    for _ in range(4):
        pygame.draw.rect(s, tone(bg, -.2), (r.randrange(6, 33), r.randrange(8, 36), 2, 1))
    return s


def varal_sprite(seed=0):
    """Varal de roupas esticado entre dois postes (favela)."""
    r = random.Random(seed + 90)
    w, h = 46, 22
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.line(s, (96, 80, 90), (2, 3), (2, h - 1))
    pygame.draw.line(s, (96, 80, 90), (w - 3, 3), (w - 3, h - 1))
    pygame.draw.line(s, (60, 50, 70), (2, 4), (w - 3, 6))
    cols = ((236, 128, 110), (248, 208, 96), (96, 170, 214), (130, 200, 130), (240, 240, 226))
    for x in range(6, w - 6, 7):
        pygame.draw.rect(s, r.choice(cols), (x, 5 + x * 2 // w, 5, r.randint(5, 9)))
    return s


def chest_sprite(open_=False):
    s = pygame.Surface((18, 14), pygame.SRCALPHA)
    wood, band, gold = (122, 78, 52), (70, 50, 70), (255, 214, 90)
    pygame.draw.rect(s, tone(wood, -.4), (0, 5, 18, 9))
    pygame.draw.rect(s, wood, (1, 6, 16, 7))
    if open_:
        pygame.draw.rect(s, (40, 20, 30), (1, 6, 16, 3))
        pygame.draw.rect(s, tone(wood, .1), (1, 1, 16, 4))
        pygame.draw.rect(s, (255, 236, 160), (4, 6, 10, 2))
    else:
        pygame.draw.rect(s, tone(wood, .15), (0, 2, 18, 5))
        pygame.draw.rect(s, tone(wood, .4), (1, 2, 16, 1))
        pygame.draw.rect(s, band, (4, 2, 2, 11))
        pygame.draw.rect(s, band, (12, 2, 2, 11))
        pygame.draw.rect(s, gold, (8, 6, 3, 4))
    return s


# favelas novas (x, y da base em tiles): comunidade ao sul do campinho
FAVELA_NOVA = [(38.8, 64.6), (41.8, 65.0), (38.8, 68.6), (38.8, 72.6), (41.8, 73.0)]
PIXACOES = [(42.3, 68.6, True), (94.5, 85.0, True), (103.0, 85.0, False), (47.0, 61.6, False)]   # (x, y, duas linhas?)
VARAIS = [(40.3, 66.8), (98.0, 30.9), (98.0, 45.9), (98.0, 65.9), (93.0, 55.9), (103.0, 75.9), (95.0, 40.9), (101.0, 60.9)]
POSTER_SPOTS = [(86, 14), (86, 27), (86, 41), (86, 53), (83, 34), (46, 60), (60, 60), (73, 60),
                (36, 12), (36, 48), (36, 66)]

# SEGREDOS: difíceis de achar; exigem puzzles, enigmas ou uma ação específica
SECRET_CODE = (3, 1, 0, 3)           # 31/03: o dia do golpe de 1964 (DDMM)
SECRET_POSTERS = [((100, 30), 0), ((22, 33), 1), ((64, 68), 2), ((77, 40), 3)]   # (tile, posição do dígito)
ESCUTA_T = 6.0                       # segundos parado, segurando E, sem policial por perto
SECRETS = {
    "bau": dict(tile=(107, 80), item="diario", fx=dict(evid=8, cash=60),
                msg="O baú abriu: o Diário do Preso, com nomes, datas e rotas dos camburões. (+evidências, +Cr$ 60)"),
    "escuta": dict(tile=(36, 30), item="gravacao", fx=dict(evid=8, cash=40, susp=4),
                   msg="Gravação feita: o Coronel Brandão confirmando as ordens de prisão. (+evidências, +Cr$ 40)"),
    "enigma": dict(tile=(42, 69), item="manifesto", fx=dict(evid=8, cash=40, susp=-5),
                   msg="O muro revelou o Manifesto: a lista de quem resiste em cada bairro. (+evidências, +Cr$ 40)"),
}
ENIGMAS = [
    ("Tenho voz, mas não tenho boca. Passo de mão em mão e ninguém consegue me prender. O que sou?",
     ["Um panfleto", "Um cadeado", "Um relógio", "Um bonde"], 0),
    ("Quanto mais o censor me risca, mais gente quer me ler. O que sou?",
     ["A previsão do tempo", "A notícia proibida", "O preço do pão", "A lista de jogos"], 1),
    ("Em dezembro de 1968, qual ato institucional fechou ainda mais o regime e abriu os anos de chumbo?",
     ["AI-1", "AI-2", "AI-5", "AI-10"], 2),
]
RUMORS = {
    "bau": "Dizem que quatro cartazes da resistência, no morro, no calçadão, na beira da lagoa e no parque, "
           "têm números pintados à mão. Juntos abrem um baú no ponto mais alto do morro. Procure o brilho amarelo.",
    "escuta": "O poste da Avenida Atlântica, perto do ponto onde a polícia costuma parar, está grampeado pelos "
              "militares. Segure E, parado ao lado dele, e só quando nenhum policial estiver por perto.",
    "enigma": "Na comunidade ao sul do campinho, um muro pichado com FORA DITADURA guarda um enigma de três "
              "perguntas. Quem acertar tudo seguido leva um manifesto.",
}


def caesar(text, k):
    """Cifra de César: desloca só as letras A-Z."""
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


BUILDINGS = [("padaria", (24, 12), 11), ("acougue", (32, 11), 12), ("bar", (40, 14), 13),
             ("hotel", (43, 21), 14), ("farmacia", (22, 26), 15), ("sobrado", (31, 32), 16)]


# ----------------------------------------------------------------------------
# Jogo
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# MENU: praia de Copacabana em 2D (entardecer, carros passando, calçadão de ondas)
# ----------------------------------------------------------------------------
CS_W, CS_H = 640, 360     # resolução interna da cena (ampliada 2x na tela)
CS_HZ = 138               # linha do horizonte
CS_SHORE = 204            # linha d'água (média)
CS_SAND_END = 258         # fim da areia / começo do calçadão
CS_PROM_END = 282         # fim do calçadão
CS_ROAD0 = 282            # começo do asfalto (logo após o calçadão)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _grad(s, rect, c0, c1):
    x, y, w, h = rect
    for i in range(h):
        pygame.draw.line(s, _lerp(c0, c1, i / float(max(1, h - 1))), (x, y + i), (x + w - 1, y + i))


def _cs_glow(col, rad, power=2.0):
    s = pygame.Surface((rad * 2, rad * 2))
    s.fill((0, 0, 0))
    for rr in range(rad, 0, -1):
        k = (1 - rr / float(rad)) ** power
        pygame.draw.circle(s, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (rad, rad), rr)
    return s


def _cs_wheel(s, cx, cy, r, ang):
    """Roda girando: pneu, calota clara e raios que rodam com o carro."""
    pygame.draw.circle(s, (24, 12, 34), (cx, cy), r)
    pygame.draw.circle(s, (62, 56, 72), (cx, cy), max(1, r - 1))
    hub = max(1, r - 2)
    pygame.draw.circle(s, (208, 208, 220), (cx, cy), hub)
    if hub >= 2:
        for i in range(3):
            a = ang + i * 2.0944
            pygame.draw.line(s, (108, 106, 126), (cx, cy), (int(cx + math.cos(a) * hub), int(cy + math.sin(a) * hub)), 1)
    s.set_at((cx, cy), (70, 68, 86))


def _cs_car(kind, col, k, facing_right):
    """Carro de perfil dos anos 70 (sem as rodas, que são animadas). Retorna (Surface, rodas, raio)."""
    base = {"fusca": (40, 22), "kombi": (42, 26), "opala": (52, 22), "onibus": (74, 32), "corcel": (48, 21)}
    bw, bh = base[kind]
    w, h = int(bw * k) + 4, int(bh * k) + 4
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    ol = (30, 16, 40)
    glass = (146, 196, 226)
    shine = (228, 246, 254)
    dark = tone(col, -0.42)
    lite = tone(col, 0.38)

    def P(pts):
        return [(int(2 + x * k), int(2 + y * k)) for x, y in pts]

    def poly(pts, c, outline=True):
        q = P(pts)
        pygame.draw.polygon(s, c, q)
        if outline:
            pygame.draw.polygon(s, ol, q, 1)

    def rect(x, y, ww, hh, c):
        pygame.draw.rect(s, c, (int(2 + x * k), int(2 + y * k), max(1, int(ww * k)), max(1, int(hh * k))))

    def line(x0, y0, x1, y1, c):
        pygame.draw.line(s, c, (int(2 + x0 * k), int(2 + y0 * k)), (int(2 + x1 * k), int(2 + y1 * k)), 1)

    if kind == "fusca":
        poly([(1, 17), (1, 13), (5, 11), (10, 9), (14, 4), (22, 2), (29, 4), (33, 9), (38, 11), (39, 14), (39, 17)], col)
        poly([(14, 8), (16, 5), (22, 3.5), (27, 5), (30, 8)], glass)
        line(22, 4, 22, 8, ol)
        line(16.5, 7.5, 19, 4.8, shine)
        line(3, 12, 37, 12, lite)
        rect(2, 14.5, 36, 2, dark)
        line(19, 9, 19, 15, dark)
        rect(20, 11, 2, 1, lite)
        rect(37, 12, 2, 2, (255, 240, 180))
        rect(1, 12, 2, 2, (232, 60, 60))
        rect(0, 16, 40, 2, (196, 196, 208))
        wheels, wy, wr = [9, 30], 18, 5
    elif kind == "kombi":
        poly([(1, 20), (1, 6), (4, 3), (36, 3), (40, 9), (41, 20)], col)
        poly([(1, 11), (41, 11), (41, 20), (1, 20)], (242, 236, 222))
        line(1, 11, 41, 11, ol)
        for gx in (5, 13, 21, 29):
            rect(gx, 4.5, 6.5, 5, glass)
            line(gx + 1, 8.5, gx + 3, 5.5, shine)
        poly([(33, 4.5), (38, 4.5), (40, 9), (33, 9)], glass, False)
        line(14, 11, 14, 19, (176, 170, 160))
        line(30, 11, 30, 19, (176, 170, 160))
        rect(2, 18, 39, 2, (200, 194, 184))
        rect(40, 13, 2, 3, (255, 240, 180))
        rect(0, 13, 2, 3, (232, 60, 60))
        rect(18, 13, 5, 1.2, lite)
        line(2, 5, 40, 5, lite)
        wheels, wy, wr = [9, 33], 21, 5
    elif kind == "opala":
        poly([(1, 17), (1, 11), (6, 9), (14, 8), (19, 3), (33, 3), (38, 8), (48, 10), (51, 13), (51, 17)], col)
        poly([(20, 7.5), (22, 4.5), (31, 4.5), (35, 7.5)], glass)
        line(27, 4.5, 27, 7.5, ol)
        line(22, 7, 24.5, 4.8, shine)
        rect(2, 11, 48, 1, lite)
        rect(2, 14.5, 48, 2, dark)
        line(20, 8, 20, 15, dark)
        line(33, 8, 33, 15, dark)
        rect(22, 10, 2, 1, lite)
        rect(49, 11, 2, 2, (255, 240, 180))
        rect(0, 11, 2, 3, (232, 60, 60))
        rect(0, 16, 52, 2, (200, 200, 212))
        wheels, wy, wr = [11, 40], 18, 5
    elif kind == "corcel":
        poly([(1, 17), (1, 11), (5, 9), (14, 8), (20, 3), (32, 3), (37, 8), (45, 10), (47, 13), (47, 17)], col)
        poly([(21, 7.5), (23, 4.5), (31, 4.5), (34, 7.5)], glass)
        line(23, 7, 25.5, 4.8, shine)
        rect(2, 12, 44, 1, dark)
        rect(2, 14.5, 44, 2, dark)
        line(19, 8, 19, 15, dark)
        line(32, 8, 32, 15, dark)
        rect(45, 11, 2, 2, (255, 240, 180))
        rect(0, 11, 2, 3, (232, 60, 60))
        rect(0, 16, 48, 2, (200, 200, 212))
        wheels, wy, wr = [10, 37], 18, 5
    else:  # onibus
        poly([(1, 25), (1, 4), (4, 2), (68, 2), (73, 6), (73, 25)], col)
        poly([(1, 17), (73, 17), (73, 25), (1, 25)], (244, 238, 224))
        line(1, 17, 73, 17, ol)
        rect(1, 14.5, 72, 2, lite)
        for gx in range(5, 62, 9):
            rect(gx, 5, 7, 8, glass)
            line(gx + 1, 12, gx + 3.5, 6, shine)
        poly([(63, 5), (70, 5), (72, 11), (63, 11)], glass, False)
        line(62, 5, 62, 24, ol)
        rect(26, 3, 12, 2, (255, 196, 80))
        rect(1, 23, 72, 2, (200, 194, 184))
        rect(72, 19, 2, 3, (255, 240, 180))
        rect(0, 19, 2, 3, (232, 60, 60))
        wheels, wy, wr = [14, 58], 26, 5.5
    r = max(3, int(wr * k))
    pts = []
    for wx in wheels:
        cx, cy = int(2 + wx * k), int(2 + wy * k)
        pygame.draw.circle(s, ol, (cx, cy), r + 2)       # cava da roda
        pts.append((cx, cy))
    if not facing_right:
        s = pygame.transform.flip(s, True, False)
        pts = [(w - 1 - x, y) for x, y in pts]
    return s, pts, r


def _cs_person(shirt, pants, skin, hair, frame, kind="walk", shorts=True, hat=False, board=None):
    """Pessoa de perfil (olhando para a direita) com ciclo de 4 quadros: braços e pernas balançam."""
    s = pygame.Surface((13, 20), pygame.SRCALPHA)
    ol = (36, 20, 44)
    sw = (-1, 0, 1, 0)[frame % 4]
    bob = 1 if frame % 2 == 1 else 0
    top = 1 + bob
    skin_d = tone(skin, -0.28)
    foot = 18
    # braço de trás
    ax = 6 - sw * 2
    if kind == "jog":
        pygame.draw.rect(s, skin_d, (ax - 1, top + 6, 3, 2))
    else:
        pygame.draw.rect(s, skin_d, (ax, top + 5, 1, 5))
    # perna de trás e da frente
    hip = top + 11
    for lx, c_pant, c_skin in ((6 - sw * 2, tone(pants, -0.25), skin_d), (5 + sw * 2, pants, skin)):
        lh = foot - hip
        ph_ = 3 if shorts else lh
        pygame.draw.rect(s, c_pant, (lx, hip, 2, min(ph_, lh)))
        if ph_ < lh:
            pygame.draw.rect(s, c_skin, (lx, hip + ph_, 2, lh - ph_))
        pygame.draw.rect(s, (60, 40, 70), (lx, foot - 1, 3, 1))
    # tronco
    pygame.draw.rect(s, shirt, (4, top + 5, 5, 6))
    pygame.draw.rect(s, tone(shirt, 0.3), (4, top + 5, 1, 6))
    pygame.draw.rect(s, tone(shirt, -0.3), (8, top + 5, 1, 6))
    pygame.draw.rect(s, pants, (4, top + 10, 5, 1))
    # braço da frente
    ax = 6 + sw * 2
    if kind == "jog":
        pygame.draw.rect(s, skin, (ax, top + 6, 3, 2))
        pygame.draw.rect(s, skin, (ax + 2, top + 4, 1, 3))
    else:
        pygame.draw.rect(s, skin, (ax, top + 5, 1, 5))
    # cabeça
    pygame.draw.rect(s, skin, (4, top, 5, 5))
    pygame.draw.rect(s, hair, (4, top - 1, 5, 2))
    pygame.draw.rect(s, hair, (4, top, 1, 3))
    s.set_at((7, top + 2), ol)
    if hat:
        pygame.draw.rect(s, (248, 218, 112), (2, top - 1, 9, 1))
        pygame.draw.rect(s, (224, 172, 70), (4, top - 2, 5, 1))
    if board:
        pygame.draw.rect(s, ol, (10, top, 3, 17))
        pygame.draw.rect(s, board, (10, top + 1, 2, 15))
        pygame.draw.rect(s, (255, 255, 255), (10, top + 4, 2, 1))
    return s


def _cs_dog(frame):
    s = pygame.Surface((12, 9), pygame.SRCALPHA)
    fur, dk, ol = (204, 142, 84), (136, 88, 54), (36, 20, 44)
    pygame.draw.rect(s, fur, (2, 2, 7, 3))
    pygame.draw.rect(s, fur, (8, 0, 3, 3))
    pygame.draw.rect(s, dk, (8, 0, 1, 2))
    pygame.draw.rect(s, (240, 214, 170), (3, 4, 5, 1))
    s.set_at((10, 1), ol)
    s.set_at((11, 2), ol)
    pygame.draw.line(s, fur, (2, 2), (0, 0 if frame == 0 else 1))
    if frame == 0:
        pygame.draw.rect(s, dk, (8, 5, 1, 3))
        pygame.draw.rect(s, dk, (10, 5, 1, 2))
        pygame.draw.rect(s, dk, (2, 5, 1, 2))
        pygame.draw.rect(s, dk, (0, 5, 1, 3))
    else:
        pygame.draw.rect(s, dk, (7, 5, 1, 3))
        pygame.draw.rect(s, dk, (9, 5, 1, 3))
        pygame.draw.rect(s, dk, (3, 5, 1, 3))
        pygame.draw.rect(s, dk, (5, 5, 1, 3))
    return s


def _cs_beam(k):
    """Feixe de luz dos faróis (aponta para a direita)."""
    w, h = int(64 * k), int(18 * k)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        half = 1.5 + (h / 2.0 - 1.5) * (x / float(w))
        a = int(96 * (1 - x / float(w)) ** 1.4)
        pygame.draw.line(s, (255, 232, 170, a), (x, int(h / 2 - half)), (x, int(h / 2 + half)))
    return s



class CopaScene:
    """Cena 2D de abertura: Copacabana ao entardecer."""

    def __init__(self):
        self.t = 0.0
        self.surf = pygame.Surface((CS_W, CS_H)).convert()
        self.rnd = random.Random(1970)
        self.build_sky()
        self.build_far()
        self.build_beach()
        self.build_promenade()
        self.build_road()
        self.build_fx()
        # nuvens
        self.clouds = []
        for i in range(7):
            self.clouds.append(dict(x=self.rnd.uniform(0, CS_W), y=self.rnd.uniform(10, 92),
                                    v=self.rnd.uniform(1.5, 4.5), spr=self.make_cloud(self.rnd.randint(70, 150))))
        # gaivotas
        self.birds = [dict(x=self.rnd.uniform(0, CS_W), y=self.rnd.uniform(30, 110),
                           v=self.rnd.uniform(14, 26), ph=self.rnd.uniform(0, 6)) for _ in range(6)]
        # pessoas (4 quadros de caminhada; alguns correm, outros levam prancha)
        self.walkers = []
        pal = [((230, 70, 70), (50, 70, 140)), ((250, 200, 60), (40, 40, 60)), ((70, 170, 200), (240, 240, 240)),
               ((240, 120, 170), (60, 90, 160)), ((90, 190, 110), (230, 220, 200)), ((250, 250, 250), (200, 60, 60)),
               ((250, 140, 50), (40, 60, 120)), ((160, 90, 200), (60, 60, 70))]
        skins = [(246, 206, 170), (214, 154, 112), (160, 104, 72), (110, 70, 50)]
        hairs = [(40, 26, 20), (90, 54, 30), (20, 16, 20), (200, 160, 80)]
        boards = [(255, 214, 80), (80, 200, 230), (255, 110, 150)]
        for i in range(13):
            sh, pa = pal[i % len(pal)]
            sk, hr = self.rnd.choice(skins), self.rnd.choice(hairs)
            on_prom = i < 8
            if on_prom:
                kind = "jog" if i % 3 == 0 else "walk"
                y = self.rnd.randint(CS_SAND_END + 4, CS_PROM_END - 2)
                v = self.rnd.uniform(26, 36) if kind == "jog" else self.rnd.uniform(9, 15)
                fps = 9.0 if kind == "jog" else 5.0
            else:
                kind = "board" if i % 2 == 0 else "walk"
                y = self.rnd.randint(CS_SHORE + 8, CS_SHORE + 14)
                v = self.rnd.uniform(5, 8)
                fps = 4.0
            hat = (not on_prom) and self.rnd.random() < 0.5
            bd = self.rnd.choice(boards) if kind == "board" else None
            frames = [_cs_person(sh, pa, sk, hr, f, kind, shorts=True, hat=hat, board=bd) for f in range(4)]
            self.walkers.append(dict(x=self.rnd.uniform(0, CS_W), y=y, d=self.rnd.choice((-1, 1)), v=v,
                                     fps=fps, ph=self.rnd.uniform(0, 4), f=frames))
        self.walkers.sort(key=lambda w: w["y"])
        self.dog = dict(x=140.0, y=CS_SHORE + 17, d=1, f=[_cs_dog(0), _cs_dog(1)])
        self.kid = _cs_person((255, 120, 150), (60, 90, 160), (246, 206, 170), (90, 54, 30), 1, "walk", True, False)
        self.vb = [_cs_person((250, 200, 60), (230, 70, 70), (214, 154, 112), (40, 26, 20), 1, "walk", True, False),
                   _cs_person((70, 170, 200), (240, 240, 240), (246, 206, 170), (200, 160, 80), 1, "walk", True, False)]
        self.sparks = [(int(self.rnd.uniform(0, CS_W)), int(self.rnd.uniform(CS_HZ + 3, CS_SHORE - 9)),
                        self.rnd.uniform(0, 6.28)) for _ in range(90)]
        self.puffs = []
        self.lane_y = {0: CS_ROAD0 + 34, 1: CS_H - 9}
        # carros
        self.kinds = ["fusca", "kombi", "opala", "corcel", "onibus", "fusca"]
        self.colors = [(222, 74, 70), (70, 150, 210), (244, 196, 60), (90, 180, 120), (240, 240, 232),
                       (230, 130, 60), (160, 90, 190), (60, 60, 80), (240, 120, 160), (40, 150, 150)]
        self.cache = {}
        self.cars = []
        for lane in (0, 1):
            x = self.rnd.uniform(-60, 120)
            while x < CS_W + 60:
                self.cars.append(self.new_car(lane, x))
                x += self.rnd.uniform(130, 260)
        self.cars.sort(key=lambda c: c["lane"])

    # ------------------------------------------------------------------ construção
    def make_cloud(self, w):
        h = max(14, w // 4)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        r = random.Random(w * 7)
        for _ in range(w // 6):
            cx = r.randint(h // 2, w - h // 2)
            cy = r.randint(h // 3, h - h // 3)
            rad = r.randint(h // 4, h // 2)
            pygame.draw.ellipse(s, (255, 214, 190, 170), (cx - rad * 2, cy - rad, rad * 4, rad * 2))
        for _ in range(w // 8):
            cx = r.randint(h // 2, w - h // 2)
            cy = r.randint(h // 2, h - 3)
            rad = r.randint(h // 5, h // 3)
            pygame.draw.ellipse(s, (232, 110, 140, 140), (cx - rad * 2, cy - rad // 2, rad * 4, rad))
        for _ in range(w // 10):
            cx = r.randint(h // 2, w - h // 2)
            cy = r.randint(2, h // 2)
            rad = r.randint(h // 6, h // 4)
            pygame.draw.ellipse(s, (255, 244, 220, 190), (cx - rad * 2, cy - rad // 2, rad * 4, rad))
        return s

    def build_sky(self):
        s = pygame.Surface((CS_W, CS_HZ + 4))
        stops = [(0.0, (30, 34, 104)), (0.30, (92, 58, 142)), (0.55, (190, 86, 148)),
                 (0.78, (252, 130, 120)), (0.92, (255, 184, 118)), (1.0, (255, 220, 150))]
        for y in range(CS_HZ + 4):
            t = y / float(CS_HZ + 3)
            for i in range(len(stops) - 1):
                if stops[i][0] <= t <= stops[i + 1][0]:
                    u = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                    c = _lerp(stops[i][1], stops[i + 1][1], u)
                    break
            pygame.draw.line(s, c, (0, y), (CS_W, y))
        # estrelas
        r = random.Random(3)
        for _ in range(60):
            x, y = r.randrange(CS_W), r.randrange(0, 56)
            a = r.choice((120, 170, 220))
            s.set_at((x, y), (a, a, min(255, a + 20)))
        # sol
        sx, sy = 468, 128
        g = _cs_glow((255, 150, 90), 150, 2.2)
        s.blit(g, (sx - 150, sy - 150), special_flags=pygame.BLEND_RGB_ADD)
        g2 = _cs_glow((255, 220, 150), 64, 1.6)
        s.blit(g2, (sx - 64, sy - 64), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (255, 214, 130), (sx, sy), 20)
        pygame.draw.circle(s, (255, 240, 190), (sx, sy), 16)
        pygame.draw.circle(s, (255, 252, 226), (sx - 2, sy - 2), 9)
        self.sky = s
        self.sun = (sx, sy)

    def mountain(self, s, pts, col, hi, rim):
        pygame.draw.polygon(s, col, pts)
        # luz do poente: contorno do lado direito mais claro
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            if y1 > y0 and x1 > x0 and y0 < CS_HZ - 2:
                pygame.draw.line(s, rim, (x0, y0), (x1, y1), 1)
        return s

    def build_far(self):
        s = pygame.Surface((CS_W, CS_HZ + 2), pygame.SRCALPHA)
        hz = CS_HZ
        haze = (214, 120, 150)
        rim = (255, 170, 130)
        # morros distantes atrás (Dois Irmãos / Gávea) à direita
        self.mountain(s, [(520, hz), (540, 96), (556, 84), (566, 90), (578, 70), (590, 76), (604, 92), (640, 100), (640, hz)],
                      (126, 74, 140), None, rim)
        # Pão de Açúcar ao fundo, à esquerda
        pts = [(52, hz), (60, 110), (74, 82), (94, 70), (116, 72), (132, 86), (142, 106), (150, hz)]
        self.mountain(s, pts, (110, 62, 126), None, rim)
        for i in range(0, 38, 3):                      # faixa de luz no lado do sol
            pygame.draw.line(s, (190, 96, 140), (128 - i // 6, 80 + i), (132 + i // 7, 86 + i), 1)
        # bondinho (cabo até o Morro da Urca)
        pygame.draw.line(s, (60, 30, 70), (30, 108), (112, 72), 1)
        # Morro da Urca
        self.mountain(s, [(0, hz), (0, 110), (14, 104), (30, 106), (44, 116), (56, hz)], (96, 54, 112), None, rim)
        # Forte de Copacabana e a pedra do Arpoador
        pygame.draw.polygon(s, (74, 44, 86), [(0, hz), (0, 126), (30, 128), (52, 134), (66, hz)])
        pygame.draw.rect(s, (230, 190, 170), (14, 121, 18, 6))
        pygame.draw.rect(s, (200, 150, 140), (14, 121, 18, 1))
        for bx in range(15, 32, 3):
            pygame.draw.rect(s, (160, 100, 110), (bx, 119, 2, 2))
        # Morro do Leme (verde) e linha de prédios da orla
        self.mountain(s, [(430, hz), (452, 124), (480, 114), (510, 104), (540, 100), (576, 106), (610, 116), (640, 120), (640, hz)],
                      (62, 78, 104), None, rim)
        pygame.draw.polygon(s, (50, 66, 92), [(500, hz), (530, 112), (560, 108), (600, 116), (640, 124), (640, hz)])
        r = random.Random(11)
        x = 392
        while x < 640:
            w = r.randint(5, 9)
            hh = r.randint(8, 24) if x < 520 else r.randint(14, 34)
            top = hz - hh
            pygame.draw.rect(s, (74, 62, 104), (x, top, w, hh))
            pygame.draw.rect(s, (110, 86, 130), (x + w - 1, top, 1, hh))
            for wy in range(top + 2, hz - 2, 3):
                for wx in range(x + 1, x + w - 1, 2):
                    if r.random() < 0.38:
                        s.set_at((wx, wy), (255, 214, 130))
            x += w + r.randint(0, 2)
        # ilhas Cagarras
        for ix, iw, ih in ((290, 16, 5), (312, 10, 4), (330, 20, 6)):
            pygame.draw.ellipse(s, (120, 72, 128), (ix, hz - ih, iw, ih * 2))
        # névoa no horizonte (suaviza tudo que está longe)
        for i in range(34):
            a = int(120 * (1 - i / 34.0) ** 1.6)
            pygame.draw.line(s, (255, 190, 150, a), (0, hz - i), (CS_W, hz - i))
        self.far = s
        # veleiro
        self.boats = [dict(x=250, y=hz + 14, v=1.2, kind="veleiro"), dict(x=130, y=hz + 30, v=-0.8, kind="barco")]

    def build_beach(self):
        # base do mar (gradiente) + areia
        s = pygame.Surface((CS_W, CS_SAND_END - CS_HZ + 4))
        sea0, sea1 = (250, 160, 138), (24, 104, 150)
        sea_h = CS_SHORE - 8 - CS_HZ
        for y in range(sea_h):
            t = y / float(sea_h - 1)
            pygame.draw.line(s, _lerp(sea0, sea1, t ** 0.8), (0, y), (CS_W, y))
        # areia
        sand0, sand1 = (246, 206, 160), (226, 170, 132)
        top = sea_h
        for y in range(top, s.get_height()):
            t = (y - top) / float(max(1, s.get_height() - top))
            pygame.draw.line(s, _lerp(sand0, sand1, t), (0, y), (CS_W, y))
        r = random.Random(9)
        for _ in range(900):
            x, y = r.randrange(CS_W), r.randrange(top, s.get_height())
            c = r.choice(((255, 226, 186), (206, 150, 118), (236, 190, 146)))
            s.set_at((x, y), c)
        self.sea_sand = s
        # elementos de praia (desenhados uma vez, de trás para frente)
        b = pygame.Surface((CS_W, CS_H), pygame.SRCALPHA)
        r = random.Random(77)
        # posto salva-vidas
        self.lifeguard(b, 372, CS_SHORE + 30)
        # rede de vôlei
        self.volley(b, 168, CS_SHORE + 36)
        # guarda-sóis e toalhas (ordenados por y)
        items = []
        cols = [((232, 60, 70), (250, 240, 230)), ((250, 190, 50), (250, 240, 230)), ((60, 150, 220), (250, 240, 230)),
                ((60, 190, 130), (250, 240, 230)), ((240, 110, 170), (250, 240, 230)), ((250, 140, 50), (250, 240, 230)),
                ((140, 90, 200), (250, 240, 230))]
        for i in range(17):
            x = 30 + i * 36 + r.randint(-12, 12)
            y = r.randint(CS_SHORE + 22, CS_SAND_END - 8)
            if 150 < x < 200 or 340 < x < 410:
                continue
            items.append((y, x, cols[i % len(cols)]))
        items.sort()
        for y, x, (c1, c2) in items:
            self.umbrella(b, x, y, c1, c2, r)
        # barracas coloridas (mais perto da areia)
        self.beach_flags = [(60, CS_SAND_END - 22, (255, 210, 60)), (300, CS_SAND_END - 20, (240, 80, 120)),
                            (560, CS_SAND_END - 24, (80, 190, 230))]
        self.beach = b

    def umbrella(self, b, x, y, c1, c2, r):
        # sombra
        sh = pygame.Surface((30, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (90, 40, 70, 90), (0, 0, 30, 6))
        b.blit(sh, (x - 14, y - 2))
        # toalha
        tc = r.choice(((250, 240, 230), (255, 120, 150), (110, 200, 240), (255, 220, 100)))
        pygame.draw.rect(b, tc, (x - 11, y - 1, 12, 5))
        pygame.draw.rect(b, (60, 36, 70), (x - 11, y - 1, 12, 5), 1)
        # pessoa deitada
        pygame.draw.rect(b, (216, 150, 110), (x - 9, y, 4, 2))
        pygame.draw.rect(b, r.choice(((230, 70, 70), (70, 120, 220), (250, 200, 60))), (x - 5, y, 5, 2))
        # haste
        pygame.draw.line(b, (90, 60, 60), (x + 4, y + 2), (x + 4, y - 28), 1)
        # copa listrada
        for i in range(-12, 13):
            h = int(10 * (1 - (i / 12.5) ** 2))
            col = c1 if ((i + 12) // 4) % 2 == 0 else c2
            pygame.draw.line(b, col, (x + 4 + i, y - 27 + (10 - h)), (x + 4 + i, y - 18), 1)
        pygame.draw.line(b, (50, 24, 56), (x + 4 - 12, y - 17), (x + 4 + 12, y - 17), 1)
        pygame.draw.circle(b, (255, 250, 230), (x + 4, y - 29), 1)

    def lifeguard(self, b, x, y):
        pygame.draw.rect(b, (110, 70, 70), (x - 14, y - 10, 2, 12))
        pygame.draw.rect(b, (110, 70, 70), (x + 12, y - 10, 2, 12))
        pygame.draw.rect(b, (250, 240, 230), (x - 16, y - 24, 32, 14))
        pygame.draw.rect(b, (230, 60, 60), (x - 16, y - 20, 32, 4))
        pygame.draw.rect(b, (40, 24, 50), (x - 16, y - 24, 32, 14), 1)
        pygame.draw.rect(b, (150, 200, 230), (x - 12, y - 22, 8, 7))
        pygame.draw.rect(b, (230, 60, 60), (x - 18, y - 28, 36, 5))
        pygame.draw.rect(b, (40, 24, 50), (x - 18, y - 28, 36, 5), 1)
        pygame.draw.line(b, (110, 70, 70), (x + 18, y - 28), (x + 18, y - 40), 1)
        pygame.draw.rect(b, (255, 210, 60), (x + 18, y - 40, 7, 4))
        pygame.draw.rect(b, (110, 70, 70), (x - 6, y - 10, 12, 2))
        for i in range(5):
            pygame.draw.line(b, (110, 70, 70), (x - 8 + i * 4, y - 8), (x - 8 + i * 4, y), 1)

    def volley(self, b, x, y):
        for px in (x, x + 46):
            pygame.draw.line(b, (110, 70, 70), (px, y), (px, y - 22), 2)
        for i in range(6):
            pygame.draw.line(b, (250, 244, 234), (x, y - 20 + i * 2), (x + 46, y - 20 + i * 2), 1)
        for i in range(0, 47, 3):
            pygame.draw.line(b, (250, 244, 234), (x + i, y - 20), (x + i, y - 9), 1)
        pygame.draw.rect(b, (250, 244, 234), (x, y - 21, 46, 1))
        pygame.draw.circle(b, (255, 210, 60), (x + 30, y - 34), 2)
        pygame.draw.circle(b, (40, 24, 50), (x + 30, y - 34), 2, 1)

    def build_promenade(self):
        # calçadão de Copacabana: ondas pretas e brancas
        h = CS_PROM_END - CS_SAND_END
        s = pygame.Surface((CS_W, h))
        white, black = (238, 228, 216), (58, 44, 66)
        for y in range(h):
            for x in range(CS_W):
                v = math.sin(x * 0.075 + (y // 6) * 0.9) * 2.4 + y * 0.5
                col = white if int(v + 100) % 4 < 2 else black
                s.set_at((x, y), col)
        # meio-fio claro
        pygame.draw.rect(s, (250, 242, 228), (0, 0, CS_W, 1))
        pygame.draw.rect(s, (200, 150, 140), (0, h - 2, CS_W, 2))
        # sombreado de luz quente
        warm = pygame.Surface((CS_W, h), pygame.SRCALPHA)
        for y in range(h):
            pygame.draw.line(warm, (255, 140, 100, 34 + y), (0, y), (CS_W, y))
        s.blit(warm, (0, 0))
        self.prom = s

    def build_road(self):
        h = CS_H - CS_ROAD0
        s = pygame.Surface((CS_W, h))
        _grad(s, (0, 0, CS_W, h), (92, 72, 104), (46, 36, 64))
        r = random.Random(5)
        for _ in range(500):
            x, y = r.randrange(CS_W), r.randrange(h)
            c = r.choice(((104, 84, 116), (70, 54, 86), (60, 46, 78)))
            s.set_at((x, y), c)
        # calçada oposta (faixa clara embaixo) e meio-fio
        pygame.draw.rect(s, (214, 168, 150), (0, 0, CS_W, 3))
        pygame.draw.rect(s, (150, 106, 118), (0, 3, CS_W, 2))
        # linha amarela dupla e faixas tracejadas
        mid = 40
        pygame.draw.rect(s, (244, 196, 60), (0, mid, CS_W, 1))
        pygame.draw.rect(s, (244, 196, 60), (0, mid + 3, CS_W, 1))
        for x in range(0, CS_W, 40):
            pygame.draw.rect(s, (232, 224, 214), (x, 20, 22, 1))
            pygame.draw.rect(s, (232, 224, 214), (x + 12, 62, 22, 1))
        # reflexos do poente no asfalto
        refl = pygame.Surface((CS_W, h), pygame.SRCALPHA)
        for y in range(h):
            a = int(60 * (1 - y / float(h)))
            pygame.draw.line(refl, (255, 150, 110, a), (0, y), (CS_W, y))
        s.blit(refl, (0, 0))
        self.road = s

    def build_fx(self):
        self.lamp_glow = _cs_glow((255, 190, 100), 46, 2.0)
        self.head_glow = _cs_glow((255, 224, 150), 30, 1.8)
        self.tail_glow = _cs_glow((220, 40, 40), 14, 1.8)
        self.sun_glows = [_cs_glow((206, 92, 56), 130, 2.4), _cs_glow((232, 106, 64), 130, 2.4),
                          _cs_glow((255, 122, 74), 130, 2.4)]
        self.lamp_dim = _cs_glow((150, 110, 60), 46, 2.0)
        self.beams = {(0, True): _cs_beam(1.0), (1, True): _cs_beam(1.4)}
        self.beams[(0, False)] = pygame.transform.flip(self.beams[(0, True)], True, False)
        self.beams[(1, False)] = pygame.transform.flip(self.beams[(1, True)], True, False)
        v = pygame.Surface((CS_W, CS_H), pygame.SRCALPHA)
        # vinheta barata: bordas escurecidas
        for i in range(48):
            a = int(120 * (1 - i / 48.0) ** 2.2)
            pygame.draw.rect(v, (20, 6, 40, a), (i, i, CS_W - 2 * i, CS_H - 2 * i), 1)
        self.vig = v
        # palmeiras imperiais (base x, altura, inclinação)
        self.palms = [dict(x=34, h=118, lean=-6, ph=0.0), dict(x=214, h=100, lean=4, ph=1.7),
                      dict(x=372, h=112, lean=-3, ph=3.1), dict(x=538, h=104, lean=5, ph=4.4),
                      dict(x=618, h=124, lean=-5, ph=5.6)]
        self.lamps = [120, 292, 452, 584]

    def new_car(self, lane, x):
        r = self.rnd
        kind = r.choice(self.kinds)
        col = r.choice(self.colors)
        if kind == "onibus":
            col = r.choice(((60, 120, 210), (220, 70, 60), (60, 160, 100), (250, 170, 40)))
        k = 1.0 if lane == 0 else 1.4
        right = (lane == 0)
        key = (kind, col, k, right)
        if key not in self.cache:
            self.cache[key] = _cs_car(kind, col, k, right)
        spr, wheels, wr = self.cache[key]
        spd = r.uniform(34, 62) if lane == 0 else r.uniform(46, 84)
        return dict(lane=lane, x=x, spr=spr, wheels=wheels, wr=wr, v=spd if right else -spd, kind=kind,
                    ph=r.uniform(0, 6.28), puff=r.uniform(0, 0.3), wang=r.uniform(0, 6.28))

    # ------------------------------------------------------------------ atualização
    def update(self, dt):
        self.t += dt
        for c in self.clouds:
            c["x"] += c["v"] * dt
            if c["x"] > CS_W + 10:
                c["x"] = -c["spr"].get_width() - 10
        for b in self.birds:
            b["x"] += b["v"] * dt
            if b["x"] > CS_W + 10:
                b["x"] = -12
                b["y"] = self.rnd.uniform(30, 110)
        for b in self.boats:
            b["x"] += b["v"] * dt
            if b["x"] > CS_W + 30:
                b["x"] = -30
            elif b["x"] < -30:
                b["x"] = CS_W + 30
        for w in self.walkers:
            w["x"] += w["d"] * w["v"] * dt
            if w["x"] > CS_W + 8:
                w["x"] = -8
            elif w["x"] < -8:
                w["x"] = CS_W + 8
        dg = self.dog
        dg["x"] += dg["d"] * 36 * dt
        if dg["x"] > CS_W - 14:
            dg["d"] = -1
        elif dg["x"] < 14:
            dg["d"] = 1
        for c in self.cars:
            c["x"] += c["v"] * dt
            c["wang"] += c["v"] * dt / float(c["wr"])
            c["puff"] -= dt
            w = c["spr"].get_width()
            if c["puff"] <= 0 and len(self.puffs) < 48:
                c["puff"] = self.rnd.uniform(0.16, 0.3)
                k = 1.0 if c["lane"] == 0 else 1.4
                rx = c["x"] + (2 if c["v"] > 0 else w - 2)
                self.puffs.append(dict(x=rx, y=self.lane_y[c["lane"]] - 3 * k, age=0.0, life=self.rnd.uniform(0.7, 1.1),
                                       dx=(-1 if c["v"] > 0 else 1) * self.rnd.uniform(4, 10), k=k))
            if c["v"] > 0 and c["x"] > CS_W + 30:
                self.respawn(c, True)
            elif c["v"] < 0 and c["x"] < -w - 30:
                self.respawn(c, False)
        for p in self.puffs:
            p["age"] += dt
            p["x"] += p["dx"] * dt
            p["y"] -= 7 * dt
        self.puffs = [p for p in self.puffs if p["age"] < p["life"]]

    def respawn(self, c, right):
        # mantém espaçamento: nasce atrás do carro mais recuado da mesma faixa
        same = [o for o in self.cars if o["lane"] == c["lane"] and o is not c]
        gap = self.rnd.uniform(120, 300)
        if right:
            start = min([o["x"] for o in same] + [0]) - gap
            start = min(start, -90 - self.rnd.uniform(0, 120))
        else:
            start = max([o["x"] + o["spr"].get_width() for o in same] + [CS_W]) + gap
            start = max(start, CS_W + 40 + self.rnd.uniform(0, 120))
        n = self.new_car(c["lane"], start)
        c.update(n)

    # ------------------------------------------------------------------ desenho
    def draw_palm(self, s, p):
        t = self.t
        bx, by = p["x"], CS_PROM_END - 1
        gust = max(0.0, math.sin(t * 0.45 + p["ph"] * 0.3)) ** 3 * 0.10
        top = (bx + p["lean"] + gust * 26, by - p["h"])
        # base alargada
        pygame.draw.polygon(s, (92, 68, 78), [(bx - 5, by), (bx + 5, by), (bx + 3, by - 7), (bx - 3, by - 7)])
        # tronco curvo com anéis e brilho do poente
        n = 24
        prev = None
        for i in range(n + 1):
            u = i / float(n)
            x = bx + (top[0] - bx) * u + math.sin(u * 3.0) * 2 + (u ** 2) * gust * 14
            y = by + (top[1] - by) * u
            wdt = 4.4 - 2.4 * u
            if prev:
                pygame.draw.line(s, (84, 62, 74), prev, (int(x), int(y)), int(wdt) + 1)
                pygame.draw.line(s, (186, 150, 134), (prev[0] + 1, prev[1]), (int(x) + 1, int(y)), 1)
            if i % 2 == 0:
                pygame.draw.line(s, (58, 40, 54), (int(x) - 2, int(y)), (int(x) + 2, int(y)), 1)
            prev = (int(x), int(y))
        cx, cy = prev
        pygame.draw.rect(s, (112, 156, 84), (cx - 2, cy - 1, 4, 8))
        pygame.draw.rect(s, (74, 118, 66), (cx - 2, cy + 5, 4, 2))
        # cacho de cocos
        for ox, oy in ((-3, 8), (2, 9), (0, 10), (-1, 7)):
            pygame.draw.circle(s, (112, 76, 52), (cx + ox, cy + oy), 2)
            s.set_at((cx + ox - 1, cy + oy - 1), (190, 144, 96))
        sway = math.sin(t * 1.3 + p["ph"]) * 0.10 + gust
        for i in range(11):
            ang = (-math.pi + 0.15) + i * ((math.pi - 0.3) / 10.0)
            ang += sway + math.sin(t * 2.1 + i + p["ph"]) * 0.035
            ln = 36 + 6 * math.sin(i * 1.7)
            pts = []
            for j in range(9):
                u = j / 8.0
                dx = math.cos(ang) * ln * u
                dy = math.sin(ang) * ln * u * 0.9 + (u ** 2) * (22 + 12 * abs(math.cos(ang)))
                pts.append((cx + dx, cy - 3 + dy))
            col = (34, 108, 78) if i % 2 == 0 else (46, 134, 88)
            hi = (96, 170, 96)
            for j in range(len(pts) - 1):
                wdt = 3 if j < 4 else 2
                pygame.draw.line(s, (18, 62, 52), pts[j], pts[j + 1], wdt + 1)
                pygame.draw.line(s, col, pts[j], pts[j + 1], wdt)
            # folíolos dos dois lados da nervura
            for j in range(1, 8):
                (x0, y0), (x1, y1) = pts[j], pts[j + 1]
                ddx, ddy = x1 - x0, y1 - y0
                nrm = math.hypot(ddx, ddy) or 1.0
                px_, py_ = -ddy / nrm, ddx / nrm
                L = 5.0 * (1 - j / 10.0)
                flutter = math.sin(t * 3.0 + j + i) * 0.8
                for sgn in (1, -1):
                    ex = x0 + px_ * L * sgn + ddx / nrm * 1.5
                    ey = y0 + py_ * L * sgn + 2.2 + flutter
                    pygame.draw.line(s, col if sgn > 0 else (28, 92, 70), (x0, y0), (ex, ey), 1)
            if math.sin(ang) < -0.2:
                pygame.draw.line(s, hi, pts[2], pts[5], 1)

    def draw_lamp(self, s, x):
        by = CS_PROM_END
        pygame.draw.rect(s, (40, 28, 52), (x - 1, by - 52, 3, 52))
        pygame.draw.rect(s, (40, 28, 52), (x - 5, by - 54, 11, 3))
        pygame.draw.rect(s, (255, 224, 150), (x - 4, by - 51, 9, 2))
        pygame.draw.rect(s, (30, 20, 40), (x - 3, by - 3, 7, 3))
        pygame.draw.line(s, (92, 70, 100), (x, by - 50), (x, by - 4), 1)

    def draw_boat(self, s, b):
        t = self.t
        bob = int(math.sin(t * 1.5 + b["x"] * 0.05) * 1)
        x, y = int(b["x"]), b["y"] + bob
        flut = int(math.sin(t * 3 + x * 0.1) * 1)
        d = 1 if b["v"] > 0 else -1
        # esteira
        for i in range(1, 5):
            pygame.draw.line(s, (255, 220, 190), (x - d * (8 + i * 4), y + 4 + i // 2),
                             (x - d * (11 + i * 4), y + 4 + i // 2), 1)
        if b["kind"] == "veleiro":
            pygame.draw.polygon(s, (255, 226, 196), [(x, y - 17), (x, y - 1), (x + 9 + flut, y - 1)])
            pygame.draw.polygon(s, (240, 164, 150), [(x - 1, y - 14), (x - 1, y - 1), (x - 8 - flut, y - 1)])
            pygame.draw.polygon(s, (250, 240, 232), [(x - 9, y), (x + 9, y), (x + 6, y + 3), (x - 6, y + 3)])
            pygame.draw.line(s, (60, 30, 70), (x - 9, y + 3), (x + 9, y + 3), 1)
            pygame.draw.line(s, (70, 40, 80), (x, y - 17), (x, y), 1)
        else:
            pygame.draw.polygon(s, (74, 40, 80), [(x - 8, y), (x + 8, y), (x + 5, y + 3), (x - 5, y + 3)])
            pygame.draw.rect(s, (250, 200, 160), (x - 2, y - 4, 5, 4))
            pygame.draw.line(s, (60, 30, 70), (x + 1, y - 4), (x + 1, y - 9), 1)
            pygame.draw.rect(s, (255, 240, 180), (x + 3, y - 3, 1, 1))
        pygame.draw.line(s, (255, 190, 140), (x - 6, y + 5), (x + 6, y + 5), 1)

    def draw_kite(self, s):
        t = self.t
        kx = 96 + math.sin(t * 0.9) * 10
        ky = 50 + math.sin(t * 1.3) * 5
        hx, hy = 115, CS_SHORE + 12
        # linha com barriga
        prev = (hx, hy)
        for i in range(1, 13):
            u = i / 12.0
            x = hx + (kx - hx) * u + math.sin(u * 3.14 + t) * 3 * (1 - u)
            y = hy + (ky - hy) * u + math.sin(u * 3.14) * 6
            pygame.draw.line(s, (255, 236, 220), prev, (x, y), 1)
            prev = (x, y)
        # cauda
        tx, ty = kx, ky + 9
        for i in range(9):
            nx = kx + math.sin(t * 4 + i * 0.9) * (2 + i * 0.4) - i * 0.6
            ny = ky + 9 + i * 3
            pygame.draw.line(s, (255, 236, 220), (tx, ty), (nx, ny), 1)
            pygame.draw.rect(s, (255, 90, 120) if i % 2 == 0 else (255, 214, 80), (int(nx) - 1, int(ny), 3, 2))
            tx, ty = nx, ny
        # pipa
        tilt = math.sin(t * 1.3) * 2
        pts = [(kx, ky - 9), (kx + 6, ky + tilt), (kx, ky + 9), (kx - 6, ky - tilt)]
        pygame.draw.polygon(s, (255, 90, 120), pts)
        pygame.draw.polygon(s, (255, 214, 80), [pts[0], pts[1], (kx, ky)])
        pygame.draw.polygon(s, (80, 190, 230), [pts[2], pts[3], (kx, ky)])
        pygame.draw.polygon(s, (40, 20, 50), pts, 1)

    def draw_sand_extras(self, s):
        t = self.t
        # soltador de pipa
        s.blit(self.kid, (112 - 6, CS_SHORE + 26 - 18))
        # vôlei: dois jogadores e uma bola que vai e volta
        gy = CS_SHORE + 38
        p = t % 4.8
        jl = 5 * max(0.0, 1 - min(p, 4.8 - p) / 0.35)
        jr = 5 * max(0.0, 1 - abs(p - 2.4) / 0.35)
        for px, jump, fl, spr in ((158, jl, False, self.vb[0]), (226, jr, True, self.vb[1])):
            sh = pygame.Surface((11, 3), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (60, 20, 50, 100), (0, 0, 11, 3))
            s.blit(sh, (px - 5, gy - 1))
            img = pygame.transform.flip(spr, True, False) if fl else spr
            s.blit(img, (px - 6, gy - 18 - int(jump)))
        if p < 2.4:
            u = p / 2.4
            bx = 166 + 54 * u
        else:
            u = (p - 2.4) / 2.4
            bx = 220 - 54 * u
        by = gy - 16 - 38 * math.sin(math.pi * u)
        sh = pygame.Surface((7, 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (60, 20, 50, 90), (0, 0, 7, 2))
        s.blit(sh, (int(bx) - 3, gy))
        pygame.draw.circle(s, (40, 24, 50), (int(bx), int(by)), 3)
        pygame.draw.circle(s, (255, 238, 130), (int(bx), int(by)), 2)
        s.set_at((int(bx), int(by)), (240, 140, 60))
        # cachorro correndo na beira da água
        dg = self.dog
        fr = dg["f"][int(t * 10) % 2]
        if dg["d"] < 0:
            fr = pygame.transform.flip(fr, True, False)
        sh = pygame.Surface((12, 3), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (60, 20, 50, 90), (0, 0, 12, 3))
        s.blit(sh, (int(dg["x"]) - 6, dg["y"] - 1))
        s.blit(fr, (int(dg["x"]) - 6, dg["y"] - 8 - int(abs(math.sin(t * 10)) * 1.2)))

    def draw(self):
        s = self.surf
        t = self.t
        s.blit(self.sky, (0, 0))
        for c in self.clouds:
            s.blit(c["spr"], (int(c["x"]), int(c["y"])))
        # gaivotas batendo asa
        for b in self.birds:
            fl = math.sin(t * 8 + b["ph"])
            x, y = int(b["x"]), int(b["y"] + math.sin(t * 0.8 + b["ph"]) * 3)
            wy = int(fl * 3)
            col = (70, 36, 80)
            pygame.draw.lines(s, col, False, [(x - 6, y - wy), (x - 3, y - wy // 2 - 1), (x, y)], 1)
            pygame.draw.lines(s, col, False, [(x, y), (x + 3, y - wy // 2 - 1), (x + 6, y - wy)], 1)
            s.set_at((x, y + 1), col)
        s.blit(self.far, (0, 0))
        # bondinho do Pão de Açúcar (duas cabines em sentidos opostos)
        for u in (0.5 + 0.5 * math.sin(t * 0.2), 0.5 - 0.5 * math.sin(t * 0.2)):
            cx, cy = 30 + 82 * u, 108 - 36 * u
            pygame.draw.line(s, (60, 30, 70), (cx, cy), (cx, cy + 3), 1)
            pygame.draw.rect(s, (232, 60, 60), (int(cx) - 3, int(cy) + 3, 6, 4))
            pygame.draw.rect(s, (255, 232, 160), (int(cx) - 2, int(cy) + 4, 4, 1))
        s.blit(self.sea_sand, (0, CS_HZ))
        # reflexo do sol no mar (colunas de brilho)
        sx = self.sun[0]
        for y in range(CS_HZ + 2, CS_SHORE + 4, 2):
            u = (y - CS_HZ) / float(CS_SHORE - CS_HZ)
            wd = 6 + u * 54
            for k in range(int(3 + u * 6)):
                ph = t * (1.6 + k * 0.3) + y * 0.5 + k * 2.1
                ox = math.sin(ph) * wd * 0.5 + math.sin(y * 0.37 + k) * wd * 0.35
                ln = 3 + int(abs(math.sin(ph * 0.7)) * (4 + u * 12))
                col = _lerp((255, 232, 170), (255, 170, 110), min(1.0, u))
                pygame.draw.line(s, col, (sx + ox - ln, y), (sx + ox + ln, y), 1)
        # ondas do mar (linhas claras que sobem e crescem)
        for i in range(34):
            u = ((i / 34.0) + t * 0.035) % 1.0
            y = CS_HZ + 4 + int(u * u * (CS_SHORE - CS_HZ - 12))
            x0 = int((i * 97 + t * (4 + u * 10)) % (CS_W + 80)) - 40
            ln = 8 + int(u * 40)
            col = _lerp((255, 200, 170), (210, 240, 246), u)
            pygame.draw.line(s, col, (x0, y), (x0 + ln, y), 1)
        # brilhos que piscam na água
        for x, y, ph in self.sparks:
            v = math.sin(t * 3.0 + ph)
            if v > 0.86:
                pygame.draw.line(s, (255, 252, 236), (x - 1, y), (x + 1, y), 1)
                s.set_at((int(x), int(y) - 1), (255, 240, 210))
                s.set_at((int(x), int(y) + 1), (255, 240, 210))
            elif v > 0.62:
                s.set_at((int(x), int(y)), (255, 236, 200))
        for b in self.boats:
            self.draw_boat(s, b)
        # água rasa + espuma na beira (ondas vão e vêm)
        for x in range(0, CS_W, 2):
            y1 = CS_SHORE + int(math.sin(x * 0.045 + t * 1.1) * 3 + math.sin(x * 0.11 - t * 0.7) * 1.5 + math.sin(t * 0.6) * 3)
            y1 = max(CS_SHORE - 6, y1)
            top = CS_SHORE - 8
            pygame.draw.line(s, (36, 116, 156), (x, top), (x, y1 - 5), 2)
            pygame.draw.line(s, (92, 176, 190), (x, y1 - 5), (x, y1 - 2), 2)
            pygame.draw.line(s, (214, 242, 242), (x, y1 - 2), (x, y1), 2)
            pygame.draw.line(s, (255, 252, 244), (x, y1), (x + 1, y1), 1)
            pygame.draw.line(s, (196, 140, 116), (x, y1 + 1), (x + 1, y1 + 3), 2)
        s.blit(self.beach, (0, 0))
        self.draw_kite(s)
        for fx, fy, fc in self.beach_flags:
            pygame.draw.line(s, (90, 60, 60), (fx, fy), (fx, fy - 14), 1)
            for i in range(6):
                pygame.draw.line(s, fc, (fx + i, fy - 14 + int(math.sin(t * 5 + i * 0.7) * 1)),
                                 (fx + i, fy - 11 + int(math.sin(t * 5 + i * 0.7) * 1)), 1)
        # pessoas: as da areia antes do calçadão, as do calçadão depois
        for on_prom in (False, True):
            if on_prom:
                s.blit(self.prom, (0, CS_SAND_END))
            for w in self.walkers:
                if (w["y"] >= CS_SAND_END) != on_prom:
                    continue
                fi = int(t * w["fps"] + w["ph"]) % 4
                fr = w["f"][fi]
                if w["d"] < 0:
                    fr = pygame.transform.flip(fr, True, False)
                sh = pygame.Surface((10, 3), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (30, 10, 50, 90), (0, 0, 10, 3))
                s.blit(sh, (int(w["x"]) - 4, w["y"] - 1))
                s.blit(fr, (int(w["x"]) - 6, w["y"] - 18))
            if not on_prom:
                self.draw_sand_extras(s)
        for lx in self.lamps:
            self.draw_lamp(s, lx)
        for p in self.palms:
            self.draw_palm(s, p)
        s.blit(self.road, (0, CS_ROAD0))
        # carros: faixa de trás (lane 0) primeiro
        for lane in (0, 1):
            k = 1.0 if lane == 0 else 1.4
            for c in self.cars:
                if c["lane"] != lane:
                    continue
                spr = c["spr"]
                bounce = int(abs(math.sin(t * 16 + c["ph"])) * 1.3)
                x = int(c["x"])
                y = self.lane_y[lane] - spr.get_height() + 4 - bounce
                sh = pygame.Surface((spr.get_width(), 6), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (14, 6, 30, 120), (2, 0, spr.get_width() - 4, 6))
                s.blit(sh, (x, self.lane_y[lane] - 4))
                fwd = 1 if c["v"] > 0 else -1
                hx = x + (spr.get_width() - 3 if fwd > 0 else 3)
                hy = y + spr.get_height() - int(9 * k)
                beam = self.beams[(lane, fwd > 0)]
                s.blit(beam, (hx if fwd > 0 else hx - beam.get_width(), hy - beam.get_height() // 2))
                s.blit(spr, (x, y))
                for wx, wy in c["wheels"]:
                    _cs_wheel(s, x + wx, y + wy, c["wr"], c["wang"])
                s.blit(self.head_glow, (hx - 30 + fwd * 14, hy - 30), special_flags=pygame.BLEND_RGB_ADD)
                tx = x + (3 if fwd > 0 else spr.get_width() - 3)
                s.blit(self.tail_glow, (tx - 14, hy - 14), special_flags=pygame.BLEND_RGB_ADD)
        # fumaça dos escapamentos
        for p in self.puffs:
            u = p["age"] / p["life"]
            rad = int((2 + u * 6) * p["k"])
            a = int(110 * (1 - u))
            pf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(pf, (216, 196, 206, a), (rad + 1, rad + 1), rad)
            s.blit(pf, (int(p["x"]) - rad, int(p["y"]) - rad))
        # luz dos postes (um deles pisca de leve) e brilho do sol pulsando
        for i, lx in enumerate(self.lamps):
            g = self.lamp_glow
            if i == 2 and math.sin(t * 37.0) * math.sin(t * 9.0) > 0.88:
                g = self.lamp_dim
            s.blit(g, (lx - 46, CS_PROM_END - 52 - 46), special_flags=pygame.BLEND_RGB_ADD)
        gi = max(0, min(2, int(1.5 + 1.4 * math.sin(t * 0.9))))
        s.blit(self.sun_glows[gi], (self.sun[0] - 130, self.sun[1] - 130 + 20), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(self.vig, (0, 0))
        return s


# ----------------------------------------------------------------------------
# CASA DO AGENTE ROSSO: porta no mapa + interior (mural de provas, cofrinho, cama)
# ----------------------------------------------------------------------------
HOME_TILE = (41, 36)            # centro x e linha da base da casa no mapa (em tiles)
HOME_DOOR = (HOME_TILE[0] * TS, HOME_TILE[1] * TS + 6)     # onde o agente fica para entrar (px)
SLEEP_COST = 60                 # dormir gasta 1 minuto do prazo da Central...
SLEEP_SUSP = 30                 # ...mas baixa a suspeita do regime
BRIBE_COST = 50                 # propina para o censor ou o coronel (tecla P)
BRIBE_SUSP = 20
START_BANK = 120                # dinheiro guardado em casa no começo (Cr$)
ROOM_X0, ROOM_X1, ROOM_Y0, ROOM_Y1 = 14, 306, 92, 172      # onde o agente anda dentro de casa
# (id, x, y do ponto de uso, raio, rótulo) em pixels internos 320x180
HOME_SPOTS = (("porta", 27, 98, 22, "Sair"),
              ("mural", 124, 98, 34, "Mural de provas"),
              ("cama", 270, 120, 30, "Cama"))
SHORT = dict(cida="Cida", tavares="Tavares", zeca="Zeca", lucia="Lúcia", dom="Dom Aurélio", nelson="Seu Nelson")
TOPICS = dict(cida="Desaparecimentos forçados", tavares="Censura à imprensa", zeca="Censura às artes",
              lucia="Repressão estudantil", dom="Tortura e perseguição", nelson="Arrocho e greves")
MANCHETES = [
    "Jornal da manhã: 'Brasil cresce como nunca!' Três colunas da página 4 estão cobertas por tarjas pretas.",
    "O rádio só toca marchas e jogo da seleção. Ninguém fala dos sumidos.",
    "Um vizinho some da escada do prédio. Ninguém viu. Ninguém ouviu.",
    "Um panfleto embaixo da porta: 'Quem cala consente.' Alguém da rede passou por aqui.",
    "Chuva fina no Rio. A Central avisa que a linha segue segura por mais um dia.",
]


def casa_sprite():
    """Casinha rosa do Agente Rosso: telhado de barro, chaminé, placa e aldrava de porquinho."""
    r = random.Random(99)
    w, h = 96, 96
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    lights = []
    wall, roofc = (236, 152, 172), (150, 84, 100)
    pygame.draw.rect(s, (60, 46, 70), (66, 0, 14, 14))              # chaminé
    brick_wall(s, (67, 2, 12, 12), (170, 90, 80), r, 5, 3)
    pygame.draw.rect(s, (60, 46, 70), (65, 0, 16, 2))
    pygame.draw.rect(s, tone(roofc, -.5), (0, 10, w, 20))           # telhado
    roof_tiles(s, (1, 10, w - 2, 18), roofc, r)
    pygame.draw.rect(s, tone(roofc, .35), (1, 10, w - 2, 1))
    pygame.draw.rect(s, tone(roofc, -.55), (0, 27, w, 3))
    brick_wall(s, (3, 30, w - 6, h - 30), wall, r)                  # parede
    overlay(s, (w - 14, 30, 11, h - 30), (50, 20, 90, 60))
    overlay(s, (3, 30, w - 6, 3), (40, 10, 70, 70))
    pygame.draw.rect(s, tone(wall, .35), (2, 31, w - 4, 2))
    pygame.draw.rect(s, tone(wall, -.6), (2, h - 4, w - 4, 4))
    for wx in (9, 71):                                              # janelas acesas
        window(s, wx, 42, 14, 17, True, r, curtain=(120, 70, 140), flowers=True)
        lights.append((wx + 7, 50, 24, (112, 66, 20), 0))
    pygame.draw.rect(s, (30, 22, 56), (33, 38, 30, 11))             # placa ROSSO
    pygame.draw.rect(s, (250, 206, 84), (33, 38, 30, 11), 1)
    draw_tiny(s, "ROSSO", 48 - tiny_width("ROSSO") // 2, 41, (255, 226, 130))
    lights.append((48, 44, 24, (110, 70, 20), 1))
    door(s, 38, 56, 20, h - 60, (90, 56, 120))                      # porta
    pygame.draw.circle(s, (250, 170, 188), (48, 77), 3)             # aldrava de porquinho
    s.set_at((47, 77), (110, 54, 84))
    s.set_at((49, 77), (110, 54, 84))
    pygame.draw.rect(s, (60, 54, 70), (63, 60, 2, 3))               # lampião ao lado da porta
    pygame.draw.rect(s, (255, 226, 140), (62, 63, 4, 5))
    lights.append((64, 65, 22, (130, 90, 30), 0))
    pygame.draw.rect(s, (176, 164, 176), (34, h - 5, 28, 5))        # degrau
    pygame.draw.rect(s, (214, 204, 214), (34, h - 5, 28, 1))
    return outlined(s), [(lx + 1, ly + 1, lr, lc, lf) for lx, ly, lr, lc, lf in lights]


def home_room_surfaces():
    """Interior da casa (320x180): devolve (fundo estático, moldura/cortinas da janela)."""
    r = random.Random(5)
    s = pygame.Surface((IW, IH))
    WALL = 84
    for x in range(IW):                                             # papel de parede listrado
        pygame.draw.line(s, (100, 72, 126) if (x // 8) % 2 == 0 else (90, 64, 116), (x, 0), (x, WALL))
    for yy in range(8, 56, 16):
        for xx in range(4, IW, 16):
            pygame.draw.polygon(s, (118, 88, 142), [(xx, yy - 3), (xx + 3, yy), (xx, yy + 3), (xx - 3, yy)])
    for i in range(10):
        overlay(s, (0, i, IW, 1), (20, 8, 36, 90 - i * 9))
    pygame.draw.rect(s, (84, 50, 62), (0, 62, IW, 20))              # rodapé de madeira
    for x in range(6, IW, 24):
        pygame.draw.rect(s, (70, 40, 52), (x, 66, 18, 12), 1)
    pygame.draw.rect(s, (170, 120, 96), (0, 61, IW, 2))
    pygame.draw.rect(s, (58, 34, 44), (0, 81, IW, 4))
    for y in range(WALL + 1, IH, 10):                               # assoalho
        row = (y - WALL) // 10
        for x0 in range(-((row * 17) % 40), IW, 40):
            c = shade((176, 118, 80), (_hash(x0, row, 4) % 21) - 10)
            pygame.draw.rect(s, c, (x0, y, 40, 10))
            pygame.draw.rect(s, tone(c, .14), (x0, y, 40, 1))
            pygame.draw.rect(s, tone(c, -.35), (x0, y + 9, 40, 1))
            pygame.draw.rect(s, tone(c, -.35), (x0 + 39, y, 1, 10))
    overlay(s, (0, WALL + 1, IW, 6), (40, 16, 50, 70))
    # tapete
    rx, ry, rw, rh = 96, 126, 128, 42
    pygame.draw.rect(s, (60, 22, 40), (rx - 2, ry - 2, rw + 4, rh + 4))
    pygame.draw.rect(s, (160, 52, 74), (rx, ry, rw, rh))
    pygame.draw.rect(s, (240, 200, 120), (rx + 4, ry + 4, rw - 8, rh - 8), 1)
    for k in range(rx + 10, rx + rw - 12, 12):
        cy_ = ry + rh // 2
        pygame.draw.polygon(s, (240, 200, 120), [(k, cy_), (k + 5, cy_ - 5), (k + 10, cy_), (k + 5, cy_ + 5)])
        pygame.draw.circle(s, (250, 232, 180), (k + 5, cy_), 1)
    for k in range(rx, rx + rw, 4):
        pygame.draw.line(s, (240, 220, 190), (k, ry - 3), (k, ry - 1))
        pygame.draw.line(s, (240, 220, 190), (k, ry + rh), (k, ry + rh + 2))
    # porta de saída
    pygame.draw.rect(s, (46, 26, 36), (10, 22, 36, 62))
    pygame.draw.rect(s, (112, 72, 64), (13, 25, 30, 58))
    pygame.draw.rect(s, (150, 104, 92), (13, 25, 2, 58))
    pygame.draw.rect(s, (60, 40, 50), (17, 29, 22, 18))
    pygame.draw.rect(s, (255, 214, 130), (19, 31, 18, 14))
    pygame.draw.rect(s, (60, 40, 50), (27, 31, 2, 14))
    pygame.draw.rect(s, (88, 54, 54), (17, 52, 22, 26), 1)
    pygame.draw.circle(s, (250, 210, 90), (39, 60), 2)
    pygame.draw.rect(s, (30, 22, 56), (14, 11, 28, 9))
    pygame.draw.rect(s, (250, 206, 84), (14, 11, 28, 9), 1)
    draw_tiny(s, "SAIDA", 28 - tiny_width("SAIDA") // 2, 13, (255, 226, 130))
    pygame.draw.rect(s, (60, 22, 40), (10, 88, 36, 7))
    pygame.draw.rect(s, (150, 56, 66), (12, 89, 32, 5))
    # cabide com sobretudo e chapéu
    pygame.draw.rect(s, (70, 50, 60), (58, 30, 2, 54))
    pygame.draw.rect(s, (70, 50, 60), (52, 82, 14, 2))
    coat = (176, 138, 96)
    pygame.draw.polygon(s, tone(coat, -.5), [(51, 40), (67, 40), (69, 74), (49, 74)])
    pygame.draw.polygon(s, coat, [(52, 41), (66, 41), (68, 73), (50, 73)])
    pygame.draw.rect(s, tone(coat, .3), (52, 41, 2, 32))
    pygame.draw.rect(s, tone(coat, -.3), (65, 41, 2, 32))
    pygame.draw.rect(s, tone(coat, -.5), (58, 41, 1, 32))
    pygame.draw.ellipse(s, (62, 46, 78), (50, 28, 18, 5))
    pygame.draw.rect(s, (62, 46, 78), (54, 22, 10, 8))
    pygame.draw.rect(s, (214, 62, 66), (54, 27, 10, 2))
    # mural de provas: moldura e cortiça
    pygame.draw.rect(s, (60, 36, 40), (72, 12, 104, 53))
    pygame.draw.rect(s, (110, 66, 50), (73, 13, 102, 51))
    pygame.draw.rect(s, (186, 138, 88), (75, 15, 98, 47))
    for _ in range(160):
        s.set_at((r.randrange(76, 172), r.randrange(16, 61)), r.choice(((150, 104, 64), (210, 164, 112), (170, 120, 76))))
    for i in range(6):
        x, y = 78 + (i % 3) * 32, 17 + (i // 3) * 23
        pygame.draw.rect(s, (150, 104, 64), (x, y, 28, 20), 1)
    pygame.draw.rect(s, (30, 22, 56), (106, 4, 36, 9))
    pygame.draw.rect(s, (250, 206, 84), (106, 4, 36, 9), 1)
    draw_tiny(s, "PROVAS", 124 - tiny_width("PROVAS") // 2, 6, (255, 226, 130))
    pygame.draw.rect(s, (60, 36, 40), (74, 79, 100, 4))             # prateleira
    pygame.draw.rect(s, (150, 100, 70), (74, 78, 100, 2))
    for bx in (80, 166):
        pygame.draw.rect(s, (60, 36, 40), (bx, 72, 3, 6))
    # janela (a vista e a moldura são desenhadas por cima)
    pygame.draw.rect(s, (60, 36, 48), (184, 16, 44, 44))
    pygame.draw.rect(s, (30, 20, 50), (187, 19, 38, 38))
    # cama
    bx, by = 236, 36
    pygame.draw.rect(s, (60, 36, 40), (bx - 2, by - 2, 72, 32))
    pygame.draw.rect(s, (104, 66, 62), (bx, by, 68, 28))
    for k in range(bx + 6, bx + 66, 10):
        pygame.draw.line(s, (84, 50, 52), (k, by + 2), (k, by + 26))
    pygame.draw.rect(s, (150, 104, 92), (bx, by, 68, 2))
    pygame.draw.rect(s, (60, 36, 40), (bx + 2, by + 26, 64, 36))    # colchão/lençol
    pygame.draw.rect(s, (240, 234, 226), (bx + 3, by + 27, 62, 34))
    pygame.draw.ellipse(s, (255, 250, 244), (bx + 8, by + 28, 28, 12))
    pygame.draw.ellipse(s, (214, 206, 206), (bx + 8, by + 36, 28, 4))
    pygame.draw.rect(s, (170, 58, 92), (bx + 3, by + 42, 62, 32))   # coberta
    pygame.draw.rect(s, (214, 96, 128), (bx + 3, by + 42, 62, 4))
    for k in range(bx + 8, bx + 64, 10):
        pygame.draw.line(s, (140, 40, 72), (k, by + 48), (k, by + 72))
    pygame.draw.rect(s, (60, 36, 40), (bx - 2, by + 62, 72, 14))    # pé da cama
    pygame.draw.rect(s, (104, 66, 62), (bx, by + 64, 68, 10))
    pygame.draw.rect(s, (150, 104, 92), (bx, by + 64, 68, 2))
    for lx in (bx, bx + 62):
        pygame.draw.rect(s, (60, 36, 40), (lx, by + 74, 6, 3))
    for lx in (bx - 2, bx + 66):                                    # pés da cabeceira
        pygame.draw.rect(s, (60, 36, 40), (lx, by - 2, 4, 40))
    # lâmpada pendurada
    pygame.draw.line(s, (40, 28, 52), (160, 0), (160, 10))
    pygame.draw.rect(s, (255, 226, 140), (156, 10, 8, 6))
    pygame.draw.rect(s, (255, 252, 220), (158, 11, 4, 3))
    # moldura da janela: cruz, peitoril e cortinas (camada transparente)
    ov = pygame.Surface((IW, IH), pygame.SRCALPHA)
    fr = (60, 36, 48)
    pygame.draw.rect(ov, fr, (184, 16, 44, 3))
    pygame.draw.rect(ov, fr, (184, 57, 44, 3))
    pygame.draw.rect(ov, fr, (184, 16, 3, 44))
    pygame.draw.rect(ov, fr, (225, 16, 3, 44))
    pygame.draw.rect(ov, fr, (205, 19, 2, 38))
    pygame.draw.rect(ov, fr, (187, 37, 38, 2))
    pygame.draw.rect(ov, (170, 120, 96), (181, 60, 50, 3))
    pygame.draw.rect(ov, (60, 36, 40), (181, 63, 50, 1))
    for cx0 in (187, 217):
        pygame.draw.rect(ov, (170, 70, 100), (cx0, 19, 8, 38))
        for k in range(cx0 + 2, cx0 + 8, 3):
            pygame.draw.line(ov, (130, 46, 76), (k, 19), (k, 56))
    return s, ov


def home_table_sprite():
    """Mesa com rádio e cofrinho de porquinho."""
    s = pygame.Surface((52, 34), pygame.SRCALPHA)
    wood = (150, 98, 70)
    pygame.draw.rect(s, tone(wood, -.4), (2, 14, 48, 7))
    pygame.draw.rect(s, wood, (2, 14, 48, 5))
    pygame.draw.rect(s, tone(wood, .3), (2, 14, 48, 1))
    for lx in (4, 44):
        pygame.draw.rect(s, tone(wood, -.35), (lx, 20, 4, 14))
        pygame.draw.rect(s, wood, (lx, 20, 3, 14))
    pygame.draw.rect(s, (60, 40, 40), (6, 3, 16, 11))               # rádio
    pygame.draw.rect(s, (200, 150, 90), (7, 4, 14, 9))
    pygame.draw.circle(s, (40, 30, 30), (11, 9), 3)
    pygame.draw.rect(s, (240, 230, 200), (16, 6, 4, 1))
    pygame.draw.rect(s, (250, 210, 90), (17, 9, 1, 3))
    pygame.draw.ellipse(s, (222, 124, 152), (28, 6, 14, 9))         # cofrinho
    pygame.draw.ellipse(s, (250, 170, 188), (28, 5, 13, 8))
    pygame.draw.rect(s, (250, 170, 188), (40, 8, 3, 3))
    pygame.draw.rect(s, (222, 124, 152), (30, 12, 2, 3))
    pygame.draw.rect(s, (222, 124, 152), (37, 12, 2, 3))
    pygame.draw.rect(s, (110, 54, 84), (32, 6, 5, 1))
    s.set_at((40, 7), (30, 14, 30))
    pygame.draw.circle(s, (250, 210, 90), (46, 12), 2)
    return s


def home_plant_sprite():
    s = pygame.Surface((22, 34), pygame.SRCALPHA)
    for ang, ln in ((-60, 14), (-30, 18), (0, 20), (30, 18), (60, 14), (-85, 9), (85, 9)):
        a = math.radians(ang)
        e = (11 + int(math.sin(a) * ln), 22 - int(math.cos(a) * ln * 0.9))
        pygame.draw.line(s, (40, 110, 80), (11, 22), e, 3)
        pygame.draw.line(s, (96, 176, 104), (11, 21), (e[0], e[1] - 1), 1)
    pygame.draw.rect(s, (110, 54, 48), (5, 22, 12, 12))
    pygame.draw.rect(s, (150, 76, 60), (5, 22, 11, 11))
    pygame.draw.rect(s, (200, 110, 84), (5, 22, 12, 2))
    return s


# ----------------------------------------------------------------------------
# INTERIORES 2D: casa do agente, padaria, açougue, bar (com o informante), hotel, farmácia e sobrado
# ----------------------------------------------------------------------------
INF_SIZE = (30, 46)            # canvas do informante (antes do contorno): bem maior e mais largo que os outros


def make_informante(d, f):
    """O Informante do bar: homem negro, muito musculoso, cabelo preto espetado e regata clara."""
    if d == "left":
        return pygame.transform.flip(make_informante("right", f), True, False)
    s = pygame.Surface(INF_SIZE, pygame.SRCALPHA)
    skin, sk_hi, sk_lo, sk_dp = (98, 62, 44), (146, 98, 68), (64, 38, 30), (42, 24, 22)
    hair, h_hi = (20, 16, 24), (74, 66, 90)
    tank, tank_lo, tank_hi = (230, 224, 208), (170, 160, 156), (252, 248, 238)
    jeans, jeans_lo = (50, 66, 116), (32, 42, 80)
    boot = (52, 34, 30)
    gold = (246, 200, 70)
    la = lb = aa = ab = 0
    if f == 1:
        la, aa, ab = -1, 1, -1
    elif f == 2:
        lb, aa, ab = -1, -1, 1
    side = d == "right"
    back = d == "up"

    def R(x, y, w, h, c):
        pygame.draw.rect(s, c, (x, y, w, h))

    def P(x, y, c):
        s.set_at((x, y), c)

    # ---- pernas (calça boca de sino) e botas
    for lx, off in ((8, la), (15, lb)):
        if side:
            lx = 10 if lx == 8 else 14
        R(lx, 34, 6, 5 + off, jeans)
        R(lx, 34, 1, 5 + off, tone(jeans, .22))
        R(lx + 5, 34, 1, 5 + off, jeans_lo)
        R(lx - 1, 39 + off, 8, 3, jeans)                      # boca de sino
        R(lx - 1, 39 + off, 1, 3, tone(jeans, .22))
        R(lx + 6, 39 + off, 1, 3, jeans_lo)
        R(lx - 1, 42 + off, 8, 2, boot)
        R(lx - 1, 42 + off, 8, 1, tone(boot, .3))
        R(lx - 1, 43 + off, 8, 1, tone(boot, -.4))
    # ---- cinto
    bx0, bw = (8, 14) if side else (7, 16)
    R(bx0, 32, bw, 3, (36, 24, 28))
    if not side and not back:
        R(13, 32, 4, 3, gold)
        R(14, 33, 2, 1, (120, 80, 20))
    # ---- tronco: V de ombros largos afunilando na cintura
    if side:
        pygame.draw.polygon(s, tank, [(8, 21), (21, 21), (20, 33), (9, 33)])
        R(8, 21, 2, 12, tank_hi)
        R(19, 22, 2, 11, tank_lo)
        R(9, 32, 11, 1, tank_lo)
        R(12, 21, 6, 3, skin)                                  # decote lateral
        R(14, 24, 4, 2, sk_lo)                                 # peitoral de lado
    elif back:
        pygame.draw.polygon(s, tank, [(5, 21), (24, 21), (21, 33), (8, 33)])
        R(5, 21, 2, 12, tank_hi)
        R(22, 22, 2, 11, tank_lo)
        R(14, 22, 1, 11, tank_lo)                              # costura
        R(8, 32, 14, 1, tank_lo)
        for yy in (24, 27, 30):                                # dorsais marcados
            R(9, yy, 4, 1, tank_lo)
            R(17, yy, 4, 1, tank_lo)
    else:
        pygame.draw.polygon(s, tank, [(5, 21), (24, 21), (21, 33), (8, 33)])
        R(5, 21, 2, 12, tank_hi)
        R(22, 22, 2, 11, tank_lo)
        R(8, 32, 14, 1, tank_lo)
        # decote em V mostrando o peitoral
        pygame.draw.polygon(s, skin, [(10, 21), (19, 21), (16, 28), (13, 28)])
        pygame.draw.polygon(s, sk_hi, [(10, 21), (13, 21), (13, 26), (11, 23)])
        R(14, 22, 1, 6, sk_lo)                                 # divisão dos peitorais
        R(11, 27, 3, 1, sk_lo)
        R(15, 27, 3, 1, sk_lo)
        # corrente dourada
        for gx, gy in ((11, 21), (12, 23), (13, 25), (14, 26), (15, 26), (16, 25), (17, 23), (18, 21)):
            P(gx, gy, gold)
        P(14, 27, (255, 236, 150))
        P(14, 28, gold)
        # gomos do abdômen sob a regata
        R(14, 29, 1, 3, tank_lo)
        R(11, 30, 3, 1, tank_lo)
        R(15, 30, 3, 1, tank_lo)
    # ---- pescoço grosso
    if not side:
        R(11, 17, 8, 4, skin if not back else sk_lo)
        R(11, 17, 8, 1, sk_lo)
        R(18, 18, 1, 3, sk_lo)
    else:
        R(11, 17, 7, 4, skin)
        R(11, 17, 7, 1, sk_lo)
    # ---- braços musculosos (ombro, bíceps, antebraço, punho)
    def arm(x, y, mirror_hi, swing):
        pygame.draw.ellipse(s, skin, (x - 1, y, 8, 7))                    # deltoide
        pygame.draw.ellipse(s, skin, (x, y + 3 + swing, 7, 10))           # bíceps
        R(x + 1, y + 11 + swing, 5, 6, skin)                              # antebraço
        pygame.draw.ellipse(s, skin, (x + 1, y + 16 + swing, 5, 5))      # punho
        R(x + 1, y + 19 + swing, 5, 1, sk_lo)
        # luz e sombra para dar volume
        hx = x + 1 if mirror_hi else x + 4
        R(hx, y + 3 + swing, 1, 5, sk_hi)
        R(hx, y + 1, 3, 1, sk_hi)
        R(hx, y + 2, 2, 1, sk_hi)
        sx = x + 5 if mirror_hi else x + 1
        R(sx, y + 6 + swing, 1, 5, sk_lo)
        R(sx, y + 12 + swing, 1, 4, sk_lo)
        P(x + 3, y + 10 + swing, sk_dp)                                   # dobra do cotovelo
        R(x + 1, y + 15 + swing, 5, 1, sk_dp)                             # pulseira de couro
        P(x + 2, y + 15 + swing, (150, 100, 50))
    if side:
        arm(10, 21, True, ab)
    else:
        arm(0, 21, True, aa)
        arm(22, 21, False, ab)
    # ---- cabeça
    if side:
        pygame.draw.ellipse(s, skin, (8, 6, 11, 13))
        R(9, 13, 9, 5, skin)
        R(17, 11, 3, 3, skin)                                  # nariz
        P(19, 12, sk_hi)
        R(9, 10, 5, 1, hair)                                   # sobrancelha
        R(15, 10, 3, 1, hair)
        P(16, 11, (250, 244, 236))
        P(17, 11, (20, 12, 16))
        R(14, 17, 4, 1, sk_lo)                                 # queixo forte
        R(16, 15, 3, 1, sk_dp)                                 # boca
        R(8, 11, 2, 3, sk_lo)                                  # orelha
        P(9, 12, sk_dp)
        R(9, 17, 8, 1, sk_lo)
    elif back:
        pygame.draw.ellipse(s, skin, (8, 6, 13, 13))
        R(9, 13, 11, 5, skin)
        R(7, 11, 2, 3, sk_lo)
        R(20, 11, 2, 3, sk_lo)
        R(9, 17, 11, 1, sk_lo)
    else:
        pygame.draw.ellipse(s, skin, (8, 6, 13, 13))
        R(9, 13, 11, 5, skin)                                  # mandíbula larga
        R(9, 17, 11, 1, sk_lo)
        R(7, 11, 2, 3, skin)                                   # orelhas
        R(20, 11, 2, 3, skin)
        P(8, 12, sk_dp)
        P(21, 12, sk_dp)
        R(9, 8, 3, 3, sk_hi)                                   # brilho na testa
        # sobrancelhas grossas e franzidas
        R(10, 10, 4, 1, hair)
        R(15, 10, 4, 1, hair)
        P(10, 9, hair)
        P(18, 9, hair)
        P(13, 11, hair)
        P(15, 11, hair)
        # olhos
        R(11, 12, 3, 1, (250, 244, 236))
        R(16, 12, 3, 1, (250, 244, 236))
        R(12, 12, 1, 1, (20, 12, 16))
        R(17, 12, 1, 1, (20, 12, 16))
        P(10, 13, sk_hi)
        P(19, 13, sk_hi)
        # nariz largo, boca séria e queixo quadrado
        R(13, 14, 3, 2, sk_lo)
        P(14, 14, sk_hi)
        R(12, 16, 5, 1, (122, 62, 58))
        R(13, 17, 3, 1, sk_hi)
    # ---- cabelo preto espetado: coroa de pontas bem separadas
    if side:
        crown = [(10, 3), (12, 0), (15, 1), (17, 3)]
    else:
        crown = [(9, 3), (11, 0), (14, 2), (17, 0), (19, 3)]
    for cx_, ty_ in crown:
        pygame.draw.polygon(s, hair, [(cx_ - 3, 9), (cx_, ty_), (cx_ + 3, 9)])
        P(cx_, ty_ + 2, h_hi)
        P(cx_ - 1, ty_ + 4, h_hi)
    R(9, 7, 11 if not side else 10, 3, hair)
    R(8, 9, 2, 3, hair)
    if not side:
        R(19, 9, 2, 3, hair)
    if back:
        R(8, 8, 13, 8, hair)
        R(10, 15, 9, 1, tone(hair, .2))
    R(10, 8, 7, 1, h_hi)
    return s


def informante_frames():
    frames = {}
    for d in ("down", "up", "left", "right"):
        frames[d] = [outlined(make_informante(d, f)) for f in (0, 1, 2)]
    return frames, (INF_SIZE[0] // 2 + 1, INF_SIZE[1] - 1)


# ---------------------------------------------------------------- ferramentas de desenho dos interiores
ROOM_WALL = 84                                   # y onde a parede termina e o piso começa
ROOM_BOUNDS = (14, 306, 92, 172)                 # onde o agente anda dentro dos lugares
BOTTLES = [(66, 150, 92), (204, 84, 62), (240, 202, 92), (92, 124, 206), (206, 206, 214), (150, 92, 62),
           (118, 190, 150), (232, 140, 70)]


def rm_ceiling(s, h=10):
    for i in range(h):
        overlay(s, (0, i, IW, 1), (20, 8, 36, 90 - i * 9))


def rm_plaster(s, rect, base, seed=1, speck=0.03):
    pygame.draw.rect(s, base, rect)
    rr = random.Random(seed)
    x0, y0, w, h = rect
    for _ in range(int(w * h * speck)):
        s.set_at((x0 + rr.randrange(w), y0 + rr.randrange(h)), tone(base, rr.choice((-.12, .1, -.2))))


def rm_stripes(s, rect, c1, c2, w=8):
    x0, y0, rw, rh = rect
    for x in range(x0, x0 + rw, w):
        pygame.draw.rect(s, c1 if ((x - x0) // w) % 2 == 0 else c2, (x, y0, min(w, x0 + rw - x), rh))


def rm_diamonds(s, y0, y1, col, step=16, size=3):
    for yy in range(y0, y1, step):
        for xx in range(step // 2, IW, step):
            pygame.draw.polygon(s, col, [(xx, yy - size), (xx + size, yy), (xx, yy + size), (xx - size, yy)])


def rm_wainscot(s, y0, y1, base, line=(170, 120, 96)):
    """Lambri de madeira: painéis com moldura e frisos."""
    pygame.draw.rect(s, base, (0, y0, IW, y1 - y0))
    for x in range(6, IW, 24):
        pygame.draw.rect(s, tone(base, -.3), (x, y0 + 4, 18, y1 - y0 - 8), 1)
        pygame.draw.rect(s, tone(base, .18), (x + 1, y0 + 5, 16, 1))
    pygame.draw.rect(s, line, (0, y0 - 1, IW, 2))
    pygame.draw.rect(s, tone(line, -.5), (0, y0 + 1, IW, 1))
    pygame.draw.rect(s, tone(base, -.6), (0, y1 - 3, IW, 3))


def rm_azulejo(s, rect, base, seed=1, size=8, accent=None):
    x0, y0, w, h = rect
    for ty in range(h // size + 1):
        for tx in range(w // size + 1):
            x, y = x0 + tx * size, y0 + ty * size
            ww, hh = min(size, x0 + w - x), min(size, y0 + h - y)
            if ww <= 0 or hh <= 0:
                continue
            c = shade(base, (_hash(tx, ty, seed) % 9) - 4)
            pygame.draw.rect(s, c, (x, y, ww, hh))
            pygame.draw.rect(s, tone(c, .4), (x, y, ww, 1))
            pygame.draw.rect(s, tone(c, .4), (x, y, 1, hh))
            pygame.draw.rect(s, tone(c, -.3), (x, y + hh - 1, ww, 1))
            pygame.draw.rect(s, tone(c, -.2), (x + ww - 1, y, 1, hh))
            if ww > 4 and hh > 4:
                s.set_at((x + 2, y + 2), tone(c, .7))
            if accent and (tx + ty) % 3 == 0 and ww > 5 and hh > 5:
                pygame.draw.polygon(s, accent, [(x + 4, y + 2), (x + 6, y + 4), (x + 4, y + 6), (x + 2, y + 4)])


def rm_wood_floor(s, y0=ROOM_WALL + 1, base=(176, 118, 80), pw=40, ph=10, seed=4):
    for y in range(y0, IH, ph):
        row = (y - y0) // ph
        for x0 in range(-((row * 17) % pw), IW, pw):
            c = shade(base, (_hash(x0, row, seed) % 21) - 10)
            pygame.draw.rect(s, c, (x0, y, pw, ph))
            pygame.draw.rect(s, tone(c, .14), (x0, y, pw, 1))
            pygame.draw.rect(s, tone(c, -.35), (x0, y + ph - 1, pw, 1))
            pygame.draw.rect(s, tone(c, -.35), (x0 + pw - 1, y, 1, ph))
    overlay(s, (0, y0, IW, 6), (40, 16, 50, 70))


def rm_tile_floor(s, y0, c1, c2, size=10, seed=2):
    grout = tone(c1, -.45)
    for ty, y in enumerate(range(y0, IH, size)):
        for tx, x in enumerate(range(0, IW, size)):
            c = c1 if (tx + ty) % 2 == 0 else c2
            c = shade(c, (_hash(tx, ty, seed) % 7) - 3)
            pygame.draw.rect(s, c, (x, y, size, size))
            pygame.draw.rect(s, tone(c, .2), (x, y, size, 1))
            pygame.draw.rect(s, grout, (x + size - 1, y, 1, size))
            pygame.draw.rect(s, grout, (x, y + size - 1, size, 1))
    overlay(s, (0, y0, IW, 6), (40, 16, 50, 70))


def rm_shadow(s, cx, y, w, h=5, a=70):
    """Sombra suave de um móvel no chão."""
    o = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(o, (30, 10, 50, a), (0, 0, w, h))
    s.blit(o, (cx - w // 2, y))


def rm_door(s, x, y, w, col, sign="SAIDA", glass=True, mat=(150, 56, 66), sign_col=(255, 226, 130)):
    h = ROOM_WALL - y
    pygame.draw.rect(s, (46, 26, 36), (x - 3, y - 2, w + 6, h + 2))
    pygame.draw.rect(s, col, (x, y, w, h))
    pygame.draw.rect(s, tone(col, .3), (x, y, 2, h))
    pygame.draw.rect(s, tone(col, -.3), (x + w - 2, y, 2, h))
    if glass:
        gx, gy, gw, gh = x + 4, y + 5, w - 8, 18
        pygame.draw.rect(s, (60, 40, 50), (gx - 2, gy - 2, gw + 4, gh + 4))
        for i in range(gh):
            pygame.draw.rect(s, mix((255, 226, 140), (255, 170, 100), i / float(gh)), (gx, gy + i, gw, 1))
        pygame.draw.rect(s, (60, 40, 50), (gx + gw // 2, gy, 1, gh))
        pygame.draw.rect(s, (255, 250, 214), (gx, gy, gw, 1))
    pygame.draw.rect(s, tone(col, -.25), (x + 5, y + 29, w - 10, h - 35), 1)
    pygame.draw.rect(s, tone(col, .2), (x + 6, y + 30, w - 12, 1))
    pygame.draw.circle(s, (250, 210, 90), (x + w - 6, y + 40), 2)
    if sign:
        sw = tiny_width(sign) + 8
        sx = x + w // 2 - sw // 2
        pygame.draw.rect(s, (30, 22, 56), (sx, y - 14, sw, 9))
        pygame.draw.rect(s, (250, 206, 84), (sx, y - 14, sw, 9), 1)
        draw_tiny(s, sign, sx + 4, y - 12, sign_col)
    if mat:
        pygame.draw.rect(s, tone(mat, -.6), (x - 2, ROOM_WALL + 4, w + 4, 8))
        pygame.draw.rect(s, mat, (x, ROOM_WALL + 5, w, 6))
        pygame.draw.rect(s, tone(mat, .3), (x + 2, ROOM_WALL + 6, w - 4, 1))


def rm_window(s, x, y, w, h, frame=(60, 36, 48), curtain=None, seed=3, sill=(170, 120, 96)):
    """Janela com céu de fim de tarde e silhueta da cidade lá fora."""
    rr = random.Random(seed)
    pygame.draw.rect(s, tone(frame, -.4), (x - 2, y - 2, w + 4, h + 4))
    for i in range(h):
        pygame.draw.rect(s, mix((50, 38, 108), (244, 142, 112), i / float(h)), (x, y + i, w, 1))
    for _ in range(5):
        s.set_at((x + rr.randrange(w), y + rr.randrange(max(1, h // 3))), (255, 244, 220))
    bx = x
    while bx < x + w:
        bw = rr.randrange(5, 11)
        bh = rr.randrange(h // 5, h // 2)
        bw = min(bw, x + w - bx)
        pygame.draw.rect(s, (46, 30, 72), (bx, y + h - bh, bw, bh))
        for wy in range(y + h - bh + 2, y + h - 2, 4):
            for wx in range(bx + 1, bx + bw - 1, 3):
                if rr.random() < .45:
                    s.set_at((wx, wy), (255, 218, 120))
        bx += bw + 1
    pygame.draw.rect(s, frame, (x, y, w, 2))
    pygame.draw.rect(s, frame, (x, y + h - 2, w, 2))
    pygame.draw.rect(s, frame, (x, y, 2, h))
    pygame.draw.rect(s, frame, (x + w - 2, y, 2, h))
    pygame.draw.rect(s, frame, (x + w // 2 - 1, y, 2, h))
    pygame.draw.rect(s, frame, (x, y + h // 2 - 1, w, 2))
    pygame.draw.rect(s, tone(frame, .35), (x, y, w, 1))
    pygame.draw.rect(s, sill, (x - 3, y + h, w + 6, 3))
    pygame.draw.rect(s, tone(sill, -.5), (x - 3, y + h + 3, w + 6, 1))
    if curtain:
        for cx0 in (x + 1, x + w - 9):
            pygame.draw.rect(s, curtain, (cx0, y + 1, 8, h - 2))
            for k in range(cx0 + 2, cx0 + 8, 3):
                pygame.draw.line(s, tone(curtain, -.3), (k, y + 1), (k, y + h - 2))
        pygame.draw.rect(s, (90, 70, 60), (x - 3, y - 4, w + 6, 2))


def rm_clock(s, cx, cy, r=6, hour=8, minute=10, face=(246, 238, 214), rim=(60, 36, 40)):
    pygame.draw.circle(s, rim, (cx, cy), r + 1)
    pygame.draw.circle(s, face, (cx, cy), r)
    for k in range(12):
        a = math.radians(k * 30)
        s.set_at((int(cx + math.sin(a) * (r - 1)), int(cy - math.cos(a) * (r - 1))), (60, 40, 40))
    ah = math.radians((hour % 12) * 30 + minute * .5)
    am = math.radians(minute * 6)
    pygame.draw.line(s, (40, 30, 40), (cx, cy), (int(cx + math.sin(ah) * (r - 3)), int(cy - math.cos(ah) * (r - 3))))
    pygame.draw.line(s, (40, 30, 40), (cx, cy), (int(cx + math.sin(am) * (r - 1)), int(cy - math.cos(am) * (r - 1))))
    s.set_at((cx, cy), (200, 50, 50))


def rm_frame(s, x, y, w, h, inner=(214, 190, 150), frame=(86, 52, 44), art=None):
    pygame.draw.rect(s, tone(frame, -.5), (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, frame, (x, y, w, h))
    pygame.draw.rect(s, tone(frame, .3), (x, y, w, 1))
    pygame.draw.rect(s, inner, (x + 2, y + 2, w - 4, h - 4))
    if art == "retrato":
        cx0 = x + w // 2
        pygame.draw.circle(s, (176, 120, 96), (cx0, y + h // 2 - 1), max(2, w // 5))
        pygame.draw.rect(s, (70, 56, 90), (cx0 - w // 4, y + h // 2 + 2, w // 2, max(2, h // 4)))
    elif art == "paisagem":
        pygame.draw.rect(s, (110, 170, 214), (x + 2, y + 2, w - 4, (h - 4) // 2))
        pygame.draw.rect(s, (84, 150, 100), (x + 2, y + 2 + (h - 4) // 2, w - 4, (h - 4) // 2))
        pygame.draw.polygon(s, (60, 110, 80), [(x + 2, y + h // 2 + 2), (x + w // 3, y + 4), (x + w // 2, y + h // 2 + 2)])
    elif art == "familia":
        for k, cc in enumerate(((176, 120, 96), (206, 150, 120), (150, 100, 80))):
            pygame.draw.circle(s, cc, (x + 4 + k * ((w - 8) // 2), y + h // 2), 2)
            pygame.draw.rect(s, tone(cc, -.4), (x + 3 + k * ((w - 8) // 2), y + h // 2 + 2, 3, 3))


def rm_bottle(s, x, y, col, h=9, w=3):
    """Garrafa com o pé em (x, y)."""
    pygame.draw.rect(s, tone(col, -.45), (x, y - h + 3, w, h - 3))
    pygame.draw.rect(s, col, (x, y - h + 3, w - 1, h - 3))
    pygame.draw.rect(s, tone(col, -.2), (x + 1, y - h, max(1, w - 2), 4))
    pygame.draw.rect(s, (236, 214, 150), (x + 1, y - h - 1, max(1, w - 2), 1))
    s.set_at((x, y - h + 5), tone(col, .7))
    pygame.draw.rect(s, (246, 240, 220), (x, y - 4, w - 1, 2))


def rm_shelf(s, x, y, w, col=(112, 68, 52)):
    pygame.draw.rect(s, tone(col, -.5), (x, y, w, 4))
    pygame.draw.rect(s, col, (x, y, w, 3))
    pygame.draw.rect(s, tone(col, .35), (x, y, w, 1))
    overlay(s, (x, y + 4, w, 3), (30, 10, 50, 70))


def rm_hang_lamp(s, cx, y_top, y_shade, w=12, col=(214, 160, 70)):
    pygame.draw.line(s, (40, 28, 52), (cx, y_top), (cx, y_shade))
    pygame.draw.polygon(s, tone(col, -.4), [(cx - w // 2, y_shade + 6), (cx + w // 2, y_shade + 6), (cx + 3, y_shade), (cx - 3, y_shade)])
    pygame.draw.polygon(s, col, [(cx - w // 2 + 1, y_shade + 5), (cx + w // 2 - 1, y_shade + 5), (cx + 2, y_shade + 1), (cx - 2, y_shade + 1)])
    pygame.draw.rect(s, (255, 244, 190), (cx - 2, y_shade + 6, 5, 2))


def rm_sign(s, text, cx, y, bg=(30, 22, 56), fg=(255, 226, 130), border=(250, 206, 84)):
    w = tiny_width(text) + 8
    pygame.draw.rect(s, bg, (cx - w // 2, y, w, 9))
    pygame.draw.rect(s, border, (cx - w // 2, y, w, 9), 1)
    draw_tiny(s, text, cx - w // 2 + 4, y + 2, fg)


def rm_chalkboard(s, x, y, w, h, lines):
    pygame.draw.rect(s, (70, 44, 36), (x - 2, y - 2, w + 4, h + 4))
    pygame.draw.rect(s, (36, 66, 56), (x, y, w, h))
    pygame.draw.rect(s, (60, 100, 84), (x, y, w, 1))
    for i, ln in enumerate(lines):
        draw_tiny(s, ln, x + 3, y + 3 + i * 7, (236, 238, 226))
    pygame.draw.rect(s, (200, 200, 190), (x + 2, y + h - 2, 5, 1))


# ---------------------------------------------------------------- móveis (sprites com transparência)
def rm_counter_sprite(w, front=20, wood=(124, 72, 58), top=(226, 184, 132), rail=True, tile=None):
    s = pygame.Surface((w, front + 8), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(top, -.5), (0, 0, w, 8))
    pygame.draw.rect(s, top, (0, 0, w, 6))
    pygame.draw.rect(s, tone(top, .45), (0, 0, w, 1))
    pygame.draw.rect(s, tone(top, -.25), (0, 5, w, 1))
    pygame.draw.rect(s, tone(wood, -.5), (0, 8, w, front))
    pygame.draw.rect(s, wood, (0, 8, w, front - 2))
    pygame.draw.rect(s, tone(wood, .3), (0, 8, w, 1))
    if tile:
        for ty in range(10, front + 4, 5):
            for tx in range(1, w - 1, 6):
                pygame.draw.rect(s, tile if (tx // 6 + ty // 5) % 2 == 0 else tone(tile, .25), (tx, ty, 5, 4))
    else:
        for x in range(4, w - 4, 14):
            pygame.draw.rect(s, tone(wood, -.35), (x, 11, 11, front - 8), 1)
            pygame.draw.rect(s, tone(wood, .2), (x + 1, 12, 9, 1))
    if rail:
        pygame.draw.rect(s, (214, 180, 90), (0, front + 3, w, 2))
        pygame.draw.rect(s, (255, 236, 160), (0, front + 3, w, 1))
    return s


def rm_stool_sprite(col=(190, 60, 70)):
    s = pygame.Surface((12, 20), pygame.SRCALPHA)
    pygame.draw.line(s, (120, 120, 140), (3, 8), (1, 18))
    pygame.draw.line(s, (120, 120, 140), (8, 8), (10, 18))
    pygame.draw.line(s, (150, 150, 170), (6, 8), (6, 18))
    pygame.draw.ellipse(s, (150, 150, 170), (1, 13, 10, 4), 1)
    pygame.draw.ellipse(s, tone(col, -.45), (0, 2, 12, 7))
    pygame.draw.ellipse(s, col, (0, 1, 12, 6))
    pygame.draw.rect(s, tone(col, .5), (3, 2, 5, 1))
    return s


def rm_round_table_sprite(w=32, wood=(150, 98, 70), cloth=None):
    s = pygame.Surface((w, 30), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(wood, -.4), (w // 2 - 2, 10, 4, 15))
    pygame.draw.rect(s, wood, (w // 2 - 2, 10, 3, 15))
    pygame.draw.ellipse(s, tone(wood, -.4), (w // 2 - 9, 23, 18, 6))
    pygame.draw.ellipse(s, wood, (w // 2 - 9, 23, 18, 5))
    top = cloth or wood
    pygame.draw.ellipse(s, tone(top, -.5), (0, 3, w, 12))
    pygame.draw.ellipse(s, top, (0, 2, w, 10))
    pygame.draw.ellipse(s, tone(top, .3), (3, 3, w - 6, 5))
    pygame.draw.ellipse(s, tone(top, -.2), (2, 6, w - 4, 4), 1)
    return s


def rm_crates_sprite():
    s = pygame.Surface((30, 30), pygame.SRCALPHA)
    for k, yy in enumerate((16, 2)):
        pygame.draw.rect(s, (60, 40, 30), (0, yy + 5, 30, 13))
        pygame.draw.rect(s, (214, 70, 60), (1, yy + 6, 28, 11))
        pygame.draw.rect(s, (236, 110, 90), (1, yy + 6, 28, 1))
        for bx in range(3, 28, 4):
            pygame.draw.rect(s, (110, 62, 28), (bx, yy, 3, 6))
            pygame.draw.rect(s, (240, 200, 90), (bx, yy - 1, 3, 1))
        pygame.draw.rect(s, (250, 230, 200), (4, yy + 9, 12, 4))
    return s


def rm_sack_sprite(col=(232, 218, 190)):
    s = pygame.Surface((20, 22), pygame.SRCALPHA)
    pygame.draw.ellipse(s, tone(col, -.4), (0, 4, 20, 18))
    pygame.draw.ellipse(s, col, (0, 4, 19, 16))
    pygame.draw.polygon(s, tone(col, -.2), [(4, 6), (6, 0), (10, 3), (14, 0), (16, 6)])
    pygame.draw.rect(s, (160, 60, 60), (4, 9, 12, 6))
    draw_tiny(s, "TRIGO", 10 - tiny_width("TRIGO") // 2, 10, (250, 240, 220))
    return s


def rm_sofa_sprite(w=58, col=(150, 60, 80)):
    s = pygame.Surface((w, 30), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(col, -.5), (0, 0, w, 20))
    pygame.draw.rect(s, col, (2, 1, w - 4, 16))
    pygame.draw.rect(s, tone(col, .3), (2, 1, w - 4, 2))
    for k in range(4, w - 6, 16):
        pygame.draw.rect(s, tone(col, -.3), (k + 12, 4, 1, 12))
        pygame.draw.circle(s, tone(col, .3), (k + 6, 9), 1)
    pygame.draw.rect(s, tone(col, -.5), (0, 12, w, 14))
    pygame.draw.rect(s, tone(col, .12), (3, 14, w - 6, 9))
    pygame.draw.rect(s, tone(col, .4), (3, 14, w - 6, 1))
    pygame.draw.line(s, tone(col, -.4), (w // 2, 14), (w // 2, 22))
    for ax in (0, w - 7):
        pygame.draw.rect(s, tone(col, -.45), (ax, 8, 7, 18))
        pygame.draw.rect(s, tone(col, .1), (ax + 1, 9, 5, 5))
    for lx in (3, w - 7):
        pygame.draw.rect(s, (60, 36, 40), (lx, 26, 4, 4))
    return s


def rm_armchair_sprite(col=(70, 110, 140), facing="right"):
    s = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.rect(s, tone(col, -.5), (3, 0, 24, 16))
    pygame.draw.rect(s, col, (4, 1, 22, 13))
    pygame.draw.rect(s, tone(col, .35), (4, 1, 22, 2))
    pygame.draw.rect(s, tone(col, -.5), (0, 10, 30, 16))
    pygame.draw.rect(s, tone(col, .12), (6, 14, 18, 8))
    pygame.draw.rect(s, tone(col, .4), (6, 14, 18, 1))
    for ax in (0, 24):
        pygame.draw.rect(s, tone(col, -.4), (ax, 10, 6, 16))
        pygame.draw.rect(s, col, (ax + 1, 11, 4, 5))
    for lx in (2, 24):
        pygame.draw.rect(s, (60, 36, 40), (lx, 26, 4, 4))
    return s


def rm_jukebox_sprite():
    s = pygame.Surface((30, 58), pygame.SRCALPHA)
    body = (150, 56, 96)
    pygame.draw.ellipse(s, tone(body, -.5), (0, 0, 30, 24))
    pygame.draw.rect(s, tone(body, -.5), (0, 12, 30, 44))
    pygame.draw.ellipse(s, body, (1, 1, 28, 22))
    pygame.draw.rect(s, body, (1, 12, 28, 42))
    pygame.draw.rect(s, tone(body, .3), (1, 12, 2, 42))
    pygame.draw.ellipse(s, (30, 24, 50), (4, 4, 22, 20))                # vidro em arco
    pygame.draw.rect(s, (30, 24, 50), (4, 14, 22, 14))
    pygame.draw.ellipse(s, (60, 50, 90), (6, 6, 18, 16))
    pygame.draw.rect(s, (60, 50, 90), (6, 14, 18, 12))
    for k in range(5):                                                   # pilha de discos
        pygame.draw.rect(s, (20, 18, 24), (8, 16 + k * 2, 14, 1))
    pygame.draw.rect(s, (240, 210, 120), (13, 12, 4, 4))
    pygame.draw.rect(s, (214, 196, 230), (5, 30, 20, 8))                 # painel de botões
    for k in range(6):
        pygame.draw.rect(s, (200, 60, 70) if k % 2 == 0 else (60, 130, 200), (6 + k * 3, 32, 2, 3))
    for gy in range(41, 52, 2):                                          # alto-falante
        pygame.draw.rect(s, (60, 30, 56), (6, gy, 18, 1))
    pygame.draw.rect(s, (246, 200, 70), (2, 54, 26, 2))
    return s


def rm_briefcase_sprite():
    s = pygame.Surface((12, 9), pygame.SRCALPHA)
    pygame.draw.rect(s, (60, 36, 28), (0, 2, 12, 7))
    pygame.draw.rect(s, (112, 70, 44), (1, 3, 10, 5))
    pygame.draw.rect(s, (156, 104, 66), (1, 3, 10, 1))
    pygame.draw.rect(s, (60, 36, 28), (4, 0, 4, 3), 1)
    pygame.draw.rect(s, (246, 200, 70), (5, 5, 2, 2))
    return s


# ---------------------------------------------------------------- BAR (onde fica o Informante)
def _decor(lst, spr, x, y, sort_y=None):
    """Registra um móvel com contorno: (y de ordenação, sprite, x, y) - o contorno de 1px fica fora."""
    o = outlined(spr)
    lst.append((sort_y if sort_y is not None else y + spr.get_height(), o, x - 1, y - 1))


def room_bar():
    r = random.Random(21)
    s = pygame.Surface((IW, IH))
    W_ = ROOM_WALL
    rm_stripes(s, (0, 0, IW, W_), (68, 44, 96), (60, 38, 88), 10)
    rm_diamonds(s, 10, 58, (82, 58, 112), 20, 2)
    rm_ceiling(s)
    rm_wainscot(s, 58, W_, (96, 52, 62))
    rm_tile_floor(s, W_ + 1, (206, 196, 182), (74, 54, 86), 10)
    rm_door(s, 10, 22, 36, (112, 72, 64), "SAIDA")
    # bandeirolas de time e relógio entre a porta e o espelho
    pygame.draw.line(s, (40, 28, 52), (50, 14), (74, 18))
    for k, cc in enumerate(((214, 52, 60), (250, 250, 250), (30, 30, 36), (214, 52, 60))):
        px = 52 + k * 6
        py = 14 + int(k * 4 / 3)
        pygame.draw.polygon(s, tone(cc, -.45), [(px - 1, py), (px + 5, py), (px + 2, py + 9)])
        pygame.draw.polygon(s, cc, [(px, py), (px + 4, py), (px + 2, py + 7)])
    rm_clock(s, 62, 46, 7, 9, 40)
    # espelho do balcão com prateleiras de garrafas
    pygame.draw.rect(s, (46, 28, 36), (76, 16, 128, 56))
    pygame.draw.rect(s, (110, 66, 50), (77, 17, 126, 54))
    for i in range(50):
        pygame.draw.rect(s, mix((196, 232, 236), (118, 156, 176), i / 50.0), (79, 19 + i, 122, 1))
    for dx in (14, 52, 96):
        pygame.draw.line(s, (232, 250, 250), (79 + dx, 19), (79 + dx - 12, 68))
        pygame.draw.line(s, (214, 240, 244), (80 + dx, 19), (80 + dx - 12, 68))
    for sy in (33, 47, 61):
        rm_shelf(s, 79, sy, 122)
        for bx in range(83, 197, 6):
            rm_bottle(s, bx, sy, r.choice(BOTTLES), r.randrange(8, 12))
    for gx in range(86, 196, 11):                              # copos na prateleira de baixo
        pygame.draw.rect(s, (214, 236, 244), (gx, 55, 3, 5))
        pygame.draw.rect(s, (160, 200, 214), (gx, 55, 3, 1))
    neon_text(s, "BAR", 128, 4, (110, 240, 236), 2)
    pygame.draw.rect(s, (110, 240, 236), (122, 2, 1, 12))
    pygame.draw.rect(s, (110, 240, 236), (154, 2, 1, 12))
    # jukebox na parede da direita
    s.blit(outlined(rm_jukebox_sprite()), (213, 25))
    rm_shadow(s, 229, 85, 38, 6, 80)
    # pôster da Copa, alvo de dardos e quadro
    pygame.draw.rect(s, (30, 24, 40), (254, 14, 32, 42))
    pygame.draw.rect(s, (30, 130, 70), (256, 16, 28, 38))
    pygame.draw.circle(s, (250, 214, 60), (270, 32), 8)
    pygame.draw.circle(s, (50, 70, 160), (270, 32), 5)
    pygame.draw.rect(s, (250, 214, 60), (256, 16, 28, 1))
    draw_tiny(s, "MEXICO", 270 - tiny_width("MEXICO") // 2, 44, (250, 244, 214))
    draw_tiny(s, "70", 270 - tiny_width("70") // 2, 49, (250, 214, 60))
    for rad, cc in ((9, (40, 30, 40)), (8, (230, 224, 206)), (6, (40, 130, 80)), (4, (214, 60, 60)), (2, (30, 30, 36))):
        pygame.draw.circle(s, cc, (298, 34), rad)
    pygame.draw.line(s, (240, 240, 240), (292, 34), (304, 34))
    rm_frame(s, 292, 50, 18, 14, art="paisagem")
    # luminária pendurada sobre a mesa do informante
    rm_hang_lamp(s, 268, 0, 52, 16, (60, 150, 130))
    overlay(s, (0, W_ + 1, IW, IH - W_), (24, 10, 50, 56))
    # sujeira de bar no chão
    for _ in range(46):
        s.set_at((r.randrange(16, 304), r.randrange(98, 176)), r.choice(((150, 118, 84), (96, 76, 70), (230, 214, 190))))
    pygame.draw.ellipse(s, (60, 46, 70), (146, 150, 22, 6))
    # móveis
    decor, cols = [], []
    cw = 156
    cs = pygame.Surface((cw, 42), pygame.SRCALPHA)
    cs.blit(rm_counter_sprite(cw, 20, (112, 62, 56), (222, 178, 128)), (0, 14))
    pygame.draw.rect(cs, (150, 150, 166), (20, 6, 3, 9))                       # chopeira
    pygame.draw.rect(cs, (214, 214, 226), (17, 4, 9, 3))
    pygame.draw.rect(cs, (214, 60, 60), (18, 1, 2, 4))
    pygame.draw.rect(cs, (60, 130, 200), (23, 1, 2, 4))
    pygame.draw.rect(cs, (60, 50, 70), (62, 4, 20, 11))                         # caixa registradora
    pygame.draw.rect(cs, (210, 196, 150), (64, 5, 16, 5))
    pygame.draw.rect(cs, (60, 120, 90), (66, 6, 12, 2))
    for k in range(4):
        pygame.draw.rect(cs, (240, 230, 190), (65 + k * 4, 11, 3, 2))
    pygame.draw.rect(cs, (236, 226, 190), (34, 8, 12, 7))                       # pote de amendoim
    pygame.draw.ellipse(cs, (200, 150, 80), (34, 5, 12, 5))
    for gx in (124, 130, 136):
        pygame.draw.rect(cs, (214, 236, 244), (gx, 9, 3, 6))
        pygame.draw.rect(cs, (240, 190, 70), (gx, 11, 3, 4))
    _decor(decor, cs, 58, 62, 104)
    cols.append(pygame.Rect(56, 90, 160, 16))
    for sx in (74, 106, 138, 170, 202):
        _decor(decor, rm_stool_sprite((196, 60, 72)), sx, 112, 132)
        cols.append(pygame.Rect(sx + 1, 122, 10, 10))
    # mesa alta com dois fregueses conversando
    rm_shadow(s, 128, 160, 28, 5, 70)
    ts = pygame.Surface((24, 30), pygame.SRCALPHA)
    pygame.draw.rect(ts, (60, 44, 40), (11, 8, 3, 20))
    pygame.draw.ellipse(ts, (60, 44, 40), (5, 26, 14, 4))
    pygame.draw.ellipse(ts, (96, 62, 52), (0, 3, 24, 8))
    pygame.draw.ellipse(ts, (176, 126, 96), (0, 2, 24, 7))
    pygame.draw.rect(ts, (214, 236, 244), (5, 0, 3, 4))
    pygame.draw.rect(ts, (240, 190, 70), (5, 2, 3, 2))
    pygame.draw.rect(ts, (214, 236, 244), (16, 0, 3, 4))
    _decor(decor, ts, 116, 134, 164)
    cols.append(pygame.Rect(116, 154, 24, 8))
    # mesa do informante, cinzeiro, copos, jornal e a maleta
    tb = rm_round_table_sprite(36, (112, 70, 54), (160, 50, 62))
    pygame.draw.polygon(tb, (226, 220, 204), [(6, 6), (16, 3), (20, 7), (10, 10)])
    pygame.draw.line(tb, (90, 86, 90), (9, 6), (16, 5))
    pygame.draw.ellipse(tb, (60, 56, 70), (23, 3, 8, 4))
    pygame.draw.ellipse(tb, (120, 120, 140), (24, 3, 6, 3))
    pygame.draw.rect(tb, (214, 236, 244), (3, 0, 3, 5))
    pygame.draw.rect(tb, (240, 190, 70), (3, 2, 3, 3))
    _decor(decor, tb, 240, 118, 150)
    cols.append(pygame.Rect(242, 136, 32, 10))
    _decor(decor, rm_briefcase_sprite(), 280, 146, 156)
    # engradados de cerveja no canto
    _decor(decor, rm_crates_sprite(), 16, 138, 168)
    cols.append(pygame.Rect(16, 158, 30, 10))
    # fregueses decorativos (sem fala)
    pa = dict(skin=(190, 140, 104), hair=(40, 28, 24), style="short", top=(120, 170, 120), sleeve=(120, 170, 120),
              legs=(70, 70, 90), shoes=(50, 40, 40), headwear="hat", hw=[(120, 90, 62)])
    pb = dict(skin=(226, 184, 150), hair=(150, 90, 50), style="short", top=(214, 90, 70), sleeve=(214, 90, 70),
              legs=(60, 80, 120), shoes=(40, 34, 40))
    fa, anc = make_actor(pa)
    fb, _ = make_actor(pb)
    decor.append((150, fa["right"][0], 110 - anc[0], 150 - anc[1]))
    decor.append((150, fb["left"][0], 148 - anc[0], 150 - anc[1]))
    npcs = [
        dict(id="seu_dino", name="Seu Dino", dlg="dino", x=162, y=85, face="down",
             p=dict(skin=(214, 164, 124), hair=(60, 54, 60), style="short", top=(250, 250, 250), sleeve=(250, 250, 250),
                    legs=(40, 36, 52), shoes=(30, 24, 30), beard=True, glasses=False)),
        dict(id="informante", name="Bastião, o Informante", dlg="informante", x=294, y=142, face="down",
             p={}, actor=informante_frames),
    ]
    spots = [("porta", 28, 100, 22, "Sair", None),
             ("npc:seu_dino", 162, 114, 40, "Falar com Seu Dino", None),
             ("npc:informante", 294, 142, 34, "Falar com o Informante", None),
             ("look", 229, 100, 20, "Jukebox",
              "Você põe uma ficha. Sai um samba de letra dupla: parece romance, mas fala de saudade dos que sumiram.")]
    lights = [(138, 12, 56, (30, 150, 150), 1), (268, 60, 74, (255, 190, 110), 1), (229, 56, 44, (210, 60, 150), 1),
              (140, 50, 64, (150, 110, 60), 0), (28, 52, 34, (200, 150, 80), 0)]
    return dict(title="Bar do Seu Dino", bg=s, decor=decor, cols=cols, spots=spots, npcs=npcs, lights=lights,
                start=(28, 112), anim="bar")


def anim_bar(g, f, t):
    """Vitrola com lâmpadas pulsando, cone de luz da luminária, poeira e fumaça de cigarro."""
    pal = ((255, 80, 120), (255, 214, 80), (90, 220, 255), (150, 255, 140))
    for k in range(9):
        a = math.pi * (k / 8.0)
        bx = int(228 - math.cos(a) * 10)
        by = int(30 - math.sin(a) * 6)
        on = (int(t * 6) + k) % 4
        f.set_at((bx, by), pal[on])
        f.set_at((bx, by + 1), tone(pal[on], -.3))
    for k in range(5):
        pygame.draw.rect(f, pal[(int(t * 4) + k) % 4], (219 + k * 4, 33, 2, 2))
    cone = pygame.Surface((IW, IH), pygame.SRCALPHA)
    pygame.draw.polygon(cone, (255, 200, 120, 26), [(262, 60), (274, 60), (304, 150), (232, 150)])
    pygame.draw.polygon(cone, (255, 220, 160, 18), [(264, 60), (272, 60), (290, 150), (246, 150)])
    f.blit(cone, (0, 0))
    for i in range(7):                                       # poeira dançando no cone
        ph = (t * 0.12 + i * 0.37) % 1.0
        x = 250 + (i * 17) % 38 + math.sin(t * 0.8 + i) * 3
        y = 70 + ph * 70
        f.set_at((int(x), int(y)), (255, 236, 190))
    for i in range(6):                                       # fumaça do cinzeiro
        ph = (t * 0.45 + i * 0.17) % 1.0
        sm = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(sm, (220, 220, 230, int(110 * (1 - ph))), (4, 4), 1 + int(ph * 3))
        f.blit(sm, (int(266 + math.sin(ph * 7 + i) * 4) - 4, int(124 - ph * 28) - 4))


# ---------------------------------------------------------------- registro dos lugares com interior
ROOM_BUILDERS = {"bar": room_bar}
# onde o agente fica na calçada para entrar (px): centro do prédio + posição da porta no sprite
ROOM_DOORS = {"bar": ((40 + OX) * TS - 48 + 45, (14 + OY) * TS + 6)}
ROOM_LABEL = {"bar": "Bar"}

REWARD = dict(doc=(4, 15), evid=(5, 20), pista=(2, 10))      # (evidências, Cr$) por entrega
HINT_COST = 10
INF_HINTS = {
    "mario": "O Professor Mário anda pela Av. Atlântica e pelo Largo. Ele é o primeiro contato da rede.",
    "a_pick": "Os panfletos estão na Feira Livre. O bilhete é uma cifra de César: gire as letras até fazer sentido.",
    "a_drop": "Dom Aurélio circula perto da igreja, no Largo da Carioca. Ele espera os panfletos.",
    "b_pick": "A gaveta do Largo abre com toques: memorize a sequência de luzes e repita.",
    "b_drop": "O estúdio do Zeca fica na Av. Atlântica. Leve a fita sem chamar atenção da polícia.",
    "c_cida": "Dona Cida guarda uma data. Quem perdeu um filho não esquece o dia.",
    "c_pick": "A chave está escondida no Calçadão. Olhe onde o mar encontra a pedra.",
    "c_cofre": "O cofre da sacristia usa quatro dígitos: dia e mês, a data que Dona Cida contou.",
    "rota": "Volte ao Professor Mário e escolha Igreja, Rádio ou Imprensa. Depois de escolher, não há volta.",
    "r_zeca": "Zeca circula entre o Calçadão e a Av. Atlântica. Ouça o que a censura fez com ele.",
    "r_tavares": "Tavares anda entre o Largo e a Feira Livre.",
    "i_tavares": "Tavares anda entre o Largo e a Feira Livre.",
    "i_pick": "A gaveta do arquivo fica no Largo. Memorize a sequência de luzes e repita.",
    "i_drop": "Os negativos vão para o Tavares, que circula entre o Largo e a Feira.",
    "i_nelson": "Seu Nelson só fala depois que você conhecer o Tavares.",
}

DLG["dino"] = {
    "start": D("Seu Dino", "Boa noite, bicho esquisito. Aqui só se serve cachaça, cerveja e silêncio. "
                           "Se quer conversar de verdade, o grandalhão da mesa do canto é quem sabe das coisas.",
               nxt="p2"),
    "p2": D("Seu Dino", "Chama-se Bastião. Ele não vende nada: só recebe papel, fita e história, e guarda cópia "
                        "em lugar que ninguém acha. Mas só abre a boca para quem chega com alguma coisa na mão."),
    "again": D("Seu Dino", "A vitrola está alta de propósito: quem fala baixo aqui não é ouvido. O Bastião está na mesa do canto."),
}
DLG["informante"] = {
    "start": D("Bastião", "Então você é o porco de quem andam falando. Sente-se, mas não olhe pra mim: olhe pro copo. "
                          "Chamam-me Bastião. Aqui dentro eu sou ouvido, lá fora sou apenas o homem que carrega caixa.",
               nxt="s2", flag="inf_met"),
    "s2": D("Bastião", "Meu trabalho é guardar cópias. Você me traz documentos, fitas e o que as testemunhas disseram, "
                       "eu tiro cópia e escondo onde o regime não alcança. O original segue o seu caminho, nada se perde."),
    "s3": D("Bastião", "Cada coisa que você me entrega engrossa o dossiê e rende uns trocados da rede. "
                       "Se estiver perdido, uma dica minha custa Cr$ %d. Mostre o que você tem." % HINT_COST),
    "again": D("Bastião", "De volta. Ponha na mesa o que conseguiu: documentos, evidências e pistas. Eu cuido do resto."),
}
DLG["informante"]["s2"]["nxt"] = "s3"


class RoomsMixin:
    """Interiores 2D (bar do informante e outros lugares) e a entrega de provas."""

    def build_rooms(self):
        self.rooms = {}
        self.room_npcs = []
        for kind, fn in ROOM_BUILDERS.items():
            spec = fn()
            objs = []
            for c in spec["npcs"]:
                n = NPC(dict(id=c["id"], name=c["name"], dlg=c["dlg"], pos=(0, 0), face=c.get("face", "down"),
                             p=c["p"], actor=c.get("actor")))
                n.x, n.y = float(c["x"]), float(c["y"])
                n.home = (n.x, n.y)
                n.stops, n.speed = [], 0
                objs.append(n)
                self.room_npcs.append(n)
            spec["npc_objs"] = objs
            self.rooms[kind] = spec

    # ------------------------------------------------------------ entrar e sair
    def near_room_door(self):
        for kind, (dx, dy) in ROOM_DOORS.items():
            if math.hypot(dx - self.px, dy - self.py) < 24:
                return kind
        return None

    def enter_room(self, kind):
        spec = self.rooms[kind]
        self.rk = kind
        self.hx, self.hy = float(spec["start"][0]), float(spec["start"][1])
        self.hdir, self.hanim, self.hmoving = "down", 0.0, False
        br = self.npc_by_id["brandao"]
        if br.chase or self.susp >= 80:
            br.chase = False
            br.path = []
            self.chase_cd = 30.0
            self.notify("Você se escondeu no bar. O cerco esfriou um pouco.", 4.5)
        self.state = "room"

    def exit_room(self):
        dx, dy = ROOM_DOORS[self.rk]
        self.px, self.py = float(dx), float(dy + 2)
        self.dir = "down"
        self.rk = None
        self.state = "play"

    def room_blocked(self, rect):
        x0, x1, y0, y1 = ROOM_BOUNDS
        if rect.left < x0 or rect.right > x1 or rect.top < y0 - 4 or rect.bottom > y1:
            return True
        spec = self.rooms[self.rk]
        if rect.collidelist(spec["cols"]) != -1:
            return True
        for n in spec["npc_objs"]:
            if rect.colliderect(pygame.Rect(int(n.x) - 8, int(n.y) - 5, 16, 5)):
                return True
        return False

    def room_update(self, dt):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.hmoving = bool(dx or dy)
        if not self.hmoving:
            self.hanim = 0.0
            return
        n = math.hypot(dx, dy)
        spd = 58 * (RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0)
        nx = self.hx + dx / n * spd * dt
        if not self.room_blocked(pygame.Rect(int(nx) - 4, int(self.hy) - 4, 8, 4)):
            self.hx = nx
        ny = self.hy + dy / n * spd * dt
        if not self.room_blocked(pygame.Rect(int(self.hx) - 4, int(ny) - 4, 8, 4)):
            self.hy = ny
        if dx:
            self.hdir = "right" if dx > 0 else "left"
        else:
            self.hdir = "down" if dy > 0 else "up"
        self.hanim += dt * (spd / 58.0)

    def room_spot(self):
        best, bd = None, 1e9
        for sid, x, y, rad, lab, txt in self.rooms[self.rk]["spots"]:
            d = math.hypot(x - self.hx, y - self.hy)
            if d < rad and d < bd:
                best, bd = (sid, x, y, lab, txt), d
        return best

    def room_interact(self):
        sp = self.room_spot()
        if not sp:
            return
        sid = sp[0]
        if sid == "porta":
            self.exit_room()
        elif sid.startswith("npc:"):
            nid = sid[4:]
            for n in self.rooms[self.rk]["npc_objs"]:
                if n.id == nid:
                    self.dir = self.hdir
                    self.start_dialogue(n)
                    return
        elif sp[4]:
            self.notify(sp[4], 5.5)

    # ------------------------------------------------------------ desenho
    def draw_room(self):
        spec = self.rooms[self.rk]
        f = self.frame
        f.blit(spec["bg"], (0, 0))
        seq = [0, 1, 0, 2]
        pf = seq[int(self.hanim * 8) % 4] if self.hmoving else 0
        hero = self.frames[self.hdir][pf]
        objs = list(spec["decor"])
        for n in spec["npc_objs"]:
            f.blit(self.npc_shadow, (int(n.x - 7), int(n.y - 4)))
            sp = n.frames[n.face][0]
            objs.append((n.y, sp, int(n.x - n.anchor[0]), int(n.y - n.anchor[1])))
        f.blit(self.npc_shadow, (int(self.hx - 7), int(self.hy - 4)))
        objs.append((self.hy, hero, int(self.hx - self.anchor[0]), int(self.hy - self.anchor[1])))
        objs.sort(key=lambda o: o[0])
        for _, spr, px, py in objs:
            f.blit(spr, (px, py))
        fn = globals().get("anim_" + str(spec.get("anim")))
        if fn:
            fn(self, f, self.t)
        for x, y, rad, col, flick in spec["lights"]:
            k = (0.86 + 0.14 * math.sin(self.t * 7 + x)) if flick else 0.9
            f.blit(self.glow_surf(col, rad, k), (x - rad, y - rad), special_flags=pygame.BLEND_RGB_ADD)
        f.blit(self.vig, (0, 0))
        pygame.transform.scale(f, (W, H), self.screen)

    def draw_room_hud(self):
        spec = self.rooms[self.rk]
        title = "%s - Dia %d" % (spec["title"], self.day)
        tw = self.f_med.size(title)[0] + 70
        self.panel((640 - tw // 2, 6, tw, 50), 225)
        self.text(title, self.f_med, (255, 244, 220), (640, 31), center=True)
        txt = "Prazo %s (parado aqui dentro)   Cr$ %d no bolso" % (self.fmt_time(TIME_LIMIT - self.clock), self.money)
        w = self.f_sm.size(txt)[0] + 44
        self.panel((16, 64, w, 38), 215, border=(255, 222, 150))
        self.text(txt, self.f_sm, (255, 238, 180), (38, 75))
        obj = "Objetivo: " + self.objective()
        w = self.f_sm.size(obj)[0] + 44
        self.panel((16, 108, w, 38), 215, border=(255, 222, 150))
        self.text(obj, self.f_sm, (190, 240, 255), (38, 119))
        self.draw_status_panel()
        if self.state == "room":
            self.text("E: usar    Esc: pausa", self.f_xs, (255, 255, 255), (W - 18, 12), right=True)
            sp = self.room_spot()
            if sp:
                sx = int(self.hx * SC)
                sy = int((self.hy - 36) * SC) + int(math.sin(self.t * 4) * 4)
                self.draw_bubble_at(sx, sy, True, "E")
                self.text(sp[3], self.f_sm, (255, 214, 120), (sx, sy - 44), center=True)

    # ------------------------------------------------------------ entrega ao informante
    def inf_have(self, item):
        sid = dict(panfletos="a_pick", fita="b_pick", lista="c_cofre")[item]
        return sid in self.done_steps or item in self.pack or item in self.stash

    def entrega_rows(self):
        rows = []

        def add(kind, key, label, ok):
            rows.append(dict(kind=kind, key=key, label=label, ok=ok, done=(kind, key) in self.delivered))
        add("doc", "lista", "Documento: Lista de presos", self.inf_have("lista"))
        add("doc", "panfletos", "Documento: Panfletos", self.inf_have("panfletos"))
        add("evid", "fita", "Evidência: Fita cassete", self.inf_have("fita"))
        for k in TESTIMONIES:
            add("pista", k, "Pista: %s (%s)" % (SHORT[k], TOPICS[k]), k in self.flags)
        rows.append(dict(kind="dica", key=None, label="Pedir uma dica (Cr$ %d)" % HINT_COST, ok=True, done=False))
        return rows

    def open_entrega(self):
        self.ent = dict(idx=0, msg="Mostre o que você tem. Eu faço a cópia, o original segue com você.")
        self.state = "entrega"

    def entrega_key(self, k):
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        rows = self.entrega_rows()
        ent = self.ent
        if k in (pygame.K_ESCAPE, pygame.K_TAB):
            self.state = "room"
        elif k in (pygame.K_UP, pygame.K_w):
            ent["idx"] = (ent["idx"] - 1) % len(rows)
        elif k in (pygame.K_DOWN, pygame.K_s):
            ent["idx"] = (ent["idx"] + 1) % len(rows)
        elif k in yes:
            r = rows[ent["idx"]]
            if r["kind"] == "dica":
                if self.money < HINT_COST:
                    ent["msg"] = "Sem Cr$ %d no bolso, sem dica." % HINT_COST
                else:
                    self.money -= HINT_COST
                    st = self.cur_step()
                    if "missao" not in self.flags:
                        ent["msg"] = "Ligue para a Central de um orelhão e receba a missão."
                    elif st:
                        ent["msg"] = INF_HINTS.get(st["id"], st["obj"])
                    else:
                        ent["msg"] = "Missões de campo concluídas. Reúna as testemunhas e procure Helen Harper."
            elif r["done"]:
                ent["msg"] = "Essa cópia já está guardada."
            elif not r["ok"]:
                ent["msg"] = "Você ainda não tem isso."
            else:
                ev, cash = REWARD[r["kind"]]
                self.delivered.add((r["kind"], r["key"]))
                self.apply(dict(evid=ev, cash=cash))
                ent["msg"] = "Cópia guardada. +%d evidências, +Cr$ %d." % (ev, cash)
                if all(x["done"] or not x["ok"] for x in self.entrega_rows() if x["kind"] != "dica") and \
                        len(self.delivered) >= 7 and "inf_full" not in self.flags:
                    self.flags.add("inf_full")
                    self.notify("Bastião guardou tudo. O dossiê está completo no esconderijo.", 5.0)

    def draw_entrega(self):
        s = self.screen
        gold = (255, 214, 120)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 4, 24, 150))
        s.blit(dim, (0, 0))
        self.panel((140, 40, 1000, 640), 248)
        self.text("ENTREGAR AO INFORMANTE", self.f_big, gold, (640, 80), center=True)
        rows = self.entrega_rows()
        for i, r in enumerate(rows):
            y = 126 + i * 44
            sel = i == self.ent["idx"]
            if sel:
                self.pix_rect((170, y - 4, 940, 38), (24, 12, 40), 4)
                self.pix_rect((174, y - 1, 932, 32), (255, 214, 120), 4)
            col = (56, 28, 24) if sel else (255, 240, 214)
            self.text(r["label"], self.f_ch, col, (196, y + 2), shadow=not sel)
            if r["kind"] == "dica":
                tag, tc = "", col
            elif r["done"]:
                tag, tc = "Guardado", (40, 150, 100) if sel else (120, 236, 180)
            elif r["ok"]:
                tag, tc = "Entregar", (150, 40, 60) if sel else (255, 214, 120)
            else:
                tag, tc = "Ainda não tem", (110, 90, 100) if sel else (150, 130, 160)
            self.text(tag, self.f_ch, tc, (1086, y + 2), right=True, shadow=not sel)
        for j, ln in enumerate(wrap(self.ent["msg"], self.f_sm, 940)[:2]):
            self.text(ln, self.f_sm, (190, 240, 255), (196, 574 + j * 28), shadow=False)
        self.text("Cima/Baixo: escolher    Enter: entregar    Esc: voltar", self.f_xs, (255, 255, 255), (640, 650), center=True)


class Game(RoomsMixin):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Agente Rosso - Operação Verdade (Rio de Janeiro, 1970)")
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))
        self.fps_clock = pygame.time.Clock()
        self.f_title = PixFont(50, 3)
        self.f_big = PixFont(26, 2)
        self.f_med = PixFont(18, 2)
        self.f_txt = PixFont(16, 2)
        self.f_ch = PixFont(15, 2)
        self.f_sm = PixFont(12, 2)
        self.f_xs = PixFont(10, 2)
        self.screen.fill((22, 10, 46))
        self.screen.blit(self.f_big.render("Carregando o Rio de Janeiro...", True, (255, 226, 150)), (W // 2 - 190, H // 2 - 14))
        pygame.display.flip()
        pygame.event.pump()

        self.frame = pygame.Surface((IW, IH)).convert()
        self.tiles = build_tiles()
        self.ground = build_ground(self.tiles)
        self.mini = build_minimap(self.tiles)
        self.glow_cache = {}
        self.build_world()
        self.hero = HERO
        self.frames, self.anchor = make_actor(HERO["p"])
        self.build_overlays()
        self.build_home()
        self.build_rooms()

        self.copa = CopaScene()
        self.title_btn = pygame.Rect(0, 0, 360, 78)
        self.title_btn.center = (640, 500)
        self.state = "title"
        self.t = 0.0
        self.menu_i = 0
        self.cam = [0.0, 0.0]
        self.intro_t = 0.0
        self.ending = None
        self.reset_play()

    # -------------------------------------------------------------- mundo
    def build_world(self):
        self.objs = []
        self.colliders = []
        self.lights = []          # (x, y, raio, cor, treme)
        r = random.Random(21)

        def add(o):
            self.objs.append(o)
            if o.col is not None:
                self.colliders.append(o.col)
            w, h = o.frames[0].get_size()
            ox, oy = o.x - w // 2, o.y - h
            for lx, ly, lr, lc, lf in o.lights:
                self.lights.append((ox + lx, oy + ly, lr, lc, lf))

        def addo(o):      # objeto da praça original: desloca para dentro do mapa novo
            o.x += OX * TS
            o.y += OY * TS
            if o.col is not None:
                o.col.move_ip(OX * TS, OY * TS)
            add(o)

        # prédios
        for kind, (tx, ty), seed in BUILDINGS:
            spr, lts = building_sprite(kind, seed)
            x, y = tx * TS, ty * TS
            addo(Obj(spr, x, y, col=pygame.Rect(x - 44, y - 18, 88, 18), shadow=(0.2, 0.3, 70), lights=lts))
        # barril em chamas, mastro, banca, caixotes
        fire_frames = barrel_fire_frames()
        self.fire = Obj(None, 31 * TS + 8, 19 * TS + 14, frames=fire_frames, fps=9,
                        col=pygame.Rect(31 * TS + 2, 19 * TS + 8, 12, 6), shadow=False,
                        lights=[(12, 12, 54, (214, 110, 36), 1), (12, 24, 70, (110, 56, 22), 1)])
        addo(self.fire)
        addo(Obj(None, 27 * TS + 8, 16 * TS + 6, frames=[outlined(f) for f in flag_frames()], fps=5,
                col=pygame.Rect(27 * TS + 4, 16 * TS, 8, 6)))
        addo(Obj(outlined(banca_sprite()), 36 * TS, 22 * TS, col=pygame.Rect(36 * TS - 20, 22 * TS - 6, 40, 6),
                lights=[(23, 24, 30, (110, 70, 24), 0)]))
        crate = outlined(crate_sprite())
        barrel = outlined(barrel_sprite())
        addo(Obj(crate, 35 * TS + 4, 24 * TS + 2, col=pygame.Rect(35 * TS - 4, 24 * TS - 4, 14, 6)))
        addo(Obj(crate, 33 * TS + 2, 24 * TS + 6))
        addo(Obj(barrel, 34 * TS + 12, 25 * TS + 2, col=pygame.Rect(34 * TS + 6, 25 * TS - 4, 12, 6)))
        # calçada: fuscas estacionados e caminhão do exército
        carcols = [(60, 130, 200), (222, 70, 60), (244, 206, 80), (96, 168, 120)]
        addo(Obj(outlined(fusca_sprite(carcols[0], True)), 11 * TS + 8, 14 * TS + 8,
                col=pygame.Rect(11 * TS - 2, 14 * TS + 2, 20, 6)))
        addo(Obj(outlined(fusca_sprite(carcols[1])), 11 * TS + 8, 17 * TS + 8,
                col=pygame.Rect(11 * TS - 2, 17 * TS + 2, 20, 6)))
        addo(Obj(outlined(fusca_sprite(carcols[2], True)), 11 * TS + 8, 25 * TS + 4,
                col=pygame.Rect(11 * TS - 2, 25 * TS - 2, 20, 6)))
        addo(Obj(outlined(truck_sprite()), 12 * TS + 4, 10 * TS + 6, col=pygame.Rect(12 * TS - 14, 10 * TS, 36, 6)))
        # carros em movimento na avenida
        bcols = ((236, 190, 50), (70, 150, 200))
        self.car_front = [outlined(fusca_sprite(c)) for c in carcols] + [outlined(onibus_sprite(c)) for c in bcols]
        self.car_back = [outlined(fusca_sprite(c, True)) for c in carcols] + [outlined(onibus_sprite(c, True)) for c in bcols]
        L1, L2 = AV0 * TS + 36, AV0 * TS + 116
        self.cars = [(L1, 0, 28, 0), (L1, 330, 28, 4), (L1, 700, 28, 2), (L1, 1000, 28, 3),
                     (L2, 150, -32, 1), (L2, 520, -32, 5), (L2, 860, -32, 0), (L2, 1100, -32, 2)]
        self.car_shadows = {}
        self.car_shadow = pygame.Surface((22, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(self.car_shadow, (30, 12, 64, 96), (0, 0, 22, 7))
        # postes de luz, bancos, canteiros, caixa de correio
        lamp = outlined(lamp_sprite())
        lamp_l = [(7, 20, 34, (170, 112, 40), 0), (22, 20, 34, (170, 112, 40), 0), (15, 52, 38, (120, 76, 28), 0)]
        lamp_pos = [(25, 15), (37, 15), (25, 24), (38, 25), (13, 8), (13, 15), (13, 24), (13, 31), (31, 24)]
        for tx, ty in lamp_pos:
            x, y = tx * TS + (10 if tx == 13 else 8), ty * TS + 14
            addo(Obj(lamp, x, y, col=pygame.Rect(x - 3, y - 4, 6, 4), shadow=(0.3, 0.5, 70), lights=lamp_l))
        bench = outlined(bench_sprite())
        for tx, ty in ((27, 24), (36, 17), (26, 19), (30, 14)):
            x, y = tx * TS + 8, ty * TS + 14
            addo(Obj(bench, x, y, col=pygame.Rect(x - 13, y - 6, 26, 6), shadow=(0.4, 0.4, 60)))
        planters = [outlined(planter_sprite(i)) for i in range(3)]
        for i, (tx, ty) in enumerate(((27, 12), (36, 13), (22, 17), (24, 22), (40, 18), (38, 29), (28, 29))):
            x, y = tx * TS + 8, ty * TS + 14
            addo(Obj(planters[i % 3], x, y, col=pygame.Rect(x - 12, y - 5, 24, 5), shadow=(0.4, 0.4, 56)))
        addo(Obj(outlined(mailbox_sprite()), 21 * TS + 8, 18 * TS + 14, col=pygame.Rect(21 * TS + 5, 18 * TS + 10, 6, 4),
                shadow=(0.4, 0.4, 56)))
        # ---------------------------------------------------------------- RIO DE JANEIRO
        npc_pts = [(d["pos"][0] * TS + 8, d["pos"][1] * TS + 14) for d in NPC_DEFS]
        big_occ = []

        def put(spr, x, y, cw=None, ch=5, **kw):
            col = pygame.Rect(int(x - cw // 2), int(y - ch), cw, ch) if cw else None
            o = Obj(spr, x, y, col=col, **kw)
            add(o)
            return o

        def near_npc_pt(x, y, rad=28):
            return any(abs(x - nx) < rad and abs(y - ny) < rad for nx, ny in npc_pts)

        # palmeiras na calçada (lado leste da avenida) e no calçadão
        palms = [outlined(palm_sprite(i)) for i in range(3)]
        for ty in range(3, MH - 5, 3):
            if any(ya - 2 <= ty <= yb + 2 for ya, yb in CROSS_ROWS):
                continue
            x = (shore(ty) + 4) * TS + 6
            y = ty * TS + 14
            add(Obj(palms[ty % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))
        for ty in range(2, MH - 1, 4):
            x, y = 23 * TS + 12, ty * TS + 14
            add(Obj(palms[(ty // 4) % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))
        # postes e bancos: calçadão, calçada, Largo e parque
        for ty in range(3, MH - 1, 6):
            x, y = 21 * TS + 8, ty * TS + 14
            add(Obj(lamp, x, y, col=pygame.Rect(x - 3, y - 4, 6, 4), shadow=(0.3, 0.5, 70), lights=lamp_l))
        for tx, ty in ((37, 4), (37, 10), (37, 14), (37, 62), (37, 68), (37, 73), (42, 17), (60, 17), (78, 17),
                       (46, 22), (82, 22), (83, 46), (62, 61), (50, 61), (36, 21), (85, 12)):
            x, y = tx * TS + (10 if tx == 37 else 8), ty * TS + 14
            add(Obj(lamp, x, y, col=pygame.Rect(x - 3, y - 4, 6, 4), shadow=(0.3, 0.5, 70), lights=lamp_l))
        for ty in (14, 26, 44, 56, 68):
            x, y = 21 * TS + 8, ty * TS + 14
            add(Obj(bench, x, y, col=pygame.Rect(x - 13, y - 6, 26, 6), shadow=(0.4, 0.4, 60)))
        for tx, ty in ((48, 17), (70, 17), (76, 23)):
            x, y = tx * TS + 8, ty * TS + 14
            add(Obj(bench, x, y, col=pygame.Rect(x - 13, y - 6, 26, 6), shadow=(0.4, 0.4, 60)))

        # ---- mar: Pão de Açúcar, ilhas e veleiros
        put(outlined(pao_acucar_sprite()), 84, 12 * TS, 150, 10, shadow=False)
        vel = [outlined(veleiro_sprite(c)) for c in ((236, 84, 70), (70, 130, 220), (250, 200, 60))]
        for i, (x, y) in enumerate(((50, 300), (96, 420), (30, 560), (120, 700), (64, 830), (100, 960),
                                    (44, 1080), (126, 250))):
            add(Obj(vel[i % 3], x, y, bob=1.6, shadow=False))
        ilha = [outlined(ilha_sprite(k)) for k in (1, 2)]
        add(Obj(ilha[0], 40, 640, shadow=False))
        add(Obj(ilha[1], 110, 900, shadow=False))
        self.glints = []
        for _ in range(320):
            gy, gx = r.uniform(0, MH * TS), r.uniform(2, 150)
            if gx < shore_px(gy) - 16 and self.tiles[min(MH - 1, int(gy // TS))][int(gx // TS)] == 6:
                self.glints.append((gx, gy, r.uniform(0, 6.28)))

        # ---- praia: guarda-sóis, quiosques, salva-vidas e vôlei
        skip_rows = BEACH_KIOSK_ROWS + (24, 48, 70, 36, 60)
        umb = [outlined(guardasol_sprite(a, b)) for a, b in (
            ((236, 84, 70), (250, 240, 230)), ((250, 200, 60), (80, 160, 220)), ((70, 170, 150), (250, 240, 230)),
            ((220, 90, 170), (250, 220, 90)), ((60, 120, 210), (250, 240, 230)))]
        for ty in range(13, MH - 2):
            if any(abs(ty - kr) < 3 for kr in skip_rows):
                continue
            for _ in range(2):
                if r.random() < 0.55:
                    x = int(r.uniform(shore_px(ty * TS) / TS + 2.2, 18.4) * TS)
                    y = ty * TS + r.randint(4, 14)
                    if near_npc_pt(x, y, 30) or self.tiles[min(ty, MH - 1)][x // TS] != 7:
                        continue
                    put(umb[r.randrange(len(umb))], x, y, 6, 4, shadow=(0.3, 0.4, 60))
        kcols = [(236, 96, 80), (70, 170, 190), (250, 190, 60), (150, 110, 210)]
        for i, kr in enumerate(BEACH_KIOSK_ROWS):
            put(outlined(quiosque_sprite(kcols[i % len(kcols)])), 19 * TS + 4, kr * TS + 12, 44, 10,
                lights=[(26, 33, 40, (150, 96, 36), 0)], shadow=(0.3, 0.4, 70))
        sv = outlined(salva_vidas_sprite())
        for row in (24, 48, 70):
            put(sv, 268, row * TS + 14, 24, 5, shadow=(0.3, 0.4, 60))
        rede = outlined(rede_volei_sprite())
        for row in (36, 60):
            y = row * TS + 14
            add(Obj(rede, 240, y, shadow=False))
            self.colliders.append(pygame.Rect(240 - 30, y - 4, 4, 4))
            self.colliders.append(pygame.Rect(240 + 26, y - 4, 4, 4))

        # ---- Cristo Redentor no Corcovado, acima do morro
        put(outlined(corcovado_sprite()), 100 * TS, 13 * TS, 100, 10, shadow=False,
            lights=[(58, 22, 44, (150, 130, 90), 0)])

        # ---- Arcos da Lapa com o bondinho no topo
        arc = outlined(arcos_sprite())
        for k in range(ARCOS_N):
            x0 = ARCOS_X0 + k * 64
            add(Obj(arc, x0 + 32, ARCOS_BASE, shadow=False))
            for a, b in ((0, 7), (25, 39), (57, 64)):
                self.colliders.append(pygame.Rect(x0 + a, ARCOS_BASE - 8, b - a, 8))
        tram = bonde_sprite()
        self.trams = [dict(r=outlined(tram), l=outlined(pygame.transform.flip(tram, True, False)),
                           x0=ARCOS_X0 + 40, x1=ARCOS_X0 + ARCOS_N * 64 - 40,
                           y=ARCOS_BASE - 86 + 12, ky=ARCOS_BASE + 1, sp=22, ph=0)]

        # ---- Largo da Carioca: Igreja, Theatro, Colombo, livraria e cinema
        lb = LARGO_BASE * TS
        spr, lts = igreja_sprite()
        put(spr, 51 * TS, lb, 100, 14, shadow=(0.2, 0.3, 70), lights=lts)
        spr, lts = teatro_sprite()
        put(spr, 68 * TS, lb, 116, 14, shadow=(0.2, 0.3, 70), lights=lts)
        for kind, cx_, seed in (("livraria", 43.5, 31), ("colombo", 59, 32), ("cinema", 76.5, 33)):
            spr, lts = building_sprite(kind, seed)
            put(spr, int(cx_ * TS), lb, 88, 18, shadow=(0.2, 0.3, 70), lights=lts)
        for tx in (46, 56, 62, 73, 79):
            x, y = tx * TS + 8, 17 * TS + 14
            add(Obj(palms[tx % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))

        # ---- Praça XV: casarões e palácios históricos do Rio, chafariz, palmeiras-imperiais e a baía
        pb = 85 * TS
        for sprf, cx_, cw_ in ((real_gabinete_sprite, 43, 84), (biblioteca_sprite, 53.5, 130),
                               (paco_imperial_sprite, 64.5, 142), (palacio_tiradentes_sprite, 76, 128)):
            spr, lts = sprf()
            put(spr, int(cx_ * TS), pb, cw_, 16, shadow=(0.2, 0.3, 70), lights=lts)
        chaf = [outlined(f) for f in chafariz_frames()]
        add(Obj(None, int(64.5 * TS), 88 * TS - 2, frames=chaf, fps=6, col=pygame.Rect(int(64.5 * TS) - 18, 88 * TS - 8, 36, 8),
                shadow=False, lights=[(23, 30, 40, (90, 130, 170), 1)]))
        for tx in (39, 47, 51, 58, 61, 68, 72, 80, 84):
            x, y = tx * TS + 8, 87 * TS + 10
            add(Obj(palms[tx % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))
        for tx in (41, 50, 62, 67, 78, 85):
            x, y = tx * TS + 8, 88 * TS + 12
            add(Obj(lamp, x, y, col=pygame.Rect(x - 3, y - 4, 6, 4), shadow=(0.3, 0.5, 70), lights=lamp_l))
        for tx in (45, 56, 74):
            x, y = tx * TS + 8, 86 * TS + 14
            add(Obj(bench, x, y, col=pygame.Rect(x - 13, y - 6, 26, 6), shadow=(0.4, 0.4, 60)))
        for i, (bx, by) in enumerate(((46, 1452), (70, 1462), (83, 1450))):
            add(Obj(vel[(i + 1) % 3], bx * TS, by, bob=1.6, shadow=False))

        # ---- Forte de Copacabana, no promontório ao sul da praia
        spr, lts = forte_sprite()
        put(spr, int(11.5 * TS), 88 * TS, 112, 16, shadow=(0.2, 0.3, 70), lights=lts)

        # ---- lojas ao longo da rua do Catete
        for i, kind in enumerate(("botequim", "mercado", "sobrado", "barbearia", "sorveteria", "pensao")):
            spr, lts = building_sprite(kind, 40 + i)
            put(spr, (41 + 7 * i) * TS, SHOPS_BASE * TS, 88, 18, shadow=(0.2, 0.3, 70), lights=lts)

        # ---- casa do Agente Rosso (porta rosa ao lado da praça)
        spr, lts = casa_sprite()
        put(spr, HOME_TILE[0] * TS, HOME_TILE[1] * TS, 88, 18, shadow=(0.2, 0.3, 70), lights=lts)

        # ---- feira livre
        fcols = (((220, 60, 60), (250, 244, 232)), ((60, 150, 90), (250, 244, 232)), ((240, 180, 50), (250, 244, 232)),
                 ((60, 110, 200), (250, 244, 232)), ((200, 80, 160), (250, 244, 232)), ((240, 130, 40), (250, 244, 232)))
        for i, fx in enumerate(FEIRA_X):
            c1, c2 = fcols[i % len(fcols)]
            put(outlined(barraca_sprite(c1, c2, r)), fx * TS + 8, 61 * TS, 34, 6, shadow=(0.4, 0.4, 56))

        # ---- campinho de pelada
        gol = outlined(gol_sprite())
        for gy in (62 * TS + 14, 73 * TS + 14):
            gx = 50 * TS
            add(Obj(gol, gx, gy, shadow=False))
            self.colliders.append(pygame.Rect(gx - 15, gy - 4, 3, 4))
            self.colliders.append(pygame.Rect(gx + 13, gy - 4, 3, 4))

        # ---- lagoa: pedalinhos e palmeiras na ciclovia
        ped = [outlined(pedalinho_sprite(c)) for c in ((240, 240, 250), (250, 190, 200), (250, 220, 120))]
        for i, (tx, ty) in enumerate(((70, 66), (76, 70), (73, 67.5), (79, 66))):
            add(Obj(ped[i % 3], int(tx * TS), int(ty * TS), bob=1.2, shadow=False))
        for a in range(10):
            x = int(LAGOA_C[0] * TS + 8 + math.cos(a * math.pi / 5) * 9 * 1.17 * TS)
            y = int(LAGOA_C[1] * TS + 8 + math.sin(a * math.pi / 5) * 5 * 1.17 * TS)
            if 0 < y < MH * TS - 4:
                add(Obj(palms[a % 3], x, y, col=pygame.Rect(x - 3, y - 4, 6, 4)))

        # ---- Rocinha (1970): barracos de madeira e zinco encostados uns nos outros, de frente para os becos
        roc_spr = [outlined(barraco70_sprite(i)) for i in range(20)]
        for k, row in enumerate(ROC_ROWS):
            if row == ROC_ROWS[-1]:
                continue                                  # o beco de baixo e so muro pichado
            blk = []                                      # trechos sem casa: escadas que chegam do norte, largo, bau
            if k > 0:
                for sx, sy0, sy1, sw, st in ROC_SEGS[k - 1]:
                    blk.append((sx - 1.75, sx + sw + 1.75))
            if row == 50:
                blk.append((0, 94.4))
            if row == 80:
                blk.append((105.2, 200))
            rr = random.Random(1970 + row)
            cx = 89.4
            while cx <= 106.8:
                if not any(a <= cx <= b for a, b in blk):
                    put(roc_spr[rr.randrange(len(roc_spr))], int(cx * TS), row * TS, 30, 6, shadow=(0.3, 0.4, 60))
                cx += 2.2 + rr.uniform(-0.05, 0.2)
        put(outlined(venda_sprite()), int(89.6 * TS), int(49.6 * TS), 40, 6, shadow=(0.3, 0.4, 60))
        put(outlined(bica_sprite()), int(91.7 * TS), int(48.2 * TS), 20, 6, shadow=(0.3, 0.4, 60))
        put(outlined(placa_sprite()), int(87.5 * TS), int(52.2 * TS), 10, 4, shadow=(0.2, 0.3, 60))

        # ---- favelas novas, pixação "FORA DITADURA", varais e pôsteres de revolução
        barr = [outlined(barraco_sprite(900 + i)) for i in range(8)]
        for i, (bx, by) in enumerate(FAVELA_NOVA):
            x, y = int(bx * TS), int(by * TS)
            put(barr[i % len(barr)], x, y, 30, 6, shadow=(0.3, 0.4, 60))
            big_occ.append(pygame.Rect(x - 20, y - 50, 40, 54))
        for i, (wx, wy, bg_) in enumerate(PIXACOES):
            spr = outlined(pixacao_sprite(i, bg_))
            x, y = int(wx * TS), int(wy * TS)
            put(spr, x, y, shadow=(0.2, 0.3, 60))
            big_occ.append(pygame.Rect(x - spr.get_width() // 2, y - spr.get_height(), spr.get_width(), spr.get_height() + 6))
        for i, (vx, vy) in enumerate(VARAIS):
            put(outlined(varal_sprite(i)), int(vx * TS), int(vy * TS), shadow=False)
        posters_sp = [outlined(rev_poster_sprite(k)) for k in range(4)]
        for i, (qx, qy) in enumerate(POSTER_SPOTS):
            put(posters_sp[i % 4], qx * TS + 8, qy * TS + 14, shadow=False)
        for i, (tile, _pos) in enumerate(SECRET_POSTERS):        # cartazes secretos: brilho amarelo bem sutil
            put(posters_sp[(i + 1) % 4], tile[0] * TS + 8, tile[1] * TS + 14, shadow=False,
                lights=[(20, 22, 22, (255, 196, 90), 1)])
        self.chest_closed = outlined(chest_sprite(False))
        self.chest_open = outlined(chest_sprite(True))
        bx_, by_ = SECRETS["bau"]["tile"]
        self.chest_obj = put(self.chest_closed, bx_ * TS + 8, by_ * TS + 14, shadow=(0.3, 0.4, 60),
                             lights=[(11, 8, 24, (255, 196, 90), 1)])

        # ---- árvores e arbustos
        trees = [outlined(tree_sprite(k, 100 + k * 7 + v)) for k in (0, 1, 3) for v in range(2)]
        ipes = [outlined(tree_sprite(2, 300 + v)) for v in range(2)]
        jacas = [outlined(tree_sprite(4, 400 + v)) for v in range(2)]
        occ = [c.inflate(8, 6) for c in self.colliders] + big_occ
        placed = []
        for ty in range(1, MH):
            for tx in range(MW):
                t = self.tiles[ty][tx]
                if t not in (2, 4):
                    continue
                if 45 <= tx <= 71 and 26 <= ty <= 51:        # a praça original continua sem árvores
                    continue
                if 87 <= tx <= 91 and ty >= 14:              # acesso ao morro
                    continue
                prob = 0.30 if t == 4 else 0.035
                if tx >= 88 and t == 4:
                    prob = 0.16
                if r.random() > prob:
                    continue
                x = tx * TS + r.randint(2, 14)
                y = ty * TS + r.randint(8, 16)
                if any(abs(x - px) < 22 and abs(y - py) < 12 for px, py in placed):
                    continue
                if near_npc_pt(x, y, 24) or any(rc.collidepoint(x, y) for rc in occ):
                    continue
                placed.append((x, y))
                roll = r.random()
                spr = r.choice(ipes) if roll < 0.08 else (r.choice(jacas) if roll < 0.16 else r.choice(trees))
                add(Obj(spr, x, y, col=pygame.Rect(x - 4, y - 5, 8, 5)))
        bush = [outlined(bush_sprite(i)) for i in range(3)]
        for i in range(170):
            tx, ty = r.randint(38, 106), r.randint(3, 73)
            if self.tiles[ty][tx] not in (2, 4) or (46 <= tx <= 64 and 29 <= ty <= 47) or (87 <= tx <= 91):
                continue
            x, y = tx * TS + 8, ty * TS + 14
            if near_npc_pt(x, y, 24):
                continue
            add(Obj(bush[i % 3], x, y, shadow=False))
        # ---- orelhões: a Central liga e passa a missão por aqui
        ph_spr = outlined(orelhao_sprite())
        self.phones = []
        for tx, ty in PHONE_TILES:
            x, y = tx * TS + 8, ty * TS + 14
            add(Obj(ph_spr, x, y, col=pygame.Rect(x - 6, y - 5, 12, 5), shadow=(0.3, 0.4, 60),
                    lights=[(14, 26, 22, (140, 80, 24), 0)]))
            self.phones.append(dict(x=x, y=y - 4))
        self.central = Voice(ph_spr)
        self.build_nav()
        # NPCs
        self.npcs = [NPC(d) for d in NPC_DEFS]
        self.npc_by_id = {n.id: n for n in self.npcs}
        for n in self.npcs:
            self.colliders.append(n.rect)
        self.npc_shadow = pygame.Surface((14, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(self.npc_shadow, (30, 12, 64, 96), (0, 0, 14, 6))
        # pedestres de fundo: calçadas, calçadão, praia, Largo, feira, campinho, lagoa e morro
        ring = [(PLAZA_C[0] + math.cos(a * math.pi / 8) * 160, PLAZA_C[1] + math.sin(a * math.pi / 8) * 96)
                for a in range(16)]
        coast = [(shore_px(y) + 16, y) for y in range(260, 1100, 60)]
        lagoa_ring = [(LAGOA_C[0] * TS + 8 + math.cos(a * math.pi / 6) * 166,
                       LAGOA_C[1] * TS + 8 + math.sin(a * math.pi / 6) * 92) for a in range(12)]
        Wd = WALKER_DEFS
        self.walkers = [
            Walker(Wd[0], [(589, 80), (589, 1150)], 15, 0),
            Walker(Wd[1], [(589, 1150), (589, 80)], 13, 0),
            Walker(Wd[2], ring, 13, 0),
            Walker(Wd[3], ring, 12, 8),
            Walker(Wd[4], ring[::-1], 11, 4),
            Walker(Wd[5], [(368, 120), (368, 1100)], 14, 0),
            Walker(Wd[6], [(368, 1100), (368, 120)], 12, 0),
            Walker(Wd[7], coast, 10, 0),
            Walker(Wd[8], coast[::-1], 9, 0),
            Walker(Wd[9], coast, 8, 6),
            Walker(Wd[1], [(700, 262), (1200, 262)], 12, 0),
            Walker(Wd[3], [(1230, 282), (720, 282)], 11, 0),
            Walker(Wd[4], [(700, 104), (1380, 104)], 13, 0),
            Walker(Wd[0], [(1336, 160), (1336, 930)], 12, 0),
            Walker(Wd[2], [(660, 922), (1300, 922)], 12, 0),
            Walker(Wd[6], [(660, 992), (1040, 992)], 10, 0),
            Walker(Wd[10], [(730, 1030), (850, 1030), (850, 1150), (730, 1150)], 24, 0),
            Walker(Wd[11], [(850, 1150), (730, 1150), (730, 1030), (850, 1030)], 26, 1),
            Walker(Wd[10], lagoa_ring, 10, 0),
            Walker(Wd[8], lagoa_ring[::-1], 10, 6),
        ] + [Walker(Wd[(3 * i + 1) % len(Wd)], lp, 11 + i % 3 * 2, i) for i, lp in enumerate(ROC_LOOPS)]
        # partículas: pétalas e papéis levados pelo vento
        self.motes = [[r.random() * IW, r.random() * IH, r.uniform(3, 9), r.uniform(0, 6.28), r.randrange(3)]
                      for _ in range(46)]

    def build_overlays(self):
        self.vig = pygame.Surface((IW, IH), pygame.SRCALPHA)
        for y in range(IH):
            for x in range(IW):
                dx, dy = (x - IW / 2) / (IW / 2), (y - IH / 2) / (IH / 2)
                d = math.sqrt(dx * dx * 0.8 + dy * dy)
                a = int(clamp((d - 0.6) * 240, 0, 160))
                if a:
                    self.vig.set_at((x, y), (36, 12, 64, a))
        self.grad = pygame.Surface((IW, IH), pygame.SRCALPHA)
        for y in range(IH):
            k = 1.0 - y / float(IH)
            self.grad.fill((90, 40, 130, int(46 * k * k)), (0, y, IW, 1))
        self.tint = pygame.Surface((IW, IH))
        self.tint.fill((252, 238, 238))
        # marcadores das missões: itens e pontos de ação
        self.mk_item = {}
        for key, it in ITEMS.items():
            m = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.rect(m, tone(it["cor"], -.3), (0, 1, 10, 9))
            pygame.draw.rect(m, it["cor"], (0, 0, 10, 7))
            pygame.draw.rect(m, tone(it["cor"], .6), (1, 1, 4, 2))
            pygame.draw.rect(m, (255, 255, 255), (6, 3, 2, 2))
            self.mk_item[key] = outlined(m)
        m = pygame.Surface((14, 9), pygame.SRCALPHA)
        pygame.draw.ellipse(m, (255, 214, 110), (0, 0, 14, 9), 2)
        pygame.draw.ellipse(m, (255, 244, 200), (4, 3, 6, 3))
        self.mk_spot = outlined(m)

    def reset_play(self):
        self.px, self.py = (26.0 + OX) * TS, (21.0 + OY) * TS
        self.dir = "right"
        self.anim = 0.0
        self.moving = False
        self.evid = 10
        self.susp = 10
        self.flags = set()
        self.dl = None
        for n in self.npcs:
            n.talked = False
            n.reset()
        self.pending_call = None
        self.call_due = None
        self.done_calls = set()
        self.ring_phone = None
        self.ring_t = 0.0
        self.toast = None
        self.watch_cd = 0.0
        self.chase_cd = 14.0
        self.clock = 0.0            # tempo de operação (máximo 15 min)
        self.warned = set()
        self.step_i = 0             # passo atual da cadeia de missões
        self.route = None           # linha de ação escolhida (trava até o final)
        self.secrets = set()        # segredos desvendados
        self.posters_read = set()   # cartazes secretos já lidos (posição do dígito)
        self.listen = 0.0           # progresso da escuta do grampo
        self.rumor_i = 0
        self._lp = None
        if getattr(self, "chest_obj", None):
            self.chest_obj.frames = [self.chest_closed]
        self.pack = []              # mochila
        self.done_steps = set()
        self.puz = None
        self.day = 1                # contador de dias (cada noite dormida passa um dia)
        self.money = 0              # dinheiro no bolso (Cr$)
        self.bank = START_BANK      # dinheiro guardado no mural, em casa
        self.stash = []             # itens guardados no mural
        self.hx, self.hy, self.hdir = 50.0, 112.0, "down"
        self.hanim, self.hmoving = 0.0, False
        self.home_sky = "dusk"
        self.su = dict(col=0, row=0, msg="")
        self.cfm = None
        self.sleepfx = None
        self.pause_from = "play"
        self.rk = None              # interior em que o agente está (None = rua)
        self.delivered = set()      # cópias já entregues ao informante
        self.ent = dict(idx=0, msg="")
        for n in getattr(self, 'room_npcs', []):
            n.talked = False
            n.talking = False
        self.cam = [self.px - IW / 2, self.py - IH / 2]

    # --------------------------------------------------------- colisão
    def blocked(self, rect):
        if rect.left < 0 or rect.top < 0 or rect.right > MW * TS or rect.bottom > MH * TS:
            return True
        for qx, qy in ((rect.left, rect.top), (rect.right - 1, rect.top),
                       (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1)):
            if self.tiles[qy // TS][qx // TS] in BLOCK_T:
                return True
        return rect.collidelist(self.colliders) != -1

    # ----------------------------------------------------------- diálogo
    def fmt(self, s):
        return s.format(nome=self.hero["nome"])

    def evidence_count(self):
        return sum(1 for k in TESTIMONIES if k in self.flags)

    def ready(self):
        return self.evidence_count() >= NEEDED and self.chain_done()

    def start_dialogue(self, npc):
        did = npc.dlg
        tree = DLG[did]
        if did == "helen":
            if self.ready() and "entrega" in self.flags:
                key = "start"
            elif self.ready():
                key = "semcontato"
            else:
                key = "wait"
        elif did == "mario":
            key = "start"
            if "mario_ok" in self.flags:
                st = self.cur_step()
                key = ("dica_" + st["id"]) if st else "dica_fim"
                if key not in tree:
                    key = "again"
        else:
            key = "again" if npc.talked else "start"
        npc.face = {"left": "right", "right": "left", "up": "down", "down": "up"}[self.dir]
        npc.talking = True
        self.dl = dict(npc=npc, tree=tree, key=key, shown=0.0, idx=0, node=None)
        self.enter_node(key)
        self.state = "dialogue"

    def apply(self, fx):
        for k, v in fx.items():
            if k == "evid":
                self.evid = clamp(self.evid + v, 0, 100)
            elif k == "susp":
                self.susp = clamp(self.susp + v, 0, 100)
            elif k == "cash":
                self.money += v
            elif k == "route":
                self.route = v

    def enter_node(self, key):
        dl = self.dl
        node = dl["tree"][key]
        dl["key"] = key
        dl["node"] = node
        dl["shown"] = 0.0
        dl["idx"] = 0
        self.apply(node["fx"])
        if node["flag"]:
            self.flags.add(node["flag"])
        dl["text"] = self.fmt(node["text"])
        dl["choices"] = None
        if node["ch"]:
            dl["choices"] = [dict(text=self.fmt(c["text"]), nxt=c["nxt"], fx=c["fx"]) for c in node["ch"]]
        dl["speaker"] = node["sp"]

    def dialogue_advance(self):
        dl = self.dl
        full = len(dl["text"])
        if dl["shown"] < full:
            dl["shown"] = float(full)
            return
        if dl["choices"]:
            c = dl["choices"][dl["idx"]]
            self.apply(c["fx"])
            self.enter_node(c["nxt"])
            return
        node = dl["node"]
        if node["nxt"]:
            self.enter_node(node["nxt"])
            return
        # fim da conversa
        scene = dl.get("scene")
        if not scene and dl["key"] not in ("wait", "semcontato") and not dl["key"].startswith("dica"):
            dl["npc"].talked = True
        dl["npc"].talking = False
        end = node["end"]
        self.dl = None
        if scene and dl.get("step_done"):
            self.complete_step(dl["step_done"])
        if self.susp >= 100:
            end = "capturado"
        if end:
            self.begin_ending(end)
        elif self.dl is None:
            if self.rk and dl["npc"].id == "informante":
                self.open_entrega()
            else:
                self.state = "room" if self.rk else "play"

    def begin_ending(self, outcome):
        n = self.evidence_count()
        key = outcome
        if self.route and (self.route + "_" + outcome) in ENDINGS:
            key = self.route + "_" + outcome
        if len(self.secrets) >= len(SECRETS) and outcome in ("denuncia", "partes", "panfleto"):
            key = "resistencia"
        txt = ENDINGS[key] + "\n\n"
        if self.route:
            txt += "Linha seguida: %s. Você documentou %d de 6 grandes abusos do regime e cumpriu %d de %d etapas dela. " % (
                ROUTES[self.route]["nome"], n, self.missions_done(), self.missions_total())
        else:
            txt += "Você documentou %d de 6 grandes abusos do regime, mas não chegou a escolher uma linha de ação. " % n
        txt += "Segredos desvendados: %d de %d. " % (len(self.secrets), len(SECRETS))
        if outcome != "capturado":
            if self.evid >= 80:
                txt += "As provas eram sólidas demais para serem ignoradas. "
            elif self.evid < 40:
                txt += "Mas as provas eram frágeis, e o regime pôde negar quase tudo. "
            if self.susp >= 60:
                txt += "O Agente Rosso precisou sumir do país por um tempo."
            else:
                txt += "O Agente Rosso voltou às sombras sem ser notado."
        txt += "\n\n" + EPILOGO
        self.ending = dict(text=txt, t=0.0, clock=self.clock)
        self.state = "ending"

    # --------------------------------------------------------- objetivos
    def objective(self):
        c = self.evidence_count()
        if "missao" not in self.flags:
            return "Vá a um orelhão e ligue para a Central"
        if self.pending_call:
            return "Atenda o orelhão que está tocando"
        st = self.cur_step()
        if st:
            return st["obj"]
        if c < NEEDED:
            return "Encontre as testemunhas e reúna provas (%d/%d)" % (c, NEEDED)
        if "entrega" not in self.flags:
            return "Aguarde a ligação da Central no orelhão (%d/6 provas)" % c
        return "Entregue o dossiê à correspondente Helen Harper (%d/6 provas)" % c

    # ------------------------------------------------ missões de campo
    def steps(self):
        """Cadeia ativa: contato, escolha da linha e, depois da escolha, só os passos daquela linha."""
        ids = ["mario", "rota"] + (ROUTES[self.route]["steps"] if self.route else [])
        return [STEP_DEFS[i] for i in ids]

    def cur_step(self):
        sl = self.steps()
        return sl[self.step_i] if self.step_i < len(sl) else None

    def chain_done(self):
        return self.route is not None and self.step_i >= len(self.steps())

    def missions_done(self):
        if not self.route:
            return 0
        return sum(1 for k in ROUTES[self.route]["steps"] if k in self.done_steps)

    def missions_total(self):
        return len(ROUTES[self.route]["steps"]) if self.route else 0

    def fmt_time(self, secs):
        secs = int(max(0, secs))
        return "%d:%02d" % (secs // 60, secs % 60)

    def near_tile(self, tile):
        x, y = tile[0] * TS + 8, tile[1] * TS + 14
        return math.hypot(x - self.px, y - self.py) < 28

    def step_target(self):
        """Posição do objetivo atual da cadeia de missões (para a seta e o minimapa)."""
        if "missao" not in self.flags or self.pending_call:
            return None
        st = self.cur_step()
        if not st:
            return None
        if "npc" in st:
            n = self.npc_by_id[st["npc"]]
            return n.x, n.y - 10, st["label"]
        if "tile" in st:
            return st["tile"][0] * TS + 8, st["tile"][1] * TS + 4, st["label"]
        return None

    def sync_steps(self):
        """Passos que dependem de uma conversa (flag) se completam sozinhos."""
        for _ in range(len(MISSION_STEPS)):
            st = self.cur_step()
            if st and st["k"] == "flag" and st["flag"] in self.flags:
                self.complete_step(st["id"])
            else:
                break

    def complete_step(self, sid):
        st = self.cur_step()
        if not st or st["id"] != sid:
            return
        if st.get("take") in self.pack:
            self.pack.remove(st["take"])
        if st.get("give") and st["give"] not in self.pack:
            self.pack.append(st["give"])
        self.apply(st.get("fx", {}))
        self.done_steps.add(sid)
        self.step_i += 1
        if st.get("msg"):
            self.notify(st["msg"], 5.0)
        if st.get("after"):
            self.start_scene(self.npc_by_id[st["after"][0]], st["after"][1], None)
        self.sync_steps()

    def try_mission_interact(self):
        if "missao" not in self.flags or self.pending_call:
            return False
        st = self.cur_step()
        if not st:
            return False
        k = st["k"]
        if k in ("pickup", "puzzle"):
            if self.near_tile(st["tile"]):
                self.step_interact(st)
                return True
        elif k == "deliver" and st["item"] in self.pack:
            npc = self.npc_by_id.get(st.get("npc") or st.get("scene_npc"))
            if "npc" in st:
                ok = npc is not None and math.hypot(npc.x - self.px, npc.y - self.py) < 26
            else:
                ok = self.near_tile(st["tile"])
            if ok and npc is not None:
                self.start_scene(npc, st["scene"], st["id"])
                return True
        return False

    def step_interact(self, st):
        if st["k"] == "pickup" and st["item"] not in self.pack and st["item"] not in self.stash:
            self.pack.append(st["item"])
            self.notify("Você pegou: %s" % ITEMS[st["item"]]["nome"], 3.5)
        if st.get("puzzle"):
            self.open_puzzle(st["puzzle"], st["id"])
        else:
            self.complete_step(st["id"])

    def start_scene(self, npc, key, step_done):
        npc.talking = True
        self.dl = dict(npc=npc, tree=SCENES[key], key="start", shown=0.0, idx=0, node=None,
                       scene=True, step_done=step_done)
        self.enter_node("start")
        self.state = "dialogue"

    def time_up(self):
        if self.state in ("ending", "title", "intro"):
            return
        if self.dl:
            self.dl["npc"].talking = False
        self.dl = None
        self.puz = None
        self.begin_ending("prazo")

    # ---------------------------------------------------------------- puzzles
    def open_puzzle(self, kind, step_id, **extra):
        rnd = random.Random()
        p = dict(kind=kind, step=step_id, t=0.0, msg="", msg_t=0.0, shake=0.0)
        if kind == "cifra":
            p["shift"] = rnd.randint(3, 9)
            p["guess"] = rnd.choice([g for g in range(26) if g != p["shift"]])
        elif kind == "toques":
            p.update(seq=[rnd.randrange(4) for _ in range(5)], phase="show", i=0, pad=-1, timer=1.0,
                     inp=[], lit={})
        elif kind == "enigma":
            p.update(q=0, sel=0, perm=self.enigma_perms())
        else:
            p.update(dig=[0, 0, 0, 0], cur=0, tries=0)
        p.update(extra)
        self.puz = p
        self.state = "puzzle"

    def puz_fail(self, msg, susp=2):
        p = self.puz
        p["msg"], p["msg_t"], p["shake"] = msg, 2.4, 0.4
        self.apply(dict(susp=susp))

    def puz_success(self):
        sid = self.puz["step"]
        self.puz = None
        self.state = "play"
        if isinstance(sid, str) and sid.startswith("sec_"):
            self.secret_done(sid[4:])
        else:
            self.complete_step(sid)

    def puz_update(self, dt):
        p = self.puz
        if not p:
            return
        p["t"] += dt
        p["msg_t"] = max(0.0, p["msg_t"] - dt)
        p["shake"] = max(0.0, p["shake"] - dt)
        if p["kind"] != "toques":
            return
        for k in list(p["lit"]):
            p["lit"][k] -= dt
            if p["lit"][k] <= 0:
                del p["lit"][k]
        if p["phase"] == "show":
            p["timer"] -= dt
            if p["timer"] <= 0:
                if p["pad"] >= 0:
                    p["pad"] = -1
                    p["timer"] = 0.25
                    p["i"] += 1
                    if p["i"] >= len(p["seq"]):
                        p["phase"], p["inp"] = "input", []
                elif p["i"] < len(p["seq"]):
                    p["pad"] = p["seq"][p["i"]]
                    p["timer"] = 0.5

    def puz_key(self, k):
        p = self.puz
        if not p:
            self.state = "play"
            return
        if k == pygame.K_ESCAPE:
            self.puz = None
            self.state = "play"
            self.notify("Você se afastou do esconderijo.", 2.5)
            return
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        left, right = (pygame.K_LEFT, pygame.K_a), (pygame.K_RIGHT, pygame.K_d)
        up, dn = (pygame.K_UP, pygame.K_w), (pygame.K_DOWN, pygame.K_s)
        if p["kind"] == "cifra":
            if k in left:
                p["guess"] = (p["guess"] - 1) % 26
            elif k in right:
                p["guess"] = (p["guess"] + 1) % 26
            elif k in yes:
                if p["guess"] == p["shift"]:
                    self.puz_success()
                else:
                    self.puz_fail("Isso não faz sentido. O bilhete continua embaralhado.")
        elif p["kind"] == "enigma":
            q_, shown, ok = self.enigma_cur(p)
            pick = None
            if pygame.K_1 <= k <= pygame.K_4:
                p["sel"] = pick = k - pygame.K_1
            elif k in up:
                p["sel"] = (p["sel"] - 1) % 4
            elif k in dn:
                p["sel"] = (p["sel"] + 1) % 4
            elif k in yes:
                pick = p["sel"]
            if pick is not None:
                if pick == ok:
                    p["q"] += 1
                    p["sel"] = 0
                    if p["q"] >= len(ENIGMAS):
                        self.puz_success()
                    else:
                        p["msg"], p["msg_t"] = "Certo! A tinta escorre e revela a próxima pergunta.", 2.2
                else:
                    p.update(q=0, sel=0, perm=self.enigma_perms())
                    self.puz_fail("Errado! A tinta escorre e o muro recomeça do início.", 3)
        elif p["kind"] == "toques":
            if p["phase"] == "input" and pygame.K_1 <= k <= pygame.K_4:
                i = k - pygame.K_1
                p["lit"][i] = 0.25
                if i != p["seq"][len(p["inp"])]:
                    self.puz_fail("Tom errado! A linha chiou: ouça de novo.")
                    p.update(phase="show", i=0, pad=-1, timer=1.2, inp=[])
                    return
                p["inp"].append(i)
                if len(p["inp"]) == len(p["seq"]):
                    self.puz_success()
        else:
            if k in left:
                p["cur"] = (p["cur"] - 1) % 4
            elif k in right:
                p["cur"] = (p["cur"] + 1) % 4
            elif k in up:
                p["dig"][p["cur"]] = (p["dig"][p["cur"]] + 1) % 10
            elif k in dn:
                p["dig"][p["cur"]] = (p["dig"][p["cur"]] - 1) % 10
            elif pygame.K_0 <= k <= pygame.K_9:
                p["dig"][p["cur"]] = k - pygame.K_0
                p["cur"] = min(3, p["cur"] + 1)
            elif k in yes:
                if tuple(p["dig"]) == tuple(p.get("code", COFRE_CODE)):
                    self.puz_success()
                else:
                    p["tries"] += 1
                    self.puz_fail("A porta não cede. Combinação errada.")

    def draw_puzzle(self):
        p = self.puz
        if not p:
            return
        s = self.screen
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 4, 24, 160))
        s.blit(dim, (0, 0))
        ox = int(math.sin(self.t * 70) * 6) if p["shake"] > 0 else 0
        cx = 640 + ox
        self.panel((190 + ox, 90, 900, 540), 248)
        gold, soft = (255, 214, 120), (240, 236, 250)
        kind = p["kind"]
        if kind == "cifra":
            self.text("BILHETE CIFRADO", self.f_big, gold, (cx, 134), center=True)
            y = 176
            for ln in wrap("Cada letra foi trocada por outra, sempre com o mesmo deslocamento. "
                           "Gire o disco até o texto fazer sentido.", self.f_sm, 780):
                self.text(ln, self.f_sm, soft, (cx, y), center=True, shadow=False)
                y += 24
            enc = caesar(CIFRA_TEXT, p["shift"])
            dec = caesar(enc, -p["guess"])
            self.text("Bilhete interceptado:", self.f_sm, (150, 230, 210), (cx, 244), center=True, shadow=False)
            for i, ln in enumerate(textwrap.wrap(enc, 24)):
                self.text(ln, self.f_big, gold, (cx, 282 + i * 38), center=True)
            self.text("Disco de deslocamento", self.f_sm, (150, 230, 210), (cx, 372), center=True, shadow=False)
            self.text("<   %02d   >" % p["guess"], self.f_big, (120, 236, 196), (cx, 406), center=True)
            self.text("Lido com este disco:", self.f_sm, (150, 230, 210), (cx, 450), center=True, shadow=False)
            for i, ln in enumerate(textwrap.wrap(dec, 24)):
                self.text(ln, self.f_big, (255, 248, 232), (cx, 486 + i * 36), center=True)
            hint = "Setas: girar o disco     Enter: confirmar     Esc: sair"
        elif kind == "enigma":
            q_, shown, _ok = self.enigma_cur(p)
            self.text("ENIGMA DO MURO", self.f_big, gold, (cx, 134), center=True)
            self.text("Acerte as três perguntas seguidas. Um erro e a tinta escorre: recomeça tudo.", self.f_sm, soft,
                      (cx, 180), center=True, shadow=False)
            self.text("Pergunta %d de %d" % (p["q"] + 1, len(ENIGMAS)), self.f_sm, (150, 230, 210), (cx, 214),
                      center=True, shadow=False)
            y = 246
            for ln in wrap(q_, self.f_med, 780):
                self.text(ln, self.f_med, (255, 248, 232), (cx, y), center=True, shadow=False)
                y += 36
            y = max(y + 14, 346)
            for i, o in enumerate(shown):
                sel = i == p["sel"]
                self.pix_rect((cx - 300, y + i * 52 - 4, 600, 44), gold if sel else (24, 12, 40), 4)
                self.pix_rect((cx - 296, y + i * 52, 592, 36), (60, 36, 96) if sel else (28, 16, 48), 4)
                self.text("%d   %s" % (i + 1, o), self.f_txt, (255, 244, 220), (cx - 270, y + i * 52 + 6), shadow=False)
            hint = "1-4 ou setas + Enter: responder     Esc: sair"
        elif kind == "toques":
            self.text("CÓDIGO DE TOQUES", self.f_big, gold, (cx, 134), center=True)
            msg = ("Ouça a sequência de tons e memorize." if p["phase"] == "show"
                   else "Sua vez: repita a sequência com as teclas 1, 2, 3 e 4.")
            self.text(msg, self.f_med, soft, (cx, 190), center=True, shadow=False)
            base = [(190, 60, 76), (226, 184, 60), (64, 170, 108), (70, 124, 214)]
            for i in range(4):
                x = cx - 260 + i * 136
                lit = p["pad"] == i or i in p["lit"]
                col = tone(base[i], .55) if lit else tone(base[i], -.35)
                self.pix_rect((x - 4, 246, 120, 120), (255, 244, 220) if lit else (24, 12, 40), 4)
                self.pix_rect((x, 250, 112, 112), col, 4)
                self.text(str(i + 1), self.f_big, (255, 248, 232), (x + 56, 306), center=True)
            n = len(p["seq"])
            for i in range(n):
                done = i < len(p["inp"])
                pygame.draw.rect(s, (24, 12, 40), (cx - n * 22 + i * 44, 416, 30, 30))
                pygame.draw.rect(s, (120, 236, 196) if done else (70, 52, 96), (cx - n * 22 + i * 44 + 3, 419, 24, 24))
            hint = "Teclas 1-4: repetir os tons     Esc: sair"
        else:
            self.text(p.get("title", "COFRE DA SACRISTIA"), self.f_big, gold, (cx, 134), center=True)
            self.text(p.get("sub", "Quatro rodas numeradas. A senha é uma data: dia e mês."), self.f_sm, soft,
                      (cx, 184), center=True, shadow=False)
            for i in range(4):
                x = cx - 230 + i * 120
                sel = i == p["cur"]
                self.pix_rect((x - 6, 226, 112, 142), gold if sel else (24, 12, 40), 4)
                self.pix_rect((x, 232, 100, 130), (28, 16, 48), 4)
                self.text(str(p["dig"][i]), self.f_title, (255, 244, 220), (x + 50, 297), center=True, shadow=False)
                if sel:
                    pygame.draw.polygon(s, gold, [(x + 38, 222), (x + 62, 222), (x + 50, 208)])
                    pygame.draw.polygon(s, gold, [(x + 38, 372), (x + 62, 372), (x + 50, 386)])
            if p.get("bau"):
                clue = self.bau_clue()
            elif "cida" in self.flags:
                clue = "Pista de Dona Cida: 'Escrevi atrás da foto o dia em que meu Paulo sumiu: 15 de março.'"
            else:
                clue = "Sem pista ainda: Dona Cida guardou a data em que o filho desapareceu. Fale com ela."
            if p["tries"] >= 3:
                clue += "  Dica do Prof. Mário: dia e mês, nessa ordem."
            y = 410
            for ln in wrap(clue, self.f_ch, 800):
                self.text(ln, self.f_ch, (150, 230, 210), (cx, y), center=True, shadow=False)
                y += 28
            hint = "Setas: escolher e mudar     0-9: digitar     Enter: abrir     Esc: sair"
        if p["msg_t"] > 0:
            self.text(p["msg"], self.f_med, (255, 130, 160), (cx, 566), center=True)
        self.text(hint, self.f_xs, gold, (cx, 604), center=True, shadow=False)

    # ------------------------------------------------- navegação dos NPCs
    def build_nav(self):
        """Grade de 8 px com as células por onde um NPC pode andar (só obstáculos fixos)."""
        CS = 8
        nw, nh = MW * TS // CS, MH * TS // CS
        free = [[True] * nw for _ in range(nh)]
        for cy in range(nh):
            y = cy * CS + CS // 2
            for cx in range(nw):
                x = cx * CS + CS // 2
                if x < 8 or y < 8 or x > MW * TS - 8 or y > MH * TS - 8:
                    free[cy][cx] = False
                    continue
                for qx, qy in ((x - 5, y - 5), (x + 4, y - 5), (x - 5, y), (x + 4, y)):
                    if self.tiles[qy // TS][qx // TS] in BLOCK_T:
                        free[cy][cx] = False
                        break
        for c in self.colliders:
            x0, x1 = (c.left - 5) // CS, (c.right + 4) // CS
            y0, y1 = c.top // CS, (c.bottom + 4) // CS
            for cy in range(max(0, y0), min(nh, y1 + 1)):
                for cx in range(max(0, x0), min(nw, x1 + 1)):
                    x, y = cx * CS + CS // 2, cy * CS + CS // 2
                    if c.left - 5 < x < c.right + 5 and c.top < y < c.bottom + 5:
                        free[cy][cx] = False
        self.nav, self.nav_w, self.nav_h = free, nw, nh

    def cell_free(self, x, y):
        cx, cy = int(x) // 8, int(y) // 8
        return 0 <= cx < self.nav_w and 0 <= cy < self.nav_h and self.nav[cy][cx]

    def find_path(self, a, b):
        """A* na grade de navegação; devolve a lista de pontos (px) só com as curvas."""
        import heapq
        CS = 8
        nw, nh, free = self.nav_w, self.nav_h, self.nav

        def cell(p):
            return (min(nw - 1, max(0, int(p[0]) // CS)), min(nh - 1, max(0, int(p[1]) // CS)))

        def nearest(c):
            if free[c[1]][c[0]]:
                return c
            for r in range(1, 9):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        x, y = c[0] + dx, c[1] + dy
                        if 0 <= x < nw and 0 <= y < nh and free[y][x]:
                            return (x, y)
            return None

        s, e = nearest(cell(a)), nearest(cell(b))
        if s is None or e is None:
            return []
        openh = [(0.0, 0.0, s)]
        came = {s: None}
        gs = {s: 0.0}
        while openh:
            _, gc, cur = heapq.heappop(openh)
            if cur == e:
                break
            if gc > gs[cur]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cur[0] + dx, cur[1] + dy
                if not (0 <= nx < nw and 0 <= ny < nh) or not free[ny][nx]:
                    continue
                if dx and dy and not (free[cur[1]][nx] and free[ny][cur[0]]):
                    continue
                ng = gc + (1.414 if dx and dy else 1.0)
                if ng < gs.get((nx, ny), 1e9):
                    gs[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    ddx, ddy = abs(nx - e[0]), abs(ny - e[1])
                    heapq.heappush(openh, (ng + max(ddx, ddy) + 0.414 * min(ddx, ddy), ng, (nx, ny)))
        if e not in came:
            return []
        cells = []
        c = e
        while c is not None:
            cells.append(c)
            c = came[c]
        cells.reverse()
        pts = []
        for i, c in enumerate(cells):
            if 0 < i < len(cells) - 1:
                d1 = (c[0] - cells[i - 1][0], c[1] - cells[i - 1][1])
                d2 = (cells[i + 1][0] - c[0], cells[i + 1][1] - c[1])
                if d1 == d2:
                    continue
            pts.append((c[0] * CS + CS // 2, c[1] * CS + CS // 2))
        return pts

    # -------------------------------------------- orelhão e teia de eventos
    def notify(self, text, dur=4.5):
        self.toast = [text, dur]

    def gate_msg(self, n):
        """Por que a testemunha ainda não fala com o agente (None = pode falar)."""
        if not n.quest or n.dlg == "helen":
            return None
        if "missao" not in self.flags:
            return "Ligue primeiro para a Central, de um orelhão, e receba a missão."
        req = NPC_REQ.get(n.id)
        if req and req not in self.flags and not (n.id == "dom" and "dom_ok" in self.flags):
            return "%s só fala com quem for indicado por %s." % (n.name, NPC_NAMES[req])
        return None

    def npc_marker(self, n):
        if not n.quest or n.talked:
            return False
        if n.dlg == "helen":
            return self.ready() and "entrega" in self.flags
        return self.gate_msg(n) is None

    def near_phone(self):
        best, bd = None, 30.0
        for p in self.phones:
            d = math.hypot(p["x"] - self.px, p["y"] - self.py)
            if d < bd:
                best, bd = p, d
        return best

    # ------------------------------------------------------------ segredos
    def bau_clue(self):
        if not self.posters_read:
            return "Quatro rodas numeradas. Ninguém te passou a combinação: cartazes da resistência guardam os números."
        got = " ".join(str(SECRET_CODE[i]) if i in self.posters_read else "?" for i in range(4))
        return "Números lidos nos cartazes: %s   (dia e mês, nessa ordem)" % got

    def rumor_text(self):
        left = [k for k in ("bau", "escuta", "enigma") if k not in self.secrets]
        if not left:
            return "A rede não ouviu mais boato nenhum, Rosso. Você já desvendou todos os segredos."
        self.rumor_i += 1
        return RUMORS[left[self.rumor_i % len(left)]]

    def secret_near(self):
        out = [t for t, _ in SECRET_POSTERS]
        out += [sd["tile"] for k, sd in SECRETS.items()]
        return [t for t in out if math.hypot(t[0] * TS + 8 - self.px, t[1] * TS + 14 - self.py) < 44]

    def try_secret_interact(self):
        if self.rk:
            return False
        for tile, pos in SECRET_POSTERS:
            if self.near_tile(tile):
                self.posters_read.add(pos)
                txt = "Cartaz da resistência: em tinta vermelha, o número %d é %d. (%d/4)" % (
                    pos + 1, SECRET_CODE[pos], len(self.posters_read))
                if len(self.posters_read) == 4:
                    txt += " Os quatro formam uma data. Algum baú no alto do morro espera por ela."
                self.notify(txt, 6.0)
                return True
        for sid, sd in SECRETS.items():
            if not self.near_tile(sd["tile"]):
                continue
            if sid in self.secrets:
                self.notify("Você já desvendou este segredo.", 3.0)
                return True
            if sid == "bau":
                self.open_puzzle("cofre", "sec_bau", bau=True, code=SECRET_CODE, title="BAÚ DO ALTO DO MORRO",
                                 sub="Quatro rodas numeradas. Os números dos cartazes formam a combinação.")
            elif sid == "enigma":
                self.open_puzzle("enigma", "sec_enigma")
            else:
                self.notify("Fique parado e segure E para escutar. Se um policial chegar perto, o chiado estraga tudo.", 5.0)
            return True
        return False

    def secret_done(self, sid):
        sd = SECRETS[sid]
        self.secrets.add(sid)
        if sd["item"] not in self.pack:
            self.pack.append(sd["item"])
        self.apply(sd["fx"])
        txt = sd["msg"]
        if sid == "bau" and getattr(self, "chest_obj", None):
            self.chest_obj.frames = [self.chest_open]
        if len(self.secrets) == len(SECRETS):
            txt += " Todos os segredos! Um final secreto espera por você."
        self.notify(txt, 7.0)

    def update_listen(self, dt):
        sd = SECRETS["escuta"]
        if "escuta" in self.secrets:
            self.listen = 0.0
            return
        keys = pygame.key.get_pressed()
        pos = (round(self.px, 1), round(self.py, 1))
        moved = self._lp is not None and pos != self._lp
        self._lp = pos
        cop = any(math.hypot(c.x - self.px, c.y - self.py) < 90
                  for c in (self.npc_by_id.get("brandao"), self.npc_by_id.get("osmar")) if c is not None)
        if self.near_tile(sd["tile"]) and keys[pygame.K_e] and not moved:
            if cop:
                if self.listen > 0:
                    self.notify("Um policial se aproximou! O chiado denunciou você.", 3.0)
                self.listen = 0.0
                self.susp = clamp(self.susp + 6 * dt, 0, 100)
            else:
                self.listen += dt
                if self.listen >= ESCUTA_T:
                    self.listen = 0.0
                    self.secret_done("escuta")
        else:
            self.listen = max(0.0, self.listen - dt * 2)

    def enigma_perms(self):
        perms = []
        for _q, opts, _a in ENIGMAS:
            p_ = list(range(len(opts)))
            random.shuffle(p_)
            perms.append(p_)
        return perms

    def enigma_cur(self, p):
        q, opts, ans = ENIGMAS[p["q"]]
        perm = p["perm"][p["q"]]
        return q, [opts[i] for i in perm], perm.index(ans)

    def try_interact(self):
        if self.try_mission_interact():
            return
        if self.try_secret_interact():
            return
        if self.near_home_door():
            self.enter_home()
            return
        rk = self.near_room_door()
        if rk:
            self.enter_room(rk)
            return
        n, ph = self.near_npc(), self.near_phone()
        dn = math.hypot(n.x - self.px, n.y - self.py) if n else 1e9
        dp = math.hypot(ph["x"] - self.px, ph["y"] - self.py) if ph else 1e9
        if ph and dp <= dn:
            self.start_call()
        elif n:
            msg = self.gate_msg(n)
            if msg:
                self.notify(msg)
            else:
                self.start_dialogue(n)

    # ------------------------------------------------------- casa do agente
    def build_home(self):
        self.home_bg, self.home_win = home_room_surfaces()
        self.home_table = outlined(home_table_sprite())
        self.home_plant = outlined(home_plant_sprite())
        # cama, mesa e vaso bloqueiam a passagem
        self.home_cols = [pygame.Rect(236, 94, 68, 18), pygame.Rect(36, 124, 50, 10), pygame.Rect(287, 164, 14, 8)]
        self.home_beam = {}
        for sky, col in (("dusk", (255, 170, 120, 46)), ("dawn", (200, 226, 255, 54))):
            b = pygame.Surface((IW, IH), pygame.SRCALPHA)
            pygame.draw.polygon(b, col, [(182, 112), (230, 112), (214, 158), (150, 158)])
            self.home_beam[sky] = b

    def near_home_door(self):
        return math.hypot(HOME_DOOR[0] - self.px, HOME_DOOR[1] - self.py) < 26

    def enter_home(self):
        self.hx, self.hy, self.hdir = 50.0, 112.0, "down"
        self.hanim, self.hmoving = 0.0, False
        self.home_sky = "dusk"
        br = self.npc_by_id["brandao"]
        if br.chase or self.susp >= 80:
            br.chase = False
            br.path = []
            self.chase_cd = 30.0
            self.notify("Você se escondeu em casa. O cerco esfriou um pouco.", 4.5)
        self.state = "home"

    def exit_home(self):
        self.px, self.py = float(HOME_DOOR[0]), float(HOME_DOOR[1] + 2)
        self.dir = "down"
        self.state = "play"

    def home_blocked(self, rect):
        if rect.left < ROOM_X0 or rect.right > ROOM_X1 or rect.top < ROOM_Y0 - 4 or rect.bottom > ROOM_Y1:
            return True
        return rect.collidelist(self.home_cols) != -1

    def home_update(self, dt):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.hmoving = bool(dx or dy)
        if not self.hmoving:
            self.hanim = 0.0
            return
        n = math.hypot(dx, dy)
        spd = 58 * (RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0)
        nx = self.hx + dx / n * spd * dt
        if not self.home_blocked(pygame.Rect(int(nx) - 4, int(self.hy) - 4, 8, 4)):
            self.hx = nx
        ny = self.hy + dy / n * spd * dt
        if not self.home_blocked(pygame.Rect(int(self.hx) - 4, int(ny) - 4, 8, 4)):
            self.hy = ny
        if dx:
            self.hdir = "right" if dx > 0 else "left"
        else:
            self.hdir = "down" if dy > 0 else "up"
        self.hanim += dt * (spd / 58.0)

    def home_spot(self):
        best, bd = None, 1e9
        for sid, x, y, rad, lab in HOME_SPOTS:
            d = math.hypot(x - self.hx, y - self.hy)
            if d < rad and d < bd:
                best, bd = (sid, x, y, lab), d
        return best

    def home_interact(self):
        sp = self.home_spot()
        if not sp:
            return
        if sp[0] == "porta":
            self.exit_home()
        elif sp[0] == "mural":
            self.su = dict(col=0, row=0, msg="")
            self.state = "stash"
        elif sp[0] == "cama":
            self.cfm = dict(idx=0, text="Dormir agora e passar para o dia %d? A suspeita do regime cai %d pontos, "
                                        "mas a noite custa %d segundos do prazo da Central."
                                        % (self.day + 1, SLEEP_SUSP, SLEEP_COST))
            self.state = "confirm"

    # ---- mural de provas: guardar e pegar itens e dinheiro
    def stash_rows(self, col):
        return ["$"] + (self.pack if col == 0 else self.stash)

    def stash_key(self, k):
        su = self.su
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        if k in (pygame.K_ESCAPE, pygame.K_TAB):
            self.state = "home"
        elif k in (pygame.K_LEFT, pygame.K_a):
            su["col"] = 0
        elif k in (pygame.K_RIGHT, pygame.K_d):
            su["col"] = 1
        elif k in (pygame.K_UP, pygame.K_w):
            su["row"] -= 1
        elif k in (pygame.K_DOWN, pygame.K_s):
            su["row"] += 1
        elif k in yes:
            self.stash_move()
            su["msg"] = su.get("msg", "")
        su["row"] = su["row"] % len(self.stash_rows(su["col"]))

    def stash_move(self):
        su = self.su
        col, row = su["col"], su["row"] % len(self.stash_rows(su["col"]))
        if row == 0:
            step = 50 if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else 10
            if col == 0:
                amt = min(step, self.money)
                self.money -= amt
                self.bank += amt
                su["msg"] = ("Guardou Cr$ %d no mural." % amt) if amt else "Você não tem dinheiro no bolso."
            else:
                amt = min(step, self.bank)
                self.bank -= amt
                self.money += amt
                su["msg"] = ("Pegou Cr$ %d para o dia." % amt) if amt else "Não há dinheiro guardado."
            return
        key = self.stash_rows(col)[row]
        src, dst = (self.pack, self.stash) if col == 0 else (self.stash, self.pack)
        src.remove(key)
        dst.append(key)
        su["msg"] = ("Guardou: %s." if col == 0 else "Pegou: %s.") % ITEMS[key]["nome"]
        su["row"] = min(su["row"], len(src))

    # ---- cama: confirmar e dormir
    def confirm_key(self, k):
        c = self.cfm
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        if k == pygame.K_ESCAPE or k == pygame.K_2:
            self.state = "home"
        elif k == pygame.K_1:
            self.start_sleep()
        elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN,
                   pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s):
            c["idx"] = 1 - c["idx"]
        elif k in yes:
            if c["idx"] == 0:
                self.start_sleep()
            else:
                self.state = "home"

    def start_sleep(self):
        self.sleepfx = dict(t=0.0, did=False, head="")
        self.state = "sleep"

    def sleep_update(self, dt):
        sf = self.sleepfx
        sf["t"] += dt
        if sf["t"] >= 1.4 and not sf["did"]:
            sf["did"] = True
            self.day += 1
            self.susp = max(0.0, self.susp - SLEEP_SUSP)
            self.clock = min(float(TIME_LIMIT), self.clock + SLEEP_COST)
            self.home_sky = "dawn"
            for n in self.npcs:
                n.reset()
            self.chase_cd = max(self.chase_cd, 20.0)
            sf["head"] = MANCHETES[(self.day - 2) % len(MANCHETES)]
        if sf["t"] >= 4.8:
            self.sleepfx = None
            self.state = "home"
            if TIME_LIMIT - self.clock <= 0:
                self.time_up()
            else:
                self.notify("Dia %d. A suspeita baixou, mas o prazo da Central encurtou." % self.day, 4.5)

    # ---- propina (tecla P): usa o dinheiro do bolso
    def bribe_target(self):
        for n in self.npcs:
            if n.id in ("osmar", "brandao") and not n.talking and math.hypot(n.x - self.px, n.y - self.py) < 30:
                return n
        return None

    def try_bribe(self):
        tg = self.bribe_target()
        if tg is None:
            return
        if self.money < BRIBE_COST:
            self.notify("Você precisa de Cr$ %d no bolso." % BRIBE_COST, 3.0)
            return
        self.money -= BRIBE_COST
        self.susp = max(0.0, self.susp - BRIBE_SUSP)
        self.notify("%s guardou a nota no bolso e olhou para o outro lado." % tg.name, 4.0)

    # ---- desenho da casa
    def draw_home_sky(self, f):
        x0, y0, w, h = 187, 19, 38, 38
        dusk = self.home_sky == "dusk"
        c0, c1 = ((46, 30, 100), (255, 140, 110)) if dusk else ((110, 170, 236), (255, 212, 160))
        for i in range(h):
            pygame.draw.line(f, mix(c0, c1, i / float(h - 1)), (x0, y0 + i), (x0 + w - 1, y0 + i))
        if dusk:
            for k, (sx, sy) in enumerate(((190, 22), (200, 26), (212, 21), (220, 28), (195, 31))):
                if int(self.t * 1.5 + k) % 4:
                    f.set_at((sx, sy), (255, 244, 226))
            sun = (x0 + 26, y0 + 25)
        else:
            sun = (x0 + 12, y0 + 14)
        pygame.draw.circle(f, (255, 232, 160), sun, 5)
        pygame.draw.circle(f, (255, 250, 220), sun, 3)
        hill = (60, 40, 84) if dusk else (90, 110, 150)
        pygame.draw.polygon(f, hill, [(x0, y0 + h), (x0, y0 + h - 8), (x0 + 10, y0 + h - 14), (x0 + 18, y0 + h - 10),
                                      (x0 + 30, y0 + h - 18), (x0 + w, y0 + h - 9), (x0 + w, y0 + h)])

    def draw_mural_live(self, f):
        pts = []
        for i, k in enumerate(TESTIMONIES):
            if k not in self.flags:
                continue
            x, y = 78 + (i % 3) * 32, 17 + (i // 3) * 23
            paper = (250, 244, 214) if i % 2 == 0 else (250, 226, 160)
            pygame.draw.rect(f, (110, 70, 50), (x, y + 1, 28, 20))
            pygame.draw.rect(f, paper, (x, y, 28, 19))
            for ly, lw in ((9, 20), (12, 16), (15, 18)):
                pygame.draw.rect(f, (130, 108, 118), (x + 4, y + ly, lw, 1))
            draw_tiny(f, SHORT[k][0], x + 4, y + 2, (170, 40, 60))
            pts.append((x + 14, y + 1))
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(f, (206, 48, 60), a, b, 1)
        for p in pts:
            pygame.draw.circle(f, (150, 20, 36), p, 2)
            f.set_at((p[0] - 1, p[1] - 1), (255, 170, 170))
        for j, key in enumerate(self.stash[:6]):                    # itens guardados ficam na prateleira
            f.blit(self.mk_item[key], (80 + j * 14, 66))
        if self.bank > 0:                                           # dinheiro guardado
            for n_ in range(1 + min(2, self.bank // 100)):
                pygame.draw.rect(f, (60, 110, 70), (160 - n_ * 3, 69 - n_ * 2, 14, 9))
                pygame.draw.rect(f, (130, 190, 120), (161 - n_ * 3, 70 - n_ * 2, 12, 7))
                pygame.draw.circle(f, (70, 130, 80), (167 - n_ * 3, 73 - n_ * 2), 2)

    def draw_home(self):
        f = self.frame
        f.blit(self.home_bg, (0, 0))
        self.draw_home_sky(f)
        f.blit(self.home_win, (0, 0))
        self.draw_mural_live(f)
        f.blit(self.home_beam[self.home_sky], (0, 0))
        seq = [0, 1, 0, 2]
        pf = seq[int(self.hanim * 8) % 4] if self.hmoving else 0
        hero = self.frames[self.hdir][pf]
        f.blit(self.npc_shadow, (int(self.hx - 7), int(self.hy - 4)))
        objs = [(134, self.home_table, 34, 98), (172, self.home_plant, 284, 136),
                (self.hy, hero, int(self.hx - self.anchor[0]), int(self.hy - self.anchor[1]))]
        objs.sort(key=lambda o: o[0])
        for _, spr, px, py in objs:
            f.blit(spr, (px, py))
        k = 0.9 + 0.1 * math.sin(self.t * 7)
        f.blit(self.glow_surf((200, 140, 70), 60, k), (160 - 60, 14 - 60), special_flags=pygame.BLEND_RGB_ADD)
        wc = (120, 90, 150) if self.home_sky == "dusk" else (110, 130, 170)
        f.blit(self.glow_surf(wc, 44, 0.8), (206 - 44, 40 - 44), special_flags=pygame.BLEND_RGB_ADD)
        f.blit(self.glow_surf((150, 100, 50), 30, 0.9), (60 - 30, 112 - 30), special_flags=pygame.BLEND_RGB_ADD)
        f.blit(self.vig, (0, 0))
        pygame.transform.scale(f, (W, H), self.screen)

    def draw_status_panel(self):
        self.panel((862, 560, 262, 112), 225)
        for i, (lab, val, col) in enumerate((("Evidências reunidas", self.evid, (80, 214, 166)),
                                              ("Suspeita do regime", self.susp, (230, 56, 100)))):
            y = 574 + i * 48
            self.text(lab, self.f_xs, (255, 240, 214), (888, y), shadow=False)
            self.seg_bar(890, y + 22, 214, 12, val, col)

    def draw_home_hud(self):
        title = "Casa do Agente Rosso - Dia %d" % self.day
        tw = self.f_med.size(title)[0] + 70
        self.panel((640 - tw // 2, 6, tw, 50), 225)
        self.text(title, self.f_med, (255, 244, 220), (640, 31), center=True)

        def chip(y, txt, col=(255, 238, 180)):
            w = self.f_sm.size(txt)[0] + 44
            self.panel((16, y, w, 38), 215, border=(255, 222, 150))
            self.text(txt, self.f_sm, col, (38, y + 11))
        chip(64, "Prazo %s (parado em casa)   Cr$ %d no bolso" % (self.fmt_time(TIME_LIMIT - self.clock), self.money))
        chip(108, "Objetivo: " + self.objective(), (190, 240, 255))
        self.draw_status_panel()
        if self.state == "home":
            self.text("E: usar    Esc: pausa", self.f_xs, (255, 255, 255), (W - 18, 12), right=True)
            sp = self.home_spot()
            if sp:
                sx = int(self.hx * SC)
                sy = int((self.hy - 36) * SC) + int(math.sin(self.t * 4) * 4)
                self.draw_bubble_at(sx, sy, True, "E")
                self.text(sp[3], self.f_sm, (255, 214, 120), (sx, sy - 44), center=True)

    def draw_stash(self):
        s = self.screen
        su = self.su
        gold = (255, 214, 120)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 4, 24, 150))
        s.blit(dim, (0, 0))
        self.panel((120, 40, 1040, 640), 248)
        self.text("MURAL DE PROVAS", self.f_big, gold, (640, 80), center=True)
        self.pix_rect((150, 108, 980, 186), (96, 58, 44), 4)
        self.pix_rect((158, 116, 964, 170), (186, 138, 88), 4)
        pts = []
        for i, k in enumerate(TESTIMONIES):
            x, y = 176 + i * 152, 134
            got = k in self.flags
            pygame.draw.rect(s, (110, 70, 50), (x + 3, y + 4, 136, 138))
            pygame.draw.rect(s, (250, 244, 214) if got else (150, 104, 66), (x, y, 136, 138))
            if got:
                self.text(SHORT[k], self.f_ch, (150, 40, 60), (x + 68, y + 34), center=True, shadow=False)
                for j, ln in enumerate(wrap(TOPICS[k], self.f_xs, 120)):
                    self.text(ln, self.f_xs, (70, 50, 70), (x + 68, y + 70 + j * 22), center=True, shadow=False)
                pts.append((x + 68, y + 8))
            else:
                self.text("???", self.f_med, (206, 166, 116), (x + 68, y + 70), center=True, shadow=False)
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(s, (206, 48, 60), a, b, 3)
        for p in pts:
            pygame.draw.circle(s, (24, 12, 40), p, 8)
            pygame.draw.circle(s, (230, 52, 70), p, 6)
            pygame.draw.circle(s, (255, 170, 170), (p[0] - 2, p[1] - 2), 2)
        heads = ("Na mochila (vai com você hoje)", "Guardado no mural (fica em casa)")
        for c in (0, 1):
            x0 = 160 + c * 500
            self.panel((x0, 308, 480, 290), 255, border=(150, 230, 210) if su["col"] == c else (120, 100, 150),
                       fill=(40, 24, 70))
            self.text(heads[c], self.f_sm, (255, 238, 180), (x0 + 28, 326), shadow=False)
            rows = self.stash_rows(c)
            for i, key in enumerate(rows):
                y = 366 + i * 36
                sel = su["col"] == c and su["row"] == i
                if sel:
                    self.pix_rect((x0 + 20, y - 4, 440, 32), gold, 4)
                col = (56, 28, 24) if sel else (244, 240, 252)
                if key == "$":
                    self.text("Dinheiro: Cr$ %d" % (self.money if c == 0 else self.bank), self.f_ch, col,
                              (x0 + 36, y), shadow=not sel)
                else:
                    pygame.draw.rect(s, (24, 12, 40), (x0 + 36, y + 2, 20, 20))
                    pygame.draw.rect(s, ITEMS[key]["cor"], (x0 + 38, y + 4, 16, 16))
                    self.text(ITEMS[key]["nome"], self.f_ch, col, (x0 + 68, y), shadow=not sel)
            if len(rows) == 1:
                self.text("Nenhum item.", self.f_xs, (170, 160, 190), (x0 + 36, 366 + 44), shadow=False)
        self.text("Setas: escolher / trocar de lado    Enter: passar para o outro lado (Shift: Cr$ 50)    Esc: voltar",
                  self.f_xs, gold, (640, 616), center=True, shadow=False)
        if su.get("msg"):
            self.text(su["msg"], self.f_sm, (150, 230, 210), (640, 646), center=True)

    def draw_confirm(self):
        c = self.cfm
        s = self.screen
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 4, 24, 150))
        s.blit(dim, (0, 0))
        self.panel((290, 230, 700, 270), 250)
        y = 262
        for ln in wrap(c["text"], self.f_txt, 620):
            self.text(ln, self.f_txt, (255, 248, 232), (330, y))
            y += 30
        for i, lab in enumerate(("1. Dormir", "2. Ainda não")):
            bx = 340 + i * 330
            sel = i == c["idx"]
            self.pix_rect((bx - 4, 424, 268, 52), (24, 12, 40), 4)
            self.pix_rect((bx, 428, 260, 44), (255, 214, 120) if sel else (92, 62, 128), 4)
            self.text(lab, self.f_med, (56, 28, 24) if sel else (255, 238, 190), (bx + 130, 450), center=True,
                      shadow=False)

    def draw_sleep(self):
        sf = self.sleepfx
        t = sf["t"]
        if t < 1.2:
            a = t / 1.2
        elif t < 4.0:
            a = 1.0
        else:
            a = max(0.0, 1 - (t - 4.0) / 0.8)
        ov = pygame.Surface((W, H))
        ov.fill((8, 4, 20))
        ov.set_alpha(int(255 * clamp(a, 0, 1)))
        self.screen.blit(ov, (0, 0))
        if 1.4 <= t < 4.2:
            ta = min(1.0, (t - 1.4) / 0.5) * (1.0 if t < 3.8 else max(0.0, 1 - (t - 3.8) / 0.4))
            col = lambda c: tuple(int(v * ta) for v in c)
            self.text("Dia %d" % self.day, self.f_title, col((255, 214, 120)), (640, 270), center=True, shadow=False)
            for j, ln in enumerate(wrap(sf["head"], self.f_ch, 820)):
                self.text(ln, self.f_ch, col((244, 240, 250)), (640, 350 + j * 30), center=True, shadow=False)

    def schedule_call(self, kind):
        self.pending_call = kind
        self.ring_t = 0.0
        best, bd = 0, 1e9
        for i, p in enumerate(self.phones):
            d = math.hypot(p["x"] - self.px, p["y"] - self.py)
            if d < bd:
                best, bd = i, d
        self.ring_phone = best
        self.notify("O orelhão está tocando! Atenda.", 5.0)

    def start_call(self):
        if self.pending_call:
            kind = self.pending_call
            self.done_calls.add(kind)
            self.pending_call = None
            self.ring_phone = None
        else:
            kind = "missao" if "missao" not in self.flags else "menu"
        self.central.talking = True
        self.dl = dict(npc=self.central, tree=self.call_tree(kind), key="start", shown=0.0, idx=0, node=None)
        self.enter_node("start")
        self.state = "dialogue"

    def where_text(self):
        parts = []
        for n in self.npcs:
            if not n.quest or n.talked:
                continue
            if n.dlg == "helen":
                if self.ready() and "entrega" in self.flags:
                    parts.append("Helen Harper: %s" % district(n.x, n.y))
                continue
            msg = self.gate_msg(n)
            if msg is None:
                parts.append("%s: %s" % (n.name, district(n.x, n.y)))
            elif "missao" in self.flags:
                parts.append("%s: aguarda indicação de %s" % (n.name, NPC_NAMES[NPC_REQ[n.id]]))
        if not parts:
            return "Todos os contatos disponíveis já foram ouvidos. Fique perto de um orelhão: eu ligo."
        return "Última posição conhecida. " + "; ".join(parts) + "."

    def call_tree(self, kind):
        S = "Central (voz no telefone)"
        if kind == "missao":
            return {
                "start": D(S, "Chiado na linha... 'Aqui é a Central. Código Rosso, é você? Fale baixo, {nome}. "
                              "Esta linha só fica segura por alguns minutos.'", nxt="m1"),
                "m1": D(S, "'Sua missão é documentar o que o regime esconde. Há gente que viu e viveu cada abuso, "
                           "mas só abre a boca para quem chega por indicação.'", nxt="m2"),
                "m2": D(S, "'Seus primeiros contatos: Dona Cida, uma mãe que procura o filho; Tavares, jornalista; "
                           "e Zeca, compositor. Eles não ficam parados: cada um tem sua rotina e circula pelo Rio.'",
                        nxt="m3"),
                "m3": D(S, "'Reúna pelo menos três testemunhos e procure o Professor Mário: ele passa as tarefas da rede. Depois eu ligo de novo para combinar a entrega "
                           "à correspondente Helen Harper. Cuidado com o Coronel Brandão e o censor Osmar: eles "
                           "patrulham a cidade.'",
                        ch=[C("Entendido. Vou a campo.", "fim"),
                            C("E se eu for descoberto?", "risco"),
                            C("Como acho essa gente se ela vive circulando?", "como")]),
                "risco": D(S, "'A Central nega que você existe. Por isso: discrição, e nada de carregar provas "
                              "à vista de patrulha.'", nxt="fim", fx={"susp": -2}),
                "como": D(S, "'Ligue de qualquer orelhão: eu digo onde cada um foi visto por último. E siga a "
                             "seta amarela nas bordas da tela.'", nxt="fim"),
                "fim": D(S, "'Câmbio e desligo. Boa sorte, Agente Rosso.' A linha cai com um clique seco.",
                         flag="missao"),
            }
        if kind == "alerta":
            return {
                "start": D(S, "'Rosso, atenda! Houve um vazamento: o censor Osmar anotou seu nome numa lista. "
                              "Alguém contou que um porco de sobretudo anda fazendo perguntas.'",
                           ch=[C("Vou sumir por um tempo e voltar com calma.", "sumir"),
                               C("Estamos perto. Sigo em frente.", "seguir"),
                               C("Preciso de reforço. Alguém pode abrir portas?", "reforco")]),
                "sumir": D(S, "'Sensato. Troque de calçada, mude o horário, finja que passeia.'", nxt="fim",
                           fx={"susp": -12}),
                "seguir": D(S, "'Coragem não é falta de medo, Rosso. Mas seu rosto já está em circulação.'",
                            nxt="fim", fx={"susp": 8, "evid": 4}),
                "reforco": D(S, "'Consigo uma indicação: Dom Aurélio vai falar com você sem precisar de "
                                "intermediário. Use bem.'", nxt="fim", fx={"susp": 3}, flag="dom_ok"),
                "fim": D(S, "'Mantenha a linha livre. Câmbio.'", flag="alerta_ok"),
            }
        if kind == "entrega":
            return {
                "start": D(S, "'Vozes e provas já formam um dossiê, Rosso. Bom trabalho.'", nxt="e1"),
                "e1": D(S, "'Helen Harper, a correspondente, circula entre o Café Colombo, o hotel da praça e a "
                           "calçada da Atlântica. Entregue o dossiê pessoalmente e não dê nome a ninguém.'",
                        ch=[C("Vou agora mesmo.", "fim"), C("Posso ouvir mais testemunhas antes?", "mais")]),
                "mais": D(S, "'Pode. Mais vozes deixam o dossiê mais forte, mas cada dia de exposição custa "
                             "caro. Você decide.'", nxt="fim"),
                "fim": D(S, "'Desligando. Que a verdade chegue lá fora.'", flag="entrega"),
            }
        if kind == "perigo":
            return {
                "start": D(S, "'Rosso, a Central captou o rádio da polícia: estão fechando o cerco. O Coronel "
                              "Brandão mandou procurarem um porco de sobretudo.'",
                           ch=[C("Vou me misturar à multidão.", "esconder"), C("Não posso parar agora.", "ignorar")]),
                "esconder": D(S, "'Feira, praia, qualquer lugar cheio. A multidão é o melhor disfarce.'", nxt="fim",
                              fx={"susp": -18}),
                "ignorar": D(S, "'Então seja rápido. Se Brandão te alcançar, mantenha a frieza.'", nxt="fim",
                             fx={"susp": 4}),
                "fim": D(S, "'Câmbio.'", flag="perigo_ok"),
            }
        c = self.evidence_count()
        sit = "Testemunhos reunidos: %d de 6. Suspeita do regime: %d%%. " % (c, int(self.susp))
        sit += ("Cuidado: o cerco está fechando." if self.susp >= 70 else
                "Você está passando despercebido." if self.susp < 30 else "Já há olhos em você.")
        return {
            "start": D(S, "'Central na escuta. O que precisa, {nome}?'",
                       ch=[C("Onde estão as testemunhas agora?", "onde"), C("Como está a situação?", "sit"),
                           C("Há algum boato na rede?", "boato"),
                           C("Nada. Só confirmando a linha.", "tchau")]),
            "onde": D(S, "'" + self.where_text() + "'", nxt="start"),
            "sit": D(S, "'" + sit + "'", nxt="start"),
            "boato": D(S, "'" + self.rumor_text() + "'", nxt="start"),
            "tchau": D(S, "'Então desligue logo. Câmbio.'"),
        }

    def update_events(self, dt):
        if self.toast:
            self.toast[1] -= dt
            if self.toast[1] <= 0:
                self.toast = None
        if self.state != "play":
            return
        self.ring_t += dt
        self.watch_cd = max(0.0, self.watch_cd - dt)
        self.chase_cd = max(0.0, self.chase_cd - dt)
        if "missao" not in self.flags:
            return
        self.sync_steps()
        # teia de eventos: o andamento da missão faz a Central ligar
        if self.pending_call is None:
            c = self.evidence_count()
            want = None
            if self.ready() and "entrega" not in self.done_calls:
                want = "entrega"
            elif c >= 2 and "alerta" not in self.done_calls:
                want = "alerta"
            elif self.susp >= 70 and "perigo" not in self.done_calls:
                want = "perigo"
            if want and self.call_due is None:
                self.call_due = [want, 2.5]
            if self.call_due:
                self.call_due[1] -= dt
                if self.call_due[1] <= 0:
                    self.schedule_call(self.call_due[0])
                    self.call_due = None
        # patrulhas do regime: ficar perto delas com provas no bolso levanta suspeita
        for n in self.npcs:
            if n.id in ("osmar", "brandao") and (self.evid >= 15 or self.pack) and not n.talking:
                if math.hypot(n.x - self.px, n.y - self.py) < 40:
                    if self.susp < 90:
                        self.susp = min(90.0, self.susp + 3.0 * dt)
                    if self.watch_cd <= 0:
                        self.notify("%s está de olho em você!" % n.name, 3.5)
                        self.watch_cd = 12.0
        # cerco: com a suspeita alta, o coronel vem atrás do agente
        br = self.npc_by_id["brandao"]
        if self.susp >= 80 and self.chase_cd <= 0 and not br.talking:
            br.chase = True
            if math.hypot(br.x - self.px, br.y - self.py) < 20:
                self.susp = max(0.0, self.susp - 14.0)
                self.chase_cd = 45.0
                br.chase = False
                br.path = []
                self.notify("O Coronel Brandão te alcançou!", 3.0)
                self.start_dialogue(br)
        elif br.chase:
            br.chase = False
            br.path = []

    def draw_toast(self):
        if not self.toast:
            return
        txt, t = self.toast
        a = clamp(t / 0.5, 0, 1)
        tw = self.f_med.size(txt)[0] + 60
        self.panel((640 - tw // 2, 116, tw, 46), int(228 * a), border=(255, 214, 110))
        self.text(txt, self.f_med, (255, 244, 220), (640, 139), center=True)

    # ------------------------------------------------------------- loop
    def run(self):
        while True:
            dt = min(self.fps_clock.tick(FPS) / 1000.0, 0.05)
            self.t += dt
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.state == "title":
                    if self.title_btn.collidepoint(e.pos):
                        self.start_new_game()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    else:
                        self.on_key(e.key)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            self.fullscreen = not getattr(self, "fullscreen", False)
            flags = pygame.FULLSCREEN if self.fullscreen else 0
            self.screen = pygame.display.set_mode((W, H), flags)

    def on_key(self, k):
        yes = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER)
        up = (pygame.K_UP, pygame.K_w)
        dn = (pygame.K_DOWN, pygame.K_s)
        st = self.state
        if st == "title":
            if k in yes:
                self.start_new_game()
            elif k == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
        elif st == "intro":
            if k in yes or k == pygame.K_ESCAPE:
                self.state = "play"
        elif st == "play":
            if k in yes:
                self.try_interact()
            elif k == pygame.K_p:
                self.try_bribe()
            elif k in (pygame.K_TAB, pygame.K_j):
                self.state = "journal"
            elif k == pygame.K_ESCAPE:
                self.pause_from = "play"
                self.state = "pause"
        elif st == "home":
            if k in yes:
                self.home_interact()
            elif k == pygame.K_ESCAPE:
                self.pause_from = "home"
                self.state = "pause"
        elif st == "room":
            if k in yes:
                self.room_interact()
            elif k == pygame.K_ESCAPE:
                self.pause_from = "room"
                self.state = "pause"
        elif st == "entrega":
            self.entrega_key(k)
        elif st == "stash":
            self.stash_key(k)
        elif st == "confirm":
            self.confirm_key(k)
        elif st == "journal":
            if k in (pygame.K_TAB, pygame.K_j, pygame.K_ESCAPE) or k in yes:
                self.state = "play"
        elif st == "pause":
            if k == pygame.K_ESCAPE or k in yes:
                self.state = self.pause_from
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
        elif st == "puzzle":
            self.puz_key(k)
        elif st == "ending":
            if k in yes and self.ending["t"] > 1.5:
                self.state = "title"

    def start_new_game(self):
        self.reset_play()
        self.state = "intro"
        self.intro_t = 0.0

    def near_npc(self):
        best, bd = None, 26.0
        for n in self.npcs:
            d = math.hypot(n.x - self.px, n.y - self.py)
            if d < bd:
                best, bd = n, d
        return best

    # ----------------------------------------------------------- update
    def update(self, dt):
        if self.state in ("play", "dialogue", "puzzle") and not self.rk:
            self.clock += dt
            left = TIME_LIMIT - self.clock
            for mark, txt in ((120, "Faltam 2 minutos: a Central vai cortar a linha!"),
                              (30, "30 segundos! Entregue o dossiê agora!")):
                if left <= mark and mark not in self.warned:
                    self.warned.add(mark)
                    self.notify(txt, 5.0)
            if left <= 0:
                self.clock = float(TIME_LIMIT)
                self.time_up()
        if self.state == "play" and not self.rk:
            self.update_listen(dt)
        if self.state == "title":
            self.copa.update(dt)
        if self.state in ("play", "dialogue", "title"):
            for wk in self.walkers:
                wk.update(dt)
            for n in self.npcs:
                n.update(dt, self)
        self.update_events(dt)
        if self.state == "play":
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            self.moving = bool(dx or dy)
            if self.moving:
                n = math.hypot(dx, dy)
                spd = 58 * (RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0)
                vx, vy = dx / n * spd * dt, dy / n * spd * dt
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
                self.anim += dt * (spd / 58.0)
            else:
                self.anim = 0.0
        elif self.state == "puzzle":
            self.puz_update(dt)
        elif self.state == "home":
            self.home_update(dt)
        elif self.state == "room":
            self.room_update(dt)
        elif self.state == "sleep":
            self.sleep_update(dt)
        elif self.state == "dialogue":
            dl = self.dl
            dl["shown"] = min(float(len(dl["text"])), dl["shown"] + dt * 60)
        elif self.state == "ending":
            self.ending["t"] += dt
        elif self.state == "intro":
            self.intro_t += dt
        # câmera
        if self.state == "title":
            tx = 62 * TS + math.sin(self.t * 0.05) * 560 - IW / 2
            ty = 38 * TS + math.sin(self.t * 0.037) * 330 - IH / 2
            self.cam[0] += (tx - self.cam[0]) * 0.03
            self.cam[1] += (ty - self.cam[1]) * 0.03
        else:
            tx, ty = self.px - IW / 2, self.py - IH / 2 - 6
            self.cam[0] += (tx - self.cam[0]) * 0.14
            self.cam[1] += (ty - self.cam[1]) * 0.14
        self.cam[0] = clamp(self.cam[0], 0, MW * TS - IW)
        self.cam[1] = clamp(self.cam[1], 0, MH * TS - IH)

    # ------------------------------------------------------------ render
    def glow_surf(self, col, rad, k):
        key = (col, rad, int(k * 10))
        g = self.glow_cache.get(key)
        if g is None:
            g = make_glow(tuple(int(v * k * 0.48) for v in col), rad)
            self.glow_cache[key] = g
        return g

    def render_world(self):
        f = self.frame
        cx, cy = int(self.cam[0]), int(self.cam[1])
        t = self.t
        f.blit(self.ground, (0, 0), (cx, cy, IW, IH))
        # mar vivo: espuma na arrebentação e brilhos do sol poente
        if cx < 20 * TS:
            for sy in range(0, IH, 2):
                wy = cy + sy
                ph_ = math.sin(t * 1.5 + wy * 0.1)
                sx = int(shore_px(wy) + ph_ * 3.5) - cx
                if -8 < sx < IW:
                    f.fill((252, 252, 255), (sx, sy, 2 + int((ph_ + 1) * 1.5), 1))
                    f.fill((176, 232, 240), (sx - 7, sy, 3, 1))
            for gx, gy, ph in self.glints:
                sx, sy = int(gx - cx), int(gy - cy)
                if 0 <= sx < IW and 0 <= sy < IH and math.sin(t * 2.2 + ph) > 0.55:
                    f.fill((255, 244, 214), (sx, sy, 2, 1))
        vis = []
        for o in self.objs:
            spr = o.surf(t)
            w, h = spr.get_size()
            by = o.y + (math.sin(t * 1.3) * o.bob if o.bob else 0)
            px, py = int(o.x - w // 2 - cx), int(by - h - cy)
            if px + w < -40 or px > IW + 40 or py + h < -40 or py > IH + 40:
                continue
            vis.append((o.y, spr, px, py, o))
        # sombras
        for _, spr, px, py, o in vis:
            if o.shadow is not None:
                f.blit(o.shadow, (px + 2, py + spr.get_height() - 1))
        for n in self.npcs:
            f.blit(self.npc_shadow, (int(n.x - 7 - cx), int(n.y - 4 - cy)))
        for wk in self.walkers:
            f.blit(self.npc_shadow, (int(wk.x - 7 - cx), int(wk.y - 4 - cy)))
        f.blit(self.npc_shadow, (int(self.px - 7 - cx), int(self.py - 4 - cy)))
        # carros em movimento (com faróis ou lanternas acesas)
        car_lights = []
        for lx, y0, sp, k in self.cars:
            yy = (y0 + sp * t) % (MH * TS + 40) - 20
            spr = (self.car_front if sp > 0 else self.car_back)[k]
            px, py = int(lx - spr.get_width() // 2 - cx), int(yy - spr.get_height() - cy)
            if -40 < px < IW and -40 < py < IH + 40:
                cs = self.car_shadows.get(spr.get_width())
                if cs is None:
                    cs = pygame.Surface((spr.get_width() - 2, 8 if spr.get_height() > 30 else 7), pygame.SRCALPHA)
                    pygame.draw.ellipse(cs, (30, 12, 64, 96), (0, 0, cs.get_width(), cs.get_height()))
                    self.car_shadows[spr.get_width()] = cs
                f.blit(cs, (px + 1, int(yy - 5 - cy)))
                vis.append((yy, spr, px, py, None))
                if sp > 0:
                    car_lights.append((lx - cx, yy - 5 - cy, 22, (104, 92, 48)))
                else:
                    car_lights.append((lx - cx, yy - 8 - cy, 14, (96, 16, 20)))
        # bondinho nos Arcos da Lapa
        for tr in self.trams:
            span = tr["x1"] - tr["x0"]
            u = (t * tr["sp"] + tr["ph"]) % (2 * span)
            fwd = u < span
            bx = tr["x0"] + (u if fwd else 2 * span - u)
            spr = tr["r"] if fwd else tr["l"]
            px, py = int(bx - spr.get_width() // 2 - cx), int(tr["y"] - spr.get_height() - cy)
            if -80 < px < IW + 80 and -50 < py < IH + 50:
                vis.append((tr["ky"], spr, px, py, None))
                car_lights.append((bx - cx, tr["y"] - 14 - cy, 26, (110, 88, 30)))
        # orelhão tocando: brilho vermelho pulsante
        if self.pending_call and self.ring_phone is not None:
            ph = self.phones[self.ring_phone]
            k = 0.5 + 0.5 * math.sin(self.ring_t * 14)
            car_lights.append((ph["x"] - cx, ph["y"] - 16 - cy, 30, (int(150 * k), int(30 * k), int(24 * k))))
        # atores
        for n in self.npcs:
            fr = n.frame()
            hop = int(abs(math.sin(t * 5 + n.x)) * 2) if n.hop and self.state != "dialogue" and not n.moving else 0
            breath = 1 if (not n.hop and not n.moving and self.state != "dialogue" and ((t * 0.55 + n.x * 0.071) % 1.0) < 0.1) else 0
            px, py = int(n.x - n.anchor[0] - cx), int(n.y - n.anchor[1] - cy - hop - breath)
            vis.append((n.y, fr, px, py, None))
        for wk in self.walkers:
            fr = wk.frame()
            vis.append((wk.y, fr, int(wk.x - wk.anchor[0] - cx), int(wk.y - wk.anchor[1] - cy), None))
        seq = [0, 1, 0, 2]
        pf = seq[int(self.anim * 8) % 4] if self.moving else 0
        sp = self.frames[self.dir][pf]
        vis.append((self.py, sp, int(self.px - self.anchor[0] - cx), int(self.py - self.anchor[1] - cy), None))
        rk_ = self.near_room_door() if self.state == "play" else None
        if rk_:
            sx = int((ROOM_DOORS[rk_][0] - cx) * SC)
            sy = int((ROOM_DOORS[rk_][1] - 62 - cy) * SC) + int(math.sin(self.t * 4) * 4)
            self.draw_bubble_at(sx, sy, True, "E")
            self.text(ROOM_LABEL[rk_], self.f_sm, (255, 214, 120), (sx, sy - 44), center=True)
        mst = self.cur_step() if ("missao" in self.flags and not self.pending_call) else None
        if mst and "tile" in mst:
            mx, my = mst["tile"][0] * TS + 8, mst["tile"][1] * TS + 14
            bob = int(math.sin(t * 4) * 2)
            if mst["k"] == "pickup" and mst["item"] not in self.pack:
                mspr, gcol = self.mk_item[mst["item"]], ITEMS[mst["item"]]["cor"]
            else:
                mspr, gcol = self.mk_spot, (190, 150, 60)
            vis.append((my, mspr, int(mx - mspr.get_width() // 2 - cx), int(my - mspr.get_height() - 4 - cy - bob), None))
            car_lights.append((mx - cx, my - 8 - cy, 22, tuple(int(v * 0.45) for v in gcol)))
        vis.sort(key=lambda v: v[0])
        for _, spr, px, py, _o in vis:
            f.blit(spr, (px, py))
        # luzes: janelas, néons, postes, fogueira (brilho aditivo)
        for lx, ly, lr, lc, lf in self.lights:
            sx, sy = lx - cx, ly - cy
            if sx < -lr or sx > IW + lr or sy < -lr or sy > IH + lr:
                continue
            k = 1.0
            if lf:
                k = 0.78 + 0.22 * math.sin(t * 11 + lx * 0.37) * math.sin(t * 7.3 + ly * 0.21) + 0.1
            f.blit(self.glow_surf(lc, lr, clamp(k, 0.5, 1.0)), (int(sx - lr), int(sy - lr)),
                   special_flags=pygame.BLEND_RGB_ADD)
        for sx, sy, lr, lc in car_lights:
            f.blit(self.glow_surf(lc, lr, 1.0), (int(sx - lr), int(sy - lr)), special_flags=pygame.BLEND_RGB_ADD)
        # pétalas e papéis flutuando
        for m in self.motes:
            x = (m[0] + t * m[2] + math.sin(t * 0.9 + m[3]) * 6) % IW
            y = (m[1] + math.sin(t * 0.7 + m[3]) * 10 + t * 3.2) % IH
            ix, iy = int(x), int(y)
            if m[4] == 0:
                f.set_at((ix, iy), (255, 236, 226))
            elif m[4] == 1:
                f.fill((250, 168, 190), (ix, iy, 2, 1))
                f.set_at((ix + 1, iy + 1), (214, 110, 150))
            else:
                f.fill((250, 246, 236), (ix, iy, 2, 2))
                f.set_at((ix + 1, iy + 2), (120, 80, 120))

    def post_fx(self):
        f = self.frame
        small = pygame.transform.smoothscale(f, (IW // 3, IH // 3))
        blur = pygame.transform.smoothscale(small, (IW, IH))
        for i in range(10):
            a = int(255 * (1 - i / 10.0))
            blur.set_alpha(a)
            f.blit(blur, (0, i * 4), (0, i * 4, IW, 4))
            f.blit(blur, (0, IH - (i + 1) * 4), (0, IH - (i + 1) * 4, IW, 4))
        # bloom: realça só o que é bem claro
        b = pygame.transform.smoothscale(f, (IW // 4, IH // 4))
        b.fill((170, 156, 156), special_flags=pygame.BLEND_RGB_SUB)
        b = pygame.transform.smoothscale(b, (IW, IH))
        f.blit(b, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        f.blit(self.tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        f.blit(self.grad, (0, 0))
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
            sh = font.render(s, True, (24, 12, 40))
            off = font.k if PIXEL_TEXT else 2
            self.screen.blit(sh, (r.x + off, r.y + off))
        self.screen.blit(img, r)
        return r

    def text_outline(self, s, font, col, oc, pos, w=4):
        img = font.render(s, True, col)
        oi = font.render(s, True, oc)
        r = img.get_rect(center=pos)
        st = 3 if PIXEL_TEXT else 2
        for dx in range(-w, w + 1, st):
            for dy in range(-w, w + 1, st):
                self.screen.blit(oi, (r.x + dx, r.y + dy))
        self.screen.blit(img, r)

    def pix_rect(self, rect, col, u=4):
        """Retângulo com cantos chanfrados em degrau (visual pixel art)."""
        x, y, w, h = rect
        pygame.draw.rect(self.screen, col, (x + u, y, w - 2 * u, h))
        pygame.draw.rect(self.screen, col, (x, y + u, w, h - 2 * u))

    def panel(self, rect, alpha=235, border=(255, 222, 150), fill=(48, 28, 82), outline=(20, 10, 34)):
        x, y, w, h = rect
        u = 4
        s = pygame.Surface((w, h), pygame.SRCALPHA)

        def notched(col, ins):
            ww, hh = w - 2 * ins, h - 2 * ins
            pygame.draw.rect(s, col, (ins + u, ins, ww - 2 * u, hh))
            pygame.draw.rect(s, col, (ins, ins + u, ww, hh - 2 * u))

        notched(outline + (255,), 0)
        notched(border + (255,), u)
        notched(fill + (alpha,), 2 * u)
        pygame.draw.rect(s, tone(fill, .2) + (alpha,), (3 * u, 2 * u, w - 6 * u, 3))
        pygame.draw.rect(s, tone(fill, -.4) + (alpha,), (3 * u, h - 2 * u - 3, w - 6 * u, 3))
        for cx_, cy_ in ((u, u), (w - 2 * u, u), (u, h - 2 * u), (w - 2 * u, h - 2 * u)):
            pygame.draw.rect(s, tone(border, .4) + (255,), (cx_, cy_, u, u))
        self.screen.blit(s, (x, y))

    def draw_sprite_big(self, spr, pos, scale):
        big = pygame.transform.scale(spr, (spr.get_width() * scale, spr.get_height() * scale))
        self.screen.blit(big, pos)

    def seg_bar(self, x, y, w, h, val, col, segs=10):
        s = self.screen
        self.pix_rect((x - 4, y - 4, w + 8, h + 8), (18, 8, 30), 3)
        gap = 3
        sw = (w - (segs - 1) * gap) / float(segs)
        for i in range(segs):
            sx = x + int(i * (sw + gap))
            on = val > i * 100.0 / segs
            c = col if on else (66, 48, 88)
            pygame.draw.rect(s, c, (sx, y, int(sw), h))
            if on:
                pygame.draw.rect(s, tone(col, .45), (sx, y, int(sw), 3))
                pygame.draw.rect(s, tone(col, -.35), (sx, y + h - 3, int(sw), 3))

    # --------------------------------------------------------------- HUD
    def draw_hud(self):
        s = self.screen
        title = "%s - Rio de Janeiro, 1970 - Dia %d" % (district(self.px, self.py), self.day)
        tw = self.f_med.size(title)[0] + 70
        self.panel((640 - tw // 2, 6, tw, 50), 225)
        self.text(title, self.f_med, (255, 244, 220), (640, 31), center=True)
        obj = self.objective()
        ow = self.f_sm.size(obj)[0] + 64
        self.panel((16, 64, ow, 42), 215, border=(150, 230, 210))
        pygame.draw.polygon(s, (255, 214, 110), [(34, 85), (42, 77), (50, 85), (42, 93)])
        pygame.draw.polygon(s, (24, 12, 40), [(34, 85), (42, 77), (50, 85), (42, 93)], 2)
        self.text(obj, self.f_sm, (255, 238, 180), (62, 74))

        def chip(y, txt, col=(255, 238, 180)):
            w = self.f_sm.size(txt)[0] + 44
            self.panel((16, y, w, 38), 215, border=(255, 222, 150))
            self.text(txt, self.f_sm, col, (38, y + 11))
        left = TIME_LIMIT - self.clock
        chip(112, "Prazo %s   Testemunhos %d/%d" % (self.fmt_time(left), self.evidence_count(), NEEDED),
             (255, 130, 160) if left < 120 else (255, 238, 180))
        chip(156, "Cr$ %d   Mochila: %s" % (self.money, ", ".join(ITEMS[i]["nome"] for i in self.pack) or "vazia"),
             (190, 240, 255))
        self.draw_status_panel()
        # minimapa circular
        cc, rr = (1196, 620), 62
        pygame.draw.circle(s, (20, 10, 34), cc, rr + 10)
        pygame.draw.circle(s, (255, 222, 150), cc, rr + 7)
        pygame.draw.circle(s, (20, 10, 34), cc, rr + 3)
        px_, py_ = int(self.px / TS * 2), int(self.py / TS * 2)
        crop = pygame.Surface((64, 64))
        crop.fill((70, 62, 90))
        crop.blit(self.mini, (32 - px_, 32 - py_))
        pygame.draw.rect(crop, (255, 255, 255), (29, 29, 6, 6))
        pygame.draw.rect(crop, (230, 40, 70), (30, 30, 4, 4))
        for n in self.npcs:
            if self.npc_marker(n):
                nx, ny = int(n.x / TS * 2) - px_ + 32, int(n.y / TS * 2) - py_ + 32
                if 0 <= nx < 62 and 0 <= ny < 62:
                    crop.fill((255, 240, 80), (nx, ny, 3, 3))
        mt = self.step_target()
        if mt:
            nx, ny = int(mt[0] / TS * 2) - px_ + 32, int(mt[1] / TS * 2) - py_ + 32
            if 1 <= nx < 61 and 1 <= ny < 61:
                crop.fill((255, 140, 60), (nx - 1, ny - 1, 5, 5))
        for p in self.phones:
            nx, ny = int(p["x"] / TS * 2) - px_ + 32, int(p["y"] / TS * 2) - py_ + 32
            if 0 <= nx < 62 and 0 <= ny < 62:
                crop.fill((90, 220, 255), (nx, ny, 3, 3))
        nx, ny = int(HOME_DOOR[0] / TS * 2) - px_ + 32, int(HOME_DOOR[1] / TS * 2) - py_ + 32
        if 0 <= nx < 61 and 0 <= ny < 61:
            crop.fill((255, 150, 210), (nx - 1, ny - 1, 4, 4))
        big = pygame.transform.scale(crop, (rr * 2, rr * 2)).convert_alpha()
        mask = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (rr, rr), rr - 2)
        big.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(big, (cc[0] - rr, cc[1] - rr))
        self.draw_pointer()
        self.draw_toast()

    def pointer_target(self):
        """Para onde a seta aponta: o orelhão certo ou a testemunha mais próxima."""
        if "missao" not in self.flags or self.pending_call:
            if self.pending_call and self.ring_phone is not None:
                p = self.phones[self.ring_phone]
                return p["x"], p["y"] - 10, "Orelhão"
            best, bd = None, 1e9
            for p in self.phones:
                d = math.hypot(p["x"] - self.px, p["y"] - self.py)
                if d < bd:
                    best, bd = p, d
            return best["x"], best["y"] - 10, "Orelhão"
        mt = self.step_target()
        if mt:
            return mt
        target, bd = None, 1e9
        for n in self.npcs:
            if self.npc_marker(n):
                d = math.hypot(n.x - self.px, n.y - self.py)
                if d < bd:
                    target, bd = n, d
        if target is None:
            return None
        return target.x, target.y - 10, target.name

    def draw_pointer(self):
        """Seta na borda da tela apontando o próximo objetivo (a cidade ficou grande)."""
        tg = self.pointer_target()
        if tg is None:
            return
        tx, ty, name = tg
        sx = (tx - self.cam[0]) * SC
        sy = (ty - self.cam[1]) * SC
        if 40 < sx < W - 40 and 40 < sy < H - 40:
            return
        dx, dy = sx - W / 2, sy - H / 2
        k = min((W / 2 - 50) / abs(dx) if dx else 1e9, (H / 2 - 60) / abs(dy) if dy else 1e9)
        ax, ay = W / 2 + dx * k, H / 2 + dy * k
        ang = math.atan2(dy, dx)
        pts = [(ax + math.cos(ang) * 18, ay + math.sin(ang) * 18),
               (ax + math.cos(ang + 2.4) * 14, ay + math.sin(ang + 2.4) * 14),
               (ax + math.cos(ang - 2.4) * 14, ay + math.sin(ang - 2.4) * 14)]
        pygame.draw.polygon(self.screen, (24, 12, 40), pts, 6)
        pygame.draw.polygon(self.screen, (255, 214, 110), pts)
        self.text(name, self.f_xs, (255, 238, 180), (int(ax), int(ay) + (26 if ay < H / 2 else -26)), center=True)

    def draw_bubble_at(self, sx, sy, near, lab, hot=False):
        fill = (255, 226, 130) if near else ((255, 150, 130) if hot else (255, 255, 255))
        self.pix_rect((sx - 24, sy - 24, 48, 48), (24, 12, 40), 4)
        self.pix_rect((sx - 20, sy - 20, 40, 40), fill, 4)
        pygame.draw.polygon(self.screen, (24, 12, 40), [(sx - 8, sy + 22), (sx + 8, sy + 22), (sx, sy + 34)])
        pygame.draw.polygon(self.screen, fill, [(sx - 5, sy + 19), (sx + 5, sy + 19), (sx, sy + 28)])
        col = (150, 70, 30) if near else ((140, 20, 30) if hot else (60, 120, 90))
        self.text(lab, self.f_big, col, (sx, sy), center=True, shadow=False)

    def draw_bubbles(self):
        cx, cy = int(self.cam[0]), int(self.cam[1])
        near = self.near_npc() if self.state == "play" else None
        nph = self.near_phone() if self.state == "play" else None
        for n in self.npcs:
            show_q = self.npc_marker(n)
            if not show_q and n is not near:
                continue
            sx = int((n.x - cx) * SC)
            sy = int((n.y - n.anchor[1] - cy) * SC) - 26 + int(math.sin(self.t * 4) * 4)
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H:
                continue
            self.draw_bubble_at(sx, sy, n is near, "E" if n is near else "?")
        for i, p in enumerate(self.phones):
            ringing = bool(self.pending_call) and i == self.ring_phone
            need = "missao" not in self.flags
            isnear = p is nph
            if not (ringing or need or isnear):
                continue
            sx = int((p["x"] - cx) * SC)
            sy = int((p["y"] - 40 - cy) * SC) + 10 + int(math.sin(self.t * (14 if ringing else 4)) * (5 if ringing else 4))
            if sx < -30 or sx > W + 30 or sy < -30 or sy > H:
                continue
            self.draw_bubble_at(sx, sy, isnear, "E" if isnear else ("!" if ringing else "?"), hot=ringing)
        if self.state == "play" and self.near_home_door():
            sx = int((HOME_DOOR[0] - cx) * SC)
            sy = int((HOME_DOOR[1] - 62 - cy) * SC) + int(math.sin(self.t * 4) * 4)
            self.draw_bubble_at(sx, sy, True, "E")
            self.text("Casa", self.f_sm, (255, 214, 120), (sx, sy - 44), center=True)
        mst = self.cur_step() if ("missao" in self.flags and not self.pending_call and self.state == "play") else None
        if mst and "tile" in mst:
            mx, my = mst["tile"][0] * TS + 8, mst["tile"][1] * TS + 14
            sx = int((mx - cx) * SC)
            sy = int((my - 34 - cy) * SC) + int(math.sin(self.t * 4) * 4)
            if -30 <= sx <= W + 30 and -30 <= sy <= H:
                isnear = self.near_tile(mst["tile"])
                self.draw_bubble_at(sx, sy, isnear, "E" if isnear else "!")
        if self.state == "play" and not self.rk:
            for tile in self.secret_near():
                mx, my = tile[0] * TS + 8, tile[1] * TS + 14
                sx = int((mx - cx) * SC)
                sy = int((my - 34 - cy) * SC) + int(math.sin(self.t * 4) * 4)
                self.draw_bubble_at(sx, sy, True, "E")

    # --------------------------------------------------------- diálogo UI
    def draw_dialogue(self):
        dl = self.dl
        s = self.screen
        self.panel((40, 388, 1200, 326), 238)
        name = dl["speaker"]
        tw = self.f_med.size(name)[0] + 60
        self.panel((90, 360, tw, 54), 255, border=(255, 246, 200), fill=(246, 186, 76))
        self.text(name, self.f_med, (62, 30, 24), (90 + 30, 376), shadow=False)
        # retrato
        self.panel((78, 432, 184, 262), 255, border=(150, 230, 210), fill=(92, 62, 128))
        pygame.draw.rect(s, (60, 36, 96), (98, 452, 144, 222))
        for i in range(14):
            pygame.draw.rect(s, mix((120, 78, 150), (230, 130, 140), i / 13.0), (98, 452 + i * 16, 144, 16))
        sprite = dl["npc"].frames["down"][0]
        sc = 5 if sprite.get_height() > 30 else 6
        self.draw_sprite_big(sprite, (170 - sprite.get_width() * sc // 2, 668 - sprite.get_height() * sc), sc)
        txt = dl["text"][:int(dl["shown"])]
        lines = wrap(txt, self.f_txt, 880)
        y = 416
        for ln in lines:
            self.text(ln, self.f_txt, (255, 248, 232), (296, y))
            y += 30
        full = dl["shown"] >= len(dl["text"])
        if dl["choices"] and full:
            y += 12
            for i, c in enumerate(dl["choices"]):
                sel = i == dl["idx"]
                ls = wrap("%d. %s" % (i + 1, c["text"]), self.f_ch, 850)
                hh = 28 * len(ls) + 8
                if sel:
                    self.pix_rect((290, y - 3, 930, hh), (24, 12, 40), 4)
                    self.pix_rect((294, y, 922, hh - 6), (255, 214, 120), 4)
                    ay = y + hh // 2 - 3
                    pygame.draw.polygon(s, (24, 12, 40), [(300, ay - 8), (300, ay + 8), (314, ay)])
                for ln in ls:
                    self.text(ln, self.f_ch, (56, 28, 24) if sel else (255, 232, 190), (322, y + 3), shadow=not sel)
                    y += 28
                y += 10
        elif full:
            by = 676 + int(abs(math.sin(self.t * 5)) * 4)
            pygame.draw.polygon(s, (255, 214, 120), [(1196, by), (1214, by), (1205, by + 10)])
            self.text("E", self.f_xs, (255, 214, 120), (1180, 676), right=True, shadow=False)

    # ----------------------------------------------------------- telas
    def backdrop(self):
        if not hasattr(self, "_bd"):
            bd = pygame.Surface((W, H))
            for y in range(H):
                bd.fill(mix((22, 10, 46), (86, 36, 96), y / float(H)), (0, y, W, 1))
            rr = random.Random(5)
            for _ in range(90):
                x, y = rr.randrange(W), rr.randrange(int(H * 0.7))
                z = rr.choice((2, 2, 4))
                bd.fill((255, 240, 220), (x, y, z, z))
            self._bd = bd
        self.screen.blit(self._bd, (0, 0))

    def draw_title(self):
        """Menu: só a cena de Copacabana e o botão Iniciar abaixo do centro (sem título por enquanto)."""
        s = self.screen
        r = self.title_btn
        pulse = 0.5 + 0.5 * math.sin(self.t * 3.0)
        mx, my = pygame.mouse.get_pos()
        hover = r.collidepoint(mx, my)
        # halo pulsante atrás do botão
        halo = pygame.Surface((r.w + 60, r.h + 60), pygame.SRCALPHA)
        for i in range(5):
            a = int((26 + 30 * pulse) * (1 - i / 5.0))
            pygame.draw.rect(halo, (255, 200, 110, a), (i * 5, i * 5, halo.get_width() - i * 10, halo.get_height() - i * 10),
                             border_radius=18)
        s.blit(halo, (r.x - 30, r.y - 30))
        grow = 6 if hover else 0
        rr = r.inflate(grow * 2, grow)
        self.panel(tuple(rr), 255, border=(255, 246, 200), fill=(246, 186, 76))
        ay = rr.centery
        ax = rr.x + 44 + int(pulse * 5)
        pygame.draw.polygon(s, (24, 12, 40), [(ax, ay - 14), (ax, ay + 14), (ax + 22, ay)])
        self.text("Iniciar", self.f_big, (62, 30, 24), rr.center, center=True, shadow=False)

    def draw_intro(self):
        s = self.screen
        self.backdrop()
        a = clamp(self.intro_t / 1.5, 0, 1)
        self.panel((110, 56, 1060, 610), 235)
        lines = ["OPERAÇÃO VERDADE", "Brasil, 1970 - Anos de Chumbo", "",
                 "Há seis anos o país vive sob uma ditadura militar.",
                 "O Congresso está fechado, a imprensa é censurada e quem discorda some.",
                 "Você é o Agente Rosso, um porco espião de uma rede clandestina.",
                 "Ligue para a Central e procure o Professor Mário, da rede.",
                 "Escolha uma linha (Igreja, Rádio ou Imprensa): depois não há volta. Casa = porta rosa.",
                 "Reúna testemunhas e entregue o dossiê a Helen Harper.",
                 "15 min de prazo. Shift = correr. Itens perto da polícia dão suspeita. Há segredos!",
                 "", "[Enter]"]
        y = 100
        for i, ln in enumerate(lines):
            col = (255, 214, 120) if i < 2 else (244, 240, 250)
            c = tuple(int(v * a) for v in col)
            self.text(ln, self.f_big if i == 0 else self.f_med, c, (640, y), center=True, shadow=False)
            y += 70 if i == 0 else 48

    def draw_journal(self):
        self.panel((150, 76, 980, 570), 245)
        h = self.hero
        self.text("Diário de %s - %s" % (h["nome"], h["titulo"]), self.f_big, (255, 244, 220), (200, 112))
        y = 176
        for ln in wrap(h["desc"], self.f_txt, 880):
            self.text(ln, self.f_txt, (240, 236, 250), (200, y), shadow=False)
            y += 30
        y += 10
        self.text("Evidências reunidas: %d / 100" % self.evid, self.f_med, (120, 236, 196), (200, y))
        self.text("Suspeita do regime: %d / 100" % self.susp, self.f_med, (255, 130, 160), (200, y + 36))
        self.text("Segredos: %d / 3" % len(self.secrets), self.f_ch, (255, 214, 120), (200, y + 70), shadow=False)
        y += 90
        self.text("Abusos documentados:", self.f_med, (255, 214, 120), (200, y))
        for i, (k, lab) in enumerate(PROBLEMS):
            done = k in self.flags
            bx, by = 208, y + 38 + i * 28
            pygame.draw.rect(self.screen, (20, 10, 34), (bx, by, 18, 18))
            pygame.draw.rect(self.screen, (255, 240, 214), (bx + 2, by + 2, 14, 14))
            if done:
                pygame.draw.polygon(self.screen, (40, 170, 120), [(bx + 4, by + 9), (bx + 8, by + 13), (bx + 15, by + 3), (bx + 15, by + 6), (bx + 8, by + 16), (bx + 4, by + 12)])
            self.text(lab, self.f_ch, (244, 240, 252), (bx + 30, by + 1), shadow=False)
        y0 = y - 90
        self.text("Missões da rede:", self.f_med, (255, 214, 120), (780, y0))
        rows = [("mario", "Contato: Professor Mário"),
                ("rota", "Linha: " + (ROUTES[self.route]["nome"] if self.route else "a escolher"))]
        if self.route:
            rows += [(sid, STEP_DEFS[sid]["label"]) for sid in ROUTES[self.route]["steps"]]
        for i, (sid, lab) in enumerate(rows):
            bx, by = 788, y0 + 38 + i * 28
            pygame.draw.rect(self.screen, (20, 10, 34), (bx, by, 18, 18))
            pygame.draw.rect(self.screen, (255, 240, 214), (bx + 2, by + 2, 14, 14))
            if sid in self.done_steps:
                pygame.draw.polygon(self.screen, (40, 170, 120), [(bx + 4, by + 9), (bx + 8, by + 13), (bx + 15, by + 3), (bx + 15, by + 6), (bx + 8, by + 16), (bx + 4, by + 12)])
            self.text(lab, self.f_ch, (244, 240, 252), (bx + 30, by + 1), shadow=False)
        self.text("Mochila: " + (", ".join(ITEMS[i]["nome"] for i in self.pack) or "vazia"), self.f_ch,
                  (190, 240, 255), (788, y0 + 38 + len(rows) * 28 + 10), shadow=False)
        self.text("Prazo restante: " + self.fmt_time(TIME_LIMIT - self.clock), self.f_ch,
                  (255, 130, 160), (788, y0 + 38 + len(rows) * 28 + 44), shadow=False)
        self.text("Objetivo: " + self.objective(), self.f_sm, (255, 238, 170), (200, 596))

    def draw_ending(self):
        s = self.screen
        a = clamp(self.ending["t"] / 1.5, 0, 1)
        self.backdrop()
        self.panel((100, 24, 1080, 672), 235)
        col = lambda c: tuple(int(v * a) for v in c)
        self.text("FIM DA OPERAÇÃO", self.f_big, col((255, 214, 120)), (640, 64), center=True, shadow=False)
        y = 112
        for ln in wrap(self.ending["text"], self.f_ch, 960):
            self.text(ln, self.f_ch, col((244, 240, 250)), (150, y), shadow=False)
            y += 28
        y = max(y + 14, 556)
        self.text("Evidências reunidas: %d" % self.evid, self.f_med, col((120, 236, 196)), (150, y), shadow=False)
        self.text("Suspeita do regime: %d" % self.susp, self.f_med, col((255, 130, 160)), (150, y + 36), shadow=False)
        self.text("Tempo de operação: %s (limite 15:00)" % self.fmt_time(self.ending.get("clock", 0)), self.f_med,
                  col((200, 190, 255)), (150, y + 72), shadow=False)
        if self.ending["t"] > 1.5:
            self.text("[Enter] voltar ao menu", self.f_sm, (255, 214, 120), (1140, 662), right=True, shadow=False)

    def draw_pause(self):
        self.panel((400, 230, 480, 240), 240)
        self.text("PAUSA", self.f_big, (255, 244, 220), (640, 290), center=True)
        self.text("Esc / Enter: continuar", self.f_txt, (240, 236, 250), (640, 364), center=True)
        self.text("Q: voltar ao menu", self.f_txt, (240, 236, 250), (640, 404), center=True)

    # -------------------------------------------------------------- draw
    def draw(self):
        st = self.state
        if st in ("intro", "ending"):
            if st == "intro":
                self.draw_intro()
            else:
                self.draw_ending()
            return
        if st == "title":
            self.screen.blit(pygame.transform.scale(self.copa.draw(), (W, H)), (0, 0))
            self.draw_title()
            return
        base = self.pause_from if st == "pause" else st
        if self.rk and base in ("room", "dialogue", "entrega"):
            self.draw_room()
            self.draw_room_hud()
            if st == "dialogue":
                self.draw_dialogue()
            elif st == "entrega":
                self.draw_entrega()
            elif st == "pause":
                self.draw_pause()
            self.draw_toast()
            return
        if base in ("home", "stash", "confirm", "sleep"):
            self.draw_home()
            self.draw_home_hud()
            if st == "stash":
                self.draw_stash()
            elif st == "confirm":
                self.draw_confirm()
            elif st == "sleep":
                self.draw_sleep()
            elif st == "pause":
                self.draw_pause()
            self.draw_toast()
            return
        self.render_world()
        self.post_fx()
        pygame.transform.scale(self.frame, (W, H), self.screen)
        self.draw_hud()
        self.draw_bubbles()
        if st == "dialogue":
            self.draw_dialogue()
        elif st == "puzzle":
            self.draw_puzzle()
        elif st == "journal":
            self.draw_journal()
        elif st == "pause":
            self.draw_pause()
        elif st == "play":
            self.text("Tab: diário    Esc: pausa", self.f_xs, (255, 255, 255), (W - 18, 12), right=True)
            if self.listen > 0:
                pct = clamp(self.listen / ESCUTA_T, 0, 1)
                pygame.draw.rect(self.screen, (20, 10, 34), (490, 640, 300, 22))
                pygame.draw.rect(self.screen, (120, 236, 196), (494, 644, int(292 * pct), 14))
                self.text("Escutando o grampo... fique parado", self.f_sm, (255, 244, 220), (640, 622), center=True)
            tg = self.bribe_target()
            if tg:
                self.text("P: subornar %s (Cr$ %d)" % (tg.name, BRIBE_COST), self.f_sm, (255, 214, 120),
                          (640, 690), center=True)


if __name__ == "__main__":
    Game().run()
