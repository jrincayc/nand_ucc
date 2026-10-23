// improve.s -- module improver, bit-exact with tools/ref_improve.py improve_record().  Entry: imp_record (link ra, sp = SWTOP).
// In : IM_NIN, IM_S (slots), SLA/SLB (slot gates, 0xFF = hole), SOUT[0..IM_NO) pinned output signals.
// Out: IM_RES = 1 improved (RNA/RNB slots with 0xFF holes, ROUT outputs) or 0 (no strict gain / cannot be laid out).
.macro LDB d base i
    li   gp, \base
    add  gp, gp, \i
    lbu  \d, 0(gp)
.endm
.macro STB v base i t
    li   \t, \base
    add  \t, \t, \i
    sb   \v, 0(\t)
.endm
.macro PUSHRA
    addi sp, sp, -4
    sw   ra, 0(sp)
.endm
.macro POPRA
    lw   ra, 0(sp)
    addi sp, sp, 4
.endm

// ---------------------------------------------------------------- compact (GA, GB, IM_NG, OUTS)
compact:
    lw   s0, IM_NIN(x0)
    lw   s1, IM_NG(x0)
    add  a1, s0, s1
    li   a0, 0
cp0:
    STB  a0, REM, a0, t0
    addi a0, a0, 1
    bne  a0, a1, cp0
    li   a2, 0
cp1:
    beq  a2, s1, cp9
    LDB  a0, GA, a2
    LDB  a3, REM, a0
    LDB  a0, GB, a2
    LDB  a4, REM, a0
    STB  a3, GA, a2, t0
    STB  a4, GB, a2, t0
    mv   t1, a3
    mv   t2, a4
    bleu a3, a4, cp2
    mv   t1, a4
    mv   t2, a3
cp2:
    STB  t1, KMN, a2, t0
    STB  t2, KMX, a2, t0
    STB  x0, DUP, a2, t0
    li   a5, 0
cp3:
    beq  a5, a2, cp8
    LDB  a0, DUP, a5
    bnez a0, cp4
    LDB  a0, KMN, a5
    bne  a0, t1, cp4
    LDB  a0, KMX, a5
    bne  a0, t2, cp4
    add  a0, s0, a5
    add  a3, s0, a2
    STB  a0, REM, a3, t0
    li   a0, 1
    STB  a0, DUP, a2, t0
    j    cp8
cp4:
    addi a5, a5, 1
    j    cp3
cp8:
    addi a2, a2, 1
    j    cp1
cp9:
    lw   a1, IM_NO(x0)
    li   a2, 0
cp10:
    beq  a2, a1, cp11
    LDB  a0, OUTS, a2
    LDB  a3, REM, a0
    STB  a3, OUTS, a2, t0
    addi a2, a2, 1
    j    cp10
cp11:
    add  a1, s0, s1
    li   a0, 0
cp12:
    STB  x0, LIVE, a0, t0
    addi a0, a0, 1
    bne  a0, a1, cp12
    li   a4, 0
    lw   a1, IM_NO(x0)
    li   a2, 0
cp13:
    beq  a2, a1, cp14
    LDB  a0, OUTS, a2
    STB  a0, STK, a4, t0
    addi a4, a4, 1
    addi a2, a2, 1
    j    cp13
cp14:
    beqz a4, cp20
    addi a4, a4, -1
    LDB  a0, STK, a4
    bltu a0, s0, cp14
    LDB  a3, LIVE, a0
    bnez a3, cp14
    li   a3, 1
    STB  a3, LIVE, a0, t0
    sub  a0, a0, s0
    LDB  a3, GA, a0
    STB  a3, STK, a4, t0
    addi a4, a4, 1
    LDB  a3, GB, a0
    STB  a3, STK, a4, t0
    addi a4, a4, 1
    j    cp14
cp20:
    li   a0, 0
cp21:
    STB  a0, REN, a0, t0
    addi a0, a0, 1
    bne  a0, s0, cp21
    li   a4, 0
    li   a2, 0
cp22:
    beq  a2, s1, cp25
    add  a3, s0, a2
    LDB  a0, LIVE, a3
    beqz a0, cp24
    LDB  a0, GA, a2
    LDB  a5, REN, a0
    LDB  a0, GB, a2
    LDB  t1, REN, a0
    add  a3, s0, a4
    add  t2, s0, a2
    STB  a3, REN, t2, t0
    STB  a5, GA, a4, t0
    STB  t1, GB, a4, t0
    addi a4, a4, 1
cp24:
    addi a2, a2, 1
    j    cp22
cp25:
    sw   a4, IM_NG(x0)
    lw   a1, IM_NO(x0)
    li   a2, 0
cp26:
    beq  a2, a1, cp27
    LDB  a0, OUTS, a2
    LDB  a3, REN, a0
    STB  a3, OUTS, a2, t0
    addi a2, a2, 1
    j    cp26
cp27:
    ret

// ---------------------------------------------------------------- fan-out counts FO (pins + outputs)
mkfo:
    lw   s0, IM_NIN(x0)
    lw   s1, IM_NG(x0)
    add  a1, s0, s1
    li   a0, 0
fo0:
    STB  x0, FO, a0, t0
    addi a0, a0, 1
    bne  a0, a1, fo0
    li   a2, 0
fo1:
    beq  a2, s1, fo3
    LDB  a0, GA, a2
    LDB  a3, FO, a0
    addi a3, a3, 1
    STB  a3, FO, a0, t0
    LDB  a0, GB, a2
    LDB  a3, FO, a0
    addi a3, a3, 1
    STB  a3, FO, a0, t0
    addi a2, a2, 1
    j    fo1
fo3:
    lw   a1, IM_NO(x0)
    li   a2, 0
fo4:
    beq  a2, a1, fo5
    LDB  a0, OUTS, a2
    LDB  a3, FO, a0
    addi a3, a3, 1
    STB  a3, FO, a0, t0
    addi a2, a2, 1
    j    fo4
fo5:
    ret

// ---------------------------------------------------------------- insv: insert a0 into the sorted unique list ITL (count a3)
insv:
    li   a1, 0
iv0:
    beq  a1, a3, ivapp
    LDB  a2, ITL, a1
    beq  a2, a0, ivdone
    bltu a0, a2, ivshift
    addi a1, a1, 1
    j    iv0
ivshift:
    mv   t1, a3
iv1:
    beq  t1, a1, ivput
    addi t2, t1, -1
    LDB  a2, ITL, t2
    STB  a2, ITL, t1, t0
    mv   t1, t2
    j    iv1
ivput:
    STB  a0, ITL, a1, t0
    addi a3, a3, 1
    ret
ivapp:
    STB  a0, ITL, a3, t0
    addi a3, a3, 1
ivdone:
    ret

// ---------------------------------------------------------------- chain cuts of IM_ROOT -> CK[0..IM_NCUT) sorted by (len, leaves)
mkcuts:
    PUSHRA
    lw   s0, IM_NIN(x0)
    lw   a0, IM_ROOT(x0)
    sub  a0, a0, s0
    LDB  a1, GA, a0
    LDB  a2, GB, a0
    li   a3, 0
    mv   a0, a1
    jal  ra, insv
    mv   a0, a2
    jal  ra, insv
    // copy ITL -> LV, k in a4
    mv   a4, a3
    li   a5, 0                       // number of cuts
mc0:
    li   t0, 0
mc1:
    li   t1, LV
    add  t1, t1, t0
    li   t2, ITL
    add  t2, t2, t0
    lbu  t2, 0(t2)
    sb   t2, 0(t1)
    addi t0, t0, 1
    bne  t0, a3, mc1
    // key
    slli a0, a4, 24
    li   t1, LV
    lbu  t2, 0(t1)
    slli t2, t2, 16
    add  a0, a0, t2
    li   t0, 1
    bleu a4, t0, mc2
    lbu  t2, 1(t1)
    slli t2, t2, 8
    add  a0, a0, t2
    li   t0, 2
    bleu a4, t0, mc2
    lbu  t2, 2(t1)
    add  a0, a0, t2
mc2:
    // insertion into CK (stable)
    mv   t1, a5
mc3:
    beqz t1, mc5
    addi t2, t1, -1
    slli t0, t2, 2
    li   a1, CK
    add  t0, t0, a1
    lw   a2, 0(t0)
    bleu a2, a0, mc5
    sw   a2, 4(t0)
    mv   t1, t2
    j    mc3
mc5:
    slli t0, t1, 2
    li   a1, CK
    add  t0, t0, a1
    sw   a0, 0(t0)
    addi a5, a5, 1
    // next cut: replace the last leaf if it is a gate
    li   t1, LV
    add  t1, t1, a4
    lbu  t2, -1(t1)
    bltu t2, s0, mcend
    sub  t2, t2, s0
    LDB  a1, GA, t2
    LDB  a2, GB, t2
    sw   a1, IM_CNT(x0)
    sw   a2, IM_SAVED(x0)
    li   a3, 0
    addi t0, a4, -1
    sw   t0, IM_K(x0)
    li   t0, 0
mc6:
    lw   t1, IM_K(x0)
    beq  t0, t1, mc7
    sw   t0, IM_NS(x0)
    LDB  a0, LV, t0
    jal  ra, insv
    lw   t0, IM_NS(x0)
    addi t0, t0, 1
    j    mc6
mc7:
    lw   a0, IM_CNT(x0)
    jal  ra, insv
    lw   a0, IM_SAVED(x0)
    jal  ra, insv
    li   t0, 3
    bgtu a3, t0, mcend
    mv   a4, a3
    j    mc0
mcend:
    sw   a5, IM_NCUT(x0)
    POPRA
    ret

// ---------------------------------------------------------------- search(IM_K, IM_F, IM_GMAX) -> a0 = 1 and IM_N, PROG
search:
    lw   s0, IM_GMAX(x0)
    li   s1, 1
sr_g:
    bgtu s1, s0, sr_fail
    lw   a5, IM_K(x0)
    li   t0, 0
sr_i:
    LDB  a0, BASE, t0
    STB  a0, SIG, t0, t1
    addi t0, t0, 1
    bne  t0, a5, sr_i
    li   a4, 0
    STB  x0, JJ, a4, t0
    STB  x0, II, a4, t0
sr_l:
    beq  a4, s1, sr_leaf
sr_c:
    LDB  a0, JJ, a4
    LDB  a1, II, a4
    bgeu a0, a5, sr_back
    LDB  a2, SIG, a1
    LDB  a3, SIG, a0
    and  a2, a2, a3
    lw   a3, IM_FULL(x0)
    xor  a2, a2, a3
    addi t1, a1, 1
    mv   t2, a0
    bleu t1, a0, sr_adv
    li   t1, 0
    addi t2, a0, 1
sr_adv:
    STB  t2, JJ, a4, t0
    STB  t1, II, a4, t0
    li   t1, 0
sr_d:
    beq  t1, a5, sr_new
    LDB  a3, SIG, t1
    beq  a3, a2, sr_c
    addi t1, t1, 1
    j    sr_d
sr_new:
    STB  a2, SIG, a5, t0
    slli a3, a4, 1
    STB  a1, PROG, a3, t0
    addi a3, a3, 1
    STB  a0, PROG, a3, t0
    addi a5, a5, 1
    addi a4, a4, 1
    STB  x0, JJ, a4, t0
    STB  x0, II, a4, t0
    j    sr_l
sr_leaf:
    lw   a3, IM_F(x0)
    li   t1, 0
sr_f:
    beq  t1, a5, sr_back
    LDB  a2, SIG, t1
    beq  a2, a3, sr_ok
    addi t1, t1, 1
    j    sr_f
sr_back:
    beqz a4, sr_nextg
    addi a4, a4, -1
    addi a5, a5, -1
    j    sr_c
sr_nextg:
    addi s1, s1, 1
    j    sr_g
sr_ok:
    sw   s1, IM_N(x0)
    li   a0, 1
    ret
sr_fail:
    li   a0, 0
    ret

// ---------------------------------------------------------------- try_cut: a0 = key of the cut; IM_ROOT.  Returns a0 = 1 if the module was rewritten.
try_cut:
    PUSHRA
    srli t0, a0, 24
    sw   t0, IM_K(x0)
    li   t1, LV
    srli t0, a0, 16
    andi t0, t0, 255
    sb   t0, 0(t1)
    srli t0, a0, 8
    andi t0, t0, 255
    sb   t0, 1(t1)
    andi t0, a0, 255
    sb   t0, 2(t1)
    lw   s0, IM_NIN(x0)
    lw   s1, IM_NG(x0)
    add  a1, s0, s1
    li   a0, 0
tc0:
    STB  x0, CONE, a0, t0
    STB  x0, INNER, a0, t0
    STB  x0, LEAFF, a0, t0
    addi a0, a0, 1
    bne  a0, a1, tc0
    lw   a4, IM_K(x0)
    li   a0, 0
tc1:
    LDB  a2, LV, a0
    li   a3, 1
    STB  a3, LEAFF, a2, t0
    addi a0, a0, 1
    bne  a0, a4, tc1
    lw   a0, IM_ROOT(x0)
    li   a4, 0
    STB  a0, STK, a4, t0
    li   a4, 1
tc2:
    beqz a4, tc3
    addi a4, a4, -1
    LDB  a0, STK, a4
    bltu a0, s0, tc2
    LDB  a3, LEAFF, a0
    bnez a3, tc2
    LDB  a3, CONE, a0
    bnez a3, tc2
    li   a3, 1
    STB  a3, CONE, a0, t0
    sub  a0, a0, s0
    LDB  a3, GA, a0
    STB  a3, STK, a4, t0
    addi a4, a4, 1
    LDB  a3, GB, a0
    STB  a3, STK, a4, t0
    addi a4, a4, 1
    j    tc2
tc3:
    mv   a2, s0
tc4:
    beq  a2, a1, tc6
    LDB  a3, CONE, a2
    beqz a3, tc5
    sub  a0, a2, s0
    LDB  a3, GA, a0
    LDB  a5, CONE, a3
    beqz a5, tcA
    LDB  a5, INNER, a3
    addi a5, a5, 1
    STB  a5, INNER, a3, t0
tcA:
    LDB  a3, GB, a0
    LDB  a5, CONE, a3
    beqz a5, tc5
    LDB  a5, INNER, a3
    addi a5, a5, 1
    STB  a5, INNER, a3, t0
tc5:
    addi a2, a2, 1
    j    tc4
tc6:
    li   a5, 0
    mv   a2, s0
tc7:
    beq  a2, a1, tc9
    LDB  a3, CONE, a2
    beqz a3, tc8
    lw   a0, IM_ROOT(x0)
    beq  a2, a0, tcS
    LDB  a3, FO, a2
    LDB  a4, INNER, a2
    bne  a3, a4, tc8
    li   t0, OUTS
    lbu  t2, 0(t0)
    beq  t2, a2, tc8
    lw   t1, IM_NO(x0)
    li   t2, 2
    bne  t1, t2, tcS
    lbu  t2, 1(t0)
    beq  t2, a2, tc8
tcS:
    addi a5, a5, 1
tc8:
    addi a2, a2, 1
    j    tc7
tc9:
    sw   a5, IM_SAVED(x0)
    lw   a4, IM_K(x0)
    li   a0, 3
    li   t0, 1
    beq  a4, t0, tcF
    li   a0, 15
    li   t0, 2
    beq  a4, t0, tcF
    li   a0, 255
tcF:
    sw   a0, IM_FULL(x0)
    li   t1, 0
    li   t2, 0xAA
    and  t2, t2, a0
    STB  t2, BASE, t1, t0
    li   t1, 1
    li   t2, 0xCC
    and  t2, t2, a0
    STB  t2, BASE, t1, t0
    li   t1, 2
    li   t2, 0xF0
    and  t2, t2, a0
    STB  t2, BASE, t1, t0
    li   a2, 0
tcV:
    beq  a2, a4, tcW
    LDB  a3, LV, a2
    LDB  a5, BASE, a2
    STB  a5, VAL, a3, t0
    addi a2, a2, 1
    j    tcV
tcW:
    mv   a2, s0
tcX:
    beq  a2, a1, tcY
    LDB  a3, CONE, a2
    beqz a3, tcZ
    sub  a0, a2, s0
    LDB  a3, GA, a0
    LDB  a5, VAL, a3
    LDB  a3, GB, a0
    LDB  a3, VAL, a3
    and  a5, a5, a3
    lw   a3, IM_FULL(x0)
    xor  a5, a5, a3
    STB  a5, VAL, a2, t0
tcZ:
    addi a2, a2, 1
    j    tcX
tcY:
    lw   a3, IM_ROOT(x0)
    LDB  a3, VAL, a3
    sw   a3, IM_F(x0)
    li   a2, 0
tcB:
    beq  a2, a4, tcN
    LDB  a5, BASE, a2
    beq  a5, a3, tcL
    addi a2, a2, 1
    j    tcB
tcL:
    LDB  a0, LV, a2
    sw   a0, IM_NS(x0)
    sw   x0, IM_N(x0)
    j    tcR
tcN:
    lw   a0, IM_SAVED(x0)
    addi a0, a0, -1
    li   t0, 6
    bleu a0, t0, tcG
    li   a0, 6
tcG:
    blez a0, tcFail
    sw   a0, IM_GMAX(x0)
    jal  ra, search
    beqz a0, tcFail
    lw   a0, IM_ROOT(x0)
    lw   t0, IM_N(x0)
    add  a0, a0, t0
    addi a0, a0, -1
    sw   a0, IM_NS(x0)
tcR:
    jal  ra, rewrite
    li   a0, 1
    POPRA
    ret
tcFail:
    li   a0, 0
    POPRA
    ret

// ---------------------------------------------------------------- rewrite: insert IM_N new gates (PROG over LV) before IM_ROOT, users of the root use IM_NS, then compact
rewrite:
    PUSHRA
    lw   s0, IM_NIN(x0)
    lw   s1, IM_NG(x0)
    lw   a4, IM_ROOT(x0)
    lw   a5, IM_N(x0)
    sub  a3, a4, s0                  // g0
    li   a0, 0                       // destination index
    li   a2, 0
rw1:
    beq  a2, a3, rw2
    LDB  t1, GA, a2
    STB  t1, NGA, a0, t0
    LDB  t1, GB, a2
    STB  t1, NGB, a0, t0
    addi a0, a0, 1
    addi a2, a2, 1
    j    rw1
rw2:
    li   a2, 0
rw3:
    beq  a2, a5, rw6
    slli t1, a2, 1
    LDB  a1, PROG, t1
    addi t1, t1, 1
    LDB  t2, PROG, t1
    lw   t1, IM_K(x0)
    bltu a1, t1, rw4
    sub  a1, a1, t1
    add  a1, a1, a4
    j    rw4b
rw4:
    LDB  a1, LV, a1
rw4b:
    bltu t2, t1, rw5
    sub  t2, t2, t1
    add  t2, t2, a4
    j    rw5b
rw5:
    LDB  t2, LV, t2
rw5b:
    STB  a1, NGA, a0, t0
    STB  t2, NGB, a0, t0
    addi a0, a0, 1
    addi a2, a2, 1
    j    rw3
rw6:
    mv   a2, a3
rw7:
    beq  a2, s1, rw9
    LDB  a1, GA, a2
    bltu a1, a4, rw8
    add  a1, a1, a5
rw8:
    LDB  t2, GB, a2
    bltu t2, a4, rw8b
    add  t2, t2, a5
rw8b:
    STB  a1, NGA, a0, t0
    STB  t2, NGB, a0, t0
    addi a0, a0, 1
    addi a2, a2, 1
    j    rw7
rw9:
    // a0 = new gate count; r2 = root + n; replace r2 -> ns in all gates, copy back
    add  a3, a4, a5                  // r2
    lw   a4, IM_NS(x0)
    li   a2, 0
rw10:
    beq  a2, a0, rw13
    LDB  a1, NGA, a2
    bne  a1, a3, rw11
    mv   a1, a4
rw11:
    STB  a1, GA, a2, t0
    LDB  a1, NGB, a2
    bne  a1, a3, rw12
    mv   a1, a4
rw12:
    STB  a1, GB, a2, t0
    addi a2, a2, 1
    j    rw10
rw13:
    sw   a0, IM_NG(x0)
    lw   a1, IM_NO(x0)
    lw   t1, IM_ROOT(x0)
    li   a2, 0
rw14:
    beq  a2, a1, rw17
    LDB  a0, OUTS, a2
    bltu a0, t1, rw15
    add  a0, a0, a5
rw15:
    bne  a0, a3, rw16
    mv   a0, a4
rw16:
    STB  a0, OUTS, a2, t0
    addi a2, a2, 1
    j    rw14
rw17:
    jal  ra, compact
    POPRA
    ret

// ---------------------------------------------------------------- improve (GA, GB, IM_NG, OUTS): compact, then rewrite until nothing changes
improve:
    PUSHRA
    jal  ra, compact
imp1:
    jal  ra, mkfo
    sw   x0, IM_GI(x0)
imp2:
    lw   a0, IM_GI(x0)
    lw   t0, IM_NG(x0)
    beq  a0, t0, imp_done
    lw   t0, IM_NIN(x0)
    add  a0, a0, t0
    sw   a0, IM_ROOT(x0)
    jal  ra, mkcuts
    sw   x0, IM_CI(x0)
imp3:
    lw   a0, IM_CI(x0)
    lw   t0, IM_NCUT(x0)
    beq  a0, t0, imp4
    slli t0, a0, 2
    li   t1, CK
    add  t0, t0, t1
    lw   a0, 0(t0)
    jal  ra, try_cut
    bnez a0, imp1
    lw   a0, IM_CI(x0)
    addi a0, a0, 1
    sw   a0, IM_CI(x0)
    j    imp3
imp4:
    lw   a0, IM_GI(x0)
    addi a0, a0, 1
    sw   a0, IM_GI(x0)
    j    imp2
imp_done:
    POPRA
    ret

// ---------------------------------------------------------------- partition: PA/PB/POUT from GA/GB/OUTS (outputs last, ascending); a0 = 0 if impossible
partition:
    lw   s0, IM_NIN(x0)
    lw   s1, IM_NG(x0)
    lw   a4, IM_NO(x0)
    li   t0, OUTS
    lbu  a0, 0(t0)
    bltu a0, s0, pt_fail
    li   t1, 2
    bne  a4, t1, pt_ok1
    lbu  a1, 1(t0)
    bltu a1, s0, pt_fail
    beq  a0, a1, pt_fail
pt_ok1:
    // IORD: non-outputs ascending, then outputs ascending
    li   a5, 0
    li   a2, 0
pt1:
    beq  a2, s1, pt3
    add  a3, s0, a2
    li   t0, OUTS
    lbu  t1, 0(t0)
    beq  t1, a3, pt2
    li   t2, 2
    bne  a4, t2, pt1a
    lbu  t1, 1(t0)
    beq  t1, a3, pt2
pt1a:
    STB  a3, IORD, a5, t0
    addi a5, a5, 1
pt2:
    addi a2, a2, 1
    j    pt1
pt3:
    li   t0, OUTS
    lbu  a0, 0(t0)
    li   t1, 2
    bne  a4, t1, pt3b
    lbu  a1, 1(t0)
    bleu a0, a1, pt3a
    mv   t2, a0
    mv   a0, a1
    mv   a1, t2
pt3a:
    STB  a0, IORD, a5, t0
    addi a5, a5, 1
    mv   a0, a1
pt3b:
    STB  a0, IORD, a5, t0
    addi a5, a5, 1
    // PREN
    li   a0, 0
pt4:
    STB  a0, PREN, a0, t0
    addi a0, a0, 1
    bne  a0, s0, pt4
    li   a2, 0
pt5:
    beq  a2, s1, pt6
    LDB  a3, IORD, a2
    add  a0, s0, a2
    STB  a0, PREN, a3, t0
    addi a2, a2, 1
    j    pt5
pt6:
    li   a2, 0
pt7:
    beq  a2, s1, pt9
    LDB  a3, IORD, a2
    sub  a3, a3, s0
    LDB  a0, GA, a3
    LDB  a0, PREN, a0 
    j    pt7a
pt7a:
    add  a1, s0, a2
    bgeu a0, a1, pt_fail
    STB  a0, PA, a2, t0
    LDB  a3, IORD, a2
    sub  a3, a3, s0
    LDB  a0, GB, a3
    LDB  a0, PREN, a0
    bgeu a0, a1, pt_fail
    STB  a0, PB, a2, t0
    addi a2, a2, 1
    j    pt7
pt9:
    li   a2, 0
pt10:
    beq  a2, a4, pt11
    LDB  a0, OUTS, a2
    LDB  a3, PREN, a0
    STB  a3, POUT, a2, t0
    addi a2, a2, 1
    j    pt10
pt11:
    li   a0, 1
    ret
pt_fail:
    li   a0, 0
    ret

// ---------------------------------------------------------------- imp_record
imp_record:
    PUSHRA
    sw   x0, IM_RES(x0)
    lw   s0, IM_NIN(x0)
    lw   s1, IM_S(x0)
    li   a2, 0
ir0:
    beq  a2, s1, ir1
    LDB  a0, SLA, a2
    li   t0, 0xFF
    beq  a0, t0, ir0n
    add  t1, s0, a2
    bgeu a0, t1, ir_none
    LDB  a1, SLB, a2
    bgeu a1, t1, ir_none
ir0n:
    addi a2, a2, 1
    j    ir0
ir1:
    li   a0, 0
ir2:
    STB  a0, REN, a0, t0
    addi a0, a0, 1
    bne  a0, s0, ir2
    li   a4, 0
    li   a2, 0
ir3:
    beq  a2, s1, ir5
    LDB  a0, SLA, a2
    li   t0, 0xFF
    beq  a0, t0, ir4
    LDB  a0, REN, a0
    LDB  a1, SLB, a2
    LDB  a1, REN, a1
    STB  a0, GA, a4, t0
    STB  a1, GB, a4, t0
    add  a3, s0, a4
    add  t2, s0, a2
    STB  a3, REN, t2, t0
    addi a4, a4, 1
ir4:
    addi a2, a2, 1
    j    ir3
ir5:
    sw   a4, IM_NG(x0)
    sw   a4, IM_REAL(x0)
    lw   a1, IM_NO(x0)
    li   a2, 0
ir6:
    beq  a2, a1, ir7
    LDB  a0, SOUT, a2
    LDB  a3, REN, a0
    STB  a3, OUTS, a2, t0
    addi a2, a2, 1
    j    ir6
ir7:
    jal  ra, compact
    jal  ra, improve
ir8:
    jal  ra, partition
    beqz a0, ir_none
    // equal to the current module?
    lw   s1, IM_NG(x0)
    lw   a4, IM_NO(x0)
    li   a2, 0
    li   a5, 1
ir9:
    beq  a2, s1, ir10
    LDB  a0, GA, a2
    LDB  a1, PA, a2
    bne  a0, a1, ir9n
    LDB  a0, GB, a2
    LDB  a1, PB, a2
    beq  a0, a1, ir9o
ir9n:
    li   a5, 0
ir9o:
    addi a2, a2, 1
    j    ir9
ir10:
    li   a2, 0
ir11:
    beq  a2, a4, ir12
    LDB  a0, OUTS, a2
    LDB  a1, POUT, a2
    beq  a0, a1, ir11o
    li   a5, 0
ir11o:
    addi a2, a2, 1
    j    ir11
ir12:
    bnez a5, ir14
    li   a2, 0
ir13:
    beq  a2, s1, ir13b
    LDB  a0, PA, a2
    STB  a0, GA, a2, t0
    LDB  a0, PB, a2
    STB  a0, GB, a2, t0
    addi a2, a2, 1
    j    ir13
ir13b:
    li   a2, 0
ir13c:
    beq  a2, a4, ir13d
    LDB  a0, POUT, a2
    STB  a0, OUTS, a2, t0
    addi a2, a2, 1
    j    ir13c
ir13d:
    jal  ra, improve
    j    ir8
ir14:
    lw   a0, IM_NG(x0)
    lw   t0, IM_REAL(x0)
    bgeu a0, t0, ir_none
    // layout
    lw   s0, IM_NIN(x0)
    lw   s1, IM_S(x0)
    lw   a4, IM_NO(x0)
    li   a2, 0
ly1:
    beq  a2, a4, ly2
    LDB  a0, OUTS, a2
    LDB  a1, SOUT, a2
    sub  a1, a1, s0
    STB  a1, SOF, a0, t0
    addi a2, a2, 1
    j    ly1
ly2:
    // free slots
    li   a5, 0
    li   a2, 0
ly3:
    beq  a2, s1, ly5
    add  a3, s0, a2
    li   t0, SOUT
    lbu  t1, 0(t0)
    beq  t1, a3, ly4
    li   t2, 2
    bne  a4, t2, ly3a
    lbu  t1, 1(t0)
    beq  t1, a3, ly4
ly3a:
    STB  a2, FREE, a5, t0
    addi a5, a5, 1
ly4:
    addi a2, a2, 1
    j    ly3
ly5:
    // non-output gates -> free slots in order
    lw   t1, IM_NG(x0)
    li   a3, 0
    li   a2, 0
ly6:
    beq  a2, t1, ly9
    add  a0, s0, a2
    li   t0, OUTS
    lbu  t2, 0(t0)
    beq  t2, a0, ly8
    li   t2, 2
    bne  a4, t2, ly6a
    lbu  t2, 1(t0)
    beq  t2, a0, ly8
ly6a:
    bgeu a3, a5, ir_none
    LDB  t2, FREE, a3
    STB  t2, SOF, a0, t0
    addi a3, a3, 1
ly8:
    addi a2, a2, 1
    j    ly6
ly9:
    // result slots: holes, then gates
    li   a2, 0
ly10:
    beq  a2, s1, ly11
    li   t2, 0xFF
    STB  t2, RNA, a2, t0
    STB  t2, RNB, a2, t0
    addi a2, a2, 1
    j    ly10
ly11:
    li   a2, 0
ly12:
    lw   t1, IM_NG(x0)
    beq  a2, t1, ly14
    add  a0, s0, a2
    LDB  a3, SOF, a0
    LDB  a1, GA, a2
    bltu a1, s0, ly12a
    LDB  a1, SOF, a1
    add  a1, a1, s0
ly12a:
    LDB  a5, GB, a2
    bltu a5, s0, ly12b
    LDB  a5, SOF, a5
    add  a5, a5, s0
ly12b:
    add  t1, s0, a3
    bgeu a1, t1, ir_none
    bgeu a5, t1, ir_none
    STB  a1, RNA, a3, t0
    STB  a5, RNB, a3, t0
    addi a2, a2, 1
    j    ly12
ly14:
    // outputs
    li   a2, 0
ly15:
    beq  a2, a4, ly16
    LDB  a0, OUTS, a2
    bltu a0, s0, ly15a
    LDB  a0, SOF, a0
    add  a0, a0, s0
ly15a:
    STB  a0, ROUT, a2, t0
    addi a2, a2, 1
    j    ly15
ly16:
    // entries: gates and runs of holes
    li   a5, 0
    li   a3, 0
    li   a2, 0
ly17:
    beq  a2, s1, ly19
    LDB  a0, RNA, a2
    li   t0, 0xFF
    bne  a0, t0, ly18
    bnez a3, ly17n
    li   a3, 1
    addi a5, a5, 1
    j    ly17n
ly18:
    li   a3, 0
    addi a5, a5, 1
ly17n:
    addi a2, a2, 1
    j    ly17
ly19:
    slli t0, a5, 1
    add  t0, t0, a5
    add  t0, t0, a4
    addi t0, t0, 4
    li   t1, 40
    bgtu t0, t1, ir_none
    li   a0, 1
    sw   a0, IM_RES(x0)
ir_none:
    POPRA
    ret
