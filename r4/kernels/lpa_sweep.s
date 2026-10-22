// lpa_sweep.s -- calibration kernel: size-capped label propagation sweeps over a CSR graph in RAM (RV32EC).  Not the final in-world program;
// it measures the instruction cost per neighbour visit / per vertex.  Fixed vertex order (no shuffle), first-max tie rule.
// RAM: OFF u16[N+1], NBR u16[E], WT u8[E], LAB u16[N], VOTES u16[N], SIZE u16[N], TL u16[maxdeg]; sweep counter at RAM[0x50].
.equ OFF,   0x1000
.equ LAB,   0x3000
.equ VOTES, 0x5000
.equ SIZE,  0x7000
.equ TL,    0x9000
.equ NBR,   0xB000
.equ WT,    0x14000
.equ NV,    3770
.equ CAP,   480
.equ SWEEPS, 4
start:
    li   t0, SWEEPS
    sb   t0, 0x50(x0)
sweep:
    li   a0, 0
vloop:
    li   t0, NV
    beq  a0, t0, vend
    slli t0, a0, 1
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
    add  t1, t1, a1
    lbu  a5, 0(t1)
    slli t1, a4, 1
    li   t2, VOTES
    add  t1, t1, t2
    lhu  t2, 0(t1)
    bnez t2, seen
    slli t0, a3, 1
    li   s0, TL
    add  s0, s0, t0
    sh   a4, 0(s0)
    addi a3, a3, 1
seen:
    add  t2, t2, a5
    sh   t2, 0(t1)
    addi a1, a1, 1
    bne  a1, a2, eloop
    li   s0, 0
    li   a1, 0
p1:
    slli t0, a1, 1
    li   t1, TL
    add  t1, t1, t0
    lhu  t1, 0(t1)
    slli t1, t1, 1
    li   t2, VOTES
    add  t1, t1, t2
    lhu  t2, 0(t1)
    bgeu s0, t2, p1n
    mv   s0, t2
p1n:
    addi a1, a1, 1
    bne  a1, a3, p1
    slli t0, a0, 1
    li   t1, LAB
    add  t1, t1, t0
    lhu  s1, 0(t1)
    slli t0, s1, 1
    li   t1, VOTES
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sltu a5, t2, s0
    li   a4, -1
    li   a1, 0
p2:
    slli t0, a1, 1
    li   t1, TL
    add  t1, t1, t0
    lhu  a2, 0(t1)
    slli t0, a2, 1
    li   t1, VOTES
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sh   x0, 0(t1)
    bne  t2, s0, p2n
    bgez a4, p2n
    slli t0, a2, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t1, 0(t1)
    li   t0, CAP
    bgeu t1, t0, p2n
    mv   a4, a2
p2n:
    addi a1, a1, 1
    bne  a1, a3, p2
    beqz a5, vnext
    bltz a4, vnext
    slli t0, s1, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t2, 0(t1)
    addi t2, t2, -1
    sh   t2, 0(t1)
    slli t0, a4, 1
    li   t1, SIZE
    add  t1, t1, t0
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
    slli t0, a0, 1
    li   t1, LAB
    add  t1, t1, t0
    sh   a4, 0(t1)
vnext:
    addi a0, a0, 1
    j    vloop
vend:
    lbu  t0, 0x50(x0)
    addi t0, t0, -1
    sb   t0, 0x50(x0)
    bnez t0, sweep
halt:
    j    halt
