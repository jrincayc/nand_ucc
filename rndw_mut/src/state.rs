//! Whole-world save / load (local copy of nandgen/rndw/src/state.rs, unchanged).
//!
//!   rndw-state 1
//!   cfg <width> <height> <rom_abits> <event_limit>
//!   tick <n>
//!   faults <n>
//!   part <id> <kind code> <x> <y> <rot>       (ids must be 0,1,2,... in order)
//!   rom <part id> <addr> <value>              (nonzero cells only)
//!   wire <out_x> <out_y> <in_x> <in_y>
//!   dff <part id> <0|1>                       (only DFFs holding 1)
//!   src <part id> <0|1>                       (only Sources holding 1)
//!   arm <part id> <16 register values>

use crate::world::{Config, Kind, World, ARM_REGS};
use std::fmt::Write;

impl World {
    pub fn save_state(&self) -> String {
        let mut s = String::new();
        let _ = writeln!(s, "rndw-state 1");
        let _ = writeln!(
            s,
            "cfg {} {} {} {}",
            self.cfg.width, self.cfg.height, self.cfg.rom_abits, self.cfg.event_limit
        );
        let _ = writeln!(s, "tick {}", self.tick);
        let _ = writeln!(s, "faults {}", self.faults);
        for (i, p) in self.parts.iter().enumerate() {
            let _ = writeln!(s, "part {} {} {} {} {}", i, p.kind.code(), p.x, p.y, p.rot);
        }
        for (i, p) in self.parts.iter().enumerate() {
            match p.kind {
                Kind::Rom => {
                    for (addr, &v) in self.roms[p.aux as usize].iter().enumerate() {
                        if v != 0 {
                            let _ = writeln!(s, "rom {} {} {}", i, addr, v);
                        }
                    }
                }
                Kind::Dff => {
                    if self.out_value(i as u32, 0) == 1 {
                        let _ = writeln!(s, "dff {} 1", i);
                    }
                }
                Kind::Source => {
                    if self.out_value(i as u32, 0) == 1 {
                        let _ = writeln!(s, "src {} 1", i);
                    }
                }
                Kind::Arm => {
                    let r = &self.arms[p.aux as usize];
                    let regs: Vec<String> = r.iter().map(|v| v.to_string()).collect();
                    let _ = writeln!(s, "arm {} {}", i, regs.join(" "));
                }
                Kind::Nand => {}
            }
        }
        for &(ox, oy, ix, iy) in &self.wires {
            let _ = writeln!(s, "wire {} {} {} {}", ox, oy, ix, iy);
        }
        s
    }

    pub fn load_state(text: &str) -> Result<World, String> {
        let mut lines: Vec<(usize, Vec<&str>)> = Vec::new();
        for (i, l) in text.lines().enumerate() {
            let l = l.trim();
            if l.is_empty() || l.starts_with('#') {
                continue;
            }
            lines.push((i + 1, l.split_whitespace().collect()));
        }
        match lines.first() {
            Some((_, t)) if t.len() == 2 && t[0] == "rndw-state" && t[1] == "1" => {}
            _ => return Err("not an rndw-state 1 file".into()),
        }
        fn num<T: std::str::FromStr>(t: &[&str], i: usize, ln: usize) -> Result<T, String> {
            t.get(i)
                .and_then(|s| s.parse::<T>().ok())
                .ok_or_else(|| format!("line {}: missing or bad field {}", ln, i))
        }
        let mut cfg = Config::default();
        for (ln, t) in &lines {
            if t[0] == "cfg" {
                cfg = Config {
                    width: num(t, 1, *ln)?,
                    height: num(t, 2, *ln)?,
                    rom_abits: num(t, 3, *ln)?,
                    event_limit: num(t, 4, *ln)?,
                };
            }
        }
        cfg.validate()?;
        let mut w = World::new(cfg);
        let mut tick = 0u64;
        let mut faults = 0u64;
        for (ln, t) in &lines {
            match t[0] {
                "part" => {
                    let id: usize = num(t, 1, *ln)?;
                    if id != w.parts.len() {
                        return Err(format!("line {}: part ids must be consecutive from 0", ln));
                    }
                    let code: u8 = num(t, 2, *ln)?;
                    let kind = Kind::from_code_any(code).ok_or_else(|| format!("line {}: bad kind {}", ln, code))?;
                    w.place(kind, num(t, 3, *ln)?, num(t, 4, *ln)?, num(t, 5, *ln)?)
                        .map_err(|e| format!("line {}: {}", ln, e))?;
                }
                "tick" => tick = num(t, 1, *ln)?,
                "faults" => faults = num(t, 1, *ln)?,
                _ => {}
            }
        }
        for (ln, t) in &lines {
            match t[0] {
                "rom" => {
                    let (p, a, v): (u32, usize, u8) = (num(t, 1, *ln)?, num(t, 2, *ln)?, num(t, 3, *ln)?);
                    w.rom_poke(p, a, v).map_err(|e| format!("line {}: {}", ln, e))?;
                }
                "wire" => {
                    let (ox, oy, ix, iy): (i32, i32, i32, i32) =
                        (num(t, 1, *ln)?, num(t, 2, *ln)?, num(t, 3, *ln)?, num(t, 4, *ln)?);
                    w.connect((ox, oy), (ix, iy)).map_err(|e| format!("line {}: {}", ln, e))?;
                }
                _ => {}
            }
        }
        for (ln, t) in &lines {
            match t[0] {
                "dff" | "src" => {
                    let (p, v): (u32, u8) = (num(t, 1, *ln)?, num(t, 2, *ln)?);
                    if p as usize >= w.parts.len() {
                        return Err(format!("line {}: bad part id", ln));
                    }
                    if t[0] == "dff" {
                        w.set_dff(p, v);
                    } else {
                        w.set_source(p, v);
                    }
                }
                "arm" => {
                    let p: usize = num(t, 1, *ln)?;
                    let part = w.parts.get(p).ok_or_else(|| format!("line {}: bad part id", ln))?;
                    if part.kind != Kind::Arm {
                        return Err(format!("line {}: part {} is not an ARM", ln, p));
                    }
                    let ai = part.aux as usize;
                    for r in 0..ARM_REGS {
                        w.arms[ai][r] = num(t, 2 + r, *ln)?;
                    }
                }
                _ => {}
            }
        }
        w.settle();
        w.tick = tick;
        w.faults = faults;
        w.take_en_wire_event();
        w.en_wire_events = 0;
        Ok(w)
    }
}
