"""Quine builder program for Hack-vN (milestone 2).  Pieces are assembled into one Asm and checked against the
reference command stream machine_row.commands.  Variables live in RAM at fixed addresses (see VARS)."""
import sys, random
import common, isahack, machine_row as MR
from common import ARM_BASE as ARM, ROM_BASE
from isahack import Asm

KIND = {0: 'nand', 1: 'dff', 2: 'rom', 3: 'arm'}
OX, OY = 0, MR.STRIDE            # child arm origin relative to the issuing arm
ROW_Y = OY + MR.ARM_H            # y of the node row
X_START = OX + 6                 # x of node 0


class Vars:
    """Fixed RAM layout; 16-bit variables are little endian."""
    def __init__(self): self.next, self.names = 0, {}
    def v(self, name, size=2):
        self.names[name] = self.next; self.next += size; return self.names[name]


def lo(v): return v & 255
def hi(v): return v >> 8


# ---- 16-bit helpers (D is 8 bit; no carry flag) -------------------------------------------------------------
def inc16_by2(a, var, tag):
    """var += 2 where var is always even (so carry iff the new low byte is 0)."""
    a.ldDc(2); a.A(var); a.C('M', 'D+M'); a.C('D', 'M')
    a.jump(tag, 'JNE', 'D')
    a.A(var + 1); a.C('M', 'M+1')
    a.label(tag)


_uid = [0]
def uid(p='t'):
    _uid[0] += 1; return f'{p}{_uid[0]}'


def dec16_loop(a, var, lab):
    """var -= 1; if var != 0 goto lab   (16 bit)."""
    t1, t2 = uid(), uid()
    a.A(var); a.C('D', 'M'); a.jump(t1, 'JNE', 'D')   # lo == 0 -> borrow
    a.A(var + 1); a.C('M', 'M-1')
    a.label(t1)
    a.A(var); a.C('M', 'M-1'); a.C('D', 'M'); a.jump(lab, 'JNE', 'D')
    a.A(var + 1); a.C('D', 'M'); a.jump(lab, 'JNE', 'D')


PLACE_HOOK = [None]


def place_one(a, X):
    if PLACE_HOOK[0]:
        return PLACE_HOOK[0]()
    a.A(X); a.C('D', 'M'); a.stD(ARM + 0)
    a.A(X + 1); a.C('D', 'M'); a.stD(ARM + 1)
    a.setc(ARM + 15, 1)
    inc16_by2(a, X, uid('px'))


def place_run(a, V, kind, count):
    """Place `count` (>0) nodes of `kind` at the running x."""
    a.setc(ARM + 8, kind)
    a.setc(V['C'], lo(count)); a.setc(V['C'] + 1, hi(count))
    l = uid('pr')
    a.label(l); place_one(a, V['X']); dec16_loop(a, V['C'], l)


def build_place_pass(a, V, plan):
    """plan: dict(core_dffs, pre_nands, words, tail_nands).  Row layout (see machine_row.build):
       DFFs, P NANDs, then per word [2 NAND, 8 x (DFF, 3 NAND)], then tail NANDs, then the tie NAND."""
    a.setc(ARM + 9, 0)                       # ANGLE 0
    a.setc(ARM + 2, lo(ROW_Y)); a.setc(ARM + 3, hi(ROW_Y))
    a.setc(V['X'], lo(X_START)); a.setc(V['X'] + 1, hi(X_START))
    place_run(a, V, 1, plan['core_dffs'])
    place_run(a, V, 0, plan['pre_nands'])
    # words
    a.setc(V['W'], plan['words'] & 255)
    lw = uid('word')
    a.label(lw)
    a.setc(ARM + 8, 0); place_one(a, V['X']); place_one(a, V['X'])
    a.setc(V['J'], 8)
    lj = uid('bit')
    a.label(lj)
    a.setc(ARM + 8, 1); place_one(a, V['X'])
    a.setc(ARM + 8, 0); place_one(a, V['X']); place_one(a, V['X']); place_one(a, V['X'])
    a.dec_loop(V['J'], lj)
    a.dec_loop(V['W'], lw)
    place_run(a, V, 0, plan['tail_nands'] + 1)      # +1: the tie-high NAND


def build_rom_arm(a, V):
    """Place the child's ROM and ARM (after the row)."""
    a.setc(ARM + 9, 0)
    a.setc(ARM + 0, lo(OX)); a.setc(ARM + 1, hi(OX))
    a.setc(ARM + 2, lo(ROW_Y)); a.setc(ARM + 3, hi(ROW_Y))
    a.setc(ARM + 8, 2); a.setc(ARM + 15, 1)
    a.setc(ARM + 2, lo(OY)); a.setc(ARM + 3, hi(OY))
    a.setc(ARM + 8, 3); a.setc(ARM + 15, 1)


def build_rom_copy(a, V, end='end'):
    """PROGRAM_ROM every non-zero byte of our own ROM image [ROM_BASE, end) into the child's ROM."""
    a.setc(ARM + 0, lo(OX)); a.setc(ARM + 1, hi(OX))
    a.setc(ARM + 2, lo(ROW_Y)); a.setc(ARM + 3, hi(ROW_Y))
    a.setc(V['P'], lo(ROM_BASE)); a.setc(V['P'] + 1, hi(ROM_BASE))
    a.setc(V['I'], 0); a.setc(V['I'] + 1, 0)
    l, nz, done = uid('rc'), uid('nz'), uid('rd')
    a.label(l)
    a.A(V['P']); a.AP(); a.C('D', 'M'); a.jump(nz, 'JEQ', 'D')
    a.stD(ARM + 10)
    a.ldD(V['I']); a.stD(ARM + 4); a.ldD(V['I'] + 1); a.stD(ARM + 5)
    a.setc(ARM + 15, 3)
    a.label(nz)
    a.inc16(V['P'], uid('c')); a.inc16(V['I'], uid('c'))
    a.ldD(V['P'] + 1); a.A(('hi', end)); a.C('D', 'D-A'); a.jump(l, 'JNE', 'D')
    a.ldD(V['P']); a.A(('lo', end)); a.C('D', 'D-A'); a.jump(l, 'JNE', 'D')


def plan_for(R, core_end):
    kinds = R.kind
    nd = 0
    while kinds[nd] == 'dff': nd += 1
    # first RAM word starts at the first dff after the core DFFs, minus the 2 nwen/wen NANDs before it
    first = next(i for i in range(nd, len(kinds)) if kinds[i] == 'dff') - 2
    words = sum(1 for i in range(first, len(kinds)) if kinds[i] == 'dff') // 8
    word_end = first + words * 34
    return dict(core_dffs=nd, pre_nands=first - nd, words=words, tail_nands=len(kinds) - word_end)


# ---- checking ------------------------------------------------------------------------------------------------
def decode_cmds(log):
    """Arm write log -> semantic command tuples."""
    out = []
    for s in common.snapshots(log):
        r = s[:11]; cmd = s[11]
        x, y = r[0] | r[1] << 8, r[2] | r[3] << 8
        if cmd == 1: out.append(('place', KIND[r[8]], x, y)); assert r[9] == 0
        elif cmd == 2: out.append(('wire', x, y, r[4] | r[5] << 8, r[6] | r[7] << 8))
        elif cmd == 3: out.append(('rom', x, y, r[4] | r[5] << 8, r[10]))
        elif cmd == 0: pass
        else: raise ValueError(cmd)
    return out


def run_program(code, ram=None, limit=50_000_000):
    m = common.Machine(); m.load_rom(0, code)
    import os
    if os.environ.get('RAMFILL', '1') == '1': m.ram[:] = b'\xff' * len(m.ram)   # built RAM powers up as all 1s
    cpu = isahack.CPU(m); steps = 0; hw = 0
    w0 = m.wr
    def wr(a, v):
        nonlocal hw
        if (a & 0x1FFF) < ARM: hw = max(hw, (a & 0x1FFF) + 1)
        w0(a, v)
    m.wr = wr
    while cpu.step():
        steps += 1
        if steps > limit: raise RuntimeError('did not halt')
    return m, steps, hw


if __name__ == '__main__':
    ab = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    R, outs, core_end, c = MR.build(ab)
    plan = plan_for(R, core_end)
    vs = Vars(); V = dict(X=vs.v('X'), C=vs.v('C'), W=vs.v('W', 1), J=vs.v('J', 1), P=vs.v('P'), I=vs.v('I'))
    a = Asm(); build_place_pass(a, V, plan); build_rom_arm(a, V); build_rom_copy(a, V)
    a.label('halt'); a.jump('halt'); a.label('end')
    code = a.assemble()
    ref = [t for t in MR.commands(R, outs, code, OX, OY) if t[0] in ('place', 'rom')]
    m, steps, hw = run_program(code)
    got = [t for t in decode_cmds(m.armlog) if t[0] in ('place', 'rom')]
    print('code bytes', len(code), 'instrs', steps, 'accesses', m.accesses, 'RAM high-water', hw)
    print('PASS' if got == ref else 'FAIL', len(got), len(ref))
    if got != ref:
        for i, (g, e) in enumerate(zip(got, ref)):
            if g != e: print(i, g, e); break
