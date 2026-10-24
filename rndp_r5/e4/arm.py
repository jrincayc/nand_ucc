"""arm.py -- register-level model of the RNDP arm: write(reg, value) -> executes commands; collects ('place',kind,x,y,rot,val) ('track',l,x0,y0,x1,y1) ('via',x,y) in arm-relative coordinates."""
class Arm:
    def __init__(self): self.r = [0] * 16; self.cmds = []; self.faults = 0; self.writes = 0
    def s16(self, lo, hi): v = self.r[lo] | self.r[hi] << 8; return v - 65536 if v >= 32768 else v
    def write(self, reg, val):
        self.writes += 1
        if 11 <= reg <= 14: self.faults += 1; return
        self.r[reg] = val & 255
        if reg != 15: return
        ax, ay, bx, by = self.s16(0, 1), self.s16(2, 3), self.s16(4, 5), self.s16(6, 7)
        c = val & 255
        if c == 1: self.cmds.append(('place', self.r[8], ax, ay, self.r[9], self.r[10]))
        elif c == 4: self.cmds.append(('track', self.r[10], ax, ay, bx, by))
        elif c == 5: self.cmds.append(('via', ax, ay))
        elif c == 0: pass
        else: self.faults += 1
