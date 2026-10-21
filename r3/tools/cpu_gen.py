#!/usr/bin/env python3
"""cpu_gen.py -- builds the gate-level (NAND + DFF) Replicator 3 CPU from the microprogram of ucode.py.
build() -> (net, ports) ; ports: dict name -> signal for the outputs, inputs are net.inputs (romK, ramrdK, run).
Run as a script to print statistics."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import ucode, pla, expander
from netlist import Net

UC, LAB = ucode.assemble()
COND_LINES = ['br_' + c.lower() for c in ucode.CONDS]


def micro_lines(mi):
    """-> dict line -> (value, care) for one micro-instruction"""
    f = mi.f
    alu_res = any(f[x] for x in ('ldR', 'ldAR', 'ldC', 'ldZ', 'ldS'))
    d_ops = ('ADD', 'SUB', 'XOR', 'OR', 'AND', 'ARITH')
    a_ops = d_ops + ('SHL1', 'SHR1', 'SAR1', 'SHIFT')
    d_used = bool(f['ldA'] or f['ldS'] or (alu_res and f['op'] in d_ops))
    a_used = bool(f['ldS'] or (alu_res and f['op'] in a_ops))
    mem_read = d_used and f['dsel'] in ('MEM', 'BX')
    ra_care = bool(f['we'] or mem_read)
    L = {}
    for r in ('RS1', 'RS2', 'RD', 'PC', 'PS', 'AR'): L['ra_' + r.lower()] = (int(f['ra'] == r), ra_care)
    L['we'] = (f['we'], True)
    for d in ('MEM', 'IMM', 'ARLO', 'ARHI', 'BX'): L['d_' + d.lower()] = (int(f['dsel'] == d), d_used)
    L['az'] = (f['az'], a_used); L['cinm'] = (f['cinm'], alu_res)
    for n in ('ldA', 'ldR', 'ldC', 'ldZ', 'ldS', 'ldSR', 'ldAR', 'arinc', 'ldIR'): L[n] = (f[n], True)
    L['rev'] = (f['rev'], f['ra'] in ('RS1', 'RS2', 'RD'))
    for o in ucode.OPS: L['o_' + o.lower()] = (int(f['op'] == o), alu_res)
    L['kop_inc'] = (int(f['kop'] == 'INC'), True); L['kop_clr'] = (int(f['kop'] == 'CLR'), True)
    L['nx_jmp'] = (int(f['nx'] == 'JMP'), True); L['nx_disp'] = (int(f['nx'] == 'DISP'), True)
    for c in ucode.CONDS: L['br_' + c.lower()] = (int(f['nx'] == 'BR' and f['cond'] == c), True)
    for i in range(7): L[f'tgt{i}'] = ((f['tgt'] >> i & 1) if f['tgt'] is not None else 0, f['nx'] in ('JMP', 'BR'))
    return L


def control(net, upc):
    """PLA over the micro-PC -> dict of control line signals"""
    names = None; on = {}; dc = {}
    tables = {}
    for addr in range(128):
        mi = UC[addr] if addr < len(UC) else None
        if mi is None:
            for n in (names or []): dc[n].add(addr)
            if names is None: tables[addr] = None
            continue
        L = micro_lines(mi)
        if names is None:
            names = list(L); on = {n: set() for n in names}; dc = {n: set() for n in names}
            for a in tables:      # earlier dont-care addresses
                for n in names: dc[n].add(a)
        for n, (v, care) in L.items():
            if not care: dc[n].add(addr)
            elif v: on[n].add(addr)
    ctl = {}
    stats = {}
    for n in names:
        cubes = pla.cover(7, on[n], dc[n])
        stats[n] = len(cubes)
        ctl[n] = pla.synth(net, upc, cubes) if cubes else 0
    ctl['_stats'] = stats
    return ctl


def build(opt=None):
    net = Net()
    romd = [net.inp(f'rom{i}') for i in range(8)]
    ramd = [net.inp(f'ramrd{i}') for i in range(8)]
    run = net.inp('run')
    live = net.dff('live'); net.set_d(live, run)
    upc = [net.dff(f'upc{i}') for i in range(7)]
    k = [net.dff(f'k{i}') for i in range(2)]
    ir = [[net.dff(f'ir{j}_{i}') for i in range(8)] for j in range(4)]
    ar = [net.dff(f'ar{i}') for i in range(15)]
    A = [net.dff(f'a{i}') for i in range(8)]
    R = [net.dff(f'r{i}') for i in range(8)]
    C = net.dff('c'); Z = net.dff('z'); SA = net.dff('sa'); SB = net.dff('sb')
    nt = net.not_
    # ------------------------------------------------------------------ instruction view V
    isC = net.nand(ir[0][0], ir[0][1])
    E = expander.build(net, ir[0] + ir[1])
    irf = [ir[i // 8][i % 8] for i in range(32)]
    V = [0, 0] + [net.mux(isC, irf[i], E[i]) for i in range(2, 32)]
    opc5 = V[2:7]; f3 = V[12:15]; rdf = V[7:11]; rs1f = V[15:19]; rs2f = V[20:24]; v30 = V[30]; opbit5 = V[5]
    def match(bits5):    # opc5 == value (LSB-first list of 5 bits)
        return net.and_n([opc5[i] if bits5 >> i & 1 else nt(opc5[i]) for i in range(5)])
    M = dict(LUI=match(0b01101), AUIPC=match(0b00101), JAL=match(0b11011), JALR=match(0b11001), BRANCH=match(0b11000), LOAD=match(0), STORE=match(0b01000),
             OPIMM=match(0b00100), OP=match(0b01100), FENCE=match(0b00011))
    shflag = net.and_(f3[0], nt(f3[1]))
    clsone = [M['LUI'], M['AUIPC'], M['JAL'], M['JALR'], M['BRANCH'], M['LOAD'], M['STORE'], net.and_(M['OPIMM'], nt(shflag)), net.and_(M['OPIMM'], shflag),
              net.and_(M['OP'], nt(shflag)), net.and_(M['OP'], shflag), M['FENCE']]
    none = nt(net.or_n(clsone))
    cls = [net.or_n([clsone[j] for j in range(12) if j >> i & 1] + [none]) for i in range(4)]
    # ------------------------------------------------------------------ control word
    ctl = control(net, upc)
    c = lambda n: ctl[n]
    # ------------------------------------------------------------------ immediate (byte k)
    tU = net.or_(M['LUI'], M['AUIPC']); tJ = M['JAL']; tB = M['BRANCH']; tS = M['STORE']
    tI = nt(net.or_n([tU, tJ, tB, tS]))
    tIJ = net.or_(tI, tJ); tSB = net.or_(tS, tB); tIS = net.or_(tI, tS); tUJ = net.or_(tU, tJ)
    V31 = V[31]; nU = nt(tU)
    ib = [0] * 32
    ib[0] = net.and_or([(tI, V[20]), (tS, V[7])])
    for n in range(1, 5): ib[n] = net.and_or([(tIJ, V[20 + n]), (tSB, V[7 + n])])
    for n in range(5, 11): ib[n] = net.and_(nU, V[20 + n])
    ib[11] = net.and_or([(tB, V[7]), (tJ, V[20]), (tIS, V31)])
    for n in range(12, 20): ib[n] = net.mux(tUJ, V31, V[n])
    for n in range(20, 32): ib[n] = net.mux(tU, V31, V[n])
    kz = nt(net.or_(k[0], k[1])); k0s = net.and_(k[0], nt(k[1])); k1s = net.and_(k[1], nt(k[0])); k3s = net.and_(k[0], k[1])
    kdec = [kz, k0s, k1s, k3s]
    imm = [net.and_or([(kdec[kb], ib[8 * kb + j]) for kb in range(4)]) for j in range(8)]
    # ------------------------------------------------------------------ memory addressing
    rev_eff = net.and_(c('rev'), f3[2])
    kk = [net.xor(k[0], rev_eff), net.xor(k[1], rev_eff)]
    sreg = net.or_n([c('ra_rs1'), c('ra_rs2'), c('ra_rd')])
    idx = [net.and_or([(c('ra_rs1'), rs1f[i]), (c('ra_rs2'), rs2f[i]), (c('ra_rd'), rdf[i])]) for i in range(4)]
    s_ar = c('ra_ar')
    ram_addr = [net.mux(s_ar, kk[0], ar[0]), net.mux(s_ar, kk[1], ar[1]),
                net.or_n([idx[0], c('ra_ps'), net.and_(s_ar, ar[2])]), net.or_(idx[1], net.and_(s_ar, ar[3])),
                net.or_(idx[2], net.and_(s_ar, ar[4])), net.or_(idx[3], net.and_(s_ar, ar[5])),
                net.or_n([c('ra_pc'), c('ra_ps'), net.and_(s_ar, ar[6])]), net.and_(s_ar, ar[7])]
    idxzero = nt(net.or_n(idx))
    regzero = net.and_(sreg, idxzero)
    sel_rom = ar[14]
    sel_ram = nt(net.or_n(ar[8:15]))
    sel_arm = net.and_n([nt(ar[14])] + ar[4:14])
    g_ram = net.or_(net.and_(s_ar, sel_ram), net.and_(nt(s_ar), nt(regzero)))
    g_rom = net.and_(s_ar, sel_rom)
    mem = [net.and_or([(g_ram, ramd[i]), (g_rom, romd[i])]) for i in range(8)]
    we = c('we')
    ram_we = net.and_(we, net.mux(s_ar, nt(net.and_(c('ra_rd'), idxzero)), sel_ram))
    arm_en = net.and_n([we, s_ar, sel_arm])
    # ------------------------------------------------------------------ B-side data bus d, A operand
    use_mem = net.or_(c('d_mem'), net.and_(c('d_bx'), opbit5)); use_imm = net.or_(c('d_imm'), net.and_(c('d_bx'), nt(opbit5)))
    d = []
    for i in range(8):
        terms = [(use_mem, mem[i]), (use_imm, imm[i])]
        if i >= 1: terms.append((c('d_arlo'), ar[i]))
        if i <= 5: terms.append((c('d_arhi'), ar[8 + i]))
        elif i == 6: terms.append((c('d_arhi'), 1))
        d.append(net.and_or(terms))
    naz = nt(c('az'))
    Ae = [net.and_(A[i], naz) for i in range(8)]
    # ------------------------------------------------------------------ ALU
    f3z = net.and_n([nt(f3[0]), nt(f3[1]), nt(f3[2])])
    ar_sub = net.and_(c('o_arith'), net.or_(net.and_n([f3z, opbit5, v30]), net.and_(nt(f3[2]), f3[1])))
    ar_xor = net.and_(c('o_arith'), net.and_n([f3[2], nt(f3[1]), nt(f3[0])]))
    ar_or = net.and_(c('o_arith'), net.and_n([f3[2], f3[1], nt(f3[0])]))
    ar_and = net.and_(c('o_arith'), net.and_n([f3[2], f3[1], f3[0]]))
    ar_add = net.and_(c('o_arith'), nt(net.or_n([ar_sub, ar_xor, ar_or, ar_and])))
    sh_l = net.and_(c('o_shift'), nt(f3[2])); sh_r = net.and_(c('o_shift'), f3[2])
    sh_sar = net.and_n([sh_r, v30, kz]); sh_shr = net.and_(sh_r, nt(sh_sar))
    is_sub = net.or_(c('o_sub'), ar_sub); is_add = net.or_n([c('o_add'), ar_add])
    is_xor = net.or_(c('o_xor'), ar_xor); is_or = net.or_(c('o_or'), ar_or); is_and = net.or_(c('o_and'), ar_and)
    is_shl = net.or_(c('o_shl1'), sh_l); is_shr = net.or_(c('o_shr1'), sh_shr); is_sar = net.or_(c('o_sar1'), sh_sar)
    addsub = net.or_(is_add, is_sub)
    knz = net.or_(k[0], k[1])
    cin = net.and_(c('cinm'), net.mux(knz, is_sub, C))
    bp = [net.xor(d[i], is_sub) for i in range(8)]
    sm = []; cy = cin
    for i in range(8):
        s_, cy = net.full_adder(Ae[i], bp[i], cy); sm.append(s_)
    cout_add = cy
    xr = [net.xor(Ae[i], d[i]) for i in range(8)]
    orr = [net.or_(Ae[i], d[i]) for i in range(8)]
    andd = [net.and_(Ae[i], d[i]) for i in range(8)]
    shl = [cin] + Ae[:7]
    shr = Ae[1:] + [cin]
    sar = Ae[1:] + [Ae[7]]
    fillb = net.and_(SA, nt(f3[2]))
    ltu = nt(C); lts = net.mux(net.xor(SA, SB), ltu, SA)
    ltb = net.and_(nt(knz), net.mux(f3[0], lts, ltu))
    res = []
    for i in range(8):
        terms = [(addsub, sm[i]), (is_xor, xr[i]), (is_or, orr[i]), (is_and, andd[i]), (is_shl, shl[i]), (is_shr, shr[i]), (is_sar, sar[i]), (c('o_fill'), fillb)]
        if i == 0: terms.append((c('o_lt'), ltb))
        res.append(net.and_or(terms))
    cout = net.and_or([(addsub, cout_add), (is_shl, Ae[7]), (net.or_(is_shr, is_sar), Ae[0])])
    reszero = nt(net.or_n(res))
    # ------------------------------------------------------------------ state updates
    for i in range(8):
        net.set_d(A[i], net.mux(c('ldA'), A[i], d[i]))
        net.set_d(R[i], net.mux(c('ldR'), R[i], res[i]))
    net.set_d(C, net.mux(c('ldC'), C, cout))
    net.set_d(Z, net.mux(c('ldZ'), Z, net.and_(net.or_(kz, Z), reszero)))
    net.set_d(SA, net.mux(c('ldS'), net.mux(c('ldSR'), SA, R[7]), Ae[7]))
    net.set_d(SB, net.mux(c('ldS'), SB, d[7]))
    carry = c('arinc')
    ld_lo = net.and_(c('ldAR'), kz); ld_hi = net.and_(c('ldAR'), knz)
    for i in range(15):
        inc = net.xor(ar[i], carry); carry = net.and_(carry, ar[i])
        if i < 8: net.set_d(ar[i], net.mux(ld_lo, inc, res[i]))
        else: net.set_d(ar[i], net.mux(ld_hi, inc, res[i - 8]) if i - 8 < 7 else inc)
    for j in range(4):
        ld = net.and_(c('ldIR'), kdec[j])
        for i in range(8): net.set_d(ir[j][i], net.mux(ld, ir[j][i], romd[i]))
    kclr = nt(c('kop_clr'))
    net.set_d(k[0], net.and_(kclr, net.xor(k[0], c('kop_inc'))))
    net.set_d(k[1], net.and_(kclr, net.xor(k[1], net.and_(c('kop_inc'), k[0]))))
    # ------------------------------------------------------------------ sequencing
    ltu_ = ltu
    base = net.mux(f3[2], Z, net.mux(f3[1], lts, ltu_))
    taken = net.xor(base, f3[0])
    ldfill = net.and_(nt(f3[1]), net.mux(f3[0], knz, k[1]))
    stop0 = net.or_(f3[1], f3[0]); stop1 = f3[1]
    more = nt(net.and_(net.xnor(k[0], stop0), net.xnor(k[1], stop1)))
    conds = dict(isc=isC, nk3=nt(k3s), nk1=nt(k0s), taken=taken, ldfill=ldfill, more=more, shdone=net.and_n(ar[0:5]), isslt=net.and_(nt(f3[2]), f3[1]), isstore=opbit5)
    condval = net.and_or([(c('br_' + n), conds[n]) for n in conds])
    take = net.or_(c('nx_jmp'), condval)
    cy = 1; inc7 = []
    for i in range(7):
        inc7.append(net.xor(upc[i], cy)); cy = net.and_(cy, upc[i])
    disp = cls + [1, 0, 0]
    for i in range(7):
        nxt = net.mux(take, net.mux(c('nx_disp'), inc7[i], disp[i]), c(f'tgt{i}'))
        net.set_d(upc[i], net.and_(live, nxt))
    ports = {}
    for i in range(14): ports[f'rom_addr{i}'] = ar[i]
    for i in range(8): ports[f'ram_addr{i}'] = ram_addr[i]
    ports['ram_we'] = ram_we
    for i in range(8): ports[f'ram_din{i}'] = R[i]
    for i in range(4): ports[f'arm_addr{i}'] = ar[i]
    for i in range(8): ports[f'wdata{i}'] = R[i]
    ports['arm_en'] = arm_en
    state = dict(upc=upc, k=k, ir=ir, ar=ar, A=A, R=R, C=C, Z=Z, SA=SA, SB=SB, live=live)
    net.ctl_stats = ctl['_stats']
    return net, ports, state


if __name__ == '__main__':
    net, ports, state = build()
    g, f = net.n_gates()
    def flat(x):
        for y in x:
            if isinstance(y, list): yield from flat(y)
            else: yield y
    roots = list(ports.values()) + list(flat(v if isinstance(v, list) else [v] for v in state.values()))
    used = net.used_nodes(roots)
    ng = sum(1 for n in used if net.kind[n][0] == 'nand'); nf = sum(1 for n in used if net.kind[n][0] == 'dff')
    print(f'built {g} NAND, {f} DFF;  reachable from outputs: {ng} NAND, {nf} DFF')
    ps = net.ctl_stats; print('PLA product terms:', sum(ps.values()), 'for', len(ps), 'lines')
