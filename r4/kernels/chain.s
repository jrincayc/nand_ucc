// chain.s -- greedy chaining of singleton items, bit-exact with place_ref.chain([[x] for x in S], adj).
// Call: a0 = address of u16 SV[m] (the vertices of S, in the order of the items), a1 = m, link register gp (jal gp, chain).
// Needs IDX[v] = 0xFFFF for every vertex on entry (restored on exit).  Output: COUT[0..m-1] = item numbers (positions in SV) in chain order.
// Start with the item whose weight to the other items is largest (first maximum); then repeatedly the unvisited item with the largest score
// 6*w(last) + 3*w(second last) + 2*w(third last) among items adjacent to the last three (first maximum by item number), else the lowest unvisited item.
chain:
    sw   a0, V_SV(x0)
    sw   a1, V_M(x0)
    sw   x0, V_T0(x0)
    li   t0, 1
    bgtu a1, t0, cmain
    beqz a1, cret
    li   t1, COUT
    sh   x0, 0(t1)
cret:
    jr   gp
cmain:
    li   a2, 0
c1:
    slli t0, a2, 1
    add  t1, a0, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   t2, IDX
    add  t1, t1, t2
    sh   a2, 0(t1)
    li   t1, CVIS
    add  t1, t1, a2
    sb   x0, 0(t1)
    slli t0, a2, 2
    li   t1, CSC
    add  t1, t1, t0
    sw   x0, 0(t1)
    li   t1, CTOT
    add  t1, t1, t0
    sw   x0, 0(t1)
    addi a2, a2, 1
    bne  a2, a1, c1
// total weight to the other items of every item
    li   a2, 0
c2:
    slli t0, a2, 1
    add  t0, t0, a0
    lhu  a3, 0(t0)
    slli t0, a3, 1
    li   t1, OFF
    add  t0, t0, t1
    lhu  a4, 0(t0)
    lhu  a5, 2(t0)
    li   s0, 0
    beq  a4, a5, c2s
c2e:
    slli t0, a4, 1
    li   t1, NBR
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, IDX
    add  t0, t0, t1
    lhu  t0, 0(t0)
    li   t1, 65535
    beq  t0, t1, c2n
    beq  t0, a2, c2n
    slli t0, a4, 1
    li   t1, WT
    add  t0, t0, t1
    lhu  t0, 0(t0)
    add  s0, s0, t0
c2n:
    addi a4, a4, 1
    bne  a4, a5, c2e
c2s:
    slli t0, a2, 2
    li   t1, CTOT
    add  t1, t1, t0
    sw   s0, 0(t1)
    addi a2, a2, 1
    bne  a2, a1, c2
// first maximum
    li   a2, 0
    li   s0, 0
    li   a3, 0
c3:
    slli t0, a2, 2
    li   t1, CTOT
    add  t1, t1, t0
    lw   t2, 0(t1)
    bgeu s0, t2, c3n
    mv   s0, t2
    mv   a3, a2
c3n:
    addi a2, a2, 1
    bne  a2, a1, c3
    li   t1, COUT
    sh   a3, 0(t1)
    li   t1, CVIS
    add  t1, t1, a3
    li   t2, 1
    sb   t2, 0(t1)
    li   a2, 1
cloop:
    beq  a2, a1, cdone
    li   tp, 0
    li   a3, 0
ck:
    sub  t0, a2, a3
    addi t0, t0, -1
    slli t0, t0, 1
    li   t1, COUT
    add  t0, t0, t1
    lhu  a4, 0(t0)
    lw   t0, V_SV(x0)
    slli t1, a4, 1
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, OFF
    add  t0, t0, t1
    lhu  a5, 0(t0)
    lhu  s0, 2(t0)
    beq  a5, s0, cknext
ce:
    slli t0, a5, 1
    li   t1, NBR
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, IDX
    add  t0, t0, t1
    lhu  t0, 0(t0)
    li   t1, 65535
    beq  t0, t1, cen
    beq  t0, a4, cen
    li   t1, CVIS
    add  t1, t1, t0
    lbu  t1, 0(t1)
    bnez t1, cen
    slli t1, a5, 1
    li   t2, WT
    add  t1, t1, t2
    lhu  t1, 0(t1)
    slli t2, t1, 1
    beqz a3, m6
    li   a0, 1
    beq  a3, a0, m3
    mv   t1, t2
    j    mdone
m3:
    add  t1, t1, t2
    j    mdone
m6:
    slli t1, t1, 2
    add  t1, t1, t2
mdone:
    slli t2, t0, 2
    li   s1, CSC
    add  t2, t2, s1
    lw   a0, 0(t2)
    bnez a0, cadd
    slli s1, tp, 1
    li   a0, CTL
    add  s1, s1, a0
    sh   t0, 0(s1)
    addi tp, tp, 1
    li   a0, 0
cadd:
    add  a0, a0, t1
    sw   a0, 0(t2)
cen:
    addi a5, a5, 1
    bne  a5, s0, ce
cknext:
    addi a3, a3, 1
    li   t0, 3
    beq  a3, t0, cpick
    bne  a3, a2, ck
cpick:
    beqz tp, cfall
    li   a5, 0
    li   s0, 0
    li   a3, -1
cp:
    slli t0, a5, 1
    li   t1, CTL
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t1, t0, 2
    li   t2, CSC
    add  t1, t1, t2
    lw   t2, 0(t1)
    sw   x0, 0(t1)
    bltu s0, t2, cpb
    bne  t2, s0, cpn
    bgeu t0, a3, cpn
cpb:
    mv   s0, t2
    mv   a3, t0
cpn:
    addi a5, a5, 1
    bne  a5, tp, cp
    mv   a4, a3
    j    cput
cfall:
    lw   a3, V_T0(x0)
cf:
    li   t1, CVIS
    add  t1, t1, a3
    lbu  t1, 0(t1)
    beqz t1, cfound
    addi a3, a3, 1
    j    cf
cfound:
    sw   a3, V_T0(x0)
    mv   a4, a3
cput:
    slli t0, a2, 1
    li   t1, COUT
    add  t0, t0, t1
    sh   a4, 0(t0)
    li   t1, CVIS
    add  t1, t1, a4
    li   t2, 1
    sb   t2, 0(t1)
    addi a2, a2, 1
    j    cloop
cdone:
    li   a2, 0
cr:
    lw   t0, V_SV(x0)
    slli t1, a2, 1
    add  t0, t0, t1
    lhu  t0, 0(t0)
    slli t0, t0, 1
    li   t1, IDX
    add  t0, t0, t1
    li   t2, -1
    sh   t2, 0(t0)
    addi a2, a2, 1
    lw   t0, V_M(x0)
    bne  a2, t0, cr
    jr   gp
