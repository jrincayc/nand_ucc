// memmap_imp.s -- RAM map of the module improver (kernels/improve.s).  Small byte arrays, signals < 64.
.equ IM_NIN,   0x200
.equ IM_NG,    0x204
.equ IM_NO,    0x208
.equ IM_ROOT,  0x20C
.equ IM_NCUT,  0x210
.equ IM_SAVED, 0x214
.equ IM_K,     0x218
.equ IM_F,     0x21C
.equ IM_FULL,  0x220
.equ IM_N,     0x224
.equ IM_NS,    0x228
.equ IM_GMAX,  0x22C
.equ IM_S,     0x230
.equ IM_REAL,  0x234
.equ IM_RES,   0x238
.equ IM_GI,    0x23C
.equ IM_CI,    0x240
.equ IM_NENT,  0x244
.equ IM_CNT,   0x248
.equ SLA,   0x1600   // input slots: a (0xFF = hole)
.equ SLB,   0x1640
.equ SOUT,  0x1680   // input outputs (pinned slots)
.equ RNA,   0x1700   // result slots
.equ RNB,   0x1740
.equ ROUT,  0x1780
.equ GA,    0x1000
.equ GB,    0x1040
.equ OUTS,  0x1080   // 2 bytes
.equ FO,    0x1100
.equ INNER, 0x1140
.equ CONE,  0x1180
.equ LEAFF, 0x11C0
.equ VAL,   0x1200
.equ CK,    0x1300   // u32[32]
.equ LV,    0x1380
.equ BASE,  0x1390
.equ SIG,   0x13A0
.equ PROG,  0x13C0
.equ JJ,    0x13E0
.equ II,    0x13F0
.equ NGA,   0x1400
.equ NGB,   0x1440
.equ PA,    0x1480
.equ PB,    0x14C0
.equ POUT,  0x1500
.equ IORD,   0x1510
.equ PREN,  0x1550
.equ REM,   0x1800
.equ LIVE,  0x1840
.equ KMN,   0x1880
.equ KMX,   0x18C0
.equ DUP,   0x1900
.equ REN,   0x1940
.equ ITL,    0x1980
.equ SOF,   0x19C0
.equ FREE,  0x1A00
.equ STK,   0x2000   // 256 bytes
.equ SWTOP, 0x1F00   // software stack (grows down)
