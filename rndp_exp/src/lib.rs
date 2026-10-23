//! RNDP: Robot + NAND + DFF + PCB (+ optional ROM, RAM) world simulator.  Standard library only.
//! Implements nandgen/RNDP_SPEC.md v0.3.
//!   world  - parts, copper, nets (cached union-find), settle, latch, arm interpreter
//!   state  - save / load (rndp-state 1)
//!   svg    - SVG snapshots, one colour per layer
//!   netlist- nandgen netlist import (diagonal test layout) and vector replay
//!   run    - Runner (dump / checkpoint hooks) and the script-driven arm Driver

pub mod netlist;
pub mod run;
pub mod state;
pub mod svg;
pub mod world;
