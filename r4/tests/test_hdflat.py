#!/usr/bin/env python3
"""test_hdflat.py -- kernels/hdflat.s on the Rust emulator: the seed HD (cpu_mod.hd) is loaded into the module table, every module is improved by the assembly improver,
the module records are re-encoded, and the HD body is flattened.  Compared with the Python reference path
  improve_hd (ref_improve) -> hd2nl.convert -> route_ref.pack:   SRC (with late bits), KINDA, PTAB, V_N, number of ports, PSRC, V_NP, and the module records byte for byte."""
import os, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, hd2bin, hd2nl, lay, place_ref, route_ref, ref_improve, hd as H
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
hdname = os.environ.get('HDFILE', 'cpu_mod.hd')
h0 = H.read(open(os.path.join(HERE, '..', 'hd', 'm18', hdname)).read())
tmp = tempfile.mkdtemp(); open(tmp + '/hd_data.s', 'w').write(hd2bin.text(h0))
nm = len(h0.modules)
stub = 'start:\n    li sp, SWTOP\n    jal ra, mt_load\n    jal ra, mt_improve_all\n    jal ra, flatten\n' + ''.join(f'    li a0, {m}\n    li a1, RECBUF + {m * 128}\n    jal ra, mt_encode\n' for m in range(nm)) + 'halt:\n    j halt\n'
open(tmp + '/stub.s', 'w').write(stub)
files = [tmp + '/stub.s'] + [os.path.join(K, f) for f in ('memmap.s', 'memmap_route.s', 'memmap_imp.s', 'memmap_hd.s', 'improve.s', 'hdflat.s')] + [tmp + '/hd_data.s']
_, img = rvasm.assemble(files, tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('ROM bytes (code + HD data):', len(img))
rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--dump-ram', tmp + '/out.bin', '--max', '2000000000'], capture_output=True, text=True)
assert rp.returncode == 0, rp.stderr
o = open(tmp + '/out.bin', 'rb').read(); ni = int(rp.stderr.split('instructions')[1].split()[0])
# reference path
h1, rep = ref_improve.improve_hd(h0)
text, n = hd2nl.convert(h1, h1.params['ram_abits']); open(tmp + '/ref.nl', 'w').write(text); nl = lay.read_nl(tmp + '/ref.nl')
ram = bytearray(0x40000); route_ref.pack(nl, list(range(len(nl.nodes))), ram)
N = len(nl.nodes); NP = len(nl.ports)
psrc = [d for d in (place_ref.net_id(t, N) for _, t in nl.ports) if d is not None and d < N]
chk = {'V_N': struct.unpack_from('<I', o, 0x68)[0] == N, 'ports': struct.unpack_from('<I', o, 0x144)[0] == NP,
       'SRC': o[0x26000:0x26000 + 4 * N] == bytes(ram[0x26000:0x26000 + 4 * N]), 'KINDA': o[0x2A800:0x2A800 + N] == bytes(ram[0x2A800:0x2A800 + N]),
       'PTAB': o[0x2C000:0x2C000 + 6 * NP] == bytes(ram[0x2C000:0x2C000 + 6 * NP]),
       'PSRC': list(struct.unpack_from('<%dH' % len(psrc), o, 0x2A000)) == psrc and struct.unpack_from('<I', o, 0x6C)[0] == len(psrc),
       'ROMB/RAMB': struct.unpack_from('<2I', o, 0x130) == (nl.rom, nl.ram)}
recs = True
for m, mod in enumerate(h1.modules):
    ref = hd2bin.record(mod); got = list(o[0xA00 + m * 128:0xA00 + m * 128 + len(ref)])
    if got != ref: recs = False; print('record', mod.name, 'differs', got, ref)
chk['module records'] = recs
print(f'{N} nodes, {NP} ports; {ni} instructions (improve all modules + flatten):', ' '.join(f'{k}:{"ok" if v else "BAD"}' for k, v in chk.items()))
bad = sum(not v for v in chk.values())
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
