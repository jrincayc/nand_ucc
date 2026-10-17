// hack.c -- fast emulator of Hack-vN-AB (isahack.py semantics) with arm-command decoding, ROM access tracing and compare mode.
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int32_t cmd, kind, angle, ax, ay, bx, by; } Cmd;
enum { ST_HALT = 0, ST_TIMEOUT = 1, ST_ILLEGAL = 2, ST_BADCMD = 3, ST_DIVERGED = 4, ST_LOGFULL = 5, ST_BADROM = 6, ST_SHORT = 7 };

static inline int s16(int lo, int hi) { int v = lo | hi << 8; return v >= 32768 ? v - 65536 : v; }

// returns status.  out[0]=instr count, out[1]=non-rom commands, out[2]=rom commands, out[3]=diverge index, out[4],out[5]=rom origin x,y
int run(int ab, int ramn, const uint8_t *rom, int rom_len, int ram_fill, int64_t max_instr,
        const Cmd *ref, int nref, int compare, int rom_ox, int rom_oy,
        uint8_t *child, uint8_t *fetched, uint8_t *dread, Cmd *outcmds, int64_t outcap, int64_t *out)
{
    const int rom_base = 1 << (ab - 1), arm_base = rom_base - 16, amask = (1 << ab) - 1;
    uint8_t ram[4096]; memset(ram, ram_fill, sizeof ram);
    int regs[16] = {0};
    int64_t instr = 0; int nnon = 0, nrom = 0; int have_origin = compare; int ox = rom_ox, oy = rom_oy;
    int pc = rom_base, A = 0, D = 0, status = ST_TIMEOUT;
    out[3] = -1;
#define PEEK(a, kind) ({ int _a = (a) & amask, _v; \
        if (_a < ramn) _v = ram[_a]; else if (_a < rom_base) _v = 0; \
        else { int _o = _a - rom_base; _v = _o < rom_len ? rom[_o] : 0; \
               if (kind) { if (fetched) fetched[_o] |= kind; } else { if (dread) dread[_o] = 1; } } _v; })
    while (instr < max_instr) {
        int i0 = pc;
        int lo = PEEK(pc, 1), hi = PEEK(pc + 1, 2);
        pc = (pc + 2) & amask; instr++;
        int ins = lo | hi << 8;
        if ((ins >> 15) == 0) { A = ins & amask; continue; }
        int top = ins >> 13;
        if (top == 6) { int l = PEEK(A, 0), h = PEEK(A + 1, 0); A = l | ((h & (amask >> 8)) << 8); continue; }
        if (top != 7) { status = ST_ILLEGAL; goto done; }
        int a = ins >> 12 & 1, c = ins >> 6 & 63, d = ins >> 3 & 7, j = ins & 7;
        int y = a ? PEEK(A, 0) : (A & 255), r;
        switch (c) {
            case 0b101010: r = 0; break;       case 0b111111: r = 1; break;      case 0b111010: r = -1; break;
            case 0b001100: r = D; break;       case 0b110000: r = y; break;      case 0b001101: r = ~D; break;
            case 0b110001: r = ~y; break;      case 0b001111: r = -D; break;     case 0b110011: r = -y; break;
            case 0b011111: r = D + 1; break;   case 0b110111: r = y + 1; break;  case 0b001110: r = D - 1; break;
            case 0b110010: r = y - 1; break;   case 0b000010: r = D + y; break;  case 0b010011: r = D - y; break;
            case 0b000111: r = y - D; break;   case 0b000000: r = D & y; break;  case 0b010101: r = D | y; break;
            default: status = ST_ILLEGAL; goto done;
        }
        int o = r & 255, s = o > 127 ? o - 256 : o, oldA = A;
        if (d & 1) {                                   // memory write
            int w = oldA & amask;
            if (w < ramn) ram[w] = o;
            else if (w >= arm_base && w < rom_base) {
                int reg = w - arm_base; regs[reg] = o;
                if (reg == 15) {
                    int v = o;
                    if (v < 1 || v > 3) { status = ST_BADCMD; goto done; }
                    int ax = s16(regs[0], regs[1]), ay = s16(regs[2], regs[3]);
                    if (v == 3) {
                        int bx = regs[4] | regs[5] << 8;
                        if (!have_origin) { ox = ax; oy = ay; have_origin = 1; }
                        if (ax != ox || ay != oy || bx >= rom_base) { status = ST_BADROM; out[3] = nnon; goto done; }
                        if (child) child[bx] = regs[10];
                        nrom++;
                    } else {
                        Cmd cm = { v, 0, 0, ax, ay, 0, 0 };
                        if (v == 1) { if (regs[8] > 3) { status = ST_BADCMD; goto done; } cm.kind = regs[8]; cm.angle = regs[9]; }
                        else { cm.bx = s16(regs[4], regs[5]); cm.by = s16(regs[6], regs[7]); }
                        if (compare) {
                            if (nnon >= nref || memcmp(&ref[nnon], &cm, sizeof cm)) { out[3] = nnon; status = ST_DIVERGED; goto done; }
                        }
                        if (outcmds) { if (nnon >= outcap) { status = ST_LOGFULL; goto done; } outcmds[nnon] = cm; }
                        nnon++;
                    }
                }
            }
        }
        if (d & 2) D = o;
        if (d & 4) A = (A & ~255) | o;
        if (((j & 1) && s > 0) || ((j & 2) && s == 0) || ((j & 4) && s < 0)) {
            if (oldA == i0 - 2) { status = ST_HALT; goto done; }
            pc = oldA;
        }
    }
done:
    if (status == ST_HALT && compare && nnon != nref) { status = ST_SHORT; out[3] = nnon; }
    out[0] = instr; out[1] = nnon; out[2] = nrom; out[4] = ox; out[5] = oy;
    return status;
}
