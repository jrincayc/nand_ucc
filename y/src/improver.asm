// improver.asm -- the Y hardware improver (M5): reads one combinational module record from the hardware description in ROM and,
// when it can implement it with fewer NAND gates, writes the improved record into a RAM buffer.  Hack-vN-AB assembly.
// It is a transcription of tools/ref_improve.py (improve_record), the normative reference; the tests compare the records byte for byte.
//
// Entry:  ITY = type number of the module (directory slot).  Result: IMPR = 1 and the improved record at RECB (RECN bytes), or IMPR = 0
// (module not improvable / no gain: keep using the record in ROM).  Subroutine calls use the CALL / RET macros (macros.asm).
//
// Working data (all in RAM):
//   GA[s], GB[s]   the two NAND inputs of gate signal s (s = 3 .. 34).  Internally every module has exactly 3 inputs (signals 0..2); a module with
//                  fewer real inputs just has unused ones, so gate signal numbers are 3 + slot.  GA = 0xFF marks a hole, 0xFE a duplicate (merged).
//   O0, O1         output signals.   ING number of gate slots in use.
//   SCR            44 bytes of scratch whose meaning depends on the phase (see the .equ block).
// Truth tables are 8-bit: leaf i has the table 0xAA / 0xCC / 0xF0 (masked with FULL = 0x03 / 0x0F / 0xFF for 1 / 2 / 3 leaves).

// (the RAM variables are defined in ram.asm)

// ------------------------------------------------------------------------------------------------ macros (see also macros.asm)
.macro LDI arr idx           // D = arr[idx]   (arr = address of element 0, idx = variable holding the index)
    @\arr                    // A = base
    D=A                      // D = base
    @\idx                    // A = &idx
    A=D+M                    // A = base + idx
    D=M                      // D = element
.endm

.macro STI arr idx           // arr[idx] = D
    @DV                      // A = &DV
    M=D                      // save the value
    @\arr                    // A = base
    D=A                      // D = base
    @\idx                    // A = &idx
    D=D+M                    // D = base + idx
    @ADR                     // A = &ADR
    M=D                      // keep the address
    @DV                      // A = &DV
    D=M                      // D = the value again
    @ADR                     // A = &ADR
    A=M                      // A = the element address
    M=D                      // store
.endm

.macro INCV v                // v += 1
    @\v                      // A = &v
    M=M+1                    // increment
.endm

.macro DECV v                // v -= 1
    @\v                      // A = &v
    M=M-1                    // decrement
.endm

.macro CPY dst src           // dst = src (bytes)
    @\src                    // A = &src
    D=M                      // D = value
    @\dst                    // A = &dst
    M=D                      // store
.endm

.macro SUBV a b              // D = a - b (bytes, small positive values)
    @\a                      // A = &a
    D=M                      // D = a
    @\b                      // A = &b
    D=D-M                    // D = a - b
.endm

.macro IFEQV a b l           // if a == b goto l
    SUBV \a, \b              // D = a - b
    IFEQ \l                  // zero: equal
.endm

.macro IFNEV a b l           // if a != b goto l
    SUBV \a, \b              // D = a - b
    IFNE \l                  // not zero: different
.endm

.macro IFLTV a b l           // if a < b goto l (values below 128)
    SUBV \a, \b              // D = a - b
    IFLT \l                  // negative
.endm

.macro IFGEV a b l           // if a >= b goto l (values below 128)
    SUBV \a, \b              // D = a - b
    IFGE \l                  // not negative
.endm

.macro IFGTV a b l           // if a > b goto l (values below 128)
    SUBV \a, \b              // D = a - b
    IFGT \l                  // positive
.endm

.macro MAPS v                // v: record signal number -> internal number (gate signals are shifted by SH)
    IFGEV \v, NIR, maps\@   // a gate signal
    GOTO mdone\@             // an input keeps its number
maps\@:
    @SH                      // A = &SH
    D=M                      // D = shift
    @\v                      // A = &v
    M=D+M                    // v += shift
mdone\@:
.endm

.macro RMV v                 // v: if it is a merged duplicate, the gate it was merged into
    IFLK \v, 3, rmd\@       // inputs are never merged
    LDI GA, \v               // D = GA[v]
    @DUP                     // A = duplicate marker
    D=D-A                    // D = 0 when v is a duplicate
    IFNE rmd\@               // it is not
    LDI GB, \v               // D = the gate it duplicates
    ST \v                    // v = that gate
rmd\@:
.endm

.macro RNV v                 // v: signal -> its new number (inputs keep theirs)
    IFLK \v, 3, rnd\@       // inputs keep their numbers
    LDI RN, \v               // D = new number
    ST \v                    // v = it
rnd\@:
.endm

.macro MARKIN arr            // cone sweep: mark input \arr[CI] of gate CI as a cone member unless it is an input signal or a leaf of the cut
    LDI \arr, CI             // D = the input signal
    ST X2                    // keep
    IFLK X2, 3, mk\@         // an input signal: never in the cone
    IFEQV X2, BL+1, mk\@     // leaf 0
    IFEQV X2, BL+2, mk\@     // leaf 1
    IFEQV X2, BL+3, mk\@     // leaf 2
    SET BMB, CN              // bitmap = cone
    CPY BIX, X2              // the signal
    CALL bs                  // mark it
mk\@:
.endm

.macro USEDIN arr            // saved count: gate CI (outside the cone) uses \arr[CI]; if that is a cone gate it is still needed
    LDI \arr, CI             // D = the input signal
    ST X2                    // keep
    IFLK X2, 3, ui\@         // an input signal
    SET BMB, CN              // bitmap = cone
    CPY BIX, X2              // the signal
    CALL bt                  // in the cone?
    IFEQ ui\@                // no
    SET BMB, NS              // bitmap = used outside
    CPY BIX, X2              // the signal
    CALL bs                  // mark it as needed
ui\@:
.endm

.macro ADJUP v               // rewrite: reference v >= RT moves up by NN
    IFGEV \v, RT, au\@      // at or above the root
    GOTO ad\@               // below: unchanged
au\@:
    @NN                      // A = &NN
    D=M                      // D = number of inserted gates
    @\v                      // A = &v
    M=D+M                    // v += NN
ad\@:
.endm

.macro ADJDN v               // partition: reference v after the gate S moved to the end: S -> E, above S -> one lower
    IFEQV \v, XC, atend\@   // v == S
    IFGTV \v, XC, below\@   // v > S
    GOTO dn\@               // lower: unchanged
atend\@:
    CPY \v, XD               // v = E
    GOTO dn\@               // done
below\@:
    DECV \v                  // one lower
dn\@:
.endm

.macro MAPQ                  // rewrite: X0 = index into (leaves + new gates) -> signal number
    IFLTV X0, BL, leaf\@     // a leaf
    LD RT                    // D = root signal = first new gate
    @X0                      // A = &index
    D=D+M                    // D = RT + index
    @BL                      // A = &K
    D=D-M                    // D = RT + index - K
    ST X0                    // signal
    GOTO mq\@                // done
leaf\@:
    @BL+1                    // A = &leaf 0
    D=A                      // D = its address
    @X0                      // A = &index
    A=D+M                    // A = &leaf
    D=M                      // D = leaf signal
    ST X0                    // signal
mq\@:
.endm

.macro IFK v k l             // if v == constant k goto l
    @\v                      // A = &v
    D=M                      // D = v
    @\k                      // A = k
    D=D-A                    // D = v - k
    IFEQ \l                  // zero: equal
.endm

.macro IFNK v k l            // if v != constant k goto l
    @\v                      // A = &v
    D=M                      // D = v
    @\k                      // A = k
    D=D-A                    // D = v - k
    IFNE \l                  // not zero
.endm

.macro IFLK v k l            // if v < constant k goto l (small values)
    @\v                      // A = &v
    D=M                      // D = v
    @\k                      // A = k
    D=D-A                    // D = v - k
    IFLT \l                  // negative
.endm

.macro IFGK v k l            // if v >= constant k goto l (small values)
    @\v                      // A = &v
    D=M                      // D = v
    @\k                      // A = k
    D=D-A                    // D = v - k
    IFGE \l                  // not negative
.endm

// ------------------------------------------------------------------------------------------------ leaf subroutines
irdb:                         // D = next byte of the ROM record at IP, IP += 1
    @IP                       // A = &IP
    AP                       // A = the ROM address
    D=M                      // D = the byte
    @IRDV                     // A = &IRDV
    M=D                      // keep it
    INC16 IP                  // IP += 1
    @IRDV                     // A = &IRDV
    D=M                      // D = the byte
    RET irdb                  // return

bt:                          // D = nonzero when bit BIX of the bitmap at BMB is set
    LD BIX                 // D = table index
    @btab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = byte number
    @BMB                     // A = &BMB
    D=D+M                    // D = address of the bitmap byte
    @ADR                     // A = &ADR
    M=D                      // keep
    LD BIX                 // D = table index
    @mtab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = mask
    @MSK                     // A = &MSK
    M=D                      // keep
    @ADR                     // A = &ADR
    A=M                      // A = bitmap byte address
    D=M                      // D = the byte
    @MSK                     // A = &MSK
    D=D&M                    // D = the bit (nonzero when set)
    RET bt                   // return

bs:                          // set bit BIX of the bitmap at BMB
    LD BIX                 // D = table index
    @btab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = byte number
    @BMB                     // A = &BMB
    D=D+M                    // D = address of the bitmap byte
    @ADR                     // A = &ADR
    M=D                      // keep
    LD BIX                 // D = table index
    @mtab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = mask
    @MSK                     // A = &MSK
    M=D                      // keep
    @ADR                     // A = &ADR
    A=M                      // A = bitmap byte address
    D=M                      // D = the byte
    @MSK                     // A = &MSK
    D=D|M                    // set the bit
    @ADR                     // A = &ADR
    A=M                      // A = bitmap byte address
    M=D                      // store
    RET bs                   // return

keycmp:                      // compare the cut CL with the cut whose address is in X0 (4 bytes each: K, L0, L1, L2): D = CL - ref, first difference
    SET X1, 0                // byte index
kc_loop:
    @CL                      // A = &CL
    D=A                      // D = address of CL
    @X1                      // A = &index
    A=D+M                    // A = &CL[index]
    D=M                      // D = candidate byte
    @DV                      // A = &DV
    M=D                      // keep
    @X0                      // A = &X0
    D=M                      // D = reference base
    @X1                      // A = &index
    A=D+M                    // A = &ref[index]
    D=M                      // D = reference byte
    @DV                      // A = &DV
    D=M-D                    // D = candidate - reference
    IFNE kc_done             // different: that is the answer
    INCV X1                  // next byte
    @X1                      // A = &index
    D=M                      // D = index
    @4                       // A = 4
    D=D-A                    // D = index - 4
    IFLT kc_loop             // more bytes
    SET DV, 0                // all equal
    LD DV                    // D = 0
kc_done:
    RET keycmp               // return (D = difference)

ins:                         // insert the signal X2 into the sorted cut CL (K at CL, leaves at CL+1..), ignoring duplicates
    SET X1, 1                // position
ins_find:
    @CL                      // A = &CL
    D=M                      // D = K
    @1                       // A = 1
    D=D+A                    // D = K + 1 = position after the last leaf
    @X1                      // A = &position
    D=D-M                    // D = K + 1 - position
    IFEQ ins_end             // reached the end: append
    @CL                      // A = &CL
    D=A                      // D = address
    @X1                      // A = &position
    A=D+M                    // A = &CL[position]
    D=M                      // D = leaf at the position
    @X2                      // A = &new signal
    D=D-M                    // D = leaf - new
    IFEQ ins_ret             // already present
    IFGT ins_here            // leaf > new: insert before it
    INCV X1                  // next position
    GOTO ins_find            // continue
ins_here:                    // shift the leaves from position up by one
    @CL                      // A = &CL
    D=M                      // D = K
    ST X3                    // X3 = index of the last leaf
ins_shift:
    @X3                      // A = &X3
    D=M                      // D = source index
    @X1                      // A = &position
    D=D-M                    // D = source - position
    IFLT ins_put             // all moved
    @CL                      // A = &CL
    D=A                      // D = address
    @X3                      // A = &source
    A=D+M                    // A = &CL[source]
    D=M                      // D = leaf
    @DV                      // A = &DV
    M=D                      // keep
    @CL+1                    // A = &CL[1]
    D=A                      // D = address
    @X3                      // A = &source
    D=D+M                    // D = &CL[source + 1]
    @ADR                     // A = &ADR
    M=D                      // keep
    @DV                      // A = &DV
    D=M                      // D = leaf
    @ADR                     // A = &ADR
    A=M                      // A = destination
    M=D                      // CL[source + 1] = leaf
    DECV X3                  // next lower
    GOTO ins_shift           // continue
ins_put:
    @CL                      // A = &CL
    D=A                      // D = address
    @X1                      // A = &position
    A=D+M                    // A = &CL[position]
    D=A                      // D = the address
    @ADR                     // A = &ADR
    M=D                      // keep
    @X2                      // A = &new
    D=M                      // D = new signal
    @ADR                     // A = &ADR
    A=M                      // A = &CL[position]
    M=D                      // store
    @CL                      // A = &CL
    M=M+1                    // K += 1
    GOTO ins_ret             // done
ins_end:                     // append at the end
    @CL                      // A = &CL
    D=A                      // D = address
    @X1                      // A = &position
    A=D+M                    // A = &CL[position]
    D=A                      // D = the address
    @ADR                     // A = &ADR
    M=D                      // keep
    @X2                      // A = &new
    D=M                      // D = new signal
    @ADR                     // A = &ADR
    A=M                      // A = &CL[position]
    M=D                      // store
    @CL                      // A = &CL
    M=M+1                    // K += 1
ins_ret:
    RET ins                  // return

// ------------------------------------------------------------------------------------------------ load
load:                        // IP -> record header.  Fills NIR NO SL REAL ING SH GA GB O0 O1 P0 P1.  D = 0 when fine, 1 when the module is left alone
    CALL irdb                 // D = flags
    IFK IRDV, 1, ld_f_ok      // 1 = combinational, improvable
    GOTO ld_rej              // anything else: not for us
ld_f_ok:
    CALL irdb                 // D = n_in
    ST NIR                   // keep
    CALL irdb                 // D = n_out
    ST NO                    // keep
    CALL irdb                 // D = number of slots
    ST SL                    // keep
    IFGK NIR, 4, ld_rej      // more than 3 inputs
    IFLK NO, 1, ld_rej       // no output
    IFGK NO, 3, ld_rej       // more than 2 outputs
    IFGK SL, 27, ld_rej      // more than 26 slots
    @3                       // A = 3
    D=A                      // D = 3
    @NIR                     // A = &NIR
    D=D-M                    // D = 3 - n_in
    ST SH                    // gate signals are shifted by this
    SET REAL, 0              // no real gates yet
    SET CI, 3                // signal of the next slot
    SET CJ, 0                // slots done
ld_slot:
    IFGEV CJ, SL, ld_outs    // all slots read
    CALL irdb                 // D = kind
    ST X1                    // keep
    CALL irdb                 // D = first operand (or the count of a skip entry)
    ST X2                    // keep
    CALL irdb                 // D = second operand
    ST X3                    // keep
    IFK X1, 2, ld_skip       // a run of unplaced slots
    IFNK X1, 0, ld_rej       // only NAND gates are allowed
    MAPS X2                  // a, internal numbering
    MAPS X3                  // b, internal numbering
    IFGEV X2, CI, ld_rej     // a must come before the gate (slot order has to be topological)
    IFGEV X3, CI, ld_rej     // same for b
    IFLK X2, 3, ld_a_ok      // an input signal: fine
    LDI GA, X2               // D = GA[a]
    @HOLE                    // A = hole marker
    D=D-A                    // D = 0 when a is a hole
    IFEQ ld_rej              // a gate cannot use an unplaced slot
ld_a_ok:
    IFLK X3, 3, ld_b_ok      // an input signal: fine
    LDI GA, X3               // D = GA[b]
    @HOLE                    // A = hole marker
    D=D-A                    // D = 0 when b is a hole
    IFEQ ld_rej              // a gate cannot use an unplaced slot
ld_b_ok:
    LD X2                    // D = a
    STI GA, CI               // GA[CI] = a
    LD X3                    // D = b
    STI GB, CI               // GB[CI] = b
    INCV REAL                // one more real gate
    INCV CI                  // next slot signal
    INCV CJ                  // next slot
    GOTO ld_slot             // continue
ld_skip:                     // X2 holes
    LD X2                    // D = count
    IFEQ ld_rej              // a skip of 0 is not valid
    @X2                      // A = &count
    D=M                      // D = count
    @CJ                      // A = &CJ
    M=D+M                    // slots done += count
ld_hole:
    @HOLE                    // A = hole marker
    D=A                      // D = it
    STI GA, CI               // GA[CI] = hole
    INCV CI                  // next slot signal
    DECV X2                  // one less
    @X2                      // A = &X2
    D=M                      // D = left
    IFNE ld_hole             // more
    GOTO ld_slot             // continue
ld_outs:
    IFNEV CJ, SL, ld_rej     // a skip entry overran the slot count
    CPY ING, SL               // gate slots in use
    SET CJ, 0                // output index
ld_out:
    CALL irdb                 // D = output signal (record numbering)
    ST X2                    // keep
    MAPS X2                  // internal numbering
    IFLK X2, 3, ld_rej       // an output that is an input: not handled
    IFGEV X2, CI, ld_rej     // beyond the last slot
    LDI GA, X2               // D = GA[output]
    @HOLE                    // A = hole marker
    D=D-A                    // D = 0 when the slot is a hole
    IFEQ ld_rej              // an output must be a real gate
    IFNK CJ, 0, ld_o2        // second output
    CPY O0, X2               // O0
    CPY P0, X2               // pinned slot, still signal numbered
    GOTO ld_onext            // next
ld_o2:
    CPY O1, X2               // O1
    CPY P1, X2               // pinned slot, still signal numbered
ld_onext:
    INCV CJ                  // next output
    IFGEV CJ, NO, ld_odone   // all outputs read
    GOTO ld_out              // read the next one
ld_odone:
    IFNK NO, 1, ld_two       // two outputs
    CPY O1, O0               // one output: the second is a copy of the first (loops over both stay valid)
    CPY P1, P0               // same pin
    GOTO ld_fin              // finish
ld_two:
    IFEQV O0, O1, ld_rej     // the outputs must be different gates
ld_fin:
    LD P0                    // D = signal of the pinned output 0
    @3                       // A = 3
    D=D-A                    // D = its slot
    ST P0                    // store
    LD P1                    // D = signal of the pinned output 1
    @3                       // A = 3
    D=D-A                    // D = its slot
    ST P1                    // store
    @0                       // A = 0
    D=A                      // D = 0: loaded
    RET load                 // return
ld_rej:
    @1                       // A = 1
    D=A                      // D = 1: leave the module alone
    RET load                 // return

// ------------------------------------------------------------------------------------------------ compact
compact:                     // merge identical gates (the later becomes the earlier), drop holes and dead gates, keep the order of the rest
    LD ING                    // D = gate slots
    @3                       // A = 3
    D=D+A                    // D = signal after the last gate
    ST EN                    // EN
    SET CI, 3                // first gate signal
cp_g:                        // pass 1: merge, forward
    IFGEV CI, EN, cp_outs    // all gates seen
    LDI GA, CI               // D = GA[g]
    @HOLE                    // A = hole marker
    D=D-A                    // D = 0 when the slot is a hole
    IFEQ cp_gnext            // holes are skipped
    LDI GA, CI               // D = a
    ST X2                    // a
    LDI GB, CI               // D = b
    ST X3                    // b
    RMV X2                   // a through the merges so far
    RMV X3                   // b through the merges so far
    LD X2                    // D = a
    STI GA, CI               // store it back
    LD X3                    // D = b
    STI GB, CI               // store it back
    SET CJ, 3                // earlier gate h
cp_h:
    IFGEV CJ, CI, cp_gnext   // no identical earlier gate
    LDI GA, CJ               // D = GA[h]
    ST X0                    // X0 = a of h
    @DUP                     // A = duplicate marker
    D=D-A                    // D = GA[h] - 126: >= 0 for holes and duplicates
    IFGE cp_hnext            // holes and duplicates are not candidates
    LDI GB, CJ               // D = b of h
    ST X1                    // X1
    IFNEV X0, X2, cp_sw      // a differs: try the swapped order
    IFEQV X1, X3, cp_dup     // same pair
cp_sw:
    IFNEV X0, X3, cp_hnext   // not the swapped pair either
    IFEQV X1, X2, cp_dup     // swapped pair
cp_hnext:
    INCV CJ                  // next earlier gate
    GOTO cp_h                // compare
cp_dup:                      // gate g is the same as gate h
    @DUP                     // A = duplicate marker
    D=A                      // D = it
    STI GA, CI               // GA[g] = duplicate
    LD CJ                    // D = h
    STI GB, CI               // GB[g] = h
cp_gnext:
    INCV CI                  // next gate
    GOTO cp_g                // continue
cp_outs:
    RMV O0                   // outputs through the merges
    RMV O1                   // same
    SET CI, 3                // pass 2: liveness; RN[g] = 0 for all gates
cp_z:
    IFGEV CI, EN, cp_mark    // done
    @0                       // A = 0
    D=A                      // D = 0
    STI RN, CI               // RN[g] = 0
    INCV CI                  // next
    GOTO cp_z                // continue
cp_mark:
    @1                       // A = 1
    D=A                      // D = 1 = live
    STI RN, O0               // output 0 is live
    @1                       // A = 1
    D=A                      // D = 1
    STI RN, O1               // output 1 is live
    LD EN                    // D = end
    D=D-1                    // D = last gate
    ST CI                    // sweep downwards
cp_l:
    IFLK CI, 3, cp_pack      // all gates seen
    LDI RN, CI               // D = live flag
    IFEQ cp_lnext            // dead: nothing to mark
    LDI GA, CI               // D = a
    ST X0                    // a
    IFLK X0, 3, cp_lb        // an input
    @1                       // A = 1
    D=A                      // D = 1
    STI RN, X0               // a is live
cp_lb:
    LDI GB, CI               // D = b
    ST X0                    // b
    IFLK X0, 3, cp_lnext     // an input
    @1                       // A = 1
    D=A                      // D = 1
    STI RN, X0               // b is live
cp_lnext:
    DECV CI                  // next lower gate
    GOTO cp_l                // continue
cp_pack:                     // pass 3: renumber and move the live gates down
    SET CI, 3                // gate being looked at
    SET CJ, 3                // next free place
cp_p:
    IFGEV CI, EN, cp_pend    // done
    LDI RN, CI               // D = live flag
    IFEQ cp_pnext            // dead
    LDI GA, CI               // D = a
    ST X2                    // a
    LDI GB, CI               // D = b
    ST X3                    // b
    RNV X2                   // a renumbered
    RNV X3                   // b renumbered
    LD CJ                    // D = new number of this gate
    STI RN, CI               // RN[g] = new number
    LD X2                    // D = a
    STI GA, CJ               // place the gate
    LD X3                    // D = b
    STI GB, CJ               // place the gate
    INCV CJ                  // next free place
cp_pnext:
    INCV CI                  // next gate
    GOTO cp_p                // continue
cp_pend:
    LD CJ                    // D = first free signal
    @3                       // A = 3
    D=D-A                    // D = number of gates
    ST ING                    // ING
    RNV O0                   // outputs renumbered
    RNV O1                   // same
    RET compact              // return

// ------------------------------------------------------------------------------------------------ nextcut
nextcut:                     // RT = root, LKV / LK = the previous cut.  Finds the smallest chain cut of RT that is larger than LK.
                             // Result: BF = 1 and BL = (K, L0, L1, L2), or BF = 0.   Order: fewer leaves first, then lexicographic.
    SET BF, 0                // nothing found yet
    SET CL, 0                // clear the cut being generated: K
    SET CL+1, 0              // leaf 0
    SET CL+2, 0              // leaf 1
    SET CL+3, 0              // leaf 2
    SET CL+4, 0              // spare
    LDI GA, RT               // D = first input of the root
    ST X2                    // to insert
    CALL ins                 // CL = {a}
    LDI GB, RT               // D = second input of the root
    ST X2                    // to insert
    CALL ins                 // CL = sorted {a, b}
nc_loop:                     // CL is a chain cut: is it a candidate?
    LD LKV                   // D = 1 when there is a previous cut
    IFEQ nc_q                // no previous cut: every cut qualifies
    SET X0, LK               // reference = the previous cut
    CALL keycmp              // D = CL - LK
    IFGT nc_q                // larger than the previous cut: a candidate
    GOTO nc_step             // not larger: skip
nc_q:
    LD BF                    // D = 1 when a best cut exists
    IFEQ nc_take             // none yet: take it
    SET X0, BL               // reference = the best so far
    CALL keycmp              // D = CL - BL
    IFLT nc_take             // smaller than the best: take it
    GOTO nc_step             // keep the best
nc_take:
    CPY BL, CL               // K
    CPY BL+1, CL+1           // leaf 0
    CPY BL+2, CL+2           // leaf 1
    CPY BL+3, CL+3           // leaf 2
    SET BF, 1                // found
nc_step:                     // next chain cut: replace the highest leaf (if it is a gate) by its two inputs
    LDI CL, CL               // D = CL[K] = highest leaf (CL[0] holds K, so CL + K is leaf K)
    ST X2                    // keep it
    IFLK X2, 3, nc_done      // an input: no gate leaf left
    LDI GA, X2               // D = first input of that gate
    ST XB                    // keep
    LDI GB, X2               // D = second input of that gate
    ST XA                    // keep
    @0                       // A = 0
    D=A                      // D = 0
    STI CL, CL               // remove the highest leaf: CL[K] = 0
    DECV CL                  // K -= 1
    CPY X2, XB               // first input
    CALL ins                 // insert it
    CPY X2, XA               // second input
    CALL ins                 // insert it
    IFGK CL, 4, nc_done      // 4 leaves: no cut
    GOTO nc_loop             // examine the new cut
nc_done:
    RET nextcut              // return

// ------------------------------------------------------------------------------------------------ cone
cone:                        // process the cut BL of the root RT: SAVD (gates freed), FT (truth table over the cut), FULL.
                             // D = 1 when FT is the table of a single leaf (then NSIG = that leaf), else 0.
    LD BL                 // D = table index
    @ftab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = mask
    ST FULL                  // FULL
    SET CN, 0                // clear the cone bitmap
    SET CN+1, 0              // ..
    SET CN+2, 0              // ..
    SET CN+3, 0              // ..
    SET NS, 0                // clear the "used outside" bitmap
    SET NS+1, 0              // ..
    SET NS+2, 0              // ..
    SET NS+3, 0              // ..
    SET BMB, CN              // bitmap = cone
    CPY BIX, RT              // the root
    CALL bs                  // is in the cone
    CPY CI, RT               // sweep downwards from the root
cn_g:
    IFLK CI, 3, cn_used      // all gates seen
    SET BMB, CN              // bitmap = cone
    CPY BIX, CI              // this gate
    CALL bt                  // in the cone?
    IFEQ cn_next             // no
    MARKIN GA                // first input
    MARKIN GB                // second input
cn_next:
    DECV CI                  // next lower gate
    GOTO cn_g                // continue
cn_used:                     // gates outside the cone that use cone gates
    SET CI, 3                // first gate
cn_u:
    LD ING                    // D = gate count
    @3                       // A = 3
    D=D+A                    // D = end signal
    @CI                      // A = &CI
    D=D-M                    // D = end - CI
    IFLE cn_outs             // all gates seen (end <= CI)
    SET BMB, CN              // bitmap = cone
    CPY BIX, CI              // this gate
    CALL bt                  // in the cone?
    IFNE cn_unext            // a cone gate: its own uses are inside the cone
    USEDIN GA                // first input
    USEDIN GB                // second input
cn_unext:
    INCV CI                  // next gate
    GOTO cn_u                // continue
cn_outs:                     // outputs use cone gates too
    SET BMB, CN              // bitmap = cone
    CPY BIX, O0              // output 0
    CALL bt                  // in the cone?
    IFEQ cn_o1               // no
    SET BMB, NS              // bitmap = used outside
    CPY BIX, O0              // output 0
    CALL bs                  // needed
cn_o1:
    SET BMB, CN              // bitmap = cone
    CPY BIX, O1              // output 1
    CALL bt                  // in the cone?
    IFEQ cn_count            // no
    SET BMB, NS              // bitmap = used outside
    CPY BIX, O1              // output 1
    CALL bs                  // needed
cn_count:                    // SAVD = 1 (the root) + cone gates below the root that are not needed outside
    SET SAVD, 1              // the root
    SET CI, 3                // first gate
cn_c:
    IFGEV CI, RT, cn_eval    // below the root only
    SET BMB, CN              // bitmap = cone
    CPY BIX, CI              // this gate
    CALL bt                  // in the cone?
    IFEQ cn_cnext            // no
    SET BMB, NS              // bitmap = used outside
    CPY BIX, CI              // this gate
    CALL bt                  // needed outside?
    IFNE cn_cnext            // yes: not freed
    INCV SAVD                // freed
cn_cnext:
    INCV CI                  // next gate
    GOTO cn_c                // continue
cn_eval:                     // truth table of the root over the leaves
    SET CI, 0                // leaf index
cn_leaf:
    IFGEV CI, BL, cn_gates   // all K leaves set
    LD CI                 // D = table index
    @vtab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = 0xAA / 0xCC / 0xF0
    @FULL                    // A = &FULL
    D=D&M                    // D = the leaf's table over K variables
    ST X0                    // keep
    @BL+1                    // A = &leaf 0
    D=A                      // D = its address
    @CI                      // A = &CI
    A=D+M                    // A = &leaf i
    D=M                      // D = leaf signal
    ST X1                    // keep
    LD X0                    // D = table
    STI VAL, X1              // VAL[leaf] = table
    INCV CI                  // next leaf
    GOTO cn_leaf             // continue
cn_gates:
    SET CI, 3                // first gate
cn_e:
    IFGTV CI, RT, cn_f       // all gates up to the root done
    SET BMB, CN              // bitmap = cone
    CPY BIX, CI              // this gate
    CALL bt                  // in the cone?
    IFEQ cn_enext            // no
    LDI GA, CI               // D = a
    ST X2                    // keep
    LDI VAL, X2              // D = table of a
    ST X0                    // keep
    LDI GB, CI               // D = b
    ST X2                    // keep
    LDI VAL, X2              // D = table of b
    @X0                      // A = &table of a
    D=D&M                    // D = a AND b
    D=!D                     // D = NAND
    @FULL                    // A = &FULL
    D=D&M                    // keep K variables
    STI VAL, CI              // VAL[g] = table
cn_enext:
    INCV CI                  // next gate
    GOTO cn_e                // continue
cn_f:
    LDI VAL, RT              // D = table of the root
    ST FT                    // FT
    SET CI, 0                // does it equal a leaf's table?
cn_cmp:
    IFGEV CI, BL, cn_no      // no leaf matches
    LD CI                 // D = table index
    @vtab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = table
    @FULL                    // A = &FULL
    D=D&M                    // D = leaf table
    @FT                      // A = &FT
    D=D-M                    // D = leaf table - FT
    IFEQ cn_yes              // equal
    INCV CI                  // next leaf
    GOTO cn_cmp              // continue
cn_yes:
    @BL+1                    // A = &leaf 0
    D=A                      // D = its address
    @CI                      // A = &CI
    A=D+M                    // A = &leaf i
    D=M                      // D = the leaf signal
    ST NSIG                  // the root will be replaced by this signal
    @1                       // A = 1
    D=A                      // D = 1
    RET cone                 // return: equal to a leaf
cn_no:
    @0                       // A = 0
    D=A                      // D = 0
    RET cone                 // return: needs a search

// ------------------------------------------------------------------------------------------------ search
search:                      // find the fewest NAND gates (1 .. GMX) over the K leaves that compute FT.  D = 1 and SG gates in SI / SJ when found, else 0.
    SET SG, 1                // gates to use
sr_g:
    IFGTV SG, GMX, sr_fail   // nothing up to GMX gates
    SET CI, 0                // table index
sr_init:
    IFGEV CI, BL, sr_start   // K tables set
    LD CI                 // D = table index
    @vtab                     // A = table (aligned: no carry out of the low byte)
    A=D+A                    // A = entry
    D=M                      // D = table
    @FULL                    // A = &FULL
    D=D&M                    // D = variable i over K variables
    STI TB, CI               // TB[i] = it
    INCV CI                  // next
    GOTO sr_init             // continue
sr_start:
    CPY SLN, BL              // SLN = K tables so far
    SET SD, 0                // depth 0
    @255                     // A = 255
    D=A                      // D = "before the first candidate" (i = 255 wraps to 0)
    STI SI, SD               // SI[0]
    @0                       // A = 0
    D=A                      // D = 0
    STI SJ, SD               // SJ[0]
sr_next:                     // next candidate pair (i, j), j outer, i <= j, at depth SD
    LDI SI, SD               // D = last i
    D=D+1                    // i + 1 (255 + 1 = 0)
    ST X0                    // X0 = i
    LDI SJ, SD               // D = last j
    ST X1                    // X1 = j
    IFGTV X0, X1, sr_adv     // i > j: next j
    GOTO sr_store            // keep
sr_adv:
    INCV X1                  // j += 1
    SET X0, 0                // i = 0
sr_store:
    LD X0                    // D = i
    STI SI, SD               // SI[depth]
    LD X1                    // D = j
    STI SJ, SD               // SJ[depth]
    IFGEV X1, SLN, sr_back   // j beyond the table: this depth is exhausted
    LDI TB, X0               // D = table i
    ST X2                    // keep
    LDI TB, X1               // D = table j
    @X2                      // A = &table i
    D=D&M                    // D = i AND j
    D=!D                     // D = NAND
    @FULL                    // A = &FULL
    D=D&M                    // keep the rows that exist
    ST X2                    // X2 = new table
    SET CI, 0                // already present?
sr_has:
    IFGEV CI, SLN, sr_new    // not present
    LDI TB, CI               // D = table
    @X2                      // A = &new
    D=D-M                    // D = table - new
    IFEQ sr_next             // present: skip this candidate
    INCV CI                  // next table
    GOTO sr_has              // continue
sr_new:
    LD X2                    // D = new table
    STI TB, SLN              // append
    INCV SLN                 // one more signal
    INCV SD                  // one deeper
    IFEQV SD, SG, sr_last    // all SG gates chosen: check the result
    @255                     // A = 255
    D=A                      // D = before the first candidate
    STI SI, SD               // SI[depth]
    @0                       // A = 0
    D=A                      // D = 0
    STI SJ, SD               // SJ[depth]
    GOTO sr_next             // choose the next gate
sr_last:                     // is FT among the signals?
    SET CI, 0                // index
sr_fnd:
    IFGEV CI, SLN, sr_pop    // no
    LDI TB, CI               // D = table
    @FT                      // A = &FT
    D=D-M                    // D = table - FT
    IFEQ sr_found            // found
    INCV CI                  // next
    GOTO sr_fnd              // continue
sr_pop:                      // undo the last gate and try the next candidate at the depth above
    DECV SD                  // back one level
    DECV SLN                 // drop the table
    GOTO sr_next             // continue
sr_back:                     // depth exhausted
    LD SD                    // D = depth
    IFEQ sr_nextg            // depth 0: no solution with SG gates
    DECV SD                  // back one level
    DECV SLN                 // drop the table
    GOTO sr_next             // continue
sr_nextg:
    INCV SG                  // one more gate
    GOTO sr_g                // try again
sr_found:
    @1                       // A = 1
    D=A                      // D = 1
    RET search               // return: found
sr_fail:
    @0                       // A = 0
    D=A                      // D = 0
    RET search               // return: nothing

// ------------------------------------------------------------------------------------------------ rewrite
rewrite:                     // replace the root RT: NN = 0: by the signal NSIG; else by NN new gates (SI / SJ over leaves + new gates) inserted before RT
    LD NN                    // D = number of new gates
    IFNE rw_ins              // insert
    CPY R2, RT               // the old root keeps its number
    GOTO rw_rewire           // rewire the users
rw_ins:
    SET CI, 3                // first gate
rw_adj:                      // references at or above the root move up by NN
    LD ING                    // D = gates
    @3                       // A = 3
    D=D+A                    // D = end signal
    @CI                      // A = &CI
    D=D-M                    // D = end - CI
    IFLE rw_adjo             // done
    LDI GA, CI               // D = a
    ST X2                    // a
    ADJUP X2                 // adjust
    LD X2                    // D = a
    STI GA, CI               // store
    LDI GB, CI               // D = b
    ST X2                    // b
    ADJUP X2                 // adjust
    LD X2                    // D = b
    STI GB, CI               // store
    INCV CI                  // next gate
    GOTO rw_adj              // continue
rw_adjo:
    ADJUP O0                 // outputs
    ADJUP O1                 // outputs
    LD ING                    // D = gates
    @2                       // A = 2
    D=D+A                    // D = last gate signal
    ST CI                    // shift from the last gate down
rw_sh:
    IFLTV CI, RT, rw_new     // all moved
    LD CI                    // D = source
    @NN                      // A = &NN
    D=D+M                    // D = destination
    ST X3                    // keep
    LDI GA, CI               // D = a
    STI GA, X3               // copy
    LDI GB, CI               // D = b
    STI GB, X3               // copy
    DECV CI                  // next lower
    GOTO rw_sh               // continue
rw_new:                      // write the new gates at RT, RT + 1, ...
    SET CJ, 0                // new gate number
rw_t:
    IFGEV CJ, NN, rw_done    // all written
    LD RT                    // D = RT
    @CJ                      // A = &CJ
    D=D+M                    // D = signal of the new gate
    ST X3                    // keep
    LDI SI, CJ               // D = first operand index
    ST X0                    // keep
    MAPQ                     // X0 = signal
    LD X0                    // D = signal
    STI GA, X3               // GA[new]
    LDI SJ, CJ               // D = second operand index
    ST X0                    // keep
    MAPQ                     // X0 = signal
    LD X0                    // D = signal
    STI GB, X3               // GB[new]
    INCV CJ                  // next new gate
    GOTO rw_t                // continue
rw_done:
    LD ING                    // D = gates
    @NN                      // A = &NN
    D=D+M                    // D = gates + new
    ST ING                    // ING
    LD RT                    // D = RT
    @NN                      // A = &NN
    D=D+M                    // D = RT + NN = the old root's new number
    ST R2                    // R2
    D=D-1                    // D = RT + NN - 1 = the last new gate
    ST NSIG                  // replaces the root
rw_rewire:                   // every use of R2 becomes NSIG
    SET CI, 3                // first gate
rw_u:
    LD ING                    // D = gates
    @3                       // A = 3
    D=D+A                    // D = end signal
    @CI                      // A = &CI
    D=D-M                    // D = end - CI
    IFLE rw_uo               // done
    LDI GA, CI               // D = a
    @R2                      // A = &R2
    D=D-M                    // D = a - R2
    IFNE rw_ub               // not the root
    LD NSIG                  // D = replacement
    STI GA, CI               // GA = replacement
rw_ub:
    LDI GB, CI               // D = b
    @R2                      // A = &R2
    D=D-M                    // D = b - R2
    IFNE rw_un               // not the root
    LD NSIG                  // D = replacement
    STI GB, CI               // GB = replacement
rw_un:
    INCV CI                  // next gate
    GOTO rw_u                // continue
rw_uo:
    IFEQV O0, R2, rw_o0      // output 0 is the root
    GOTO rw_o1c              // no
rw_o0:
    CPY O0, NSIG             // output 0 = replacement
rw_o1c:
    IFEQV O1, R2, rw_o1      // output 1 is the root
    RET rewrite              // return
rw_o1:
    CPY O1, NSIG             // output 1 = replacement
    RET rewrite              // return

// ------------------------------------------------------------------------------------------------ partition
partition:                   // move the output gates to the end (in ascending order).  D = 0 already so, 1 reordered, 2 impossible
    LD ING                    // D = gates
    @2                       // A = 2
    D=D+A                    // D = E = signal of the last gate
    ST XD                    // XD = E
    IFLK O0, 3, pt_bad       // an output became an input signal
    IFK NO, 1, pt_one        // one output
    IFLK O1, 3, pt_bad       // second output became an input signal
    IFEQV O0, O1, pt_bad     // both outputs are the same gate
    IFLTV O0, O1, pt_ord     // O0 < O1
    CPY X0, O1               // lo = O1
    CPY X1, O0               // hi = O0
    GOTO pt_chk              // check
pt_ord:
    CPY X0, O0               // lo = O0
    CPY X1, O1               // hi = O1
pt_chk:
    IFNEV X1, XD, pt_move    // the larger output is not the last gate
    LD XD                    // D = E
    D=D-1                    // D = E - 1
    @X0                      // A = &lo
    D=D-M                    // D = E - 1 - lo
    IFNE pt_move             // the smaller output is not the second last
    GOTO pt_same             // already in place
pt_one:
    IFEQV O0, XD, pt_same    // the only output is the last gate
pt_move:
    IFK NO, 1, pt_m1         // one output: its signal
    IFLTV O0, O1, pt_m0      // the smaller output first
    CPY XC, O1               // S = O1
    GOTO pt_mv               // move it
pt_m0:
    CPY XC, O0               // S = O0
    GOTO pt_mv               // move it
pt_m1:
    CPY XC, O0               // S = O0
pt_mv:
    CALL pt_moveend          // move gate XC to the end
    IFK NO, 1, pt_topo       // one output: done
    IFEQV O0, XD, pt_o1      // O0 is now last: the other is O1
    CPY XC, O0               // S = O0
    GOTO pt_mv2              // move it
pt_o1:
    CPY XC, O1               // S = O1
pt_mv2:
    CALL pt_moveend          // move it to the end
    GOTO pt_topo             // check the order
pt_moveend:                  // gate XC goes to position XD (the end); gates above it move down; references are renamed (S -> E, above S -> one lower)
    LDI GA, XC               // D = a of S
    ST XA                    // keep
    LDI GB, XC               // D = b of S
    ST XB                    // keep
    CPY CI, XC               // from S
pt_sh:
    IFGEV CI, XD, pt_put     // all moved
    LD CI                    // D = CI
    D=D+1                    // D = CI + 1: the gate that moves down
    ST CJ                    // keep
    LDI GA, CJ               // D = its a
    STI GA, CI               // GA[CI] = it
    LDI GB, CJ               // D = its b
    STI GB, CI               // GB[CI] = it
    INCV CI                  // next
    GOTO pt_sh               // continue
pt_put:
    LD XA                    // D = a of S
    STI GA, XD               // at the end
    LD XB                    // D = b of S
    STI GB, XD               // at the end
    SET CI, 3                // rename the references
pt_adj:
    IFGTV CI, XD, pt_adjo    // all gates done
    LDI GA, CI               // D = a
    ST X2                    // keep
    ADJDN X2                 // rename
    LD X2                    // D = a
    STI GA, CI               // store
    LDI GB, CI               // D = b
    ST X2                    // keep
    ADJDN X2                 // rename
    LD X2                    // D = b
    STI GB, CI               // store
    INCV CI                  // next
    GOTO pt_adj              // continue
pt_adjo:
    ADJDN O0                 // outputs
    ADJDN O1                 // outputs
    RET pt_moveend           // return to the caller
pt_same:
    @0                       // A = 0
    D=A                      // D = 0
    RET partition            // already in place
pt_bad:
    @2                       // A = 2
    D=A                      // D = 2
    RET partition            // impossible
pt_topo:                     // every gate must use only lower signals
    SET CI, 3                // first gate
pt_t:
    IFGTV CI, XD, pt_ok      // all gates fine
    LDI GA, CI               // D = a
    ST X2                    // keep
    IFGEV X2, CI, pt_bad     // a is not below the gate
    LDI GB, CI               // D = b
    ST X2                    // keep
    IFGEV X2, CI, pt_bad     // b is not below the gate
    INCV CI                  // next gate
    GOTO pt_t                // continue
pt_ok:
    @1                       // A = 1
    D=A                      // D = 1: reordered
    RET partition            // return

// ------------------------------------------------------------------------------------------------ layout
.macro PB                    // put the byte D into RECB[WP], WP += 1
    STI RECB, WP             // RECB[WP] = D
    INCV WP                  // WP += 1
.endm

.macro SLOTOF v              // v = compact signal (gate) -> v = its slot in the record
    IFEQV \v, O0, so0\@      // output 0
    IFK NO, 2, so1c\@        // two outputs: maybe output 1
    GOTO sor\@               // an ordinary gate
so1c\@:
    IFEQV \v, O1, so1\@      // output 1
sor\@:                      // r-th free slot, r = v - 3
    LD \v                    // D = v
    @3                       // A = 3
    D=D-A                    // D = r
    ST \v                    // v = r
    IFGTV XE, \v, soa\@      // pinned slot PLO above r: no shift  (XE = PLO)
    INCV \v                  // PLO <= r: r + 1
soa\@:
    IFGTV XB, \v, sob\@      // pinned slot PHI above: no shift  (XB = PHI)
    INCV \v                  // PHI <= r: r + 1
sob\@:
    GOTO sod\@               // done
so0\@:
    CPY \v, P0               // pinned slot of output 0
    GOTO sod\@               // done
so1\@:
    CPY \v, P1               // pinned slot of output 1
sod\@:
.endm

layout:                      // build the improved record in RECB (format of the HD records, ROM_BASE + HD).  D = 0 fine, 1 impossible / too big
    SET WP, 0                // write index
    @1                       // A = 1
    D=A                      // D = flags: combinational, improvable
    PB                       // flags
    LD NIR                   // D = n_in
    PB                       // n_in
    LD NO                    // D = n_out
    PB                       // n_out
    LD SL                    // D = slots
    PB                       // slots
    SET HC, 0                // no pending holes
    SET SS, 0                // first slot
    IFK NO, 2, ly_two        // two outputs
    CPY XE, P0               // PLO = the only pin
    SET XB, 100              // PHI = none
    GOTO ly_s                // start
ly_two:
    IFLTV P0, P1, ly_o       // P0 < P1
    CPY XE, P1               // PLO
    CPY XB, P0               // PHI
    GOTO ly_s                // start
ly_o:
    CPY XE, P0               // PLO
    CPY XB, P1               // PHI
ly_s:                        // slot SS
    IFGEV SS, SL, ly_end     // all slots
    IFEQV SS, P0, ly_p0      // pinned output 0
    IFK NO, 2, ly_t1         // maybe pinned output 1
    GOTO ly_free             // an ordinary slot
ly_t1:
    IFEQV SS, P1, ly_p1      // pinned output 1
ly_free:                     // r = SS - number of pins below SS; gate 3 + r when r < ING - NO
    CPY X0, SS               // r = SS
    IFGEV P0, SS, ly_a       // P0 >= SS: not below
    DECV X0                  // pin 0 is below SS
ly_a:
    IFK NO, 2, ly_b          // second pin
    GOTO ly_c                // none
ly_b:
    IFGEV P1, SS, ly_c       // P1 >= SS: not below
    DECV X0                  // pin 1 is below SS
ly_c:
    LD ING                    // D = gates
    @NO                      // A = &NO
    D=D-M                    // D = number of non-output gates
    @X0                      // A = &r
    D=D-M                    // D = (ING - NO) - r
    IFLE ly_hole             // r >= ING - NO: a hole
    LD X0                    // D = r
    @3                       // A = 3
    D=D+A                    // D = gate signal
    ST X1                    // the gate
    GOTO ly_gate             // emit it
ly_p0:
    CPY X1, O0               // the gate of output 0
    GOTO ly_gate             // emit it
ly_p1:
    CPY X1, O1               // the gate of output 1
    GOTO ly_gate             // emit it
ly_hole:
    INCV HC                  // one more hole
    INCV SS                  // next slot
    GOTO ly_s                // continue
ly_gate:                     // X1 = gate signal: flush holes, then emit
    LD HC                    // D = pending holes
    IFEQ ly_g1               // none
    CALL ly_flush            // emit the skip entry
    IFNE ly_rej              // did not fit
ly_g1:
    LD WP                    // D = bytes written
    @3                       // A = 3
    D=D+A                    // D = after this entry
    @NO                      // A = &NO
    D=D+M                    // D = plus the output list
    @REC_MAX+1               // A = limit + 1
    D=D-A                    // D = excess
    IFGE ly_rej              // would not fit
    LDI GA, X1               // D = a
    ST X2                    // a
    LDI GB, X1               // D = b
    ST X3                    // b
    IFLK X2, 3, ly_ma        // an input: number unchanged
    SLOTOF X2                // its slot
    LD X2                    // D = slot
    @NIR                     // A = &NIR
    D=D+M                    // D = record signal number
    ST X2                    // a (record numbering)
ly_ma:
    IFLK X3, 3, ly_mb        // an input: number unchanged
    SLOTOF X3                // its slot
    LD X3                    // D = slot
    @NIR                     // A = &NIR
    D=D+M                    // D = record signal number
    ST X3                    // b (record numbering)
ly_mb:
    LD SS                    // D = slot of this gate
    @NIR                     // A = &NIR
    D=D+M                    // D = its own record signal
    ST X0                    // keep
    IFGEV X2, X0, ly_rej     // a must be below the gate
    IFGEV X3, X0, ly_rej     // b must be below the gate
    @0                       // A = 0
    D=A                      // D = kind NAND
    PB                       // kind
    LD X2                    // D = a
    PB                       // a
    LD X3                    // D = b
    PB                       // b
    INCV SS                  // next slot
    GOTO ly_s                // continue
ly_flush:                    // emit a skip entry for HC pending holes.  D = 0 fine, 1 does not fit
    LD WP                    // D = bytes written
    @3                       // A = 3
    D=D+A                    // D = after the entry
    @NO                      // A = &NO
    D=D+M                    // D = plus the output list
    @REC_MAX+1               // A = limit + 1
    D=D-A                    // D = excess
    IFGE ly_fl_no            // would not fit
    @2                       // A = 2
    D=A                      // D = kind 2
    PB                       // kind
    LD HC                    // D = holes
    PB                       // count
    @0                       // A = 0
    D=A                      // D = 0
    PB                       // padding
    SET HC, 0                // none pending
    @0                       // A = 0
    D=A                      // D = 0: fine
    RET ly_flush             // return
ly_fl_no:
    @1                       // A = 1
    D=A                      // D = 1: does not fit
    RET ly_flush             // return
ly_end:
    LD HC                    // D = pending holes
    IFEQ ly_outs             // none
    CALL ly_flush            // emit the skip entry
    IFNE ly_rej              // did not fit
ly_outs:
    LD NIR                   // D = n_in
    @P0                      // A = &P0
    D=D+M                    // D = record signal of output 0
    PB                       // output 0
    IFK NO, 2, ly_out2       // two outputs
    GOTO ly_fin              // one
ly_out2:
    LD NIR                   // D = n_in
    @P1                      // A = &P1
    D=D+M                    // D = record signal of output 1
    PB                       // output 1
ly_fin:
    CPY RECN, WP             // record length
    @0                       // A = 0
    D=A                      // D = 0
    RET layout               // fine
ly_rej:
    @1                       // A = 1
    D=A                      // D = 1
    RET layout               // impossible or too big

// ------------------------------------------------------------------------------------------------ improve_type
improve_type:                // ITY = type.  IMPR = 1 and the improved record at RECB (RECN bytes), or IMPR = 0.
    SET IMPR, 0              // nothing yet
    @ITY                     // A = &type
    D=M                      // D = type
    D=D+M                    // D = 2 * type
    @hd_dir                  // A = directory (aligned: no carry out of the low byte)
    A=D+A                    // A = directory slot
    D=M                      // D = record address, low byte
    ST IP                     // IP.low
    @ITY                     // A = &type
    D=M                      // D = type
    D=D+M                    // D = 2 * type
    @hd_dir                  // A = directory
    A=D+A                    // A = directory slot
    A=A+1                    // A = slot + 1
    D=M                      // D = record address, high byte
    ST IP+1                   // IP.high
    CALL load                // the record into the gate arrays
    IFNE imp_ret             // not for us
    CALL compact             // merge, drop holes and dead gates
imp_restart:                 // (re)start the search for an improvement
    SET RT, 3                // first root
imp_root:
    LD RT                    // D = root
    @ING                      // A = &ING
    D=D-M                    // D = root - gates
    @3                       // A = 3
    D=D-A                    // D = root - end signal
    IFGE imp_part            // all roots examined: nothing more to improve
    SET LKV, 0               // no previous cut for this root
imp_cut:
    CALL nextcut             // the next cut of this root
    LD BF                    // D = found
    IFEQ imp_nextroot        // no more cuts
    CPY LK, BL               // remember it as the previous cut
    CPY LK+1, BL+1           // ..
    CPY LK+2, BL+2           // ..
    CPY LK+3, BL+3           // ..
    SET LKV, 1               // a previous cut exists
    CALL cone                // saved gates and the truth table over the cut
    IFNE imp_leaf            // the root equals a leaf
    LD SAVD                  // D = saved gates
    D=D-1                    // D = gates that may be used
    ST GMX                   // maximum number of new gates
    IFLK GMX, 1, imp_cut     // nothing could be gained
    IFLK GMX, 7, imp_gm      // at most 6
    SET GMX, 6               // GMAX
imp_gm:
    CALL search              // exhaustive search
    IFEQ imp_cut             // none: next cut
    CPY NN, SG               // new gates
    CALL rewrite             // insert them and rewire
    CALL compact             // clean up
    GOTO imp_restart         // start again
imp_leaf:
    SET NN, 0                // no new gates
    CALL rewrite             // rewire the users of the root to the leaf
    CALL compact             // clean up
    GOTO imp_restart         // start again
imp_nextroot:
    INCV RT                  // next root
    GOTO imp_root            // continue
imp_part:                    // outputs must be the last gates, ascending (the slot layout of the record)
    CALL partition           // 0 in place, 1 reordered, 2 impossible
    IFEQ imp_gain            // already in place
    D=D-1                    // 1 -> 0
    IFEQ imp_restart         // reordered: improve again
    GOTO imp_ret             // impossible: leave the module alone
imp_gain:
    LD ING                    // D = gates now
    @REAL                    // A = &REAL
    D=D-M                    // D = gates now - gates before
    IFGE imp_ret             // no gain
    CALL layout              // slot form
    IFNE imp_ret             // does not fit
    SET IMPR, 1              // the improved record is in RECB
imp_ret:
    RET improve_type         // return

// ------------------------------------------------------------------------------------------------ ROM tables (one aligned page: indexed by adding the index to the low byte)
.org ROM_BASE + 0x3280      // after the code, in one page (HD_OFF = 0x32E0 follows the tables)
vtab:                        // truth tables of the three variables
    .byte 0xAA, 0xCC, 0xF0   // variable 0 / 1 / 2 over 8 rows
ftab:                        // table masks for 1, 2, 3 leaves (index = number of leaves, entry 0 unused)
    .byte 0x00, 0x03, 0x0F, 0xFF   // 0 leaves (unused), 1 leaf: 2 rows, 2 leaves: 4 rows, 3 leaves: 8 rows
btab:                        // bit index (0..39) -> byte number
    .byte 0,0,0,0,0,0,0,0    // bits 0..7 are in byte 0
    .byte 1,1,1,1,1,1,1,1    // bits 8..15 are in byte 1
    .byte 2,2,2,2,2,2,2,2    // bits 16..23 are in byte 2
    .byte 3,3,3,3,3,3,3,3    // bits 24..31 are in byte 3
    .byte 4,4,4,4,4,4,4,4    // bits 32..39 are in byte 4
mtab:                        // bit index (0..39) -> mask
    .byte 1,2,4,8,16,32,64,128   // bits 0..7 of byte 0
    .byte 1,2,4,8,16,32,64,128   // bits 0..7 of byte 1
    .byte 1,2,4,8,16,32,64,128   // bits 0..7 of byte 2
    .byte 1,2,4,8,16,32,64,128   // bits 0..7 of byte 3
    .byte 1,2,4,8,16,32,64,128   // bits 0..7 of byte 4
