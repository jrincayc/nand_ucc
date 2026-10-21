// ram_c.asm -- RAM map of the compact R2 builder (128 bytes).  16-bit variables: low byte first.
.equ PSEL,   0               // address of the pointer variable rdb reads through
.equ RDV,    1               // rdb: the byte just read
.equ ADST,   2               // add16: address of the destination variable
.equ AUL,    3               // add16: addend low
.equ AUH,    4               // add16: addend high (0 between calls)
.equ AO,     5               // add16 scratch
.equ AN,     6
.equ AC,     7
.equ AX,     8
.equ AH,     9
.equ DT,     10              // DBL scratch (unused, kept for macros.asm)
.equ P,      12              // ROM read pointer (copy loop) (2)
.equ CA,     14              // ROM copy offset (2)
.equ KP,     16              // exception list pointer (2)
.equ PD,     18              // path stream pointer (2)
.equ TP,     20              // table pointer (ports, RUN) (2)
.equ SX,     22              // site x (2)
.equ SY,     24              // site y (2)
.equ CX,     26              // current point x (2)
.equ CY,     28              // current point y (2)
.equ ROWL,   30              // rows left
.equ COLL,   31              // columns left
.equ SKIPL,  32              // plain NAND sites left before the next exception
.equ NEXTK,  33              // kind of that exception
.equ KINDV,  34              // kind of the current site: 0 NAND, 1 DFF, 2 empty
.equ BYT,    35              // current segment byte
.equ LEN,    36              // current segment length
.equ LAYER,  37              // layer of the path being laid
.equ NP,     38              // counter
// return addresses (2 bytes each)
.equ RA_rdb,      40
.equ RA_add16,    42
.equ RA_sitekind, 44
.equ RA_getlen,   46
.equ RA_dpath,    48
.equ RA_kinit,    50
.equ RA_tabpt,    52
// 54..127 free
