// builder.asm -- RNDP Replicator 1 builder: reads the hardware description (hd_data.asm) from ROM and builds a copy of the machine
// through the arm: PLACE every part, copy the ROM image, wire everything (dedicated-lane layout), wire EN, wire RUN last.
// It is a direct transcription of ref_flatten.commands() (tools/ref_flatten.py).  All coordinates are relative to the parent's arm;
// the child's arm is at x = CHILD_DX.  Positions: core node g at (X0+2g, Y0+3g); the tie-high node is node n_core; RAM tile gates
// follow, gate j of tile k at (XT+2j, Y0+3(n_core+1+TG k+j)), XT = tie_x+8.  NAND pins A (x,y) B (x,y+1) Y (x+1,y); DFF D (x,y) Q (x+1,y).
// Wiring one sink = TRACK L1 (tc,dr)-(tc,r); VIA (tc,r); TRACK L0 (px,r)-(tc,r); [r != py] TRACK L0 (px,r)-(px,py).
// Arm registers: 0,1 A.x  2,3 A.y  4,5 B.x  6,7 B.y  8 KIND  9 ANGLE  10 VAL  15 CMD.  CMD 1 PLACE, 3 PROGRAM_ROM, 4 TRACK, 5 VIA.

.equ ARM,      ARM_BASE      // first arm register
.equ CHILD_DX, 4700          // x offset of the child's arm
.equ X0,       10            // x of core node 0 (relative to the arm that owns it)
.equ Y0,       13            // y of core node 0
.equ RAM_ABITS, 7            // address width of the RAM part (HD param ram_abits)

// ================================================================================================== main
start:                       // reset lands here (ROM_BASE)
    SET MODE, 0              // phase 0 places
    SET AUH, 0               // add16 addend high byte is 0 between calls
    SET RUNP, RUNS           // next free RUN sink slot
    SET PSEL, P              // rdb reads through P
    // ---- place the child's ROM and arm first (PROGRAM_ROM needs the ROM; nothing is wired before phase 1)
    WR16 0, CHILD_DX-15      // A.x = x of the ROM origin
    WR16 2, 0                // A.y = 0
    WRK 8, 2                 // KIND = ROM
    WRK 9, 1                 // ANGLE = 1 (rotated)
    WRK 10, AB-1             // VAL = number of ROM address bits
    WRK 15, 1                // CMD = PLACE
    WR16 0, CHILD_DX         // A.x = x of the child's arm
    WRK 8, 3                 // KIND = ARM
    WRK 10, 0                // VAL = 0
    WRK 15, 1                // CMD = PLACE
    WRK 9, 0                 // ANGLE = 0 for every NAND and DFF

phase:                       // ---- start of a phase: the core body
    SET16 P, hd_body         // P -> first instance
    SET16 CX, CHILD_DX+X0    // node 0 ...
    SET16 CY, Y0             // ... at (CHILD_DX + X0, Y0)
inst_next:                   // ---- next body instance
    SET PSEL, P              // read through P
    CALL rdb                 // D = type (0xFF = END)
    ST TY8                   // keep it
    D=D+1                    // 0xFF + 1 = 0 -> END
    IFEQ body_end            // leave the loop at END
    CALL lookup              // MP, NIN, NG for this type; GP -> first gate
    SET PSEL, P              // back to P
    COPY16 RP, P             // the references of this instance start here
    CALL skiprefs            // step P over them
    COPY16 BX, CX            // base: output pin of the instance's first node ...
    ADDI BX, 1               // ... x + 1
    COPY16 BY, CY            // ... y
    CALL gates               // place or wire every gate of the instance
    GOTO inst_next           // next instance

body_end:                    // END of the body: CX, CY = position of the tie-high node
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE tiles_start         // wire pass: the tie node is already known and placed
    COPY16 TIEX, CX          // output pin of the tie node: x + 1
    ADDI TIEX, 1             // ... x + 1
    COPY16 TIEY, CY          // ... y
    SET EK, 0                // the tie-high node is a NAND with unconnected inputs
    CALL emit                // PLACE it
tiles_start:
    // ---- the RAM part: origin (RX, RY) = (tie_x + 8, tie_y + 3) = (TIEX + 7, TIEY + 3); address width AB-8 = ram_abits
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE tiles_done          // wire pass: already placed
    COPY16 CX, TIEX          // x of the RAM origin ...
    ADDI CX, 7               // ... TIEX + 7
    COPY16 CY, TIEY          // y of the RAM origin ...
    ADDI CY, 3               // ... TIEY + 3
    WRA 0, CX                // A.x
    WRA 1, CX+1              // A.x high
    WRA 2, CY                // A.y
    WRA 3, CY+1              // A.y high
    WRK 8, 4                 // KIND = RAM
    WRK 10, RAM_ABITS        // VAL = address width
    WRK 15, 1                // CMD = PLACE
    WRK 8, 0                 // (KIND back to NAND for later)
    WRK 10, 0                // (VAL back to 0)
tiles_done:
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE wiring_tail         // wire pass: ports and RUN remain
    // ---- end of phase 0: copy the ROM image (program ROM before anything is wired).  Zero bytes need no command.
    WR16 0, CHILD_DX-15      // A.x = x of the child's ROM origin
    WR16 2, 0                // A.y = 0
    SET16 CA, 0              // ROM offset 0
    SET16 P, ROM_BASE        // read pointer = start of this ROM
    SET PSEL, P              // rdb reads through P
rom_loop:                    // for every ROM address up to hd_end
    CALL rdb                 // D = ROM byte at P; P += 1
    ST T0                    // keep it
    IFEQ rom_skip            // zero: nothing to program
    WRA 4, CA                // B.x low = offset
    WRA 5, CA+1              // B.x high
    WRA 10, T0               // VAL = byte
    WRK 15, 3                // CMD = PROGRAM_ROM
rom_skip:
    INC16 CA                 // next offset
    LD P                     // D = pointer low
    @lo(hd_end)              // A = low byte of the end
    D=D-A                    // zero at the end
    IFNE rom_loop            // more to do
    LD P+1                   // D = pointer high
    @hi(hd_end)              // A = high byte of the end
    D=D-A                    // zero at the end
    IFNE rom_loop            // more to do
    // ---- RAM read bits: extend the real pin of output 8+c of the last tile to the out column, with a via
    SET NP, 0                // c = 0
ext_loop:
    COPY16 DR, TIEY          // y of RAM pin DOUT[c] = TIEY + 3 + c
    ADDI DR, 3               // ... + 3
    LD NP                    // D = c
    ST AUL                   // addend low
    SET ADST, DR             // add to DR
    CALL add16               // DR = TIEY + 3 + c
    COPY16 TC, TIEX          // DOUT column = RX + 1 = TIEX + 8
    ADDI TC, 8               // ...
    WRA 0, TC                // A.x
    WRA 1, TC+1              // A.x high
    WRA 2, DR                // A.y
    WRA 3, DR+1              // A.y high
    COPY16 TC, TIEX          // out column XR = RX + 3 + c = TIEX + 10 + c
    ADDI TC, 10              // ... + 10
    LD NP                    // D = c
    ST AUL                   // addend low
    SET ADST, TC             // add to TC
    CALL add16               // TC = TIEX + 10 + c
    WRA 4, TC                // B.x
    WRA 5, TC+1              // B.x high
    WRA 6, DR                // B.y
    WRA 7, DR+1              // B.y high
    WRK 10, 0                // layer 0
    WRK 15, 4                // CMD = TRACK
    WRA 0, TC                // A.x = out column
    WRA 1, TC+1              // A.x high
    WRK 15, 5                // CMD = VIA (A.y is still the pin row)
    @NP                      // A = &NP
    M=M+1                    // next c
    D=M                      // D = c
    @8                       // A = 8
    D=D-A                    // zero after c = 7
    IFNE ext_loop            // more
    SET MODE, 1              // phase 1: wiring
    GOTO phase               // walk everything again

wiring_tail:                 // ---- ports (EN last), then RUN
    SET16 P, hd_ports        // P -> ports record
    SET PSEL, P              // read through P
    CALL rdb                 // D = number of ports
    ST NP                    // ports left
port_loop:                   // for each port
    LD NP                    // D = ports left
    IFEQ ports_done          // none
    SET PSEL, P              // read through P
    CALL decref              // driver of the port: relative to the tie node, or absolute
    CALL addtie              // make it absolute
    SET PSEL, P              // back to P
    CALL rdb                 // D = sink pad x + 32 (+ 0x80: relative to the RAM origin)
    ST PX                    // keep
    SET PX+1, 0              // high byte
    CALL rdb                 // D = sink pad y + 32
    ST PY                    // keep
    SET PY+1, 0              // high byte
    CALL rdb                 // D = lane row + 32
    ST RR                    // keep
    SET RR+1, 0              // high byte
    LD PX                    // D = x byte
    IFLT pt_ram              // bit 7: RAM frame
    ADDK PX, CHILD_DX-32     // x in the parent's frame
    ADDK PY, 65536-32        // y
    ADDK RR, 65536-32        // row
    GOTO pt_wire             // go
pt_ram:                      // pad = RAM origin (TIEX + 7, TIEY + 3) + offset
    ADDK PX, 65536-128-32+7  // x byte - 0x80 - 32, plus 7
    ADDV PX, TIEX            // + TIEX
    ADDK PY, 65536-32+3      // y byte - 32 + 3
    ADDV PY, TIEY            // + TIEY
    ADDK RR, 65536-32+3      // row byte - 32 + 3
    ADDV RR, TIEY            // + TIEY
pt_wire:
    CALL wire_sink           // wire it
    @NP                      // A = &NP
    M=M-1                    // one less
    GOTO port_loop           // next
ports_done:
    SET NP, RUNS             // read pointer = first recorded RUN sink
run_loop:                    // for each recorded sink
    LD NP                    // D = read pointer
    @RUNP                    // A = &write pointer
    D=D-M                    // zero when all sinks have been wired
    IFEQ halt                // done
    LD NP                    // D = read pointer
    ST SPT                   // source of the copy
    SET DPT, PX              // destination = PX, PY, RR
    SET SK, 6                // 6 bytes
    CALL copyb               // restore the sink
    LD SPT                   // D = new read pointer
    ST NP                    // keep
    COPY16 TC, TIEX          // the driver is the tie node's output pin
    COPY16 DR, TIEY          // ... y
    CALL wire_sink           // wire it
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

add16:                       // the 16-bit variable at RAM address ADST += (AUH:AUL), mod 2^16; AUH is cleared
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

dist:                        // T (16-bit signed, nodes) -> U = 2 T, V = 3 T
    COPY16 U, T0             // U = T
    ADDV U, T0               // U = 2 T
    COPY16 V, U              // V = 2 T
    ADDV V, T0               // V = 3 T
    RET dist                 // return

copyb:                       // copy SK bytes from RAM[SPT..] to RAM[DPT..]; both pointers advance
    @SPT                     // A = &SPT
    A=M                      // A = source byte address
    D=M                      // D = the byte
    PUT DPT                  // store it at the destination and advance DPT
    @SPT                     // A = &SPT
    M=M+1                    // next source byte
    @SK                      // A = &SK
    M=M-1                    // one less
    D=M                      // D = bytes left
    IFNE copyb               // repeat
    RET copyb                // return

skip1:                       // step over one reference at the pointer in PSEL (1 byte, or 3 for 0xFD / 0xFE)
    CALL rdb                 // D = reference byte
    @3                       // A = 3
    D=D+A                    // D = byte + 3 (mod 256): 0 for 0xFD, 1 for 0xFE
    IFEQ sk_far              // 0xFD: two more bytes follow
    D=D-1                    // 0 for 0xFE
    IFNE sk_done             // an ordinary one-byte reference
sk_far:
    CALL rdb                 // distance low
    CALL rdb                 // distance high
sk_done:
    RET skip1                // return

skiprefs:                    // step P over the NIN references of the current instance
    SET PSEL, P              // read through P
    LD NIN                   // D = references
    ST SN                    // loop counter
sr_loop:
    LD SN                    // D = references left
    IFEQ sr_done             // none
    CALL skip1               // one reference
    @SN                      // A = &SN
    M=M-1                    // one less
    GOTO sr_loop             // next
sr_done:
    RET skiprefs             // return

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
    CALL rdb                 // n_out (ignored)
    CALL rdb                 // n_gates
    ST NG                    // gates
    SET PSEL, P              // back to P
    RET lookup               // return

decref:                      // decode one reference at the pointer in PSEL.  RFL = 0: relative, U/V valid (node offset from the base
                             // node); 1: absolute site in TC/DR; 2: RUN (absolute site of the tie node, wired last)
    CALL rdb                 // D = reference byte
    ST DB                    // keep it
    IFLT dec_big             // 0x80 and above: special sources
    D=-D                     // 1..127: node b back; T = -b
    ST T0                    // T low
    SET T1, 255              // T high (negative)
    GOTO dec_rel             // go
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
    @125                     // A = 0x7D
    D=D-A                    // D = EV - 125
    IFEQ dec_fback           // 0xFD: far backward
    CALL rdb                 // 0xFE: distance low
    ST T0                    // T low
    CALL rdb                 // distance high
    ST T1                    // T high
    GOTO dec_rel             // go
dec_fback:
    CALL rdb                 // distance low
    D=!D                     // ~low
    ST T0                    // T low
    CALL rdb                 // distance high
    D=!D                     // ~high
    ST T1                    // T high
    INC16 T0                 // T = -distance
dec_rel:
    CALL dist                // U = 2 T, V = 3 T
    SET RFL, 0               // relative
    RET decref               // return
dec_rom:                     // ROM data bit EV: site (CHILD_DX - 2 - EV, 1)
    @lo(CHILD_DX-2)          // A = low byte of the x of data bit 0
    D=A                      // D = it
    @EV                      // A = &EV
    D=D-M                    // D = low byte of x (no borrow: the low byte is large)
    ST TC                    // TC low
    SET TC+1, hi(CHILD_DX-2) // TC high
    SET16 DR, 1              // y = 1
    SET RFL, 1               // absolute
    RET decref               // return
dec_tie:
    SET RFL, 1               // absolute
    GOTO dec_tp              // share the site
dec_run:
    SET RFL, 2               // RUN: the same site, wired last
dec_tp:
    COPY16 TC, TIEX          // tie output pin x
    COPY16 DR, TIEY          // y
    RET decref               // return
dec_ramrd:                   // RAM read bit c = EV - 10: the out column of DOUT[c]: (TIEX + 10 + c, TIEY + 3 + c)
    COPY16 TC, TIEX          // x ...
    COPY16 DR, TIEY          // ... y of the tie node
    LD EV                    // D = EV
    @10                      // A = 10
    D=D-A                    // D = c
    ST T0                    // keep c
    ADDI TC, 10              // x = TIEX + 10
    ADDI DR, 3               // y = TIEY + 3
    LD T0                    // D = c
    ST AUL                   // addend low
    SET ADST, TC             // add to x
    CALL add16               // TC = TIEX + 10 + c
    LD T0                    // D = c
    ST AUL                   // addend low
    SET ADST, DR             // add to y
    CALL add16               // DR = TIEY + 3 + c
    SET RFL, 1               // absolute
    RET decref               // return

addtie:                      // a relative result (RFL 0) is relative to the tie node: make it absolute
    @RFL                     // A = &RFL
    D=M                      // D = flag
    IFNE at_done             // already absolute
    COPY16 TC, TIEX          // tie output pin x
    ADDV TC, U               // + 2 d
    COPY16 DR, TIEY          // tie y
    ADDV DR, V               // + 3 d
at_done:
    RET addtie               // return

resolve:                     // SIG = signal number of the current module/tile; result RFL + site (TC, DR), absolute
    SET RFL, 0               // normal
    LD SIG                   // D = signal
    @NIN                     // A = &NIN
    D=D-M                    // D = SIG - NIN
    IFLT res_input           // a module input
    ST T0                    // an earlier gate g' of the instance: T = g'
    SET T1, 0                // high byte
    CALL dist                // U = 2 g', V = 3 g'
    COPY16 TC, BX            // base output pin x
    ADDV TC, U               // + 2 g'
    COPY16 DR, BY            // base y
    ADDV DR, V               // + 3 g'
    RET resolve              // return
res_input:
    COPY16 SP, RP            // core: the references of the instance
    SET PSEL, SP             // read through SP
    LD SIG                   // D = input number
    ST SN                    // references to step over
rs_loop:
    LD SN                    // D = references left
    IFEQ rs_found            // at the wanted one
    CALL skip1               // step over one
    @SN                      // A = &SN
    M=M-1                    // one less
    GOTO rs_loop             // next
rs_found:
    CALL decref              // decode it
    @RFL                     // A = &RFL
    D=M                      // D = flag
    IFNE rs_done             // absolute
    COPY16 TC, BX            // relative to the instance's first node
    ADDV TC, U               // + 2 d
    COPY16 DR, BY            // y
    ADDV DR, V               // + 3 d
rs_done:
    SET PSEL, P              // back to P
    RET resolve              // return
wire_sink:                   // driver site (TC, DR), sink pad (PX, PY), lane row RR
    WRA 0, TC                // A.x = tc
    WRA 1, TC+1              // A.x high
    WRA 2, DR                // A.y = dr
    WRA 3, DR+1              // A.y high
    WRA 4, TC                // B.x = tc
    WRA 5, TC+1              // B.x high
    WRA 6, RR                // B.y = r
    WRA 7, RR+1              // B.y high
    WRK 10, 1                // layer 1
    WRK 15, 4                // TRACK (tc,dr)-(tc,r)
    WRA 2, RR                // A.y = r
    WRA 3, RR+1              // A.y high
    WRK 15, 5                // VIA at (tc,r)
    WRA 0, PX                // A.x = px
    WRA 1, PX+1              // A.x high
    WRK 10, 0                // layer 0
    WRK 15, 4                // TRACK (px,r)-(tc,r)
    LD RR                    // D = r low
    @PY                      // A = &PY
    D=D-M                    // r low - py low
    IFNE ws_vert             // differ
    LD RR+1                  // D = r high
    @PY+1                    // A = &PY.high
    D=D-M                    // r high - py high
    IFEQ ws_done             // r == py: no vertical segment
ws_vert:
    WRA 4, PX                // B.x = px
    WRA 5, PX+1              // B.x high
    WRA 6, PY                // B.y = py
    WRA 7, PY+1              // B.y high
    WRK 15, 4                // TRACK (px,r)-(px,py)
ws_done:
    RET wire_sink            // return

emit:                        // the current gate (EK, CX, CY, SA, SB): PLACE it (phase 0) or wire its inputs (phase 1)
    @MODE                    // A = &MODE
    D=M                      // D = phase
    IFNE em_wire             // wire pass
    WRA 0, CX                // A.x
    WRA 1, CX+1              // A.x high
    WRA 2, CY                // A.y
    WRA 3, CY+1              // A.y high
    WRA 8, EK                // KIND = 0 NAND / 1 DFF
    WRK 15, 1                // CMD = PLACE
    RET emit                 // return
em_wire:
    SET PIN, 0               // pin 0 first
    LD SA                    // D = its signal
    ST SIG                   // resolve it
em_pin:
    CALL resolve             // RFL, (TC, DR) = the driver's output site
    COPY16 PX, CX            // sink pad x
    COPY16 PY, CY            // sink pad y = node y + pin
    COPY16 RR, CY            // lane row = node y - 1 + 2 pin
    @PIN                     // A = &PIN
    D=M                      // D = pin
    IFEQ em_p0               // pin 0
    ADDI PY, 1               // pin 1: y + 1
    ADDI RR, 1               // r = y - 1 + 2 = y + 1
    GOTO em_lane             // go
em_p0:
    ADDK RR, 65535           // r = y - 1
em_lane:
    LD RFL                   // D = flag
    D=D-1                    // 1 less
    D=D-1                    // 2 less: zero for RUN
    IFNE em_wire_it          // an ordinary source
    LD RUNP                  // RUN: remember the sink (PX, PY, RR) for the end of the build
    ST DPT                   // destination
    SET SPT, PX              // source
    SET SK, 6                // 6 bytes
    CALL copyb               // copy
    LD DPT                   // D = new write pointer
    ST RUNP                  // keep
    GOTO em_next             // done with this pin
em_wire_it:
    CALL wire_sink           // wire it
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

gates:                       // walk NG gate records at GP; for each: emit (place or wire), step CX, CY
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
    CALL emit                // PLACE or WIRE
    ADDI CX, 2               // next node: x += 2 ...
    ADDI CY, 3               // ... y += 3
    @NG                      // A = &NG
    M=M-1                    // one gate less
    GOTO gates               // next gate
gt_done:
    RET gates                // return
