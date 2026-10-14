"""Gate-level ACC8 CPU (see isa/ACC8.md).  Interface: in rdata[8], reset; out addr[13], wdata[8], we.
One memory address per tick, combinational read, clocked write.  States (one-hot): F0 opcode fetch,
F1 operand byte 1, F2 operand byte 2 (3-byte instructions), X execute, X2 second access of LPZ/SPZ."""
from nandgen import *

PC_RESET = 0x1000


def ao(n, pairs):
    """OR of (sel & bit) terms for single bits; pairs = [(sel, bit)]."""
    ts = [n.nand(s, b) for s, b in pairs]
    acc = ts[0]
    if len(ts) == 1:
        return n.not_(acc)
    for t in ts[1:-1]:
        acc = n.and_(acc, t)
    return n.nand(acc, ts[-1])


def build_acc8(level=2):
    n = Net(level)
    rdata = n.bus_in('rdata', 8)
    reset = n.input('reset')
    PC, P, OP = n.dff_bus(13), n.dff_bus(13), None
    OPlo, OPhi = n.dff_bus(8), n.dff_bus(5)
    ACC, IR = n.dff_bus(8), n.dff_bus(8)
    Z, C = n.dff_bus(1)[0], n.dff_bus(1)[0]
    sF0, sF1, sF2, sX, sX2 = n.dff_bus(5)
    nr = n.not_(reset)
    OP13 = OPlo + OPhi
    with n.scope('decode'):
        nir = [n.not_(b) for b in IR]
        oh3 = onehot(n, IR[:3]); oh2 = onehot(n, IR[:2])
        hi4 = lambda v: n.and_(n.and_(IR[7] if v & 8 else nir[7], IR[6] if v & 4 else nir[6]),
                               n.and_(IR[5] if v & 2 else nir[5], IR[4] if v & 1 else nir[4]))
        g_alu = hi4(0x4)
        isImm, isZp = n.and_(g_alu, nir[3]), n.and_(g_alu, IR[3])
        gf = [n.and_(g_alu, oh3[i]) for i in range(8)]        # func i of either group
        g5 = n.and_(n.and_(hi4(0x5), nir[3]), ONE)
        STZ, INCZ, DECZ, LPZ, SPZ = [n.and_(g5, oh3[i]) for i in range(5)]
        gbr = n.and_(n.and_(hi4(0x5), IR[3]), nir[2])
        g3 = n.and_(n.and_(hi4(0x8), nir[3]), nir[2])
        LDA, STA, LPA, JMP = [n.and_(g3, oh2[i]) for i in range(4)]
        gs = n.and_(n.and_(hi4(0x0), nir[3]), ONE)
        CLC, SEC, CPL, SHL, SHR, ROL, ROR = [n.and_(gs, oh3[i]) for i in range(1, 8)]
        gm = n.and_(n.and_(hi4(0x0), IR[3]), nir[2])
        LDX, STX, LDXP, STXP = [n.and_(gm, oh2[i]) for i in range(4)]
        LPZSPZ = n.or_(LPZ, SPZ)
    with n.scope('control'):
        r7, r6 = rdata[7], rdata[6]
        cls00, cls01 = n.and_(n.not_(r7), n.not_(r6)), n.and_(n.not_(r7), r6)
        cls10, cls11 = n.and_(r7, n.not_(r6)), n.and_(r7, r6)
        n.set_d(sF0, n.or_(reset, n.or_(sX2, n.or_(n.and_(sX, n.not_(LPZSPZ)), n.and_(sF0, cls11)))))
        n.set_d(sF1, n.and_(nr, n.and_(sF0, n.or_(cls01, cls10))))
        n.set_d(sF2, n.and_(nr, n.and_(sF1, IR[7])))
        n.set_d(sX, n.and_(nr, n.or_(n.or_(n.and_(sF0, cls00), n.and_(sF1, nir[7])), sF2)))
        n.set_d(sX2, n.and_(nr, n.and_(sX, LPZSPZ)))
        selpc = n.or_(sF0, n.or_(sF1, sF2))
        selP = n.and_(sX, n.or_(n.or_(LDX, STX), n.or_(LDXP, STXP)))
    with n.scope('addr'):
        addr = bus_mux(n, bus_mux(n, OP13, P, selP), PC, selpc)
        inc = incrementer(n, addr)
    with n.scope('alu'):
        incdec = n.or_(INCZ, DECZ)
        sYm = n.or_(n.or_(isZp, LDA), n.or_(LDX, LDXP))
        sYa, sYff = n.or_(SHL, ROL), n.or_(DECZ, CPL)
        X = bus_mux(n, ACC, rdata, incdec)
        Yr = [ao(n, [(sYm, rdata[i]), (isImm, OPlo[i]), (sYa, ACC[i]), (sYff, ONE)]) for i in range(8)]
        fADD, fADC, fSUB, fSBC, fAND, fOR, fXOR = [gf[i] for i in range(1, 8)]
        inv = n.or_(fSUB, fSBC)
        cin = n.or_(n.or_(n.and_(n.or_(fADC, ROL), C), n.or_(fSUB, INCZ)), n.and_(fSBC, n.not_(C)))
        Y = [n.xor(b, inv) for b in Yr]
        c = cin
        res = []
        sLD, sSUM = gf[0], None
        sSUM = n.or_(n.or_(n.or_(fADD, fADC), n.or_(fSUB, fSBC)), n.or_(n.or_(SHL, ROL), n.or_(incdec, ZERO)))
        sAND, sOR, sXOR, sSHR = fAND, fOR, n.or_(fXOR, CPL), n.or_(SHR, ROR)
        lrd = n.or_(sLD, n.or_(LDA, n.or_(LDX, LDXP)))   # load-type: pass Y
        shr_in = [ACC[1], ACC[2], ACC[3], ACC[4], ACC[5], ACC[6], ACC[7], n.and_(ROR, C)]
        for i in range(8):
            x, y = X[i], Y[i]
            t1 = n.nand(x, y); u = n.nand(x, t1); v = n.nand(y, t1); xr = n.nand(u, v)
            t4 = n.nand(xr, c); s = n.nand(n.nand(xr, t4), n.nand(c, t4)); c = n.nand(t4, t1)
            andv, orv = n.not_(t1), n.nand(n.not_(xr), t1)
            res.append(ao(n, [(lrd, y), (sSUM, s), (sAND, andv), (sOR, orv), (sXOR, xr), (sSHR, shr_in[i])]))
        cout = c
        zero = n.not_(or_tree(n, res))
    with n.scope('flags'):
        aluOp = g_alu
        zen = n.or_(n.or_(aluOp, n.or_(LDA, n.or_(LDX, LDXP))), n.or_(n.or_(incdec, CPL), n.or_(n.or_(SHL, SHR), n.or_(ROL, ROR))))
        n.set_d(Z, n.mux(Z, zero, n.and_(sX, zen)))
        cpos = n.or_(n.or_(fADD, fADC), n.or_(SHL, ROL))
        cneg = n.or_(fSUB, fSBC)
        cnew = ao(n, [(cpos, cout), (cneg, n.not_(cout)), (sSHR, ACC[0]), (SEC, ONE)])
        cen = n.or_(n.or_(cpos, cneg), n.or_(n.or_(sSHR, SEC), CLC))
        n.set_d(C, n.mux(C, cnew, n.and_(sX, cen)))
    with n.scope('acc'):
        aen = n.or_(n.or_(aluOp, n.or_(LDA, n.or_(LDX, LDXP))), n.or_(n.or_(CPL, sSHR), n.or_(SHL, ROL)))
        register(n, ACC, n.and_(sX, aen), res)
    with n.scope('ir_op'):
        register(n, IR, sF0, rdata)
        incx = n.and_(sX, LPZSPZ)
        for i in range(8):
            n.set_d(OPlo[i], n.mux(n.mux(OPlo[i], inc[i], incx), rdata[i], sF1))
        for j in range(5):
            v = n.mux(OPhi[j], inc[8 + j], incx)
            v = n.mux(v, rdata[j], sF2)
            n.set_d(OPhi[j], n.and_(v, n.not_(sF1)))
    with n.scope('p'):
        ldp_inc = selP & 0 if False else n.and_(sX, n.or_(LDXP, STXP))
        ldp_op = n.and_(sX, LPA)
        ldp_lo, ldp_hi = n.and_(sX, LPZ), n.and_(sX2, LPZ)
        for i in range(13):
            v = n.mux(P[i], inc[i], ldp_inc)
            v = n.mux(v, OP13[i], ldp_op)
            if i < 8: v = n.mux(v, rdata[i], ldp_lo)
            else: v = n.mux(v, rdata[i - 8], ldp_hi)
            n.set_d(P[i], v)
    with n.scope('pc'):
        cond = n.mux(n.mux(Z, n.not_(Z), IR[0]), n.mux(C, n.not_(C), IR[0]), IR[1])
        taken = n.and_(sX, n.and_(gbr, cond))
        jmp = n.and_(sX, JMP)
        for i in range(13):
            if i < 8: v = n.mux(PC[i], OPlo[i], n.or_(taken, jmp))
            else: v = n.mux(PC[i], OPhi[i - 8], jmp)
            v = n.mux(v, inc[i], selpc)
            n.set_d(PC[i], n.mux(v, ONE if (PC_RESET >> i) & 1 else ZERO, reset))
    with n.scope('wdata'):
        wPl, wPh = n.and_(sX, SPZ), n.and_(sX2, SPZ)
        wRes = incdec
        wAcc = n.not_(n.or_(n.or_(wPl, wPh), wRes))
        wdata = [ao(n, [(wPl, P[i]), (wPh, P[i + 8] if i < 5 else ZERO), (wRes, res[i]), (wAcc, ACC[i])]) for i in range(8)]
        we = n.or_(n.and_(sX, n.or_(n.or_(n.or_(STZ, incdec), n.or_(SPZ, STA)), n.or_(STX, STXP))), n.and_(sX2, SPZ))
    return n.finalize({'addr': addr, 'wdata': wdata, 'we': [we], 'pc': PC, 'acc': ACC, 'p': P, 'z': [Z], 'c': [C],
                       'st': [sF0, sF1, sF2, sX, sX2], 'ir': IR})


if __name__ == '__main__':
    for lv in (1, 2):
        c = build_acc8(lv)
        print(lv, 'NAND', len(c.gates), 'DFF', c.n_dff, c.by_scope()[0])
