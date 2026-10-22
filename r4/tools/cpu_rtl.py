#!/usr/bin/env python3
"""cpu_rtl.py -- register-transfer model of the Replicator 3 CPU: executes the microprogram of ucode.py one tick at a time.
The gate-level CPU (cpu_gen.py) must match this model tick for tick (state registers) and rvemu.py at instruction boundaries.
State: uPC k IR[4 bytes] AR[15] A R C Z SA SB, RAM (256 bytes), ROM, arm writes."""
import os, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import ucode, rvemu
from rvemu import expand, Illegal, sx

import os
RB = rvemu.ROM_BITS; AB = rvemu.AB; RA = rvemu.RAM_BITS
ROM_BASE = 1 << AB; PCM = (1 << RB) - 1; NA = AB + 1; ARB = ucode.ARB
UCODE, LAB = ucode.assemble()


def immediate(v):
    opc = (v >> 2) & 31
    if opc in (0x0D, 0x05): return v & 0xFFFFF000                                                  # U
    if opc == 0x1B: return sx(((v >> 31) << 20) | (((v >> 12) & 255) << 12) | (((v >> 20) & 1) << 11) | (((v >> 21) & 0x3FF) << 1), 21) & 0xFFFFFFFF   # J
    if opc == 0x18: return sx(((v >> 31) << 12) | (((v >> 7) & 1) << 11) | (((v >> 25) & 63) << 5) | (((v >> 8) & 15) << 1), 13) & 0xFFFFFFFF          # B
    if opc == 0x08: return sx(((v >> 25) << 5) | ((v >> 7) & 31), 12) & 0xFFFFFFFF                # S
    return sx(v >> 20, 12) & 0xFFFFFFFF                                                             # I


def iclass(v):
    opc = (v >> 2) & 31; f3 = (v >> 12) & 7
    if opc == 0x0D: return 0
    if opc == 0x05: return 1
    if opc == 0x1B: return 2
    if opc == 0x19: return 3
    if opc == 0x18: return 4
    if opc == 0x00: return 5
    if opc == 0x08: return 6
    if opc == 0x04: return 8 if (f3 & 3) == 1 else 7
    if opc == 0x0C: return 10 if (f3 & 3) == 1 else 9
    if opc == 0x03: return 11
    return 15


class CPU:
    def __init__(self, rom=b''):
        self.rom = bytes(rom); self.ram = bytearray(1 << RA); self.arm = []
        self.upc = 0; self.k = 0; self.ir = [0, 0, 0, 0]; self.ar = 0; self.A = 0; self.R = 0; self.C = 0; self.Z = 0; self.SA = 0; self.SB = 0
        self.ticks = 0; self.trace = None

    def romb(self, a): o = a & PCM; return self.rom[o] if o < len(self.rom) else 0

    def V(self):
        if self.ir[0] & 3 == 3: return self.ir[0] | self.ir[1] << 8 | self.ir[2] << 16 | self.ir[3] << 24
        return expand(self.ir[0] | self.ir[1] << 8)

    def state(self): return (self.upc, self.k, tuple(self.ir), self.ar, self.A, self.R, self.C, self.Z, self.SA, self.SB)

    def tick(self):
        mi = UCODE[self.upc]; f = mi.f
        try: v = self.V()
        except Illegal: v = 0xFFFFFFFF           # illegal compressed word: class 15 (halt)
        k, ar = self.k, self.ar
        opc5 = (v >> 2) & 31; f3 = (v >> 12) & 7; rd = (v >> 7) & 15; rs1 = (v >> 15) & 15; rs2 = (v >> 20) & 15
        right = f3 >> 2 & 1
        kk = (k ^ 3) if (f['rev'] and right) else k
        ra = f['ra']; reg = ra in ('RS1', 'RS2', 'RD')
        idx = {'RS1': rs1, 'RS2': rs2, 'RD': rd}.get(ra, 0)
        if reg: addr = idx * 4 + kk
        elif ra == 'PC': addr = 0x40 + kk
        elif ra == 'PS': addr = 0x44 + kk
        elif ra == 'AR': addr = ar & ((1 << RA) - 1)
        else: addr = 0
        dout = self.ram[addr]
        sel_rom = (ar >> AB) & 1; sel_arm = (ar >> AB) == 0 and (ar >> 4) == (ROM_BASE - 16) >> 4; sel_ram = (ar >> RA) == 0 and not sel_arm
        if ra == 'AR': mem = self.romb(ar) if sel_rom else (dout if sel_ram else 0)
        else: mem = 0 if (reg and idx == 0) else dout
        if ARB == 3 and ra in ('PC', 'PS') and kk == 2: mem = 1 << (AB - 16)         # the ROM-select bit of the architectural PC
        imm = (immediate(v) >> (8 * k)) & 255
        dsel = f['dsel']
        if dsel == 'BX': dsel = 'IMM' if not (opc5 >> 3 & 1) else 'MEM'      # opcode bit 5 = opc5 bit 3
        d = {'MEM': mem, 'IMM': imm, 'ARLO': ar & 0xFE, 'ARHI': ((ar >> 8) & 255) if ARB == 3 else (1 << (RB - 8)) | ((ar >> 8) & ((1 << (RB - 8)) - 1))}[dsel]
        Ae = 0 if f['az'] else self.A
        op = f['op']
        if op == 'ARITH':
            if f3 == 0: op = 'SUB' if ((opc5 >> 3) & 1 and (v >> 30) & 1) else 'ADD'
            elif f3 in (2, 3): op = 'SUB'
            else: op = {4: 'XOR', 6: 'OR', 7: 'AND'}.get(f3, 'ADD')
        elif op == 'SHIFT':
            if not right: op = 'SHL1'
            else: op = 'SAR1' if ((v >> 30) & 1 and k == 0) else 'SHR1'
        init = 1 if op == 'SUB' else 0
        cin = (init if k == 0 else self.C) if f['cinm'] else 0
        cout = 0
        if op == 'ADD': t = Ae + d + cin; res, cout = t & 255, t >> 8
        elif op == 'SUB': t = Ae + (d ^ 255) + cin; res, cout = t & 255, t >> 8
        elif op == 'XOR': res = Ae ^ d
        elif op == 'OR': res = Ae | d
        elif op == 'AND': res = Ae & d
        elif op == 'SHL1': res, cout = ((Ae << 1) | cin) & 255, Ae >> 7
        elif op == 'SHR1': res, cout = (cin << 7) | (Ae >> 1), Ae & 1
        elif op == 'SAR1': res, cout = (Ae & 128) | (Ae >> 1), Ae & 1
        elif op == 'FILL': res = 255 if (self.SA and not (f3 >> 2 & 1)) else 0
        elif op == 'LT':
            ltu = 1 - self.C; lts = self.SA if (self.SA ^ self.SB) else ltu
            res = (ltu if f3 & 1 else lts) if k == 0 else 0
        else: raise ValueError(op)
        # conditions
        z = self.Z
        base = z if not (f3 >> 2 & 1) else ((1 - self.C) if (f3 >> 1 & 1) else (self.SA if (self.SA ^ self.SB) else 1 - self.C))
        stop_k = 3 if f3 & 2 else (1 if f3 & 1 else 0)
        conds = dict(ISC=int(self.ir[0] & 3 != 3), NK3=int(k != 3), NK1=int(k != 1), NK2=int(k != 2), TAKEN=base ^ (f3 & 1),
                     LDFILL=int((k != 0) if (f3 & 3) == 0 else (k >> 1 & 1) if (f3 & 3) == 1 else 0), MORE=int(k != stop_k),
                     SHDONE=int((ar & 31) == 31), ISSLT=int((f3 >> 1) == 1), ISSTORE=(opc5 >> 3) & 1)
        # next micro address
        nx = f['nx']
        if nx == 'SEQ': nu = self.upc + 1
        elif nx == 'JMP': nu = f['tgt']
        elif nx == 'BR': nu = f['tgt'] if conds[f['cond']] else self.upc + 1
        else: nu = ucode.DISPATCH_BASE + iclass(v)
        # writes (use pre-tick state)
        if f['we']:
            if ra == 'AR':
                if sel_ram: self.ram[addr] = self.R
                elif sel_arm: self.arm.append((ar & 15, self.R))
            elif not (ra == 'RD' and idx == 0): self.ram[addr] = self.R
        # state update
        ir = list(self.ir)
        if f['ldIR']: ir[k] = self.romb(ar)
        new_ar = ar
        if f['ldAR']:
            if k == 0: new_ar = (ar & ~0xFF) | res
            elif k == 1: new_ar = (ar & ~(((1 << (min(AB, 15) - 7)) - 1) << 8)) | ((res & ((1 << (min(AB, 15) - 7)) - 1)) << 8)
        elif f['arinc']: new_ar = (ar + 1) & ((2 << AB) - 1)
        if f['ldARX'] and k == 2: new_ar = (new_ar & 0xFFFF) | ((res & ((1 << (AB - 15)) - 1)) << 16)
        if f['arrom']: new_ar = (new_ar & 0xFFFF) | (1 << AB)
        if f['ldA']: self.A = d
        if f['ldR']: self.R_new = res
        newR = res if f['ldR'] else self.R
        if f['ldC']: self.C = cout
        if f['ldZ']: self.Z = int((1 if k == 0 else z) and res == 0)
        sa, sb = self.SA, self.SB
        if f['ldS']: sa, sb = Ae >> 7, d >> 7
        if f['ldSR']: sa = self.R >> 7
        self.SA, self.SB = sa, sb
        self.R = newR; self.ir = ir; self.ar = new_ar
        self.k = {'HOLD': k, 'INC': (k + 1) & 3, 'CLR': 0}[f['kop']]
        self.upc = nu; self.ticks += 1
        return mi


def run_until_fetch(cpu, maxticks=100000):
    """tick until the micro-PC is at L0 again after executing at least one instruction (returns ticks used)"""
    n = 0
    while True:
        cpu.tick(); n += 1
        if cpu.upc == LAB['L0']: return n
        if n > maxticks: raise RuntimeError('no instruction boundary')
