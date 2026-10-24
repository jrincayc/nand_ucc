//! mrouter -- PathFinder-style negotiated-congestion router, two layers, cost = runs + vias (+ small length), pads pierce both layers.
//! usage: mrouter PROBLEM.txt OUT.txt [--iters N]
//! PROBLEM: "grid x0 y0 w h" / "pad x y net" (net>=0 owner, -2 blocked) / "l0 x y net" / "net id nsinks" + "d x y kind" + "s x y late"*
use std::collections::BinaryHeap;
use std::cmp::Reverse;
use std::io::Write;
const LEN: i64 = 2; const RUN: i64 = 100; const VIA: i64 = 100;
struct Net { id: i32, drv: (i32, i32, i32), sinks: Vec<(i32, i32, i32)> }
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let txt = std::fs::read_to_string(&a[1]).unwrap();
    let mut iters = 60; let mut i = 3; while i < a.len() { if a[i] == "--iters" { iters = a[i + 1].parse().unwrap(); i += 2 } else { panic!("arg") } }
    let (mut gx0, mut gy0, mut w, mut h) = (0i32, 0i32, 0usize, 0usize);
    let mut pads: Vec<(i32, i32, i32)> = vec![]; let mut l0s: Vec<(i32, i32, i32)> = vec![]; let mut nets: Vec<Net> = vec![];
    for line in txt.lines() {
        let t: Vec<&str> = line.split_whitespace().collect(); if t.is_empty() { continue }
        match t[0] {
            "grid" => { gx0 = t[1].parse().unwrap(); gy0 = t[2].parse().unwrap(); w = t[3].parse().unwrap(); h = t[4].parse().unwrap() }
            "pad" => pads.push((t[1].parse().unwrap(), t[2].parse().unwrap(), t[3].parse().unwrap())),
            "l0" => l0s.push((t[1].parse().unwrap(), t[2].parse().unwrap(), t[3].parse().unwrap())),
            "net" => nets.push(Net { id: t[1].parse().unwrap(), drv: (0, 0, 0), sinks: vec![] }),
            "d" => nets.last_mut().unwrap().drv = (t[1].parse().unwrap(), t[2].parse().unwrap(), t[3].parse().unwrap()),
            "s" => nets.last_mut().unwrap().sinks.push((t[1].parse().unwrap(), t[2].parse().unwrap(), t[3].parse().unwrap())),
            _ => panic!("bad line {}", line) }
    }
    let n = w * h;
    let mut pad = vec![-1i32; n]; for &(x, y, nt) in &pads { pad[(y - gy0) as usize * w + (x - gx0) as usize] = nt }
    let mut l0only = vec![-1i32; n]; for &(x, y, nt) in &l0s { l0only[(y - gy0) as usize * w + (x - gx0) as usize] = nt }
    let mut occ = vec![[0i32; 2]; n]; let mut hist = vec![[0i64; 2]; n];
    let nn = nets.len();
    let mut tree_cells: Vec<Vec<(usize, usize)>> = vec![vec![]; nn];          // (cell, layer) used by the net
    let mut routes: Vec<Vec<Option<Vec<String>>>> = nets.iter().map(|n| vec![None; n.sinks.len()]).collect();
    let mut dist = vec![i64::MAX; 6 * n]; let mut par = vec![u32::MAX; 6 * n]; let mut stamp = vec![0u32; 6 * n]; let mut cur_stamp = 0u32;
    let mut pf: f64 = 1.0; let hf: i64 = 80;
    let mut mark = vec![[0u32; 2]; n]; let mut mark_id = 0u32;
    // net order: by total hpwl ascending
    let mut order: Vec<usize> = (0..nn).collect();
    let hp = |nt: &Net| -> i32 { nt.sinks.iter().map(|s| (s.0 - nt.drv.0).abs() + (s.1 - nt.drv.1).abs()).sum() };
    order.sort_by_key(|&k| hp(&nets[k]));
    let mut final_fail = 0;
    for it in 0..iters {
        let mut fails = 0;
        for &k in &order {
            let nt = &nets[k]; let nid = nt.id;
            // rip up
            for &(c, l) in &tree_cells[k] { occ[c][l] -= 1 } tree_cells[k].clear();
            mark_id += 1;
            let mut addcell = |c: usize, l: usize, occ: &mut Vec<[i32; 2]>, tc: &mut Vec<(usize, usize)>, mark: &mut Vec<[u32; 2]>| { if mark[c][l] != mark_id { mark[c][l] = mark_id; occ[c][l] += 1; tc.push((c, l)) } };
            let dcell = (nt.drv.1 - gy0) as usize * w + (nt.drv.0 - gx0) as usize;
            let mut tree: Vec<(usize, usize)> = vec![];
            if nt.drv.2 == 0 { tree.push((dcell, 0)); tree.push((dcell, 1)) } else { tree.push((dcell, 0)) }
            for &(c, l) in &tree { addcell(c, l, &mut occ, &mut tree_cells[k], &mut mark) }
            let mut sidx: Vec<usize> = (0..nt.sinks.len()).collect();
            sidx.sort_by_key(|&s| (nt.sinks[s].2, (nt.sinks[s].0 - nt.drv.0).abs() + (nt.sinks[s].1 - nt.drv.1).abs()));
            for &s in &sidx {
                let (sx, sy, late) = nt.sinks[s]; let goal = (sy - gy0) as usize * w + (sx - gx0) as usize;
                let goal_l0 = l0only[goal] == nid;
                if tree_cells[k].contains(&(goal, 0)) || (!goal_l0 && tree_cells[k].contains(&(goal, 1))) { routes[k][s] = Some(vec![]); continue }
                cur_stamp += 1;
                let mut pq: BinaryHeap<Reverse<(i64, i64, u32)>> = BinaryHeap::new();
                let hh = |c: usize| -> i64 { let x = (c % w) as i64; let y = (c / w) as i64; let gxx = (goal % w) as i64; let gyy = (goal / w) as i64; LEN * ((x - gxx).abs() + (y - gyy).abs()) };
                let sid = |c: usize, l: usize, d: usize| -> usize { ((l * h * w) + c) * 3 + d };
                for &(c, l) in &tree_cells[k] { let s0 = sid(c, l, 0); stamp[s0] = cur_stamp; dist[s0] = 0; par[s0] = u32::MAX; pq.push(Reverse((hh(c), 0, s0 as u32))) }
                let mut found: Option<usize> = None;
                while let Some(Reverse((_f, g, s0))) = pq.pop() {
                    let s0 = s0 as usize; if stamp[s0] != cur_stamp || dist[s0] < g { continue }
                    let d = s0 % 3; let rest = s0 / 3; let l = rest / (h * w); let c = rest % (h * w);
                    if c == goal && (!goal_l0 || l == 0) && !(tree_cells[k].contains(&(c, l)) && g == 0) { found = Some(s0); break }
                    let x = (c % w) as i32; let y = (c / w) as i32;
                    // via
                    let ol = 1 - l;
                    if l0only[c] == -1 || (c == goal && false) {
                        let p = pad[c];
                        if p == -1 || p == nid {
                            let oth = occ[c][ol] - if mark[c][ol] == mark_id { 1 } else { 0 }; let cc = (oth as f64 * pf) as i64 * 40 + hist[c][ol];
                            let ng = g + VIA + cc; let ns = sid(c, ol, 0);
                            if stamp[ns] != cur_stamp || ng < dist[ns] { stamp[ns] = cur_stamp; dist[ns] = ng; par[ns] = s0 as u32; pq.push(Reverse((ng + hh(c), ng, ns as u32))) }
                        }
                    }
                    for &(nd, dx, dy) in &[(1usize, 1i32, 0i32), (1, -1, 0), (2, 0, 1), (2, 0, -1)] {
                        let nx = x + dx; let ny = y + dy; if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 { continue }
                        let nc = ny as usize * w + nx as usize;
                        let p = pad[nc]; if p != -1 && p != nid { continue }
                        if l0only[nc] != -1 && (l0only[nc] != nid || l != 0) { continue }
                        let others = occ[nc][l] - if mark[nc][l] == mark_id { 1 } else { 0 }; let cc = (others as f64 * pf) as i64 * 40 + hist[nc][l];
                        let ng = g + LEN + cc + if d == nd { 0 } else { RUN }; let ns = sid(nc, l, nd);
                        if stamp[ns] != cur_stamp || ng < dist[ns] { stamp[ns] = cur_stamp; dist[ns] = ng; par[ns] = s0 as u32; pq.push(Reverse((ng + hh(nc), ng, ns as u32))) }
                    }
                }
                match found {
                    None => { fails += 1; routes[k][s] = None }
                    Some(mut s0) => {
                        let mut path: Vec<(i32, i32, usize)> = vec![];
                        loop { let d = s0 % 3; let _ = d; let rest = s0 / 3; let l = rest / (h * w); let c = rest % (h * w); path.push(((c % w) as i32 + gx0, (c / w) as i32 + gy0, l)); let p = par[s0]; if p == u32::MAX { break } s0 = p as usize }
                        path.reverse();
                        // runs
                        let mut cmds: Vec<String> = vec![]; let mut cur: Option<(usize, i32, i32, i32, i32)> = None;
                        let lt = late;
                        for q in 1..path.len() {
                            let (ax, ay, al) = path[q - 1]; let (bx, by, bl) = path[q];
                            if al != bl { if let Some(r) = cur.take() { cmds.push(format!("T {} {} {} {} {} {}", lt, r.0, r.1, r.2, r.3, r.4)) } cmds.push(format!("V {} {} {}", lt, ax, ay)); continue }
                            match cur {
                                Some(r) if r.0 == bl && (ax, ay) == (r.3, r.4) && ((r.1 == r.3 && r.3 == bx && bx == ax) || (r.2 == r.4 && r.4 == by && by == ay)) => { cur = Some((r.0, r.1, r.2, bx, by)) }
                                _ => { if let Some(r) = cur.take() { cmds.push(format!("T {} {} {} {} {} {}", lt, r.0, r.1, r.2, r.3, r.4)) } cur = Some((bl, ax, ay, bx, by)) }
                            }
                        }
                        if let Some(r) = cur.take() { cmds.push(format!("T {} {} {} {} {} {}", lt, r.0, r.1, r.2, r.3, r.4)) }
                        routes[k][s] = Some(cmds);
                        for q in 0..path.len() {
                            let (px, py, pl) = path[q]; let c = (py - gy0) as usize * w + (px - gx0) as usize;
                            addcell(c, pl, &mut occ, &mut tree_cells[k], &mut mark);
                            if q > 0 && path[q - 1].2 != pl { addcell(c, 1 - pl, &mut occ, &mut tree_cells[k], &mut mark) }
                            if q + 1 < path.len() && path[q + 1].2 != pl { addcell(c, 1 - pl, &mut occ, &mut tree_cells[k], &mut mark) }
                        }
                    }
                }
            }
        }
        let mut over = 0; for c in 0..n { for l in 0..2 { if occ[c][l] > 1 { over += 1; hist[c][l] += hf } } }
        eprintln!("iter {} fails {} overused cells {} pf {:.2}", it, fails, over, pf);
        final_fail = fails;
        if fails == 0 && over == 0 { break }
        pf = (pf * 1.25).min(40.0);
    }
    let mut out = std::io::BufWriter::new(std::fs::File::create(&a[2]).unwrap());
    for (k, nt) in nets.iter().enumerate() { for (s, r) in routes[k].iter().enumerate() { match r { Some(c) => { for l in c { writeln!(out, "{} {} {}", nt.id, s, l).unwrap() } writeln!(out, "{} {} END", nt.id, s).unwrap() } None => writeln!(out, "{} {} FAIL", nt.id, s).unwrap() } } }
    eprintln!("final fails {}", final_fail);
    { let mut f = std::fs::File::create("/tmp/over.txt").unwrap(); for c in 0..n { for l in 0..2 { if occ[c][l] > 1 { writeln!(f, "{} {} {} {}", (c % w) as i32 + gx0, (c / w) as i32 + gy0, l, occ[c][l]).unwrap() } } } }
    let mut shown = 0;
    for c in 0..n { for l in 0..2 { if occ[c][l] > 1 && shown < 25 {
        let who: Vec<i32> = (0..nn).filter(|&k| tree_cells[k].contains(&(c, l))).map(|k| nets[k].id).collect();
        eprintln!("over cell ({},{}) L{} nets {:?} pad {} l0 {}", (c % w) as i32 + gx0, (c / w) as i32 + gy0, l, who, pad[c], l0only[c]); shown += 1 } } }
}
