"""Subroutine library for the builder: 16-bit arithmetic on R0/R1, bit reader, Exp-Golomb(k=2) decoder.
Convention: leaf subroutines return through RET (2 bytes); non-leaf ones save RET in RET2."""
import isahack
from builder import uid, lo, hi, ARM


class Lib:
    def __init__(self, a, V):
        self.a, self.V, self.subs, self.used = a, V, {}, set()
        self.rets = []

    def call(self, name):
        """Call convention: D = index of the return-table entry (low byte of its address); callee stores it."""
        a = self.a
        r = uid('ret')
        self.used.add(name)
        if name == 'sub16': self.used.add('add16')
        i = len(self.rets); self.rets.append(r)
        a.A(('tab', i)); a.C('D', 'A'); a.jump(name); a.label(r)

    def ret(self, saved=False, slot=None):
        a, V = self.a, self.V
        a.ldD(V[slot or ('RET2' if saved else 'RET')]); a.A(('page',)); a.C('A', 'D'); a.AP(); a.C('', '0', 'JMP')

    def save_ret(self, slot='RET2'):
        self.a.stD(self.V[slot])

    def finalize(self):
        """Insert the jump-over and the return table at the very start (reset PC) of the image."""
        a = self.a
        head = [('A', 'start'), ('W', 7 << 13 | isahack.COMP['0'] << 6 | isahack.JUMP['JMP']), ('L', 'rettab')]
        head += [('LA', r) for r in self.rets] + [('L', 'start')]
        a.items[0:0] = head
        assert 2 * 2 + 2 * len(self.rets) <= 250

    # unsigned x < y  ->  jump to lab_lt, else fall through   (x, y byte variables)
    def ult(self, x, y, lab_lt):
        a = self.a
        xn, ge, tl = uid('xn'), uid('ge'), uid('tl')
        a.ldD(x); a.jump(xn, 'JLT', 'D')
        a.ldD(y); a.jump(lab_lt, 'JLT', 'D')              # x < 128 <= y
        a.A(x); a.C('D', 'M'); a.A(y); a.C('D', 'D-M'); a.jump(lab_lt, 'JLT', 'D'); a.jump(ge)
        a.label(xn)
        a.ldD(y); a.jump(ge, 'JGE', 'D')                  # x >= 128 > y
        a.A(x); a.C('D', 'M'); a.A(y); a.C('D', 'D-M'); a.jump(lab_lt, 'JLT', 'D')
        a.label(ge)

    def build(self):
        a, V = self.a, self.V
        R0, R1, U, BP, BB, BN = V['R0'], V['R1'], V['U'], V['BP'], V['BB'], V['BN']

        def add16():
            a.stD(V['RET'])
            a.label('add16_body')
            nc = uid('nc')
            a.ldD(R0); a.stD(U)
            a.A(R1); a.C('D', 'D+M'); a.stD(R0)
            a.A(R0 + 1); a.C('D', 'M'); a.A(R1 + 1); a.C('D', 'D+M'); a.stD(R0 + 1)
            self.ult(R0, U, nc + 'c')                      # sum < a  -> carry
            a.jump(nc)
            a.label(nc + 'c'); a.A(R0 + 1); a.C('M', 'M+1')
            a.label(nc)
            self.ret()

        def sub16():
            # R0 -= R1  as  R1 = -R1 ; R0 += R1  (falls into add16's body)
            a.stD(V['RET'])
            z, out = uid('ng'), uid('no')
            a.ldD(R1); a.jump(z, 'JEQ', 'D')
            a.A(R1); a.C('M', '-M'); a.A(R1 + 1); a.C('M', '!M'); a.jump(out)
            a.label(z); a.A(R1 + 1); a.C('M', '-M')
            a.label(out)
            a.jump('add16_body')

        def shl1():
            a.stD(V['RET'])                                         # R1 += R1
            ng, dn = uid('ng'), uid('dn')
            a.ldD(R1); a.jump(ng, 'JLT', 'D')
            a.stD(R1); a.C('D', 'D+M'); a.stD(R1)
            a.A(R1 + 1); a.C('D', 'M'); a.C('D', 'D+M'); a.stD(R1 + 1); a.jump(dn)
            a.label(ng)
            a.stD(R1); a.C('D', 'D+M'); a.stD(R1)
            a.A(R1 + 1); a.C('D', 'M'); a.C('D', 'D+M'); a.C('D', 'D+1'); a.stD(R1 + 1)
            a.label(dn)
            self.ret()

        def getbit():
            a.stD(V['RET'])                                       # D = next bit (MSB first)
            have, one, out = uid('hv'), uid('one'), uid('out')
            a.ldD(BN); a.jump(have, 'JNE', 'D')
            a.A(BP); a.AP(); a.C('D', 'M'); a.stD(BB)
            a.inc16(BP, uid('bpi'))
            a.setc(BN, 8)
            a.label(have)
            a.A(BN); a.C('M', 'M-1')
            a.ldD(BB); a.jump(one, 'JLT', 'D')
            a.stD(BB); a.C('D', 'D+M'); a.stD(BB); a.ldDc(0); a.jump(out)
            a.label(one)
            a.stD(BB); a.C('D', 'D+M'); a.stD(BB); a.ldDc(1)
            a.label(out)
            a.stD(V['TB'])
            self.ret()

        def readEG():                                       # R1 = n (leading 1 + z+2 bits), k=2
            Z = V['Z']
            self.save_ret()
            a.setc(Z, 0)
            lz, ld = uid('lz'), uid('ld')
            a.label(lz)
            self.call('getbit'); a.ldD(V['TB']); a.jump(ld, 'JNE', 'D')
            a.A(Z); a.C('M', 'M+1'); a.jump(lz)
            a.label(ld)
            a.setc(R1, 1); a.setc(R1 + 1, 0)
            a.ldD(Z); a.C('D', 'D+1'); a.C('D', 'D+1'); a.stD(Z)       # Z = z + 2 bits to read
            lb = uid('lb'); z1 = uid('z1')
            a.label(lb)
            self.call('shl1'); self.call('getbit'); a.ldD(V['TB'])
            a.jump(z1, 'JEQ', 'D')
            a.A(R1); a.C('M', 'M+1')
            a.label(z1)
            a.dec_loop(Z, lb)
            self.ret(saved=True)

        def getbits():                                      # FV = next CN bits (MSB first), CN >= 1
            self.save_ret()
            CN, FV, TB = V['CN'], V['FV'], V['TB']
            a.setc(FV, 0)
            lb = uid('gb')
            a.label(lb)
            self.call('getbit')
            a.ldD(FV); a.A(FV); a.C('D', 'D+M'); a.A(TB); a.C('D', 'D+M'); a.stD(FV)
            a.dec_loop(CN, lb)
            self.ret(saved=True)

        self.fns = dict(add16=add16, sub16=sub16, shl1=shl1, getbit=getbit, readEG=readEG, getbits=getbits)

    def emit(self):
        for name in sorted(self.used):
            self.a.label(name); self.fns[name]()
