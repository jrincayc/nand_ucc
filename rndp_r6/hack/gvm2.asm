// gvm.asm -- glue VM: variable-length ops: opcode byte = 4*id + nargs, then nargs argument bytes; variables are RAM byte addresses
.macro END
    .byte 0
.endm
.macro SETW v k
    .byte 7,\v,lo(\k),hi(\k)
.endm
.macro CPYW d s
    .byte 10,\d,\s
.endm
.macro ADDW v k
    .byte 15,\v,lo(\k),hi(\k)
.endm
.macro SETB v k
    .byte 18,\v,\k
.endm
.macro TMPL t
    .byte 22,lo(\t),hi(\t)
.endm
.macro EMT l
    .byte 25,\l
.endm
.macro EMV
    .byte 28
.endm
.macro CALLG t
    .byte 34,lo(\t),hi(\t)
.endm
.macro DJNZ v t
    .byte 39,\v,lo(\t),hi(\t)
.endm
.macro CMPB v k
    .byte 42,\v,\k
.endm
.macro JNZG t
    .byte 46,lo(\t),hi(\t)
.endm
.macro JNEB v k t
    CMPB \v,\k
    JNZG \t
.endm
.macro INCB v
    .byte 49,\v
.endm
.macro SKZ v m
    .byte 54,\v,\m
.endm
.macro SKB v
    .byte 57,\v
.endm
.macro DBLB v
    .byte 61,\v
.endm
.macro RDD v
    .byte 65,\v
.endm
.macro CPYB d s
    .byte 70,\d,\s
.endm
.macro TMPLV
    .byte 72
.endm
.macro JMPG t
    .byte 78,lo(\t),hi(\t)
.endm
.macro ADDB v k
    .byte 82,\v,\k
.endm
.macro ADDWV v s
    .byte 86,\v,\s
.endm
.macro CALLS t
    .byte 90,lo(\t),hi(\t)
.endm

gb:                          // next bytecode byte -> RAM[PW++]
    SET PSEL, GP
    CALL rdb
    PUT PW
    RET gb

gvm:                         // run the bytecode at GP until the top-level END
    SET SPG, GST
    SET SKP, 0
gv_loop:
    SET PW, OPC
    CALL gb
    LD OPC
    @3
    D=D&A
    ST NARG
    SET PW, A1
gv_ar:
    LD NARG
    IFEQ gv_run
    CALL gb
    @NARG
    M=M-1
    GOTO gv_ar
gv_run:
    LD SKP
    IFEQ gv_ex
    SET SKP, 0
    GOTO gv_loop
gv_ex:
    LD OPC
    @252
    D=D&A
    IFEQ gv_end
    @4
    D=D-A
    IFEQ gv_setw
    @4
    D=D-A
    IFEQ gv_cpyw
    @4
    D=D-A
    IFEQ gv_addw
    @4
    D=D-A
    IFEQ gv_setb
    @4
    D=D-A
    IFEQ gv_tmpl
    @4
    D=D-A
    IFEQ gv_emt
    @4
    D=D-A
    IFEQ gv_emv
    @4
    D=D-A
    IFEQ gv_callg
    @4
    D=D-A
    IFEQ gv_djnz
    @4
    D=D-A
    IFEQ gv_cmpb
    @4
    D=D-A
    IFEQ gv_jnz
    @4
    D=D-A
    IFEQ gv_incb
    @4
    D=D-A
    IFEQ gv_skz
    @4
    D=D-A
    IFEQ gv_skb
    @4
    D=D-A
    IFEQ gv_dblb
    @4
    D=D-A
    IFEQ gv_rdd
    @4
    D=D-A
    IFEQ gv_cpyb
    @4
    D=D-A
    IFEQ gv_tmplv
    @4
    D=D-A
    IFEQ gv_jmp
    @4
    D=D-A
    IFEQ gv_addb
    @4
    D=D-A
    IFEQ gv_addwv
    SET16 RA_gx, gv_loop     // CALLS: asm subroutine at A1:A2, returns via RET gx
    @A1
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
    LD A1
    ST TP
    LD A2
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
    LD A1
    ST GP
    LD A2
    ST GP+1
    GOTO gv_loop
gv_djnz:
    @A1
    A=M
    M=M-1
    D=M
    IFEQ gv_loop
    LD A2
    ST GP
    LD A3
    ST GP+1
    GOTO gv_loop
gv_cmpb:
    @A1
    A=M
    D=M
    @A2
    D=D-M
    ST FLG
    GOTO gv_loop
gv_jnz:
    LD FLG
    IFNE gv_jmp
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
    SET SKP, 1
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
    SET AUH, 0
    LD AUL
    IFGE gv_aw
    SET AUH, 255
gv_aw:
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
