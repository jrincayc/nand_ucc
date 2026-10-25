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
