// route3.s -- router stage 3, bit-exact with the command list of tools/route_ref.py: place commands and wiring (track / via) commands through the arm window.
// route3_place: place every gate and the three parts.   route3_wire: wire every net (late sinks queued, emitted last).  ROM programming (if any) goes between the two calls.
// Needs route1 + route2 results and the macro A16b from route2.s.  Uses sp as the arm window pointer.  Link: ra.
.macro PT x y l
    mv   a0, \x
    mv   a1, \y
    li   a2, \l
    jal  gp, addpt
.endm
.macro PTY x l
    mv   a0, \x
    lw   a1, RV_T5(x0)
    li   a2, \l
    jal  gp, addpt
.endm

route3_place:
    li   sp, ARMB
    sb   x0, 9(sp)
    lw   a5, V_N(x0)
    li   a4, 0
pl1:
    li   t0, KINDA
    add  t0, t0, a4
    lbu  a0, 0(t0)
    li   t0, ROWA
    add  t0, t0, a4
    lbu  t1, 0(t0)
    slli t1, t1, 1
    li   t0, YT
    add  t0, t0, t1
    lhu  a2, 0(t0)
    A16b t0, COLA, a4, t1
    lhu  t0, 0(t0)
    A16b t0, GXT, t0, t1
    lhu  a1, 0(t0)
    addi a1, a1, 1
    li   a3, 0
    sw   ra, RV_T9(x0)
    jal  gp, armplace
    lw   ra, RV_T9(x0)
    addi a4, a4, 1
    bne  a4, a5, pl1
    sw   ra, RV_T9(x0)
    li   t0, YT+2*(R_ROWS-1)
    lhu  a2, 0(t0)
    li   a0, 2
    lw   a1, RV_XR(x0)
    lw   a3, RV_ROMB(x0)
    jal  gp, armplace
    li   t0, YT+2*(R_ROWS-1)
    lhu  a2, 0(t0)
    li   a0, 3
    lw   a1, RV_XA(x0)
    li   a3, 0
    jal  gp, armplace
    lw   a3, RV_RAMB(x0)
    beqz a3, plz
    li   t0, YT+2*(R_ROWS-1)
    lhu  a2, 0(t0)
    li   a0, 4
    lw   a1, RV_XM(x0)
    jal  gp, armplace
plz:
    lw   ra, RV_T9(x0)
    ret

// armplace: a0 kind, a1 x, a2 y, a3 value
armplace:
    lw   t0, RV_OX(x0)
    add  a1, a1, t0
    lw   t0, RV_OY(x0)
    add  a2, a2, t0
    sb   a3, 10(sp)
    sb   a0, 8(sp)
    sb   a1, 0(sp)
    srli t0, a1, 8
    sb   t0, 1(sp)
    sb   a2, 2(sp)
    srli t0, a2, 8
    sb   t0, 3(sp)
    li   t0, 1
    sb   t0, 15(sp)
    jr   gp

// armw: a0 type (4 track, 5 via), a1 x1, a2 y1, a3 x2, a4 y2, a5 layer
armw:
    lw   t0, RV_OX(x0)
    add  a1, a1, t0
    sb   a1, 0(sp)
    srli t1, a1, 8
    sb   t1, 1(sp)
    lw   t0, RV_OY(x0)
    add  a2, a2, t0
    sb   a2, 2(sp)
    srli t1, a2, 8
    sb   t1, 3(sp)
    li   t1, 5
    beq  a0, t1, armw2
    lw   t0, RV_OX(x0)
    add  a3, a3, t0
    sb   a3, 4(sp)
    srli t1, a3, 8
    sb   t1, 5(sp)
    lw   t0, RV_OY(x0)
    add  a4, a4, t0
    sb   a4, 6(sp)
    srli t1, a4, 8
    sb   t1, 7(sp)
    sb   a5, 10(sp)
armw2:
    sb   a0, 15(sp)
    jr   gp

// emit_seg: as armw, but queued if RV_LATE != 0
emit_seg:
    lw   t0, RV_LATE(x0)
    beqz t0, armw
    li   t1, Q1
    li   t2, RV_Q1N
    li   tp, 1
    beq  t0, tp, es1
    li   t1, Q2
    li   t2, RV_Q2N
es1:
    lw   tp, 0(t2)
    li   t0, QCAP
    bgeu tp, t0, esover
    addi t0, tp, 1
    sw   t0, 0(t2)
    slli t0, tp, 3
    slli tp, tp, 2
    add  t0, t0, tp
    add  t1, t1, t0
    sh   a0, 0(t1)
    sh   a1, 2(t1)
    sh   a2, 4(t1)
    sh   a3, 6(t1)
    sh   a4, 8(t1)
    sh   a5, 10(t1)
    jr   gp
esover:
    li   t0, 3
    sw   t0, V_ERR(x0)
    jr   gp

addpt:
    lw   t0, RV_PN(x0)
    slli t1, t0, 2
    slli t2, t0, 1
    add  t1, t1, t2
    li   t2, PTS
    add  t1, t1, t2
    sh   a0, 0(t1)
    sh   a1, 2(t1)
    sh   a2, 4(t1)
    addi t0, t0, 1
    sw   t0, RV_PN(x0)
    jr   gp

adddst:
    lw   t0, RV_DN(x0)
    li   a0, DST
    slli t1, t0, 2
    slli t2, t0, 1
    add  t1, t1, t2
    add  t1, t1, a0                 // end of the driver stub
adl:
    beq  a0, t1, adz
    lw   t0, RV_PN(x0)
    slli a1, t0, 2
    slli a2, t0, 1
    add  a1, a1, a2
    li   a2, PTS
    add  a1, a1, a2                 // destination
    lhu  a2, 0(a0)
    sh   a2, 0(a1)
    lhu  a2, 2(a0)
    sh   a2, 2(a1)
    lhu  a2, 4(a0)
    sh   a2, 4(a1)
    addi t0, t0, 1
    sw   t0, RV_PN(x0)
    addi a0, a0, 6
    j    adl
adz:
    jr   gp

// setlh: row a0 = (min(a1,a2), max(a1,a2)) ; updlh: widen row a0 by a1
setlh:
    slli t0, a0, 1
    li   t1, TLO
    add  t1, t1, t0
    li   t2, THI
    add  t0, t0, t2
    bleu a1, a2, sl1
    sh   a2, 0(t1)
    sh   a1, 0(t0)
    jr   gp
sl1:
    sh   a1, 0(t1)
    sh   a2, 0(t0)
    jr   gp
updlh:
    slli t0, a0, 1
    li   t1, TLO
    add  t1, t1, t0
    lhu  t2, 0(t1)
    bleu t2, a1, ul1
    sh   a1, 0(t1)
ul1:
    li   t1, THI
    add  t1, t1, t0
    lhu  t2, 0(t1)
    bgeu t2, a1, ul2
    sh   a1, 0(t1)
ul2:
    jr   gp

// drvpts: net RV_NET -> RV_DROW, RV_DCOL, RV_DY, DST (reversed stub), RV_DN
drvpts:
    sw   gp, RV_T6(x0)
    lw   a1, RV_NET(x0)
    jal  gp, drvpin
    sw   a4, RV_DROW(x0)
    sw   a5, RV_DCOL(x0)
    slli t0, a4, 1
    li   t1, YT
    add  t0, t0, t1
    lhu  a3, 0(t0)
    sw   a3, RV_DY(x0)
    lw   t0, V_N(x0)
    bgeu a1, t0, dvp
    li   t0, DST
    sh   a5, 0(t0)
    sh   a3, 2(t0)
    li   t1, 1
    sh   t1, 4(t0)
    sw   t1, RV_DN(x0)
    lw   gp, RV_T6(x0)
    jr   gp
dvp:
    sub  t1, a1, t0
    li   t2, 8
    lw   a2, RV_XR(x0)
    bltu t1, t2, dv1
    sub  t1, t1, t2
    lw   a2, RV_XM(x0)
dv1:
    add  a3, a3, t1                 // y = dY + j
    li   t0, DST
    sh   a5, 0(t0)
    sh   a3, 2(t0)
    li   t2, 1
    sh   t2, 4(t0)
    sh   a5, 6(t0)
    sh   a3, 8(t0)
    sh   x0, 10(t0)
    addi a2, a2, 1
    sh   a2, 12(t0)
    sh   a3, 14(t0)
    sh   x0, 16(t0)
    li   t1, 3
    sw   t1, RV_DN(x0)
    lw   gp, RV_T6(x0)
    jr   gp

// sinkpts: record a2 -> a4 row, a5 col, and pushes the stub points
sinkpts:
    sw   gp, RV_T6(x0)
    sw   a2, RV_REC(x0)
    jal  gp, sinkpin
    slli t0, a4, 1
    li   t1, YT
    add  t0, t0, t1
    lhu  a3, 0(t0)                   // Y of the row
    li   t1, 0x8000
    lw   a2, RV_REC(x0)
    bgeu a2, t1, stp
    andi t0, a2, 1
    bnez t0, st1
    mv   a0, a5
    mv   a1, a3
    li   a2, 1
    jal  gp, addpt
    lw   gp, RV_T6(x0)
    jr   gp
st1:
    addi a3, a3, 1
    addi a0, a5, 1
    mv   a1, a3
    li   a2, 0
    jal  gp, addpt
    mv   a0, a5
    mv   a1, a3
    li   a2, 0
    jal  gp, addpt
    mv   a0, a5
    mv   a1, a3
    li   a2, 1
    jal  gp, addpt
    lw   gp, RV_T6(x0)
    jr   gp
stp:
    sub  t0, a2, t1
    slli t1, t0, 2
    slli t0, t0, 1
    add  t0, t0, t1
    li   t1, PTAB
    add  t0, t0, t1
    lhu  t1, 0(t0)
    lhu  t2, 2(t0)                  // a
    srli t1, t1, 8                  // side
    add  a3, a3, t2                 // y = Y + a
    beqz t1, stpl
    sub  a0, a5, t2
    addi a0, a0, -1                 // x + 1
    j    stpa
stpl:
    add  a0, a5, t2
    addi a0, a0, 1                  // x
stpa:
    mv   a1, a3
    li   a2, 0
    jal  gp, addpt
    mv   a0, a5
    mv   a1, a3
    li   a2, 0
    jal  gp, addpt
    mv   a0, a5
    mv   a1, a3
    li   a2, 1
    jal  gp, addpt
    lw   gp, RV_T6(x0)
    jr   gp

route3_wire:
    sw   ra, RV_LINKR(x0)
    li   sp, ARMB
    sw   x0, RV_Q1N(x0)
    sw   x0, RV_Q2N(x0)
    sw   x0, RV_LATE(x0)
    li   a1, 0
w_net:
    sw   a1, RV_NET(x0)
    A16b t0, NOFF, a1, t1
    lhu  a2, 0(t0)
    lhu  a3, 2(t0)
    bne  a2, a3, w_go
    j    w_next
w_go:
    sub  a3, a3, a2
    sw   a3, RV_NK(x0)
    // track y and trunk reset per interval row
    A16b t0, IVS, a1, t1
    lhu  a4, 0(t0)
    lhu  a5, 2(t0)
w_iv:
    beq  a4, a5, w_ivd
    li   t0, IVROW
    add  t0, t0, a4
    lbu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, YT
    add  t1, t1, t0
    lhu  t1, 0(t1)
    addi t1, t1, -1
    li   t2, IVTRK
    add  t2, t2, a4
    lbu  t2, 0(t2)
    sub  t1, t1, t2
    li   t2, TYT
    add  t2, t2, t0
    sh   t1, 0(t2)
    li   t2, TLO
    add  t2, t2, t0
    li   t1, 65535
    sh   t1, 0(t2)
    addi a4, a4, 1
    j    w_iv
w_ivd:
    // lane x
    li   t0, LIDX
    add  t0, t0, a1
    lbu  a2, 0(t0)
    li   a3, 65535
    li   t1, 255
    beq  a2, t1, w_nl
    li   t0, ZONE
    add  t0, t0, a1
    lbu  t0, 0(t0)
    A16b t1, ZXB, t0, t2
    lhu  t1, 0(t1)
    add  a3, t1, a2
w_nl:
    sw   a3, RV_LANE(x0)
    jal  gp, drvpts
    // keys: sorted insertion
    lw   a1, RV_NET(x0)
    A16b t0, NOFF, a1, t1
    lhu  t0, 0(t0)
    sw   t0, RV_T0(x0)                // first sink record index
    li   a4, 0
w_key:
    lw   t0, RV_NK(x0)
    beq  a4, t0, w_keyd
    sw   a4, RV_SI(x0)
    lw   t0, RV_T0(x0)
    add  t0, t0, a4
    A16b t1, NSNK, t0, t2
    lhu  a2, 0(t1)
    sw   a2, RV_REC(x0)
    jal  gp, sinkpin
    lw   t0, RV_DROW(x0)
    sub  t0, a4, t0
    bgez t0, wk1
    sub  t0, x0, t0
wk1:
    lw   t1, RV_DCOL(x0)
    sub  t1, a5, t1
    bgez t1, wk2
    sub  t1, x0, t1
wk2:
    slli t0, t0, 12
    add  t0, t0, t1
    lw   a2, RV_REC(x0)
    li   t1, 0x8000
    bgeu a2, t1, wk3
    A16b t2, SRC, a2, t1
    lhu  t2, 0(t2)
    j    wk4
wk3:
    sub  t2, a2, t1
    slli t1, t2, 2
    slli t2, t2, 1
    add  t2, t2, t1
    li   t1, PTAB+4
    add  t2, t2, t1
    lhu  t2, 0(t2)
wk4:
    srli t2, t2, 14
    slli t2, t2, 19
    add  t0, t0, t2                   // key
    lw   a4, RV_SI(x0)
    mv   a5, a4                       // insertion position
wk5:
    beqz a5, wk6
    addi t1, a5, -1
    slli t2, t1, 2
    li   a3, KEYS
    add  t2, t2, a3
    lw   a3, 0(t2)
    bleu a3, t0, wk6
    sw   a3, 4(t2)
    slli t2, t1, 1
    li   a3, KREC
    add  t2, t2, a3
    lhu  a3, 0(t2)
    sh   a3, 2(t2)
    mv   a5, t1
    j    wk5
wk6:
    slli t2, a5, 2
    li   a3, KEYS
    add  t2, t2, a3
    sw   t0, 0(t2)
    slli t2, a5, 1
    li   a3, KREC
    add  t2, t2, a3
    sh   a2, 0(t2)
    addi a4, a4, 1
    j    w_key
w_keyd:
    li   t0, 1
    sw   t0, RV_FIRST(x0)
    sw   x0, RV_SPAN(x0)
    sw   x0, RV_SI(x0)
w_snk:
    lw   a4, RV_SI(x0)
    lw   t0, RV_NK(x0)
    beq  a4, t0, w_next
    slli t1, a4, 2
    li   t2, KEYS
    add  t1, t1, t2
    lw   t1, 0(t1)
    srli t1, t1, 19
    sw   t1, RV_LATE(x0)
    slli t1, a4, 1
    li   t2, KREC
    add  t1, t1, t2
    lhu  a2, 0(t1)
    sw   x0, RV_PN(x0)
    jal  gp, sinkpts
    jal  gp, proc_sink
    jal  gp, flushpts
    lw   a4, RV_SI(x0)
    addi a4, a4, 1
    sw   a4, RV_SI(x0)
    j    w_snk
w_next:
    lw   a1, RV_NET(x0)
    addi a1, a1, 1
    lw   t0, V_N(x0)
    addi t0, t0, 16
    bne  a1, t0, w_net
    // queued late commands
    sw   x0, RV_LATE(x0)
    li   a4, Q1
    lw   a5, RV_Q1N(x0)
    jal  gp, qflush
    li   a4, Q2
    lw   a5, RV_Q2N(x0)
    jal  gp, qflush
    lw   ra, RV_LINKR(x0)
    ret

qflush:
    sw   gp, RV_T6(x0)
qf1:
    beqz a5, qf2
    sw   a4, RV_T7(x0)
    sw   a5, RV_T8(x0)
    lhu  a0, 0(a4)
    lhu  a1, 2(a4)
    lhu  a2, 4(a4)
    lhu  a3, 6(a4)
    lhu  t0, 8(a4)
    lhu  a5, 10(a4)
    mv   a4, t0
    jal  gp, armw
    lw   a4, RV_T7(x0)
    lw   a5, RV_T8(x0)
    addi a4, a4, 12
    addi a5, a5, -1
    j    qf1
qf2:
    lw   gp, RV_T6(x0)
    jr   gp

// convert the point list PTS[0..PN) into track / via commands
flushpts:
    sw   gp, RV_T6(x0)
    lw   t0, RV_PN(x0)
    li   a4, 1
fp1:
    lw   t0, RV_PN(x0)
    bgeu a4, t0, fp9
    sw   a4, RV_T7(x0)
    slli t1, a4, 2
    slli t2, a4, 1
    add  t1, t1, t2
    li   t2, PTS-6
    add  t1, t1, t2
    lhu  a1, 0(t1)
    lhu  a2, 2(t1)
    lhu  t2, 4(t1)
    lhu  a3, 6(t1)
    lhu  a4, 8(t1)
    lhu  a5, 10(t1)
    bne  t2, a5, fpv
    li   a0, 4
    jal  gp, emit_seg
    j    fpn
fpv:
    li   a0, 5
    jal  gp, emit_seg
fpn:
    lw   a4, RV_T7(x0)
    addi a4, a4, 1
    j    fp1
fp9:
    lw   gp, RV_T6(x0)
    jr   gp

// one sink: PTS holds the stub; a4 = row, a5 = col
proc_sink:
    sw   gp, RV_T9(x0)
    lw   s0, RV_DROW(x0)
    lw   s1, RV_DCOL(x0)
    A16b t0, TYT, a4, t1
    lhu  tp, 0(t0)
    PT   a5, tp, 1
    PT   a5, tp, 0
    lw   t0, RV_FIRST(x0)
    bnez t0, ps_first
    A16b t0, TLO, a4, t1
    lhu  t0, 0(t0)
    li   t1, 65535
    bne  t0, t1, ps_old
    // new row, not the first sink
    lw   a3, RV_LANE(x0)
    PT   a3, tp, 0
    PT   a3, tp, 1
    lw   t0, RV_SPAN(x0)
    bnez t0, psn_span
    A16b t0, TYT, s0, t1
    lhu  t0, 0(t0)
    sw   t0, RV_T5(x0)
    PTY  a3, 1
    PTY  a3, 0
    A16b t0, TLO, s0, t1
    lhu  a2, 0(t0)
    bgeu a3, a2, pn1
    PTY  a2, 0
    j    pn2
pn1:
    A16b t0, THI, s0, t1
    lhu  a2, 0(t0)
    bgeu a2, a3, pn2
    PTY  a2, 0
pn2:
    mv   a0, s0
    mv   a1, a3
    jal  gp, updlh
    lw   t0, RV_T5(x0)
    bleu tp, t0, pn3
    sw   t0, RV_SPLO(x0)
    sw   tp, RV_SPHI(x0)
    j    pn4
pn3:
    sw   tp, RV_SPLO(x0)
    sw   t0, RV_SPHI(x0)
pn4:
    li   t0, 1
    sw   t0, RV_SPAN(x0)
    j    psn_set
psn_span:
    lw   t0, RV_SPLO(x0)
    bgeu tp, t0, pn5
    mv   a2, t0
    PT   a3, a2, 1
    sw   tp, RV_SPLO(x0)
    j    psn_set
pn5:
    lw   t0, RV_SPHI(x0)
    bleu tp, t0, psn_set
    mv   a2, t0
    PT   a3, a2, 1
    sw   tp, RV_SPHI(x0)
psn_set:
    mv   a0, a4
    mv   a1, a5
    mv   a2, a3
    jal  gp, setlh
    lw   gp, RV_T9(x0)
    jr   gp
ps_old:
    A16b t0, TLO, a4, t1
    lhu  a3, 0(t0)
    A16b t0, THI, a4, t1
    lhu  a2, 0(t0)
    bgeu a5, a3, po1
    PT   a3, tp, 0
    j    po3
po1:
    bgeu a2, a5, po3
    PT   a2, tp, 0
po3:
    mv   a0, a4
    mv   a1, a5
    jal  gp, updlh
    lw   gp, RV_T9(x0)
    jr   gp
ps_first:
    sw   x0, RV_FIRST(x0)
    bne  a4, s0, psf2
    beq  s1, a5, psf1
    PT   s1, tp, 0
    PT   s1, tp, 1
psf1:
    jal  gp, adddst
    mv   a0, a4
    mv   a1, a5
    mv   a2, s1
    jal  gp, setlh
    lw   gp, RV_T9(x0)
    jr   gp
psf2:
    lw   a3, RV_LANE(x0)
    PT   a3, tp, 0
    PT   a3, tp, 1
    A16b t0, TYT, s0, t1
    lhu  t0, 0(t0)
    sw   t0, RV_T5(x0)
    PTY  a3, 1
    PTY  a3, 0
    PTY  s1, 0
    PTY  s1, 1
    jal  gp, adddst
    mv   a0, a4
    mv   a1, a5
    mv   a2, a3
    jal  gp, setlh
    mv   a0, s0
    mv   a1, s1
    mv   a2, a3
    jal  gp, setlh
    lw   t0, RV_T5(x0)
    bleu tp, t0, pf3
    sw   t0, RV_SPLO(x0)
    sw   tp, RV_SPHI(x0)
    j    pf4
pf3:
    sw   tp, RV_SPLO(x0)
    sw   t0, RV_SPHI(x0)
pf4:
    li   t0, 1
    sw   t0, RV_SPAN(x0)
    lw   gp, RV_T9(x0)
    jr   gp
