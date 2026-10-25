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
    SETXR LXG, RXG
    SETXR RTX0V, RTX0
    SETXR OX, RXB-1
    SETYR OY, INVY
    SETB CNT, 7
r_inv:
    SETW TP, t_inv
    TMPLV
    ADDW OX, 4
    DJNZ CNT, r_inv
    SETXR CXV, RXB
    SETB CNT, 7
r_bus:
    CPYW P0X, CXV
    ADDW P0X, 65535
    SETYR P0Y, 3
    CPYW P1X, P0X
    SETYR P1Y, RTOP
    EMT 1
    CPYW P0X, CXV
    ADDW P0X, 1
    SETYR P0Y, 2
    CPYW P1X, P0X
    EMT 1
    ADDW CXV, 4
    DJNZ CNT, r_bus
    SETXR CXV, RXBUS
    SETB CNT, 9
r_db:
    CPYW P0X, CXV
    SETYR P0Y, RTY0-1
    CPYW P1X, CXV
    SETYR P1Y, RBOT
    EMT 1
    ADDW CXV, 2
    DJNZ CNT, r_db
    SETXR OX, RTX0
    SETYR OY, RTY0
    TMPL t_rtie
    SETYR TYK, RTY0
    SETB V, 0
r_tile:
    CPYW LY0, TYK
    ADDW LY0, 3
    SETXR LBX, RXB
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
