"""spec.py -- E4 instruction word format (plane columns) and arm register map."""
B = 24
F_D, F_REG, F_SRC, F_CEN, F_CPOL, F_CCOL, F_PH = 0, 8, 12, 15, 16, 17, 22      # lowest column of each field
W_D, W_REG, W_SRC, W_CCOL, W_PH = 8, 4, 3, 5, 2
PH_NONE, PH_A, PH_P, PH_C = 0, 1, 2, 3
SRC_CONST, SRC_YLO, SRC_YHI, SRC_YLO1, SRC_YHI1 = 0, 1, 2, 3, 4
# arm registers
AXL, AXH, AYL, AYH, BXL, BXH, BYL, BYH, KIND, ANGLE, VAL, CMD = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15
def pack(d=0, reg=0, src=SRC_CONST, cen=0, cpol=0, ccol=0, ph=PH_NONE):
    assert 0 <= d < 256 and 0 <= reg < 16 and 0 <= src < 8 and 0 <= ccol < 32 and 0 <= ph < 4
    w = d | reg << F_REG | src << F_SRC | cen << F_CEN | cpol << F_CPOL | ccol << F_CCOL | ph << F_PH
    return [(w >> i) & 1 for i in range(B)]
def unpack(bits):
    w = sum(b << i for i, b in enumerate(bits))
    return dict(d=w & 255, reg=(w >> F_REG) & 15, src=(w >> F_SRC) & 7, cen=(w >> F_CEN) & 1, cpol=(w >> F_CPOL) & 1, ccol=(w >> F_CCOL) & 31, ph=(w >> F_PH) & 3)
