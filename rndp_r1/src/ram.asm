// ram.asm -- RAM map of the RNDP Replicator 1 builder.  The machine has 128 bytes of RAM (addresses 0..127).
// 16-bit variables: low byte first.  Names that share an address are never live at the same time (see the comment).
.equ MODE,   0               // 0 = place pass, 1 = wire pass
.equ PSEL,   1               // address of the pointer variable rdb reads through
.equ RDV,    2               // rdb: the byte just read
.equ DT,     3               // DBL scratch
.equ ADST,   4               // add16: address of the destination variable
.equ AUL,    5               // add16: addend low
.equ AUH,    6               // add16: addend high (0 between calls)
.equ AO,     7               // add16 scratch
.equ AN,     8               // add16 scratch
.equ AC,     9               // add16 scratch
.equ AX,     10              // add16 scratch (also the remainder in the PICKHI division)
.equ AH,     11              // add16 carry
.equ P,      12              // ROM read pointer for the body walk (2)
.equ CX,     14              // x of the current node (2); also the ROM copy offset CA
.equ CA,     14              // ROM copy offset (CX is free during the ROM copy)
.equ CY,     16              // y of the current node (2)
.equ BX,     18              // x of the output pin of the first node of the current instance (2)
.equ BY,     20              // y of the same (2)
.equ TIEX,   22              // x of the output pin of the tie-high node (2)
.equ TIEY,   24              // y of the tie-high node (2)
.equ LY0,    26              // y of gate 0 of the LAST RAM tile (2)
.equ TMP,    28              // ROM address of the tile record (2)
.equ TOUTP,  30              // ROM address of the tile's output list (2)
.equ TNIN,   32              // tile inputs
.equ TG,     33              // tile gates
.equ WN,     34              // index of the last tile (count - 1)
.equ KT,     35              // current tile index
.equ TY8,    36              // module type for lookup
.equ WALK,   37              // 0 core instance, 1 tile
.equ TG3N,   38              // -3 * TG (2)
.equ NIN,    40              // inputs of the current module
.equ NG,     41              // gates left in the current module
.equ GP,     42              // ROM pointer into the gate records (2)
.equ RP,     44              // ROM address of the references of the current instance (2); also the rule pointer for tiles
.equ SP,     46              // scratch ROM pointer (2)
.equ MP,     46              // lookup: record address (same as SP, never live together)
.equ EK,     48              // gate kind
.equ SA,     49              // first input signal
.equ SB,     50              // second input signal
.equ SIG,    51              // signal being resolved
.equ PIN,    52              // input pin being wired
.equ RFL,    53              // result flag of a reference: 0 relative (U,V), 1 absolute (TC,DR), 2 RUN (absolute)
.equ DB,     54              // reference byte
.equ EV,     55              // reference byte & 0x7F
.equ OP,     56              // rule opcode
.equ SN,     57              // loop counter
.equ T0,     58              // 16-bit distance (2): T0 low, T1 high
.equ T1,     59
.equ U,      60              // 2 * T (2)
.equ V,      62              // 3 * T (2)
.equ TC,     64              // lane driver site x (2)
.equ DR,     66              // lane driver site y (2)
.equ PX,     68              // sink pad x (2)
.equ PY,     70              // sink pad y (2)
.equ RR,     72              // lane row (2)
.equ NP,     74              // loop counter / read pointer
.equ RUNP,   75              // write pointer into RUNS
.equ RUNS,   76              // 2 recorded RUN sinks of 6 bytes (PX, PY, RR) = 12 bytes
.equ SK,     88              // copyb: byte count
.equ SPT,    89              // copyb: source address
.equ DPT,    90              // copyb: destination address
// return addresses (2 bytes each, one per subroutine)
.equ RA_rdb,       92
.equ RA_add16,     94
.equ RA_lookup,    96
.equ RA_skip1,     98
.equ RA_skiprefs, 100
.equ RA_decref,   102
.equ RA_dist,     104
.equ RA_addtie,   106
.equ RA_resolve,  108
.equ RA_emit,     110
.equ RA_gates,    112
.equ RA_wire_sink,114
.equ RA_copyb,    116
// 118..127 free
