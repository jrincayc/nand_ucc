"""spec2.py -- E4 v2 instruction word: d[7:0] reg[11:8] src[14:12] D[15] cpol[16] ccol[21:17] ph[23:22]."""
B = 24
F_D, F_REG, F_SRC, F_DFL, F_CPOL, F_CCOL, F_PH = 0, 8, 12, 15, 16, 17, 22
PH_NONE, PH_A, PH_P, PH_C = 0, 1, 2, 3
SRC_CONST, SRC_YLO, SRC_YHI, SRC_YLO1, SRC_YHI1, SRC_SUM, SRC_WF = 0, 1, 2, 3, 4, 5, 6
CC_ALWAYS = 24                      # ccol 24..31 read constant 1; with cpol=1 the row is unconditional
AXL, AXH, AYL, AYH, BXL, BXH, BYL, BYH, KIND, ANGLE, VAL, CMD = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15
def pack_int(d=0, reg=0, src=0, D=0, cpol=1, ccol=CC_ALWAYS, ph=0):
    assert 0 <= d < 256 and 0 <= reg < 16 and 0 <= src < 8 and 0 <= ccol < 32 and 0 <= ph < 4 and D in (0, 1) and cpol in (0, 1)
    return d | reg << F_REG | src << F_SRC | D << F_DFL | cpol << F_CPOL | ccol << F_CCOL | ph << F_PH
def bits(w): return [(w >> i) & 1 for i in range(B)]
def unpack(w): return dict(d=w & 255, reg=(w >> F_REG) & 15, src=(w >> F_SRC) & 7, D=(w >> F_DFL) & 1, cpol=(w >> F_CPOL) & 1, ccol=(w >> F_CCOL) & 31, ph=(w >> F_PH) & 3)
