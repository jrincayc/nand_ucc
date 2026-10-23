// hdflat.s -- module table from the HD data, module improvement, flatten into the packed netlist (SRC, KINDA, PTAB, V_N, V_NP, PSRC).
// Needs hd_data.s (hd2bin.py), memmap.s, memmap_route.s, memmap_imp.s, memmap_hd.s, improve.s.  sp = SWTOP.
mt_load:
    PUSHRA
    li   s0, 0
ml0:
    li   t0, HD_NMODS
    beq  s0, t0, ml_done
    li   a1, hd_modoff
    slli t0, s0, 1
    add  a1, a1, t0
    lhu  a1, 0(a1)
    li   t0, hd_mods
    add  a1, a1, t0
    slli a2, s0, 7
    slli t0, s0, 6
    add  a2, a2, t0
    li   t0, MT
    add  a2, a2, t0
    lbu  t0, 1(a1)
    sb   t0, 0(a2)
    lbu  t1, 2(a1)
    sb   t1, 1(a2)
    lbu  a3, 3(a1)
    sb   a3, 2(a2)
    addi a1, a1, 4
    li   a4, 0
ml1:
    bgeu a4, a3, ml3
    lbu  t0, 0(a1)
    bnez t0, ml2
    lbu  t1, 1(a1)
    lbu  t2, 2(a1)
    add  t0, a2, a4
    sb   t1, 8(t0)
    sb   t2, 64(t0)
    addi a4, a4, 1
    j    ml1n
ml2:
    lbu  t1, 1(a1)
    li   t2, 0xFF
ml2a:
    beqz t1, ml1n
    add  t0, a2, a4
    sb   t2, 8(t0)
    sb   t2, 64(t0)
    addi a4, a4, 1
    addi t1, t1, -1
    j    ml2a
ml1n:
    addi a1, a1, 3
    j    ml1
ml3:
    lbu  t0, 0(a1)
    sb   t0, 4(a2)
    lbu  t1, 1(a2)
    li   t2, 2
    bne  t1, t2, ml4
    lbu  t0, 1(a1)
    sb   t0, 5(a2)
ml4:
    mv   a0, s0
    sw   s0, FV_M(x0)
    jal  ra, mt_derive
    lw   s0, FV_M(x0)
    addi s0, s0, 1
    j    ml0
ml_done:
    POPRA
    ret

// mt_derive: a0 = module -> RK, n_nodes, output node offsets
mt_derive:
    slli a2, a0, 7
    slli t0, a0, 6
    add  a2, a2, t0
    li   t0, MT
    add  a2, a2, t0
    lbu  a3, 2(a2)
    lbu  a4, 0(a2)
    li   a1, 0
    li   a5, 0
md1:
    bgeu a5, a3, md2
    add  t0, a2, a5
    sb   a1, 120(t0)
    lbu  t1, 8(t0)
    li   t2, 0xFF
    beq  t1, t2, md1n
    addi a1, a1, 1
md1n:
    addi a5, a5, 1
    j    md1
md2:
    sb   a1, 3(a2)
    lbu  a5, 1(a2)
    li   a1, 0
md3:
    beq  a1, a5, md4
    add  t0, a2, a1
    lbu  t1, 4(t0)
    sub  t1, t1, a4
    add  t1, t1, a2
    lbu  t1, 120(t1)
    sb   t1, 6(t0)
    addi a1, a1, 1
    j    md3
md4:
    ret

// mt_improve_all: improve every module that qualifies (n_in <= 3, n_out <= 2, slots <= 26)
mt_improve_all:
    PUSHRA
    li   s0, 0
mi0:
    li   t0, HD_NMODS
    beq  s0, t0, mi_done
    sw   s0, FV_M(x0)
    slli a2, s0, 7
    slli t0, s0, 6
    add  a2, a2, t0
    li   t0, MT
    add  a2, a2, t0
    lbu  a3, 2(a2)
    li   t0, 26
    bgtu a3, t0, mi_next
    lbu  a4, 0(a2)
    li   t0, 3
    bgtu a4, t0, mi_next
    lbu  a5, 1(a2)
    li   t0, 2
    bgtu a5, t0, mi_next
    sw   a4, IM_NIN(x0)
    sw   a5, IM_NO(x0)
    sw   a3, IM_S(x0)
    li   a1, 0
mi1:
    bgeu a1, a3, mi2
    add  t0, a2, a1
    lbu  t1, 8(t0)
    lbu  t2, 64(t0)
    li   gp, SLA
    add  gp, gp, a1
    sb   t1, 0(gp)
    li   gp, SLB
    add  gp, gp, a1
    sb   t2, 0(gp)
    addi a1, a1, 1
    j    mi1
mi2:
    lbu  t0, 4(a2)
    li   gp, SOUT
    sb   t0, 0(gp)
    lbu  t0, 5(a2)
    sb   t0, 1(gp)
    jal  ra, imp_record
    lw   t0, IM_RES(x0)
    beqz t0, mi_next
    lw   s0, FV_M(x0)
    slli a2, s0, 7
    slli t0, s0, 6
    add  a2, a2, t0
    li   t0, MT
    add  a2, a2, t0
    lw   a3, IM_S(x0)
    li   a1, 0
mi3:
    bgeu a1, a3, mi4
    li   gp, RNA
    add  gp, gp, a1
    lbu  t1, 0(gp)
    li   gp, RNB
    add  gp, gp, a1
    lbu  t2, 0(gp)
    add  t0, a2, a1
    sb   t1, 8(t0)
    sb   t2, 64(t0)
    addi a1, a1, 1
    j    mi3
mi4:
    li   gp, ROUT
    lbu  t0, 0(gp)
    sb   t0, 4(a2)
    lbu  t0, 1(gp)
    sb   t0, 5(a2)
    mv   a0, s0
    jal  ra, mt_derive
mi_next:
    lw   s0, FV_M(x0)
    addi s0, s0, 1
    j    mi0
mi_done:
    POPRA
    ret

// mt_encode: a0 = module, a1 = destination -> record in the HD format (a0 = length)
mt_encode:
    slli a2, a0, 7
    slli t0, a0, 6
    add  a2, a2, t0
    li   t0, MT
    add  a2, a2, t0
    li   t0, 1
    sb   t0, 0(a1)
    lbu  t0, 0(a2)
    sb   t0, 1(a1)
    lbu  a4, 1(a2)
    sb   a4, 2(a1)
    lbu  a3, 2(a2)
    sb   a3, 3(a1)
    addi a0, a1, 4                    // write pointer
    li   a5, 0                        // slot
    li   t2, 0                        // pending hole run
me1:
    bgeu a5, a3, me4
    add  t0, a2, a5
    lbu  t1, 8(t0)
    li   gp, 0xFF
    bne  t1, gp, me2
    addi t2, t2, 1
    addi a5, a5, 1
    j    me1
me2:
    beqz t2, me3
    li   gp, 2
    sb   gp, 0(a0)
    sb   t2, 1(a0)
    sb   x0, 2(a0)
    addi a0, a0, 3
    li   t2, 0
me3:
    sb   x0, 0(a0)
    sb   t1, 1(a0)
    lbu  t1, 64(t0)
    sb   t1, 2(a0)
    addi a0, a0, 3
    addi a5, a5, 1
    j    me1
me4:
    beqz t2, me5
    li   gp, 2
    sb   gp, 0(a0)
    sb   t2, 1(a0)
    sb   x0, 2(a0)
    addi a0, a0, 3
me5:
    lbu  t0, 4(a2)
    sb   t0, 0(a0)
    addi a0, a0, 1
    li   t1, 2
    bne  a4, t1, me6
    lbu  t0, 5(a2)
    sb   t0, 0(a0)
    addi a0, a0, 1
me6:
    sub  a0, a0, a1
    ret

// fl_res: a0 = HD reference -> a0 = net id | late << 14   (link gp; clobbers a1, t0-t2)
fl_res:
    li   t0, 0x4000
    bgeu a0, t0, flr_sp
    srli a1, a0, 12
    li   t0, 0xFFF
    and  a0, a0, t0
    li   t0, BTYP
    add  t0, t0, a0
    lbu  t2, 0(t0)
    slli t0, a0, 1
    li   t1, NBASE
    add  t0, t0, t1
    lhu  a0, 0(t0)
    li   t0, 2
    bltu t2, t0, flr_ret
    addi t2, t2, -2
    slli t0, t2, 7
    slli t1, t2, 6
    add  t0, t0, t1
    li   t1, MT
    add  t0, t0, t1
    add  t0, t0, a1
    lbu  t0, 6(t0)
    add  a0, a0, t0
flr_ret:
    jr   gp
flr_sp:
    li   t1, 0x4010
    beq  a0, t1, flr_run
    li   t1, 0x4008
    bgeu a0, t1, flr_ram
    li   t0, 0x4000
    sub  a0, a0, t0
    lw   t0, V_N(x0)
    add  a0, a0, t0
    jr   gp
flr_ram:
    li   t0, 0x4008
    sub  a0, a0, t0
    lw   t0, V_N(x0)
    add  a0, a0, t0
    addi a0, a0, 8
    jr   gp
flr_run:
    lw   a0, V_N(x0)
    addi a0, a0, -1
    li   t0, 2 << 14
    add  a0, a0, t0
    jr   gp

// fl_sig: t1 = module signal, a3 = module block, a5 = base node -> a1 = net id   (link gp)
fl_sig:
    lbu  t0, 0(a3)
    bgeu t1, t0, fs_g
    slli t1, t1, 2
    li   t2, FV_IR
    add  t1, t1, t2
    lw   a1, 0(t1)
    jr   gp
fs_g:
    sub  t1, t1, t0
    add  t2, a3, t1
    lbu  t2, 120(t2)
    add  a1, a5, t2
    jr   gp

flatten:
    PUSHRA
    li   s0, 0
    li   a4, hd_body
    li   a5, 0
f1:
    li   t0, HD_NBODY
    beq  s0, t0, f1d
    lbu  t2, 0(a4)
    li   t0, BTYP
    add  t0, t0, s0
    sb   t2, 0(t0)
    slli t0, s0, 1
    li   t1, NBASE
    add  t0, t0, t1
    sh   a5, 0(t0)
    li   a0, 1
    li   a1, 1
    beqz t2, f1c
    li   a1, 2
    li   t0, 1
    beq  t2, t0, f1c
    addi t2, t2, -2
    slli t0, t2, 7
    slli t1, t2, 6
    add  t0, t0, t1
    li   t1, MT
    add  t0, t0, t1
    lbu  a0, 3(t0)
    lbu  a1, 0(t0)
f1c:
    add  a5, a5, a0
    slli t0, a1, 1
    add  a4, a4, t0
    addi a4, a4, 1
    addi s0, s0, 1
    j    f1
f1d:
    addi t0, a5, 1
    sw   t0, V_N(x0)
    // ---- pass 2
    li   s0, 0
    li   a4, hd_body
f2:
    li   t0, HD_NBODY
    beq  s0, t0, f2d
    lbu  t2, 0(a4)
    addi a4, a4, 1
    sw   t2, FV_TYPE(x0)
    slli t0, s0, 1
    li   t1, NBASE
    add  t0, t0, t1
    lhu  a5, 0(t0)
    li   a2, 1
    beqz t2, f2n
    li   a2, 2
    li   t0, 1
    beq  t2, t0, f2n
    addi t0, t2, -2
    slli a3, t0, 7
    slli t1, t0, 6
    add  a3, a3, t1
    li   t1, MT
    add  a3, a3, t1
    lbu  a2, 0(a3)
f2n:
    sw   a2, FV_NR(x0)
    li   s1, 0
f2r:
    lw   t0, FV_NR(x0)
    beq  s1, t0, f2e
    lhu  a0, 0(a4)
    addi a4, a4, 2
    jal  gp, fl_res
    slli t0, s1, 2
    li   t1, FV_IR
    add  t0, t0, t1
    sw   a0, 0(t0)
    addi s1, s1, 1
    j    f2r
f2e:
    lw   t2, FV_TYPE(x0)
    li   t0, 2
    bgeu t2, t0, f2m
    slli t0, a5, 2
    li   t1, SRC
    add  t0, t0, t1
    lw   a0, FV_IR(x0)
    sh   a0, 0(t0)
    li   a1, 0xFFFF
    sh   a1, 2(t0)
    li   a2, 0
    beqz t2, f2k
    lw   a1, FV_IR+4(x0)
    sh   a1, 2(t0)
    j    f2k0
f2k:
    li   a2, 1
f2k0:
    li   t0, KINDA
    add  t0, t0, a5
    sb   a2, 0(t0)
    j    f2n2
f2m:
    addi t0, t2, -2
    slli a3, t0, 7
    slli t1, t0, 6
    add  a3, a3, t1
    li   t1, MT
    add  a3, a3, t1
    li   s1, 0
f2s:
    lbu  a2, 2(a3)
    bgeu s1, a2, f2n2
    add  t0, a3, s1
    lbu  t1, 8(t0)
    li   t2, 0xFF
    beq  t1, t2, f2sn
    lbu  t2, 120(t0)
    add  t2, t2, a5
    li   t0, KINDA
    add  t0, t0, t2
    sb   x0, 0(t0)
    slli t2, t2, 2
    li   a0, SRC
    add  a0, a0, t2
    jal  gp, fl_sig
    sh   a1, 0(a0)
    add  t0, a3, s1
    lbu  t1, 64(t0)
    jal  gp, fl_sig
    sh   a1, 2(a0)
f2sn:
    addi s1, s1, 1
    j    f2s
f2n2:
    addi s0, s0, 1
    j    f2
f2d:
    // tie node
    lw   t0, V_N(x0)
    addi t0, t0, -1
    li   t1, KINDA
    add  t1, t1, t0
    sb   x0, 0(t1)
    slli t0, t0, 2
    li   t1, SRC
    add  t0, t0, t1
    li   t1, 0xFFFF
    sh   t1, 0(t0)
    sh   t1, 2(t0)
    // ports
    li   s0, 0
    li   s1, 0                         // PSRC count
    li   a4, hd_ports
hp1:
    li   t0, HD_NPORTS
    beq  s0, t0, hp9
    lhu  a0, 4(a4)
    jal  gp, fl_res
    lhu  t0, 6(a4)
    beqz t0, hp2
    li   t1, 1 << 14
    add  a0, a0, t1
hp2:
    slli t0, s0, 2
    slli t1, s0, 1
    add  t0, t0, t1
    li   t1, PTAB
    add  t0, t0, t1
    lhu  t1, 0(a4)
    sh   t1, 0(t0)
    lhu  t1, 2(a4)
    sh   t1, 2(t0)
    sh   a0, 4(t0)
    slli a0, a0, 18
    srli a0, a0, 18
    lw   t1, V_N(x0)
    bgeu a0, t1, hp3
    slli t0, s1, 1
    li   t1, PSRC
    add  t0, t0, t1
    sh   a0, 0(t0)
    addi s1, s1, 1
hp3:
    addi a4, a4, 8
    addi s0, s0, 1
    j    hp1
hp9:
    sw   s1, V_NP(x0)
    li   t0, HD_NPORTS
    sw   t0, RV_NPORT(x0)
    li   t0, HD_ROMB
    sw   t0, RV_ROMB(x0)
    li   t0, HD_RAMB
    sw   t0, RV_RAMB(x0)
    POPRA
    ret
