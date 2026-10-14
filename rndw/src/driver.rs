//! Harness that drives one arm through its pins, one register write per tick, using Source parts.
//! This exercises the real pin protocol (no back door) and lets circuits be built before a CPU
//! exists.  The driver occupies x in [ox, ox+21), y in [oy, oy+13) of the grid.

use crate::world::{Kind, Pin, World, CMD_PLACE, CMD_PROGRAM_ROM, CMD_WIRE, R_ANGLE, R_CMD, R_KIND, R_VAL};
use std::collections::VecDeque;

pub struct Driver {
    pub arm: u32,
    pub sources: Vec<u32>,
    queue: VecDeque<(u8, u8)>,
    shadow: [Option<u8>; 16],
}

impl Driver {
    /// Place an ARM at (ox, oy) and 13 Sources at x = ox + 20, wired to its pins in order:
    /// ADDR[0..4], EN, DATA[0..8].
    pub fn install(w: &mut World, ox: i32, oy: i32) -> Result<Driver, String> {
        let arm = w.place(Kind::Arm, ox, oy, 0)?;
        let mut sources = Vec::new();
        for i in 0..13 {
            sources.push(w.place(Kind::Source, ox + 20, oy + i, 0)?);
        }
        for i in 0..13u8 {
            let s = w.pin_site(sources[i as usize], Pin::Out(0)).unwrap();
            let a = w.pin_site(arm, Pin::In(i)).unwrap();
            w.connect(s, a)?;
        }
        w.take_en_wire_event(); // harness wiring is not a CPU being connected
        Ok(Driver { arm, sources, queue: VecDeque::new(), shadow: [None; 16] })
    }

    pub fn idle(&self) -> bool {
        self.queue.is_empty()
    }

    pub fn pending(&self) -> usize {
        self.queue.len()
    }

    /// Queue a register write (skipped if the register already holds the value; CMD always writes).
    pub fn reg(&mut self, r: usize, v: u8) {
        if r != R_CMD && self.shadow[r] == Some(v) {
            return;
        }
        self.shadow[r] = Some(v);
        self.queue.push_back((r as u8, v));
    }

    fn reg16(&mut self, lo: usize, v: i32) {
        self.reg(lo, (v & 0xFF) as u8);
        self.reg(lo + 1, ((v >> 8) & 0xFF) as u8);
    }

    pub fn nop(&mut self, n: usize) {
        for _ in 0..n {
            self.reg(R_CMD, 0);
        }
    }

    pub fn place(&mut self, kind: u8, x: i32, y: i32, rot: u8) {
        self.reg16(0, x);
        self.reg16(2, y);
        self.reg(R_KIND, kind);
        self.reg(R_ANGLE, rot);
        self.reg(R_CMD, CMD_PLACE);
    }

    pub fn wire(&mut self, ax: i32, ay: i32, bx: i32, by: i32) {
        self.reg16(0, ax);
        self.reg16(2, ay);
        self.reg16(4, bx);
        self.reg16(6, by);
        self.reg(R_CMD, CMD_WIRE);
    }

    pub fn program_rom(&mut self, x: i32, y: i32, addr: u16, val: u8) {
        self.reg16(0, x);
        self.reg16(2, y);
        self.reg16(4, addr as i32);
        self.reg(R_VAL, val);
        self.reg(R_CMD, CMD_PROGRAM_ROM);
    }

    /// Drive the sources for the coming tick: the next queued write with EN = 1, or EN = 0.
    pub fn pre_step(&mut self, w: &mut World) {
        let (en, reg, val) = match self.queue.pop_front() {
            Some((r, v)) => (1, r, v),
            None => (0, 0, 0),
        };
        for i in 0..4 {
            w.set_source(self.sources[i], (reg >> i) & 1);
        }
        w.set_source(self.sources[4], en);
        for j in 0..8 {
            w.set_source(self.sources[5 + j], (val >> j) & 1);
        }
        w.settle();
    }
}
