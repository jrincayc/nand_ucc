// build_graph.s -- netlist -> weighted vertex graph (CSR), bit-exact with place_ref.build_graph.  Call: jal ra, build_graph.
// Inputs: V_N (gate count), V_NP (number of port reads of gates), SRC u16[2N] (source code of input 0 and 1 of every gate: gate n = n, ROM bit j = N+j,
// RAM-out bit c = N+8+c, 0xFFFF = open), PSRC u16[NP] (gate numbers read by ports).  Outputs: V_NV = N+1 (vertex N = anchor for ROM/ARM/RAM),
// OFF u16[NV+1], NBR u16[E], WT u16[E] (neighbours in first-insertion order).  V_ERR = 1 if the degree bound exceeds 20480, 2 if there are more than 512 port reads.

// srcof: a1 = k, a2 = p (0/1) -> t0 = SRC[2k+p]
.macro SRCOF
    slli t0, a1, 1
    add  t0, t0, a2
    slli t0, t0, 1
    li   t1, SRC
    add  t0, t0, t1
    lhu  t0, 0(t0)
.endm

build_graph:
    sw   ra, V_LINK(x0)
    li   t0, 60
    sb   t0, 0x80(x0)
    li   t0, 30
    sb   t0, 0x81(x0)
    li   t0, 20
    sb   t0, 0x82(x0)
    li   t0, 15
    sb   t0, 0x83(x0)
    li   t0, 12
    sb   t0, 0x84(x0)
    li   t0, 10
    sb   t0, 0x85(x0)
    li   t0, 8
    sb   t0, 0x86(x0)
    li   t0, 7
    sb   t0, 0x87(x0)
    li   t0, 6
    sb   t0, 0x88(x0)
    li   t0, 6
    sb   t0, 0x89(x0)
    li   t0, 5
    sb   t0, 0x8A(x0)
    sw   x0, V_ERR(x0)
    lw   t0, V_NP(x0)
    li   t1, 512
    bleu t0, t1, npok
    li   t0, 2
    sw   t0, V_ERR(x0)
    lw   ra, V_LINK(x0)
    ret
npok:
    lw   a0, V_N(x0)
    addi a5, a0, 16
    sw   a5, V_NN(x0)
// ---- init per-net: count = 1 (driver), LASTK = id for gates / 0xFFFF for ROM and RAM-out bits, ANCH = 0
    li   a1, 0
ginit:
    slli t0, a1, 1
    li   t1, POFF
    add  t1, t1, t0
    li   t2, 1
    sh   t2, 0(t1)
    li   t1, LASTK
    add  t1, t1, t0
    mv   t2, a1
    bltu a1, a0, gi1
    li   t2, -1
gi1:
    sh   t2, 0(t1)
    li   t1, ANCH
    add  t1, t1, a1
    sb   x0, 0(t1)
    addi a1, a1, 1
    bne  a1, a5, ginit
// ---- pass 1: count the sinks of every net (a gate reading the same net twice counts once)
    li   a1, 0
p1k:
    li   a2, 0
p1s:
    SRCOF
    li   t1, 65535
    beq  t0, t1, p1n
    slli t0, t0, 18                  // drop the late bits (bits 14-15)
    srli t0, t0, 18
    beq  t0, a1, p1n
    slli t1, t0, 1
    li   t2, LASTK
    add  t1, t1, t2
    lhu  t2, 0(t1)
    beq  t2, a1, p1n
    sh   a1, 0(t1)
    slli t1, t0, 1
    li   t2, POFF
    add  t1, t1, t2
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
p1n:
    addi a2, a2, 1
    li   t0, 2
    bne  a2, t0, p1s
    addi a1, a1, 1
    bne  a1, a0, p1k
    lw   a3, V_NP(x0)
    li   a1, 0
    beqz a3, p1pd
p1p:
    slli t0, a1, 1
    li   t1, PSRC
    add  t0, t0, t1
    lhu  t0, 0(t0)
    li   t1, ANCH
    add  t1, t1, t0
    lbu  t2, 0(t1)
    bnez t2, p1pn
    li   t2, 1
    sb   t2, 0(t1)
    slli t1, t0, 1
    li   t2, POFF
    add  t1, t1, t2
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
p1pn:
    addi a1, a1, 1
    bne  a1, a3, p1p
p1pd:
// ---- prefix sums: POFF[id] = start of the pin list, FP[id] = fill pointer
    li   a1, 0
    li   a2, 0
pre:
    slli t0, a1, 1
    li   t1, POFF
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sh   a2, 0(t1)
    li   t1, FP
    add  t1, t1, t0
    sh   a2, 0(t1)
    add  a2, a2, t2
    addi a1, a1, 1
    bne  a1, a5, pre
    slli t0, a5, 1
    li   t1, POFF
    add  t1, t1, t0
    sh   a2, 0(t1)
// ---- pass 2: drivers first, then sinks in ascending gate number, then the anchor for port reads
    li   a1, 0
g2:
    slli t0, a1, 1
    li   t1, LASTK
    add  t1, t1, t0
    mv   t2, a1
    mv   a4, a1
    bltu a1, a0, g2a
    li   t2, -1
    mv   a4, a0
g2a:
    sh   t2, 0(t1)
    li   t1, ANCH
    add  t1, t1, a1
    sb   x0, 0(t1)
    li   t1, FP
    add  t1, t1, t0
    lhu  t2, 0(t1)
    addi tp, t2, 1
    sh   tp, 0(t1)
    slli t2, t2, 1
    li   t1, PIN
    add  t1, t1, t2
    sh   a4, 0(t1)
    addi a1, a1, 1
    bne  a1, a5, g2
    li   a1, 0
p2k:
    li   a2, 0
p2s:
    SRCOF
    li   t1, 65535
    beq  t0, t1, p2n
    slli t0, t0, 18                  // drop the late bits (bits 14-15)
    srli t0, t0, 18
    beq  t0, a1, p2n
    slli t1, t0, 1
    li   t2, LASTK
    add  t1, t1, t2
    lhu  t2, 0(t1)
    beq  t2, a1, p2n
    sh   a1, 0(t1)
    slli t1, t0, 1
    li   t2, FP
    add  t1, t1, t2
    lhu  t2, 0(t1)
    addi tp, t2, 1
    sh   tp, 0(t1)
    slli t2, t2, 1
    li   t1, PIN
    add  t1, t1, t2
    sh   a1, 0(t1)
p2n:
    addi a2, a2, 1
    li   t0, 2
    bne  a2, t0, p2s
    addi a1, a1, 1
    bne  a1, a0, p2k
    lw   a3, V_NP(x0)
    li   a1, 0
    beqz a3, p2pd
p2p:
    slli t0, a1, 1
    li   t1, PSRC
    add  t0, t0, t1
    lhu  t0, 0(t0)
    li   t1, ANCH
    add  t1, t1, t0
    lbu  t2, 0(t1)
    bnez t2, p2pn
    li   t2, 1
    sb   t2, 0(t1)
    slli t1, t0, 1
    li   t2, FP
    add  t1, t1, t2
    lhu  t2, 0(t1)
    addi tp, t2, 1
    sh   tp, 0(t1)
    slli t2, t2, 1
    li   t1, PIN
    add  t1, t1, t2
    sh   a0, 0(t1)
p2pn:
    addi a1, a1, 1
    bne  a1, a3, p2p
p2pd:
// ---- degree upper bound per vertex (sum over nets of 2..12 pins of p-1), then segment starts
    addi a4, a0, 1
    sw   a4, V_NV(x0)
    li   a1, 0
sz:
    slli t0, a1, 1
    li   t1, SEG
    add  t1, t1, t0
    sh   x0, 0(t1)
    addi a1, a1, 1
    bne  a1, a4, sz
    li   a1, 0
ub:
    slli t0, a1, 1
    li   t1, POFF
    add  t1, t1, t0
    lhu  a2, 0(t1)
    lhu  a3, 2(t1)
    sub  a3, a3, a2
    li   t0, 2
    bltu a3, t0, ubn
    li   t0, 12
    bgtu a3, t0, ubn
    addi s0, a3, -1
    add  s1, a2, a3
ubp:
    slli t0, a2, 1
    li   t1, PIN
    add  t1, t1, t0
    lhu  t0, 0(t1)
    slli t0, t0, 1
    li   t1, SEG
    add  t1, t1, t0
    lhu  t2, 0(t1)
    add  t2, t2, s0
    sh   t2, 0(t1)
    addi a2, a2, 1
    bne  a2, s1, ubp
ubn:
    addi a1, a1, 1
    bne  a1, a5, ub
    li   a1, 0
    li   a2, 0
spn:
    slli t0, a1, 1
    li   t1, SEG
    add  t1, t1, t0
    lhu  t2, 0(t1)
    sh   a2, 0(t1)
    li   t1, LEN
    add  t1, t1, t0
    sh   x0, 0(t1)
    add  a2, a2, t2
    addi a1, a1, 1
    bne  a1, a4, spn
    slli t0, a4, 1
    li   t1, SEG
    add  t1, t1, t0
    sh   a2, 0(t1)
    li   t0, 20480
    bleu a2, t0, okub
    li   t0, 1
    sw   t0, V_ERR(x0)
    j    gdone
okub:
// ---- fill: for every net (id order) of 2..12 pins, for every ordered pair (a, b): weight += 60 // (p-1), neighbours in first-insertion order
    li   a1, 0
cn:
    lw   a5, V_NN(x0)
    slli t0, a1, 1
    li   t1, POFF
    add  t1, t1, t0
    lhu  a2, 0(t1)
    lhu  a3, 2(t1)
    sub  a3, a3, a2
    li   t0, 2
    bltu a3, t0, cnn
    li   t0, 12
    bgtu a3, t0, cnn
    li   t0, 0x7E
    add  t0, t0, a3
    lbu  s0, 0(t0)
    mv   a5, a2
    add  s1, a2, a3
    mv   a2, a5
cia:
    slli t0, a2, 1
    li   t1, PIN
    add  t1, t1, t0
    lhu  a3, 0(t1)
    mv   tp, a5
cib:
    beq  tp, a2, cibn
    slli t0, tp, 1
    li   t1, PIN
    add  t1, t1, t0
    lhu  a0, 0(t1)
    slli a4, a3, 1
    li   t1, SEG
    add  t1, t1, a4
    lhu  t0, 0(t1)
    li   t1, LEN
    add  t1, t1, a4
    lhu  t1, 0(t1)
    slli t0, t0, 1
    li   t2, NBR
    add  t0, t0, t2
    slli t1, t1, 1
    add  t1, t1, t0
sl:
    beq  t0, t1, nf
    lhu  t2, 0(t0)
    beq  t2, a0, fd
    addi t0, t0, 2
    j    sl
fd:
    li   t2, WTD
    add  t0, t0, t2
    lhu  t2, 0(t0)
    add  t2, t2, s0
    li   t1, 65535
    bleu t2, t1, fd1
    mv   t2, t1
fd1:
    sh   t2, 0(t0)
    j    cibn
nf:
    sh   a0, 0(t0)
    li   t2, WTD
    add  t0, t0, t2
    sh   s0, 0(t0)
    li   t1, LEN
    add  t1, t1, a4
    lhu  t2, 0(t1)
    addi t2, t2, 1
    sh   t2, 0(t1)
cibn:
    addi tp, tp, 1
    bne  tp, s1, cib
    addi a2, a2, 1
    bne  a2, s1, cia
cnn:
    lw   a0, V_N(x0)
    addi a1, a1, 1
    lw   a5, V_NN(x0)
    bne  a1, a5, cn
// ---- compaction into CSR (forward copy: the destination never passes the source)
    lw   a4, V_NV(x0)
    li   a1, 0
    li   a2, 0
cv:
    slli t0, a1, 1
    li   t1, SEG
    add  t1, t1, t0
    lhu  a3, 0(t1)
    li   t1, LEN
    add  t1, t1, t0
    lhu  a5, 0(t1)
    li   t1, OFF
    add  t1, t1, t0
    sh   a2, 0(t1)
    beqz a5, cvn
cc:
    slli t0, a3, 1
    li   t1, NBR
    add  t0, t0, t1
    lhu  t2, 0(t0)
    li   t1, WTD
    add  t0, t0, t1
    lhu  s0, 0(t0)
    slli t0, a2, 1
    li   t1, NBR
    add  t0, t0, t1
    sh   t2, 0(t0)
    li   t1, WTD
    add  t0, t0, t1
    sh   s0, 0(t0)
    addi a3, a3, 1
    addi a2, a2, 1
    addi a5, a5, -1
    bnez a5, cc
cvn:
    addi a1, a1, 1
    bne  a1, a4, cv
    slli t0, a4, 1
    li   t1, OFF
    add  t1, t1, t0
    sh   a2, 0(t1)
gdone:
    lw   ra, V_LINK(x0)
    ret
