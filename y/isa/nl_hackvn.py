"""Gate-level Hack-vN CPU (see isa/HACK_VN.md).  Interface: in rdata[8], reset; out addr[AB], wdata[8], we.
One memory address per tick; read data is combinational from addr, writes are clocked at the same tick.
States (one-hot DFFs): F0 fetch low byte, F1 fetch high byte (+A-instruction), X execute C-instruction,
AP0 / AP1 the two reads of the indirect pointer load.  A-instr = 2 ticks, C = 3, AP = 4."""
from nandgen import *
import common

AB = common.AB
PC_RESET = common.ROM_BASE


def hackvn_core(n, reset, get_rdata):
    """Adds the CPU to Net n.  `get_rdata(addr)` must return the 8 read-data wires for the address bus
    (the address is a function of registers only, so this is not a combinational loop).
    Returns a dict of signals."""
    PC, A, D = n.dff_bus(AB), n.dff_bus(AB), n.dff_bus(8)
    IRlo, IRhi = n.dff_bus(8), n.dff_bus(5)          # IRhi = instruction bits 12..8
    sF0, sF1, sX, sAP0, sAP1 = n.dff_bus(5)
    selpc = n.or_(sF0, sF1)
    with n.scope('addr'):
        addr = bus_mux(n, A, PC, selpc)
        inc = incrementer(n, addr)
    rdata = get_rdata(addr)
    hi7, hi6, hi5 = rdata[7], rdata[6], rdata[5]
    with n.scope('control'):
        isC = n.and_(hi7, n.and_(hi6, hi5))
        isAP = n.and_(hi7, n.and_(hi6, n.not_(hi5)))
        isA = n.not_(hi7)
        nr = n.not_(reset)
        n.set_d(sF0, n.or_(reset, n.or_(sX, n.or_(sAP1, n.and_(sF1, n.not_(n.or_(isC, isAP)))))))
        n.set_d(sF1, n.and_(nr, sF0))
        n.set_d(sX, n.and_(nr, n.and_(sF1, isC)))
        n.set_d(sAP0, n.and_(nr, n.and_(sF1, isAP)))
        n.set_d(sAP1, n.and_(nr, sAP0))
        d1, d2, d3 = IRlo[5], IRlo[4], IRlo[3]
    with n.scope('alu'):
        y = bus_mux(n, A[:8], rdata, IRhi[4])
        out, zr, ng = alu(n, D, y, IRhi[3], IRhi[2], IRhi[1], IRhi[0], IRlo[7], IRlo[6])
    with n.scope('pc'):
        pos = n.and_(n.not_(ng), n.not_(zr))
        jump = n.and_(sX, n.or_(n.or_(n.and_(IRlo[2], ng), n.and_(IRlo[1], zr)), n.and_(IRlo[0], pos)))
        nxt = bus_mux(n, bus_mux(n, PC, A, jump), inc, selpc)
        for i, (q, d) in enumerate(zip(PC, nxt)):
            n.set_d(q, n.mux(d, ONE if (PC_RESET >> i) & 1 else ZERO, reset))
    with n.scope('areg'):
        ldImm = n.or_(n.and_(sF1, isA), sAP1)
        ldInc, ldAlu = sAP0, n.and_(sX, d1)
        imm = IRlo + rdata[:AB - 8]
        for i, q in enumerate(A):
            v = n.mux(A[i], out[i] if i < 8 else A[i], ldAlu)
            v = n.mux(v, inc[i], ldInc)
            n.set_d(q, n.mux(v, imm[i], ldImm))
    with n.scope('dreg'):
        register(n, D, n.and_(sX, d2), out)
    with n.scope('ir'):
        register(n, IRlo, n.or_(sF0, sAP0), rdata)
        register(n, IRhi, sF1, rdata[:5])
    we = n.and_(sX, d3)
    return dict(addr=addr, wdata=out, we=we, pc=PC, a=A, d=D, st=[sF0, sF1, sX, sAP0, sAP1], ir=IRlo + IRhi)


def build_hackvn(level=2):
    n = Net(level)
    rdata = n.bus_in('rdata', 8)
    reset = n.input('reset')
    s = hackvn_core(n, reset, lambda addr: rdata)
    return n.finalize({'addr': s['addr'], 'wdata': s['wdata'], 'we': [s['we']], 'pc': s['pc'], 'a': s['a'],
                       'd': s['d'], 'st': s['st'], 'ir': s['ir']})


if __name__ == '__main__':
    for lv in (0, 1, 2):
        c = build_hackvn(lv)
        print(lv, 'NAND', len(c.gates), 'DFF', c.n_dff, c.by_scope()[0])
