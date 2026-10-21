#!/usr/bin/env python3
"""ucode.py -- the microprogram of the Replicator 3 CPU (RV32EC, byte-serial) and its micro-assembler.

One micro-instruction = one clock tick.  Fields (all default 0 / none):
  ra    RAM address source: RS1 RS2 RD (register file: 4*idx + kk), PC (0x40 + kk), PS (0x44 + kk), AR (AR[7:0]).  kk = k, or 3-k when rev.
  we    write R into the addressed memory byte (RAM, or the ARM window when ra=AR and AR is in 0x3FF0..0x3FFF; ROM and gaps ignore it)
  dsel  B-side data source: MEM (addressed byte; x0 reads 0), IMM (byte k of the immediate), ARLO ({AR[7:1],0}), ARHI ({0,1,AR[13:8]}),
        BX (IMM when the instruction is OP-IMM/LOAD/JALR-like i.e. opcode bit 5 = 0, else MEM)
  az    force the A operand to 0
  op    ADD SUB XOR OR AND SHL1 SHR1 SAR1 FILL LT, or ARITH / SHIFT (decoded from the instruction)
  cinm  0: carry-in 0;  1: chain (k == 0 ? (op is SUB) : C)
  ldA ldR ldC ldZ ldS ldSR   load A <- d, R <- res, C <- carry, Z <- (k==0 ? 1 : Z) & res==0, (SA,SB) <- (A[7], d[7]), SA <- R[7]
  ldAR  AR[7:0] <- res when k == 0, AR[14:8] <- res[6:0] when k != 0   (arinc: AR <- AR + 1, never together with ldAR)
  ldIR  IR byte k <- ROM[AR[13:0]]
  kop   k: HOLD INC CLR       rev: 1 -> kk = 3 - k when the instruction is a right shift (SHIFT dir)
  nx    SEQ (default), JMP label, BR cond label (taken if cond), DISP (uPC <- 16 + class)
"""
import sys

RA = ['NONE', 'RS1', 'RS2', 'RD', 'PC', 'PS', 'AR']
DSEL = ['MEM', 'IMM', 'ARLO', 'ARHI', 'BX']
OPS = ['ADD', 'SUB', 'XOR', 'OR', 'AND', 'SHL1', 'SHR1', 'SAR1', 'FILL', 'LT', 'ARITH', 'SHIFT']
KOP = ['HOLD', 'INC', 'CLR']
CONDS = ['ISC', 'NK3', 'NK1', 'TAKEN', 'LDFILL', 'MORE', 'SHDONE', 'ISSLT', 'ISSTORE']
FLAGS = ['we', 'az', 'cinm', 'ldA', 'ldR', 'ldC', 'ldZ', 'ldS', 'ldSR', 'ldAR', 'arinc', 'ldIR', 'rev']
DISPATCH_BASE = 16          # DISP: next = 16 + class
CLASSES = ['LUI', 'AUIPC', 'JAL', 'JALR', 'BRANCH', 'LOAD', 'STORE', 'OPIMM', 'SHIMM', 'OP', 'SHREG', 'FENCE']   # 12 = ... 15 = HALT


class MI:
    def __init__(self, label, src, **kw):
        self.label, self.src = label, src
        self.f = dict(ra='NONE', dsel='MEM', op='ADD', kop='HOLD', nx='SEQ', cond=None, tgt=None, **{n: 0 for n in FLAGS})
        for k, v in kw.items():
            if k not in self.f: raise KeyError(k)
            self.f[k] = v
        self.addr = None


def build():
    P = []
    def m(label=None, **kw):
        import inspect
        fr = inspect.stack()[1]
        P.append(MI(label, f'{fr.lineno}', **kw))
    # ------------------------------------------------------------------ instruction start: load PC into AR, copy it to PS
    m('L0', ra='PC', dsel='MEM', az=1, op='ADD', ldR=1, ldAR=1)
    m('L1', ra='PS', we=1, kop='INC')
    m('L2', ra='PC', dsel='MEM', az=1, op='ADD', ldR=1, ldAR=1)
    m('L3', ra='PS', we=1, kop='CLR')
    # ------------------------------------------------------------------ fetch 2 or 4 bytes from ROM[AR], AR counts up
    m('F0', ldIR=1, arinc=1, kop='INC')
    m('F1', ldIR=1, arinc=1, kop='INC', nx='BR', cond='ISC', tgt='SP0')
    m('F2', ldIR=1, arinc=1, kop='INC')
    m('F3', ldIR=1, arinc=1, kop='INC')
    # ------------------------------------------------------------------ PC <- AR (next sequential pc), then dispatch
    m('SP0', dsel='ARLO', az=1, op='ADD', ldR=1, kop='CLR')
    m('SP1', ra='PC', we=1, kop='INC')
    m('SP2', dsel='ARHI', az=1, op='ADD', ldR=1)
    m('SP3', ra='PC', we=1, kop='CLR', nx='DISP')
    # ------------------------------------------------------------------ dispatch table (16 entries at DISPATCH_BASE)
    DT = {'LUI': 'LU0', 'AUIPC': 'AU0', 'JAL': 'JL0', 'JALR': 'JR0', 'BRANCH': 'BR0', 'LOAD': 'EA0', 'STORE': 'EA0', 'OPIMM': 'AL0',
          'SHIMM': 'SH0', 'OP': 'AL0', 'SHREG': 'SH0', 'FENCE': 'L0'}
    P.append(None)                      # marker: pad to DISPATCH_BASE (done in assemble)
    for i in range(16):
        cl = CLASSES[i] if i < len(CLASSES) else None
        m(f'D{i}', nx='JMP', tgt=DT.get(cl, 'HALT'))
    # ------------------------------------------------------------------ OP / OP-IMM arithmetic and logic (also slt, sltu)
    m('AL0', ra='RS1', dsel='MEM', ldA=1)
    m('AL1', ra='RS2', dsel='BX', op='ARITH', cinm=1, ldR=1, ldC=1, ldS=1, nx='BR', cond='ISSLT', tgt='SL1')
    m('AL2', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='AL0')
    m('AL3', nx='JMP', tgt='L0')
    m('SL1', kop='INC', nx='BR', cond='NK3', tgt='AL0')
    m('SW0', op='LT', ldR=1)
    m('SW1', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='SW0')
    m('SW2', nx='JMP', tgt='L0')
    # ------------------------------------------------------------------ LUI, AUIPC
    m('LU0', dsel='IMM', az=1, op='ADD', ldR=1)
    m('LU1', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='LU0')
    m('LU2', nx='JMP', tgt='L0')
    m('AU0', ra='PS', dsel='MEM', ldA=1)
    m('AU1', dsel='IMM', op='ADD', cinm=1, ldR=1, ldC=1)
    m('AU2', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='AU0')
    m('AU3', nx='JMP', tgt='L0')
    # ------------------------------------------------------------------ branches: compare rs1 - rs2 over 4 bytes, then maybe AR <- PS + imm
    m('BR0', ra='RS1', dsel='MEM', ldA=1)
    m('BR1', ra='RS2', dsel='MEM', op='SUB', cinm=1, ldC=1, ldS=1, ldZ=1, kop='INC', nx='BR', cond='NK3', tgt='BR0')
    m('BR2', nx='BR', cond='TAKEN', tgt='TG0')
    m('BR3', nx='JMP', tgt='L0')
    # target: AR <- PS + imm (bytes 0 and 1), then PC <- AR again, then next instruction
    m('TG0', ra='PS', dsel='MEM', ldA=1)
    m('TG1', dsel='IMM', op='ADD', cinm=1, ldC=1, ldAR=1, kop='INC', nx='BR', cond='NK1', tgt='TG0')
    m('TG2', kop='CLR')
    m('TP0', dsel='ARLO', az=1, op='ADD', ldR=1, kop='CLR')
    m('TP1', ra='PC', we=1, kop='INC')
    m('TP2', dsel='ARHI', az=1, op='ADD', ldR=1)
    m('TP3', ra='PC', we=1, kop='CLR', nx='JMP', tgt='L0')
    # ------------------------------------------------------------------ JAL: rd <- PC (already the next pc), then branch to PS + imm
    m('JL0', ra='PC', dsel='MEM', az=1, op='ADD', ldR=1)
    m('JL1', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='JL0')
    m('JL2', nx='JMP', tgt='TG0')
    # ------------------------------------------------------------------ JALR: AR <- rs1 + imm, rd <- PC, PC <- AR (bit 0 cleared by ARLO)
    m('JR0', ra='RS1', dsel='MEM', ldA=1)
    m('JR1', dsel='IMM', op='ADD', cinm=1, ldC=1, ldAR=1, kop='INC', nx='BR', cond='NK1', tgt='JR0')
    m('JR2', kop='CLR')
    m('JR3', ra='PC', dsel='MEM', az=1, op='ADD', ldR=1)
    m('JR4', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='JR3')
    m('JR5', nx='JMP', tgt='TP0')
    # ------------------------------------------------------------------ LOAD / STORE: AR <- rs1 + imm, then bytes
    m('EA0', ra='RS1', dsel='MEM', ldA=1)
    m('EA1', dsel='IMM', op='ADD', cinm=1, ldC=1, ldAR=1, kop='INC', nx='BR', cond='NK1', tgt='EA0')
    m('EA2', kop='CLR', nx='BR', cond='ISSTORE', tgt='ST0')
    m('LD0', nx='BR', cond='LDFILL', tgt='LDF')
    m('LD0b', ra='AR', dsel='MEM', az=1, op='ADD', ldR=1, nx='JMP', tgt='LD1')
    m('LDF', op='FILL', ldR=1)
    m('LD1', ra='RD', we=1, arinc=1, ldSR=1, kop='INC', nx='BR', cond='NK3', tgt='LD0')
    m('LD2', nx='JMP', tgt='L0')
    m('ST0', ra='RS2', dsel='MEM', az=1, op='ADD', ldR=1)
    m('ST1', ra='AR', we=1, arinc=1, kop='INC', nx='BR', cond='MORE', tgt='ST0')
    m('ST2', kop='CLR', nx='JMP', tgt='L0')
    # ------------------------------------------------------------------ shifts: AR <- ~shamt, rd <- rs1, then shamt single-bit passes over rd
    m('SH0', ra='RS2', dsel='BX', az=1, op='SUB', cinm=0, ldAR=1)
    m('SC0', ra='RS1', dsel='MEM', az=1, op='ADD', ldR=1)
    m('SC1', ra='RD', we=1, kop='INC', nx='BR', cond='NK3', tgt='SC0')
    m('SL0', nx='BR', cond='SHDONE', tgt='L0')
    m('SP_0', ra='RD', dsel='MEM', ldA=1, rev=1)
    m('SP_1', op='SHIFT', cinm=1, ldR=1, ldC=1)
    m('SP_2', ra='RD', we=1, rev=1, kop='INC', nx='BR', cond='NK3', tgt='SP_0')
    m('SP_3', arinc=1, nx='JMP', tgt='SL0')
    m('HALT', nx='JMP', tgt='HALT')
    return P


def assemble():
    """-> list of 128 entries (dict or None), label -> address"""
    P = build(); out = []; lab = {}
    for mi in P:
        if mi is None:
            while len(out) < DISPATCH_BASE: out.append(None)
            continue
        mi.addr = len(out); out.append(mi)
        if mi.label in lab: raise ValueError('duplicate label ' + mi.label)
        lab[mi.label] = mi.addr
    for mi in out:
        if mi is not None and mi.f['tgt'] is not None: mi.f['tgt'] = lab[mi.f['tgt']]
    assert len(out) <= 128, len(out)
    # the micro-instructions before DISPATCH_BASE: L0..SP3 = 16 exactly
    assert lab['D0'] == DISPATCH_BASE, lab['D0']
    return out, lab


if __name__ == '__main__':
    t, lab = assemble()
    print(len([x for x in t if x]), 'micro-instructions,', len(t), 'addresses used')
