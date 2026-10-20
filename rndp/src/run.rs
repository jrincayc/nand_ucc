//! Runner (dump / checkpoint / snapshot / SVG hooks) and the script-driven arm Driver.
//!
//! The Driver places one ARM at (ARM_X, ARM_Y), 13 one-cell SOURCEs, and lays 13 ordinary tracks
//! from the sources to the ARM pads (same TRACK path as any arm; no back door).  The harness block
//! occupies x 8..=13, y 2..=10; put scripted circuits outside it.

use crate::svg;
use crate::world::*;
use std::fs;
use std::path::PathBuf;

pub const ARM_X: i32 = 10;
pub const ARM_Y: i32 = 2;

#[derive(Default, Clone)]
pub struct RunOpts {
    pub out_dir: PathBuf,
    pub dump_on_en: Option<String>,
    pub svg_on_en: bool,
    pub checkpoint: Option<(PathBuf, u64)>,
    pub snapshot: Option<(String, u64)>,
    pub svg_every: u64,
    pub svg_window: Option<(i32, i32, i32, i32)>,
    pub svg_scale: f64,
}

pub struct Runner {
    pub w: World,
    pub o: RunOpts,
    pub notes: Vec<String>,
}

fn write_atomic(path: &PathBuf, text: &str) -> std::io::Result<()> {
    let mut tmp = path.clone().into_os_string();
    tmp.push(".tmp");
    let tmp = PathBuf::from(tmp);
    fs::write(&tmp, text)?;
    fs::rename(&tmp, path)
}

impl Runner {
    pub fn new(w: World, o: RunOpts) -> Runner {
        Runner { w, o, notes: vec![] }
    }
    fn path(&self, name: &str) -> PathBuf {
        self.o.out_dir.join(name)
    }
    pub fn write_svg(&mut self, name: &str) {
        let s = svg::render(&self.w, self.o.svg_window, if self.o.svg_scale > 0.0 { self.o.svg_scale } else { 6.0 });
        let p = self.path(name);
        match fs::write(&p, s) {
            Ok(_) => self.notes.push(format!("wrote {}", p.display())),
            Err(e) => self.notes.push(format!("cannot write {}: {}", p.display(), e)),
        }
    }
    pub fn step(&mut self) {
        self.w.step();
        let t = self.w.tick;
        if self.w.take_en_event() {
            if let Some(pre) = self.o.dump_on_en.clone() {
                let p = self.path(&format!("{}_t{}.state", pre, t));
                match write_atomic(&p, &self.w.save_state()) {
                    Ok(_) => self.notes.push(format!("t{}: EN event, wrote {}", t, p.display())),
                    Err(e) => self.notes.push(format!("cannot write {}: {}", p.display(), e)),
                }
            }
            if self.o.svg_on_en {
                self.write_svg(&format!("en_t{}.svg", t));
            }
        }
        if let Some((f, n)) = self.o.checkpoint.clone() {
            if *&n > 0 && t % n == 0 {
                if let Err(e) = write_atomic(&f, &self.w.save_state()) {
                    self.notes.push(format!("checkpoint failed: {}", e));
                }
            }
        }
        if let Some((pre, n)) = self.o.snapshot.clone() {
            if n > 0 && t % n == 0 {
                let p = self.path(&format!("{}_{:012}.state", pre, t));
                if let Err(e) = write_atomic(&p, &self.w.save_state()) {
                    self.notes.push(format!("snapshot failed: {}", e));
                }
            }
        }
        if self.o.svg_every > 0 && t % self.o.svg_every == 0 {
            self.write_svg(&format!("tick_{:012}.svg", t));
        }
    }
    pub fn run(&mut self, n: u64) {
        for _ in 0..n {
            self.step();
        }
    }
}

pub struct Driver {
    pub arm: u32,
    src: [u32; 13], // ADDR0..3, EN, DATA0..7
    cur: [Option<u8>; 11],
}

impl Driver {
    pub fn install(w: &mut World) -> Result<Driver, String> {
        let arm = w.place(Kind::Arm, ARM_X, ARM_Y, 0, 0)?;
        let mut src = [0u32; 13];
        for i in 0..5 {
            let y = ARM_Y + i as i32;
            src[i] = w.place(Kind::Source, ARM_X - 2, y, 0, 0)?;
            w.track(0, (ARM_X - 2, y), (ARM_X, y))?;
        }
        for j in 0..8 {
            let y = ARM_Y + j as i32;
            src[5 + j] = w.place(Kind::Source, ARM_X + 3, y, 0, 0)?;
            w.track(0, (ARM_X + 3, y), (ARM_X + 1, y))?;
        }
        Ok(Driver { arm, src, cur: [None; 11] })
    }

    fn write(&mut self, r: &mut Runner, addr: u8, data: u8) {
        for i in 0..4 {
            r.w.set_source(self.src[i], (addr >> i) & 1);
        }
        for j in 0..8 {
            r.w.set_source(self.src[5 + j], (data >> j) & 1);
        }
        r.w.set_source(self.src[4], 1);
        r.step();
        r.w.set_source(self.src[4], 0);
    }

    pub fn set_reg(&mut self, r: &mut Runner, reg: usize, v: u8) {
        if self.cur[reg] != Some(v) {
            self.write(r, reg as u8, v);
            self.cur[reg] = Some(v);
        }
    }
    fn set16(&mut self, r: &mut Runner, lo: usize, v: i32) {
        self.set_reg(r, lo, (v & 0xFF) as u8);
        self.set_reg(r, lo + 1, ((v >> 8) & 0xFF) as u8);
    }
    pub fn exec(&mut self, r: &mut Runner, code: u8) {
        self.write(r, 15, code);
    }
    pub fn set_a(&mut self, r: &mut Runner, x: i32, y: i32) {
        self.set16(r, 0, x - ARM_X);
        self.set16(r, 2, y - ARM_Y);
    }
    pub fn set_b(&mut self, r: &mut Runner, x: i32, y: i32) {
        self.set16(r, 4, x - ARM_X);
        self.set16(r, 6, y - ARM_Y);
    }
    pub fn place(&mut self, r: &mut Runner, kind: u8, x: i32, y: i32, rot: u8, abits: u8) {
        self.set_a(r, x, y);
        self.set_reg(r, R_KIND, kind);
        self.set_reg(r, R_ANGLE, rot);
        self.set_reg(r, R_VAL, abits);
        self.exec(r, CMD_PLACE);
    }
    pub fn track(&mut self, r: &mut Runner, l: u8, a: (i32, i32), b: (i32, i32)) {
        self.set_a(r, a.0, a.1);
        self.set_b(r, b.0, b.1);
        self.set_reg(r, R_VAL, l);
        self.exec(r, CMD_TRACK);
    }
    pub fn via(&mut self, r: &mut Runner, x: i32, y: i32) {
        self.set_a(r, x, y);
        self.exec(r, CMD_VIA);
    }
    /// PROGRAM_ROM: the address is B.x taken as an unsigned 16-bit value (arm-relative form is not used).
    pub fn rom(&mut self, r: &mut Runner, x: i32, y: i32, addr: u16, v: u8) {
        self.set_a(r, x, y);
        self.set_reg(r, 4, (addr & 0xFF) as u8);
        self.set_reg(r, 5, (addr >> 8) as u8);
        self.set_reg(r, R_VAL, v);
        self.exec(r, CMD_PROGRAM_ROM);
    }
    pub fn nop(&mut self, r: &mut Runner) {
        self.exec(r, CMD_NOP);
    }
}

/// Run a script.  Lines (# comments):
///   place KIND X Y [ROT] [ABITS]   KIND nand dff rom arm ram or 0..4
///   track L AX AY BX BY | via X Y | rom X Y ADDR VAL | nop [N] | idle [N]
///   source X Y [V]                 harness-only SOURCE placed directly (not through the arm)
pub fn run_script(r: &mut Runner, d: &mut Driver, text: &str) -> Result<(), String> {
    for (n, line) in text.lines().enumerate() {
        let line = line.split('#').next().unwrap().trim();
        if line.is_empty() {
            continue;
        }
        let w: Vec<&str> = line.split_whitespace().collect();
        let num = |i: usize| -> Result<i32, String> {
            w.get(i).ok_or(format!("script line {}: missing argument", n + 1))?.parse::<i32>().map_err(|e| format!("script line {}: {}", n + 1, e))
        };
        let opt = |i: usize, dflt: i32| -> Result<i32, String> { if w.len() > i { num(i) } else { Ok(dflt) } };
        match w[0] {
            "place" => {
                let kind = match w.get(1).copied().unwrap_or("") {
                    "nand" => 0,
                    "dff" => 1,
                    "rom" => 2,
                    "arm" => 3,
                    "ram" => 4,
                    s => s.parse::<u8>().map_err(|_| format!("script line {}: bad kind {}", n + 1, s))?,
                };
                d.place(r, kind, num(2)?, num(3)?, opt(4, 0)? as u8, opt(5, 0)? as u8);
            }
            "track" => d.track(r, num(1)? as u8, (num(2)?, num(3)?), (num(4)?, num(5)?)),
            "via" => d.via(r, num(1)?, num(2)?),
            "rom" => d.rom(r, num(1)?, num(2)?, num(3)? as u16, num(4)? as u8),
            "nop" => {
                for _ in 0..opt(1, 1)? {
                    d.nop(r);
                }
            }
            "idle" => r.run(opt(1, 1)? as u64),
            "source" => {
                let id = r.w.place(Kind::Source, num(1)?, num(2)?, 0, 0).map_err(|e| format!("script line {}: {}", n + 1, e))?;
                r.w.set_source(id, opt(3, 0)? as u8);
            }
            c => return Err(format!("script line {}: unknown command {}", n + 1, c)),
        }
    }
    Ok(())
}

/// Apply build commands directly to the world, without a driver arm and without ticks (seed construction / validation).
/// Same line syntax as `run_script` for place / track / via / rom, absolute coordinates.  Failed commands count as faults.
pub fn run_build(w: &mut World, text: &str) -> Result<(u64, u64), String> {
    let (mut ok, mut bad) = (0u64, 0u64);
    for (n, line) in text.lines().enumerate() {
        let line = line.split('#').next().unwrap().trim();
        if line.is_empty() {
            continue;
        }
        let t: Vec<&str> = line.split_whitespace().collect();
        let num = |i: usize| -> Result<i32, String> {
            t.get(i).ok_or(format!("build line {}: missing argument", n + 1))?.parse::<i32>().map_err(|e| format!("build line {}: {}", n + 1, e))
        };
        let res = match t[0] {
            "place" => {
                let k = Kind::from_code(num(1)? as u8).ok_or(format!("build line {}: bad kind", n + 1))?;
                w.place(k, num(2)?, num(3)?, num(4)? as u8, num(5)? as u32).map(|_| ())
            }
            "track" => w.track(num(1)? as u32, (num(2)?, num(3)?), (num(4)?, num(5)?)),
            "via" => w.via(num(1)?, num(2)?),
            "rom" => w.program_rom(num(1)?, num(2)?, num(3)? as u64, num(4)? as u8),
            c => return Err(format!("build line {}: unknown command {}", n + 1, c)),
        };
        match res {
            Ok(()) => ok += 1,
            Err(e) => {
                bad += 1;
                w.fault(format!("build line {}: {}", n + 1, e));
            }
        }
    }
    Ok((ok, bad))
}
