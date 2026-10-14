"""Assemble the builder piece by piece and compare with the reference command stream."""
import sys
import common, isahack, machine_row as MR
import builder as B
from builder import *
from blib import Lib
import wirepass as WP
from isahack import Asm


def make(ab, upto='core'):
    R, outs, core_end, c = MR.build(ab)
    plan = plan_for(R, core_end)
    vs = Vars(); V = {}
    for n, sz in [('X', 2), ('C', 2), ('W', 1), ('J', 1), ('P', 2), ('I', 2), ('R0', 2), ('R1', 2), ('U', 1), ('RET', 2),
                  ('RET2', 2), ('RET3', 2), ('BP', 2), ('BB', 1), ('BN', 1), ('Z', 1), ('CN', 1), ('FV', 1), ('TB', 1),
                  ('DX', 2), ('DY', 1), ('XS', 2), ('XD', 2), ('K', 1), ('TX', 2)]:
        V[n] = vs.v(n, sz)
    a = Asm(); L = Lib(a, V)
    def placesub():
        L.call('place1')
    B.PLACE_HOOK[0] = placesub
    L.fns = {}
    build_place_pass(a, V, plan)
    # tie output site x = X - 1  (X is the x after the tie NAND)
    a.ldD(V['X']); a.jump('tx0', 'JNE', 'D')
    a.A(V['X'] + 1); a.C('D', 'M-1'); a.stD(V['TX'] + 1); a.jump('tx1')
    a.label('tx0'); a.ldD(V['X'] + 1); a.stD(V['TX'] + 1)
    a.label('tx1'); a.ldD(V['X']); a.C('D', 'D-1'); a.stD(V['TX'])
    build_rom_arm(a, V); build_rom_copy(a, V)
    nd = plan['core_dffs']
    WP.build_core_wires(a, L, V, nd, core_end)
    # deferred run wires: tie -> reset gate pins
    for pin in (0, 1):
        a.ldD(V['TX']); a.stD(ARM + 0); a.ldD(V['TX'] + 1); a.stD(ARM + 1)
        a.ldD(V['XD']); a.stD(ARM + 4); a.ldD(V['XD'] + 1); a.stD(ARM + 5)
        a.setc(ARM + 6, lo(ROW_Y + pin)); a.setc(ARM + 15, 2)
    a.label('halt'); a.jump('halt')
    L.build()
    def place1():
        B.PLACE_HOOK[0] = None
        B.place_one(a, V['X']); L.ret()
    L.fns['place1'] = place1; L.used.add('place1')
    done = set()
    L.subs = {'ref': WP.build_ref_sub(L, V)}
    L.fns['ref'] = L.subs['ref']; L.used.add('ref')
    while True:
        todo = sorted(L.used - done)
        if not todo: break
        for n in todo: a.label(n); L.fns[n](); done.add(n)
    stream, nbits = WP.encode_core(R, outs, core_end)
    a.label('stream'); a.data(stream); a.label('end')
    return a, R, outs, core_end, c, plan, V, len(stream)


def ref_subset(R, outs, code, core_end):
    cmds = MR.commands(R, outs, code, OX, OY)
    xs = lambda i: OX + 6 + MR.PITCH * i
    out = []
    for t in cmds:
        if t[0] in ('place', 'rom'): out.append(t)
        elif t[0] == 'wire':
            dx = t[3]
            if dx < xs(core_end) or dx <= OX + 1: out.append(t)
    return out


if __name__ == '__main__':
    ab = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    a, R, outs, core_end, c, plan, V, slen = make(ab)
    code = a.assemble()
    ref = ref_subset(R, outs, code, core_end)
    m, steps, hw = B.run_program(code)
    got = [t for t in decode_cmds(m.armlog) if t[0] in ('place', 'rom', 'wire')]
    print(f'code+data {len(code)} B (stream {slen} B), instrs {steps}, accesses {m.accesses}, RAM high-water {hw}')
    gp, rp = [t for t in got if t[0] != 'wire'], [t for t in ref if t[0] != 'wire']
    gw, rw = [t for t in got if t[0] == 'wire'], [t for t in ref if t[0] == 'wire']
    print('place/rom', 'PASS' if gp == rp else 'FAIL', len(gp), len(rp))
    print('wires set', 'PASS' if sorted(gw) == sorted(rw) else 'FAIL', len(gw), len(rw))
    print('run wires last', gw[-2:] == rw[-2:])
    if sorted(gw) != sorted(rw):
        sg, sr = set(gw), set(rw)
        print('missing', sorted(sr - sg)[:5], 'extra', sorted(sg - sr)[:5])
