#!/usr/bin/env python3
"""test_pipeline.py (S5) -- the whole program (kernels/main.s) on the Rust emulator, from the seed HD in ROM to the arm command stream.
Reference (Python, all normative models): improve_hd -> hd2nl -> place_ref.order(seed 1) -> route_ref.route, plus PROGRAM_ROM of the child image.
Checks: decoded arm commands == reference commands (place, rom, track, via, in order); the child ROM image (decoded rom commands) == own image with the improved records;
V_ERR == 0.  Prints measured instruction counts."""
import os, struct, subprocess, sys, tempfile, time
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, hd2bin, hd2nl, lay, place_ref, route_ref, ref_improve, hd as H
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
hdname = os.environ.get('HDFILE', 'cpu_mod.hd'); SEED = int(os.environ.get('PLACE_SEED', '1'))
h0 = H.read(open(os.path.join(HERE, '..', 'hd', 'm18', hdname)).read())
tmp = tempfile.mkdtemp(); open(tmp + '/hd_data.s', 'w').write(hd2bin.text(h0))
open(tmp + '/const.s', 'w').write(f'.equ RNG_SEED, {place_ref.Rng(SEED).s}\n')
# macros are defined by the first file that needs them: improve.s, route1.s, route2.s precede their users
files = [tmp + '/const.s'] + [os.path.join(K, f) for f in ('start.s', 'memmap.s', 'memmap_route.s', 'memmap_imp.s', 'memmap_hd.s', 'improve.s', 'route1.s', 'route2.s', 'route3.s', 'hdflat.s', 'main.s', 'build_graph.s', 'lpa_level.s', 'chain.s', 'place_order.s')] + [tmp + '/hd_data.s']
_, img = rvasm.assemble(files, tmp + '/o'); img = bytes(img); open(tmp + '/rom.bin', 'wb').write(img); print('program ROM bytes (code + HD data):', len(img))
t0 = time.time()
rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--armlog', tmp + '/arm.log', '--dump-ram', tmp + '/out.bin', '--max', '3000000000'], capture_output=True, text=True)
assert rp.returncode == 0, rp.stderr
ni = int(rp.stderr.split('instructions')[1].split()[0]); print(f'run: {ni} instructions, {time.time() - t0:.1f} s on the emulator')
o = open(tmp + '/out.bin', 'rb').read(); err = struct.unpack_from('<I', o, 0x70)[0]
def s16(v): return v - 65536 if v >= 32768 else v
regs = [0] * 16; got = []
for l in open(tmp + '/arm.log'):
    r, v = map(int, l.split()); regs[r] = v
    if r != 15: continue
    w = lambda i: regs[i] | regs[i + 1] << 8
    ax, ay, bx, by = s16(w(0)), s16(w(2)), s16(w(4)), s16(w(6))
    if v == 1: got.append(('place', regs[8], ax, ay, regs[9], regs[10]))
    elif v == 3: got.append(('rom', ax, ay, w(4), regs[10]))
    elif v == 4: got.append(('track', regs[10], ax, ay, bx, by))
    elif v == 5: got.append(('via', ax, ay))
    else: got.append(('?', v))
# reference
h1, rep = ref_improve.improve_hd(h0)
text, n = hd2nl.convert(h1, h1.params['ram_abits']); open(tmp + '/ref.nl', 'w').write(text); nl = lay.read_nl(tmp + '/ref.nl')
order = place_ref.order(nl, seed=SEED); cmds, info = route_ref.route(nl, order); cmds = [tuple(c) for c in cmds]
sym = {}
for l in open(tmp + '/o/symbols.txt'):
    if '=' in l: k, v = l.split('='); sym[k.strip()] = int(v.strip(), 0)
child = bytearray(img); base = 1 << 18; m0 = sym['hd_mods'] - base
for i, mod in enumerate(h1.modules):
    off = m0 + struct.unpack_from('<H', img, sym['hd_modoff'] - base + 2 * i)[0]; ext = hd2bin.extent(h0.modules[i])
    rec = hd2bin.record(mod); child[off:off + ext] = bytes(rec) + bytes(ext - len(rec))
xr, y21 = info['pb']['rom'], info['Y'][21]
OX = info['W'] + 8 - info['pb']['arm']; OY = -info['Y'][21]       # child frame offset the program sets (kernels/main.s): child is 8 cells right of the parent, same rows
def shift(c):
    if c[0] == 'place': return ('place', c[1], c[2] + OX, c[3] + OY) + tuple(c[4:])
    if c[0] == 'track': return ('track', c[1], c[2] + OX, c[3] + OY, c[4] + OX, c[5] + OY)
    return ('via', c[1] + OX, c[2] + OY)
cmds = [shift(c) for c in cmds]
places = [c for c in cmds if c[0] == 'place']; wires = [c for c in cmds if c[0] != 'place']
roms = [('rom', xr + OX, y21 + OY, a, v) for a, v in enumerate(child[:sym['hd_end'] - base]) if v]
exp = places + roms + wires
ok = got == exp
print(f'{len(got)} commands (reference {len(exp)}: {len(places)} place, {len(roms)} rom bytes, {len(wires)} track/via); board W={info["W"]} H={info["H"]}; V_ERR={err}:', 'IDENTICAL' if ok and err == 0 else 'MISMATCH')
if not ok:
    for i, (g, e) in enumerate(zip(got, exp)):
        if g != e: print(' first difference at', i, g, e); break
print('child ROM image', 'EQUALS' if bytes(child[:sym['hd_end'] - base]) == img[:sym['hd_end'] - base] else 'differs from', 'the image of this program (fixed point when equal)')
open(tmp + '/summary.txt', 'w').write(f'{ni}\n'); print('RESULT', 'PASS' if ok and err == 0 else 'FAIL'); sys.exit(0 if ok and err == 0 else 1)
