// memmap.s -- RAM map shared by the placement kernels (RAM 0x00000-0x3FFFF; 0x00-0x4F registers, 0x50-0xFF kernel variables; arm window 0x3FFF0 at the top).
// Vertex count limit NVMAX = 4080 (u16 indices, LNEXT stops 16 bytes short of the arm window); directed edge limit 20480.
.equ OFF,    0x01000   // u16[NV+1]  CSR offsets
.equ LAB,    0x03000   // u16[NV]    LPA labels; after contraction: group number of every vertex (in place)
.equ VSZ,    0x05000   // u16[NV]    vertex sizes (number of gates in the vertex)
.equ SIZE,   0x07000   // u16[NV]    LPA group sizes;  build_graph: SEG;  contraction: GIDL
.equ ORD,    0x09000   // u16[NV]    LPA vertex order; contraction: GCNT;  build_graph: PIN (to 0x12000)
.equ TL,     0x0B000   // u16[NV]    LPA touched labels; contraction: MEM
.equ VOTES,  0x0D000   // u32[NV]    LPA votes; contraction: TSEG (0xD000) and TLEN (0xF000)
.equ NBR,    0x12000   // u16[20480]
.equ WT,     0x1C000   // u16[20480]
.equ TNBR,   0x26000   // u16[20480] contraction temporary lists (also chain scratch, build_graph inputs)
.equ TWT,    0x30000   // u16[20480]
.equ LHEAD,  0x3A000   // u16[NV]    first gate (leaf) of the vertex' leaf list
.equ LTAIL,  0x3C000   // u16[NV]    last gate of the vertex' leaf list
.equ LNEXT,  0x3E000   // u16[N+1]   next gate in the leaf list
.equ WTD,    0xA000    // WT - NBR  and  TWT - TNBR
.equ GIDL,   0x07000
.equ GCNT,   0x09000
.equ MEM,    0x0B000
.equ TSEG,   0x0D000
.equ TLEN,   0x0F000
// chain scratch (inside TNBR/TWT, which are free while chaining)
.equ CTOT,   0x26000   // u32[m]
.equ CSC,    0x2A000   // u32[m]
.equ CVIS,   0x2E000   // u8[m]
.equ CTL,    0x2F000   // u16[m] touched list
.equ COUT,   0x31000   // u16[m] chain order (item indices)
.equ FINAL,  0x33000   // u16[N+1] final leaf order
.equ IDX,    0x07000   // u16[NV] vertex -> position in the item list (0xFFFF = not an item); shares SIZE/GIDL: initialised by the caller before chaining
// build_graph inputs and temporaries (inside TNBR/TWT)
.equ SRC,    0x26000
.equ PSRC,   0x2A000
.equ POFF,   0x2A400
.equ FP,     0x2C400
.equ LASTK,  0x2E400
.equ ANCH,   0x30400
.equ SEG,    0x07000
.equ LEN,    0x03000
.equ PIN,    0x09000
// variables
.equ V_RNG,   0x50
.equ V_NV,    0x54
.equ V_CAP,   0x58
.equ V_SW,    0x5C
.equ V_MOVED, 0x60
.equ V_LINK,  0x64
.equ V_N,     0x68
.equ V_NP,    0x6C
.equ V_ERR,   0x70
.equ V_NN,    0x74
.equ WTAB,    0x80
.equ V_NG,    0x90
.equ V_LV,    0x94
.equ V_M,     0x98
.equ V_SV,    0x9C
.equ V_OUT,   0xA0
.equ V_T0,    0xA4
.equ V_T1,    0xA8
.equ V_T2,    0xAC
.equ V_T3,    0xB0
.equ V_T4,    0xB4
