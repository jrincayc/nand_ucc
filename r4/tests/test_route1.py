#!/usr/bin/env python3
"""test_route1.py -- kernels/route1.s (fold, sink lists, zones, lanes, x positions) on the Rust emulator against route_ref.route(...)[1]."""
import os, struct, subprocess, sys, tempfile
os.environ.update(ROM_BITS='16', AB='18', RAM_BITS='18')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools')]
import rvasm, lay, place_ref, route_ref
EXE = os.path.join(HERE, '..', 'rvemu_rs', 'target', 'release', 'rvemu'); K = os.path.join(HERE, '..', 'kernels')
tmp = tempfile.mkdtemp(); stub = tmp + '/stub.s'
open(stub, 'w').write('start:\n    jal ra, route1\n    jal ra, route2\nhalt:\n    j halt\n')
_, img = rvasm.assemble([stub, os.path.join(K, 'memmap.s'), os.path.join(K, 'memmap_route.s'), os.path.join(K, 'route1.s'), os.path.join(K, 'route2.s')], tmp + '/o'); open(tmp + '/rom.bin', 'wb').write(bytes(img)); print('kernel ROM bytes (with stub):', len(img))
def u16(b, a, n): return list(struct.unpack_from('<%dH' % n, b, a))
bad = 0
for name in ('cpu_g1.nl',):
    p = os.path.join(HERE, '..', 'hd', 'm18', name)
    if not os.path.exists(p): continue
    nl = lay.read_nl(p); N = len(nl.nodes); order = place_ref.order(nl)
    cmds, info = route_ref.route(nl, order)
    ram = bytearray(0x40000); route_ref.pack(nl, order, ram); open(tmp + '/ram.bin', 'wb').write(ram)
    rp = subprocess.run([EXE, tmp + '/rom.bin', '--rom-bits', '16', '--ab', '18', '--ram-bytes', str(0x40000), '--load-ram', tmp + '/ram.bin', '--dump-ram', tmp + '/out.bin', '--max', '500000000'], capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr
    o = open(tmp + '/out.bin', 'rb').read(); NN = N + 16; cols = info['cols']; nz = info['nz']
    chk = {'ROW': list(o[0x1000:0x1000 + N]) == info['ROW'], 'COL': u16(o, 0x2000, N) == info['COL'],
           'NOFF': u16(o, 0x4000, NN + 1) == info['NOFF'], 'NSNK': u16(o, 0x6200, len(info['NSNK'])) == info['NSNK'],
           'ZONE': list(o[0xA200:0xA200 + NN]) == info['ZONE'], 'LIDX': list(o[0xB300:0xB300 + NN]) == info['LIDX'],
           'ZW': list(o[0x17800:0x17800 + nz]) == info['ZW'], 'GXT': u16(o, 0xC400, cols) == info['GXT'],
           'IVS': u16(o, 0xC600, NN + 1) == info['IVS'], 'NI': struct.unpack_from('<I', o, 0x128)[0] == info['NI'], 'TRK': list(o[0x16000:0x16000 + info['NI']]) == info['TRK'],
           'T': u16(o, 0x17880, 22) == info['T'], 'Y': u16(o, 0x17840, 22) == info['Y'], 'H': struct.unpack_from('<I', o, 0x12C)[0] == info['H'],
           'XR/XA/XM/W': list(struct.unpack_from('<4I', o, 0x118)) == [info['pb']['rom'], info['pb']['arm'], info['pb']['ram'], info['W']]}
    ni = int(rp.stderr.split('instructions')[1].split()[0])
    print(name, N, 'gates;', ni, 'instructions;', ' '.join(f'{k}:{"ok" if v else "BAD"}' for k, v in chk.items()))
    bad += sum(not v for v in chk.values())
print('RESULT', 'PASS' if not bad else 'FAIL'); sys.exit(1 if bad else 0)
