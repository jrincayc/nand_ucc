//! Whole-world save / load (`rndp-state 1`).  Copper is stored as segments and vias in laying
//! order; the loader rebuilds the cell map and the connectivity cache.
//!
//!   rndp-state 1
//!   cfg <W> <H> <layers> <rom_on> <ram_on> <max_rom_bits> <max_ram_bits> <event_limit>
//!   tick <n> / faults <n> / romwritten <n>
//!   part <id> <kind code> <x> <y> <rot> <abits>      (ids 0,1,2,... in order)
//!   seg <layer> <x0> <y0> <x1> <y1>
//!   via <x> <y>
//!   mem <part id> <addr> <value>                     (nonzero ROM / RAM cells only)
//!   dff <part id> 1 / src <part id> 1
//!   arm <part id> <16 register values>
//! Lines starting with '#' are comments.  Parts first, then copper, then everything else.

use crate::world::{Config, CopperOp, Kind, World, ARM_REGS};
use std::fmt::Write;

impl World {
    pub fn save_state(&self) -> String {
        let c = &self.cfg;
        let mut s = String::new();
        let _ = writeln!(s, "rndp-state 1");
        let _ = writeln!(
            s,
            "cfg {} {} {} {} {} {} {} {}",
            c.width, c.height, c.layers, c.rom_on as u8, c.ram_on as u8, c.max_rom_bits, c.max_ram_bits, c.event_limit
        );
        let _ = writeln!(s, "tick {}\nfaults {}\nromwritten {}", self.tick, self.faults, self.rom_written);
        for (i, p) in self.parts.iter().enumerate() {
            let _ = writeln!(s, "part {} {} {} {} {} {}", i, p.kind.code(), p.x, p.y, p.rot, p.abits);
        }
        for op in &self.log {
            match *op {
                CopperOp::Seg { l, x0, y0, x1, y1 } => {
                    let _ = writeln!(s, "seg {} {} {} {} {}", l, x0, y0, x1, y1);
                }
                CopperOp::Via { x, y } => {
                    let _ = writeln!(s, "via {} {}", x, y);
                }
            }
        }
        for (i, p) in self.parts.iter().enumerate() {
            match p.kind {
                Kind::Rom | Kind::Ram => {
                    for (a, v) in self.mems[p.aux as usize].nonzero() {
                        let _ = writeln!(s, "mem {} {} {}", i, a, v);
                    }
                }
                Kind::Dff | Kind::Source => {
                    if self.out_value(i as u32, 0) == 1 {
                        let _ = writeln!(s, "{} {} 1", if p.kind == Kind::Dff { "dff" } else { "src" }, i);
                    }
                }
                Kind::Arm => {
                    let r: Vec<String> = self.arms[p.aux as usize].iter().map(|v| v.to_string()).collect();
                    let _ = writeln!(s, "arm {} {}", i, r.join(" "));
                }
                Kind::Nand => {}
            }
        }
        s
    }

    pub fn load_state(text: &str) -> Result<World, String> {
        let mut lines = text.lines().enumerate().filter(|(_, l)| !l.trim().is_empty() && !l.trim_start().starts_with('#'));
        match lines.next() {
            Some((_, l)) if l.trim() == "rndp-state 1" => {}
            _ => return Err("not an rndp-state 1 file".into()),
        }
        let recs: Vec<(usize, Vec<&str>)> = lines.map(|(n, l)| (n + 1, l.split_whitespace().collect())).collect();
        let num = |n: usize, w: &Vec<&str>, i: usize| -> Result<i64, String> {
            w.get(i).ok_or(format!("line {}: missing field", n))?.parse::<i64>().map_err(|e| format!("line {}: {}", n, e))
        };
        let mut cfg = Config::default();
        let (mut tick, mut faults, mut written) = (0u64, 0u64, 0u64);
        for (n, w) in &recs {
            match w[0] {
                "cfg" => {
                    cfg = Config {
                        width: num(*n, w, 1)? as u32,
                        height: num(*n, w, 2)? as u32,
                        layers: num(*n, w, 3)? as u32,
                        rom_on: num(*n, w, 4)? != 0,
                        ram_on: num(*n, w, 5)? != 0,
                        max_rom_bits: num(*n, w, 6)? as u32,
                        max_ram_bits: num(*n, w, 7)? as u32,
                        event_limit: num(*n, w, 8)? as u64,
                    }
                }
                "tick" => tick = num(*n, w, 1)? as u64,
                "faults" => faults = num(*n, w, 1)? as u64,
                "romwritten" => written = num(*n, w, 1)? as u64,
                _ => {}
            }
        }
        cfg.validate()?;
        let mut world = World::new(cfg);
        for (n, w) in &recs {
            if w[0] == "part" {
                if num(*n, w, 1)? as usize != world.parts.len() {
                    return Err(format!("line {}: part ids must be consecutive", n));
                }
                let k = Kind::from_code_any(num(*n, w, 2)? as u8).ok_or(format!("line {}: bad kind", n))?;
                world
                    .place(k, num(*n, w, 3)? as i32, num(*n, w, 4)? as i32, num(*n, w, 5)? as u8, num(*n, w, 6)? as u32)
                    .map_err(|e| format!("line {}: {}", n, e))?;
            }
        }
        for (n, w) in &recs {
            match w[0] {
                "seg" => world
                    .track(
                        num(*n, w, 1)? as u32,
                        (num(*n, w, 2)? as i32, num(*n, w, 3)? as i32),
                        (num(*n, w, 4)? as i32, num(*n, w, 5)? as i32),
                    )
                    .map_err(|e| format!("line {}: {}", n, e))?,
                "via" => world.via(num(*n, w, 1)? as i32, num(*n, w, 2)? as i32).map_err(|e| format!("line {}: {}", n, e))?,
                _ => {}
            }
        }
        for (n, w) in &recs {
            match w[0] {
                "mem" => world
                    .mem_poke(num(*n, w, 1)? as u32, num(*n, w, 2)? as u64, num(*n, w, 3)? as u8)
                    .map_err(|e| format!("line {}: {}", n, e))?,
                "dff" => world.set_dff(num(*n, w, 1)? as u32, num(*n, w, 2)? as u8),
                "src" => world.set_source(num(*n, w, 1)? as u32, num(*n, w, 2)? as u8),
                "arm" => {
                    let id = num(*n, w, 1)? as usize;
                    let p = world.parts.get(id).ok_or(format!("line {}: bad part", n))?;
                    if p.kind != Kind::Arm {
                        return Err(format!("line {}: part {} is not an ARM", n, id));
                    }
                    let aux = p.aux as usize;
                    for i in 0..ARM_REGS {
                        world.arms[aux][i] = num(*n, w, 2 + i)? as u8;
                    }
                }
                _ => {}
            }
        }
        world.settle();
        world.tick = tick;
        world.faults = faults;
        world.rom_written = written;
        world.take_en_event();
        world.en_events = 0;
        Ok(world)
    }
}
