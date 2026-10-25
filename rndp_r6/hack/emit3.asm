// emit.asm -- R6 emitter: plane part (inverters, buses, lo/hi decoder lines, cells, gadget/pass slots, snake connectors)
.equ ARM, ARM_BASE
.equ XB, 24
.equ XG, 84
.equ X0, 138
.equ INVY, 2
.equ BASE0, 1041
.equ SH, 53
.equ TOPB, 7780
.equ TOPLO, 7773
.equ LASTX, 1154
.equ NSTRIP, 128
.equ NRUN, 2
.equ XEND, 1164
start:
    SET AUH, 0
    SET16 GP, rprog
    CALL gvm
halt:
    GOTO halt
// gvm.asm -- glue VM: 5-byte ops (opc a b c d); variables are RAM byte addresses
.macro G o a b c d
    .byte \o,\a,\b,\c,\d
.endm
.macro END
    G 0,0,0,0,0
.endm
.macro SETW v k
    G 1,\v,lo(\k),hi(\k),0
.endm
.macro CPYW d s
    G 2,\d,\s,0,0
.endm
.macro ADDW v k
    G 3,\v,lo(\k),hi(\k),0
.endm
.macro SETB v k
    G 4,\v,\k,0,0
.endm
.macro TMPL t
    G 5,0,lo(\t),hi(\t),0
.endm
.macro EMT l
    G 6,\l,0,0,0
.endm
.macro EMV
    G 7,0,0,0,0
.endm
.macro CALLG t
    G 8,0,lo(\t),hi(\t),0
.endm
.macro DJNZ v t
    G 9,\v,lo(\t),hi(\t),0
.endm
.macro JNEB v k t
    G 10,\v,\k,lo(\t),hi(\t)
.endm
.macro INCB v
    G 11,\v,0,0,0
.endm
.macro SKZ v m
    G 12,\v,\m,0,0
.endm
.macro SKB v
    G 13,\v,0,0,0
.endm
.macro DBLB v
    G 14,\v,0,0,0
.endm
.macro RDD v
    G 15,\v,0,0,0
.endm
.macro CPYB d s
    G 16,\d,\s,0,0
.endm
.macro TMPLV
    G 17,0,0,0,0
.endm
.macro JMPG t
    G 18,0,lo(\t),hi(\t),0
.endm
.macro ADDB v k
    G 19,\v,\k,0,0
.endm
.macro CALLS t
    G 21,0,lo(\t),hi(\t),0
.endm
.macro ADDWV v s
    G 20,\v,\s,0,0
.endm

gb:                          // next bytecode byte -> RAM[PW++]
    SET PSEL, GP
    CALL rdb
    PUT PW
    RET gb

gvm:                         // run the bytecode at GP until the top-level END
    SET SPG, GST
gv_loop:
    SET PW, OPC
    CALL gb
    CALL gb
    CALL gb
    CALL gb
    CALL gb
    LD OPC
    IFEQ gv_end
    D=D-1
    IFEQ gv_setw
    D=D-1
    IFEQ gv_cpyw
    D=D-1
    IFEQ gv_addw
    D=D-1
    IFEQ gv_setb
    D=D-1
    IFEQ gv_tmpl
    D=D-1
    IFEQ gv_emt
    D=D-1
    IFEQ gv_emv
    D=D-1
    IFEQ gv_callg
    D=D-1
    IFEQ gv_djnz
    D=D-1
    IFEQ gv_jneb
    D=D-1
    IFEQ gv_incb
    D=D-1
    IFEQ gv_skz
    D=D-1
    IFEQ gv_skb
    D=D-1
    IFEQ gv_dblb
    D=D-1
    IFEQ gv_rdd
    D=D-1
    IFEQ gv_cpyb
    D=D-1
    IFEQ gv_tmplv
    D=D-1
    IFEQ gv_jmp
    D=D-1
    IFEQ gv_addb
    D=D-1
    IFEQ gv_addwv
    GOTO gv_calls
gv_calls:
    SET16 RA_gx, gv_loop
    @A2
    AP
    0;JMP
gv_setw:
    LD A2
    @A1
    A=M
    M=D
    LD A3
    @A1
    A=M+1
    M=D
    GOTO gv_loop
gv_cpyw:
    @A2
    A=M
    D=M
    @A1
    A=M
    M=D
    @A2
    A=M+1
    D=M
    @A1
    A=M+1
    M=D
    GOTO gv_loop
gv_addw:
    LD A2
    ST AUL
    LD A3
    ST AUH
    LD A1
    ST ADST
    CALL add16
    GOTO gv_loop
gv_setb:
    LD A2
    @A1
    A=M
    M=D
    GOTO gv_loop
gv_tmpl:
    LD A2
    ST TP
    LD A3
    ST TP+1
gv_tmplv:
    CALL tmpl
    GOTO gv_loop
gv_emt:
    LD A1
    ST DT
    CALL emt
    GOTO gv_loop
gv_emv:
    CALL emv
    GOTO gv_loop
gv_callg:
    @GP
    D=M
    @SPG
    A=M
    M=D
    @GP+1
    D=M
    @SPG
    A=M+1
    M=D
    @SPG
    M=M+1
    M=M+1
gv_jmp:
    LD A2
    ST GP
    LD A3
    ST GP+1
    GOTO gv_loop
gv_djnz:
    @A1
    A=M
    M=M-1
    D=M
    IFNE gv_jmp
    GOTO gv_loop
gv_jneb:
    @A1
    A=M
    D=M
    @A2
    D=D-M
    IFEQ gv_loop
    LD A3
    ST GP
    LD A4
    ST GP+1
    GOTO gv_loop
gv_incb:
    @A1
    A=M
    M=M+1
    GOTO gv_loop
gv_skz:
    @A1
    A=M
    D=M
    @A2
    A=M
    D=D&M
    IFNE gv_loop
    GOTO gv_skip
gv_skb:
    @A1
    A=M
    D=M
    IFNE gv_loop
gv_skip:
    ADDI GP, 5
    GOTO gv_loop
gv_dblb:
    @A1
    A=M
    D=M
    DBL
    @A1
    A=M
    M=D
    GOTO gv_loop
gv_rdd:
    SET PSEL, DP
    CALL rdb
    @A1
    A=M
    M=D
    GOTO gv_loop
gv_cpyb:
    @A2
    A=M
    D=M
    @A1
    A=M
    M=D
    GOTO gv_loop
gv_addb:
    @A1
    A=M
    D=M
    @A2
    D=D+M
    @A1
    A=M
    M=D
    GOTO gv_loop
gv_addwv:
    @A2
    A=M
    D=M
    ST AUL
    LD A1
    ST ADST
    CALL add16
    GOTO gv_loop
gv_end:
    LD SPG
    @GST
    D=D-A
    IFEQ gv_done
    @SPG
    M=M-1
    M=M-1
    A=M
    D=M
    ST GP
    @SPG
    A=M+1
    D=M
    ST GP+1
    GOTO gv_loop
gv_done:
    RET gvm

emt:                         // TRACK layer DT from P0 to P1
    WRA 0, P0X
    WRA 1, P0X+1
    WRA 2, P0Y
    WRA 3, P0Y+1
    WRA 4, P1X
    WRA 5, P1X+1
    WRA 6, P1Y
    WRA 7, P1Y+1
    WRA 10, DT
    WRK 15, 4
    RET emt

emv:                         // VIA at P0
    WRA 0, P0X
    WRA 1, P0X+1
    WRA 2, P0Y
    WRA 3, P0Y+1
    WRK 15, 5
    RET emv

rdpt:                        // (QX,QY) = (OX,OY) + (dx16, sext dy8) read from the template
    SET PSEL, TP
    CALL rdb
    ST AUL
    CALL rdb
    ST AUH
    COPY16 QX, OX
    SET ADST, QX
    CALL add16
    CALL rdb
    ST AUL
    COPY16 QY, OY
    LD AUL
    IFGE rp_y
    SET AUH, 255
rp_y:
    SET ADST, QY
    CALL add16
    RET rdpt

tmpl:                        // run the template at TP with origin (OX,OY)
    SET PSEL, TP
    CALL rdb
    ST BYT
    @3
    D=D&A
    IFEQ tm_end
    @1
    D=D-A
    IFEQ tm_place
    @1
    D=D-A
    IFEQ tm_track
    CALL rdpt                // via
    WRA 0, QX
    WRA 1, QX+1
    WRA 2, QY
    WRA 3, QY+1
    WRK 15, 5
    GOTO tmpl
tm_place:
    SET PSEL, TP
    CALL rdb
    ST DT
    CALL rdpt
    WRA 0, QX
    WRA 1, QX+1
    WRA 2, QY
    WRA 3, QY+1
    WRA 8, DT
    WRK 9, 0
    WRK 10, 0
    WRK 15, 1
    GOTO tmpl
tm_track:
    CALL rdpt
    WRA 0, QX
    WRA 1, QX+1
    WRA 2, QY
    WRA 3, QY+1
    CALL rdpt
    WRA 4, QX
    WRA 5, QX+1
    WRA 6, QY
    WRA 7, QY+1
    LD BYT
    @4
    D=D&A
    IFEQ tm_l0
    SET DT, 1
    GOTO tm_ls
tm_l0:
    SET DT, 0
tm_ls:
    WRA 10, DT
    WRK 15, 4
    GOTO tmpl
tm_end:
    RET tmpl

rdb:                         // D = ROM byte at the pointer whose RAM address is in PSEL; that pointer += 1
    @PSEL
    A=M                      // A = address of the pointer variable
    AP                       // A = the pointer's value (a ROM address)
    D=M                      // D = the ROM byte
    @RDV
    M=D                      // keep the byte
    @PSEL
    A=M
    M=M+1                    // pointer.low += 1
    D=M
    @rdb_done
    D;JNE                    // no carry unless the low byte became 0
    @PSEL
    A=M+1                    // A = address of pointer.high
    M=M+1                    // pointer.high += 1
rdb_done:
    @RDV
    D=M                      // D = the byte
    RET rdb

add16:                       // the 16-bit variable at RAM address ADST += (AUH:AUL), mod 2^16; AUH is cleared
    @ADST
    A=M                      // A = address of the variable (low byte)
    D=M                      // D = its low byte
    @AO
    M=D                      // AO = old low byte
    @AUL
    D=D+M                    // D = old + addend low (mod 256)
    @AN
    M=D                      // AN = new low byte
    @AO
    D=M
    @AUL
    D=D&M                    // old & addend
    @AC
    M=D
    @AO
    D=M
    @AUL
    D=D|M                    // old | addend
    @AX
    M=D
    @AN
    D=!M                     // ~new
    @AX
    D=D&M                    // (old | addend) & ~new
    @AC
    D=D|M                    // bit 7 of D is the carry out of the low byte
    @AH
    M=0                      // assume no carry
    @add16_nc
    D;JGE                    // bit 7 clear: no carry
    @AH
    M=1                      // carry
add16_nc:
    @AN
    D=M                      // D = new low byte
    @ADST
    A=M
    M=D                      // store the low byte
    @AUH
    D=M                      // D = addend high
    @AH
    D=D+M                    // D = addend high + carry
    @ADST
    A=M+1                    // A = address of the high byte
    M=D+M                    // high byte += D
    @AUH
    M=0                      // addend high is 0 again for the next caller
    RET add16

getlen:                      // LEN = BYT & 15, or the next stream byte when that is 0; D = LEN
    LD BYT
    @15
    D=D&A
    ST LEN
    IFNE gl_done
    CALL rdb                 // extended length
    ST LEN
gl_done:
    LD LEN
    RET getlen

dpath:                       // lay the path starting at (CX, CY), reading segment bytes at PD
    SET PSEL, PD
    CALL rdb
    ST BYT
    CALL getlen
    IFNE dp_go
    RET dpath                // no path
dp_go:
    LD BYT                   // first segment: via bit = start layer
    @64
    D=D&A
    IFEQ dp_l0
    SET LAYER, 1
    GOTO dp_lset
dp_l0:
    SET LAYER, 0
dp_lset:
    WRA 10, LAYER
dp_seg:                      // BYT, LEN describe the segment that starts at (CX, CY)
    WRA 0, CX                // A = current point
    WRA 1, CX+1
    WRA 2, CY
    WRA 3, CY+1
    LD BYT
    @48
    D=D&A                    // direction * 16
    IFEQ dp_r
    @16
    D=D-A
    IFEQ dp_l
    @16
    D=D-A
    IFEQ dp_d
    // 3: -y
    LD LEN
    D=-D
    ST AUL
    SET AUH, 255
    SET ADST, CY
    CALL add16
    GOTO dp_emit
dp_r:                        // 0: +x
    LD LEN
    ST AUL
    SET ADST, CX
    CALL add16
    GOTO dp_emit
dp_l:                        // 1: -x
    LD LEN
    D=-D
    ST AUL
    SET AUH, 255
    SET ADST, CX
    CALL add16
    GOTO dp_emit
dp_d:                        // 2: +y
    LD LEN
    ST AUL
    SET ADST, CY
    CALL add16
dp_emit:
    WRA 4, CX                // B = new point
    WRA 5, CX+1
    WRA 6, CY
    WRA 7, CY+1
    WRK 15, 4                // TRACK
    LD BYT
    IFLT dp_done             // bit 7: last segment
    SET PSEL, PD
    CALL rdb
    ST BYT
    CALL getlen
    LD BYT
    @64
    D=D&A
    IFEQ dp_seg              // no via
    WRA 0, CX                // VIA at the current point
    WRA 1, CX+1
    WRA 2, CY
    WRA 3, CY+1
    WRK 15, 5
    LD LAYER                 // toggle the layer
    IFEQ dp_to1
    SET LAYER, 0
    GOTO dp_tset
dp_to1:
    SET LAYER, 1
dp_tset:
    WRA 10, LAYER
    GOTO dp_seg
dp_done:
    RET dpath


rd8:                         // (QX,QY) = (OX,OY) + two unsigned bytes from the stream at TP; D = first byte (flag use)
    SET PSEL, TP
    CALL rdb
    ST AUL
    COPY16 QX, OX
    SET ADST, QX
    CALL add16
    CALL rdb
    ST AUL
    COPY16 QY, OY
    SET ADST, QY
    CALL add16
    RET rd8

tile:                        // replicate the stored tile at origin (OX,OY); TP points at t_tile
    SET PSEL, TP
    CALL rdb
    ST CNT5
ti_pl:
    SET PSEL, TP
    CALL rdb                 // x | kind << 7
    ST DT
    @127
    D=D&A
    ST AUL
    COPY16 QX, OX
    SET ADST, QX
    CALL add16
    CALL rdb
    ST AUL
    COPY16 QY, OY
    SET ADST, QY
    CALL add16
    LD DT
    IFGE ti_k0
    SET DT, 1
    GOTO ti_pe
ti_k0:
    SET DT, 0
ti_pe:
    WRA 0, QX
    WRA 1, QX+1
    WRA 2, QY
    WRA 3, QY+1
    WRA 8, DT
    WRK 9, 0
    WRK 10, 0
    WRK 15, 1
    @CNT5
    M=M-1
    D=M
    IFNE ti_pl
ti_tr:                       // trails until 255
    SET PSEL, TP
    CALL rdb
    D=D+1
    IFEQ ti_vias
    D=D-1
    ST AUL
    COPY16 QX, OX
    SET ADST, QX
    CALL add16
    CALL rdb
    ST AUL
    COPY16 QY, OY
    SET ADST, QY
    CALL add16
    CALL dpath
    GOTO ti_tr
ti_vias:
    SET PSEL, TP
    CALL rdb
    ST CNT5
    IFEQ ti_end
ti_v:
    CALL rd8
    WRA 0, QX
    WRA 1, QX+1
    WRA 2, QY
    WRA 3, QY+1
    WRK 15, 5
    @CNT5
    M=M-1
    D=M
    IFNE ti_v
ti_end:
    RET gx

// prog.asm -- plane emitter as glue-VM bytecode
prog:
    SETW LXG, XG
    SETW OX, XB-1
    SETW OY, INVY
    SETB CNT, 14
p_inv:
    SETW TP, t_inv
    TMPLV
    ADDW OX, 4
    DJNZ CNT, p_inv
    SETW CXV, XB
    SETB CNT, 14
p_bus:
    CPYW P0X, CXV
    ADDW P0X, 65535
    SETW P0Y, 3
    CPYW P1X, P0X
    SETW P1Y, TOPB
    EMT 1
    CPYW P0X, CXV
    ADDW P0X, 1
    SETW P0Y, 2
    CPYW P1X, P0X
    EMT 1
    ADDW CXV, 4
    DJNZ CNT, p_bus
    SETW LY0, 6
    SETW CXV, X0-1
    SETB V, 0
p_lo:
    SETW LBX, XB
    CALLG line
    SETW P0X, XG+45
    CPYW P0Y, LY0
    CPYW P1X, CXV
    CPYW P1Y, LY0
    EMT 0
    CPYW P0X, P1X
    CPYW P0Y, P1Y
    EMV
    SETW P1Y, TOPLO
    EMT 1
    ADDW LY0, 8
    ADDW CXV, 8
    INCB V
    JNEB V, 128, p_lo
    SETW DP, ROM_BASE
    SETW BY, BASE0
    SETB SV, 0
p_st:
    CPYW LY0, BY
    ADDW LY0, 65535
    CPYB V, SV
    SETW LBX, XB+28
    CALLG line
    SETW P0X, XG+45
    CPYW P0Y, LY0
    SETW P1X, LASTX
    CPYW P1Y, LY0
    EMT 0
    SETW CXV, X0
    SETB CNT2, 0
p_col:
    RDD V
    SKB V
    CALLG cellb
    CPYW LYV, BY
    ADDW LYV, 9
    SETB MSK, 1
    SETB CNT3, 8
p_lane:
    SETW TP, t_pass
    SKZ V, MSK
    SETW TP, t_gad
    CPYW OX, CXV
    CPYW OY, LYV
    TMPLV
    ADDW LYV, 5
    DBLB MSK
    DJNZ CNT3, p_lane
    ADDW CXV, 8
    INCB CNT2
    JNEB CNT2, 128, p_col
    CPYW LYV, BY
    ADDW LYV, 9
    SETW OX, 0
    SETB CNT3, 8
p_cn:
    SETW P0X, LASTX+7
    CPYW P0Y, LYV
    CPYW P1X, OX
    ADDW P1X, XEND
    CPYW P1Y, LYV
    EMT 0
    JNEB SV, NSTRIP-1, p_cn2
    JMPG p_cn3
p_cn2:
    CPYW OY, LYV
    SETW TP, t_conn
    TMPLV
    CPYW P0X, OX
    ADDW P0X, 2
    CPYW P0Y, LYV
    ADDW P0Y, SH
    SETW P1X, X0-1
    CPYW P1Y, P0Y
    EMT 0
p_cn3:
    ADDW OX, 2
    ADDW LYV, 5
    DJNZ CNT3, p_cn
    ADDW BY, SH
    INCB SV
    JNEB SV, NRUN, p_st
    END
cellb:
    CPYW OX, CXV
    CPYW OY, BY
    TMPL t_cell
    END
line:
    CPYW XK, LXG
    SETB KK, 0
    SETB MSK, 1
l_loop:
    JNEB KK, 0, l_k
    CPYW LB2, LBX
    SETB VM, 1
    SETB CNT4, 0
    CALLG lit
    CPYW LB2, LBX
    ADDW LB2, 4
    SETB VM, 2
    SETB CNT4, 2
    CALLG lit
    SETW TP, t_stg0
    JMPG l_t
l_k:
    CPYW LB2, LBX
    ADDW LB2, 4
    CPYB VM, MSK
    DBLB VM
    CPYB CNT4, KK
    ADDB CNT4, 2
    CALLG lit
    SETW TP, t_stg1
l_t:
    CPYW OX, XK
    CPYW OY, LY0
    TMPLV
    ADDW XK, 8
    ADDW LBX, 4
    DBLB MSK
    INCB KK
    JNEB KK, 6, l_loop
    END
lit:
    CPYW P0X, LB2
    ADDW P0X, 1
    SKZ V, VM
    ADDW P0X, 65534
    CPYW P0Y, LY0
    ADDWV P0Y, CNT4
    EMV
    CPYW P1X, XK
    CPYW P1Y, P0Y
    EMT 0
    JNEB CNT4, 0, lit2
    END
lit2:
    CPYW P0X, XK
    CPYW P0Y, P1Y
    CPYW P1Y, LY0
    ADDW P1Y, 1
    EMT 0
    END

// prog_ram.asm -- RAM block emitter (bytecode)
.equ RXB, 4
.equ RXG, 36
.equ RXBUS, 92
.equ RTX0, 116
.equ RTY0, 12
.equ RTH, 57
.equ RTOP, 7262
.equ RBOT, 7291
.equ RDOUT, 0
rprog:
    SETW LXG, RXG
    SETW RTX0V, RTX0
    SETW OX, RXB-1
    SETW OY, INVY
    SETB CNT, 7
r_inv:
    SETW TP, t_inv
    TMPLV
    ADDW OX, 4
    DJNZ CNT, r_inv
    SETW CXV, RXB
    SETB CNT, 7
r_bus:
    CPYW P0X, CXV
    ADDW P0X, 65535
    SETW P0Y, 3
    CPYW P1X, P0X
    SETW P1Y, RTOP
    EMT 1
    CPYW P0X, CXV
    ADDW P0X, 1
    SETW P0Y, 2
    CPYW P1X, P0X
    EMT 1
    ADDW CXV, 4
    DJNZ CNT, r_bus
    SETW CXV, RXBUS
    SETB CNT, 9
r_db:
    CPYW P0X, CXV
    SETW P0Y, RTY0-1
    CPYW P1X, CXV
    SETW P1Y, RBOT
    EMT 1
    ADDW CXV, 2
    DJNZ CNT, r_db
    SETW OX, RTX0
    SETW OY, RTY0
    TMPL t_rtie
    SETW TYK, RTY0
    SETB V, 0
r_tile:
    CPYW LY0, TYK
    ADDW LY0, 3
    SETW LBX, RXB
    CALLG line
    CPYW OX, RTX0V
    CPYW OY, LY0
    TMPL t_rsel
    CPYW OX, RTX0V
    CPYW OY, TYK
    SETW TP, t_tile
    CALLS tile
    TMPL t_rtap
    JNEB V, 127, r_lk
    TMPL t_rdout
    JMPG r_nx
r_lk:
    TMPL t_rlink
r_nx:
    ADDW TYK, RTH
    INCB V
    JNEB V, 128, r_tile
    END

t_inv:
    .byte 1,0,1,0,0
    .byte 3,0,0,1
    .byte 2,0,0,1,0,0,0
    .byte 2,0,0,0,1,0,0
    .byte 2,0,0,1,1,0,1
    .byte 0
t_cell:
    .byte 1,0,0,0,0
    .byte 2,0,0,255,0,0,0
    .byte 3,255,255,1
    .byte 2,255,255,1,0,0,1
    .byte 2,1,0,0,3,0,0
    .byte 3,3,0,0
    .byte 6,3,0,0,3,0,45
    .byte 0
t_gad:
    .byte 2,255,255,0,0,0,0
    .byte 2,255,255,0,255,255,1
    .byte 2,255,255,1,0,0,1
    .byte 1,0,0,0,0
    .byte 2,1,0,0,5,0,0
    .byte 3,3,0,1
    .byte 2,3,0,1,5,0,1
    .byte 1,0,5,0,0
    .byte 2,6,0,0,7,0,0
    .byte 0
t_pass:
    .byte 2,255,255,0,7,0,0
    .byte 0
t_conn:
    .byte 3,140,4,0
    .byte 6,140,4,0,140,4,3
    .byte 3,140,4,3
    .byte 2,140,4,3,2,0,3
    .byte 3,2,0,3
    .byte 6,2,0,3,2,0,53
    .byte 3,2,0,53
    .byte 0
t_stg0:
    .byte 1,0,0,0,0
    .byte 2,1,0,0,4,0,0
    .byte 2,3,0,0,3,0,1
    .byte 2,3,0,1,4,0,1
    .byte 1,0,4,0,0
    .byte 0
t_stg1:
    .byte 2,253,255,0,0,0,0
    .byte 1,0,0,0,0
    .byte 2,1,0,0,4,0,0
    .byte 2,3,0,0,3,0,1
    .byte 2,3,0,1,4,0,1
    .byte 1,0,4,0,0
    .byte 0
t_rtap:
    .byte 3,232,255,1
    .byte 2,232,255,1,2,0,1
    .byte 3,234,255,5
    .byte 2,234,255,5,2,0,5
    .byte 3,236,255,6
    .byte 2,236,255,6,2,0,6
    .byte 3,238,255,7
    .byte 2,238,255,7,2,0,7
    .byte 3,240,255,8
    .byte 2,240,255,8,2,0,8
    .byte 3,242,255,9
    .byte 2,242,255,9,2,0,9
    .byte 3,244,255,10
    .byte 2,244,255,10,2,0,10
    .byte 3,246,255,11
    .byte 2,246,255,11,2,0,11
    .byte 3,248,255,12
    .byte 2,248,255,12,2,0,12
    .byte 0
t_rlink:
    .byte 2,17,0,55,17,0,57
    .byte 2,21,0,55,21,0,57
    .byte 2,25,0,55,25,0,57
    .byte 2,29,0,55,29,0,57
    .byte 2,33,0,55,33,0,57
    .byte 2,37,0,55,37,0,57
    .byte 2,41,0,55,41,0,57
    .byte 2,45,0,55,45,0,57
    .byte 0
t_rsel:
    .byte 2,221,255,0,2,0,0
    .byte 0
t_rdout:
    .byte 1,0,17,0,59
    .byte 2,17,0,55,17,0,60
    .byte 1,0,21,0,59
    .byte 2,21,0,55,21,0,60
    .byte 1,0,25,0,59
    .byte 2,25,0,55,25,0,60
    .byte 1,0,29,0,59
    .byte 2,29,0,55,29,0,60
    .byte 1,0,33,0,59
    .byte 2,33,0,55,33,0,60
    .byte 1,0,37,0,59
    .byte 2,37,0,55,37,0,60
    .byte 1,0,41,0,59
    .byte 2,41,0,55,41,0,60
    .byte 1,0,45,0,59
    .byte 2,45,0,55,45,0,60
    .byte 0
t_rtie:
    .byte 1,0,2,0,250
    .byte 2,17,0,252,17,0,0
    .byte 2,21,0,252,21,0,0
    .byte 2,25,0,252,25,0,0
    .byte 2,29,0,252,29,0,0
    .byte 2,33,0,252,33,0,0
    .byte 2,37,0,252,37,0,0
    .byte 2,41,0,252,41,0,0
    .byte 2,45,0,252,45,0,0
    .byte 2,3,0,250,3,0,252
    .byte 2,3,0,252,45,0,252
    .byte 0

t_tile:
    .byte 58
    .byte 12,2
    .byte 17,2
    .byte 140,6
    .byte 17,6
    .byte 22,6
    .byte 27,6
    .byte 32,6
    .byte 37,6
    .byte 42,6
    .byte 140,12
    .byte 17,12
    .byte 22,12
    .byte 27,12
    .byte 32,12
    .byte 37,12
    .byte 42,12
    .byte 140,18
    .byte 17,18
    .byte 22,18
    .byte 27,18
    .byte 32,18
    .byte 37,18
    .byte 42,18
    .byte 140,24
    .byte 17,24
    .byte 22,24
    .byte 27,24
    .byte 32,24
    .byte 37,24
    .byte 42,24
    .byte 140,30
    .byte 17,30
    .byte 22,30
    .byte 27,30
    .byte 32,30
    .byte 37,30
    .byte 42,30
    .byte 140,36
    .byte 17,36
    .byte 22,36
    .byte 27,36
    .byte 32,36
    .byte 37,36
    .byte 42,36
    .byte 140,42
    .byte 17,42
    .byte 22,42
    .byte 27,42
    .byte 32,42
    .byte 37,42
    .byte 42,42
    .byte 140,48
    .byte 17,48
    .byte 22,48
    .byte 27,48
    .byte 32,48
    .byte 37,48
    .byte 42,48
    .byte 2,5,64,20,161
    .byte 2,6,73,36,11,162
    .byte 2,7,72,41,9,34,131
    .byte 2,8,70,47,14,161
    .byte 2,9,69,32,18,12,35,195
    .byte 2,10,68,32,25,13,33,195
    .byte 2,11,67,32,30,14,33,195
    .byte 11,19,54,134
    .byte 11,19,32,30,134
    .byte 11,19,134
    .byte 11,25,198
    .byte 11,31,134
    .byte 11,37,134
    .byte 11,43,198
    .byte 12,2,26,177
    .byte 12,3,26,97,0,30,162
    .byte 12,18,51,0,16,163
    .byte 12,24,34,0,16,178
    .byte 12,30,51,0,16,163
    .byte 12,36,51,0,16,163
    .byte 12,42,51,0,16,163
    .byte 13,2,4,161
    .byte 13,24,50,64,17,35,130
    .byte 13,42,34,0,19,177
    .byte 13,48,51,0,18,36,129
    .byte 14,2,171
    .byte 15,2,37,130
    .byte 17,0,67,34,0,17,164
    .byte 18,2,1,37,3,35,2,99,146
    .byte 18,30,50,9,162
    .byte 18,36,50,9,162
    .byte 18,42,50,9,162
    .byte 18,48,50,9,162
    .byte 20,25,17,54,69,50,5,54,149
    .byte 20,25,130
    .byte 20,25,96,24,130
    .byte 21,55,115,64,27,48,35,21,181
    .byte 22,48,17,34,16,19,176,38
    .byte 23,6,33,132
    .byte 23,12,33,132
    .byte 23,18,33,132
    .byte 23,24,33,132
    .byte 25,55,116,4,48,28,78,181
    .byte 27,24,49,22,33,211
    .byte 29,0,67,33,7,32,22,18,161
    .byte 29,55,65,48,26,77,181
    .byte 31,30,18,54,3,116,17,56,17,184
    .byte 31,30,129
    .byte 31,30,96,18,129
    .byte 32,7,2,50,114,16,16,97,17,34,212
    .byte 32,13,17,50,30,97,148
    .byte 32,19,18,98,16,16,51,145
    .byte 32,31,19,33,29,114,147
    .byte 32,37,19,33,29,114,147
    .byte 33,18,33,132
    .byte 33,24,33,132
    .byte 33,30,33,132
    .byte 33,36,33,132
    .byte 33,42,33,132
    .byte 33,48,33,132
    .byte 33,55,115,1,48,19,9,179
    .byte 37,18,18,62,23,52,147
    .byte 37,36,51,10,112,31,90,178
    .byte 37,55,81,48,16,7,179
    .byte 38,6,4,161
    .byte 38,12,4,161
    .byte 38,18,4,161
    .byte 38,24,4,161
    .byte 38,30,4,161
    .byte 38,36,4,161
    .byte 38,42,4,161
    .byte 41,0,67,32,41,23,161
    .byte 41,55,81,53,115,3,181
    .byte 43,6,37,6,32,43,16,32,161
    .byte 45,0,65,32,45,25,163
    .byte 45,55,82,183
    .byte 12,6,99,0,16,179
    .byte 12,12,99,0,16,179
    .byte 12,48,98,0,16,178
    .byte 13,24,196
    .byte 13,42,196
    .byte 13,48,196
    .byte 14,18,195
    .byte 16,30,193
    .byte 16,36,193
    .byte 18,6,98,8,50,129
    .byte 18,12,98,8,50,129
    .byte 18,18,98,8,50,129
    .byte 20,31,194
    .byte 20,37,194
    .byte 20,43,194
    .byte 21,0,3,37,7,100,6,163
    .byte 23,30,97,132
    .byte 23,36,97,132
    .byte 23,42,97,132
    .byte 23,48,97,132
    .byte 31,12,193
    .byte 31,18,193
    .byte 31,36,193
    .byte 31,42,193
    .byte 33,0,35,7,96,24,19,163
    .byte 33,6,67,33,129
    .byte 33,12,67,33,129
    .byte 38,48,68,161
    .byte 255
    .byte 29
    .byte 2,1
    .byte 2,5
    .byte 2,6
    .byte 2,7
    .byte 2,8
    .byte 2,9
    .byte 2,10
    .byte 2,11
    .byte 2,12
    .byte 11,25
    .byte 11,43
    .byte 17,0
    .byte 17,55
    .byte 20,25
    .byte 21,0
    .byte 21,55
    .byte 25,0
    .byte 25,55
    .byte 29,0
    .byte 29,55
    .byte 31,30
    .byte 33,0
    .byte 33,55
    .byte 37,0
    .byte 37,55
    .byte 41,0
    .byte 41,55
    .byte 45,0
    .byte 45,55
