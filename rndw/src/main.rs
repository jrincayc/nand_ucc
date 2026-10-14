//! rndw command line: batch and interactive modes.  Standard library only.

use rndw::driver::Driver;
use rndw::netlist::Netlist;
use rndw::svg::{render, SvgOpts, SvgPolicy};
use rndw::vectors::run_vectors;
use rndw::world::{Config, Kind, World};
use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::time::Instant;

const HELP: &str = "\
rndw - RNDW world simulator (Robot + NAND + DFF + Wires + ROM)

USAGE: rndw [OPTIONS]

World source (default: an empty world):
  --world FILE            load a saved state / seed world (rndw-state 1 format)
  --netlist FILE          load a nandgen netlist; inputs become harness Sources
  --script FILE           build things through a driven arm (one register write per tick)
  --vectors FILE          with --netlist: replay a rndw-vectors trace against the Python reference
                          and exit 1 on any mismatch (see tools/gen_vectors.py)

World parameters (ignored when --world supplies a cfg line):
  --width N  --height N   grid size, at most 65536 (default 65536 x 65536)
  --rom-bits N            ROM address bits, 1..16 (default 12)
  --event-limit N         max settle events per phase before a convergence fault (default 5000000)

Running:
  --steps N               ticks to run.  Default: 1000, or until the script finishes if --script
                          is given, or unlimited with --interactive
  --interactive           print status periodically; press Enter to pause (menu: save / svg / quit)
  --status-every N        status line every N ticks (default 10000 interactive, off in batch)

Output:
  --out-dir DIR           directory for SVG and state files (default .)
  --svg-on-en             SVG when a WIRE command attaches to the EN pin of any ARM
  --svg-every N           SVG every N ticks (0 = off)
  --svg-at-end            SVG after the last tick
  --svg-max-elements N    above this many parts+wires, draw coarse merged blocks (default 50000)
  --svg-window X0,Y0,X1,Y1  draw only this region (X1, Y1 exclusive)
  --svg-scale F           pixels per grid cell (default 6)
  --save FILE             write the final state (rndw-state 1) to FILE
  -h, --help              this text

Script lines (# comments):  place KIND X Y [ROT] | wire AX AY BX BY | rom X Y ADDR VAL | nop [N]
  KIND is nand, dff, rom, arm or 0..3.  The driver arm occupies x 0..21, y 0..13.
";

struct Args {
    world: Option<String>,
    netlist: Option<String>,
    script: Option<String>,
    vectors: Option<String>,
    steps: Option<u64>,
    interactive: bool,
    status_every: Option<u64>,
    out_dir: String,
    svg_on_en: bool,
    svg_every: u64,
    svg_at_end: bool,
    svg_max: usize,
    svg_window: Option<(i32, i32, i32, i32)>,
    svg_scale: f64,
    save: Option<String>,
    cfg: Config,
}

fn parse_args() -> Result<Args, String> {
    let mut a = Args {
        world: None,
        netlist: None,
        script: None,
        vectors: None,
        steps: None,
        interactive: false,
        status_every: None,
        out_dir: ".".into(),
        svg_on_en: false,
        svg_every: 0,
        svg_at_end: false,
        svg_max: SvgOpts::default().max_elements,
        svg_window: None,
        svg_scale: SvgOpts::default().scale,
        save: None,
        cfg: Config::default(),
    };
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        let mut val = |name: &str| it.next().ok_or_else(|| format!("{} needs a value", name));
        fn n<T: std::str::FromStr>(s: String, name: &str) -> Result<T, String> {
            s.parse::<T>().map_err(|_| format!("bad value for {}: {}", name, s))
        }
        match arg.as_str() {
            "-h" | "--help" => {
                print!("{}", HELP);
                std::process::exit(0);
            }
            "--world" => a.world = Some(val("--world")?),
            "--netlist" => a.netlist = Some(val("--netlist")?),
            "--script" => a.script = Some(val("--script")?),
            "--vectors" => a.vectors = Some(val("--vectors")?),
            "--width" => a.cfg.width = n(val("--width")?, "--width")?,
            "--height" => a.cfg.height = n(val("--height")?, "--height")?,
            "--rom-bits" => a.cfg.rom_abits = n(val("--rom-bits")?, "--rom-bits")?,
            "--event-limit" => a.cfg.event_limit = n(val("--event-limit")?, "--event-limit")?,
            "--steps" => a.steps = Some(n(val("--steps")?, "--steps")?),
            "--interactive" => a.interactive = true,
            "--status-every" => a.status_every = Some(n(val("--status-every")?, "--status-every")?),
            "--out-dir" => a.out_dir = val("--out-dir")?,
            "--svg-on-en" => a.svg_on_en = true,
            "--svg-every" => a.svg_every = n(val("--svg-every")?, "--svg-every")?,
            "--svg-at-end" => a.svg_at_end = true,
            "--svg-max-elements" => a.svg_max = n(val("--svg-max-elements")?, "--svg-max-elements")?,
            "--svg-scale" => a.svg_scale = n(val("--svg-scale")?, "--svg-scale")?,
            "--svg-window" => {
                let s = val("--svg-window")?;
                let v: Vec<i32> = s.split(',').filter_map(|p| p.trim().parse().ok()).collect();
                if v.len() != 4 {
                    return Err("--svg-window needs X0,Y0,X1,Y1".into());
                }
                a.svg_window = Some((v[0], v[1], v[2], v[3]));
            }
            "--save" => a.save = Some(val("--save")?),
            other => return Err(format!("unknown option {} (try --help)", other)),
        }
    }
    a.cfg.validate()?;
    Ok(a)
}

fn read(path: &str) -> Result<String, String> {
    std::fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))
}

fn kind_code(s: &str) -> Result<u8, String> {
    match s.to_ascii_lowercase().as_str() {
        "nand" => Ok(0),
        "dff" => Ok(1),
        "rom" => Ok(2),
        "arm" => Ok(3),
        other => other.parse::<u8>().map_err(|_| format!("bad part kind '{}'", s)),
    }
}

fn load_script(path: &str, d: &mut Driver) -> Result<(), String> {
    for (i, line) in read(path)?.lines().enumerate() {
        let l = line.trim();
        if l.is_empty() || l.starts_with('#') {
            continue;
        }
        let t: Vec<&str> = l.split_whitespace().collect();
        let err = |m: &str| format!("{} line {}: {}", path, i + 1, m);
        let num = |k: usize| -> Result<i32, String> {
            t.get(k).and_then(|s| s.parse::<i32>().ok()).ok_or_else(|| err("missing or bad number"))
        };
        match t[0] {
            "place" => {
                let rot = if t.len() > 4 { num(4)? as u8 } else { 0 };
                d.place(kind_code(t.get(1).ok_or_else(|| err("missing kind"))?)?, num(2)?, num(3)?, rot);
            }
            "wire" => d.wire(num(1)?, num(2)?, num(3)?, num(4)?),
            "rom" => d.program_rom(num(1)?, num(2)?, num(3)? as u16, num(4)? as u8),
            "nop" => d.nop(if t.len() > 1 { num(1)? as usize } else { 1 }),
            other => return Err(err(&format!("unknown script command '{}'", other))),
        }
    }
    Ok(())
}

fn spawn_stdin() -> Receiver<String> {
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        let stdin = io::stdin();
        for line in stdin.lock().lines() {
            match line {
                Ok(l) => {
                    if tx.send(l).is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    });
    rx
}

/// Pause menu.  Returns false to quit.
fn menu(w: &World, rx: &Receiver<String>, policy: &SvgPolicy, out_dir: &str) -> bool {
    println!("-- paused at tick {} --", w.tick);
    println!("   s [file] save state | v [file] write SVG | t status | c continue | q quit");
    loop {
        print!("rndw> ");
        let _ = io::stdout().flush();
        let line = match rx.recv() {
            Ok(l) => l,
            Err(_) => return false,
        };
        let mut t = line.split_whitespace();
        match t.next() {
            None | Some("c") | Some("continue") => return true,
            Some("q") | Some("quit") => return false,
            Some("t") | Some("status") => println!("{}", w.stats().line()),
            Some("s") | Some("save") => {
                let path = t.next().map(PathBuf::from).unwrap_or_else(|| {
                    PathBuf::from(out_dir).join(format!("rndw_state_t{}.txt", w.tick))
                });
                match std::fs::write(&path, w.save_state()) {
                    Ok(_) => println!("saved {}", path.display()),
                    Err(e) => println!("save failed: {}", e),
                }
            }
            Some("v") | Some("svg") => {
                let res = match t.next() {
                    Some(f) => std::fs::write(f, render(w, &policy.opts)).map(|_| PathBuf::from(f)),
                    None => policy.write(w, "manual"),
                };
                match res {
                    Ok(p) => println!("wrote {}", p.display()),
                    Err(e) => println!("svg failed: {}", e),
                }
            }
            Some(other) => println!("unknown command '{}'", other),
        }
    }
}

fn run() -> Result<(), String> {
    let a = parse_args()?;
    let mut world = match &a.world {
        Some(f) => World::load_state(&read(f)?)?,
        None => World::new(a.cfg.clone()),
    };
    let mut netinfo = None;
    if let Some(f) = &a.netlist {
        let nl = Netlist::parse(&read(f)?)?;
        let map = nl.build(&mut world)?;
        netinfo = Some((nl, map));
    }
    if let Some(vf) = &a.vectors {
        let (nl, map) = netinfo.as_ref().ok_or("--vectors needs --netlist")?;
        world.settle();
        let rep = run_vectors(&mut world, nl, map, &read(vf)?)?;
        println!(
            "{}: {} ticks, {} wire comparisons, {} mismatches",
            vf, rep.ticks, rep.compared, rep.mismatches
        );
        for m in &rep.first {
            println!("  MISMATCH {}", m);
        }
        if rep.mismatches > 0 {
            std::process::exit(1);
        }
        return Ok(());
    }
    let mut driver = match &a.script {
        Some(f) => {
            let mut d = Driver::install(&mut world, 0, 0)?;
            load_script(f, &mut d)?;
            Some(d)
        }
        None => None,
    };
    world.settle();
    world.take_en_wire_event();

    let policy = SvgPolicy {
        dir: PathBuf::from(&a.out_dir),
        on_en: a.svg_on_en,
        every: a.svg_every,
        opts: SvgOpts { max_elements: a.svg_max, window: a.svg_window, scale: a.svg_scale, signals: true },
    };
    let steps = match (a.steps, a.interactive, driver.is_some()) {
        (Some(n), _, _) => Some(n),
        (None, true, _) => None,
        (None, false, true) => None, // run until the script is finished
        (None, false, false) => Some(1000),
    };
    let until_script = a.steps.is_none() && !a.interactive && driver.is_some();
    let status_every = a.status_every.unwrap_or(if a.interactive { 10_000 } else { 0 });
    let mut rx = if a.interactive { Some(spawn_stdin()) } else { None };
    if a.interactive {
        println!("interactive: press Enter to pause. {}", world.stats().line());
    }

    let t0 = Instant::now();
    let start_tick = world.tick;
    loop {
        if let Some(n) = steps {
            if world.tick - start_tick >= n {
                break;
            }
        }
        if until_script && driver.as_ref().map_or(true, |d| d.idle()) {
            break;
        }
        if let Some(d) = driver.as_mut() {
            d.pre_step(&mut world);
        }
        world.step();
        for p in policy.after_step(&mut world) {
            println!("wrote {}", p.display());
        }
        if status_every > 0 && world.tick % status_every == 0 {
            let rate = (world.tick - start_tick) as f64 / t0.elapsed().as_secs_f64().max(1e-9);
            println!("{} | {:.0} ticks/s", world.stats().line(), rate);
        }
        if let Some(r) = &rx {
            match r.try_recv() {
                Ok(_) => {
                    if !menu(&world, r, &policy, &a.out_dir) {
                        break;
                    }
                }
                Err(TryRecvError::Empty) => {}
                Err(TryRecvError::Disconnected) => rx = None,
            }
        }
    }
    // A finished driver must not leave EN high, or a saved state would re-run its last command.
    if let Some(d) = driver.as_mut() {
        if d.idle() {
            d.pre_step(&mut world);
        }
    }
    if a.svg_at_end {
        match policy.write(&world, "end") {
            Ok(p) => println!("wrote {}", p.display()),
            Err(e) => eprintln!("svg failed: {}", e),
        }
    }
    if let Some(f) = &a.save {
        std::fs::write(f, world.save_state()).map_err(|e| format!("{}: {}", f, e))?;
        println!("saved {}", f);
    }
    println!("{}", world.stats().report());
    for m in world.fault_log.iter().take(10) {
        println!("  fault: {}", m);
    }
    let _ = Kind::Nand;
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {}", e);
        std::process::exit(1);
    }
}
