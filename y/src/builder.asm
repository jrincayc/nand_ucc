// builder.asm -- the Y builder (flattener): reads the hardware description (hd_data.asm) from ROM and builds a copy of
// the machine through the arm (PLACE every part, copy the ROM, WIRE everything, wire EN, wire RUN last).  M4, Hack-vN-AB.
//
// The program is a direct transcription of ref_flatten.commands() (tools/ref_flatten.py).  Geometry (all coordinates are
// relative to the arm that issues the command, spec v0.5):
//     child arm origin (0, STRIDE=140);  child ROM at (0, 149);  core node i at (6+2i, 149), the tie-high NAND is node n_core;
//     RAM tile k, node j at (6+2k, 153+2j).   NAND pins: A (x,y) B (x,y+1) Y (x+1,y);  DFF pins: D (x,y) Q (x+1,y).
// Two passes over the same description: MODE 0 places the parts, then the ROM is copied; MODE 1 wires.
// Registers of the arm: 0,1 A.x  2,3 A.y  4,5 B.x  6,7 B.y  8 KIND  9 ANGLE  10 VAL  15 CMD.  CMD 1 PLACE, 2 WIRE, 3 PROGRAM_ROM.
//
// A "source" is 5 bytes: x (2), y (2) of the OUTPUT pin that drives an input, and a flag byte (1 = the RUN line).
// Subroutines (CALL / RET macros, return address in RA_<name>): rdb add16 put5 lookup decref resolve emit gates.

.equ ARM,     ARM_BASE       // first arm register (ROM_BASE - 16), predefined by the assembler
.equ NODE_X0, 6              // x of core node 0
.equ ROW_Y,   149            // y of the core row and of the ROM origin (STRIDE 140 + arm height 9)
.equ TILE_Y,  153            // y of tile node 0 (ROM origin + 4)
.equ ARM_Y,   140            // y of the child's arm origin (= STRIDE)

// (the RAM variables are defined in ram.asm)

// ================================================================================================== main
// Flow (M5): the child's ROM and arm are placed first; then two phases over the same description.  A phase walks the body once per
// module type (group TSEL = 0 .. 15); only the instances of type TSEL are placed (phase 0) or wired (phase 1), the other
// instances are stepped over.  At the start of each group the improver is run on the record of type TSEL; when it improves it,
// the improved record is in RECB and this group (and only this group) reads that record instead of the one in ROM.
// Phase 0 also programs each type's record (improved or not) into the child's ROM; the rest of the ROM is copied after the groups.
start:                       // reset lands here (ROM_BASE)
    SET MODE, 0              // phase 0 places
    SET TSEL, 16             // no type selected
    SET IMPR, 0              // no improved record
    SET PSEL, P              // rdb reads through P
    SET16 TIEX, 0            // not known before the body has been walked once
    SET RUNP, RUNS           // next free RUN sink slot
    SET AUH, 0               // add16 addend high byte is 0 between calls
    SET PB+4, 0              // the pin-base slot is never RUN
    // ---- the chain record: tile module type and tile count
    SET16 P, hd_chain        // P -> chain record
    CALL rdb                 // D = tile module type
    ST TY8                   // keep it
    CALL rdb                 // D = number of tiles
    ST WN                    // index of the LAST tile, W - 1 (W = 256 does not fit a byte)
    CALL lookup              // MP = tile record, NIN/NG = its inputs and gates
    COPY16 TMP, MP           // keep the tile record
    LD NIN                   // D = tile inputs
    ST TNIN                  // keep
    LD NG                    // D = tile gates
    ST TG                    // keep
    // TOUTP = TMP + 4 + 3 * TG  (the list of output signals follows the gates)
    COPY16 TOUTP, TMP        // start at the record
    LD TG                    // D = TG
    D=D+M                    // D = 2 TG
    D=D+M                    // D = 3 TG
    @4                       // A = 4
    D=D+A                    // D = 3 TG + 4
    ST AUL                   // addend low
    SET ADST, TOUTP          // add to TOUTP
    CALL add16               // TOUTP done
    // RAMX = 7 + 2 (W-1)  (x of the output pins of the last tile column: 6 + 2 (W-1) + 1)
    SET16 RAMX, 7            // 7
    SET ADST, RAMX           // add to RAMX
    LD WN                    // D = W - 1
    ST AUL                   // addend low
    CALL add16               // RAMX = 7 + (W-1)
    LD WN                    // D = W - 1 (add16 does not keep AUL)
    ST AUL                   // addend low
    CALL add16               // RAMX = 7 + 2 (W-1)  (a 16-bit sum: 2 W can exceed 255)

    // ---- place the child's ROM and arm first (PROGRAM_ROM needs the ROM; nothing is wired before phase 1)
    WRK 0, 0                 // A.x low = 0 (ROM at x = 0)
    WRK 1, 0                 // A.x high
    WRK 2, ROW_Y             // A.y low = 149
    WRK 3, 0                 // A.y high
    WRK 8, 2                 // KIND = ROM
    WRK 9, 0                 // ANGLE = 0
    WRK 15, 1                // CMD = PLACE
    WRK 2, ARM_Y             // A.y low = 140 (the child's arm)
    WRK 8, 3                 // KIND = ARM
    WRK 15, 1                // CMD = PLACE

phase:                       // ---- start of a phase: all groups
    SET TSEL, 0              // first type
group:
    LD TSEL                  // D = type
    @16                      // A = 16
    D=D-A                    // D = TSEL - 16
    IFGE phase_done          // all types done
    LD TSEL                  // D = type
    DBL                      // D = 2 * type
    @hd_dir                  // A = directory (aligned)
    A=D+A                    // A = slot
    A=A+1                    // A = slot + 1 (high byte of the record address; 0 = empty slot)
    D=M                      // D = it
    IFEQ group_next          // no such type
    LD TSEL                  // D = type
    ST ITY                   // the improver works on this type
    CALL improve_type        // IMPR, RECB, RECN   (clobbers every temporary; the persistent block survives)
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE no_prog             // phase 1: the ROM is already programmed
    CALL progrec             // PROGRAM_ROM the record of this type
no_prog:
    SET PSEL, P              // rdb reads through P
    SET PB+4, 0              // the pin-base slot is never RUN
    SET AUH, 0               // add16 addend high byte
    SET16 P, hd_body         // P -> first instance
    SET16 NB, NODE_X0        // node 0 is at x = 6 ...
    SET16 NB+2, ROW_Y        // ... y = 149
inst_next:                   // ---- next body instance
    SET PSEL, P              // read through P
    CALL rdb                 // D = type (0xFF = END)
    ST TY8                   // keep it
    D=D+1                    // 0xFF + 1 = 0 -> END
    IFEQ body_end            // leave the loop at END
    CALL lookup              // MP, NIN, NG for this type; GP -> first gate
    LD TY8                   // D = type of this instance
    @TSEL                    // A = &TSEL
    D=D-M                    // zero when it is the type of this group
    IFEQ inst_sel            // ours
    CALL skiprefs            // not ours: step over its references ...
    LD NG                    // D = its slots
    DBL                      // D = 2 * slots
    ST AUL                   // addend low
    SET ADST, NB             // x of the next instance ...
    CALL add16               // ... = x + 2 * slots
    GOTO inst_next           // next instance
inst_sel:
    @IMPR                    // A = &IMPR
    D=M                      // D = 1 when the record of this type was improved
    IFEQ inst_rec            // no: gates come from ROM
    SET16 GP, RECB+4         // yes: gates come from the improved record in RAM (same format)
inst_rec:
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE inst_decode         // phase 1: wire, which needs the sources
    CALL skiprefs            // phase 0: only place; the references are not needed
    GOTO inst_walk           // go
inst_decode:
    // reference base: XR = x of the output pin of the instance's first node = NB.x + 1 (NB.x is even)
    LD NB                    // D = NB.x low
    @1                       // A = 1
    D=D|A                    // D = NB.x low | 1
    ST XR                    // XR.low
    LD NB+1                  // D = NB.x high
    ST XR+1                  // XR.high
    // decode the input references into SRC[0..NIN-1]
    SET RESP, SRC            // results are written starting at SRC
    LD NIN                   // D = number of inputs
    ST SN                    // loop counter
src_loop:                    // for each input reference
    LD SN                    // D = refs left
    IFEQ src_done            // none left
    CALL decref              // decode one reference into the slot at RESP (RESP advances by 5)
    @SN                      // A = &SN
    M=M-1                    // one less
    GOTO src_loop            // next
src_done:
    COPY16 PB, XR            // pin base: x of the output pin of node 0 ...
    COPY16 PB+2, NB+2        // ... and its y
inst_walk:
    SET WALK, 0              // walking a core instance
    COPY16 CUR, NB           // current node = first node
    COPY16 CUR+2, NB+2       // (y)
    CALL gates               // place or wire every gate of the instance
    COPY16 NB, CUR           // the next instance starts where this one ended
    GOTO inst_next           // next instance

body_end:                    // END of the body reached
    COPY16 TIEX, NB          // TIEX = x of the tie-high node (the same in every walk)
group_next:
    @TSEL                    // A = &TSEL
    M=M+1                    // next type
    GOTO group               // go

phase_done:                  // ---- all groups done: the tie-high node and the RAM tiles
    COPY16 NB, TIEX          // the tie-high node is at the end of the core row ...
    SET16 NB+2, ROW_Y        // ... y = 149
    @MODE                    // A = &MODE
    D=M                      // D = pass
    IFNE no_tie              // wiring phase: the tie node needs no command
    SET EK, 0                // the tie-high node is a NAND with unconnected inputs
    COPY16 CUR, NB           // at the end of the core row
    COPY16 CUR+2, NB+2       // (y)
    CALL emit                // PLACE it
no_tie:
    // ---- the RAM tiles: one column per byte, tile k at x = 6 + 2k.  Chain references are relative to the tie node.
    LD TIEX                  // D = TIEX.low (even)
    @1                       // A = 1
    D=D|A                    // + 1: output pin of the tie node
    ST XR                    // XR.low
    LD TIEX+1                // D = TIEX.high
    ST XR+1                  // XR.high
    SET KT, 0                // tile 0
    SET16 NB, NODE_X0        // column 0 is at x = 6 ...
    SET16 NB+2, TILE_Y       // ... starting at y = 153
tile_loop:                   // for k = 0 .. W-1 (the test for the last tile is at the end: k = 255 is a valid index)
    COPY16 GP, TMP           // GP -> tile record
    ADDI GP, 4               // skip the 4 header bytes: GP -> first gate
    LD TNIN                  // D = tile inputs
    ST NIN                   // (resolve compares signals with NIN)
    LD TG                    // D = tile gates
    ST NG                    // gates to do
    LD NB                    // D = column x low (even)
    @1                       // A = 1
    D=D|A                    // + 1 = x of the tile's output pins
    ST PB                    // PB.x low
    LD NB+1                  // D = column x high
    ST PB+1                  // PB.x high
    COPY16 PB+2, NB+2        // PB.y = y of tile node 0
    SET WALK, 1              // walking a tile
    COPY16 CUR, NB           // current node = node 0 of the column
    COPY16 CUR+2, NB+2       // (y)
    CALL gates               // place or wire the gates of the tile
    LD KT                    // D = k
    @WN                      // A = &WN
    D=D-M                    // zero after the last tile (an equality test: safe for k >= 128)
    IFEQ tiles_done          // all tiles done
    @KT                      // A = &KT
    M=M+1                    // next tile
    ADDI NB, 2               // next column: x += 2
    GOTO tile_loop           // continue

tiles_done:
    @MODE                    // A = &MODE
    D=M                      // D = pass
    IFNE pass2_tail          // wiring phase: ports, EN and RUN remain
    // ---- end of phase 0: copy the rest of the ROM image.  The record area (hd_mods .. hd_mods_end) was programmed type by type.
    // PROGRAM_ROM: A = ROM origin, B.x = address, VAL = byte; zero bytes are skipped (unprogrammed cells read 0)
    WRK 0, 0                 // A.x low = 0 (ROM at x = 0)
    WRK 1, 0                 // A.x high
    WRK 2, ROW_Y             // A.y = 149 (origin of the ROM)
    WRK 3, 0                 // A.y high
    SET16 CA, 0              // ROM offset 0
    SET16 P, ROM_BASE        // read pointer = start of this ROM
    SET PSEL, P              // rdb reads through P
rom_loop:                    // for every ROM address
    LD P+1                   // D = read pointer high
    @hi(hd_mods)             // A = high byte of the start of the record area
    D=D-A                    // zero when in that page
    IFNE rom_go              // no
    LD P                     // D = read pointer low
    @lo(hd_mods)             // A = low byte of the start of the record area
    D=D-A                    // zero at the start of the record area
    IFNE rom_go              // no
    SET16 P, hd_mods_end     // jump over the record area ...
    LD P                     // ... the offset follows: CA.low = P.low
    ST CA                    // store
    LD P+1                   // D = P.high
    @hi(ROM_BASE)            // A = ROM_BASE high byte
    D=D-A                    // D = offset high
    ST CA+1                  // CA.high
rom_go:
    CALL rdb                 // D = ROM byte at P; P += 1
    ST VALV                  // keep it
    IFEQ rom_skip            // zero: nothing to program
    WRA 4, CA                // B.x low = offset
    WRA 5, CA+1              // B.x high
    WRA 10, VALV             // VAL = byte
    WRK 15, 3                // CMD = PROGRAM_ROM
rom_skip:
    INC16 CA                 // next offset
    LD CA+1                  // D = offset high
    @hi(ROM_BASE)            // A = high byte of the ROM size (ROM_BASE = 2^(AB-1) = the ROM size)
    D=D-A                    // zero when the offset reached the end
    IFNE rom_loop            // more to do
    SET MODE, 1              // phase 1: wiring
    GOTO phase               // walk everything again


pass2_tail:                  // ---- ports, then EN (the last port), then RUN
    SET16 P, hd_ports        // P -> ports record
    CALL rdb                 // D = number of ports
    ST NP                    // ports left
port_loop:                   // for each port
    LD NP                    // D = ports left
    IFEQ ports_done          // none
    SET RESP, IN             // decref result goes to IN
    CALL decref              // IN = source pin of this port
    CALL rdb                 // D = sink pin x
    ST T0                    // keep
    CALL rdb                 // D = sink pin y
    ST T1                    // keep
    WRA 0, IN                // A.x low = source x low
    WRA 1, IN+1              // A.x high
    WRA 2, IN+2              // A.y low
    WRA 3, IN+3              // A.y high
    WRA 4, T0                // B.x low = sink x
    WRK 5, 0                 // B.x high = 0
    WRA 6, T1                // B.y low = sink y
    WRK 7, 0                 // B.y high = 0
    WRK 15, 2                // CMD = WIRE
    @NP                      // A = &NP
    M=M-1                    // one less
    GOTO port_loop           // next port
ports_done:
    // RUN wires last: from the output pin of the tie node to every recorded sink pin
    LD TIEX                  // D = tie node x low
    @1                       // A = 1
    D=D|A                    // + 1 = output pin of the tie node
    ST TY                    // TY = its x low (TY reused as scratch)
    LD TIEX+1                // D = tie node x high
    ST TY+1                  // TY.high
    SET RUNN, RUNS           // read pointer = first recorded sink
run_loop:                    // for each recorded sink
    LD RUNN                  // D = read pointer
    @RUNP                    // A = &write pointer
    D=D-M                    // zero when all sinks have been wired
    IFEQ halt                // done
    WRA 0, TY                // A.x low = tie output pin x low
    WRA 1, TY+1              // A.x high
    WRK 2, ROW_Y             // A.y low = 149
    WRK 3, 0                 // A.y high
    @RUNN                    // A = &read pointer
    A=M                      // A = address of the sink's x low
    D=M                      // D = x low
    @ARM+4                   // A = B.x low register
    M=D                      // write it
    @RUNN                    // A = &read pointer
    A=M+1                    // A = address of x high
    D=M                      // D = x high
    @ARM+5                   // A = B.x high register
    M=D                      // write it
    @RUNN                    // A = &read pointer
    D=M                      // D = read pointer
    @2                       // A = 2
    A=D+A                    // A = address of y low
    D=M                      // D = y low
    @ARM+6                   // A = B.y low register
    M=D                      // write it
    @RUNN                    // A = &read pointer
    D=M                      // D = read pointer
    @3                       // A = 3
    A=D+A                    // A = address of y high
    D=M                      // D = y high
    @ARM+7                   // A = B.y high register
    M=D                      // write it
    WRK 15, 2                // CMD = WIRE
    @RUNN                    // A = &read pointer
    D=M                      // D = read pointer
    @4                       // A = 4
    D=D+A                    // + 4 bytes per sink
    @RUNN                    // A = &read pointer
    M=D                      // store
    GOTO run_loop            // next sink
halt:                        // finished: the child is built; the model's halt convention
    @halt                    // A = &halt
    0;JMP                    // jump to self

// ================================================================================================== subroutines
rdb:                         // D = ROM byte at the pointer whose RAM address is in PSEL; that pointer += 1
    @PSEL                    // A = &PSEL
    A=M                      // A = address of the pointer variable
    AP                       // A = the pointer's value (a ROM address)
    D=M                      // D = the ROM byte
    @RDV                     // A = &RDV
    M=D                      // keep the byte
    @PSEL                    // A = &PSEL
    A=M                      // A = address of the pointer variable
    M=M+1                    // pointer.low += 1
    D=M                      // D = new low byte
    @rdb_done                // A = target
    D;JNE                    // no carry unless the low byte became 0
    @PSEL                    // A = &PSEL
    A=M+1                    // A = address of pointer.high
    M=M+1                    // pointer.high += 1
rdb_done:
    @RDV                     // A = &RDV
    D=M                      // D = the byte
    RET rdb                  // return

add16:                       // the 16-bit variable at RAM address ADST += (AUH:AUL), unsigned wrap-around; AUH is cleared
    @ADST                    // A = &ADST
    A=M                      // A = address of the variable (low byte)
    D=M                      // D = its low byte
    @AO                      // A = &AO
    M=D                      // AO = old low byte
    @AUL                     // A = &AUL
    D=D+M                    // D = old + addend low (mod 256)
    @AN                      // A = &AN
    M=D                      // AN = new low byte
    @AO                      // A = &AO
    D=M                      // D = old
    @AUL                     // A = &AUL
    D=D&M                    // D = old & addend
    @AC                      // A = &AC
    M=D                      // AC = old & addend
    @AO                      // A = &AO
    D=M                      // D = old
    @AUL                     // A = &AUL
    D=D|M                    // D = old | addend
    @AX                      // A = &AX
    M=D                      // AX = old | addend
    @AN                      // A = &AN
    D=!M                     // D = ~new
    @AX                      // A = &AX
    D=D&M                    // D = (old | addend) & ~new
    @AC                      // A = &AC
    D=D|M                    // bit 7 of D is the carry out of the low byte
    @AH                      // A = &AH
    M=0                      // assume no carry
    @add16_nc                // A = target
    D;JGE                    // bit 7 clear: no carry
    @AH                      // A = &AH
    M=1                      // carry
add16_nc:
    @AN                      // A = &AN
    D=M                      // D = new low byte
    @ADST                    // A = &ADST
    A=M                      // A = address of the variable
    M=D                      // store the low byte
    @AUH                     // A = &AUH
    D=M                      // D = addend high
    @AH                      // A = &AH
    D=D+M                    // D = addend high + carry
    @ADST                    // A = &ADST
    A=M+1                    // A = address of the high byte
    M=D+M                    // high byte += D
    @AUH                     // A = &AUH
    M=0                      // addend high is 0 again for the next caller
    RET add16                // return

put5:                        // copy 5 bytes from RAM[SPT..] to RAM[RESP..]; RESP += 5
    SET SK, 5                // five bytes
put5_loop:
    @SPT                     // A = &SPT
    A=M                      // A = source byte address
    D=M                      // D = the byte
    PUT RESP                 // store it at the destination and advance RESP
    @SPT                     // A = &SPT
    M=M+1                    // next source byte
    @SK                      // A = &SK
    M=M-1                    // one less
    D=M                      // D = bytes left
    IFNE put5_loop           // repeat
    RET put5                 // return

skiprefs:                    // step over the NIN reference bytes of the current instance at P (no decoding)
    SET PSEL, P              // read through P
    LD NIN                   // D = references
    ST SN                    // loop counter
sk_loop:
    LD SN                    // D = references left
    IFEQ sk_done             // none
    CALL rdb                 // D = reference byte
    @3                       // A = 3
    D=D+A                    // D = byte + 3 (mod 256): 0 for 0xFD, 1 for 0xFE
    IFEQ sk_far              // 0xFD: two more bytes follow
    D=D-1                    // 1 for 0xFE
    IFNE sk_next             // an ordinary one-byte reference
sk_far:
    CALL rdb                 // distance low
    CALL rdb                 // distance high
sk_next:
    @SN                      // A = &SN
    M=M-1                    // one less
    GOTO sk_loop             // next
sk_done:
    RET skiprefs             // return

progrec:                     // PROGRAM_ROM the record of type TSEL into the child at the same ROM address (the improved record when IMPR)
    LD TSEL                  // D = type
    ST TY8                   // lookup works on TY8
    CALL lookup              // MP = record in ROM, NG = its slots, NOUT = its outputs
    @IMPR                    // A = &IMPR
    D=M                      // D = 1 when improved
    IFEQ pg_rom              // no
    LD RECN                  // D = length of the improved record
    ST PL                    // bytes to program
    SET16 GP, RECB           // source = the improved record in RAM
    GOTO pg_go               // go
pg_rom:
    LD NG                    // D = slots (the extent of the record is fixed: 4 + 3 slots + outputs)
    D=D+M                    // 2 slots
    D=D+M                    // 3 slots
    @4                       // A = 4
    D=D+A                    // + 4 header bytes
    @NOUT                    // A = &NOUT
    D=D+M                    // + outputs
    ST PL                    // bytes to program
    COPY16 GP, MP            // source = the record in ROM
pg_go:
    LD MP                    // D = record address low
    ST CA                    // ROM offset low
    LD MP+1                  // D = record address high
    @hi(ROM_BASE)            // A = ROM_BASE high byte
    D=D-A                    // D = offset high
    ST CA+1                  // ROM offset high
    WRK 0, 0                 // A.x low = 0 (ROM at x = 0)
    WRK 1, 0                 // A.x high
    WRK 2, ROW_Y             // A.y = 149
    WRK 3, 0                 // A.y high
    SET PSEL, GP             // read the source through GP
pg_loop:
    LD PL                    // D = bytes left
    IFEQ pg_done             // none
    CALL rdb                 // D = next byte
    ST VALV                  // keep
    IFEQ pg_skip             // zero: nothing to program
    WRA 4, CA                // B.x low = offset
    WRA 5, CA+1              // B.x high
    WRA 10, VALV             // VAL = byte
    WRK 15, 3                // CMD = PROGRAM_ROM
pg_skip:
    INC16 CA                 // next offset
    @PL                      // A = &PL
    M=M-1                    // one byte less
    GOTO pg_loop             // next
pg_done:
    SET PSEL, P              // back to P
    RET progrec              // return

lookup:                      // TY8 = type -> MP = its record, NIN, NG from the header, GP -> first gate
    LD TY8                   // D = type
    DBL                      // D = 2 * type = byte offset in the directory
    @hd_dir                  // A = directory (aligned: no carry out of the low byte)
    A=D+A                    // A = slot of the record address
    D=M                      // D = record address, low byte
    ST MP                    // MP.low
    LD TY8                   // D = type
    DBL                      // D = 2 * type
    @hd_dir                  // A = directory
    A=D+A                    // A = slot
    A=A+1                    // A = slot + 1
    D=M                      // D = record address, high byte
    ST MP+1                  // MP.high
    COPY16 GP, MP            // GP -> record header
    SET PSEL, GP             // read through GP
    CALL rdb                 // flags (ignored)
    CALL rdb                 // n_in
    ST NIN                   // inputs
    CALL rdb                 // n_out
    ST NOUT                  // keep (progrec needs the record length)
    CALL rdb                 // n_gates
    ST NG                    // gates
    SET PSEL, P              // back to P
    RET lookup               // return

decref:                      // decode one reference at P (format: hd2asm.py header); relative to XR; 5-byte result at RESP
    SET PSEL, P              // read through P
    CALL rdb                 // D = reference byte
    ST DB                    // keep it
    IFLT dec_big             // 0x80 and above: special sources
    DBL                      // 1..127: node b back; D = 2b
    D=!D                     // ~(2b), low byte
    ST AUL                   // addend low
    SET AUH, 255             // addend high (the 16-bit value is ~(2b))
    SET BK, 1                // backward: add 1 afterwards  (x = XR + ~(2b) + 1 = XR - 2b)
    GOTO dec_core            // do the arithmetic
dec_big:
    LD DB                    // D = reference byte
    @127                     // A = 0x7F
    D=D&A                    // D = byte - 0x80
    ST EV                    // keep
    @8                       // A = 8
    D=D-A                    // D = EV - 8
    IFLT dec_rom             // EV 0..7: ROM data bit EV
    IFEQ dec_tie             // EV 8: tie-high node
    D=D-1                    // D = EV - 9
    IFEQ dec_run             // EV 9: RUN
    LD EV                    // D = EV
    @18                      // A = 18
    D=D-A                    // D = EV - 18
    IFLT dec_ramrd           // EV 10..17: RAM read bit EV-10
    LD EV                    // D = EV
    @125                     // A = 125 (0xFD)
    D=D-A                    // D = EV - 125
    IFEQ dec_far_back        // 0xFD: far backward
    SET BK, 0                // 0xFE: far forward
    GOTO dec_far             // read the 16-bit distance
dec_far_back:
    SET BK, 1                // backward
dec_far:
    CALL rdb                 // D = distance low byte
    ST T0                    // keep
    CALL rdb                 // D = distance high byte
    ST T1                    // keep
    LD T0                    // D = distance low
    DBL                      // D = 2 * low (mod 256)
    ST AUL                   // addend low
    LD T1                    // D = distance high
    DBL                      // D = 2 * high
    ST AUH                   // addend high (carry from the low byte follows)
    LD T0                    // D = distance low
    IFGE far_nc              // low byte < 128: doubling did not carry
    @AUH                     // A = &AUH
    M=M+1                    // carry into the high byte
far_nc:
    LD BK                    // D = 1 when backward
    IFEQ dec_core            // forward: addend is 2d
    LD AUL                   // backward: one's complement of 2d
    D=!D                     // ~low
    ST AUL                   // store
    LD AUH                   // D = high
    D=!D                     // ~high
    ST AUH                   // store
dec_core:                    // RX = XR + (AUH:AUL) (+1 when backward)
    COPY16 RX, XR            // start from the reference pin
    SET ADST, RX             // add to RX
    CALL add16               // RX += addend
    LD BK                    // D = 1 when backward
    IFEQ dec_core2           // forward: done
    ADDI RX, 1               // two's complement: ~v + 1
dec_core2:
    SET16 RY, ROW_Y          // core nodes are on the core row
    SET RFL, 0               // not RUN
    GOTO dec_out             // store the result
dec_rom:                     // ROM data pin EV: at (1, 149 + EV)
    SET16 RX, 1              // x = 1 (ROM at x = 0, data pins in column 1)
    @ROW_Y                   // A = 149
    D=A                      // D = 149
    @EV                      // A = &EV
    D=D+M                    // D = 149 + EV
    ST RY                    // RY.low
    SET RY+1, 0              // RY.high
    SET RFL, 0               // not RUN
    GOTO dec_out             // store the result
dec_tie:
    SET RFL, 0               // tie-high node
    GOTO dec_tp              // share the pin computation
dec_run:
    SET RFL, 1               // RUN: same pin as the tie node, but wired last
dec_tp:
    LD TIEX                  // D = tie node x low
    @1                       // A = 1
    D=D|A                    // + 1: its output pin
    ST RX                    // RX.low
    LD TIEX+1                // D = high
    ST RX+1                  // RX.high
    SET16 RY, ROW_Y          // on the core row
    GOTO dec_out             // store the result
dec_ramrd:                   // RAM read bit j = EV - 10: output signal outs[8 + j] of the last tile
    COPY16 TP, TOUTP         // TP -> list of tile output signals
    LD EV                    // D = EV
    @2                       // A = 2
    D=D-A                    // D = EV - 2 = 8 + j
    ST AUL                   // addend low
    SET ADST, TP             // add to TP
    CALL add16               // TP -> outs[8 + j]
    SET PSEL, TP             // read through TP
    CALL rdb                 // D = output signal number
    ST T0                    // keep
    SET PSEL, P              // back to P
    COPY16 RX, RAMX          // x of the last tile column's output pins
    LD T0                    // D = signal
    @TNIN                    // A = &TNIN
    D=D-M                    // D = gate index inside the tile
    DBL                      // D = 2 * index
    ST AUL                   // addend low
    SET16 RY, TILE_Y         // y of tile node 0
    SET ADST, RY             // add to RY
    CALL add16               // RY = 153 + 2 * index
    SET RFL, 0               // not RUN
dec_out:                     // store RES (RX, RY, RFL) at RESP
    SET SPT, RES             // source = the result block
    CALL put5                // copy it
    RET decref               // return

resolve:                     // SIG = signal number of the current module/tile; 5-byte source at RESP (RESP advances by 5)
    LD RESP                  // D = start of the result slot
    ST DESTA                 // keep it (the slot is modified after writing)
    LD SIG                   // D = signal
    @NIN                     // A = &NIN
    D=D-M                    // D = SIG - NIN
    IFLT res_input           // a module input
    DBL                      // an earlier gate j of the instance: D = 2 j
    ST AUL                   // addend low
    SET SPT, PB              // start from the pin of node 0
    CALL put5                // slot = pin base
    LD DESTA                 // D = slot address = address of x
    ST ADST                  // add to x ...
    LD WALK                  // D = 0 core, 1 tile
    IFEQ res_add             // core nodes are spaced 2 apart in x
    @ADST                    // A = &ADST
    M=M+1                    // tile nodes are spaced 2 apart in y:
    M=M+1                    // ADST = slot + 2 = address of y
res_add:
    CALL add16               // pin position of gate j
    RET resolve              // return
res_input:
    LD WALK                  // D = walk kind
    IFNE ti_start            // tiles use their rule table
    LD SIG                   // D = s
    DBL                      // 2 s
    DBL                      // 4 s
    @SIG                     // A = &SIG
    D=D+M                    // 5 s
    @SRC                     // A = SRC
    D=D+A                    // D = address of SRC[s]
    ST SPT                   // source address
    CALL put5                // copy it
    RET resolve              // return
ti_start:                    // ---- tile input SIG for tile KT, from the 5-byte rule at hd_rules + 5 * SIG
    SET16 P, hd_rules        // P -> rule table
    LD SIG                   // D = input number
    DBL                      // 2
    DBL                      // 4
    @SIG                     // A = &SIG
    D=D+M                    // 5 * input = offset of its rule
    ST AUL                   // addend low
    SET ADST, P              // add to P
    CALL add16               // P -> the rule
    COPY16 RP, P             // remember the rule start
    SET PSEL, P              // read through P
    CALL rdb                 // D = opcode
    ST OP                    // keep
    IFEQ ti_bcast            // 0 BCAST
    D=D-1                    // opcode - 1
    IFEQ ti_prev             // 1 PREV
    CALL decref              // 2/3 PICK: the first list element's pin -> result slot
    COPY16 P, RP             // P -> rule start
    ADDI P, 4                // P -> parameter
    CALL rdb                 // D = mask or divisor
    ST T0                    // keep
    LD OP                    // D = opcode
    @2                       // A = 2
    D=D-A                    // D = opcode - 2
    IFEQ ti_lo               // PICKLO: index = k AND mask
    SET T1, 0                // PICKHI: quotient = 0
    LD KT                    // D = k
    IFGE ti_rest             // k < 128: the signed tests below are exact
    SET AX, 64               // k >= 128: k / d = 2 * (64 / d) + (k - 128) / d   (d is a power of two, at most 64)
ti_d64:
    LD AX                    // D = remainder
    @T0                      // A = &T0
    D=D-M                    // D = remainder - divisor
    IFLT ti_d64_done         // finished
    ST AX                    // remainder -= divisor
    @T1                      // A = &T1
    M=M+1                    // quotient += 1
    GOTO ti_d64              // repeat
ti_d64_done:
    LD T1                    // D = 64 / d
    DBL                      // D = 128 / d
    ST T1                    // quotient so far
    LD KT                    // D = k
    @127                     // A = 127
    D=D&A                    // D = k - 128
    ST AX                    // remainder
    GOTO ti_div              // divide the rest
ti_rest:
    LD KT                    // D = k
    ST AX                    // remainder
ti_div:                      // while remainder >= divisor: subtract
    LD AX                    // D = remainder
    @T0                      // A = &T0
    D=D-M                    // D = remainder - divisor
    IFLT ti_div_done         // less than the divisor: finished
    ST AX                    // remainder -= divisor
    @T1                      // A = &T1
    M=M+1                    // quotient += 1
    GOTO ti_div              // repeat
ti_div_done:
    LD T1                    // D = index = k / divisor
    GOTO ti_scale            // go on
ti_lo:
    LD KT                    // D = k
    @T0                      // A = &T0
    D=D&M                    // D = k AND mask
ti_scale:                    // D = list index; the list entries are 2 nodes = 4 x-units apart
    DBL                      // 2 idx
    DBL                      // 4 idx
    ST AUL                   // addend low
    LD DESTA                 // D = slot address (x of the pin)
    ST ADST                  // add to x
    CALL add16               // x += 4 idx
    RET resolve              // return
ti_bcast:
    CALL decref              // same source for every tile
    RET resolve              // return
ti_prev:                     // output j of the previous tile
    COPY16 P, RP             // P -> rule start
    ADDI P, 4                // P -> parameter
    CALL rdb                 // D = which output of the previous tile
    ST T0                    // keep
    SET RFL, 0               // never RUN
    LD KT                    // D = k
    IFNE ti_prev_k           // k > 0: the previous tile's pin
    LD TIEX                  // tile 0: the tie-high node is the previous word: x low
    @1                       // A = 1
    D=D|A                    // + 1: its output pin
    ST RX                    // RX.low
    LD TIEX+1                // x high
    ST RX+1                  // RX.high
    SET16 RY, ROW_Y          // on the core row
    GOTO ti_out              // store
ti_prev_k:
    COPY16 TP, TOUTP         // TP -> list of tile output signals
    LD T0                    // D = j
    ST AUL                   // addend low
    SET ADST, TP             // add to TP
    CALL add16               // TP -> outs[j]
    SET PSEL, TP             // read through TP
    CALL rdb                 // D = output signal
    ST T1                    // keep
    SET PSEL, P              // back to P
    COPY16 RX, PB            // output pin x of this tile
    SET AUL, 254             // -2 (the previous column is 2 to the left)
    SET AUH, 255             // high byte of -2
    SET ADST, RX             // add to RX
    CALL add16               // RX = pin x of the previous column
    LD T1                    // D = signal
    @TNIN                    // A = &TNIN
    D=D-M                    // D = gate index in the tile
    DBL                      // 2 * index
    ST AUL                   // addend low
    SET16 RY, TILE_Y         // y of tile node 0
    SET ADST, RY             // add to RY
    CALL add16               // RY = 153 + 2 * index
ti_out:
    SET SPT, RES             // source = the result block
    CALL put5                // copy it to the slot
    RET resolve              // return

emit:                        // the current gate (EK, CUR, SA, SB): PLACE it (MODE 0) or WIRE its inputs (MODE 1)
    @MODE                    // A = &MODE
    D=M                      // D = pass
    IFNE em_wire             // wiring pass
    WRA 0, CUR               // A.x low
    WRA 1, CUR+1             // A.x high
    WRA 2, CUR+2             // A.y low
    WRA 3, CUR+3             // A.y high
    WRA 8, EK                // KIND = 0 NAND / 1 DFF
    WRK 9, 0                 // ANGLE = 0
    WRK 15, 1                // CMD = PLACE
    RET emit                 // return
em_wire:
    SET PIN, 0               // pin 0 first
    LD SA                    // D = its signal
    ST SIG                   // resolve it
em_pin:
    SET RESP, IN             // the source goes to IN
    CALL resolve             // IN = output pin driving this input
    COPY16 TY, CUR+2         // sink y = node y + pin
    LD PIN                   // D = pin
    IFEQ em_y                // pin 0: y as is
    ADDI TY, 1               // pin 1: one below
em_y:
    @IN+4                    // A = &flag
    D=M                      // D = RUN flag
    IFNE em_run              // RUN: wire it last
    WRA 0, IN                // A.x low = source x low
    WRA 1, IN+1              // A.x high
    WRA 2, IN+2              // A.y low
    WRA 3, IN+3              // A.y high
    WRA 4, CUR               // B.x low = sink x
    WRA 5, CUR+1             // B.x high
    WRA 6, TY                // B.y low = sink y
    WRA 7, TY+1              // B.y high
    WRK 15, 2                // CMD = WIRE
    GOTO em_next             // done with this pin
em_run:                      // RUN source: remember the sink pin (x, y) for the end of the build
    LD CUR                   // sink x low
    PUT RUNP                 // record
    LD CUR+1                 // sink x high
    PUT RUNP                 // record
    LD TY                    // sink y low
    PUT RUNP                 // record
    LD TY+1                  // sink y high
    PUT RUNP                 // record
em_next:
    LD EK                    // D = kind
    IFNE em_done             // a DFF has only one input pin
    LD PIN                   // D = pin just done
    IFNE em_done             // pin 1 done: finished
    SET PIN, 1               // pin 1 next
    LD SB                    // D = its signal
    ST SIG                   // resolve it
    GOTO em_pin              // wire it
em_done:
    RET emit                 // return

gates:                       // walk NG gate records at GP; for each: emit (place or wire), step CUR
    @NG                      // A = &NG
    D=M                      // D = gates left
    IFEQ gt_done             // none: finished
    SET PSEL, GP             // read the gate record through GP
    CALL rdb                 // D = kind
    ST EK                    // 0 nand / 1 dff
    CALL rdb                 // D = first input signal
    ST SA                    // keep
    CALL rdb                 // D = second input signal
    ST SB                    // keep
    SET PSEL, P              // back to P
    LD EK                    // D = kind
    @2                       // A = 2
    D=D-A                    // D = kind - 2 (kind 2 = skip entry of an improved module)
    IFNE gt_real             // an ordinary gate
    LD SA                    // D = number of unplaced slots k
    DBL                      // D = 2 k (k <= 26)
    ST AUL                   // addend low = 2 k
    SET ADST, CUR            // x of the current node
    CALL add16               // CUR.x += 2 k: those slots stay empty
    LD NG                    // D = slots left
    @SA                      // A = &SA
    D=D-M                    // D = slots left - k
    ST NG                    // store
    GOTO gates               // next entry
gt_real:
    CALL emit                // PLACE or WIRE
    SET ADST, CUR            // step to the next node: x += 2 for core instances ...
    LD WALK                  // D = walk kind
    IFEQ gt_step             // core
    SET ADST, CUR+2          // ... y += 2 for tiles
gt_step:
    SET AUL, 2               // addend 2
    CALL add16               // CUR += step
    @NG                      // A = &NG
    M=M-1                    // one gate less
    GOTO gates               // next gate
gt_done:
    RET gates                // return
