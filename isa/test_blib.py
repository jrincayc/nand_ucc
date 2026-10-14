import random, sys
import common, isahack, builder as B
from blib import Lib
from isahack import Asm

def mk(setup, calls, ret_halt=True):
    vs = B.Vars(); V = {}
    for n, sz in [('R0',2),('R1',2),('U',1),('RET',1),('RET2',1),('BP',2),('BB',1),('BN',1),('Z',1),('CN',1),('FV',1),('TB',1)]:
        V[n] = vs.v(n, sz)
    a = Asm(); L = Lib(a, V)
    setup(a, V)
    for c in calls: L.call(c)
    a.label('halt'); a.jump('halt')
    L.build()
    # emit subs (including transitively used ones)
    done = set()
    while True:
        todo = sorted(L.used - done)
        if not todo: break
        for n in todo:
            a.label(n); L.fns[n](); done.add(n)
    L.finalize()
    return a, V

def rd16(m, v): return m.ram[v] | m.ram[v + 1] << 8
rng = random.Random(5)
bad = 0
for trial in range(300):
    x, y = rng.randrange(65536), rng.randrange(65536)
    if trial % 7 == 0: y = x
    for op, fn in (('add16', lambda p, q: (p + q) & 0xFFFF), ('sub16', lambda p, q: (p - q) & 0xFFFF)):
        def setup(a, V):
            for v, val in ((V['R0'], x), (V['R1'], y)):
                a.setc(v, val & 255); a.setc(v + 1, val >> 8)
        a, V = mk(setup, [op])
        m, steps, hw = B.run_program(a.assemble())
        if rd16(m, V['R0']) != fn(x, y): bad += 1; print('FAIL', op, x, y, rd16(m, V['R0']), fn(x, y))
    def setup(a, V):
        a.setc(V['R1'], x & 255); a.setc(V['R1'] + 1, x >> 8)
    a, V = mk(setup, ['shl1']); m, _, _ = B.run_program(a.assemble())
    if rd16(m, V['R1']) != (2 * x) & 0xFFFF: bad += 1; print('FAIL shl1', x)
print('arith bad', bad)

# Exp-Golomb k=2: encode n = d+4 for d>=0 ; stream of random values
def eg_bits(d):
    n = d + 4; L = n.bit_length(); z = L - 3
    return '0' * z + format(n, 'b')
vals = [rng.choice([0,1,1,1,2,3,5,9,20,100,500,900]) for _ in range(40)]
bits = ''.join(eg_bits(v) for v in vals); bits += '0' * (-len(bits) % 8)
data = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
a_ = None
def setup(a, V):
    a.setc(V['BN'], 0)
    a.A('stream'); a.C('D', 'A') if False else None
vs = B.Vars(); V = {}
for n, sz in [('R0',2),('R1',2),('U',1),('RET',1),('RET2',1),('BP',2),('BB',1),('BN',1),('Z',1),('CN',1),('FV',1),('TB',1),('OUT',2),('K',1)]:
    V[n] = vs.v(n, sz)
a = Asm(); L = Lib(a, V)
a.setc(V['BN'], 0); a.setc(V['BP'], 0); a.setc(V['BP'] + 1, 0)
a.A(('lo', 'stream')); a.C('D', 'A'); a.stD(V['BP']); a.A(('hi', 'stream')); a.C('D', 'A'); a.stD(V['BP'] + 1)
a.setc(V['OUT'], 0x00); a.setc(V['OUT'] + 1, 0x01)    # output pointer 0x100
a.setc(V['K'], len(vals))
a.label('lp')
L.call('readEG')
a.A(V['R1']); a.C('D', 'M'); a.A(V['OUT']); a.AP(); a.C('M', 'D'); a.inc16(V['OUT'], 'o1')
a.A(V['R1'] + 1); a.C('D', 'M'); a.A(V['OUT']); a.AP(); a.C('M', 'D'); a.inc16(V['OUT'], 'o2')
a.dec_loop(V['K'], 'lp')
a.label('halt'); a.jump('halt')
L.build()
done = set()
while True:
    todo = sorted(L.used - done)
    if not todo: break
    for n in todo: a.label(n); L.fns[n](); done.add(n)
a.label('stream'); a.data(data)
L.finalize()
m, steps, hw = B.run_program(a.assemble())
got = [m.ram[0x100 + 2 * i] | m.ram[0x101 + 2 * i] << 8 for i in range(len(vals))]
print('EG', 'PASS' if got == [v + 4 for v in vals] else ('FAIL', got[:8], [v+4 for v in vals][:8]), 'instrs', steps)
