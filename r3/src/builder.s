// builder.s -- RNDP Replicator 3 builder (RV32EC): reads the hardware description (hd_data.s) from ROM and builds a copy of the machine through
// the arm: PLACE every part, copy the ROM image, wire everything (dedicated-lane layout), wire EN, wire RUN last.  Direct transcription of
// ref_flatten.commands() (tools/ref_flatten.py).  All coordinates are relative to the parent's arm; the child's arm is at x = CHILD_DX.
// Core node g sits at (X0+2g, Y0+3g); the tie-high node is node NCORE; the RAM part's origin is (tie_x+8, tie_y+3).
// NAND pins: A (x,y) B (x,y+1) Y (x+1,y); DFF pins: D (x,y) Q (x+1,y).
// Wiring one sink = TRACK L1 (tc,dr)-(tc,r); VIA (tc,r); TRACK L0 (px,r)-(tc,r); [r != py] TRACK L0 (px,r)-(px,py).
// Arm registers (written by stores into the window at ARM_BASE, one arm write per byte): 0,1 A.x  2,3 A.y  4,5 B.x  6,7 B.y  8 KIND  9 ANGLE
// 10 VAL  15 CMD.  CMD 1 PLACE, 3 PROGRAM_ROM, 4 TRACK, 5 VIA.  Registers 11..14 are reserved (writing them is a fault), so stores are sh/sb only.
//
// Registers: s0 = arm window base; s1 = read pointer into the ROM; a0,a1 = x,y of the current node; gp = pins/ports left; tp = pin number;
// sp = end of the list of recorded RUN sinks (RAM at RUNS); dec returns a2,a3 = driver site and t2 = 1 for RUN; wire_sink takes a2,a3 = driver
// site, a4,a5 = sink pad, t0 = lane row.

.equ ARM,        ARM_BASE
.equ CHILD_DX,   6200               // x offset of the child's arm
.equ X0,         10                 // x of core node 0
.equ Y0,         13                 // y of core node 0
.equ ROMBITS,    14                 // ROM address bits (HD param ab - 1)
.equ RAM_ABITS,  8                  // RAM part address bits (HD param ram_abits)
.equ RUNS,       0x50               // RAM: recorded RUN sinks, 6 bytes each (px, py, r as 16-bit values)
.equ TIEX,       CHILD_DX + X0 + 2*NCORE + 1     // output pin of the tie-high node, child frame in parent coordinates
.equ TIEY,       Y0 + 3*NCORE
.equ RXP,        TIEX + 7           // RAM part origin x (tie_x + 8)
.equ RYP,        TIEY + 3           // RAM part origin y (tie_y + 3)
.equ ENDX,       CHILD_DX + X0 + 2*NCORE   // x of the tie-high node = loop end

start:                              // reset lands here (ROM_BASE)
    li   s0, ARM                    // arm window base
    li   sp, RUNS                   // no RUN sink recorded yet
    // ---- the child's ROM and arm first (PROGRAM_ROM needs the ROM; nothing is wired before phase 1)
    li   t0, CHILD_DX - 15          // A.x = x of the child's ROM origin
    sh   t0, 0(s0)                  // A.x
    sh   x0, 2(s0)                  // A.y = 0
    li   t0, 2                      // KIND = ROM
    sb   t0, 8(s0)                  // KIND
    li   t0, 1                      // ANGLE = 1 (rotated)
    sb   t0, 9(s0)                  // ANGLE
    li   t0, ROMBITS                // VAL = number of ROM address bits
    sb   t0, 10(s0)                 // VAL
    li   t0, 1                      // CMD = PLACE
    sb   t0, 15(s0)                 // PLACE the ROM
    li   t0, CHILD_DX               // A.x = x of the child's arm
    sh   t0, 0(s0)                  // A.x
    li   t0, 3                      // KIND = ARM
    sb   t0, 8(s0)                  // KIND
    sb   x0, 10(s0)                 // VAL = 0
    li   t0, 1                      // CMD = PLACE
    sb   t0, 15(s0)                 // PLACE the arm
    sb   x0, 9(s0)                  // ANGLE = 0 for every NAND and DFF
    // ---- phase 0: place every core node
    li   s1, hd_body                // read pointer
    li   a0, CHILD_DX + X0          // node 0 at (CHILD_DX + X0, Y0)
    li   a1, Y0                     //
    li   t1, 1                      // constant 1 = PLACE
pl_loop:                            // one node per round
    lbu  t0, 0(s1)                  // first record byte: 0 marks a DFF
    seqz a2, t0                     // a2 = 1 for a DFF, 0 for a NAND
    li   gp, 2                      // a NAND has 2 references
    bnez t0, pl_ref                 // NAND: the byte is the first reference
    addi s1, s1, 1                  // DFF: step over the marker
    li   gp, 1                      // a DFF has 1 reference
pl_ref:                             // step over gp references
    lbu  t0, 0(s1)                  // reference byte
    addi s1, s1, 1                  // consumed
    addi t0, t0, -0xA0              // 0xA0..0xBF mark a 2-byte reference
    sltiu t0, t0, 0x20              // 1 for those
    add  s1, s1, t0                 // step over the second byte
    addi gp, gp, -1                 // one less
    bnez gp, pl_ref                 // next
    sh   a0, 0(s0)                  // A.x
    sh   a1, 2(s0)                  // A.y
    sb   a2, 8(s0)                  // KIND = 0 NAND / 1 DFF
    sb   t1, 15(s0)                 // CMD = PLACE
    addi a0, a0, 2                  // next node: x += 2
    addi a1, a1, 3                  // y += 3
    li   t0, ENDX                   // node NCORE is the tie-high node
    bne  a0, t0, pl_loop            // more nodes
    // ---- the tie-high node: a NAND with unconnected inputs; a1 = its y
    sh   a0, 0(s0)                  // A.x
    sh   a1, 2(s0)                  // A.y
    sb   x0, 8(s0)                  // KIND = NAND
    sb   t1, 15(s0)                 // PLACE
    // ---- the RAM part
    li   t0, RXP                    // A.x = RAM origin x
    sh   t0, 0(s0)                  //
    li   t0, RYP                    // A.y = RAM origin y
    sh   t0, 2(s0)                  //
    li   t0, 4                      // KIND = RAM
    sb   t0, 8(s0)                  //
    li   t0, RAM_ABITS              // VAL = address width
    sb   t0, 10(s0)                 //
    sb   t1, 15(s0)                 // PLACE the RAM
    sb   x0, 8(s0)                  // KIND back to NAND
    sb   x0, 10(s0)                 // VAL back to 0
    // ---- program the child's ROM with this ROM's image (before anything is wired); zero bytes need no command
    li   t0, CHILD_DX - 15          // A.x = x of the child's ROM origin
    sh   t0, 0(s0)                  //
    sh   x0, 2(s0)                  // A.y = 0
    li   s1, ROM_BASE               // read pointer
    li   a2, 0                      // ROM offset
    li   a3, 3                      // CMD = PROGRAM_ROM
    li   a4, hd_end                 // end of the image
rom_loop:
    lbu  t0, 0(s1)                  // the byte
    beqz t0, rom_skip               // nothing to program
    sh   a2, 4(s0)                  // B.x = offset
    sb   t0, 10(s0)                 // VAL = byte
    sb   a3, 15(s0)                 // PROGRAM_ROM
rom_skip:
    addi s1, s1, 1                  // next address
    addi a2, a2, 1                  // next offset
    bne  s1, a4, rom_loop           // until the end of the image
    // ---- RAM read bits: extend DOUT[c] = (RXP+1, RYP+c) along layer 0 to the out column RXP+3+c, with a via
    sb   x0, 10(s0)                 // layer 0
    li   a2, 0                      // c
    li   a3, 8                      // 8 bits
ext_loop:
    li   t0, RXP + 1                // A.x = DOUT column
    sh   t0, 0(s0)                  //
    li   t0, RYP                    //
    add  t0, t0, a2                 // y = RYP + c
    sh   t0, 2(s0)                  // A.y
    sh   t0, 6(s0)                  // B.y
    li   t1, RXP + 3                //
    add  t1, t1, a2                 // out column x = RXP + 3 + c
    sh   t1, 4(s0)                  // B.x
    li   t2, 4                      // TRACK
    sb   t2, 15(s0)                 // TRACK (RXP+1, y)-(RXP+3+c, y)
    sh   t1, 0(s0)                  // A.x = out column
    li   t2, 5                      // VIA
    sb   t2, 15(s0)                 // VIA at (RXP+3+c, y)
    addi a2, a2, 1                  // next c
    bne  a2, a3, ext_loop           // all 8
    // ---- phase 1: wire every sink of every core node
    li   s1, hd_body                // read pointer
    li   a0, CHILD_DX + X0          // node 0
    li   a1, Y0                     //
wr_loop:
    lbu  t0, 0(s1)                  // first record byte
    li   gp, 2                      // a NAND has 2 pins
    bnez t0, wr_pins                // NAND
    addi s1, s1, 1                  // DFF: step over the marker
    li   gp, 1                      // one pin
wr_pins:
    li   tp, 0                      // pin 0 first
wr_pin:
    jal  ra, dec                    // a2,a3 = driver site; t2 = 1 for RUN; s1 advanced
    mv   a4, a0                     // sink pad x = node x
    add  a5, a1, tp                 // sink pad y = node y + pin
    add  t0, tp, tp                 // 2 pin
    add  t0, t0, a1                 // y + 2 pin
    addi t0, t0, -1                 // lane row = y - 1 + 2 pin
    bnez t2, wr_run                 // RUN is wired last: record the sink
    jal  ra, wire_sink              // wire it
    j    wr_next                    //
wr_run:
    sh   a4, 0(sp)                  // remember px
    sh   a5, 2(sp)                  // py
    sh   t0, 4(sp)                  // lane row
    addi sp, sp, 6                  // next slot
wr_next:
    addi tp, tp, 1                  // next pin
    bne  tp, gp, wr_pin             // more pins
    addi a0, a0, 2                  // next node
    addi a1, a1, 3                  //
    li   t0, ENDX                   //
    bne  a0, t0, wr_loop            // more nodes
    // ---- ports (references are relative to the tie-high node), EN last
    li   s1, hd_ports               // read pointer
    li   gp, NPORTS                 // ports left
    li   a0, ENDX                   // current node = the tie-high node
    li   a1, TIEY                   //
pt_loop:
    jal  ra, dec                    // a2,a3 = driver site
    lbu  a4, 0(s1)                  // sink pad x + 32 (+0x80: RAM frame)
    lbu  a5, 1(s1)                  // sink pad y + 32
    lbu  t0, 2(s1)                  // lane row + 32
    addi s1, s1, 3                  //
    li   t1, 0x80                   //
    bgeu a4, t1, pt_ram             // bit 7: relative to the RAM origin
    li   t1, CHILD_DX - 32          // x in the parent's frame
    add  a4, a4, t1                 //
    addi a5, a5, -32                // y
    addi t0, t0, -32                // row
    j    pt_wire                    //
pt_ram:
    li   t1, RXP - 32 - 0x80        // x byte - 0x80 - 32 + RXP
    add  a4, a4, t1                 //
    li   t1, RYP - 32               // y byte - 32 + RYP
    add  a5, a5, t1                 //
    add  t0, t0, t1                 // row byte - 32 + RYP
pt_wire:
    jal  ra, wire_sink              // wire it
    addi gp, gp, -1                 // one port less
    bnez gp, pt_loop                // next port
    // ---- RUN last
    li   s1, RUNS                   // first recorded sink
run_loop:
    beq  s1, sp, halt               // all wired
    lh   a4, 0(s1)                  // px
    lh   a5, 2(s1)                  // py
    lh   t0, 4(s1)                  // lane row
    addi s1, s1, 6                  //
    li   a2, TIEX                   // the driver is the tie node's output pin
    li   a3, TIEY                   //
    jal  ra, wire_sink              //
    j    run_loop                   //
halt:                               // finished: the child is built; the model's halt convention
    j    halt                       //

// ---- dec: decode one reference at s1 for the node at (a0,a1); returns the driver's output site (a2,a3), t2 = 1 for RUN; s1 advances
dec:
    lbu  t0, 0(s1)                  // reference byte
    addi s1, s1, 1                  //
    li   t2, 0                      // not RUN
    li   t1, 0x80                   //
    bgeu t0, t1, dec_big            // 0x80 and above: special sources
    add  t1, t0, t0                 // 1..0x7F: node cur - d;  2d
    add  a3, t1, t0                 // 3d
    sub  a2, a0, t1                 // x = cx - 2d ...
    addi a2, a2, 1                  // ... + 1 (output pin)
    sub  a3, a1, a3                 // y = cy - 3d
    ret                             //
dec_big:
    li   t1, 0x88                   //
    bgeu t0, t1, dec_b2             // 0x88 and above
    li   a2, CHILD_DX - 2 + 0x80    // ROM data bit j = t0 - 0x80 at (CHILD_DX - 2 - j, 1)
    sub  a2, a2, t0                 //
    li   a3, 1                      //
    ret                             //
dec_b2:
    li   t1, 0xA0                   //
    bgeu t0, t1, dec_far            // 0xA0 and above
    li   a2, TIEX                   // tie / RUN / RAM read bits: base = tie output pin
    li   a3, TIEY                   //
    addi t1, t0, -0x88              // 0 tie, 1 RUN, 2.. RAM read bit
    beqz t1, dec_ret                // tie-high
    addi t1, t1, -1                 //
    bnez t1, dec_ramrd              // RAM read bit c = t0 - 0x8A
    li   t2, 1                      // RUN (same site, wired last)
dec_ret:
    ret                             //
dec_ramrd:                          // t1 = c + 1: out column of DOUT[c] = (RXP + 3 + c, RYP + c)
    addi t1, t1, -1                 // c
    li   a2, RXP + 3                //
    add  a2, a2, t1                 //
    li   a3, RYP                    //
    add  a3, a3, t1                 //
    ret                             //
dec_far:
    li   t1, 0xC0                   //
    bgeu t0, t1, dec_hot            // hot table entry
    andi t0, t0, 31                 // absolute node: high 5 bits ...
    slli t0, t0, 8                  //
    lbu  t1, 0(s1)                  // ... low byte
    addi s1, s1, 1                  //
    or   t0, t0, t1                 // node number n
    j    dec_node                   //
dec_hot:
    add  t0, t0, t0                 // 2 b
    li   t1, hd_hot - 0x180         // entry address = hd_hot + 2 (b - 0xC0)
    add  t0, t0, t1                 //
    lhu  t0, 0(t0)                  // node number n
dec_node:                           // site of node n: (CHILD_DX + X0 + 2n + 1, Y0 + 3n)
    add  a3, t0, t0                 // 2n
    add  t1, a3, t0                 // 3n
    li   a2, CHILD_DX + X0 + 1      //
    add  a2, a2, a3                 // x
    addi a3, t1, Y0                 // y
    ret                             //

// ---- wire_sink: driver site (a2,a3), sink pad (a4,a5), lane row t0
wire_sink:
    sh   a2, 0(s0)                  // A.x = tc
    sh   a3, 2(s0)                  // A.y = dr
    sh   a2, 4(s0)                  // B.x = tc
    sh   t0, 6(s0)                  // B.y = r
    li   t1, 1                      // layer 1
    sb   t1, 10(s0)                 // VAL
    li   t1, 4                      // TRACK
    sb   t1, 15(s0)                 // TRACK L1 (tc,dr)-(tc,r)
    sh   t0, 2(s0)                  // A.y = r
    li   t1, 5                      // VIA
    sb   t1, 15(s0)                 // VIA (tc,r)
    sh   a4, 0(s0)                  // A.x = px
    sb   x0, 10(s0)                 // layer 0
    li   t1, 4                      // TRACK
    sb   t1, 15(s0)                 // TRACK L0 (px,r)-(tc,r)
    beq  t0, a5, ws_done            // r == py: no vertical piece
    sh   a4, 4(s0)                  // B.x = px
    sh   a5, 6(s0)                  // B.y = py
    sb   t1, 15(s0)                 // TRACK L0 (px,r)-(px,py)
ws_done:
    ret                             //
