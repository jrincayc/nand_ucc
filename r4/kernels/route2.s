// route2.s -- router stage 2, bit-exact with tools/route_ref.py: channel intervals, left-edge tracks, row baselines Y, height H.
// Needs the results of route1 (ROWA, COLA, NOFF, NSNK, ZONE, LIDX, ZXB, GXT, RV_XR/XA/XM).  Link: ra.
// Results: IVS, IVROW, IVLO, IVHI, IVTRK, TT (tracks per row), YT (row baselines), RV_NI, RV_H.
.macro A16b d base i s
    slli \d, \i, 1
    li   \s, \base
    add  \d, \d, \s
.endm
.macro IVUPD
    slli t0, a4, 1
    li   t1, RLO
    add  t1, t1, t0
    lhu  t2, 0(t1)
    bleu t2, a5, ivu1\@
    sh   a5, 0(t1)
ivu1\@:
    li   t1, RHI
    add  t1, t1, t0
    lhu  t2, 0(t1)
    bgeu t2, a5, ivu2\@
    sh   a5, 0(t1)
ivu2\@:
.endm
.macro KEYOF v
    mv   t1, \v
    beqz a3, kb\@
    slli t1, t1, 1
    add  t1, t1, a2
    lhu  t1, 0(t1)
    j    kd\@
kb\@:
    add  t1, t1, a2
    lbu  t1, 0(t1)
kd\@:
.endm

route2:
    sw   ra, RV_LINKR(x0)
    jal  ra, r2_iv
    jal  ra, r2_sort
    jal  ra, r2_trk
    lw   ra, RV_LINKR(x0)
    ret

// pin of sink record a2 -> a4 row, a5 column   (link gp)
sinkpin:
    li   t1, 0x8000
    bgeu a2, t1, spp
    srli t0, a2, 1
    li   t1, ROWA
    add  t1, t1, t0
    lbu  a4, 0(t1)
    A16b t1, COLA, t0, t2
    lhu  t1, 0(t1)
    A16b t1, GXT, t1, t2
    lhu  a5, 0(t1)
    andi t0, a2, 1
    addi a5, a5, 1
    sub  a5, a5, t0
    jr   gp
spp:
    li   t1, 0x8000
    sub  t0, a2, t1
    slli t1, t0, 2
    slli t0, t0, 1
    add  t0, t0, t1
    li   t1, PTAB
    add  t0, t0, t1
    lhu  t1, 0(t0)
    lhu  a5, 2(t0)                  // a = port index within the part
    srli t2, t1, 8                  // side
    andi t1, t1, 255                // part
    li   a4, R_ROWS-1
    lw   t0, RV_XR(x0)
    beqz t1, sp1
    lw   t0, RV_XA(x0)
    li   a4, 1
    beq  t1, a4, sp0
    lw   t0, RV_XM(x0)
sp0:
    li   a4, R_ROWS-1
sp1:
    beqz t2, spl
    add  a5, a5, t0
    addi a5, a5, 2
    jr   gp
spl:
    sub  a5, t0, a5
    addi a5, a5, -1
    jr   gp

// pin of driver net a1 -> a4 row, a5 column   (link gp)
drvpin:
    lw   t0, V_N(x0)
    bgeu a1, t0, dpp
    li   t1, ROWA
    add  t1, t1, a1
    lbu  a4, 0(t1)
    A16b t1, COLA, a1, t2
    lhu  t1, 0(t1)
    A16b t1, GXT, t1, t2
    lhu  a5, 0(t1)
    addi a5, a5, 2
    jr   gp
dpp:
    li   a4, R_ROWS-1
    sub  t1, a1, t0
    lw   a5, RV_XR(x0)
    li   t2, 8
    bltu t1, t2, dp1
    sub  t1, t1, t2
    lw   a5, RV_XM(x0)
dp1:
    add  a5, a5, t1
    addi a5, a5, 2
    jr   gp

r2_iv:
    sw   ra, RV_T9(x0)
    li   a1, 0
    sw   x0, RV_NI(x0)
ivn:
    lw   t0, RV_NI(x0)
    A16b t1, IVS, a1, t2
    sh   t0, 0(t1)
    A16b t0, NOFF, a1, t1
    lhu  a2, 0(t0)
    lhu  a3, 2(t0)
    sw   a2, RV_T1(x0)
    sw   a3, RV_T2(x0)
    sw   a1, RV_T0(x0)
    beq  a2, a3, ivnext
    li   t2, 0
ivc:
    slli t0, t2, 1
    li   t1, RLO
    add  t1, t1, t0
    li   a0, 65535
    sh   a0, 0(t1)
    li   t1, RHI
    add  t1, t1, t0
    sh   x0, 0(t1)
    addi t2, t2, 1
    li   t0, R_ROWS
    bne  t2, t0, ivc
    jal  gp, drvpin
    IVUPD
ivs:
    lw   a2, RV_T1(x0)
    lw   a3, RV_T2(x0)
    beq  a2, a3, ivsd
    A16b t0, NSNK, a2, t1
    lhu  a2, 0(t0)
    jal  gp, sinkpin
    IVUPD
    lw   a2, RV_T1(x0)
    addi a2, a2, 1
    sw   a2, RV_T1(x0)
    j    ivs
ivsd:
    lw   a1, RV_T0(x0)
    li   a3, 0                       // a3 = lane x, valid if a2 != 255 -> a0 flag
    li   t0, LIDX
    add  t0, t0, a1
    lbu  a2, 0(t0)
    li   a0, 0
    li   t1, 255
    beq  a2, t1, ivr
    li   t0, ZONE
    add  t0, t0, a1
    lbu  t0, 0(t0)
    A16b t1, ZXB, t0, t2
    lhu  t1, 0(t1)
    add  a3, t1, a2
    li   a0, 1
ivr:
    li   a4, 0
ivr1:
    slli t0, a4, 1
    li   t1, RLO
    add  t1, t1, t0
    lhu  a5, 0(t1)
    li   t2, 65535
    beq  a5, t2, ivr3
    li   t1, RHI
    add  t1, t1, t0
    lhu  t0, 0(t1)
    beqz a0, ivr2
    bleu a5, a3, ivr4
    mv   a5, a3
ivr4:
    bgeu t0, a3, ivr2
    mv   t0, a3
ivr2:
    lw   t1, RV_NI(x0)
    mv   t2, t1
    addi t1, t1, 1
    sw   t1, RV_NI(x0)
    li   t1, IVROW
    add  t1, t1, t2
    sb   a4, 0(t1)
    A16b t1, IVLO, t2, a1
    sh   a5, 0(t1)
    A16b t1, IVHI, t2, a1
    sh   t0, 0(t1)
    lw   a1, RV_T0(x0)
ivr3:
    addi a4, a4, 1
    li   t0, R_ROWS
    bne  a4, t0, ivr1
ivnext:
    lw   a1, RV_T0(x0)
    addi a1, a1, 1
    lw   t0, V_N(x0)
    addi t0, t0, 16
    bne  a1, t0, ivn
    lw   t0, RV_NI(x0)
    A16b t1, IVS, a1, t2
    sh   t0, 0(t1)
    lw   ra, RV_T9(x0)
    ret

// csort: a0 = in (u16[]), a1 = out, a2 = keys base, a3 = 0 byte keys / 1 half keys, a4 = K   (link gp)
csort:
    lw   a5, RV_NI(x0)
    li   t0, 0
    addi tp, a4, 2
cs0:
    A16b t1, CNTA, t0, t2
    sh   x0, 0(t1)
    addi t0, t0, 1
    bne  t0, tp, cs0
    sw   x0, RV_T3(x0)
cs1:
    lw   t0, RV_T3(x0)
    beq  t0, a5, cs2
    slli t0, t0, 1
    add  t0, t0, a0
    lhu  t0, 0(t0)
    KEYOF t0
    addi t1, t1, 1
    A16b t0, CNTA, t1, t2
    lhu  t2, 0(t0)
    addi t2, t2, 1
    sh   t2, 0(t0)
    lw   t0, RV_T3(x0)
    addi t0, t0, 1
    sw   t0, RV_T3(x0)
    j    cs1
cs2:
    li   t0, 0
cs3:
    beq  t0, a4, cs4
    A16b t1, CNTA, t0, t2
    lhu  t2, 0(t1)
    lhu  tp, 2(t1)
    add  tp, tp, t2
    sh   tp, 2(t1)
    addi t0, t0, 1
    j    cs3
cs4:
    sw   x0, RV_T3(x0)
cs5:
    lw   t0, RV_T3(x0)
    beq  t0, a5, cs6
    slli t0, t0, 1
    add  t0, t0, a0
    lhu  t0, 0(t0)
    sw   t0, RV_T4(x0)
    KEYOF t0
    A16b t0, CNTA, t1, t2
    lhu  t2, 0(t0)
    addi tp, t2, 1
    sh   tp, 0(t0)
    slli t2, t2, 1
    add  t2, t2, a1
    lw   t0, RV_T4(x0)
    sh   t0, 0(t2)
    lw   t0, RV_T3(x0)
    addi t0, t0, 1
    sw   t0, RV_T3(x0)
    j    cs5
cs6:
    jr   gp

r2_sort:
    sw   ra, RV_T9(x0)
    lw   a5, RV_NI(x0)
    li   t0, 0
    beqz a5, rsd
rs0:
    A16b t1, ORDA, t0, t2
    sh   t0, 0(t1)
    addi t0, t0, 1
    bne  t0, a5, rs0
rsd:
    lw   a4, RV_W(x0)
    addi a4, a4, 1
    li   a0, ORDA
    li   a1, ORDB
    li   a2, IVHI
    li   a3, 1
    jal  gp, csort
    lw   a4, RV_W(x0)
    addi a4, a4, 1
    li   a0, ORDB
    li   a1, ORDA
    li   a2, IVLO
    li   a3, 1
    jal  gp, csort
    li   a4, R_ROWS
    li   a0, ORDA
    li   a1, ORDB
    li   a2, IVROW
    li   a3, 0
    jal  gp, csort
    lw   ra, RV_T9(x0)
    ret

// left-edge tracks over ORDB (sorted by row, lo, hi, net)
r2_trk:
    li   t0, 0
rt0:
    slli t1, t0, 1
    li   t2, TT
    add  t1, t1, t2
    sh   x0, 0(t1)
    addi t0, t0, 1
    li   t1, 32
    bne  t0, t1, rt0
    lw   a5, RV_NI(x0)
    li   a0, 0                       // position in ORDB
    li   a1, -1                      // current row
    li   a2, 0                       // number of tracks (ends[])
    beq  a0, a5, rtend
rt1:
    A16b t0, ORDB, a0, t1
    lhu  a3, 0(t0)                   // interval index
    li   t0, IVROW
    add  t0, t0, a3
    lbu  a4, 0(t0)
    beq  a4, a1, rt2
    bltz a1, rtn
    slli t0, a1, 1
    li   t1, TT
    add  t0, t0, t1
    sh   a2, 0(t0)
rtn:
    mv   a1, a4
    li   a2, 0
rt2:
    A16b t0, IVLO, a3, t1
    lhu  tp, 0(t0)
    A16b t0, IVHI, a3, t1
    lhu  gp, 0(t0)
    li   t2, 0
rt3:
    beq  t2, a2, rtnew
    A16b t0, ENDS, t2, t1
    lhu  t1, 0(t0)
    bgeu t1, tp, rt3n
    sh   gp, 0(t0)
    j    rt4
rt3n:
    addi t2, t2, 1
    j    rt3
rtnew:
    A16b t0, ENDS, a2, t1
    sh   gp, 0(t0)
    addi a2, a2, 1
rt4:
    li   t0, IVTRK
    add  t0, t0, a3
    sb   t2, 0(t0)
    addi a0, a0, 1
    bne  a0, a5, rt1
    slli t0, a1, 1
    li   t1, TT
    add  t0, t0, t1
    sh   a2, 0(t0)
rtend:
    // Y[0] = T[0] + 1 ; Y[r] = Y[r-1] + 3 + T[r]
    li   t1, TT
    lhu  t0, 0(t1)
    addi t0, t0, 1
    li   t1, YT
    sh   t0, 0(t1)
    li   a0, 1
ry:
    slli t1, a0, 1
    li   t2, TT
    add  t2, t2, t1
    lhu  t2, 0(t2)
    addi t0, t0, 3
    add  t0, t0, t2
    li   t2, YT
    add  t1, t1, t2
    sh   t0, 0(t1)
    addi a0, a0, 1
    li   t1, R_ROWS
    bne  a0, t1, ry
    // H = Y[R-1] + max(2, Rm, Q+9, 9)
    li   t1, 9
    lw   t2, RV_ROMB(x0)
    bgeu t1, t2, h1
    mv   t1, t2
h1:
    lw   t2, RV_RAMB(x0)
    addi t2, t2, 9
    bgeu t1, t2, h2
    mv   t1, t2
h2:
    add  t0, t0, t1
    sw   t0, RV_H(x0)
    ret
