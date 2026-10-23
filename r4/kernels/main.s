// main.s -- the whole R4 program:  improve the module library, flatten the HD, place, route; PROGRAM_ROM of the child image; wire.
// Order of the arm commands: place (gates, ROM, arm, RAM), PROGRAM_ROM (nonzero bytes of the child image in address order), tracks and vias (late sinks last).
main:
    li   sp, SWTOP
    jal  ra, mt_load
    jal  ra, mt_improve_all
    jal  ra, build_modimg
    jal  ra, flatten
    li   a0, 0x1000                   // the placement kernels expect zeroed scratch (everything except SRC / PSRC and the variables)
    li   a1, 0x26000
    jal  ra, zero_range
    li   a0, 0x2A400
    li   a1, ARMB
    jal  ra, zero_range
    li   t0, RNG_SEED
    sw   t0, V_RNG(x0)
    sw   x0, V_LEVELS(x0)
    jal  ra, build_graph
    jal  ra, place_order
    li   a0, 0x1000                   // the placement scratch overlays SRC / KINDA / PTAB: clear everything but FINAL, then build them again
    li   a1, FINAL
    jal  ra, zero_range
    lw   a1, V_N(x0)
    slli a1, a1, 1
    li   t0, FINAL + 16
    add  a0, a1, t0
    addi a0, a0, 3
    andi a0, a0, -4
    li   a1, ARMB
    jal  ra, zero_range
    jal  ra, flatten
    jal  ra, route1
    jal  ra, route2
    // child frame: origin at parent arm + (OX, OY); the parent's arm sits at (xa, y of the last row) of the parent frame, so
    // OX = W + GAP - xa puts the child GAP cells right of the parent, OY = -y_last_row puts it on the same rows.
    lw   t0, RV_W(x0)
    addi t0, t0, CHILD_GAP
    lw   t1, RV_XA(x0)
    sub  t0, t0, t1
    sw   t0, RV_OX(x0)
    li   t0, YT + 2 * (R_ROWS - 1)
    lhu  t0, 0(t0)
    sub  t0, x0, t0
    sw   t0, RV_OY(x0)
    jal  ra, route3_place
    jal  ra, prog_rom
    jal  ra, route3_wire
mhalt:
    j    mhalt

// module records of the child -> MODIMG (zero padded, fixed offsets)
build_modimg:
    PUSHRA
    li   a1, 0
bm0:
    li   t0, MODIMG
    add  t0, t0, a1
    sb   x0, 0(t0)
    addi a1, a1, 1
    li   t0, hd_body - hd_mods
    bne  a1, t0, bm0
    li   s0, 0
bm1:
    li   t0, HD_NMODS
    beq  s0, t0, bm2
    li   a1, hd_modoff
    slli t0, s0, 1
    add  a1, a1, t0
    lhu  a1, 0(a1)
    li   t0, MODIMG
    add  a1, a1, t0
    mv   a0, s0
    sw   s0, FV_M(x0)
    jal  ra, mt_encode
    lw   s0, FV_M(x0)
    addi s0, s0, 1
    j    bm1
bm2:
    POPRA
    ret

// PROGRAM_ROM of every nonzero byte of the child image (own image with the improved module records)
prog_rom:
    li   sp, ARMB
    li   a4, 0
    li   a5, hd_end - ROM_BASE
pr1:
    beq  a4, a5, pr9
    li   t0, ROM_BASE
    add  t0, t0, a4
    lbu  a3, 0(t0)
    li   t0, hd_mods - ROM_BASE
    bltu a4, t0, pr2
    sub  t2, a4, t0
    li   t1, hd_body - hd_mods
    bgeu t2, t1, pr2
    li   t0, MODIMG
    add  t0, t0, t2
    lbu  a3, 0(t0)
pr2:
    beqz a3, pr3
    lw   t0, RV_XR(x0)
    lw   t1, RV_OX(x0)
    add  t0, t0, t1
    sb   t0, 0(sp)
    srli t0, t0, 8
    sb   t0, 1(sp)
    li   t0, YT + 2 * (R_ROWS - 1)
    lhu  t0, 0(t0)
    lw   t1, RV_OY(x0)
    add  t0, t0, t1
    sb   t0, 2(sp)
    srli t0, t0, 8
    sb   t0, 3(sp)
    sb   a4, 4(sp)
    srli t0, a4, 8
    sb   t0, 5(sp)
    sb   a3, 10(sp)
    li   t0, 3
    sb   t0, 15(sp)
pr3:
    addi a4, a4, 1
    j    pr1
pr9:
    ret

// zero_range: bytes [a0, a1), word aligned
zero_range:
zr1:
    bgeu a0, a1, zr2
    sw   x0, 0(a0)
    addi a0, a0, 4
    j    zr1
zr2:
    ret
