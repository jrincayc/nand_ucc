# RNDW world specification v0.5 (condensed copy; the full text lives in the Project at nandgen/RNDW_SPEC.md)

v0.5 (user decision): arm coordinates are RELATIVE. A.x, A.y, B.x, B.y in PLACE/WIRE/PROGRAM_ROM are signed 16-bit two's-complement offsets from the issuing arm's origin, in world axes (arm rotation ignored). PROGRAM_ROM's cell address (B.x) stays unsigned and absolute. Reach is +-32,767. Out-of-grid result = fault.

## Time
Tick: (1) every ARM with EN=1 does one register write; CMD writes execute (1b) network re-settles; (2) all DFFs latch simultaneously; (3) network settles. Combinational cycles allowed; non-convergence is a counted fault.

## Parts
NAND (A,B,Y; zero delay) | DFF (D,Q; Q starts 0) | ROM (ADDR[a], DATA[8]; unprogrammed reads 0; a = 1..16; programmable only while no wire touches any pin) | ARM (ADDR[4], DATA[8], EN) | SOURCE (harness only).
Input pins have one driver; outputs fan out freely. Unconnected input reads 0. A fresh NAND outputs 1; two unconnected inputs = tie-high. No RAM part: RAM is NAND+DFF.

## Footprints (default orientation)
NAND 2x2: A(0,0) B(0,1) Y(1,0). DFF 2x2: D(0,0) Q(1,0). ROM 2 x max(a,8): ADDR[i](0,i) DATA[j](1,j). ARM 2x9: ADDR[i](0,i) i<4, EN(0,4), DATA[j](1,j). Wires cross freely, zero delay.

## Arm registers (memory-mapped, write-only)
0,1 A.x lo/hi; 2,3 A.y; 4,5 B.x; 6,7 B.y; 8 KIND (0 NAND,1 DFF,2 ROM,3 ARM); 9 ANGLE; 10 VAL; 11-14 reserved (write = fault); 15 CMD.
Commands: 0 NOP; 1 PLACE (A, KIND, ANGLE); 2 WIRE (A, B; one output, one input pin); 3 PROGRAM_ROM (ROM origin at A, address B.x, VAL).
Faults (counted, ignored): bad code/KIND/ANGLE, overlap, out of bounds, bad wire, input already driven, no ROM at target, address out of range, ROM already wired (any wire touching any pin locks it).

## Starting a child (section 7)
Place everything -> program ROM -> all other wires -> child arm EN wire -> `run` wire last. `run` must feed exactly ONE gate (reset = nand(run,run)). Reset state must not assert EN.

## Differential test
`rndw/diff_test.sh`: Rust vs Python nandgen.Sim, vectors format `rndw-vectors 1`. 0 mismatches over ~2.9M comparisons (v0.4); relative-coordinate change does not touch the evaluator.
