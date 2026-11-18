//! Each Rust variant's speed, for tools/jmath_fuzz.py --bench (our notes only), as tools/jmath_fuzz/JmathBench.java
//! times the JVM: nanoseconds per call over a fixed array of inputs in the function's usual range, warmed up, as
//! timed passes.
//!
//!     jmath_bench FUNCTION
use std::{env, hint::black_box, time::Instant};
use sunrise_core::jmath;

const INPUTS: usize = 1 << 14;
const BATCHES: usize = 400;

fn range(f: &str) -> (f64, f64) {
    match f {
        "exp" => (-745.0, 710.0),
        "log" | "log10" | "cbrt" => (0.0, 1e6),
        "pow" => (0.0, 16.0),
        _ => (-8.0 * std::f64::consts::PI, 8.0 * std::f64::consts::PI),
    }
}

type Variant = (&'static str, fn(f64, f64) -> f64);

fn variants(f: &str) -> Vec<Variant> {
    match f {
        "sin" => vec![
            ("jmath", |x, _| jmath::sin(x)),
            ("exact", |x, _| jmath::exact::sin(x)),
        ],
        "cos" => vec![
            ("jmath", |x, _| jmath::cos(x)),
            ("exact", |x, _| jmath::exact::cos(x)),
        ],
        "tan" => vec![("jmath", |x, _| jmath::tan(x))],
        "exp" => vec![("jmath", |x, _| jmath::exp(x))],
        "log" => vec![
            ("jmath", |x, _| jmath::log(x)),
            ("platform", |x, _| x.ln()),
            ("exact", |x, _| jmath::exact::log(x)),
            ("fdlibm", |x, _| jmath::fdlibm::log(x)),
        ],
        "log10" => vec![
            ("jmath", |x, _| jmath::log10(x)),
            ("fdlibm", |x, _| jmath::fdlibm::log10(x)),
        ],
        "pow" => vec![("jmath", jmath::pow)],
        "cbrt" => vec![
            ("jmath", |x, _| jmath::cbrt(x)),
            ("fdlibm", |x, _| jmath::fdlibm::cbrt(x)),
        ],
        "atan2" => vec![("jmath", jmath::atan2), ("platform", |x, y| x.atan2(y))],
        other => panic!("unknown function {other}"),
    }
}

fn main() {
    let f = env::args().nth(1).expect("function");
    // A simple LCG for the inputs: the timing needs a fixed spread, not the JVM's exact values.
    let mut state = 1u64;
    let mut next = || {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (state >> 11) as f64 * f64::from_bits(0x3ca << 52)
    };
    let (lo, hi) = range(&f);
    let x: Vec<f64> = (0..INPUTS).map(|_| lo + next() * (hi - lo)).collect();
    let y: Vec<f64> = (0..INPUTS)
        .map(|_| {
            if f == "pow" {
                -16.0 + 32.0 * next()
            } else {
                next() * 8.0 - 4.0
            }
        })
        .collect();
    for (name, compute) in variants(&f) {
        let run = || {
            let mut s = 0.0;
            for i in 0..INPUTS {
                s += compute(black_box(x[i]), black_box(y[i]));
            }
            black_box(s)
        };
        for _ in 0..200 {
            run();
        }
        let mut per_call: Vec<f64> = (0..BATCHES)
            .map(|_| {
                let start = Instant::now();
                run();
                start.elapsed().as_nanos() as f64 / INPUTS as f64
            })
            .collect();
        per_call.sort_by(f64::total_cmp);
        println!(
            "{{\"function\":\"{f}\",\"variant\":\"{name}\",\"median_ns\":{:.3},\"p99_ns\":{:.3}}}",
            per_call[BATCHES / 2],
            per_call[BATCHES * 99 / 100]
        );
    }
}
