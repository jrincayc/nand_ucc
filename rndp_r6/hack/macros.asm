// macros.asm -- small helper macros for the RNDP builder (Hack-vN-AB).  Every macro line is expanded in place.
// Conventions: a 16-bit variable occupies two consecutive RAM bytes, low byte first.  D is the accumulator; A is clobbered by almost
// everything; a "ROM pointer" is a 16-bit RAM variable (loaded with AP).  Subroutines: CALL stores the return address in RA_<sub>.

.macro LD v                  // D = RAM[v]
    @\v                      // A = address of the variable
    D=M                      // D = its value
.endm

.macro ST v                  // RAM[v] = D
    @\v                      // A = address of the variable
    M=D                      // store D
.endm

.macro SET v k               // RAM[v] = constant k (0..255)
    @\k                      // A = the constant
    D=A                      // D = low 8 bits of A = k
    @\v                      // A = address of the variable
    M=D                      // store it
.endm

.macro SET16 v k             // 16-bit variable v = constant k (any 16-bit value)
    @lo(\k)                  // A = low byte of the constant
    D=A                      // D = low byte
    @\v                      // A = &v
    M=D                      // v.low = low byte
    @hi(\k)                  // A = high byte of the constant
    D=A                      // D = high byte
    @\v+1                    // A = &v.high
    M=D                      // v.high = high byte
.endm

.macro COPY16 dst src        // 16-bit variable dst = 16-bit variable src
    @\src                    // A = &src.low
    D=M                      // D = src.low
    @\dst                    // A = &dst.low
    M=D                      // dst.low = D
    @\src+1                  // A = &src.high
    D=M                      // D = src.high
    @\dst+1                  // A = &dst.high
    M=D                      // dst.high = D
.endm

.macro GOTO l                // unconditional jump
    @\l                      // A = target
    0;JMP                    // jump
.endm

.macro IFEQ l                // if D == 0 goto l
    @\l                      // A = target
    D;JEQ                    // jump when D is zero
.endm

.macro IFNE l                // if D != 0 goto l
    @\l                      // A = target
    D;JNE                    // jump when D is not zero
.endm

.macro IFLT l                // if D < 0 (signed) goto l
    @\l                      // A = target
    D;JLT                    // jump when D is negative
.endm

.macro IFGE l                // if D >= 0 (signed) goto l
    @\l                      // A = target
    D;JGE                    // jump when D is not negative
.endm

.macro INC16 v               // 16-bit increment of the variable v
    @\v                      // A = &v.low
    M=M+1                    // v.low += 1
    D=M                      // D = new low byte
    @inc\@                   // A = skip target
    D;JNE                    // no carry out of the low byte unless it became 0
    @\v+1                    // A = &v.high
    M=M+1                    // carry into the high byte
inc\@:                       // (label) continue here
.endm

.macro DBL                   // D = 2 * D (the ISA has no D+D form: add D to a copy in memory)
    @DT                      // A = scratch byte
    M=D                      // scratch = D
    D=D+M                    // D = D + scratch = 2 D
.endm

.macro CALL sub              // call subroutine: store the return address in RA_<sub> (2 bytes), jump
    @lo(ret\@)               // A = low byte of the return address
    D=A                      // D = it
    @RA_\sub                 // A = &RA_<sub>.low
    M=D                      // store
    @hi(ret\@)               // A = high byte of the return address
    D=A                      // D = it
    @RA_\sub+1               // A = &RA_<sub>.high
    M=D                      // store
    @\sub                    // A = subroutine entry
    0;JMP                    // go
ret\@:                       // (label) the subroutine returns here
.endm

.macro RET sub               // return from subroutine <sub>
    @RA_\sub                 // A = &return address
    AP                       // A = the return address (pointer stored in RAM)
    0;JMP                    // jump to it
.endm

.macro PUT p                 // store D at the RAM address held in variable p, then p += 1 (D unchanged)
    @\p                      // A = &p
    A=M                      // A = destination address
    M=D                      // RAM[destination] = D
    @\p                      // A = &p
    M=M+1                    // p += 1
.endm

.macro WRA reg src           // arm register reg = RAM[src]
    @\src                    // A = &src
    D=M                      // D = value
    @ARM+\reg                // A = arm register address
    M=D                      // write the register
.endm

.macro WRK reg k             // arm register reg = constant k (0..255)
    @\k                      // A = the constant
    D=A                      // D = it
    @ARM+\reg                // A = arm register address
    M=D                      // write the register
.endm

.macro WR16 reg k            // arm register pair reg, reg+1 = 16-bit constant k
    @lo(\k)                  // A = low byte
    D=A                      // D = it
    @ARM+\reg                // A = register low
    M=D                      // write it
    @hi(\k)                  // A = high byte
    D=A                      // D = it
    @ARM+\reg+1              // A = register high
    M=D                      // write it
.endm

.macro ADDI v k              // 16-bit variable v += constant k (0..255), via add16 (AUH is 0 between calls)
    @\v                      // A = RAM address of the variable
    D=A                      // D = that address
    @ADST                    // A = &ADST
    M=D                      // ADST = &v
    @\k                      // A = the constant
    D=A                      // D = k
    @AUL                     // A = &AUL
    M=D                      // addend low = k
    CALL add16               // v += k
.endm

.macro ADDK v k              // 16-bit variable v += 16-bit constant k (mod 2^16)
    @lo(\k)                  // A = low byte of k
    D=A                      // D = it
    @AUL                     // A = &AUL
    M=D                      // addend low
    @hi(\k)                  // A = high byte of k
    D=A                      // D = it
    @AUH                     // A = &AUH
    M=D                      // addend high
    @\v                      // A = RAM address of the variable
    D=A                      // D = it
    @ADST                    // A = &ADST
    M=D                      // ADST = &v
    CALL add16               // v += k
.endm

.macro ADDV v w              // 16-bit variable v += 16-bit variable w (v may equal w)
    @\w                      // A = &w.low
    D=M                      // D = w.low
    @AUL                     // A = &AUL
    M=D                      // addend low
    @\w+1                    // A = &w.high
    D=M                      // D = w.high
    @AUH                     // A = &AUH
    M=D                      // addend high
    @\v                      // A = RAM address of v
    D=A                      // D = it
    @ADST                    // A = &ADST
    M=D                      // ADST = &v
    CALL add16               // v += w
.endm
