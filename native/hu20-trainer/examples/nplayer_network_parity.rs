//! Checks the Rust `policy_network` forward pass against PyTorch (docs/neural-policy-fallback.md).
//!
//!     nplayer_network_parity NETWORK SHA256 FIXTURE [TOLERANCE]
//!
//! The fixture holds feature bytes, legal masks and PyTorch's probabilities
//! (`neural_policy_imitation parity`). Prints the largest absolute difference and exits 1 above
//! the tolerance (default 1e-5).
use hu20_trainer::policy_network::PolicyNetwork;
use serde_json::json;
use std::path::Path;

fn run(a: &[String]) -> Result<bool, String> {
    let net = PolicyNetwork::load(Path::new(&a[1]), &a[2])?;
    let tolerance: f64 = a.get(4).map_or(Ok(1e-5), |t| t.parse().map_err(|_| "tolerance".to_string()))?;
    let b = std::fs::read(&a[3]).map_err(|e| e.to_string())?;
    if b.len() < 24 || &b[..8] != b"NPPAR001" {
        return Err("not a parity fixture".into());
    }
    let n = u64::from_le_bytes(b[8..16].try_into().unwrap()) as usize;
    let f = u64::from_le_bytes(b[16..24].try_into().unwrap()) as usize;
    let (x0, m0, p0) = (24, 24 + n * f, 24 + n * f + n);
    if b.len() != p0 + n * 6 * 8 {
        return Err("fixture size".into());
    }
    let (mut worst, mut at) = (0f64, 0usize);
    for i in 0..n {
        let input: Vec<f32> = b[x0 + i * f..x0 + (i + 1) * f].iter().map(|&v| v as f32 / 255.).collect();
        let p = net.label_probabilities(&input, b[m0 + i])?;
        for k in 0..6 {
            let o = p0 + (i * 6 + k) * 8;
            let expected = f64::from_le_bytes(b[o..o + 8].try_into().unwrap());
            let d = (p[k] - expected).abs();
            if d > worst {
                worst = d;
                at = i;
            }
        }
    }
    println!("{}", json!({"network":net.sha256,"samples":n,"max_abs_difference":worst,"at_sample":at,"tolerance":tolerance,"passed":worst <= tolerance}));
    Ok(worst <= tolerance)
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if !(4..=5).contains(&a.len()) {
        eprintln!("usage: nplayer_network_parity NETWORK SHA256 FIXTURE [TOLERANCE]");
        std::process::exit(2);
    }
    match run(&a) {
        Ok(true) => {}
        Ok(false) => std::process::exit(1),
        Err(e) => {
            eprintln!("nplayer_network_parity: {e}");
            std::process::exit(2);
        }
    }
}
