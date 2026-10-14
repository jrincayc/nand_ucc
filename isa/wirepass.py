"""Core wire pass: stream encoder (Python) and decoder (Hack-vN asm)."""
from builder import uid, lo, hi, ARM, OX, OY, ROW_Y, X_START, inc16_by2
import machine_row as MR


def eg(d):                       # Exp-Golomb k=2 of value d >= 0  ->  bit string  (n = d + 4)
    n = d + 4; z = n.bit_length() - 3
    return '0' * z + format(n, 'b')


def enc_ref(i, r):
    """Bits for the source ref r of a destination whose position is node index i."""
    if r[0] == 'n':
        d = i - r[1]
        if d >= 1: return eg(d)
        return eg(0) + '01' + eg(1 - d)
    if r[0] == 'rom': return eg(0) + '00' + format(r[1], '03b')
    if r[0] == 'tie': return eg(0) + '10'
    raise ValueError(r)


def encode_core(R, outs, core_end):
    bits = []
    for i in range(core_end):
        if R.kind[i] == 'dff': bits.append(enc_ref(i, R.a[i]))
        else: bits += [enc_ref(i, R.a[i]), enc_ref(i, R.b[i])]
    for grp in ('rom_addr', 'arm_addr', 'wdata'):
        bits += [enc_ref(core_end, r) for r in outs[grp]]
    bits.append(enc_ref(core_end, outs['arm_en']))
    s = ''.join(bits); s += '0' * (-len(s) % 8)
    return bytes(int(s[k:k + 8], 2) for k in range(0, len(s), 8)), len(s)


def inc2_odd(a, var):
    """var += 2 where var is always odd: carry iff new low byte == 1."""
    t = uid('io')
    a.ldDc(2); a.A(var); a.C('M', 'D+M'); a.C('D', 'M-1'); a.jump(t, 'JNE', 'D')
    a.A(var + 1); a.C('M', 'M+1')
    a.label(t)


def build_ref_sub(L, V):
    """Subroutine 'ref': decode one source ref and issue WIRE(source -> (DX, DY)).  XS = dest-node x + 9."""
    a = L.a
    R0, R1, XS, DX, DY, XD, FV, CN = (V[k] for k in ('R0', 'R1', 'XS', 'DX', 'DY', 'XD', 'FV', 'CN'))
    def body():
        L.save_ret('RET3')
        esc, emit, rom, fwd, tie, done = (uid(k) for k in ('esc', 'emit', 'rom', 'fwd', 'tie', 'done'))
        L.call('readEG')
        a.ldD(R1 + 1); a.jump(esc + 'n', 'JNE', 'D')              # n >= 256: normal
        a.ldD(R1); a.A(4); a.C('D', 'D-A'); a.jump(esc, 'JEQ', 'D')
        a.label(esc + 'n')
        L.call('shl1')
        a.ldD(XS); a.stD(R0); a.ldD(XS + 1); a.stD(R0 + 1)
        L.call('sub16')
        a.label(emit)
        a.ldD(R0); a.stD(ARM + 0); a.ldD(R0 + 1); a.stD(ARM + 1)
        a.ldD(DX); a.stD(ARM + 4); a.ldD(DX + 1); a.stD(ARM + 5)
        a.ldD(DY); a.stD(ARM + 6)
        a.setc(ARM + 15, 2)
        a.jump(done)
        # ---- escapes
        a.label(esc)
        a.setc(CN, 2); L.call('getbits')
        a.ldD(FV); a.jump(rom, 'JEQ', 'D')
        a.C('D', 'D-1'); a.jump(fwd, 'JEQ', 'D')
        a.label(tie)                                               # FV == 2: remember the destination, wire later
        a.ldD(DX); a.stD(XD); a.ldD(DX + 1); a.stD(XD + 1)
        a.jump(done)
        a.label(fwd)                                               # Sx = XS + 2n - 18
        L.call('readEG'); L.call('shl1')
        a.ldD(XS); a.stD(R0); a.ldD(XS + 1); a.stD(R0 + 1)
        L.call('add16')
        a.setc(R1, 18); a.setc(R1 + 1, 0); L.call('sub16')
        a.jump(emit)
        a.label(rom)
        a.setc(CN, 3); L.call('getbits')
        a.setc(ARM + 0, lo(OX + 1)); a.setc(ARM + 1, hi(OX + 1))
        a.ldDc(ROW_Y); a.A(FV); a.C('D', 'D+M'); a.stD(ARM + 2)
        a.ldD(DX); a.stD(ARM + 4); a.ldD(DX + 1); a.stD(ARM + 5)
        a.ldD(DY); a.stD(ARM + 6)
        a.setc(ARM + 15, 2)
        a.setc(ARM + 2, lo(ROW_Y))
        a.label(done)
        L.ret(saved=True, slot='RET3')
    return body


def build_core_wires(a, L, V, nd, core_end):
    """Main code: init, DFF loop, NAND loop, output groups + EN."""
    a.setc(V['BN'], 0)
    a.A(('lo', 'stream')); a.C('D', 'A'); a.stD(V['BP']); a.A(('hi', 'stream')); a.C('D', 'A'); a.stD(V['BP'] + 1)
    a.setc(ARM + 2, lo(ROW_Y)); a.setc(ARM + 3, hi(ROW_Y)); a.setc(ARM + 7, 0)
    a.setc(V['DX'], lo(X_START)); a.setc(V['DX'] + 1, hi(X_START))
    a.setc(V['XS'], lo(X_START + 9)); a.setc(V['XS'] + 1, hi(X_START + 9))
    a.setc(V['DY'], lo(ROW_Y))
    for count, pins, tag in ((nd, 1, 'dffl'), (core_end - nd, 2, 'nandl')):
        a.setc(V['C'], lo(count)); a.setc(V['C'] + 1, hi(count))
        a.label(tag)
        a.setc(V['DY'], lo(ROW_Y)); L.call('ref')
        if pins == 2:
            a.setc(V['DY'], lo(ROW_Y + 1)); L.call('ref')
        inc16_by2(a, V['DX'], uid('dx')); inc2_odd(a, V['XS'])
        from builder import dec16_loop
        dec16_loop(a, V['C'], tag)
    # output groups: (dest x, dest y0, count)
    for gx, gy, cnt, tag in ((OX, ROW_Y, 12, 'g1'), (OX, OY, 4, 'g2'), (OX + 1, OY, 8, 'g3'), (OX, OY + 4, 1, 'g4')):
        a.setc(V['DX'], lo(gx)); a.setc(V['DX'] + 1, hi(gx)); a.setc(V['DY'], lo(gy)); a.setc(V['K'], cnt)
        a.label(tag)
        L.call('ref'); a.A(V['DY']); a.C('M', 'M+1')
        a.dec_loop(V['K'], tag)
