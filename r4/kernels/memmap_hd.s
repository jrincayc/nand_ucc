// memmap_hd.s -- RAM map of the HD kernels (kernels/hdflat.s).  Module table (unpacked records), body bases, variables.
.equ MT,    0x400     // 8 modules x 192 bytes:  +0 n_in  +1 n_out  +2 n_slots  +3 n_nodes  +4,+5 output signals  +6,+7 node offset of the outputs
.equ MTB,   192       //                         +8 SA[56]  +64 SB[56] (0xFF = hole)  +120 RK[56] (node offset of the slot)
.equ NBASE, 0x8000    // u16[4096] first node number of every body instance
.equ BTYP,  0xA000    // u8[4096]  type of every body instance
.equ RECBUF,0xA00     // encoded record (mt_encode)
.equ FV_M,   0x300
.equ FV_TYPE,0x304
.equ FV_NR,  0x308
.equ FV_I,   0x30C
.equ FV_IR,  0x340    // 4 resolved input references of the instance being expanded
.equ MODIMG, 0xC00    // the module records of the child (all modules, fixed offsets), built by build_modimg
.equ CHILD_GAP, 8
