//! A small MLP policy over `policy_features`, hand-written so play needs no ML runtime
//! (docs/neural-policy-fallback.md).
//!
//! The file is the magic `NPNET001`, a little-endian u64 header length, a JSON header and then each
//! layer's float32 weights (output-major, `out × in`) followed by its biases. Hidden layers use ReLU.
//! A policy network's output (`masked-softmax-6`) is a softmax over the six menu labels, restricted
//! to the legal ones. An advantage network's (`advantage-6`) is one estimated regret per label, played
//! by regret matching (Deep CFR, docs/neural-deep-cfr.md). The reference arithmetic is in f64 over
//! f32 weights; `Fast` is an f32 path for traversals, checked against it.
use crate::cards::EquityTables;
use crate::multi_holdem::menu;
use crate::multi_policy::Policy;
use crate::nplayer::Action;
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

/// What the six outputs mean.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Output {
    /// Logits of a masked softmax: the strategy itself.
    Policy,
    /// Estimated regrets: the strategy is their regret matching.
    Advantage,
}

pub struct PolicyNetwork {
    pub header: Value,
    pub sha256: String,
    pub output: Output,
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
        let output = match header["output"].as_str() {
            Some("masked-softmax-6") => Output::Policy,
            Some("advantage-6") => Output::Advantage,
            _ => return Err("network output kind".into()),
        };
        if header["format"] != FORMAT || header["activation"] != "relu" {
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
        Ok(Self { header, sha256: String::new(), output, layers })
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
        if self.output == Output::Advantage {
            return Ok(regret_match(&self.logits(input)?, legal));
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

    /// The f32 evaluator for traversals; see `Fast`.
    pub fn fast(&self) -> Fast {
        Fast {
            output: self.output,
            layers: self.layers.iter().map(|l| {
                // Input-major copy, so each input adds a contiguous run of outputs (and zero inputs,
                // most of a quantized feature vector and many ReLU outputs, are skipped).
                let mut t = vec![0f32; l.inputs * l.outputs];
                for o in 0..l.outputs {
                    for i in 0..l.inputs {
                        t[i * l.outputs + o] = l.weights[o * l.inputs + i];
                    }
                }
                (l.inputs, l.outputs, t, l.biases.clone())
            }).collect(),
        }
    }

    /// Plays the network's strategy for `policy` at a decision whose row has no positive mass. The
    /// network reads the real table's observation, as it trained, and the policy draws its usual
    /// single random number. Returns the action, the label probabilities and the chosen label.
    /// The paired arena (#469) and the decision service both call this.
    pub fn play(&self, policy: &mut Policy, observation: &Observation<'_>, tables: &EquityTables) -> Result<(Action, [f64; ACTIONS], u8), String> {
        let (p, by_label) = self.distribution(observation, tables)?;
        let action = policy.choose_distribution(observation, &p)?;
        let chosen = menu(observation).iter().find(|(_, a)| *a == action).map(|(l, _)| *l).ok_or("network action off the menu")?;
        Ok((action, by_label, chosen))
    }
}

/// Regret matching over the legal labels: positive regrets in proportion; with none positive, the
/// legal label of highest regret (the first on ties), as in Deep CFR.
pub fn regret_match(regrets: &[f64; ACTIONS], legal: u8) -> [f64; ACTIONS] {
    let legal_labels = (0..ACTIONS).filter(|a| legal >> a & 1 == 1);
    let total: f64 = legal_labels.clone().map(|a| regrets[a].max(0.)).sum();
    let mut p = [0.; ACTIONS];
    if total > 0. {
        for a in legal_labels {
            p[a] = regrets[a].max(0.) / total;
        }
    } else {
        let best = legal_labels.fold(None, |b: Option<usize>, a| match b {
            Some(b) if regrets[b] >= regrets[a] => Some(b),
            _ => Some(a),
        });
        p[best.expect("no legal label")] = 1.;
    }
    p
}

/// An f32 forward pass for traversals: input-major weights, zero inputs skipped. It agrees with the
/// f64 reference to float32 rounding (checked by tests and `nplayer_deep_cfr bench`).
///
/// Every output is its bias plus the products of the nonzero inputs, added in input order. The
/// order is part of the contract: traversal records are compared byte for byte across builds, so
/// the kernel may change how it schedules the work but never which additions it makes or their
/// order. That rules out fused multiply-adds and reordered sums, which round differently.
pub struct Fast {
    pub output: Output,
    layers: Vec<(usize, usize, Vec<f32>, Vec<f32>)>,
}

/// Working memory for `Fast`, reused across calls.
#[derive(Default)]
pub struct Scratch {
    x: Vec<f32>,
    y: Vec<f32>,
    /// Each row's nonzero inputs as (index, value), rows back to back; `starts` delimits them.
    nonzero: Vec<(u32, f32)>,
    starts: Vec<usize>,
    /// The same nonzeros by input, as (row, value), for batches; `column_starts` delimits them.
    columns: Vec<(u32, f32)>,
    column_starts: Vec<usize>,
}

/// Outputs per register block: their partial sums stay in registers while the inputs stream past.
/// Sixteen vector registers of four (NEON) or eight (AVX) lanes hold 64; SSE2's sixteen of four
/// hold 32 with room for the products. The width changes the schedule, never the sums.
#[cfg(any(target_arch = "aarch64", target_feature = "avx"))]
const BLOCK: usize = 64;
#[cfg(not(any(target_arch = "aarch64", target_feature = "avx")))]
const BLOCK: usize = 32;
/// Outputs per block in a batch: one block of an input's weights sits in registers while it is
/// added to every row where that input is nonzero, and the batch's partial sums stay in L1.
const BATCH_BLOCK: usize = 32;
/// From this many rows, a batch walks its inputs once per block (`BATCH_BLOCK`) instead of once
/// per row; below it, rows share too few nonzero inputs for that to pay.
const BATCH_ROWS: usize = 4;

impl Fast {
    /// Logits (or regrets) for one quantized feature vector, `bytes[i] / 255`.
    pub fn logits(&self, bytes: &[u8], scratch: &mut Scratch) -> [f32; ACTIONS] {
        let mut out = [[0f32; ACTIONS]];
        self.forward(&[bytes], scratch, &mut out);
        out[0]
    }
    /// `logits` for several inputs at once, bit for bit (the sums are the same). One block of a
    /// layer's weights is read once for the whole batch, which is what limits a 2M network on
    /// many threads, whose weights don't fit in a core's cache.
    pub fn logits_batch(&self, inputs: &[&[u8]], scratch: &mut Scratch, out: &mut Vec<[f32; ACTIONS]>) {
        out.clear();
        out.resize(inputs.len(), [0.; ACTIONS]);
        self.forward(inputs, scratch, out);
    }
    fn forward(&self, inputs: &[&[u8]], scratch: &mut Scratch, out: &mut [[f32; ACTIONS]]) {
        let n = inputs.len();
        let Scratch { x, y, nonzero, starts, columns, column_starts } = scratch;
        x.clear();
        for bytes in inputs {
            x.extend(bytes.iter().map(|&b| b as f32 / 255.));
        }
        let last = self.layers.len() - 1;
        for (k, (width, outputs, t, b)) in self.layers.iter().enumerate() {
            let (width, outputs) = (*width, *outputs);
            debug_assert_eq!(x.len(), n * width);
            nonzero.clear();
            starts.clear();
            starts.push(0);
            for row in x.chunks_exact(width) {
                nonzero.extend(row.iter().enumerate().filter(|(_, &v)| v != 0.).map(|(i, &v)| (i as u32, v)));
                starts.push(nonzero.len());
            }
            y.clear();
            y.resize(n * outputs, 0.);
            let blocked = if n >= BATCH_ROWS {
                // By input: each row still adds its own nonzero inputs in increasing order.
                column_starts.clear();
                column_starts.resize(width + 1, 0);
                for &(i, _) in nonzero.iter() {
                    column_starts[i as usize + 1] += 1;
                }
                for i in 0..width {
                    column_starts[i + 1] += column_starts[i];
                }
                columns.clear();
                columns.resize(nonzero.len(), (0, 0.));
                let mut fill = column_starts[..width].to_vec();
                for r in 0..n {
                    for &(i, v) in &nonzero[starts[r]..starts[r + 1]] {
                        columns[fill[i as usize]] = (r as u32, v);
                        fill[i as usize] += 1;
                    }
                }
                let blocked = outputs / BATCH_BLOCK * BATCH_BLOCK;
                for o in (0..blocked).step_by(BATCH_BLOCK) {
                    for r in 0..n {
                        y[r * outputs + o..][..BATCH_BLOCK].copy_from_slice(&b[o..o + BATCH_BLOCK]);
                    }
                    for i in 0..width {
                        let column = &columns[column_starts[i]..column_starts[i + 1]];
                        if column.is_empty() {
                            continue;
                        }
                        let w: [f32; BATCH_BLOCK] = t[i * outputs + o..][..BATCH_BLOCK].try_into().unwrap();
                        for &(r, v) in column {
                            let acc: &mut [f32; BATCH_BLOCK] = (&mut y[r as usize * outputs + o..][..BATCH_BLOCK]).try_into().unwrap();
                            for j in 0..BATCH_BLOCK {
                                acc[j] += v * w[j];
                            }
                        }
                    }
                }
                blocked
            } else {
                outputs / BLOCK * BLOCK
            };
            for o in (0..if n >= BATCH_ROWS { 0 } else { blocked }).step_by(BLOCK) {
                for r in 0..n {
                    let mut acc: [f32; BLOCK] = b[o..o + BLOCK].try_into().unwrap();
                    for &(i, v) in &nonzero[starts[r]..starts[r + 1]] {
                        let w: &[f32; BLOCK] = t[i as usize * outputs + o..][..BLOCK].try_into().unwrap();
                        for j in 0..BLOCK {
                            acc[j] += v * w[j];
                        }
                    }
                    y[r * outputs + o..][..BLOCK].copy_from_slice(&acc);
                }
            }
            for o in blocked..outputs {
                for r in 0..n {
                    let mut acc = b[o];
                    for &(i, v) in &nonzero[starts[r]..starts[r + 1]] {
                        acc += v * t[i as usize * outputs + o];
                    }
                    y[r * outputs + o] = acc;
                }
            }
            if k < last {
                for v in y.iter_mut() {
                    *v = v.max(0.);
                }
            }
            std::mem::swap(x, y);
        }
        for (o, row) in out.iter_mut().zip(x.chunks_exact(ACTIONS)) {
            o.copy_from_slice(row);
        }
    }
    /// The strategy over the six labels at a decision with legal labels `legal`.
    pub fn strategy(&self, bytes: &[u8], legal: u8, scratch: &mut Scratch) -> [f64; ACTIONS] {
        self.strategy_of(self.logits(bytes, scratch), legal)
    }
    /// The strategy for given network outputs (from `logits` or `logits_batch`).
    pub fn strategy_of(&self, logits: [f32; ACTIONS], legal: u8) -> [f64; ACTIONS] {
        let z = logits.map(|v| v as f64);
        match self.output {
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
    fn the_fast_path_agrees_with_the_reference() {
        use rand::{Rng, SeedableRng};
        let mut rng = rand::rngs::StdRng::seed_from_u64(7);
        let weights: Vec<f32> = (0..features::len() * 32 + 32 + 32 * 16 + 16 + 16 * ACTIONS + ACTIONS).map(|_| rng.gen_range(-0.2..0.2)).collect();
        let f = file(&[32, 16, ACTIONS], |k, i| {
            let n = features::len();
            let offset = [0, n * 32 + 32, n * 32 + 32 + 32 * 16 + 16][k];
            weights[offset + i]
        });
        let net = PolicyNetwork::parse(&f).unwrap();
        let fast = net.fast();
        let mut scratch = Scratch::default();
        for _ in 0..200 {
            let bytes: Vec<u8> = (0..features::len()).map(|_| if rng.gen_bool(0.7) { 0 } else { rng.gen() }).collect();
            let x: Vec<f32> = bytes.iter().map(|&b| b as f32 / 255.).collect();
            let reference = net.logits(&x).unwrap();
            let got = fast.logits(&bytes, &mut scratch);
            for a in 0..ACTIONS {
                assert!((reference[a] - got[a] as f64).abs() < 1e-4, "{a}: {} vs {}", reference[a], got[a]);
            }
            let legal = rng.gen_range(1..64u8);
            let p = net.label_probabilities(&x, legal).unwrap();
            let q = fast.strategy(&bytes, legal, &mut scratch);
            for a in 0..ACTIONS {
                assert!((p[a] - q[a]).abs() < 1e-4);
            }
        }
    }


    /// PR477's kernel (one input at a time, each nonzero input adding its whole weight row): the
    /// bit-exact oracle for `Fast`.
    fn axpy_logits(net: &PolicyNetwork, bytes: &[u8]) -> [f32; ACTIONS] {
        let fast = net.fast();
        let mut x: Vec<f32> = bytes.iter().map(|&b| b as f32 / 255.).collect();
        let last = fast.layers.len() - 1;
        for (k, (_, outputs, t, b)) in fast.layers.iter().enumerate() {
            let mut y = b.clone();
            for (i, &v) in x.iter().enumerate() {
                if v != 0. {
                    for (acc, w) in y.iter_mut().zip(&t[i * outputs..(i + 1) * outputs]) {
                        *acc += v * w;
                    }
                }
            }
            if k < last {
                for v in y.iter_mut() {
                    *v = v.max(0.);
                }
            }
            x = y;
        }
        x[..ACTIONS].try_into().unwrap()
    }

    #[test]
    fn batched_forward_passes_equal_single_ones_bit_for_bit() {
        use rand::{Rng, SeedableRng};
        // Wider than one output tile, weights leaning negative so hidden layers have many ReLU zeros.
        let widths = [300, 520, ACTIONS];
        let f = file(&widths, |k, i| ((i as u64 * 2_654_435_761 + k as u64 * 97) % 1000) as f32 / 1000. * 0.18 - 0.1);
        let net = PolicyNetwork::parse(&f).unwrap();
        let fast = net.fast();
        let mut rng = rand::rngs::StdRng::seed_from_u64(12);
        let inputs: Vec<Vec<u8>> = (0..90).map(|k| (0..features::len()).map(|_| match k % 3 {
            0 => 0,
            _ if rng.gen_bool(0.8) => 0,
            _ => rng.gen(),
        }).collect()).collect();
        let mut scratch = Scratch::default();
        let single: Vec<[f32; ACTIONS]> = inputs.iter().map(|b| fast.logits(b, &mut scratch)).collect();
        for (b, s) in inputs.iter().zip(&single) {
            assert_eq!(s.map(f32::to_bits), axpy_logits(&net, b).map(f32::to_bits), "the old kernel's sums");
        }
        let mut out = Vec::new();
        for n in [1, 2, 5, 32, 90] {
            for (c, chunk) in inputs.chunks(n).enumerate() {
                let refs: Vec<&[u8]> = chunk.iter().map(Vec::as_slice).collect();
                fast.logits_batch(&refs, &mut scratch, &mut out);
                assert_eq!(out.len(), chunk.len());
                for (j, o) in out.iter().enumerate() {
                    assert_eq!(o.map(f32::to_bits), single[c * n + j].map(f32::to_bits), "batch {n}");
                }
            }
        }
    }

    #[test]
    fn advantage_networks_play_regret_matching() {
        assert_eq!(regret_match(&[1., -2., 3., 0., 0., 0.], 0b000111), [0.25, 0., 0.75, 0., 0., 0.]);
        assert_eq!(regret_match(&[1., -2., 3., 0., 0., 0.], 0b000010), [0., 1., 0., 0., 0., 0.]);
        assert_eq!(regret_match(&[-1., -2., -0.5, 9., 0., 0.], 0b000111), [0., 0., 1., 0., 0., 0.], "highest when none positive");
        assert_eq!(regret_match(&[-1., -1., -3., 0., 0., 0.], 0b000011), [1., 0., 0., 0., 0., 0.], "first on ties");
        let mut f = file(&[ACTIONS], |_, i| if i >= features::len() * ACTIONS { (i - features::len() * ACTIONS) as f32 - 2. } else { 0. });
        // Rebuild the header with the advantage kind.
        let header_len = u64::from_le_bytes(f[8..16].try_into().unwrap()) as usize;
        let mut h: Value = serde_json::from_slice(&f[16..16 + header_len]).unwrap();
        h["output"] = json!("advantage-6");
        let hb = serde_json::to_vec(&h).unwrap();
        let body = f.split_off(16 + header_len);
        let mut g = MAGIC.to_vec();
        g.extend_from_slice(&(hb.len() as u64).to_le_bytes());
        g.extend_from_slice(&hb);
        g.extend_from_slice(&body);
        let net = PolicyNetwork::parse(&g).unwrap();
        assert_eq!(net.output, Output::Advantage);
        // Regrets are bias - 2: [-2, -1, 0, 1, 2, 3].
        let p = net.label_probabilities(&vec![0.; features::len()], 0b111111).unwrap();
        assert!((p[4] - 2. / 6.).abs() < 1e-12 && (p[5] - 0.5).abs() < 1e-12 && p[0] == 0.);
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
