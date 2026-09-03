#!/usr/bin/env python3
"""Dump the placed contents of a .kicad_sch as plain text with real mm coordinates.

Reading a schematic by eye from the s-expression is slow and error-prone. This
prints symbols, wires, junctions and labels with the coordinates you need in
order to place new parts on-grid and know what a net already connects to.

    schdump.py board.kicad_sch                     # everything
    schdump.py board.kicad_sch --box 150 90 300 150   # x0 y0 x1 y1, mm
    schdump.py board.kicad_sch --what symbols wires

Coordinates are millimetres in KiCad sheet space: x grows right, y grows DOWN.
A symbol's pin at library offset (sx, sy) lands at (X + sx, Y - sy) when the
symbol is unrotated -- the library y axis is flipped relative to the sheet.
"""
import argparse
import re
import sys


def toplevel(src):
    """Yield each top-level item that follows the (lib_symbols ...) block."""
    i = src.index('\t(lib_symbols')
    d, j = 0, i
    while True:
        c = src[j]
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                break
        j += 1
    body = src[j + 1:]
    k = 0
    while k < len(body):
        if body[k] == '(':
            d, s = 0, k
            while True:
                c = body[k]
                if c == '"':
                    k += 1
                    while body[k] != '"':
                        if body[k] == '\\':
                            k += 1
                        k += 1
                elif c == '(':
                    d += 1
                elif c == ')':
                    d -= 1
                    if d == 0:
                        break
                k += 1
            yield body[s:k + 1]
        k += 1


def at(item):
    m = re.search(r'\(at ([\d.-]+) ([\d.-]+)(?: ([\d.-]+))?\)', item)
    return (float(m.group(1)), float(m.group(2)), m.group(3) or '0') if m else None


def pts(item):
    return [float(v) for p in re.findall(r'\(xy ([\d.-]+) ([\d.-]+)\)', item) for v in p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sch')
    ap.add_argument('--box', nargs=4, type=float, metavar=('X0', 'Y0', 'X1', 'Y1'),
                    help='only report items touching this mm rectangle')
    ap.add_argument('--what', nargs='+',
                    default=['symbols', 'wires', 'junctions', 'labels'],
                    choices=['symbols', 'wires', 'junctions', 'labels'])
    a = ap.parse_args()

    x0, y0, x1, y1 = a.box if a.box else (-1e9, -1e9, 1e9, 1e9)
    inside = lambda x, y: x0 <= x <= x1 and y0 <= y <= y1

    items = list(toplevel(open(a.sch).read()))

    if 'symbols' in a.what:
        rows = []
        for it in items:
            if not it.startswith('(symbol'):
                continue
            lib = re.search(r'\(lib_id "([^"]+)"', it).group(1)
            x, y, rot = at(it)
            if not inside(x, y):
                continue
            ref = re.search(r'\(property "Reference" "([^"]+)"', it)
            val = re.search(r'\(property "Value" "([^"]*)"', it)
            fp = re.search(r'\(property "Footprint" "([^"]*)"', it)
            rows.append((x, y, ref.group(1) if ref else '?',
                         val.group(1) if val else '', rot, lib,
                         fp.group(1) if fp else ''))
        print(f'=== SYMBOLS ({len(rows)}) ===')
        for x, y, ref, val, rot, lib, fp in sorted(rows):
            print(f'  {ref:8} {val:22} x={x:<8} y={y:<8} rot={rot:<4} {lib}')
            if fp:
                print(f'           {"":22} fp: {fp}')

    if 'wires' in a.what:
        rows = [pts(it) for it in items if it.startswith('(wire')]
        rows = [p for p in rows if len(p) == 4 and (inside(p[0], p[1]) or inside(p[2], p[3]))]
        print(f'\n=== WIRES ({len(rows)}) ===')
        for p in sorted(rows):
            kind = 'H' if p[1] == p[3] else 'V' if p[0] == p[2] else 'diag'
            print(f'  ({p[0]}, {p[1]}) -> ({p[2]}, {p[3]})   {kind}')

    if 'junctions' in a.what:
        rows = [at(it)[:2] for it in items if it.startswith('(junction')]
        rows = [p for p in rows if inside(*p)]
        print(f'\n=== JUNCTIONS ({len(rows)}) ===')
        for x, y in sorted(rows):
            print(f'  ({x}, {y})')

    if 'labels' in a.what:
        rows = []
        for it in items:
            if not re.match(r'\((?:global_|hierarchical_)?label', it):
                continue
            nm = re.search(r'label "([^"]+)"', it).group(1)
            x, y, rot = at(it)
            if inside(x, y):
                rows.append((x, y, rot, nm))
        print(f'\n=== LABELS ({len(rows)}) ===')
        for x, y, rot, nm in sorted(rows):
            print(f'  {nm:26} x={x:<8} y={y:<8} rot={rot}')


if __name__ == '__main__':
    sys.exit(main())
