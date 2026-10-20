//! SVG snapshot: parts as boxes, copper per layer in distinct colours, vias as circles.
use crate::world::{CopperOp, Kind, Pin, World};
use std::fmt::Write;

const LAYER_COL: [&str; 8] = ["#d33", "#26c", "#2a2", "#c80", "#a3a", "#0aa", "#888", "#640"];

/// window = (x0, y0, x1, y1) with x1, y1 exclusive; None = bounding box of everything.
pub fn render(w: &World, window: Option<(i32, i32, i32, i32)>, scale: f64) -> String {
    let st = w.stats();
    let (x0, y0, x1, y1) = window.unwrap_or((st.bbox.0 - 1, st.bbox.1 - 1, st.bbox.2 + 2, st.bbox.3 + 2));
    let (pw, ph) = ((x1 - x0).max(1) as f64 * scale, (y1 - y0).max(1) as f64 * scale);
    let mut s = String::new();
    let _ = writeln!(s, "<svg xmlns='http://www.w3.org/2000/svg' width='{:.0}' height='{:.0}' viewBox='0 0 {:.0} {:.0}'>", pw, ph, pw, ph);
    let _ = writeln!(s, "<rect width='100%' height='100%' fill='#fff'/>");
    let cx = |x: i32| (x - x0) as f64 * scale + scale / 2.0;
    let cy = |y: i32| (y - y0) as f64 * scale + scale / 2.0;
    for p in &w.parts {
        if p.x + p.w <= x0 || p.x >= x1 || p.y + p.h <= y0 || p.y >= y1 {
            continue;
        }
        let col = match p.kind {
            Kind::Nand => "#cde",
            Kind::Dff => "#dec",
            Kind::Rom => "#edc",
            Kind::Ram => "#ecd",
            Kind::Arm => "#fd8",
            Kind::Source => "#ddd",
        };
        let _ = writeln!(
            s,
            "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='{}' stroke='#667' stroke-width='0.5'/>",
            (p.x - x0) as f64 * scale, (p.y - y0) as f64 * scale, p.w as f64 * scale, p.h as f64 * scale, col
        );
    }
    let sw = (scale * 0.5).max(0.8);
    for op in &w.log {
        match *op {
            CopperOp::Seg { l, x0: ax, y0: ay, x1: bx, y1: by } => {
                let _ = writeln!(
                    s,
                    "<line x1='{:.1}' y1='{:.1}' x2='{:.1}' y2='{:.1}' stroke='{}' stroke-width='{:.1}' stroke-linecap='square' opacity='0.8'/>",
                    cx(ax), cy(ay), cx(bx), cy(by), LAYER_COL[(l % 8) as usize], sw
                );
            }
            CopperOp::Via { x, y } => {
                let _ = writeln!(s, "<circle cx='{:.1}' cy='{:.1}' r='{:.1}' fill='#fff' stroke='#000' stroke-width='0.8'/>", cx(x), cy(y), scale * 0.35);
            }
        }
    }
    for (i, p) in w.parts.iter().enumerate() {
        let kinds = [Pin::In(0), Pin::Out(0)];
        let _ = kinds;
        let mut pins = Vec::new();
        for k in 0..64u8 {
            if let Some(pt) = w.pin_site(i as u32, Pin::In(k)) {
                pins.push(pt);
            }
            if k < 8 {
                if let Some(pt) = w.pin_site(i as u32, Pin::Out(k)) {
                    pins.push(pt);
                }
            }
        }
        let _ = p;
        for (x, y) in pins {
            let _ = writeln!(s, "<circle cx='{:.1}' cy='{:.1}' r='{:.1}' fill='#222'/>", cx(x), cy(y), (scale * 0.2).max(0.6));
        }
    }
    s.push_str("</svg>\n");
    s
}
