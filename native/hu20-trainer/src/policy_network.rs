//! A small MLP policy over `policy_features`, hand-written so play needs no ML runtime
//! (docs/neural-policy-fallback.md).
//!
//! The file is the magic `NPNET001`, a little-endian u64 header length, a JSON header and then each
//! layer's float32 weights (output-major, `out × in`) followed by its biases. Hidden layers use ReLU;
//! the output is a softmax over the six menu labels, restricted to the legal ones. Arithmetic is in
//! f64 over f32 weights, so results don't depend on summation order beyond f64 rounding.
use crate::cards::EquityTables;
use crate::multi_holdem::menu;
use crate::nplayer::Observation;
use crate::policy_features::{self as features, ACTIONS};
use serde_json::Value;
use std::path::Path;

pub const FORMAT: &str = "nplayer-policy-network-v1";
pub const MAGIC: &[u8; 8] = b"NPNET001";

struct Layer {
    inputs: usize,
    outputs: usize,
    weights: Vec<f32>,
    biases: Vec<f32>,
}

pub struct PolicyNetwork {
    pub header: Value,
    pub sha256: String,
    layers: Vec<Layer>,
}

impl PolicyNetwork {
    /// Loads a network file whose SHA-256 must equal `expected`, and whose feature layout must be
    /// this build's `policy_features` layout.
    pub fn load(path: &Path, expected: &str) -> Result<Self, String> {
        let bytes = std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
        let sha = {
            use sha2::{Digest, Sha256};
            format!("{:x}", Sha256::digest(&bytes))
        };
        if sha != expected {
            return Err("network SHA256 mismatch".into());
        }
        let mut net = Self::parse(&bytes)?;
        net.sha256 = sha;
        Ok(net)
    }

    pub fn parse(bytes: &[u8]) -> Result<Self, String> {
        if bytes.len() < 16 || &bytes[..8] != MAGIC {
            return Err("not a policy network file".into());
        }
        let size = u64::from_le_bytes(bytes[8..16].try_into().unwrap()) as usize;
        let body = 16usize.checked_add(size).filter(|&e| e <= bytes.len()).ok_or("network header length")?;
        let header: Value = serde_json::from_slice(&bytes[16..body]).map_err(|e| e.to_string())?;
        if header["format"] != FORMAT || header["activation"] != "relu" || header["output"] != "masked-softmax-6" {
            return Err("network format".into());
        }
        if header["layout_sha256"] != features::layout_sha256() || header["features"] != features::len() {
            return Err("network feature layout differs from this build".into());
        }
        let shapes = header["layers"].as_array().ok_or("network layers")?;
        let mut layers = Vec::new();
        let mut offset = body;
        let mut width = features::len();
        for shape in shapes {
            let (i, o) = (shape["in"].as_u64().ok_or("layer in")? as usize, shape["out"].as_u64().ok_or("layer out")? as usize);
            if i != width || o == 0 {
                return Err("network layer shapes don't chain".into());
            }
            let mut take = |n: usize| -> Result<Vec<f32>, String> {
                let end = offset.checked_add(n * 4).filter(|&e| e <= bytes.len()).ok_or("network file truncated")?;
                let v = bytes[offset..end].chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
                offset = end;
                Ok(v)
            };
            let weights = take(i * o)?;
            let biases = take(o)?;
            if weights.iter().chain(&biases).any(|v| !v.is_finite()) {
                return Err("network weights not finite".into());
            }
            layers.push(Layer { inputs: i, outputs: o, weights, biases });
            width = o;
        }
        if width != ACTIONS || layers.is_empty() {
            return Err("network output must have six labels".into());
        }
        if offset != bytes.len() {
            return Err("network file has trailing bytes".into());
        }
        Ok(Self { header, sha256: String::new(), layers })
    }

    /// Logits over the six labels for one feature vector.
    pub fn logits(&self, input: &[f32]) -> Result<[f64; ACTIONS], String> {
        if input.len() != features::len() {
            return Err("network input length".into());
        }
        let mut x: Vec<f64> = input.iter().map(|&v| v as f64).collect();
        for (k, layer) in self.layers.iter().enumerate() {
            let mut y = Vec::with_capacity(layer.outputs);
            for o in 0..layer.outputs {
                let row = &layer.weights[o * layer.inputs..(o + 1) * layer.inputs];
                let mut sum = layer.biases[o] as f64;
                for (w, v) in row.iter().zip(&x) {
                    sum += *w as f64 * v;
                }
                y.push(if k + 1 < self.layers.len() { sum.max(0.) } else { sum });
            }
            x = y;
        }
        Ok(x.try_into().unwrap())
    }

    /// Probabilities over the six labels; labels outside `legal` (a bit set) get 0.
    pub fn label_probabilities(&self, input: &[f32], legal: u8) -> Result<[f64; ACTIONS], String> {
        if legal & ((1 << ACTIONS) - 1) == 0 {
            return Err("no legal label".into());
        }
        let logits = self.logits(input)?;
        let top = (0..ACTIONS).filter(|a| legal >> a & 1 == 1).map(|a| logits[a]).fold(f64::NEG_INFINITY, f64::max);
        let mut p = [0.; ACTIONS];
        for a in 0..ACTIONS {
            if legal >> a & 1 == 1 {
                p[a] = (logits[a] - top).exp();
            }
        }
        let total: f64 = p.iter().sum();
        for v in &mut p {
            *v /= total;
        }
        Ok(p)
    }

    /// The network's strategy at an acting seat's observation, in menu order, with the label
    /// probabilities it came from. The features use the quantized bytes the network trained on.
    pub fn distribution(&self, observation: &Observation<'_>, tables: &EquityTables) -> Result<(Vec<f64>, [f64; ACTIONS]), String> {
        let bytes = features::quantize(&features::encode(observation, Some(tables))?);
        let input: Vec<f32> = bytes.iter().map(|&b| b as f32 / 255.).collect();
        let p = self.label_probabilities(&input, features::legal_mask(observation))?;
        Ok((menu(observation).iter().map(|(label, _)| p[*label as usize]).collect(), p))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// A network file with the given layer widths and weights from `value(layer, index)`.
    pub(crate) fn file(widths: &[usize], value: impl Fn(usize, usize) -> f32) -> Vec<u8> {
        let mut dims = vec![features::len()];
        dims.extend_from_slice(widths);
        let layers: Vec<_> = dims.windows(2).map(|w| json!({"in":w[0],"out":w[1]})).collect();
        let header = serde_json::to_vec(&json!({"format":FORMAT,"layout_sha256":features::layout_sha256(),
            "features":features::len(),"layers":layers,"activation":"relu","output":"masked-softmax-6"})).unwrap();
        let mut out = MAGIC.to_vec();
        out.extend_from_slice(&(header.len() as u64).to_le_bytes());
        out.extend_from_slice(&header);
        for (k, w) in dims.windows(2).enumerate() {
            for i in 0..w[0] * w[1] + w[1] {
                out.extend_from_slice(&value(k, i).to_le_bytes());
            }
        }
        out
    }

    #[test]
    fn a_linear_network_gives_the_masked_softmax_of_its_logits() {
        // One layer: logit[a] = bias[a] = a.
        let f = file(&[ACTIONS], |_, i| if i >= features::len() * ACTIONS { (i - features::len() * ACTIONS) as f32 } else { 0. });
        let net = PolicyNetwork::parse(&f).unwrap();
        let x = vec![0.5; features::len()];
        assert_eq!(net.logits(&x).unwrap(), [0., 1., 2., 3., 4., 5.]);
        let p = net.label_probabilities(&x, 0b000110).unwrap();
        let e = std::f64::consts::E;
        assert!((p[1] - 1. / (1. + e)).abs() < 1e-12 && (p[2] - e / (1. + e)).abs() < 1e-12);
        assert_eq!((p[0], p[3], p[4], p[5]), (0., 0., 0., 0.));
        assert!(net.label_probabilities(&x, 0).is_err());
    }

    #[test]
    fn hidden_layers_apply_relu() {
        // Hidden unit = -sum(x) (always negative), so ReLU zeroes it and the output is the bias.
        let n = features::len();
        let f = file(&[1, ACTIONS], |k, i| match (k, i) {
            (0, i) if i < n => -1.,
            (0, _) => 0.,
            (1, i) if i < ACTIONS => 100.,
            (1, i) => (i - ACTIONS) as f32,
            _ => unreachable!(),
        });
        let net = PolicyNetwork::parse(&f).unwrap();
        assert_eq!(net.logits(&vec![1.; n]).unwrap(), [0., 1., 2., 3., 4., 5.]);
    }

    #[test]
    fn malformed_files_are_refused() {
        let good = file(&[ACTIONS], |_, _| 0.);
        assert!(PolicyNetwork::parse(&good).is_ok());
        assert!(PolicyNetwork::parse(&good[..good.len() - 4]).is_err(), "truncated");
        let mut extra = good.clone();
        extra.extend_from_slice(&[0; 4]);
        assert!(PolicyNetwork::parse(&extra).is_err(), "trailing bytes");
        assert!(PolicyNetwork::parse(&file(&[5], |_, _| 0.)).is_err(), "wrong output width");
        let mut nan = good.clone();
        let at = nan.len() - 4;
        nan[at..].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(PolicyNetwork::parse(&nan).is_err(), "non-finite weight");
        let dir = std::env::temp_dir().join(format!("npnet-{}", std::process::id()));
        std::fs::write(&dir, &good).unwrap();
        assert!(PolicyNetwork::load(&dir, &"0".repeat(64)).is_err(), "pin mismatch");
        std::fs::remove_file(&dir).unwrap();
    }
}
