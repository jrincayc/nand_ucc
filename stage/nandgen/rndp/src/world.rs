//! Core RNDP world (RNDP_SPEC.md v0.3): parts, pads, copper, nets, settle, latch, arm.
//!
//! Connectivity: every pad and every copper cell is a union-find node.  A pad is copper in its cell
//! on every layer.  Copper never goes away, so nets only merge; the union-find is the cache.
//! Each net root carries its driver signal (at most one) and its input pins.

use std::collections::{HashMap, VecDeque};
use std::hash::{BuildHasherDefault, Hasher};

pub const NONE: u32 = u32::MAX;
pub const ARM_REGS: usize = 16;
pub const R_KIND: usize = 8;
pub const R_ANGLE: usize = 9;
pub const R_VAL: usize = 10;
pub const CMD_NOP: u8 = 0;
pub const CMD_PLACE: u8 = 1;
pub const CMD_PROGRAM_ROM: u8 = 3;
pub const CMD_TRACK: u8 = 4;
pub const CMD_VIA: u8 = 5;

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
    fn write_u64(&mut self, i: u64) {
        self.0 = (self.0.rotate_left(5) ^ i).wrapping_mul(0x517c_c1b7_2722_0a95);
    }
    fn finish(&self) -> u64 {
        self.0
    }
}
pub type FxMap<K, V> = HashMap<K, V, BuildHasherDefault<Fx>>;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Nand = 0,
    Dff = 1,
    Rom = 2,
    Arm = 3,
    Ram = 4,
    /// Harness-only forced signal source (not placeable by an arm).
    Source = 5,
}

impl Kind {
    /// Kinds an arm may place (KIND register 0..=4).
    pub fn from_code(c: u8) -> Option<Kind> {
        match c {
            0 => Some(Kind::Nand),
            1 => Some(Kind::Dff),
            2 => Some(Kind::Rom),
            3 => Some(Kind::Arm),
            4 => Some(Kind::Ram),
            _ => None,
        }
    }
    pub fn from_code_any(c: u8) -> Option<Kind> {
        if c == 5 {
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
            Kind::Ram => "RAM",
            Kind::Source => "SOURCE",
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Pin {
    In(u8),
    Out(u8),
}

pub fn pin_counts(kind: Kind, a: u32) -> (usize, usize) {
    match kind {
        Kind::Nand => (2, 1),
        Kind::Dff => (1, 1),
        Kind::Rom => (a as usize, 8),
        Kind::Ram => (a as usize + 9, 8),
        Kind::Arm => (13, 0),
        Kind::Source => (0, 1),
    }
}

/// Footprint in the default orientation: (w, h, pins at (dx, dy)).  Spec section 4.
pub fn base_layout(kind: Kind, a: u32) -> (i32, i32, Vec<(i32, i32, Pin)>) {
    match kind {
        Kind::Nand => (2, 2, vec![(0, 0, Pin::In(0)), (0, 1, Pin::In(1)), (1, 0, Pin::Out(0))]),
        Kind::Dff => (2, 2, vec![(0, 0, Pin::In(0)), (1, 0, Pin::Out(0))]),
        Kind::Rom => {
            let mut v = Vec::new();
            for i in 0..a {
                v.push((0, i as i32, Pin::In(i as u8)));
            }
            for j in 0..8 {
                v.push((1, j, Pin::Out(j as u8)));
            }
            (2, a.max(8) as i32, v)
        }
        Kind::Ram => {
            let mut v = Vec::new();
            for i in 0..a {
                v.push((0, i as i32, Pin::In(i as u8)));
            }
            v.push((0, a as i32, Pin::In(a as u8))); // WE
            for j in 0..8 {
                v.push((0, a as i32 + 1 + j, Pin::In((a + 1) as u8 + j as u8))); // DIN
                v.push((1, j, Pin::Out(j as u8))); // DOUT
            }
            (2, a as i32 + 9, v)
        }
        Kind::Arm => {
            let mut v = Vec::new();
            for i in 0..5 {
                v.push((0, i, Pin::In(i as u8))); // ADDR0..3, EN
            }
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

pub fn oriented_layout(kind: Kind, rot: u8, a: u32) -> (i32, i32, Vec<(i32, i32, Pin)>) {
    let (w, h, pins) = base_layout(kind, a);
    let (nw, nh) = if rot % 2 == 0 { (w, h) } else { (h, w) };
    let pins = pins
        .into_iter()
        .map(|(dx, dy, p)| {
            let (x, y) = rot_xy(dx, dy, w, h, rot);
            (x, y, p)
        })
        .collect();
    (nw, nh, pins)
}

/// Byte memory: dense for small address widths, sparse above 2^20 cells.
#[derive(Clone, Debug)]
pub enum Mem {
    Dense(Vec<u8>),
    Sparse(FxMap<u64, u8>),
}
impl Mem {
    pub fn new(bits: u32) -> Mem {
        if bits <= 20 {
            Mem::Dense(vec![0; 1usize << bits])
        } else {
            Mem::Sparse(FxMap::default())
        }
    }
    pub fn get(&self, a: u64) -> u8 {
        match self {
            Mem::Dense(v) => v[a as usize],
            Mem::Sparse(m) => *m.get(&a).unwrap_or(&0),
        }
    }
    pub fn set(&mut self, a: u64, v: u8) {
        match self {
            Mem::Dense(d) => d[a as usize] = v,
            Mem::Sparse(m) => {
                if v == 0 {
                    m.remove(&a);
                } else {
                    m.insert(a, v);
                }
            }
        }
    }
    pub fn nonzero(&self) -> Vec<(u64, u8)> {
        let mut r: Vec<(u64, u8)> = match self {
            Mem::Dense(v) => v.iter().enumerate().filter(|(_, &b)| b != 0).map(|(i, &b)| (i as u64, b)).collect(),
            Mem::Sparse(m) => m.iter().map(|(&a, &b)| (a, b)).collect(),
        };
        r.sort();
        r
    }
}

#[derive(Clone, Debug)]
pub struct Part {
    pub kind: Kind,
    pub x: i32,
    pub y: i32,
    pub rot: u8,
    pub w: i32,
    pub h: i32,
    /// Address width for ROM / RAM, else 0.
    pub abits: u32,
    pub in_base: u32,
    pub out_base: u32,
    /// ROM / RAM: index into World::mems.  ARM: index into World::arms.
    pub aux: u32,
    /// ROM only: a pad net has merged with something, so programming is disabled.
    pub locked: bool,
}

#[derive(Clone, Debug)]
pub struct Config {
    pub width: u32,
    pub height: u32,
    pub layers: u32,
    pub rom_on: bool,
    pub ram_on: bool,
    pub max_rom_bits: u32,
    pub max_ram_bits: u32,
    pub event_limit: u64,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            width: 65536,
            height: 65536,
            layers: 2,
            rom_on: true,
            ram_on: true,
            max_rom_bits: 16,
            max_ram_bits: 16,
            event_limit: 5_000_000,
        }
    }
}

impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if self.width == 0 || self.height == 0 || self.width > 65536 || self.height > 65536 {
            return Err("width and height must be in 1..=65536".into());
        }
        if self.layers == 0 || self.layers > 8 {
            return Err("layers must be in 1..=8".into());
        }
        if self.max_rom_bits == 0 || self.max_rom_bits > 32 || self.max_ram_bits == 0 || self.max_ram_bits > 32 {
            return Err("max ROM / RAM address bits must be in 1..=32".into());
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CopperOp {
    Seg { l: u32, x0: i32, y0: i32, x1: i32, y1: i32 },
    Via { x: i32, y: i32 },
}

#[derive(Clone, Debug, Default)]
pub struct Stats {
    pub tick: u64,
    pub counts: [u64; 6],
    pub rom_bits: u64,
    pub ram_bits: u64,
    pub rom_written: u64,
    pub nets: u64,
    pub copper_cells: Vec<u64>,
    pub segments: u64,
    pub vias: u64,
    pub track_len: u64,
    pub bbox: (i32, i32, i32, i32),
    pub faults: u64,
    pub events: u64,
}

impl Stats {
    pub fn report(&self) -> String {
        let n = &self.counts;
        let bb = self.bbox;
        let (bw, bh) = ((bb.2 - bb.0 + 1).max(0) as i64, (bb.3 - bb.1 + 1).max(0) as i64);
        format!(
            "ticks            {}\nNAND {}  DFF {}  ROM {}  RAM {}  ARM {}  SOURCE {}\nROM capacity     {} bits ({} bytes programmed by arms)\nRAM capacity     {} bits\nnets             {}\ncopper cells     {:?} per layer (pad cells excluded)\nsegments         {}  vias {}  total track length {}\nbounding box     {}x{} = {} cells  ({},{})-({},{})\nfaults           {}\nsettle events    {}",
            self.tick, n[0], n[1], n[2], n[4], n[3], n[5], self.rom_bits, self.rom_written, self.ram_bits,
            self.nets, self.copper_cells, self.segments, self.vias, self.track_len, bw, bh, bw * bh, bb.0, bb.1, bb.2, bb.3,
            self.faults, self.events
        )
    }
}

#[inline]
fn pad_key(x: i32, y: i32) -> u32 {
    ((x as u32) << 16) | (y as u32 & 0xFFFF)
}
#[inline]
fn cu_key(l: u32, x: i32, y: i32) -> u64 {
    ((l as u64) << 32) | ((x as u64) << 16) | (y as u64 & 0xFFFF)
}

pub struct World {
    pub cfg: Config,
    pub parts: Vec<Part>,
    // pins and signals
    pub in_src: Vec<u32>,
    pub in_owner: Vec<u32>,
    pub in_node: Vec<u32>,
    pub val: Vec<u8>,
    pub sig_owner: Vec<u32>,
    pub out_node: Vec<u32>,
    fanout: Vec<Vec<u32>>,
    // union-find over pads and copper cells
    parent: Vec<u32>,
    sz: Vec<u32>,
    drv: Vec<u32>,
    pins: Vec<Vec<u32>>,
    roms: Vec<Vec<u32>>,
    has_en: Vec<bool>,
    pad_at: FxMap<u32, u32>,
    part_cells: FxMap<u32, u32>,
    copper: FxMap<u64, u32>,
    pub log: Vec<CopperOp>,
    pub mems: Vec<Mem>,
    pub arms: Vec<[u8; ARM_REGS]>,
    pub tick: u64,
    pub faults: u64,
    pub fault_log: Vec<String>,
    pub events: u64,
    pub rom_written: u64,
    pub en_events: u64,
    en_flag: bool,
    counts: [u64; 6],
    track_len: u64,
    dffs: Vec<u32>,
    rams: Vec<u32>,
    arm_parts: Vec<u32>,
    queue: VecDeque<u32>,
    in_queue: Vec<bool>,
}

impl World {
    pub fn new(cfg: Config) -> World {
        World {
            cfg,
            parts: vec![],
            in_src: vec![],
            in_owner: vec![],
            in_node: vec![],
            val: vec![],
            sig_owner: vec![],
            out_node: vec![],
            fanout: vec![],
            parent: vec![],
            sz: vec![],
            drv: vec![],
            pins: vec![],
            roms: vec![],
            has_en: vec![],
            pad_at: FxMap::default(),
            part_cells: FxMap::default(),
            copper: FxMap::default(),
            log: vec![],
            mems: vec![],
            arms: vec![],
            tick: 0,
            faults: 0,
            fault_log: vec![],
            events: 0,
            rom_written: 0,
            en_events: 0,
            en_flag: false,
            counts: [0; 6],
            track_len: 0,
            dffs: vec![],
            rams: vec![],
            arm_parts: vec![],
            queue: VecDeque::new(),
            in_queue: vec![],
        }
    }

    pub fn fault(&mut self, msg: String) {
        self.faults += 1;
        if self.fault_log.len() < 256 {
            self.fault_log.push(format!("t{}: {}", self.tick, msg));
        }
    }

    /// True once if a merge joined the net of an ARM's EN pad to anything since the last call.
    pub fn take_en_event(&mut self) -> bool {
        std::mem::replace(&mut self.en_flag, false)
    }

    // ------------------------------------------------------------ union-find
    fn new_node(&mut self) -> u32 {
        let id = self.parent.len() as u32;
        self.parent.push(id);
        self.sz.push(1);
        self.drv.push(NONE);
        self.pins.push(Vec::new());
        self.roms.push(Vec::new());
        self.has_en.push(false);
        id
    }

    fn find(&mut self, mut a: u32) -> u32 {
        while self.parent[a as usize] != a {
            let p = self.parent[a as usize];
            self.parent[a as usize] = self.parent[p as usize];
            a = self.parent[a as usize];
        }
        a
    }

    fn find_ro(&self, mut a: u32) -> u32 {
        while self.parent[a as usize] != a {
            a = self.parent[a as usize];
        }
        a
    }

    fn set_in_src(&mut self, pin: u32, sig: u32) {
        self.in_src[pin as usize] = sig;
        let c = self.in_owner[pin as usize];
        if matches!(self.parts[c as usize].kind, Kind::Nand | Kind::Rom | Kind::Ram) {
            self.fanout[sig as usize].push(c);
            self.schedule(c);
        }
    }

    /// Merge two nodes.  The caller has already checked the driver rule.
    fn unite(&mut self, a: u32, b: u32) {
        let (ra, rb) = (self.find(a), self.find(b));
        if ra == rb {
            return;
        }
        if self.has_en[ra as usize] || self.has_en[rb as usize] {
            self.en_flag = true;
            self.en_events += 1;
        }
        if !self.roms[ra as usize].is_empty() || !self.roms[rb as usize].is_empty() {
            let rl: Vec<u32> = self.roms[ra as usize].iter().chain(self.roms[rb as usize].iter()).cloned().collect();
            for p in rl {
                self.parts[p as usize].locked = true;
            }
        }
        let (big, small) = if self.sz[ra as usize] >= self.sz[rb as usize] { (ra, rb) } else { (rb, ra) };
        let (db, ds) = (self.drv[big as usize], self.drv[small as usize]);
        debug_assert!(db == NONE || ds == NONE, "two drivers merged");
        let pins_small = std::mem::take(&mut self.pins[small as usize]);
        let mut pins_big = std::mem::take(&mut self.pins[big as usize]);
        if db == NONE && ds != NONE {
            for &p in &pins_big {
                self.set_in_src(p, ds);
            }
            self.drv[big as usize] = ds;
        } else if db != NONE && ds == NONE {
            for &p in &pins_small {
                self.set_in_src(p, db);
            }
        }
        pins_big.extend(pins_small);
        self.pins[big as usize] = pins_big;
        let rs = std::mem::take(&mut self.roms[small as usize]);
        self.roms[big as usize].extend(rs);
        let en = self.has_en[small as usize];
        self.has_en[big as usize] |= en;
        self.parent[small as usize] = big;
        self.sz[big as usize] += self.sz[small as usize];
    }

    /// Node of the copper in a cell on a layer (pad if the cell has one), if any.
    fn node_at(&self, l: u32, x: i32, y: i32) -> Option<u32> {
        if let Some(&n) = self.pad_at.get(&pad_key(x, y)) {
            return Some(n);
        }
        self.copper.get(&cu_key(l, x, y)).cloned()
    }

    fn node_make(&mut self, l: u32, x: i32, y: i32) -> u32 {
        if let Some(n) = self.node_at(l, x, y) {
            return n;
        }
        let n = self.new_node();
        self.copper.insert(cu_key(l, x, y), n);
        n
    }

    /// Two or more distinct roots that each hold a driver cannot be merged.
    fn drivers_conflict(&mut self, nodes: &[u32]) -> bool {
        let mut roots: Vec<u32> = nodes.iter().map(|&n| self.find_ro(n)).collect();
        roots.sort();
        roots.dedup();
        roots.iter().filter(|&&r| self.drv[r as usize] != NONE).count() > 1
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
        let (_, _, pins) = oriented_layout(p.kind, p.rot, p.abits);
        pins.into_iter().find(|q| q.2 == pin).map(|q| (p.x + q.0, p.y + q.1))
    }
    pub fn part_at(&self, x: i32, y: i32) -> Option<u32> {
        self.part_cells.get(&pad_key(x, y)).cloned()
    }
    /// Net identity of whatever copper is at (layer, x, y), or None.  Equal values mean same net.
    pub fn net_at(&self, l: u32, x: i32, y: i32) -> Option<u32> {
        self.node_at(l, x, y).map(|n| self.find_ro(n))
    }
    pub fn net_of_pin(&self, part: u32, pin: Pin) -> Option<u32> {
        let p = &self.parts[part as usize];
        let k = match pin {
            Pin::In(i) => self.in_node[(p.in_base + i as u32) as usize],
            Pin::Out(j) => self.out_node[(p.out_base + j as u32) as usize],
        };
        Some(self.find_ro(k))
    }
    pub fn is_pad(&self, x: i32, y: i32) -> bool {
        self.pad_at.contains_key(&pad_key(x, y))
    }

    // ------------------------------------------------------------ building
    pub fn place(&mut self, kind: Kind, x: i32, y: i32, rot: u8, abits: u32) -> Result<u32, String> {
        if rot > 3 {
            return Err(format!("bad rotation {} (must be 0..3)", rot));
        }
        let a = match kind {
            Kind::Rom | Kind::Ram => {
                let (on, maxb) = if kind == Kind::Rom {
                    (self.cfg.rom_on, self.cfg.max_rom_bits)
                } else {
                    (self.cfg.ram_on, self.cfg.max_ram_bits)
                };
                if !on {
                    return Err(format!("{} is disabled in this world", kind.name()));
                }
                if abits < 1 || abits > maxb {
                    return Err(format!("{} address width {} outside 1..={}", kind.name(), abits, maxb));
                }
                abits
            }
            _ => 0,
        };
        let (w, h, pins) = oriented_layout(kind, rot, a);
        if x < 0 || y < 0 || x + w > self.cfg.width as i32 || y + h > self.cfg.height as i32 {
            return Err(format!("{} at ({},{}) is out of bounds", kind.name(), x, y));
        }
        for dx in 0..w {
            for dy in 0..h {
                if self.part_cells.contains_key(&pad_key(x + dx, y + dy)) {
                    return Err(format!("{} at ({},{}) overlaps an existing part", kind.name(), x, y));
                }
            }
        }
        // Driver check: group pads by the existing nets they would join.
        let layers = self.cfg.layers;
        let mut existing: Vec<Vec<u32>> = Vec::new(); // per pad: roots of copper already in its cell
        for &(dx, dy, _) in &pins {
            let mut v = Vec::new();
            for l in 0..layers {
                if let Some(&n) = self.copper.get(&cu_key(l, x + dx, y + dy)) {
                    v.push(self.find_ro(n));
                }
            }
            v.sort();
            v.dedup();
            existing.push(v);
        }
        {
            // small DSU over [pads..., distinct roots...]
            let mut roots: Vec<u32> = existing.iter().flatten().cloned().collect();
            roots.sort();
            roots.dedup();
            let np = pins.len();
            let mut p: Vec<usize> = (0..np + roots.len()).collect();
            fn f(p: &mut Vec<usize>, mut a: usize) -> usize {
                while p[a] != a {
                    p[a] = p[p[a]];
                    a = p[a];
                }
                a
            }
            for (i, v) in existing.iter().enumerate() {
                for r in v {
                    let ri = np + roots.binary_search(r).unwrap();
                    let (a, b) = (f(&mut p, i), f(&mut p, ri));
                    if a != b {
                        p[a] = b;
                    }
                }
            }
            let mut cnt = vec![0u32; np + roots.len()];
            for (i, pin) in pins.iter().enumerate() {
                if matches!(pin.2, Pin::Out(_)) {
                    let c = f(&mut p, i);
                    cnt[c] += 1;
                }
            }
            for (k, r) in roots.iter().enumerate() {
                if self.drv[*r as usize] != NONE {
                    let c = f(&mut p, np + k);
                    cnt[c] += 1;
                }
            }
            if cnt.iter().any(|&c| c > 1) {
                return Err(format!("{} at ({},{}) would join two drivers", kind.name(), x, y));
            }
        }
        // Commit.
        let id = self.parts.len() as u32;
        let (n_in, n_out) = pin_counts(kind, a);
        let in_base = self.in_src.len() as u32;
        let out_base = self.val.len() as u32;
        self.in_src.resize(self.in_src.len() + n_in, NONE);
        self.in_owner.resize(self.in_owner.len() + n_in, id);
        self.in_node.resize(self.in_node.len() + n_in, NONE);
        let init = if kind == Kind::Nand { 1 } else { 0 };
        for _ in 0..n_out {
            self.val.push(init);
            self.sig_owner.push(id);
            self.fanout.push(Vec::new());
            self.out_node.push(NONE);
        }
        let aux = match kind {
            Kind::Rom | Kind::Ram => {
                self.mems.push(Mem::new(a));
                self.mems.len() - 1
            }
            Kind::Arm => {
                self.arms.push([0; ARM_REGS]);
                self.arms.len() - 1
            }
            _ => 0,
        } as u32;
        for dx in 0..w {
            for dy in 0..h {
                self.part_cells.insert(pad_key(x + dx, y + dy), id);
            }
        }
        self.parts.push(Part { kind, x, y, rot, w, h, abits: a, in_base, out_base, aux, locked: false });
        self.in_queue.push(false);
        self.counts[kind.code() as usize] += 1;
        match kind {
            Kind::Dff => self.dffs.push(id),
            Kind::Ram => self.rams.push(id),
            Kind::Arm => self.arm_parts.push(id),
            _ => {}
        }
        let mut pad_nodes = Vec::new();
        for &(dx, dy, pin) in &pins {
            let n = self.new_node();
            self.pad_at.insert(pad_key(x + dx, y + dy), n);
            if kind == Kind::Rom {
                self.roms[n as usize].push(id);
            }
            match pin {
                Pin::In(i) => {
                    let ip = in_base + i as u32;
                    self.in_node[ip as usize] = n;
                    self.pins[n as usize].push(ip);
                    if kind == Kind::Arm && i == 4 {
                        self.has_en[n as usize] = true;
                    }
                }
                Pin::Out(j) => {
                    let s = out_base + j as u32;
                    self.out_node[s as usize] = n;
                    self.drv[n as usize] = s;
                }
            }
            pad_nodes.push(n);
        }
        // A pad landing on existing copper joins that net (all layers).
        for (i, &(dx, dy, _)) in pins.iter().enumerate() {
            for l in 0..layers {
                if let Some(&c) = self.copper.get(&cu_key(l, x + dx, y + dy)) {
                    self.unite(pad_nodes[i], c);
                }
            }
        }
        if kind == Kind::Nand || kind == Kind::Rom || kind == Kind::Ram {
            self.schedule(id);
        }
        Ok(id)
    }

    /// Lay copper on one layer from a to b inclusive (same row or same column).  Atomic.
    pub fn track(&mut self, l: u32, a: (i32, i32), b: (i32, i32)) -> Result<(), String> {
        if l >= self.cfg.layers {
            return Err(format!("layer {} >= {}", l, self.cfg.layers));
        }
        if a.0 != b.0 && a.1 != b.1 {
            return Err(format!("TRACK ({},{})-({},{}) is not orthogonal", a.0, a.1, b.0, b.1));
        }
        let (w, h) = (self.cfg.width as i32, self.cfg.height as i32);
        for p in [a, b] {
            if p.0 < 0 || p.1 < 0 || p.0 >= w || p.1 >= h {
                return Err(format!("TRACK cell ({},{}) out of bounds", p.0, p.1));
            }
        }
        let (dx, dy) = ((b.0 > a.0) as i32 - (b.0 < a.0) as i32, (b.1 > a.1) as i32 - (b.1 < a.1) as i32);
        let n = (b.0 - a.0).abs() + (b.1 - a.1).abs() + 1;
        let mut found = Vec::new();
        for k in 0..n {
            if let Some(nd) = self.node_at(l, a.0 + dx * k, a.1 + dy * k) {
                found.push(nd);
            }
        }
        if self.drivers_conflict(&found) {
            return Err(format!("TRACK ({},{})-({},{}) would join two drivers", a.0, a.1, b.0, b.1));
        }
        let mut prev: Option<u32> = None;
        for k in 0..n {
            let nd = self.node_make(l, a.0 + dx * k, a.1 + dy * k);
            if let Some(p) = prev {
                self.unite(p, nd);
            }
            prev = Some(nd);
        }
        self.track_len += n as u64;
        self.log.push(CopperOp::Seg { l, x0: a.0, y0: a.1, x1: b.0, y1: b.1 });
        Ok(())
    }

    /// Drill a via: joins every layer at the cell.  Atomic.
    pub fn via(&mut self, x: i32, y: i32) -> Result<(), String> {
        if x < 0 || y < 0 || x >= self.cfg.width as i32 || y >= self.cfg.height as i32 {
            return Err(format!("VIA ({},{}) out of bounds", x, y));
        }
        let mut found = Vec::new();
        for l in 0..self.cfg.layers {
            if let Some(nd) = self.node_at(l, x, y) {
                found.push(nd);
            }
        }
        if self.drivers_conflict(&found) {
            return Err(format!("VIA ({},{}) would join two drivers", x, y));
        }
        let first = self.node_make(0, x, y);
        for l in 1..self.cfg.layers {
            let nd = self.node_make(l, x, y);
            self.unite(first, nd);
        }
        self.log.push(CopperOp::Via { x, y });
        Ok(())
    }

    pub fn program_rom(&mut self, x: i32, y: i32, addr: u64, v: u8) -> Result<(), String> {
        let pid = self.part_at(x, y).ok_or_else(|| format!("no part at ({},{})", x, y))?;
        let p = &self.parts[pid as usize];
        if p.kind != Kind::Rom || p.x != x || p.y != y {
            return Err(format!("no ROM with its origin at ({},{})", x, y));
        }
        if p.locked {
            return Err(format!("ROM at ({},{}) is locked", x, y));
        }
        if addr >= (1u64 << p.abits) {
            return Err(format!("ROM address {} out of range", addr));
        }
        let aux = p.aux as usize;
        self.mems[aux].set(addr, v);
        self.rom_written += 1;
        self.schedule(pid);
        Ok(())
    }

    /// Direct ROM / RAM write for state loading (ignores the lock).
    pub fn mem_poke(&mut self, part: u32, addr: u64, v: u8) -> Result<(), String> {
        let p = self.parts.get(part as usize).ok_or("bad part id")?;
        if !matches!(p.kind, Kind::Rom | Kind::Ram) {
            return Err(format!("part {} has no memory", part));
        }
        if addr >= (1u64 << p.abits) {
            return Err(format!("address {} out of range", addr));
        }
        let aux = p.aux as usize;
        self.mems[aux].set(addr, v);
        self.schedule(part);
        Ok(())
    }

    pub fn set_source(&mut self, part: u32, v: u8) {
        let s = self.parts[part as usize].out_base;
        self.set_out(s, v & 1);
    }
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

    fn read_addr(&self, ib: u32, n: u32) -> u64 {
        let mut a = 0u64;
        for i in 0..n {
            a |= (self.rd(ib + i) as u64) << i;
        }
        a
    }

    fn eval_part(&mut self, p: u32) {
        let part = &self.parts[p as usize];
        let (kind, ib, ob, aux, ab) = (part.kind, part.in_base, part.out_base, part.aux, part.abits);
        match kind {
            Kind::Nand => {
                let (a, b) = (self.rd(ib), self.rd(ib + 1));
                self.set_out(ob, 1 - (a & b));
            }
            Kind::Rom | Kind::Ram => {
                let byte = self.mems[aux as usize].get(self.read_addr(ib, ab));
                for j in 0..8u32 {
                    self.set_out(ob + j, (byte >> j) & 1);
                }
            }
            _ => {}
        }
    }

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

    fn latch(&mut self) {
        let mut dff_changes = Vec::new();
        for &p in &self.dffs {
            let part = &self.parts[p as usize];
            let d = self.rd(part.in_base);
            if self.val[part.out_base as usize] != d {
                dff_changes.push((part.out_base, d));
            }
        }
        let mut writes = Vec::new();
        for &p in &self.rams {
            let part = &self.parts[p as usize];
            let (ib, a) = (part.in_base, part.abits);
            if self.rd(ib + a) == 1 {
                let addr = self.read_addr(ib, a);
                let mut din = 0u8;
                for j in 0..8u32 {
                    din |= self.rd(ib + a + 1 + j) << j;
                }
                writes.push((p, part.aux as usize, addr, din));
            }
        }
        for (p, aux, addr, din) in writes {
            if self.mems[aux].get(addr) != din {
                self.mems[aux].set(addr, din);
                self.schedule(p);
            }
        }
        for (s, d) in dff_changes {
            self.set_out(s, d);
        }
    }

    /// One tick: arms act, network re-settles, DFFs and RAMs latch, network settles.
    pub fn step(&mut self) {
        // Settle first: a world just built (or loaded) has unsettled nets, and the arms must sample settled values (tick 0 fix).
        self.settle();
        self.run_arms();
        self.settle();
        self.latch();
        self.settle();
        self.tick += 1;
    }

    // ------------------------------------------------------------ arm
    fn run_arms(&mut self) {
        let mut cmds = Vec::new();
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
        for (ai, addr, data) in cmds {
            match addr {
                0..=10 => self.arms[ai][addr as usize] = data,
                15 => self.arm_exec(ai, data),
                _ => self.fault(format!("arm write to reserved register {}", addr)),
            }
        }
    }

    fn arm_exec(&mut self, ai: usize, code: u8) {
        let r = self.arms[ai];
        let rd16 = |lo: usize| (r[lo] as i32) | ((r[lo + 1] as i32) << 8);
        let (ox, oy) = {
            let p = &self.parts[self.arm_parts[ai] as usize];
            (p.x, p.y)
        };
        let sx = |lo: usize| rd16(lo) as u16 as i16 as i32;
        let (ax, ay) = (ox + sx(0), oy + sx(2));
        let (bx, by) = (ox + sx(4), oy + sx(6));
        let res = match code {
            CMD_NOP => Ok(()),
            CMD_PLACE => match Kind::from_code(r[R_KIND]) {
                None => Err(format!("PLACE with bad KIND {}", r[R_KIND])),
                Some(k) => self.place(k, ax, ay, r[R_ANGLE], r[R_VAL] as u32).map(|_| ()),
            },
            CMD_PROGRAM_ROM => self.program_rom(ax, ay, rd16(4) as u64, r[R_VAL]),
            CMD_TRACK => self.track(r[R_VAL] as u32, (ax, ay), (bx, by)),
            CMD_VIA => self.via(ax, ay),
            c => Err(format!("unknown arm command {}", c)),
        };
        if let Err(msg) = res {
            self.fault(msg);
        }
    }

    // ------------------------------------------------------------ reporting
    pub fn stats(&self) -> Stats {
        let mut s = Stats { tick: self.tick, counts: self.counts, faults: self.faults, events: self.events, ..Default::default() };
        for p in &self.parts {
            match p.kind {
                Kind::Rom => s.rom_bits += 8u64 << p.abits,
                Kind::Ram => s.ram_bits += 8u64 << p.abits,
                _ => {}
            }
        }
        s.rom_written = self.rom_written;
        s.nets = (0..self.parent.len()).filter(|&i| self.parent[i] == i as u32).count() as u64;
        s.copper_cells = vec![0; self.cfg.layers as usize];
        for (&k, _) in &self.copper {
            s.copper_cells[(k >> 32) as usize] += 1;
        }
        let mut bb = (i32::MAX, i32::MAX, i32::MIN, i32::MIN);
        let mut up = |x: i32, y: i32| {
            bb = (bb.0.min(x), bb.1.min(y), bb.2.max(x), bb.3.max(y));
        };
        for p in &self.parts {
            up(p.x, p.y);
            up(p.x + p.w - 1, p.y + p.h - 1);
        }
        for op in &self.log {
            match *op {
                CopperOp::Seg { x0, y0, x1, y1, .. } => {
                    s.segments += 1;
                    up(x0, y0);
                    up(x1, y1);
                }
                CopperOp::Via { x, y } => {
                    s.vias += 1;
                    up(x, y);
                }
            }
        }
        s.track_len = self.track_len;
        s.bbox = if bb.0 == i32::MAX { (0, 0, -1, -1) } else { bb };
        s
    }
}
