// prog.asm -- plane emitter as glue-VM bytecode
prog:
    SETXP LXG, XG
    SETXP OX, XB-1
    SETYP OY, INVY
    SETB CNT, 14
p_inv:
    SETW TP, t_inv
    TMPLV
    ADDW OX, 4
    DJNZ CNT, p_inv
    SETXP CXV, XB
    SETB CNT, 14
p_bus:
    CPYW P0X, CXV
    ADDW P0X, 65535
    SETYP P0Y, 3
    CPYW P1X, P0X
    SETYP P1Y, TOPB
    EMT 1
    CPYW P0X, CXV
    ADDW P0X, 1
    SETYP P0Y, 2
    CPYW P1X, P0X
    EMT 1
    ADDW CXV, 4
    DJNZ CNT, p_bus
    SETYP LY0, 6
    SETXP CXV, X0-1
    SETB V, 0
p_lo:
    SETXP LBX, XB
    CALLG line
    SETXP P0X, XG+45
    CPYW P0Y, LY0
    CPYW P1X, CXV
    CPYW P1Y, LY0
    EMT 0
    CPYW P0X, P1X
    CPYW P0Y, P1Y
    EMV
    SETYP P1Y, TOPLO
    EMT 1
    ADDW LY0, 8
    ADDW CXV, 8
    INCB V
    JNEB V, 128, p_lo
    SETW DP, ROM_BASE
    SETYP BY, BASE0
    SETB SV, 0
p_st:
    CPYW LY0, BY
    ADDW LY0, 65535
    CPYB V, SV
    SETXP LBX, XB+28
    CALLG line
    SETXP P0X, XG+45
    CPYW P0Y, LY0
    SETXP P1X, LASTX
    CPYW P1Y, LY0
    EMT 0
    SETXP CXV, X0
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
    SETXP OX, 0
    SETB CNT3, 8
p_cn:
    SETXP P0X, LASTX+7
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
    SETXP P1X, X0-1
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
