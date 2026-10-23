// memmap_route.s -- RAM map of the routing kernels (after the placement kernels are done: FINAL = placement order is the only placement result kept).
// Inputs written by the packer / reader before the run:
//   SRC    u16[2N]  source of input p of gate k at SRC[2k+p]: gate n, N+j = ROM data bit j, N+8+c = RAM data-out bit c, 0xFFFF open; bits 14-15 = late (0, 1, 2)
//   KINDA  u8[N]    0 = NAND, 1 = DFF
//   PTAB   u16[3*NP] per port read: part (0 rom, 1 arm, 2 ram) | side << 8 (1 = right-hand pin), pin number a, source (as in SRC; gate nets only)
//   V_N, V_NP, RV_ROMB (ROM address bits), RV_RAMB (RAM address bits), RV_OX, RV_OY (offset added to every coordinate)
.equ R_ROWS,   22
.equ R_ZONEW,  14
.equ PTAB,   0x2C000
.equ KINDA,  0x2A800
.equ ROWA,   0x01000   // u8[N]    row of the gate
.equ COLA,   0x02000   // u16[N]   logical column of the gate
.equ NOFF,   0x04000   // u16[NN+1]  start of the sink list of every net (NN = N + 16)
.equ NSNK,   0x06200   // u16[<=8192] sink records: gate input 2k+p (< 0x8000) or 0x8000 + port number
.equ ZONE,   0x0A200   // u8[NN]
.equ LIDX,   0x0B300   // u8[NN]   lane index in the zone, 255 = none
.equ GXT,    0x0C400   // u16[cols] x of gate column j
.equ IVS,    0x0C600   // u16[NN+1] first interval of the net
.equ IVROW,  0x0E800   // u8[6144]
.equ IVLO,   0x10000   // u16[6144]
.equ IVHI,   0x13000   // u16[6144]
.equ IVTRK,  0x16000   // u8[6144]
.equ RTAB,   0x17800   // small tables, see below
.equ ZWT,    0x17800   // u8[16] lane count (width) of every zone
.equ ZXB,    0x17810   // u16[16] x of the first lane of every zone
.equ ZCNT,   0x17830   // u8[16]
.equ YT,     0x17840   // u16[32] y baseline of every row
.equ TT,     0x17880   // u16[32] number of tracks of every row
.equ RLO,    0x178C0   // u16[32] per-row minimum (zone anchors / columns)
.equ RHI,    0x17900   // u16[32] per-row maximum
.equ RTCH,   0x17940   // u8[32]  rows touched
.equ TLO,    0x17960   // u16[32] trunk low per row
.equ THI,    0x179A0   // u16[32] trunk high per row
.equ TYT,    0x179E0   // u16[32] y of the trunk of the net in each row
.equ STUB,   0x17A20   // 3 x (x, yrel, layer) of the pin being handled: 3 x 6 bytes
.equ KEYS,   0x18000   // u32[1024] emission sort keys
.equ KREC,   0x19000   // u16[1024] sink records, sorted together with KEYS
.equ QUEUE,  0x1A000   // late command queue: 12 bytes per command (type, a, b, c, d, e)
.equ QMAX,   2000
// stage temporaries
.equ CMIN,   0x2D000   // u8[NN]
.equ CMAX,   0x2E100   // u8[NN]
.equ NFILL,  0x2F200   // u16[NN]
.equ LNET,   0x31200   // u16[NN] nets that need a lane
.equ BCNT,   0x20000   // u16[nz*R*R+1] bucket counters (up to 0x26000)
.equ SORTED, 0x35000   // u16[NN]
.equ LEND,   0x37000   // u8[16*128]
.equ ORDA,   0x35000   // u16[NI]  (track stage; overlays SORTED/LEND)
.equ ORDB,   0x38000   // u16[NI]
.equ CNTA,   0x3B000   // u16[W+2]
.equ ENDS,   0x3C000   // u16[256]
// variables
.equ RV_COLS,  0x100
.equ RV_NZ,    0x104
.equ RV_PBLR,  0x108
.equ RV_PBLA,  0x10C
.equ RV_PBLM,  0x110
.equ RV_NLN,   0x114
.equ RV_XR,    0x118
.equ RV_XA,    0x11C
.equ RV_XM,    0x120
.equ RV_W,     0x124
.equ RV_NI,    0x128
.equ RV_H,     0x12C
.equ RV_ROMB,  0x130
.equ RV_RAMB,  0x134
.equ RV_OX,    0x138
.equ RV_OY,    0x13C
.equ RV_NSINK, 0x140
.equ RV_T0,    0x150
.equ RV_T1,    0x154
.equ RV_T2,    0x158
.equ RV_T3,    0x15C
.equ RV_T4,    0x160
.equ RV_T5,    0x164
.equ RV_T6,    0x168
.equ RV_T7,    0x16C
.equ RV_T8,    0x170
.equ RV_T9,    0x174
.equ RV_LINKR, 0x178
// ---- stage 3 (emission) variables and tables
.equ RV_DROW, 0x180
.equ RV_DCOL, 0x184
.equ RV_DY,   0x188
.equ RV_LANE, 0x18C
.equ RV_FIRST,0x190
.equ RV_SPLO, 0x194
.equ RV_SPHI, 0x198
.equ RV_SPAN, 0x19C
.equ RV_LATE, 0x1A0
.equ RV_PN,   0x1A4
.equ RV_Q1N,  0x1A8
.equ RV_Q2N,  0x1AC
.equ RV_NK,   0x1B0
.equ RV_DN,   0x1B4
.equ RV_NET,  0x1B8
.equ RV_SI,   0x1BC
.equ RV_ROW,  0x1C0
.equ RV_COL,  0x1C4
.equ RV_REC,  0x1C8
.equ RV_T5B,  0x1CC
.equ PTS,     0x17B00   // 32 points x 6 bytes (x, y, layer as u16)
.equ DST,     0x17BC0   // up to 3 driver stub points, same format
.equ Q1,      0x1A000   // late queue 1 (1000 x 12 bytes)
.equ Q2,      0x1D000   // late queue 2
.equ QCAP,    1000
.equ ARMB,    0x3FFF0   // arm register window
.equ RV_NPORT, 0x144   // number of ports (PTAB records); V_NP is the placement's count of gate-reading ports
