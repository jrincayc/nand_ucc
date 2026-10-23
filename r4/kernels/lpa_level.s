// lpa_level.s -- one level of size-capped label propagation, bit-exact with place_ref.lpa_labels (shuffle, first-maximum rule, vertex sizes, u32 votes).
// Call: jal ra, lpa_level.  Inputs in RAM: V_NV (vertex count), V_CAP, V_RNG (xorshift32 state, updated), OFF u16[NV+1], NBR u16[E], WT u16[E], VSZ u16[NV].
// Outputs: LAB u16[NV] (label of every vertex = id of a vertex of its group), V_RNG.  Scratch: SIZE, ORD, TL, VOTES.

.equ SWEEPS, 15

lpa_level:
    sw   ra, V_LINK(x0)
    lw   a0, V_NV(x0)
    li   a1, 0
init:
    slli t0, a1, 1
    li   t1, LAB
    add  t1, t1, t0
    sh   a1, 0(t1)
    li   t1, ORD
    add  t1, t1, t0
    sh   a1, 0(t1)
    li   t1, VSZ
    add  t1, t1, t0
    lhu  t2, 0(t1)
    li   t1, SIZE
    add  t1, t1, t0
    sh   t2, 0(t1)
    slli t0, a1, 2
    li   t1, VOTES
    add  t1, t1, t0
    sw   x0, 0(t1)
    addi a1, a1, 1
    bne  a1, a0, init
    li   t0, SWEEPS
    sw   t0, V_SW(x0)
sweep:
    lw   a0, V_NV(x0)
    addi a1, a0, -1
shuf:
    beqz a1, shufdone
    addi a2, a1, 1
    jal  gp, below
    slli t0, a1, 1
    li   t1, ORD
    add  t0, t0, t1
    slli t1, a3, 1
    li   t2, ORD
    add  t1, t1, t2
    lhu  t2, 0(t0)
    lhu  a4, 0(t1)
    sh   a4, 0(t0)
    sh   t2, 0(t1)
    addi a1, a1, -1
    j    shuf
shufdone:
    sw   x0, V_MOVED(x0)
    li   a0, 0
vloop:
    lw   t0, V_NV(x0)
    beq  a0, t0, vend
    slli t0, a0, 1
    li   t1, ORD
    add  t1, t1, t0
    lhu  s1, 0(t1)
    slli t0, s1, 1
    li   t1, OFF
    add  t1, t1, t0
    lhu  a1, 0(t1)
    lhu  a2, 2(t1)
    li   a3, 0
    beq  a1, a2, vnext
eloop:
    slli t0, a1, 1
    li   t1, NBR
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   t2, LAB
    add  t1, t1, t2
    lhu  a4, 0(t1)
    li   t1, WT
    add  t1, t1, t0
    lhu  a5, 0(t1)
    slli t1, a4, 2
    li   t2, VOTES
    add  t1, t1, t2
    lw   t2, 0(t1)
    bnez t2, seen
    slli t0, a3, 1
    li   s0, TL
    add  s0, s0, t0
    sh   a4, 0(s0)
    addi a3, a3, 1
seen:
    add  t2, t2, a5
    sw   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a2, eloop
    li   s0, 0
    li   a1, 0
p1:
    slli t0, a1, 1
    li   t1, TL
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 2
    li   t2, VOTES
    add  t1, t1, t2
    lw   t2, 0(t1)
    bgeu s0, t2, lp1n
    mv   s0, t2
lp1n:
    addi a1, a1, 1
    bne  a1, a3, p1
    slli t0, s1, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  tp, 0(t1)
    slli t0, tp, 2
    li   t1, VOTES
    add  t1, t1, t0
    lw   t2, 0(t1)
    sltu a5, t2, s0
    li   a4, -1
    li   a1, 0
p2:
    slli t0, a1, 1
    li   t1, TL
    add  t1, t1, t0
    lhu  a2, 0(t1)
    slli t0, a2, 2
    li   t1, VOTES
    add  t1, t1, t0
    lw   t2, 0(t1)
    sw   x0, 0(t1)
    bne  t2, s0, lp2n
    bgez a4, lp2n
    slli t0, a2, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t0, s1, 1
    li   t2, VSZ
    add  t2, t2, t0
    lhu  t2, 0(t2)
    add  t1, t1, t2
    lw   t0, V_CAP(x0)
    bgtu t1, t0, lp2n
    mv   a4, a2
lp2n:
    addi a1, a1, 1
    bne  a1, a3, p2
    beqz a5, vnext
    bltz a4, vnext
    slli t0, s1, 1
    li   t2, VSZ
    add  t2, t2, t0
    lhu  a5, 0(t2)
    slli t0, tp, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sub  t2, t2, a5
    sh   t2, 0(t1)
    slli t0, a4, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t2, 0(t1)
    add  t2, t2, a5
    sh   t2, 0(t1)
    slli t0, s1, 1
    li   t1, LAB
    add  t1, t1, t0
    sh   a4, 0(t1)
    lw   t0, V_MOVED(x0)
    addi t0, t0, 1
    sw   t0, V_MOVED(x0)
vnext:
    addi a0, a0, 1
    j    vloop
vend:
    lw   t0, V_MOVED(x0)
    beqz t0, done
    lw   t0, V_SW(x0)
    addi t0, t0, -1
    sw   t0, V_SW(x0)
    bnez t0, sweep
done:
    lw   ra, V_LINK(x0)
    ret

// below: a2 = n (1..65535) -> a3 = uniform value in [0, n): next power of two minus one as a mask, bits 8.. of each xorshift32 draw, retry while >= n
below:
    addi t0, a2, -1
    srli t1, t0, 1
    or   t0, t0, t1
    srli t1, t0, 2
    or   t0, t0, t1
    srli t1, t0, 4
    or   t0, t0, t1
    srli t1, t0, 8
    or   t0, t0, t1
    lw   a3, V_RNG(x0)
bl:
    slli t1, a3, 13
    xor  a3, a3, t1
    srli t1, a3, 17
    xor  a3, a3, t1
    slli t1, a3, 5
    xor  a3, a3, t1
    srli t1, a3, 8
    and  t1, t1, t0
    bltu t1, a2, blok
    j    bl
blok:
    sw   a3, V_RNG(x0)
    mv   a3, t1
    jr   gp
