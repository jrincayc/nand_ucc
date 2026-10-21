#!/usr/bin/env python3
"""rvemu.py -- instruction-level model of the RNDP Replicator 3 CPU (RV32EC, user level).  The normative golden model for the gate-level CPU.

Architecture (decisions of 2026-10-20, see DESIGN.md):
  * RV32E base (x0..x15) + C (compressed) without the floating-point forms.  No M/A/F/D, no CSRs, no traps.  FENCE is a no-op.
    ECALL, EBREAK, reserved/illegal encodings and registers x16..x31 are not defined (the model raises Illegal).
  * Byte-serial machine: the datapath is 8 bits wide, loads/stores/arithmetic are done one byte at a time, misaligned accesses are fine.
  * The 16 registers live in the RAM part: register xN occupies the 4 bytes at address 4N (little endian).  x0 reads as 0 and is never written
    (its 4 bytes, 0..3, are ordinary RAM).  Stores to 0x04..0x3F therefore change registers, as on a memory-mapped register file.
  * Address bus is 15 bits: only address bits 14..0 are used (higher bits are ignored).  The PC is 14 bits (code runs only from ROM): the
    architectural PC value is 0x4000 | pc14, so jal/jalr/auipc see 0x4000-based addresses; every PC update wraps in 14 bits (a jalr target is
    taken modulo 0x4000 and bit 0 is cleared).  Instruction bytes are fetched from ROM address (pc + i) mod 0x4000.
  * CPU-private RAM: bytes 0x40..0x4F are used by the CPU itself (PC at 0x40, the start-of-instruction copy at 0x44) and must not be touched by
    programs (the model does not keep the PC there; tests and the builder honour this).  User data starts at 0x50.
      ROM   addr bit 14 = 1     0x4000..0x7FFF  (14-bit ROM, 16 KB), reset PC = 0x4000, read-only (stores ignored)
      ARM   0x3FF0..0x3FFF      write-only, every stored byte is one arm register write (reg = addr & 15); reads give 0
      RAM   0x0000..RAM_SIZE-1  (RAM_SIZE a power of two <= 256); beyond it, up to 0x3FEF, reads give 0 and writes are ignored
  * A word/half store to the arm window writes its bytes to consecutive arm registers, low byte first (address+0, +1, ...; register numbers
    wrap inside the 16-register window).
  * Halt convention (tests only): a jump to itself (jal x0, 0 / c.j 0) stops the model.
"""
import os, sys

ROM_BITS = int(os.environ.get('ROM_BITS', '14'))      # ROM address bits (14: 16 KB at 0x4000, 15: 32 KB at 0x8000)
ROM_BASE = 1 << ROM_BITS
ARM_BASE = ROM_BASE - 16                               # the arm window is the 16 bytes just below the ROM
AMASK = 2 * ROM_BASE - 1                               # the address bus has ROM_BITS+1 bits
PCMASK = ROM_BASE - 1


class Illegal(Exception):
    pass


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def bits(v, hi, lo):
    return (v >> lo) & ((1 << (hi - lo + 1)) - 1)


def expand(h):
    """Expand a 16-bit compressed instruction to the equivalent 32-bit instruction (RV32C, no F/D forms)."""
    op, f3 = h & 3, bits(h, 15, 13)
    rd_ = lambda lo: 8 + bits(h, lo + 2, lo)          # 3-bit register field -> x8..x15
    def I(imm, rs1, f3_, rd, opc): return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3_ << 12) | (rd << 7) | opc
    def R(f7, rs2, rs1, f3_, rd, opc): return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3_ << 12) | (rd << 7) | opc
    def S(imm, rs2, rs1, f3_, opc): return (bits(imm, 11, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3_ << 12) | (bits(imm, 4, 0) << 7) | opc
    def B(imm, rs2, rs1, f3_):
        return (bits(imm, 12, 12) << 31) | (bits(imm, 10, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3_ << 12) | (bits(imm, 4, 1) << 8) | (bits(imm, 11, 11) << 7) | 0x63
    def J(imm, rd):
        return (bits(imm, 20, 20) << 31) | (bits(imm, 10, 1) << 21) | (bits(imm, 11, 11) << 20) | (bits(imm, 19, 12) << 12) | (rd << 7) | 0x6F
    def U(imm, rd): return ((imm & 0xFFFFF) << 12) | (rd << 7) | 0x37
    if op == 0:
        if f3 == 0:       # c.addi4spn
            imm = (bits(h, 10, 7) << 6) | (bits(h, 12, 11) << 4) | (bits(h, 5, 5) << 3) | (bits(h, 6, 6) << 2)
            if imm == 0: raise Illegal('c.addi4spn imm 0 (also the all-zero halfword)')
            return I(imm, 2, 0, rd_(2), 0x13)
        imm = (bits(h, 5, 5) << 6) | (bits(h, 12, 10) << 3) | (bits(h, 6, 6) << 2)
        if f3 == 2: return I(imm, rd_(7), 2, rd_(2), 0x03)                # c.lw
        if f3 == 6: return S(imm, rd_(2), rd_(7), 2, 0x23)                # c.sw
        raise Illegal(f'quadrant 0 funct3 {f3}')
    if op == 1:
        rd = bits(h, 11, 7); imm6 = sx((bits(h, 12, 12) << 5) | bits(h, 6, 2), 6)
        if f3 == 0: return I(imm6, rd, 0, rd, 0x13)                       # c.addi / c.nop
        if f3 == 1:                                                       # c.jal
            imm = sx((bits(h, 12, 12) << 11) | (bits(h, 8, 8) << 10) | (bits(h, 10, 9) << 8) | (bits(h, 6, 6) << 7) | (bits(h, 7, 7) << 6) | (bits(h, 2, 2) << 5) | (bits(h, 11, 11) << 4) | (bits(h, 5, 3) << 1), 12)
            return J(imm, 1)
        if f3 == 2: return I(imm6, 0, 0, rd, 0x13)                        # c.li
        if f3 == 3:
            if rd == 2:                                                   # c.addi16sp
                imm = sx((bits(h, 12, 12) << 9) | (bits(h, 4, 3) << 7) | (bits(h, 5, 5) << 6) | (bits(h, 2, 2) << 5) | (bits(h, 6, 6) << 4), 10)
                if imm == 0: raise Illegal('c.addi16sp 0')
                return I(imm, 2, 0, 2, 0x13)
            if imm6 == 0: raise Illegal('c.lui 0')
            return U(imm6, rd)                                            # c.lui
        if f3 == 4:
            r = rd_(7); sh = (bits(h, 12, 12) << 5) | bits(h, 6, 2); k = bits(h, 11, 10)
            if k == 0 or k == 1:
                if sh >> 5: raise Illegal('shift amount >= 32')
                return I(sh | (0x400 if k == 1 else 0), r, 5, r, 0x13)    # c.srli / c.srai
            if k == 2: return I(imm6, r, 7, r, 0x13)                      # c.andi
            if bits(h, 12, 12): raise Illegal('c.subw/addw')
            return R(0x20 if bits(h, 6, 5) == 0 else 0, rd_(2), r, (0, 4, 6, 7)[bits(h, 6, 5)], r, 0x33)   # c.sub c.xor c.or c.and
        if f3 == 5:                                                       # c.j
            imm = sx((bits(h, 12, 12) << 11) | (bits(h, 8, 8) << 10) | (bits(h, 10, 9) << 8) | (bits(h, 6, 6) << 7) | (bits(h, 7, 7) << 6) | (bits(h, 2, 2) << 5) | (bits(h, 11, 11) << 4) | (bits(h, 5, 3) << 1), 12)
            return J(imm, 0)
        imm = sx((bits(h, 12, 12) << 8) | (bits(h, 6, 5) << 6) | (bits(h, 2, 2) << 5) | (bits(h, 11, 10) << 3) | (bits(h, 4, 3) << 1), 9)
        return B(imm, 0, rd_(7), 0 if f3 == 6 else 1)                     # c.beqz / c.bnez
    # quadrant 2
    rd = bits(h, 11, 7); rs2 = bits(h, 6, 2)
    if f3 == 0:
        if bits(h, 12, 12): raise Illegal('shift amount >= 32')
        return I(rs2, rd, 1, rd, 0x13)                                    # c.slli
    if f3 == 2:
        if rd == 0: raise Illegal('c.lwsp rd=x0')
        return I((bits(h, 3, 2) << 6) | (bits(h, 12, 12) << 5) | (bits(h, 6, 4) << 2), 2, 2, rd, 0x03)   # c.lwsp
    if f3 == 4:
        if not bits(h, 12, 12):
            if rs2 == 0:
                if rd == 0: raise Illegal('c.jr x0')
                return I(0, rd, 0, 0, 0x67)                              # c.jr
            return R(0, rs2, 0, 0, rd, 0x33)                              # c.mv
        if rs2 == 0:
            if rd == 0: raise Illegal('c.ebreak')
            return I(0, rd, 0, 1, 0x67)                                   # c.jalr
        return R(0, rs2, rd, 0, rd, 0x33)                                 # c.add
    if f3 == 6: return S((bits(h, 8, 7) << 6) | (bits(h, 12, 9) << 2), rs2, 2, 2, 0x23)   # c.swsp
    raise Illegal(f'quadrant 2 funct3 {f3}')


class Machine:
    def __init__(self, rom=b'', ram_size=256, arm_log=None):
        self.rom = bytes(rom); self.ram = bytearray(ram_size); self.ram_size = ram_size
        self.armlog = [] if arm_log is None else arm_log
        self.pc = 0; self.icount = 0; self.ccount = 0; self.halted = False

    # ---- memory
    def rb(self, a):
        a &= AMASK
        if a & ROM_BASE: o = a - ROM_BASE; return self.rom[o] if o < len(self.rom) else 0
        if a < self.ram_size: return self.ram[a]
        return 0
    def wb(self, a, v):
        a &= AMASK; v &= 255
        if a & ROM_BASE: return
        if (a >> 4) == (ARM_BASE >> 4): self.armlog.append((a & 15, v)); return
        if a < self.ram_size: self.ram[a] = v
    def rd(self, a, n): return sum(self.rb(a + i) << (8 * i) for i in range(n))
    def wr(self, a, n, v):
        for i in range(n): self.wb(a + i, v >> (8 * i))

    # ---- registers (in RAM)
    def reg(self, i):
        if i == 0: return 0
        return self.rd(4 * i, 4)
    def setreg(self, i, v):
        if i: self.wr(4 * i, 4, v & 0xFFFFFFFF)

    def fetch(self):
        f = lambda i: self.rb(ROM_BASE | ((self.pc + i) & PCMASK))
        lo = f(0) | f(1) << 8
        if lo & 3 == 3: return (lo | f(2) << 16 | f(3) << 24), 4, False
        return lo, 2, True

    def step(self):
        ins, ln, comp = self.fetch()
        if comp: ins = expand(ins)
        pc = self.pc; npc = (pc + ln) & PCMASK; pcv = ROM_BASE | pc; npcv = ROM_BASE | npc
        opc = ins & 0x7F; rd = bits(ins, 11, 7); f3 = bits(ins, 14, 12); rs1 = bits(ins, 19, 15); rs2 = bits(ins, 24, 20); f7 = bits(ins, 31, 25)
        for r in ((rd, rs1, rs2) if opc in (0x33,) else (rd, rs1) if opc in (0x13, 0x03, 0x67) else (rs1, rs2) if opc in (0x23, 0x63) else (rd,) if opc in (0x37, 0x17, 0x6F) else ()):
            if r > 15: raise Illegal(f'register x{r} at pc {pc:#x}')
        a, b = self.reg(rs1), self.reg(rs2)
        M = 0xFFFFFFFF
        if opc == 0x37: self.setreg(rd, ins & 0xFFFFF000)
        elif opc == 0x17: self.setreg(rd, pcv + (ins & 0xFFFFF000))
        elif opc == 0x6F:
            imm = sx((bits(ins, 31, 31) << 20) | (bits(ins, 19, 12) << 12) | (bits(ins, 20, 20) << 11) | (bits(ins, 30, 21) << 1), 21)
            if imm == 0 and rd == 0: self.halted = True
            self.setreg(rd, npcv); npc = (pc + imm) & PCMASK
        elif opc == 0x67:
            if f3: raise Illegal('jalr funct3')
            t = (a + sx(ins >> 20, 12)) & PCMASK & ~1; self.setreg(rd, npcv); npc = t
        elif opc == 0x63:
            imm = sx((bits(ins, 31, 31) << 12) | (bits(ins, 7, 7) << 11) | (bits(ins, 30, 25) << 5) | (bits(ins, 11, 8) << 1), 13)
            sa, sb = sx(a, 32), sx(b, 32)
            t = {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb, 6: a < b, 7: a >= b}.get(f3)
            if t is None: raise Illegal('branch funct3')
            if t: npc = (pc + imm) & PCMASK
        elif opc == 0x03:
            ad = (a + sx(ins >> 20, 12)) & M
            v = {0: lambda: sx(self.rd(ad, 1), 8), 1: lambda: sx(self.rd(ad, 2), 16), 2: lambda: self.rd(ad, 4), 4: lambda: self.rd(ad, 1), 5: lambda: self.rd(ad, 2)}.get(f3)
            if v is None: raise Illegal('load funct3')
            self.setreg(rd, v() & M)
        elif opc == 0x23:
            ad = (a + sx((bits(ins, 31, 25) << 5) | bits(ins, 11, 7), 12)) & M
            if f3 not in (0, 1, 2): raise Illegal('store funct3')
            self.wr(ad, 1 << f3, b)
        elif opc == 0x13:
            imm = sx(ins >> 20, 12)
            if f3 == 0: r = a + imm
            elif f3 == 2: r = int(sx(a, 32) < imm)
            elif f3 == 3: r = int(a < (imm & M))
            elif f3 == 4: r = a ^ (imm & M)
            elif f3 == 6: r = a | (imm & M)
            elif f3 == 7: r = a & (imm & M)
            elif f3 == 1:
                if f7 or bits(ins, 25, 25): raise Illegal('slli')
                r = a << rs2
            else:
                if f7 not in (0, 0x20) or bits(ins, 25, 25): raise Illegal('srli/srai')
                r = (sx(a, 32) >> rs2) if f7 else (a >> rs2)
            self.setreg(rd, r & M)
        elif opc == 0x33:
            if f7 not in (0, 0x20) or (f7 and f3 not in (0, 5)): raise Illegal('op funct7 (M extension not implemented)')
            sa = sx(a, 32)
            r = {0: (a - b) if f7 else (a + b), 1: a << (b & 31), 2: int(sa < sx(b, 32)), 3: int(a < b), 4: a ^ b,
                 5: (sa >> (b & 31)) if f7 else (a >> (b & 31)), 6: a | b, 7: a & b}[f3]
            self.setreg(rd, r & M)
        elif opc == 0x0F: pass
        else: raise Illegal(f'opcode {opc:#x} ({ins:#010x}) at pc {pc:#x}')
        self.pc = npc; self.icount += 1
        return ins, comp

    def run(self, maxn=10**8):
        while not self.halted and self.icount < maxn: self.step()
        return self.icount
