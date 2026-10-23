//! rndp command line.  Standard library only.
use rndp::netlist::{run_vectors, Netlist};
use rndp::run::*;
use rndp::world::*;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const HELP: &str = "\
rndp - RNDP world simulator (Robot + NAND + DFF + PCB, optional ROM and RAM)   spec: nandgen/RNDP_SPEC.md v0.3

USAGE: rndp [OPTIONS]

World source (default: an empty world):
  --world FILE             load a saved state (rndp-state 1); its cfg line overrides the parameters below
  --netlist FILE           import a nandgen netlist (inputs become SOURCEs) on a diagonal test layout, 2+ layers
  --vectors FILE           with --netlist: replay a rndw-vectors trace against the Python reference; exit 1 on mismatch
  --build FILE             apply build commands directly (absolute coordinates; place/track/via/rom), no arm, no ticks
  --script FILE            build things through a driven arm, one register write per tick.  Harness block
                           x 8..13, y 2..10 is reserved.  Lines: place KIND X Y [ROT] [ABITS] | track L AX AY BX BY |
                           via X Y | rom X Y ADDR VAL | nop [N] | idle [N] | source X Y [V]

World parameters:
  --width N --height N     grid size, at most 65536 (default 65536 x 65536)
  --layers L               copper layers 1..8 (default 2)
  --rom on|off  --ram on|off   enable the optional parts (default on)
  --max-rom-addr-bits N  --max-ram-addr-bits N   1..32 (default 16)
  --event-limit N          settle events per phase before a convergence fault (default 5000000)

Running:
  --steps N                ticks to run after the script (default 0 with a script, else 1000)

Output:
  --out-dir DIR            directory for dumps (default .)
  --save FILE              write the final state
  --dump-on-en PREFIX      write PREFIX_t<tick>.state when a merge joins an ARM's EN pad to anything
  --checkpoint FILE --checkpoint-every N    rewrite FILE every N ticks (temp file + rename)
  --snapshot-prefix P --snapshot-every M    write a new numbered state file every M ticks
  --svg-at-end FILE | --svg-on-en | --svg-every N   SVG snapshots (--svg-window X0,Y0,X1,Y1  --svg-scale F)
  --cmd-log FILE           append one line per executed arm command (tick, arm, command, absolute A/B, registers, ok/FAULT) to FILE
  --dump-pads FILE         write one line per part pin: part kind pin x y net-id (for cross-checks)
  --report                 print the report at the end (default on)
  -h, --help
";

fn val<'a>(a: &'a [String], i: &mut usize) -> Result<&'a str, String> {
    *i += 1;
    a.get(*i).map(|s| s.as_str()).ok_or_else(|| format!("{} needs a value", a[*i - 1]))
}
fn onoff(s: &str) -> Result<bool, String> {
    match s {
        "on" | "1" | "true" => Ok(true),
        "off" | "0" | "false" => Ok(false),
        _ => Err(format!("expected on|off, got {}", s)),
    }
}

fn real_main() -> Result<i32, String> {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let mut cfg = Config::default();
    let (mut world_f, mut script_f, mut save_f, mut svg_end): (Option<String>, Option<String>, Option<String>, Option<String>) = (None, None, None, None);
    let mut pads_f: Option<String> = None;
    let mut build_f: Option<String> = None;
    let (mut netlist_f, mut vectors_f): (Option<String>, Option<String>) = (None, None);
    let mut steps: Option<u64> = None;
    let mut o = RunOpts { out_dir: PathBuf::from("."), ..Default::default() };
    let (mut ck, mut ck_n, mut sp, mut sp_n) = (None::<String>, 0u64, None::<String>, 0u64);
    let mut i = 0;
    let pn = |s: &str| s.parse::<u64>().map_err(|e| format!("{}: {}", s, e));
    while i < a.len() {
        match a[i].as_str() {
            "-h" | "--help" => {
                print!("{}", HELP);
                return Ok(0);
            }
            "--world" => world_f = Some(val(&a, &mut i)?.to_string()),
            "--netlist" => netlist_f = Some(val(&a, &mut i)?.to_string()),
            "--vectors" => vectors_f = Some(val(&a, &mut i)?.to_string()),
            "--build" => build_f = Some(val(&a, &mut i)?.to_string()),
            "--script" => script_f = Some(val(&a, &mut i)?.to_string()),
            "--width" => cfg.width = pn(val(&a, &mut i)?)? as u32,
            "--height" => cfg.height = pn(val(&a, &mut i)?)? as u32,
            "--layers" => cfg.layers = pn(val(&a, &mut i)?)? as u32,
            "--rom" => cfg.rom_on = onoff(val(&a, &mut i)?)?,
            "--ram" => cfg.ram_on = onoff(val(&a, &mut i)?)?,
            "--max-rom-addr-bits" => cfg.max_rom_bits = pn(val(&a, &mut i)?)? as u32,
            "--max-ram-addr-bits" => cfg.max_ram_bits = pn(val(&a, &mut i)?)? as u32,
            "--event-limit" => cfg.event_limit = pn(val(&a, &mut i)?)?,
            "--steps" => steps = Some(pn(val(&a, &mut i)?)?),
            "--out-dir" => o.out_dir = PathBuf::from(val(&a, &mut i)?),
            "--save" => save_f = Some(val(&a, &mut i)?.to_string()),
            "--dump-on-en" => o.dump_on_en = Some(val(&a, &mut i)?.to_string()),
            "--checkpoint" => ck = Some(val(&a, &mut i)?.to_string()),
            "--checkpoint-every" => ck_n = pn(val(&a, &mut i)?)?,
            "--snapshot-prefix" => sp = Some(val(&a, &mut i)?.to_string()),
            "--snapshot-every" => sp_n = pn(val(&a, &mut i)?)?,
            "--svg-at-end" => svg_end = Some(val(&a, &mut i)?.to_string()),
            "--svg-on-en" => o.svg_on_en = true,
            "--svg-every" => o.svg_every = pn(val(&a, &mut i)?)?,
            "--svg-scale" => o.svg_scale = val(&a, &mut i)?.parse::<f64>().map_err(|e| e.to_string())?,
            "--svg-window" => {
                let v: Vec<i32> = val(&a, &mut i)?.split(',').map(|s| s.parse::<i32>().unwrap_or(0)).collect();
                if v.len() != 4 {
                    return Err("--svg-window needs X0,Y0,X1,Y1".into());
                }
                o.svg_window = Some((v[0], v[1], v[2], v[3]));
            }
            "--cmd-log" => o.cmd_log = Some(val(&a, &mut i)?.to_string()),
            "--dump-pads" => pads_f = Some(val(&a, &mut i)?.to_string()),
            "--report" => {}
            s => return Err(format!("unknown option {} (try --help)", s)),
        }
        i += 1;
    }
    if let Some(f) = ck {
        if ck_n == 0 {
            return Err("--checkpoint needs --checkpoint-every N".into());
        }
        o.checkpoint = Some((PathBuf::from(f), ck_n));
    }
    if let Some(p) = sp {
        if sp_n == 0 {
            return Err("--snapshot-prefix needs --snapshot-every M".into());
        }
        o.snapshot = Some((p, sp_n));
    }
    let world = match &world_f {
        Some(f) => World::load_state(&fs::read_to_string(f).map_err(|e| format!("{}: {}", f, e))?)?,
        None => {
            cfg.validate()?;
            World::new(cfg)
        }
    };
    fs::create_dir_all(&o.out_dir).map_err(|e| e.to_string())?;
    let mut r = Runner::new(world, o);
    if r.o.cmd_log.is_some() { r.w.cmd_log = Some(vec![]); }
    let t0 = Instant::now();
    if let Some(f) = &script_f {
        let text = fs::read_to_string(f).map_err(|e| format!("{}: {}", f, e))?;
        let mut d = Driver::install(&mut r.w)?;
        run_script(&mut r, &mut d, &text)?;
    }
    if let Some(f) = &build_f {
        let text = fs::read_to_string(f).map_err(|e| format!("{}: {}", f, e))?;
        let (ok, bad) = run_build(&mut r.w, &text)?;
        eprintln!("build: {} commands ok, {} refused", ok, bad);
    }
    let mut mism = 0usize;
    if let Some(f) = &netlist_f {
        let nl = Netlist::parse(&fs::read_to_string(f).map_err(|e| format!("{}: {}", f, e))?)?;
        let map = nl.build(&mut r.w)?;
        if let Some(vf) = &vectors_f {
            let rep = run_vectors(&mut r.w, &nl, &map, &fs::read_to_string(vf).map_err(|e| format!("{}: {}", vf, e))?)?;
            println!("vectors: {} ticks, {} comparisons, {} mismatches", rep.ticks, rep.compared, rep.mismatches);
            for m in &rep.first {
                println!("  {}", m);
            }
            mism = rep.mismatches;
        }
    }
    r.run(steps.unwrap_or(if script_f.is_some() || netlist_f.is_some() { 0 } else { 1000 }));
    for n in &r.notes {
        eprintln!("{}", n);
    }
    if let Some(f) = svg_end {
        r.write_svg(&f);
        eprintln!("{}", r.notes.last().cloned().unwrap_or_default());
    }
    if let Some(f) = save_f {
        fs::write(&f, r.w.save_state()).map_err(|e| format!("{}: {}", f, e))?;
        eprintln!("saved {}", f);
    }
    if let Some(f) = pads_f {
        let mut out = String::new();
        for (pi, p) in r.w.parts.iter().enumerate() {
            let (n_in, n_out) = pin_counts(p.kind, p.abits);
            for k in 0..n_in + n_out {
                let pin = if k < n_in { Pin::In(k as u8) } else { Pin::Out((k - n_in) as u8) };
                if let (Some((x, y)), Some(net)) = (r.w.pin_site(pi as u32, pin), r.w.net_of_pin(pi as u32, pin)) {
                    let nm = match pin { Pin::In(i) => format!("in{}", i), Pin::Out(j) => format!("out{}", j) };
                    out.push_str(&format!("{} {} {} {} {} {}\n", pi, p.kind.name(), nm, x, y, net));
                }
            }
        }
        fs::write(&f, out).map_err(|e| format!("{}: {}", f, e))?;
    }
    println!("{}", r.w.stats().report());
    for m in r.w.fault_log.iter().take(10) {
        println!("  fault: {}", m);
    }
    eprintln!("wall time {:.2}s", t0.elapsed().as_secs_f64());
    Ok(if mism > 0 || r.w.faults > 0 && netlist_f.is_some() { 1 } else { 0 })
}

fn main() {
    match real_main() {
        Ok(c) => std::process::exit(c),
        Err(e) => {
            eprintln!("error: {}", e);
            std::process::exit(2);
        }
    }
}
