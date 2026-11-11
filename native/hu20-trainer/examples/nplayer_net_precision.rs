//! Cheaper weights for traversal inference: accuracy and speed (docs/reports/advantage-inference-precision).
//!
//!     nplayer_net_precision --network NET SHA256 --inputs ROWS --rows N [--seconds S]
//!
//! `ROWS` holds feature rows as the reservoirs store them: 612 quantized feature bytes, then the
//! legal mask, per row. The production f32 kernel (`Fast`) is the reference. The study kernel walks
//! the same input-major weights and skips zero inputs, as `Fast` does, with the weights stored as:
//! - `f32`: the reference's own weights, a check that the study kernel gives `Fast`'s bits;
//! - `bf16`: the top 16 bits of each f32, rounded to nearest even;
//! - `int8`: one symmetric scale per input row (max |w| / 127), so a row costs one multiply.
//!
//! Accumulation stays f32. For each format it prints the output error against the reference, the
//! strategy's total variation from the reference strategy, and single-thread seconds per call.
use hu20_trainer::{
    policy_features as features,
    policy_network::{regret_match, Output, PolicyNetwork},
};
use serde_json::{json, Value};
use std::{collections::HashMap, path::Path, time::Instant};

const ACTIONS: usize = 6;

enum Weights {
    F32(Vec<f32>),
    Bf16(Vec<u16>),
    Int8(Vec<i8>, Vec<f32>),
}
struct Layer {
    inputs: usize,
    outputs: usize,
    w: Weights,
    b: Vec<f32>,
}

/// The network file's layers, input-major (each input's weights over the outputs are contiguous).
fn layers(bytes: &[u8]) -> Result<Vec<(usize, usize, Vec<f32>, Vec<f32>)>, String> {
    let size = u64::from_le_bytes(bytes[8..16].try_into().unwrap()) as usize;
    let header: Value = serde_json::from_slice(&bytes[16..16 + size]).map_err(|e| e.to_string())?;
    let mut offset = 16 + size;
    let mut out = Vec::new();
    for shape in header["layers"].as_array().ok_or("layers")? {
        let (i, o) = (shape["in"].as_u64().unwrap() as usize, shape["out"].as_u64().unwrap() as usize);
        let mut take = |n: usize| {
            let v: Vec<f32> = bytes[offset..offset + 4 * n].chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
            offset += 4 * n;
            v
        };
        let w = take(i * o);
        let b = take(o);
        let mut t = vec![0f32; i * o];
        for r in 0..o {
            for c in 0..i {
                t[c * o + r] = w[r * i + c];
            }
        }
        out.push((i, o, t, b));
    }
    Ok(out)
}

fn bf16(v: f32) -> u16 {
    let bits = v.to_bits();
    let round = 0x7fff + ((bits >> 16) & 1);
    (bits.wrapping_add(round) >> 16) as u16
}

fn convert(ls: &[(usize, usize, Vec<f32>, Vec<f32>)], format: &str) -> Vec<Layer> {
    ls.iter().map(|(i, o, t, b)| {
        let w = match format {
            "f32" => Weights::F32(t.clone()),
            "bf16" => Weights::Bf16(t.iter().map(|&v| bf16(v)).collect()),
            _ => {
                let mut q = vec![0i8; t.len()];
                let mut scales = vec![0f32; *i];
                for r in 0..*i {
                    let row = &t[r * o..(r + 1) * o];
                    let m = row.iter().fold(0f32, |m, v| m.max(v.abs()));
                    let s = if m > 0. { m / 127. } else { 1. };
                    scales[r] = s;
                    for (k, v) in row.iter().enumerate() {
                        q[r * o + k] = (v / s).round().clamp(-127., 127.) as i8;
                    }
                }
                Weights::Int8(q, scales)
            }
        };
        Layer { inputs: *i, outputs: *o, w, b: b.clone() }
    }).collect()
}

fn forward(layers: &[Layer], bytes: &[u8], x: &mut Vec<f32>, y: &mut Vec<f32>) -> [f32; ACTIONS] {
    x.clear();
    x.extend(bytes.iter().map(|&b| b as f32 / 255.));
    let last = layers.len() - 1;
    for (k, l) in layers.iter().enumerate() {
        debug_assert_eq!(x.len(), l.inputs);
        y.clear();
        y.extend_from_slice(&l.b);
        let o = l.outputs;
        for (i, &v) in x.iter().enumerate() {
            if v == 0. {
                continue;
            }
            match &l.w {
                Weights::F32(t) => {
                    for (acc, w) in y.iter_mut().zip(&t[i * o..(i + 1) * o]) {
                        *acc += v * w;
                    }
                }
                Weights::Bf16(t) => {
                    for (acc, w) in y.iter_mut().zip(&t[i * o..(i + 1) * o]) {
                        *acc += v * f32::from_bits((*w as u32) << 16);
                    }
                }
                Weights::Int8(t, s) => {
                    let vs = v * s[i];
                    for (acc, w) in y.iter_mut().zip(&t[i * o..(i + 1) * o]) {
                        *acc += vs * *w as f32;
                    }
                }
            }
        }
        if k < last {
            for v in y.iter_mut() {
                *v = v.max(0.);
            }
        }
        std::mem::swap(x, y);
    }
    let mut out = [0f32; ACTIONS];
    out.copy_from_slice(&x[..ACTIONS]);
    out
}

fn strategy(output: Output, z: &[f32; ACTIONS], legal: u8) -> [f64; ACTIONS] {
    let z = z.map(|v| v as f64);
    match output {
        Output::Advantage => regret_match(&z, legal),
        Output::Policy => {
            let top = (0..ACTIONS).filter(|a| legal >> a & 1 == 1).map(|a| z[a]).fold(f64::NEG_INFINITY, f64::max);
            let mut p = [0.; ACTIONS];
            for a in (0..ACTIONS).filter(|a| legal >> a & 1 == 1) {
                p[a] = (z[a] - top).exp();
            }
            let s: f64 = p.iter().sum();
            p.map(|v| v / s)
        }
    }
}

fn quantile(v: &mut [f64], q: f64) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    v[((v.len() - 1) as f64 * q).round() as usize]
}

fn main() -> Result<(), String> {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let mut m: HashMap<String, Vec<String>> = HashMap::new();
    let mut key = String::new();
    for s in &a {
        if let Some(k) = s.strip_prefix("--") {
            key = k.into();
            m.entry(key.clone()).or_default();
        } else {
            m.get_mut(&key).ok_or("arguments start with --")?.push(s.clone());
        }
    }
    let get = |k: &str| m.get(k).and_then(|v| v.first()).cloned().ok_or(format!("--{k}"));
    let net_args = m.get("network").filter(|v| v.len() == 2).ok_or("--network PATH SHA256")?;
    let net = PolicyNetwork::load(Path::new(&net_args[0]), &net_args[1])?;
    let fast = net.fast();
    let file = std::fs::read(&net_args[0]).map_err(|e| e.to_string())?;
    let raw = layers(&file)?;
    let rows: usize = get("rows")?.parse().map_err(|_| "--rows")?;
    let seconds: f64 = get("seconds").unwrap_or("5".into()).parse().map_err(|_| "--seconds")?;
    let width = features::len() + 1;
    let data = std::fs::read(get("inputs")?).map_err(|e| e.to_string())?;
    let inputs: Vec<&[u8]> = data.chunks_exact(width).take(rows).collect();
    if inputs.len() < rows {
        return Err(format!("only {} rows in --inputs", inputs.len()));
    }
    let (mut x, mut y) = (Vec::new(), Vec::new());
    let mut scratch = [Vec::new(), Vec::new()];
    let reference: Vec<[f32; ACTIONS]> = inputs.iter().map(|r| fast.logits(&r[..width - 1], &mut scratch)).collect();
    let nonzero = inputs.iter().map(|r| r[..width - 1].iter().filter(|&&b| b != 0).count()).sum::<usize>() as f64 / rows as f64;
    let mut report = Vec::new();
    for format in ["f32", "bf16", "int8"] {
        let ls = convert(&raw, format);
        let (mut abs, mut tv, mut top, mut exact) = (Vec::new(), Vec::new(), 0usize, 0usize);
        for (r, want) in inputs.iter().zip(&reference) {
            let legal = r[width - 1];
            let got = forward(&ls, &r[..width - 1], &mut x, &mut y);
            if got.iter().zip(want).all(|(a, b)| a.to_bits() == b.to_bits()) {
                exact += 1;
            }
            let worst = (0..ACTIONS).filter(|k| legal >> k & 1 == 1).map(|k| (got[k] - want[k]).abs() as f64).fold(0., f64::max);
            abs.push(worst);
            let (p, q) = (strategy(net.output, &got, legal), strategy(net.output, want, legal));
            tv.push(0.5 * (0..ACTIONS).map(|k| (p[k] - q[k]).abs()).sum::<f64>());
            let arg = |s: &[f64; ACTIONS]| (0..ACTIONS).fold(0, |b, k| if s[k] > s[b] { k } else { b });
            top += (arg(&p) == arg(&q)) as usize;
        }
        // Single thread, every input in turn, repeated until `seconds` have passed.
        let start = Instant::now();
        let mut calls = 0usize;
        let mut sink = 0f32;
        while start.elapsed().as_secs_f64() < seconds {
            for r in &inputs {
                sink += forward(&ls, &r[..width - 1], &mut x, &mut y)[0];
                calls += 1;
            }
        }
        let per_call = start.elapsed().as_secs_f64() / calls as f64;
        let mean = |v: &[f64]| v.iter().sum::<f64>() / v.len() as f64;
        let entry = json!({"format":format,"rows":rows,"exact_rows":exact,"max_abs_error_mean":mean(&abs),
            "max_abs_error_p99":quantile(&mut abs.clone(), 0.99),"max_abs_error_max":quantile(&mut abs, 1.0),
            "strategy_tv_mean":mean(&tv),"strategy_tv_p99":quantile(&mut tv.clone(), 0.99),"strategy_tv_max":quantile(&mut tv, 1.0),
            "top_label_agreement":top as f64 / rows as f64,"seconds_per_call":per_call,"sink":sink});
        eprintln!("{entry}");
        report.push(entry);
    }
    // The production kernel's own speed on the same inputs, for scale.
    let start = Instant::now();
    let mut calls = 0usize;
    while start.elapsed().as_secs_f64() < seconds {
        for r in &inputs {
            fast.logits(&r[..width - 1], &mut scratch);
            calls += 1;
        }
    }
    println!("{}", json!({"network":net.sha256,"path":net_args[0],"output":format!("{:?}", net.output),"layers":net.header["layers"],
        "mean_nonzero_features":nonzero,"fast_seconds_per_call":start.elapsed().as_secs_f64() / calls as f64,"formats":report}));
    if report[0]["exact_rows"].as_u64() != Some(rows as u64) {
        return Err("the study's f32 kernel differs from Fast".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bf16_rounds_to_nearest_even() {
        assert_eq!(bf16(1.0), 0x3f80);
        assert_eq!(bf16(f32::from_bits(0x3f80_8000)), 0x3f80, "a tie rounds to the even neighbour");
        assert_eq!(bf16(f32::from_bits(0x3f81_8000)), 0x3f82);
        assert_eq!(bf16(f32::from_bits(0x3f80_8001)), 0x3f81);
        assert_eq!(bf16(-2.5), 0xc020);
    }

    #[test]
    fn int8_rows_keep_their_largest_weight_and_bound_the_error() {
        let t = vec![0.5f32, -1.0, 0.25, 0.0, 0.0, 0.0, 3.0, -0.01, 0.02];
        let ls = convert(&[(3, 3, t.clone(), vec![0.; 3])], "int8");
        let Weights::Int8(q, s) = &ls[0].w else { panic!() };
        assert_eq!((q[1], q[6]), (-127, 127));
        assert_eq!(s[1], 1.0, "an all-zero row keeps scale 1");
        for (k, w) in t.iter().enumerate() {
            assert!((q[k] as f32 * s[k / 3] - w).abs() <= s[k / 3] / 2. + 1e-7);
        }
    }
}
