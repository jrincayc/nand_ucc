// demo.asm -- style example and M2 test program for asm.py / trace_check.py.
// Sums 10+9+...+1 into RAM[SUM], copies a 3-byte table through a pointer with AP, then halts.
.equ SUM, 0x10          // RAM byte holding the running sum
.equ CNT, 0x11          // RAM byte holding the loop counter
.equ OUT, 0x12          // RAM bytes 0x12..0x14 receive the table copy

.macro LDD addr         // D = RAM[addr]
    @\addr              // A = address of the variable
    D=M                 // D = its value
.endm

.macro STD addr         // RAM[addr] = D
    @\addr              // A = address of the variable
    M=D                 // store D there
.endm

start:                  // reset PC lands here (ROM_BASE)
    @10                 // A = 10
    D=A                 // D = 10
    STD CNT             // CNT = 10
    @0                  // A = 0
    D=A                 // D = 0
    STD SUM             // SUM = 0
loop:                   // sum += cnt; cnt -= 1; repeat while cnt > 0
    LDD SUM             // D = SUM
    @CNT                // A = &CNT
    D=D+M               // D = SUM + CNT
    STD SUM             // SUM = D
    @CNT                // A = &CNT
    M=M-1               // CNT = CNT - 1
    D=M                 // D = CNT (for the jump test)
    @loop               // A = loop target
    D;JGT               // repeat while CNT > 0
    @ptr                // A = &ptr (two-byte pointer in ROM)
    AP                  // A = pointer value = &table
    D=M                 // D = table[0]
    STD OUT             // OUT[0] = D
    @ptr                // A = &ptr
    AP                  // A = &table
    A=A+1               // A = &table[1]   (writes A[7:0] only; table does not cross a page)
    D=M                 // D = table[1]
    STD OUT+1           // OUT[1] = D
halt:                   // halt convention of the model: jump back to the A-instruction just before the jump
    @halt               // A = &halt
    0;JMP               // jump to self
ptr:  .word table       // pointer to the table
table: .byte 0x11, 0x22, 0x33  // data: three bytes to be copied
