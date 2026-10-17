//! Core world: parts, pins, wires, grid occupancy, event-driven settling, DFF latching and the
//! arm (memory-mapped command device).  Semantics follow RNDW_SPEC.md.
//! Local copy of nandgen/rndw/src/world.rs; the only addition is the optional arm command log
//! (`log_cmds`, `cmdlog`) used by the mutant experiments.

use std::collections::{HashMap, VecDeque};
use std::hash::{BuildHasherDefault, Hasher};

pub const NONE: u32 = u32::MAX;
pub const ARM_REGS: usize = 16;
/// Arm register indices (RNDW_SPEC.md section 6).
pub const R_AXL: usize = 0;
pub const R_KIND: usize = 8;
pub const R_ANGLE: usize = 9;
pub const R_VAL: usize = 10;
pub const R_CMD: usize = 15;
/// Arm command codes.
pub const CMD_NOP: u8 = 0;
pub const CMD_PLACE: u8 = 1;
pub const CMD_WIRE: u8 = 2;
pub const CMD_PROGRAM_ROM: u8 = 3;

// ---------------------------------------------------------------- fast hasher (std only)
#[derive(Default, Clone)]
pub struct Fx(u64);
impl Hasher for Fx {
    fn write(&mut self, bytes: &[u8]) {
        for b in bytes {
            self.0 = (self.0.rotate_left(5) ^ *b as u64).wrapping_mul(0x517c_c1b7_2722_0a95);
        }
    }
    fn write_u32(&mut self, i: u32) {
        self.0 = (self.0.rotate_left(5) ^ i as u64).wrapping_mul(0x517c_c1b7_2722_0a95);
    }
    fn finish(&self) -> u64 {
        self.0
    }
}
pub type FxMap<K, V> = HashMap<K, V, BuildHasherDefault<Fx>>;

// ---------------------------------------------------------------- parts and pins
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Nand = 0,
    Dff = 1,
    Rom = 2,
    Arm = 3,
    /// Harness-only forced signal source (not placeable by an arm).
    Source = 4,
}

impl Kind {
    /// Kinds an arm may place (KIND register values 0..=3).
    pub fn from_code(c: u8) -> Option<Kind> {
        match c {
            0 => Some(Kind::Nand),
            1 => Some(Kind::Dff),
            2 => Some(Kind::Rom),
            3 => Some(Kind::Arm),
            _ => None,
        }
    }
    /// Kinds including the harness-only Source (used by state files).
    pub fn from_code_any(c: u8) -> Option<Kind> {
        if c == 4 {
            Some(Kind::Source)
        } else {
            Kind::from_code(c)
        }
    }
    pub fn code(self) -> u8 {
        self as u8
    }
    pub fn name(self) -> &'static str {
        match self {
            Kind::Nand => "NAND",
            Kind::Dff => "DFF",
            Kind::Rom => "ROM",
            Kind::Arm => "ARM",
            Kind::Source => "SOURCE",
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Pin {
    In(u8),
    Out(u8),
}

impl Pin {
    fn code(self) -> u8 {
        match self {
            Pin::In(i) => i,
            Pin::Out(j) => 128 + j,
        }
    }
}

fn pin_from_code(c: u8) -> Option<Pin> {
    if c == 255 {
        None
    } else if c < 128 {
        Some(Pin::In(c))
    } else {
        Some(Pin::Out(c - 128))
    }
}

pub fn pin_counts(kind: Kind, rom_abits: u32) -> (usize, usize) {
    match kind {
        Kind::Nand => (2, 1),
        Kind::Dff => (1, 1),
        Kind::Rom => (rom_abits as usize, 8),
        Kind::Arm => (13, 0), // ADDR[0..4], EN, DATA[0..8]
        Kind::Source => (0, 1),
    }
}

/// Footprint in the default orientation: (width, height, pins at (dx, dy)).
pub fn base_layout(kind: Kind, rom_abits: u32) -> (i32, i32, Vec<(i32, i32, Pin)>) {
    match kind {
        Kind::Nand => (2, 2, vec![(0, 0, Pin::In(0)), (0, 1, Pin::In(1)), (1, 0, Pin::Out(0))]),
        Kind::Dff => (2, 2, vec![(0, 0, Pin::In(0)), (1, 0, Pin::Out(0))]),
        Kind::Rom => {
            let h = rom_abits.max(8) as i32;
            let mut v = Vec::new();
            for i in 0..rom_abits {
                v.push((0, i as i32, Pin::In(i as u8)));
            }
            for j in 0..8 {
                v.push((1, j, Pin::Out(j as u8)));
            }
            (2, h, v)
        }
        Kind::Arm => {
            let mut v = Vec::new();
            for i in 0..4 {
                v.push((0, i, Pin::In(i as u8)));
            }
            v.push((0, 4, Pin::In(4)));
            for j in 0..8 {
                v.push((1, j, Pin::In(5 + j as u8)));
            }
            (2, 9, v)
        }
        Kind::Source => (1, 1, vec![(0, 0, Pin::Out(0))]),
    }
}

fn rot_xy(dx: i32, dy: i32, w: i32, h: i32, rot: u8) -> (i32, i32) {
    match rot {
        0 => (dx, dy),
        1 => (h - 1 - dy, dx),
        2 => (w - 1 - dx, h - 1 - dy),
        _ => (dy, w - 1 - dx),
    }
}

/// Footprint rotated by rot * 90 degrees about the origin; the rotated box starts at (0, 0).
pub fn oriented_layout(kind: Kind, rot: u8, rom_abits: u32) -> (i32, i32, Vec<(i32, i32, Pin)>) {
    let (w, h, pins) = base_layout(kind, rom_abits);
    let (nw, nh) = if rot % 2 == 0 { (w, h) } else { (h, w) };
    let pins = pins
        .into_iter()
        .map(|(dx, dy, p)| {
            let (a, b) = rot_xy(dx, dy, w, h, rot);
            (a, b, p)
        })
        .collect();
    (nw, nh, pins)
}

#[derive(Clone, Debug)]
pub struct Part {
    pub kind: Kind,
    pub x: i32,
    pub y: i32,
    pub rot: u8,
    pub w: i32,
    pub h: i32,
    pub in_base: u32,
    pub out_base: u32,
    pub wired: bool,
    /// ROM: index into World::roms.  ARM: index into World::arms.
    pub aux: u32,
}

#[derive(Clone, Debug)]
pub struct Config {
    pub width: u32,
    pub height: u32,
    pub rom_abits: u32,
    pub event_limit: u64,
}

impl Default for Config {
    fn default() -> Self {
        Config { width: 65536, height: 65536, rom_abits: 12, event_limit: 5_000_000 }
    }
}

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if self.width == 0 || self.height == 0 || self.width > 65536 || self.height > 65536 {
            return Err("width and height must be in 1..=65536 (16-bit coordinates)".into());
        }
        if self.rom_abits == 0 || self.rom_abits > 16 {
            return Err("rom_abits must be in 1..=16".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
pub struct Stats {
    pub tick: u64,
    pub nand: u64,
    pub dff: u64,
    pub rom: u64,
    pub arm: u64,
    pub source: u64,
    pub wires: u64,
    pub wire_len: u64,
    pub faults: u64,
    pub events: u64,
    pub rom_bits: u64,
    pub rom_written: u64,
}

impl Stats {
    pub fn line(&self) -> String {
        format!(
            "tick {} | NAND {} DFF {} wires {} robots {} ROM {} | faults {} | events {}",
            self.tick, self.nand, self.dff, self.wires, self.arm, self.rom, self.faults, self.events
        )
    }
}

fn key(x: i32, y: i32) -> u32 {
    ((x as u32) << 16) | (y as u32 & 0xFFFF)
}

/// One logged arm command: (command code, the 16 registers at execution, error text if it faulted).
pub type CmdRec = (u8, [u8; ARM_REGS], Option<String>);

pub struct World {
    pub cfg: Config,
    pub parts: Vec<Part>,
    /// Per input pin: driving signal id, or NONE.
    pub in_src: Vec<u32>,
    /// Per output signal: current value.
    pub val: Vec<u8>,
    /// Per output signal: owning part.
    pub sig_owner: Vec<u32>,
    /// Per signal: combinational consumers (NAND and ROM parts).
    fanout: Vec<Vec<u32>>,
    /// site -> (part, pin code or 255 for a non-pin cell).
    cells: FxMap<u32, (u32, u8)>,
    pub roms: Vec<Vec<u8>>,
    pub arms: Vec<[u8; ARM_REGS]>,
    /// Wires as (out_x, out_y, in_x, in_y), in creation order.
    pub wires: Vec<(i32, i32, i32, i32)>,
    pub wire_len: u64,
    pub tick: u64,
    pub faults: u64,
    pub fault_log: Vec<String>,
    pub events: u64,
    pub rom_written: u64,
    pub en_wire_events: u64,
    en_wire_flag: bool,
    counts: [u64; 5],
    dffs: Vec<u32>,
    arm_parts: Vec<u32>,
    queue: VecDeque<u32>,
    in_queue: Vec<bool>,
    scratch_changes: Vec<(u32, u8)>,
    scratch_cmds: Vec<(usize, u8, u8)>,
    /// Added for the mutant experiments: log every executed arm command (all arms).
    pub log_cmds: bool,
    pub cmdlog: Vec<CmdRec>,
}

impl World {
    pub fn new(cfg: Config) -> World {
        World {
            cfg,
            parts: Vec::new(),
            in_src: Vec::new(),
            val: Vec::new(),
            sig_owner: Vec::new(),
            fanout: Vec::new(),
            cells: FxMap::default(),
            roms: Vec::new(),
            arms: Vec::new(),
            wires: Vec::new(),
            wire_len: 0,
            tick: 0,
            faults: 0,
            fault_log: Vec::new(),
            events: 0,
            rom_written: 0,
            en_wire_events: 0,
            en_wire_flag: false,
            counts: [0; 5],
            dffs: Vec::new(),
            arm_parts: Vec::new(),
            queue: VecDeque::new(),
            in_queue: Vec::new(),
            scratch_changes: Vec::new(),
            scratch_cmds: Vec::new(),
            log_cmds: false,
            cmdlog: Vec::new(),
        }
    }

    // ------------------------------------------------------------ faults and stats
    pub fn fault(&mut self, msg: String) {
        self.faults += 1;
        if self.fault_log.len() < 256 {
            self.fault_log.push(format!("t{}: {}", self.tick, msg));
        }
    }

    pub fn stats(&self) -> Stats {
        Stats {
            tick: self.tick,
            nand: self.counts[0],
            dff: self.counts[1],
            rom: self.counts[2],
            arm: self.counts[3],
            source: self.counts[4],
            wires: self.wires.len() as u64,
            wire_len: self.wire_len,
            faults: self.faults,
            events: self.events,
            rom_bits: self.counts[2] * (1u64 << self.cfg.rom_abits) * 8,
            rom_written: self.rom_written,
        }
    }

    /// True once if a wire has been attached to the EN pin of any ARM since the last call.
    pub fn take_en_wire_event(&mut self) -> bool {
        std::mem::replace(&mut self.en_wire_flag, false)
    }

    // ------------------------------------------------------------ queries
    #[inline]
    fn rd(&self, ipin: u32) -> u8 {
        let s = self.in_src[ipin as usize];
        if s == NONE {
            0
        } else {
            self.val[s as usize]
        }
    }

    pub fn out_value(&self, part: u32, j: u32) -> u8 {
        self.val[(self.parts[part as usize].out_base + j) as usize]
    }

    pub fn pin_value(&self, part: u32, pin: Pin) -> u8 {
        let p = &self.parts[part as usize];
        match pin {
            Pin::In(i) => self.rd(p.in_base + i as u32),
            Pin::Out(j) => self.val[(p.out_base + j as u32) as usize],
        }
    }

    pub fn pin_site(&self, part: u32, pin: Pin) -> Option<(i32, i32)> {
        let p = &self.parts[part as usize];
        let (_, _, pins) = oriented_layout(p.kind, p.rot, self.cfg.rom_abits);
        pins.into_iter().find(|q| q.2 == pin).map(|q| (p.x + q.0, p.y + q.1))
    }

    pub fn site_pin(&self, x: i32, y: i32) -> Option<(u32, Pin)> {
        let &(p, c) = self.cells.get(&key(x, y))?;
        pin_from_code(c).map(|pin| (p, pin))
    }

    /// Part occupying a site (pin or not).
    pub fn part_at(&self, x: i32, y: i32) -> Option<u32> {
        self.cells.get(&key(x, y)).map(|c| c.0)
    }

    /// Value of the output signal at an output-pin site, if any.
    pub fn signal_at_site(&self, x: i32, y: i32) -> Option<u8> {
        match self.site_pin(x, y)? {
            (p, Pin::Out(j)) => Some(self.out_value(p, j as u32)),
            _ => None,
        }
    }

    // ------------------------------------------------------------ building
    pub fn place(&mut self, kind: Kind, x: i32, y: i32, rot: u8) -> Result<u32, String> {
        if rot > 3 {
            return Err(format!("bad rotation {} (must be 0..3)", rot));
        }
        let abits = self.cfg.rom_abits;
        let (w, h, pins) = oriented_layout(kind, rot, abits);
        if x < 0 || y < 0 || x + w > self.cfg.width as i32 || y + h > self.cfg.height as i32 {
            return Err(format!("{} at ({},{}) is out of bounds", kind.name(), x, y));
        }
        for dx in 0..w {
            for dy in 0..h {
                if self.cells.contains_key(&key(x + dx, y + dy)) {
                    return Err(format!("{} at ({},{}) overlaps an existing part", kind.name(), x, y));
                }
            }
        }
        let id = self.parts.len() as u32;
        let (n_in, n_out) = pin_counts(kind, abits);
        let in_base = self.in_src.len() as u32;
        let out_base = self.val.len() as u32;
        self.in_src.resize(self.in_src.len() + n_in, NONE);
        // A NAND with unconnected inputs reads (0, 0), so its output starts at 1 (tie-high).
        let init = if kind == Kind::Nand { 1 } else { 0 };
        for _ in 0..n_out {
            self.val.push(init);
            self.sig_owner.push(id);
            self.fanout.push(Vec::new());
        }
        let aux = match kind {
            Kind::Rom => {
                self.roms.push(vec![0u8; 1usize << abits]);
                self.roms.len() - 1
            }
            Kind::Arm => {
                self.arms.push([0; ARM_REGS]);
                self.arms.len() - 1
            }
            _ => 0,
        } as u32;
        for dx in 0..w {
            for dy in 0..h {
                let code = pins
                    .iter()
                    .find(|p| p.0 == dx && p.1 == dy)
                    .map(|p| p.2.code())
                    .unwrap_or(255);
                self.cells.insert(key(x + dx, y + dy), (id, code));
            }
        }
        self.parts.push(Part { kind, x, y, rot, w, h, in_base, out_base, wired: false, aux });
        self.in_queue.push(false);
        self.counts[kind.code() as usize] += 1;
        match kind {
            Kind::Dff => self.dffs.push(id),
            Kind::Arm => self.arm_parts.push(id),
            _ => {}
        }
        Ok(id)
    }

    /// Connect an output pin site to an input pin site (either argument order).
    pub fn connect(&mut self, a: (i32, i32), b: (i32, i32)) -> Result<(), String> {
        let pa = self.site_pin(a.0, a.1).ok_or_else(|| format!("({},{}) is not a pin site", a.0, a.1))?;
        let pb = self.site_pin(b.0, b.1).ok_or_else(|| format!("({},{}) is not a pin site", b.0, b.1))?;
        let ((op, oj, osite), (ip, ii, isite)) = match (pa.1, pb.1) {
            (Pin::Out(j), Pin::In(i)) => ((pa.0, j, a), (pb.0, i, b)),
            (Pin::In(i), Pin::Out(j)) => ((pb.0, j, b), (pa.0, i, a)),
            _ => {
                return Err(format!(
                    "wire ({},{})-({},{}) must join one output pin and one input pin",
                    a.0, a.1, b.0, b.1
                ))
            }
        };
        let sig = self.parts[op as usize].out_base + oj as u32;
        let ipin = self.parts[ip as usize].in_base + ii as u32;
        if self.in_src[ipin as usize] != NONE {
            return Err(format!("input pin at ({},{}) already has a driver", isite.0, isite.1));
        }
        self.in_src[ipin as usize] = sig;
        self.parts[op as usize].wired = true;
        self.parts[ip as usize].wired = true;
        self.wires.push((osite.0, osite.1, isite.0, isite.1));
        self.wire_len += ((osite.0 - isite.0).abs() + (osite.1 - isite.1).abs()) as u64;
        let ck = self.parts[ip as usize].kind;
        if ck == Kind::Nand || ck == Kind::Rom {
            self.fanout[sig as usize].push(ip);
            self.schedule(ip);
        }
        if ck == Kind::Arm && ii == 4 {
            self.en_wire_events += 1;
            self.en_wire_flag = true;
        }
        Ok(())
    }

    /// ROM programming as the arm does it: only while no wire touches the ROM.
    pub fn program_rom(&mut self, x: i32, y: i32, addr: usize, v: u8) -> Result<(), String> {
        let pid = self.part_at(x, y).ok_or_else(|| format!("no part at ({},{})", x, y))?;
        let p = &self.parts[pid as usize];
        if p.kind != Kind::Rom || p.x != x || p.y != y {
            return Err(format!("no ROM with its origin at ({},{})", x, y));
        }
        if p.wired {
            return Err(format!("ROM at ({},{}) is wired; programming is disabled", x, y));
        }
        if addr >= (1usize << self.cfg.rom_abits) {
            return Err(format!("ROM address {} out of range", addr));
        }
        let aux = p.aux as usize;
        self.roms[aux][addr] = v;
        self.rom_written += 1;
        self.schedule(pid);
        Ok(())
    }

    /// Direct ROM write for seed worlds and state loading (ignores the wire lock).
    pub fn rom_poke(&mut self, part: u32, addr: usize, v: u8) -> Result<(), String> {
        let p = self.parts.get(part as usize).ok_or("bad part id")?;
        if p.kind != Kind::Rom {
            return Err(format!("part {} is not a ROM", part));
        }
        if addr >= (1usize << self.cfg.rom_abits) {
            return Err(format!("ROM address {} out of range", addr));
        }
        let aux = p.aux as usize;
        self.roms[aux][addr] = v;
        self.schedule(part);
        Ok(())
    }

    /// Force a Source part's output (harness only).
    pub fn set_source(&mut self, part: u32, v: u8) {
        let s = self.parts[part as usize].out_base;
        self.set_out(s, v & 1);
    }

    /// Set a DFF's stored value directly (state loading).
    pub fn set_dff(&mut self, part: u32, v: u8) {
        let s = self.parts[part as usize].out_base;
        self.set_out(s, v & 1);
    }

    // ------------------------------------------------------------ evaluation
    fn schedule(&mut self, p: u32) {
        if !self.in_queue[p as usize] {
            self.in_queue[p as usize] = true;
            self.queue.push_back(p);
        }
    }

    fn set_out(&mut self, sig: u32, v: u8) {
        let s = sig as usize;
        if self.val[s] != v {
            self.val[s] = v;
            for i in 0..self.fanout[s].len() {
                let c = self.fanout[s][i];
                self.schedule(c);
            }
        }
    }

    fn eval_part(&mut self, p: u32) {
        let part = &self.parts[p as usize];
        let (kind, ib, ob, aux) = (part.kind, part.in_base, part.out_base, part.aux);
        match kind {
            Kind::Nand => {
                let a = self.rd(ib);
                let b = self.rd(ib + 1);
                self.set_out(ob, 1 - (a & b));
            }
            Kind::Rom => {
                let mut addr = 0usize;
                for i in 0..self.cfg.rom_abits {
                    addr |= (self.rd(ib + i) as usize) << i;
                }
                let byte = self.roms[aux as usize][addr];
                for j in 0..8u32 {
                    self.set_out(ob + j, (byte >> j) & 1);
                }
            }
            _ => {}
        }
    }

    /// Settle the combinational network.  Returns false (and records a fault) if it does not
    /// converge within the configured event limit.
    pub fn settle(&mut self) -> bool {
        let limit = self.cfg.event_limit;
        let mut n = 0u64;
        while let Some(p) = self.queue.pop_front() {
            self.in_queue[p as usize] = false;
            n += 1;
            if n > limit {
                while let Some(q) = self.queue.pop_front() {
                    self.in_queue[q as usize] = false;
                }
                self.events += n;
                self.fault(format!("combinational network did not settle within {} events", limit));
                return false;
            }
            self.eval_part(p);
        }
        self.events += n;
        true
    }

    fn latch_dffs(&mut self) {
        let mut changes = std::mem::take(&mut self.scratch_changes);
        changes.clear();
        for &p in &self.dffs {
            let part = &self.parts[p as usize];
            let d = self.rd(part.in_base);
            if self.val[part.out_base as usize] != d {
                changes.push((part.out_base, d));
            }
        }
        for &(s, d) in &changes {
            self.set_out(s, d);
        }
        self.scratch_changes = changes;
    }

    /// One global tick: (1) arms apply commands read from their settled pins, then the network
    /// re-settles; (2) every DFF latches D; (3) the network settles.
    pub fn step(&mut self) {
        self.run_arms();
        self.settle();
        self.latch_dffs();
        self.settle();
        self.tick += 1;
    }

    // ------------------------------------------------------------ arm
    fn run_arms(&mut self) {
        let mut cmds = std::mem::take(&mut self.scratch_cmds);
        cmds.clear();
        for &p in &self.arm_parts {
            let part = &self.parts[p as usize];
            let b = part.in_base;
            if self.rd(b + 4) == 1 {
                let mut addr = 0u8;
                for i in 0..4u32 {
                    addr |= self.rd(b + i) << i;
                }
                let mut data = 0u8;
                for j in 0..8u32 {
                    data |= self.rd(b + 5 + j) << j;
                }
                cmds.push((part.aux as usize, addr, data));
            }
        }
        for &(ai, addr, data) in &cmds {
            self.arm_write(ai, addr, data);
        }
        self.scratch_cmds = cmds;
    }

    fn arm_write(&mut self, ai: usize, addr: u8, data: u8) {
        match addr {
            0..=10 => self.arms[ai][addr as usize] = data,
            15 => self.arm_exec(ai, data),
            _ => self.fault(format!("arm write to reserved register {}", addr)),
        }
    }

    /// Executes a command from explicit arm registers/origin (used by the mutant harness to replay a
    /// stream, and by the normal path below).
    pub fn arm_exec(&mut self, ai: usize, code: u8) {
        let r = self.arms[ai];
        let rd16 = |lo: usize| (r[lo] as i32) | ((r[lo + 1] as i32) << 8);
        // v0.5: coordinates are signed 16-bit (two's complement) offsets from the arm's origin.
        let (ox, oy) = {
            let p = &self.parts[self.arm_parts[ai] as usize];
            (p.x, p.y)
        };
        let sx = |lo: usize| rd16(lo) as u16 as i16 as i32;
        let (ax, ay) = (ox + sx(0), oy + sx(2));
        let bx_raw = rd16(4);
        let (bx, by) = (ox + sx(4), oy + sx(6));
        let res = match code {
            CMD_NOP => Ok(()),
            CMD_PLACE => match Kind::from_code(r[R_KIND]) {
                None => Err(format!("PLACE with bad KIND {}", r[R_KIND])),
                Some(k) => self.place(k, ax, ay, r[R_ANGLE]).map(|_| ()),
            },
            CMD_WIRE => self.connect((ax, ay), (bx, by)),
            CMD_PROGRAM_ROM => self.program_rom(ax, ay, bx_raw as usize, r[R_VAL]),
            c => Err(format!("unknown arm command {}", c)),
        };
        if self.log_cmds && code != CMD_NOP {
            self.cmdlog.push((code, r, res.as_ref().err().cloned()));
        }
        if let Err(msg) = res {
            self.fault(msg);
        }
    }

    /// Index of the arm (into World::arms) belonging to a part id.
    pub fn arm_index_of(&self, part: u32) -> Option<usize> {
        let p = &self.parts[part as usize];
        if p.kind == Kind::Arm { Some(p.aux as usize) } else { None }
    }
}
