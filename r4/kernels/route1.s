// route1.s -- router stage 1, bit-exact with tools/route_ref.py: fold (rank -> row, column), sink lists per net, zone and lane per net, physical x positions.
// Call: jal ra, route1   (inputs as in memmap_route.s; FINAL = placement order).  Results: ROWA, COLA, NOFF, NSNK, ZONE, LIDX, ZWT, ZXB, GXT, RV_XR/XA/XM/W.
.macro A16 d base i s
    slli \d, \i, 1
    li   \s, \base
    add  \d, \d, \s
.endm
.macro MUL22 d s
    slli \d, \s, 4
    slli t2, \s, 2
    add  \d, \d, t2
    slli t2, \s, 1
    add  \d, \d, t2
.endm
// ZPIN: pin with row a4 and anchor a5 -> per-row min / max, touched list (s1 = count), cmin tp, cmax gp
.macro ZPIN
    slli t0, a4, 1
    li   t1, RLO
    add  t1, t1, t0
    lhu  t2, 0(t1)
    li   t0, 65535
    bne  t2, t0, zpe\@
    sh   a5, 0(t1)
    li   t0, RTCH
    add  t0, t0, s1
    sb   a4, 0(t0)
    addi s1, s1, 1
    slli t0, a4, 1
    li   t1, RHI
    add  t0, t0, t1
    sh   a5, 0(t0)
    j    zpd\@
zpe\@:
    bgeu a5, t2, zpf\@
    sh   a5, 0(t1)
zpf\@:
    slli t0, a4, 1
    li   t1, RHI
    add  t1, t1, t0
    lhu  t2, 0(t1)
    bleu a5, t2, zpd\@
    sh   a5, 0(t1)
zpd\@:
    bgeu a4, tp, zpg\@
    mv   tp, a4
zpg\@:
    bleu a4, gp, zph\@
    mv   gp, a4
zph\@:
.endm

route1:
    sw   ra, RV_LINKR(x0)
    jal  ra, r1_fold
    jal  ra, r1_nets
    jal  ra, r1_zones
    jal  ra, r1_xcols
    lw   ra, RV_LINKR(x0)
    ret

// ---- fold
r1_fold:
    lw   a0, V_N(x0)
    addi t0, a0, R_ROWS-1
    li   a1, 0
cf1:
    li   t1, R_ROWS
    bltu t0, t1, cf2
    sub  t0, t0, t1
    addi a1, a1, 1
    j    cf1
cf2:
    sw   a1, RV_COLS(x0)
    addi t0, a1, -1
    li   a2, 0
cf3:
    li   t1, R_ZONEW
    bltu t0, t1, cf4
    sub  t0, t0, t1
    addi a2, a2, 1
    j    cf3
cf4:
    sw   a2, RV_NZ(x0)
    li   a2, 0
    li   a3, 0
    li   a4, 0
cf5:
    A16  t0, FINAL, a2, t1
    lhu  t0, 0(t0)
    li   t1, ROWA
    add  t1, t1, t0
    sb   a3, 0(t1)
    andi t1, a3, 1
    mv   t2, a4
    beqz t1, cf6
    addi t2, a1, -1
    sub  t2, t2, a4
cf6:
    slli t0, t0, 1
    li   t1, COLA
    add  t0, t0, t1
    sh   t2, 0(t0)
    addi a4, a4, 1
    bne  a4, a1, cf7
    li   a4, 0
    addi a3, a3, 1
cf7:
    addi a2, a2, 1
    bne  a2, a0, cf5
// logical part anchors (zone choice only): xs = 3*cols+4; ROM, ARM, RAM blocks
    slli t0, a1, 1
    add  t0, t0, a1
    addi t0, t0, 4
    lw   t1, RV_ROMB(x0)
    add  t1, t1, t0
    addi t1, t1, 1
    sw   t1, RV_PBLR(x0)
    addi t0, t1, 11
    addi t1, t0, 6
    sw   t1, RV_PBLA(x0)
    addi t0, t1, 11
    lw   t1, RV_RAMB(x0)
    add  t1, t1, t0
    addi t1, t1, 10
    sw   t1, RV_PBLM(x0)
    ret

// ---- sink lists (counting sort in pin-list order: gate inputs ascending, then ports)
r1_nets:
    lw   a0, V_N(x0)
    addi a5, a0, 16
    li   a1, 0
rn0:
    A16  t0, NOFF, a1, t1
    sh   x0, 0(t0)
    addi a1, a1, 1
    bgeu a5, a1, rn0
    slli a2, a0, 1
    li   a1, 0
rn1:
    A16  t0, SRC, a1, t1
    lhu  t0, 0(t0)
    li   t1, 65535
    beq  t0, t1, rn2
    li   t1, 0x3FFF
    and  t0, t0, t1
    A16  t1, NOFF, t0, t2
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
rn2:
    addi a1, a1, 1
    bne  a1, a2, rn1
    lw   a2, RV_NPORT(x0)
    li   a3, PTAB+4
    li   a1, 0
    beqz a2, rn4
rn3:
    lhu  t0, 0(a3)
    li   t1, 65535
    beq  t0, t1, rn3b
    li   t1, 0x3FFF
    and  t0, t0, t1
    A16  t1, NOFF, t0, t2
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
rn3b:
    addi a3, a3, 6
    addi a1, a1, 1
    bne  a1, a2, rn3
rn4:
    li   a1, 0
    li   a2, 0
rn5:
    A16  t0, NOFF, a1, t1
    lhu  t2, 0(t0)
    sh   a2, 0(t0)
    A16  t0, NFILL, a1, t1
    sh   a2, 0(t0)
    add  a2, a2, t2
    addi a1, a1, 1
    bne  a1, a5, rn5
    A16  t0, NOFF, a5, t1
    sh   a2, 0(t0)
    sw   a2, RV_NSINK(x0)
    slli a2, a0, 1
    li   a1, 0
rn6:
    A16  t0, SRC, a1, t1
    lhu  t0, 0(t0)
    li   t1, 65535
    beq  t0, t1, rn7
    li   t1, 0x3FFF
    and  t0, t0, t1
    A16  t1, NFILL, t0, t2
    lhu  t2, 0(t1)
    addi tp, t2, 1
    sh   tp, 0(t1)
    A16  t1, NSNK, t2, t0
    sh   a1, 0(t1)
rn7:
    addi a1, a1, 1
    bne  a1, a2, rn6
    lw   a2, RV_NPORT(x0)
    li   a3, PTAB+4
    li   a1, 0
    beqz a2, rn9
rn8:
    lhu  t0, 0(a3)
    li   t1, 65535
    beq  t0, t1, rn8b
    li   t1, 0x3FFF
    and  t0, t0, t1
    A16  t1, NFILL, t0, t2
    lhu  t2, 0(t1)
    addi tp, t2, 1
    sh   tp, 0(t1)
    A16  t1, NSNK, t2, t0
    li   t0, 0x8000
    add  t0, t0, a1
    sh   t0, 0(t1)
rn8b:
    addi a3, a3, 6
    addi a1, a1, 1
    bne  a1, a2, rn8
rn9:
    ret

// ---- zones and lanes
r1_zones:
    sw   ra, RV_T9(x0)
    lw   a0, V_N(x0)
    addi a5, a0, 16
    li   a1, 0
zi0:
    li   t0, ZONE
    add  t0, t0, a1
    sb   x0, 0(t0)
    li   t0, LIDX
    add  t0, t0, a1
    li   t1, 255
    sb   t1, 0(t0)
    addi a1, a1, 1
    bne  a1, a5, zi0
    li   a1, 0
zi1:
    slli t0, a1, 1
    li   t1, RLO
    add  t0, t0, t1
    li   t1, 65535
    sh   t1, 0(t0)
    addi a1, a1, 1
    li   t0, 32
    bne  a1, t0, zi1
    li   a1, 0
    sw   x0, RV_NLN(x0)
zn:
    sw   a1, RV_T0(x0)
    A16  t0, NOFF, a1, t1
    lhu  a2, 0(t0)
    lhu  a3, 2(t0)
    beq  a2, a3, znext
    li   tp, 255
    li   gp, 0
    li   s1, 0
    sw   a2, RV_T1(x0)
    sw   a3, RV_T2(x0)
    bltu a1, a0, zd1
    li   a4, R_ROWS-1
    lw   a5, RV_PBLR(x0)
    addi t0, a0, 8
    bltu a1, t0, zd2
    lw   a5, RV_PBLM(x0)
    j    zd2
zd1:
    li   t0, ROWA
    add  t0, t0, a1
    lbu  a4, 0(t0)
    A16  t0, COLA, a1, t1
    lhu  a5, 0(t0)
    slli t1, a5, 1
    add  a5, a5, t1
zd2:
    ZPIN
    lw   a2, RV_T1(x0)
zs:
    lw   a3, RV_T2(x0)
    beq  a2, a3, zsd
    A16  t0, NSNK, a2, t1
    lhu  t0, 0(t0)
    li   t1, 0x8000
    bgeu t0, t1, zport
    srli t0, t0, 1
    li   t1, ROWA
    add  t1, t1, t0
    lbu  a4, 0(t1)
    A16  t1, COLA, t0, t2
    lhu  a5, 0(t1)
    slli t1, a5, 1
    add  a5, a5, t1
    j    zsp
zport:
    sub  t0, t0, t1
    slli t1, t0, 2
    slli t0, t0, 1
    add  t0, t0, t1
    li   t1, PTAB
    add  t0, t0, t1
    lhu  t0, 0(t0)
    andi t0, t0, 255
    li   a4, R_ROWS-1
    lw   a5, RV_PBLR(x0)
    beqz t0, zsp
    lw   a5, RV_PBLA(x0)
    li   t1, 1
    beq  t0, t1, zsp
    lw   a5, RV_PBLM(x0)
zsp:
    ZPIN
    lw   a2, RV_T1(x0)
    addi a2, a2, 1
    sw   a2, RV_T1(x0)
    j    zs
zsd:
    lw   a1, RV_T0(x0)
    li   t0, CMIN
    add  t0, t0, a1
    sb   tp, 0(t0)
    li   t0, CMAX
    add  t0, t0, a1
    sb   gp, 0(t0)
    beq  tp, gp, zreset
// zone choice
    lw   t0, RV_NZ(x0)
    li   a2, 0
    li   a3, 2*3*R_ZONEW-3
    li   a5, -1
    li   s0, 0
zu:
    li   a4, 0
    li   tp, 0
zc:
    li   t0, RTCH
    add  t0, t0, tp
    lbu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, RLO
    add  t1, t1, t0
    lhu  t2, 0(t1)
    slli t2, t2, 1
    sub  t2, t2, a3
    li   t1, RHI
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    sub  t1, a3, t1
    bge  t2, t1, zk
    mv   t2, t1
zk:
    bge  x0, t2, zkn
    add  a4, a4, t2
zkn:
    addi tp, tp, 1
    bne  tp, s1, zc
    bgeu a4, a5, zb
    mv   a5, a4
    mv   s0, a2
zb:
    addi a2, a2, 1
    addi a3, a3, 2*3*R_ZONEW
    lw   t0, RV_NZ(x0)
    bne  a2, t0, zu
    lw   a1, RV_T0(x0)
    li   t0, ZONE
    add  t0, t0, a1
    sb   s0, 0(t0)
    lw   t1, RV_NLN(x0)
    A16  t0, LNET, t1, t2
    sh   a1, 0(t0)
    addi t1, t1, 1
    sw   t1, RV_NLN(x0)
zreset:
    li   tp, 0
    beqz s1, znext
zr:
    li   t0, RTCH
    add  t0, t0, tp
    lbu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, RLO
    add  t0, t0, t1
    li   t1, 65535
    sh   t1, 0(t0)
    addi tp, tp, 1
    bne  tp, s1, zr
znext:
    lw   a1, RV_T0(x0)
    addi a1, a1, 1
    lw   a0, V_N(x0)
    addi a5, a0, 16
    bne  a1, a5, zn
// ---- counting sort of the lane nets by (zone, cmin, cmax), stable in net order
    lw   t0, RV_NZ(x0)
    MUL22 a3, t0
    MUL22 a2, a3
    li   a1, 0
zbz:
    A16  t0, BCNT, a1, t1
    sh   x0, 0(t0)
    bgeu a1, a2, zbz2
    addi a1, a1, 1
    j    zbz
zbz2:
    lw   a3, RV_NLN(x0)
    li   a1, 0
    beqz a3, zbp
zb1:
    A16  t0, LNET, a1, t1
    lhu  t0, 0(t0)
    jal  gp, bucket
    addi t1, t1, 1
    A16  t0, BCNT, t1, t2
    lhu  t2, 0(t0)
    addi t2, t2, 1
    sh   t2, 0(t0)
    addi a1, a1, 1
    bne  a1, a3, zb1
zbp:
    li   a1, 0
    beqz a2, zbp2
zb2:
    A16  t0, BCNT, a1, t1
    lhu  t2, 0(t0)
    lhu  t1, 2(t0)
    add  t1, t1, t2
    sh   t1, 2(t0)
    addi a1, a1, 1
    bne  a1, a2, zb2
zbp2:
    lw   a3, RV_NLN(x0)
    li   a1, 0
    beqz a3, zlan
zb3:
    A16  t0, LNET, a1, t1
    lhu  t0, 0(t0)
    mv   a4, t0
    jal  gp, bucket
    A16  t0, BCNT, t1, t2
    lhu  t2, 0(t0)
    addi tp, t2, 1
    sh   tp, 0(t0)
    A16  t0, SORTED, t2, t1
    sh   a4, 0(t0)
    addi a1, a1, 1
    bne  a1, a3, zb3
// ---- lanes: first fit per zone in sorted order
zlan:
    li   a1, 0
zl0:
    li   t0, ZCNT
    add  t0, t0, a1
    sb   x0, 0(t0)
    addi a1, a1, 1
    li   t0, 16
    bne  a1, t0, zl0
    lw   a3, RV_NLN(x0)
    li   a1, 0
    beqz a3, zlend
zl1:
    A16  t0, SORTED, a1, t1
    lhu  a4, 0(t0)
    li   t0, ZONE
    add  t0, t0, a4
    lbu  a5, 0(t0)
    li   t0, CMIN
    add  t0, t0, a4
    lbu  s0, 0(t0)
    li   t0, CMAX
    add  t0, t0, a4
    lbu  s1, 0(t0)
    li   t0, ZCNT
    add  t0, t0, a5
    lbu  a2, 0(t0)
    slli tp, a5, 7
    li   t0, LEND
    add  tp, tp, t0
    li   t1, 0
zl2:
    beq  t1, a2, znew
    add  t0, tp, t1
    lbu  t2, 0(t0)
    bgeu t2, s0, zl2n
    sb   s1, 0(t0)
    li   t0, LIDX
    add  t0, t0, a4
    sb   t1, 0(t0)
    j    zl3
zl2n:
    addi t1, t1, 1
    j    zl2
znew:
    add  t0, tp, a2
    sb   s1, 0(t0)
    li   t0, LIDX
    add  t0, t0, a4
    sb   a2, 0(t0)
    li   t0, ZCNT
    add  t0, t0, a5
    addi a2, a2, 1
    sb   a2, 0(t0)
zl3:
    addi a1, a1, 1
    bne  a1, a3, zl1
zlend:
    lw   ra, RV_T9(x0)
    ret
// bucket: t0 = net -> t1 = (zone * R + cmin) * R + cmax   (uses t2; link gp)
bucket:
    li   t1, ZONE
    add  t1, t1, t0
    lbu  t1, 0(t1)
    MUL22 s0, t1
    li   t1, CMIN
    add  t1, t1, t0
    lbu  t1, 0(t1)
    add  s0, s0, t1
    MUL22 t1, s0
    li   s0, CMAX
    add  s0, s0, t0
    lbu  s0, 0(s0)
    add  t1, t1, s0
    jr   gp

// ---- physical x of the gate columns, lane zones and the parts
r1_xcols:
    lw   a0, RV_NZ(x0)
    li   a1, 0
    li   a2, 0
xz:
    beq  a1, a0, xz2
    li   t0, ZCNT
    add  t0, t0, a1
    lbu  t0, 0(t0)
    bnez t0, xz1
    li   t0, 1
xz1:
    li   t1, ZWT
    add  t1, t1, a1
    sb   t0, 0(t1)
    li   s0, 0
    addi t0, a1, 1
xzl:
    addi s0, s0, 3*R_ZONEW
    addi t0, t0, -1
    bnez t0, xzl
    add  s0, s0, a2
    slli t1, a1, 1
    li   t2, ZXB
    add  t1, t1, t2
    sh   s0, 0(t1)
    li   t0, ZWT
    add  t0, t0, a1
    lbu  t0, 0(t0)
    add  a2, a2, t0
    addi a1, a1, 1
    j    xz
xz2:
    lw   a3, RV_COLS(x0)
    li   a1, 0
    li   a2, 0
    li   a4, 0
    li   a5, R_ZONEW
    li   s0, 0
xg:
xgw:
    beq  a4, a0, xg2
    bltu a1, a5, xg2
    li   t0, ZWT
    add  t0, t0, a4
    lbu  t0, 0(t0)
    add  s0, s0, t0
    addi a4, a4, 1
    addi a5, a5, R_ZONEW
    j    xgw
xg2:
    slli t0, a1, 1
    add  t0, t0, a1
    add  t0, t0, s0
    A16  t1, GXT, a1, t2
    sh   t0, 0(t1)
    addi a1, a1, 1
    bne  a1, a3, xg
    addi t1, a3, -1
    A16  t0, GXT, t1, t2
    lhu  t0, 0(t0)
    addi t0, t0, 3+4                    // xs = Wg + 4 with Wg = gx(cols-1) + 3
    lw   t1, RV_ROMB(x0)
    add  t1, t1, t0
    addi t1, t1, 1
    sw   t1, RV_XR(x0)
    addi t0, t1, 11
    addi t1, t0, 6
    sw   t1, RV_XA(x0)
    addi t0, t1, 11
    lw   t1, RV_RAMB(x0)
    add  t1, t1, t0
    addi t1, t1, 10
    sw   t1, RV_XM(x0)
    addi t0, t1, 11
    sw   t0, RV_W(x0)
    ret
