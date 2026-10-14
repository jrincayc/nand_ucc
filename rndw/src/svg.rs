//! SVG snapshots of the world.
//!
//! Detail mode draws every part, pin and wire.  When parts + wires exceed `max_elements`, coarse
//! mode merges the area into square blocks (one rectangle per block, colored by the dominant part
//! kind, opacity = occupancy) and omits individual wires.  A `window` restricts either mode to a
//! region of the grid, so a region of a huge world can be drawn in full detail.

use crate::world::{oriented_layout, FxMap, Kind, World};
use std::fmt::Write;
use std::path::PathBuf;

#[derive(Clone, Debug)]
pub struct SvgOpts {
    pub max_elements: usize,
    /// (x0, y0, x1, y1), x1 and y1 exclusive.
    pub window: Option<(i32, i32, i32, i32)>,
    /// Pixels per grid cell.
    pub scale: f64,
    /// Color pins and wires carrying 1.
    pub signals: bool,
}

impl Default for SvgOpts {
    fn default() -> Self {
        SvgOpts { max_elements: 50_000, window: None, scale: 6.0, signals: true }
    }
}

fn class(k: Kind) -> &'static str {
    match k {
        Kind::Nand => "n",
        Kind::Dff => "d",
        Kind::Rom => "r",
        Kind::Arm => "a",
        Kind::Source => "s",
    }
}

fn bbox(w: &World) -> (i32, i32, i32, i32) {
    if w.parts.is_empty() {
        return (0, 0, 1, 1);
    }
    let mut b = (i32::MAX, i32::MAX, i32::MIN, i32::MIN);
    for p in &w.parts {
        b.0 = b.0.min(p.x);
        b.1 = b.1.min(p.y);
        b.2 = b.2.max(p.x + p.w);
        b.3 = b.3.max(p.y + p.h);
    }
    (b.0 - 1, b.1 - 1, b.2 + 1, b.3 + 1)
}

pub fn render(w: &World, o: &SvgOpts) -> String {
    let (x0, y0, x1, y1) = o.window.unwrap_or_else(|| bbox(w));
    let (bw, bh) = ((x1 - x0).max(1), (y1 - y0).max(1));
    let parts_in: Vec<usize> = (0..w.parts.len())
        .filter(|&i| {
            let p = &w.parts[i];
            p.x < x1 && p.x + p.w > x0 && p.y < y1 && p.y + p.h > y0
        })
        .collect();
    let inside = |x: i32, y: i32| x >= x0 && x < x1 && y >= y0 && y < y1;
    let wires_in = w
        .wires
        .iter()
        .filter(|t| inside(t.0, t.1) || inside(t.2, t.3))
        .count();
    let detail = parts_in.len() + wires_in <= o.max_elements;
    let st = w.stats();
    let mut s = String::new();
    let px_w = (bw as f64 * o.scale).clamp(64.0, 16000.0);
    let px_h = px_w * bh as f64 / bw as f64;
    let _ = writeln!(
        s,
        "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"{} {} {} {}\" width=\"{:.0}\" height=\"{:.0}\">",
        x0, y0, bw, bh, px_w, px_h
    );
    let _ = writeln!(
        s,
        "<!-- rndw tick={} parts={} wires={} faults={} mode={} window=({},{},{},{}) shown_parts={} shown_wires={} -->",
        st.tick, w.parts.len(), w.wires.len(), st.faults,
        if detail { "detail" } else { "coarse" }, x0, y0, x1, y1, parts_in.len(), wires_in
    );
    s.push_str("<style>.n{fill:#8ab4f8}.d{fill:#81c995}.r{fill:#fdd663}.a{fill:#f28b82}.s{fill:#bdc1c6}.p{fill:#202124}.h{fill:#d93025}.w{stroke:#80868b;stroke-width:.08;fill:none}.wh{stroke:#d93025;stroke-width:.12;fill:none}</style>\n");
    let _ = writeln!(s, "<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" fill=\"#fff\"/>", x0, y0, bw, bh);
    if detail {
        for &i in &parts_in {
            let p = &w.parts[i];
            let _ = writeln!(
                s,
                "<rect class=\"{}\" x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" rx=\".15\"/>",
                class(p.kind), p.x, p.y, p.w, p.h
            );
        }
        let (mut lo, mut hi) = (String::new(), String::new());
        for t in &w.wires {
            if !(inside(t.0, t.1) || inside(t.2, t.3)) {
                continue;
            }
            let high = o.signals && w.signal_at_site(t.0, t.1) == Some(1);
            let d = if high { &mut hi } else { &mut lo };
            let _ = write!(d, "M{:.1} {:.1}L{:.1} {:.1}", t.0 as f64 + 0.5, t.1 as f64 + 0.5, t.2 as f64 + 0.5, t.3 as f64 + 0.5);
        }
        if !lo.is_empty() {
            let _ = writeln!(s, "<path class=\"w\" d=\"{}\"/>", lo);
        }
        if !hi.is_empty() {
            let _ = writeln!(s, "<path class=\"wh\" d=\"{}\"/>", hi);
        }
        for &i in &parts_in {
            let p = &w.parts[i];
            let (_, _, pins) = oriented_layout(p.kind, p.rot, w.cfg.rom_abits);
            for (dx, dy, pin) in pins {
                let high = o.signals && w.pin_value(i as u32, pin) == 1;
                let _ = writeln!(
                    s,
                    "<circle class=\"{}\" cx=\"{:.1}\" cy=\"{:.1}\" r=\".14\"/>",
                    if high { "h" } else { "p" },
                    (p.x + dx) as f64 + 0.5,
                    (p.y + dy) as f64 + 0.5
                );
            }
        }
    } else {
        // Coarse: block size so that block count <= max_elements.
        let block = (((bw as f64 * bh as f64) / o.max_elements.max(1) as f64).sqrt().ceil() as i32).max(2);
        let mut acc: FxMap<(i32, i32), ([u64; 5], u64)> = FxMap::default();
        // FxMap needs a hashable key; tuples hash through write_u32 / write.
        for &i in &parts_in {
            let p = &w.parts[i];
            let key = ((p.x - x0).div_euclid(block), (p.y - y0).div_euclid(block));
            let e = acc.entry(key).or_insert(([0; 5], 0));
            let area = (p.w * p.h) as u64;
            e.0[p.kind.code() as usize] += area;
            e.1 += area;
        }
        let mut keys: Vec<_> = acc.keys().copied().collect();
        keys.sort();
        for k in keys {
            let (by_kind, total) = acc[&k];
            let dom = (0..5).max_by_key(|&c| by_kind[c]).unwrap();
            let kind = Kind::from_code_any(dom as u8).unwrap();
            let op = (total as f64 / (block as f64 * block as f64)).clamp(0.15, 1.0);
            let _ = writeln!(
                s,
                "<rect class=\"{}\" x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" fill-opacity=\"{:.2}\"/>",
                class(kind), x0 + k.0 * block, y0 + k.1 * block, block, block, op
            );
        }
    }
    s.push_str("</svg>\n");
    s
}

/// When to write snapshots automatically.
#[derive(Clone, Debug)]
pub struct SvgPolicy {
    pub dir: PathBuf,
    pub on_en: bool,
    /// Every N ticks; 0 disables.
    pub every: u64,
    pub opts: SvgOpts,
}

impl SvgPolicy {
    pub fn write(&self, w: &World, reason: &str) -> std::io::Result<PathBuf> {
        std::fs::create_dir_all(&self.dir)?;
        let path = self.dir.join(format!("world_t{}_{}.svg", w.tick, reason));
        std::fs::write(&path, render(w, &self.opts))?;
        Ok(path)
    }

    /// Call after every tick.  Always clears the EN-wire flag.
    pub fn after_step(&self, w: &mut World) -> Vec<PathBuf> {
        let mut out = Vec::new();
        let en = w.take_en_wire_event();
        if self.on_en && en {
            if let Ok(p) = self.write(w, "en_wire") {
                out.push(p);
            }
        }
        if self.every > 0 && w.tick % self.every == 0 {
            if let Ok(p) = self.write(w, "periodic") {
                out.push(p);
            }
        }
        out
    }
}
