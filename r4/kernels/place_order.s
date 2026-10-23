// place_order.s -- the whole placement order (multilevel size-capped label propagation + greedy chaining), bit-exact with place_ref.order(nl, caps=(8,32,128,512), seed).
// Call after build_graph (OFF/NBR/WT/V_NV) with V_RNG = xorshift state of the seed: jal ra, place_order.
// Output: FINAL[0..N-1] = gate numbers in placement order (rank -> gate).  Uses lpa_level, chain.
.equ V_LINK2, 0xB8
.equ V_LEVELS, 0xBC      // number of levels (test hook; 0 = 4)
.equ SVTOP,   0x37000

place_order:
    sw   ra, V_LINK2(x0)
    lw   a0, V_NV(x0)
    li   a1, 0
pi0:
    slli t0, a1, 1
    li   t1, VSZ
    add  t1, t1, t0
    li   t2, 1
    sh   t2, 0(t1)
    li   t1, LHEAD
    add  t1, t1, t0
    sh   a1, 0(t1)
    li   t1, LTAIL
    add  t1, t1, t0
    sh   a1, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, pi0
    sw   x0, V_LV(x0)
levloop:
    lw   t0, V_LV(x0)
    slli t0, t0, 1
    li   t1, 8
    sll  t1, t1, t0
    sw   t1, V_CAP(x0)
    jal  ra, lpa_level
    jal  ra, contract
    lw   t0, V_LV(x0)
    addi t0, t0, 1
    sw   t0, V_LV(x0)
    lw   t1, V_LEVELS(x0)
    bnez t1, lvset
    li   t1, 4
lvset:
    bne  t0, t1, levloop
// ---- top level: chain over all remaining vertices, flatten the leaf lists
    lw   a0, V_NV(x0)
    li   a1, 0
sv0:
    slli t0, a1, 1
    li   t1, SVTOP
    add  t1, t1, t0
    sh   a1, 0(t1)
    li   t1, IDX
    add  t1, t1, t0
    li   t2, -1
    sh   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, sv0
    li   a0, SVTOP
    lw   a1, V_NV(x0)
    jal  gp, chain
    lw   a0, V_NV(x0)
    li   a1, 0
    li   a2, 0
fl:
    slli t0, a1, 1
    li   t1, COUT
    add  t0, t0, t1
    lhu  a3, 0(t0)
    slli t0, a3, 1
    li   t1, LHEAD
    add  t1, t1, t0
    lhu  a4, 0(t1)
    li   t1, LTAIL
    add  t1, t1, t0
    lhu  a5, 0(t1)
fl2:
    slli t0, a2, 1
    li   t1, FINAL
    add  t0, t0, t1
    sh   a4, 0(t0)
    addi a2, a2, 1
    beq  a4, a5, fl3
    slli t0, a4, 1
    li   t1, LNEXT
    add  t0, t0, t1
    lhu  a4, 0(t0)
    j    fl2
fl3:
    addi a1, a1, 1
    bne  a1, a0, fl
// anchor (gate number N) position; reverse the whole order if it lies in the first half
    lw   a3, V_N(x0)
    li   a1, 0
fa:
    slli t0, a1, 1
    li   t1, FINAL
    add  t0, t0, t1
    lhu  t0, 0(t0)
    beq  t0, a3, fa2
    addi a1, a1, 1
    j    fa
fa2:
    srli t0, a2, 1
    bgeu a1, t0, noflip
    li   a4, 0
    addi a5, a2, -1
rv:
    bgeu a4, a5, noflip
    slli t0, a4, 1
    li   t1, FINAL
    add  t0, t0, t1
    slli t2, a5, 1
    add  t2, t2, t1
    lhu  s0, 0(t0)
    lhu  s1, 0(t2)
    sh   s1, 0(t0)
    sh   s0, 0(t2)
    addi a4, a4, 1
    addi a5, a5, -1
    j    rv
noflip:
    li   a1, 0
    li   a4, 0
rm:
    slli t0, a1, 1
    li   t1, FINAL
    add  t0, t0, t1
    lhu  t2, 0(t0)
    beq  t2, a3, rm2
    slli t0, a4, 1
    add  t0, t0, t1
    sh   t2, 0(t0)
    addi a4, a4, 1
rm2:
    addi a1, a1, 1
    bne  a1, a2, rm
    lw   ra, V_LINK2(x0)
    ret

// contract: V_NV vertices with labels LAB -> groups (numbered by first appearance), chained inside, leaf lists joined, coarse graph in OFF/NBR/WT, V_NV = number of groups.
// Does nothing if every vertex is its own group.
contract:
    sw   ra, V_LINK(x0)
    lw   a0, V_NV(x0)
    li   a1, 0
gl0:
    slli t0, a1, 1
    li   t1, GIDL
    add  t1, t1, t0
    li   t2, -1
    sh   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, gl0
    li   a2, 0
    li   a1, 0
gl1:
    slli t0, a1, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   t2, GIDL
    add  t1, t1, t2
    lhu  t2, 0(t1)
    li   t0, 65535
    bne  t2, t0, gl2
    sh   a2, 0(t1)
    addi a2, a2, 1
gl2:
    addi a1, a1, 1
    bne  a1, a0, gl1
    sw   a2, V_NG(x0)
    bne  a2, a0, docon
    lw   ra, V_LINK(x0)
    ret
docon:
    li   a1, 0
gc0:
    slli t0, a1, 1
    li   t1, GCNT
    add  t1, t1, t0
    sh   x0, 0(t1)
    addi a1, a1, 1
    bgeu a2, a1, gc0
    li   a1, 0
gc1:
    slli t0, a1, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  t2, 0(t1)
    slli t2, t2, 1
    li   s0, GIDL
    add  t2, t2, s0
    lhu  t2, 0(t2)
    sh   t2, 0(t1)
    slli t2, t2, 1
    li   t1, GCNT
    add  t1, t1, t2
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, gc1
    li   a1, 0
ix:
    slli t0, a1, 1
    li   t1, IDX
    add  t1, t1, t0
    li   t2, -1
    sh   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, ix
    li   a1, 0
    li   a3, 0
gp0:
    slli t0, a1, 1
    li   t1, GCNT
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sh   a3, 0(t1)
    li   t1, TSEG
    add  t1, t1, t0
    sh   a3, 0(t1)
    add  a3, a3, t2
    addi a1, a1, 1
    bne  a1, a2, gp0
    slli t0, a2, 1
    li   t1, GCNT
    add  t1, t1, t0
    sh   a3, 0(t1)
    li   a1, 0
gm:
    slli t0, a1, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  t2, 0(t1)
    slli t2, t2, 1
    li   t1, TSEG
    add  t1, t1, t2
    lhu  s0, 0(t1)
    addi s1, s0, 1
    sh   s1, 0(t1)
    slli s0, s0, 1
    li   t1, MEM
    add  s0, s0, t1
    sh   a1, 0(s0)
    addi a1, a1, 1
    bne  a1, a0, gm
// ---- chain the members of every group, join their leaf lists in that order
    li   a1, 0
gch:
    sw   a1, V_T1(x0)
    slli t0, a1, 1
    li   t1, GCNT
    add  t1, t1, t0
    lhu  a3, 0(t1)
    lhu  a4, 2(t1)
    sub  a1, a4, a3
    slli a0, a3, 1
    li   t1, MEM
    add  a0, a0, t1
    sw   a3, V_T2(x0)
    sw   a1, V_T3(x0)
    jal  gp, chain
    lw   a3, V_T2(x0)
    lw   a4, V_T3(x0)
    li   a2, 0
    li   s0, 0
    li   s1, 0
    li   tp, 0
rp:
    slli t0, a2, 1
    li   t1, COUT
    add  t0, t0, t1
    lhu  t0, 0(t0)
    add  t0, t0, a3
    slli t0, t0, 1
    li   t1, MEM
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, VSZ
    add  t1, t1, t0
    lhu  t2, 0(t1)
    add  s0, s0, t2
    li   t1, LHEAD
    add  t1, t1, t0
    lhu  t2, 0(t1)
    li   t1, LTAIL
    add  t1, t1, t0
    lhu  a0, 0(t1)
    bnez a2, rp1
    mv   s1, t2
    j    rp2
rp1:
    slli t1, tp, 1
    li   a5, LNEXT
    add  t1, t1, a5
    sh   t2, 0(t1)
rp2:
    mv   tp, a0
    addi a2, a2, 1
    bne  a2, a4, rp
    lw   a1, V_T1(x0)
    slli t0, a1, 1
    li   t1, LHEAD
    add  t1, t1, t0
    sh   s1, 0(t1)
    li   t1, LTAIL
    add  t1, t1, t0
    sh   tp, 0(t1)
    li   t1, VSZ
    add  t1, t1, t0
    sh   s0, 0(t1)
    addi a1, a1, 1
    lw   a2, V_NG(x0)
    bne  a1, a2, gch
// ---- coarse graph
    lw   a0, V_NV(x0)
    lw   a2, V_NG(x0)
    li   a1, 0
tz:
    slli t0, a1, 1
    li   t1, TSEG
    add  t1, t1, t0
    sh   x0, 0(t1)
    addi a1, a1, 1
    bne  a1, a2, tz
    li   a1, 0
ub1:
    slli t0, a1, 1
    li   t1, OFF
    add  t1, t1, t0
    lhu  t2, 0(t1)
    lhu  t1, 2(t1)
    sub  t2, t1, t2
    li   t1, LAB
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   s0, TSEG
    add  t1, t1, s0
    lhu  s0, 0(t1)
    add  s0, s0, t2
    sh   s0, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, ub1
    li   a1, 0
    li   a3, 0
ub2:
    slli t0, a1, 1
    li   t1, TSEG
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sh   a3, 0(t1)
    li   t1, TLEN
    add  t1, t1, t0
    sh   x0, 0(t1)
    add  a3, a3, t2
    addi a1, a1, 1
    bne  a1, a2, ub2
    slli t0, a2, 1
    li   t1, TSEG
    add  t1, t1, t0
    sh   a3, 0(t1)
    li   a1, 0
nf1:
    slli t0, a1, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  a3, 0(t1)
    li   t1, OFF
    add  t1, t1, t0
    lhu  a4, 0(t1)
    lhu  a5, 2(t1)
    beq  a4, a5, nf5
nf2:
    slli t0, a4, 1
    li   t1, NBR
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   t2, LAB
    add  t1, t1, t2
    lhu  s0, 0(t1)
    beq  s0, a3, nf4
    li   t1, WT
    add  t1, t1, t0
    lhu  s1, 0(t1)
    slli t0, a3, 1
    li   t1, TSEG
    add  t1, t1, t0
    lhu  tp, 0(t1)
    li   t1, TLEN
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli tp, tp, 1
    li   t2, TNBR
    add  tp, tp, t2
    slli t1, t1, 1
    add  t1, t1, tp
nf3:
    beq  tp, t1, nfnew
    lhu  t2, 0(tp)
    beq  t2, s0, nffound
    addi tp, tp, 2
    j    nf3
nffound:
    li   t2, WTD
    add  tp, tp, t2
    lhu  t2, 0(tp)
    add  t2, t2, s1
    li   t1, 65535
    bleu t2, t1, nff2
    mv   t2, t1
nff2:
    sh   t2, 0(tp)
    j    nf4
nfnew:
    sh   s0, 0(tp)
    li   t2, WTD
    add  tp, tp, t2
    sh   s1, 0(tp)
    slli t0, a3, 1
    li   t1, TLEN
    add  t1, t1, t0
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
nf4:
    addi a4, a4, 1
    bne  a4, a5, nf2
nf5:
    addi a1, a1, 1
    bne  a1, a0, nf1
    li   a1, 0
    li   a3, 0
cg:
    slli t0, a1, 1
    li   t1, TSEG
    add  t1, t1, t0
    lhu  a4, 0(t1)
    li   t1, TLEN
    add  t1, t1, t0
    lhu  a5, 0(t1)
    li   t1, OFF
    add  t1, t1, t0
    sh   a3, 0(t1)
    beqz a5, cgn
cg2:
    slli t0, a4, 1
    li   t1, TNBR
    add  t0, t0, t1
    lhu  t2, 0(t0)
    li   t1, WTD
    add  t0, t0, t1
    lhu  s0, 0(t0)
    slli t0, a3, 1
    li   t1, NBR
    add  t0, t0, t1
    sh   t2, 0(t0)
    li   t1, WTD
    add  t0, t0, t1
    sh   s0, 0(t0)
    addi a4, a4, 1
    addi a3, a3, 1
    addi a5, a5, -1
    bnez a5, cg2
cgn:
    addi a1, a1, 1
    bne  a1, a2, cg
    slli t0, a2, 1
    li   t1, OFF
    add  t1, t1, t0
    sh   a3, 0(t1)
    sw   a2, V_NV(x0)
    lw   ra, V_LINK(x0)
    ret
