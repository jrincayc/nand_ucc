rds:                         // D = next path-stream byte: raw (HM = 0) or canonical-Huffman decoded (HM != 0); stream pointer PD
    LD HM
    IFNE rds_h
    SET PSEL, PD
    CALL rdb
    RET rds
rds_h:
    CALL rdh
    RET rds

rdh:                         // one symbol: d = 2d + bit; if d < count[len] the symbol is hsym[idx + d], else idx += count, d -= count
    SET HD, 0
    SET HI, 0
    SET16 CP, hcnt
rh_l:
    LD HN
    IFNE rh_have
    SET PSEL, PD
    CALL rdb
    ST HB
    SET HN, 8
rh_have:
    @HN
    M=M-1
    LD HD
    DBL
    ST HD
    LD HB
    IFGE rh_z
    @HD
    M=M+1
rh_z:
    LD HB
    DBL
    ST HB
    SET PSEL, CP
    CALL rdb
    ST HC
    LD HD
    @HC
    D=D-M
    IFLT rh_f
    ST HD
    LD HI
    @HC
    D=D+M
    ST HI
    GOTO rh_l
rh_f:
    SET16 SP, hsym
    LD HI
    @HD
    D=D+M
    ST AUL
    SET ADST, SP
    CALL add16
    SET PSEL, SP
    CALL rdb
    RET rdh
