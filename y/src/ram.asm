// ram.asm -- the RAM map of the Y machine (Hack-vN-AB, 256 bytes of RAM).  This is the only place where RAM addresses are assigned.
//
//   0 .. 127    temporaries: the builder's variables and the improver's variables OVERLAY each other.  They are never live together:
//               the persistent block below carries everything that must survive a call of improve_type.
//   128 .. 167  RECB: the improved record (40 bytes).  It is the improver's scratch while it works, and the record it leaves behind.
//   168 ..      persistent variables
//
// The improved record has the format of a hardware-description record (hd2asm.py), so the builder reads it through a pointer to RAM
// exactly like a record in ROM.

.equ RECB,    128            // improved record buffer, REC_MAX = 40 bytes (improver scratch too)
.equ PERS,    168            // persistent block
.equ MODE,    PERS+0         // 0 = placing pass, 1 = wiring pass
.equ TSEL,    PERS+1         // module type being processed in this walk of the body (0 .. 15), 16 = finished
.equ IMPR,    PERS+2         // improve_type: 1 = the improved record is in RECB
.equ RECN,    PERS+3         // length of the improved record
.equ ITY,     PERS+4         // type given to improve_type
.equ WN,      PERS+5         // number of tiles W
.equ TNIN,    PERS+6         // inputs of the tile module
.equ TG,      PERS+7         // gates of the tile module
.equ AUH,     PERS+8         // add16 addend high byte (0 between calls)
.equ RUNN,    PERS+9         // read pointer into RUNS
.equ RUNP,    PERS+10        // write pointer into RUNS
.equ TMP,     PERS+11        // record pointer of the tile module (2 bytes)
.equ TOUTP,   PERS+13        // ROM pointer to the output list of the tile module (2 bytes)
.equ TIEX,    PERS+15        // x of the tie-high node (2 bytes)
.equ RAMX,    PERS+17        // x of the output pins of the last tile (2 bytes)
.equ RECP,    PERS+19        // pointer to the record of type TSEL (ROM, or RECB when improved) (2 bytes)
.equ RUNS,    PERS+21        // 2 x 4 bytes: x, y of the sink pins fed by RUN
.equ PERS_END, PERS+29

// ---- builder temporaries (addresses from 0; the improver's temporaries overlay them: they are never live together)
.equ WALK,    1              // 0 = walking a body instance, 1 = walking a RAM tile
.equ PSEL,    2              // RAM address of the ROM pointer that rdb reads through (P or GP)
.equ RDV,     3              // rdb: the byte just read
.equ DB,      4              // decref: the ref byte
.equ EV,      5              // decref: ref byte & 0x7F
.equ BK,      6              // decref: 1 = backward reference (needs +1 after the add)
.equ T0,      7              // scratch
.equ T1,      8              // scratch
.equ OP,      9              // tile rule opcode
.equ SIG,     10             // resolve: signal number to resolve
.equ SA,      11             // current gate: first input signal
.equ SB,      12             // current gate: second input signal
.equ EK,      13             // current gate: kind (0 nand, 1 dff)
.equ NIN,     14             // inputs of the module/tile being walked
.equ NG,      15             // gates left to do
.equ KT,      16             // tile index k
.equ TY8,     20             // instance type
.equ PIN,     21             // emit: pin number
.equ RESP,    22             // RAM address where decref/resolve/put5 write their 5-byte result
.equ DESTA,   23             // resolve: start of the result slot
.equ SK,      24             // loop counter
.equ ADST,    25             // add16: RAM address of the 16-bit variable to add to
.equ AUL,     26             // add16: addend low
.equ AO,      28             // add16: old low byte
.equ AN,      29             // add16: new low byte
.equ AC,      30             // add16: scratch
.equ AX,      31             // add16: scratch (also the remainder in tile index division)
.equ AH,      32             // add16: carry into the high byte
.equ NP,      33             // ports left
.equ VALV,    34             // ROM copy: the byte to program
.equ DT,      35             // DBL scratch
.equ SPT,     36             // put5: RAM address of the source
.equ SN,      37             // number of input references left to decode
.equ RA_rdb,     38          // return addresses (2 bytes each)
.equ RA_add16,   40
.equ RA_put5,    42
.equ RA_lookup,  44
.equ RA_decref,  46
.equ RA_resolve, 48
.equ RA_emit,    50
.equ RA_gates,   52
.equ RA_skiprefs, 60       // return addresses of the M5 routines (2 bytes each)
.equ RA_progrec,  62
.equ NOUT,    64             // lookup: n_out of the record
.equ PL,      65             // progrec: bytes left
.equ P,       54             // ROM read pointer (14 bits)
.equ GP,      56             // ROM pointer into the gate records
.equ MP,      58             // record pointer of the current instance
.equ XR,      66             // x of the output pin of the reference node (ref base)
.equ TP,      70             // scratch ROM pointer
.equ RP,      72             // ROM address of the current chain rule
.equ CA,      74             // ROM copy: address counter
.equ TY,      76             // emit: sink y
.equ NB,      78             // x, y (4 bytes) of the first node of the instance
.equ CUR,     82             // x, y of the current node
.equ PB,      86             // 5 bytes: source slot of the output pin of the instance's first node (flag 0)
.equ RES,     91             // 5 bytes: decref result: RX (91,92), RY (93,94), RFL (95)
.equ RX,      91
.equ RY,      93
.equ RFL,     95
.equ IN,      96             // 5 bytes: source of the input pin being wired
.equ SRC,     101            // 3 x 5 bytes: sources of the module inputs

// ---- improver temporaries (addresses from 0; SCR is the RECB area)
.equ NIR,    1               // n_in of the record
.equ NO,     2               // n_out
.equ SL,     3               // number of slots of the record (n_gates in the header)
.equ REAL,   4               // number of real (non-hole) gates in the record
.equ ING,     5               // gate slots in use (the gate arrays)
.equ O0,     6               // output signals (internal numbering)
.equ O1,     7               //
.equ P0,     8               // pinned output slots (original slots of the outputs)
.equ P1,     9               //
.equ IRDV,    11              // irdb: byte just read
.equ ADR,    12              // scratch: computed address
.equ DV,     13              // scratch: saved value
.equ X0,     14              // temporaries
.equ X1,     15              //
.equ X2,     16              //
.equ X3,     17              //
.equ CI,     18              // loop counters
.equ CJ,     19              //
.equ BIX,    20              // bit routines: bit index (signal number)
.equ BMB,    21              // bit routines: bitmap base address
.equ MSK,    22              // bit routines: mask
.equ RT,     23              // root signal being examined
.equ LKV,    24              // 1 when a previous cut exists for this root
.equ BF,     25              // nextcut: 1 when a cut was found
.equ XA,     26              // more temporaries (compact, nextcut, partition)
.equ XB,     27              //
.equ XC,     28              //
.equ XD,     29              //
.equ XE,     30              //
.equ RA_leaf, 31             // return address of every leaf subroutine (irdb bt bs keycmp ins; they never call anything)   2 bytes
.equ RA_d1,   33             // return address of every subroutine called by improve_type (load compact nextcut cone search ...)   2 bytes
.equ RA_improve_type, 35     // return address of improve_type                                                               2 bytes
.equ LK,     37              // last cut tried for this root: K, L0, L1, L2 (4 bytes, unused leaves 0)
.equ BL,     41              // best cut so far / the cut being processed (4 bytes)
.equ CL,     45              // cut being generated by the chain: K, L0, L1, L2 and one spare byte (5 bytes)
.equ SCR,    RECB            // scratch of the improver (40 bytes) = the improved record buffer
.equ GA0,    50              // gate arrays: GA[s] is at GA0 - 3 + s, 32 entries
.equ GB0,    82              //
.equ GA,     GA0-3           // base so that GA + s is the address for signal s
.equ GB,     GB0-3           //
// SCR is shared by the phases (a name is only used while the others in its range are dead):
.equ RN,     SCR-3           // compact: renumbering / liveness, index = signal 3 .. 28
.equ EN,     SCR+31          // compact: end signal
.equ VAL,    SCR             // cone: truth table of every signal 0 .. 28
.equ FULL,   SCR+29          // cone: table mask
.equ FT,     SCR+30          // cone: truth table of the root over the cut
.equ SAVD,   SCR+31          // cone: saved gates
.equ CN,     SCR+32          // cone bitmap (4 bytes)
.equ NS,     SCR+36          // "used outside the cone" bitmap (4 bytes)
.equ SI,     SCR             // search: chosen i per depth (6)
.equ SJ,     SCR+6           // search: chosen j per depth (6)
.equ TB,     SCR+12          // search: truth tables of the signals (up to 9)
.equ SG,     SCR+21          // search: current number of gates
.equ SD,     SCR+22          // search: depth
.equ SLN,    SCR+23          // search: number of signals in the table
.equ GMX,    SCR+24          // maximum number of new gates
.equ NN,     SCR+25          // new gates found (0 when the root equals a leaf)
.equ NSIG,   SCR+26          // signal that replaces the root
.equ R2,     SCR+27          // the old root after the shift
.equ SH,     SCR+31          // load: 3 - n_in
.equ IP,      SCR+34          // ROM read pointer (2 bytes), used while loading only
.equ WP,     CL              // layout: write index into RECB
.equ HC,     CL+1            // layout: pending hole count
.equ SS,     CL+2            // layout: slot
.equ HOLE,   127             // GA marker: unplaced slot
.equ DUP,    126             // GA marker: duplicate of the gate whose number is in GB (during compact)
.equ REC_MAX, 40             // maximum size of an improved record (bytes)

.equ RA_irdb, RA_leaf
.equ RA_bt, RA_leaf
.equ RA_bs, RA_leaf
.equ RA_keycmp, RA_leaf
.equ RA_ins, RA_leaf
.equ RA_load, RA_d1
.equ RA_compact, RA_d1
.equ RA_nextcut, RA_d1
.equ RA_cone, RA_d1
.equ RA_search, RA_d1
.equ RA_rewrite, RA_d1
.equ RA_partition, RA_d1
.equ RA_layout, RA_d1
.equ RA_cutstep, RA_d1
.equ RA_pt_moveend, RA_leaf
.equ RA_ly_flush, RA_leaf
