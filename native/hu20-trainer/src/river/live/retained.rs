//! One-hand research session. Public replay selects a row; it never updates beliefs.
use super::*;
use sha2::{Digest, Sha256};
use std::{fs::File, io::Read, sync::Arc};

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn public(v: &Value) -> Value {
    let mut x = serde_json::Map::new();
    for key in [
        "format", "button", "board", "seat", "hole", "actions", "players", "legal",
    ] {
        x.insert(key.into(), v[key].clone());
    }
    Value::Object(x)
}
pub(super) fn profile_digest(profile: &[Vec<f64>]) -> String {
    let mut h = Sha256::new();
    for row in profile {
        h.update((row.len() as u64).to_le_bytes());
        for p in row {
            h.update(p.to_bits().to_le_bytes());
        }
    }
    format!("{:x}", h.finalize())
}

pub(super) struct Captured {
    root: PublicRoot,
    tree: Tree,
    pairs: Vec<[u8; 2]>,
    profile: Vec<Vec<f64>>,
    original: Value,
    metadata: Value,
    installed: bool,
}
impl Captured {
    fn snapshot(&self, model: &str) -> Value {
        json!({"format":"river-retained-profile-snapshot-v1","model_sha256":model,
            "observation":self.original,"binding":self.metadata,
            "installed_search":self.installed,"profile":self.profile})
    }

    fn restore(
        snapshot: &Value,
        model: &str,
        table: &PolicyTable,
        tables: &EquityTables,
    ) -> Result<Self, String> {
        fields(
            snapshot,
            &[
                "format",
                "model_sha256",
                "observation",
                "binding",
                "installed_search",
                "profile",
            ],
        )?;
        if snapshot["format"] != "river-retained-profile-snapshot-v1"
            || snapshot["model_sha256"] != model
        {
            return Err("saved profile format/model mismatch".into());
        }
        let original = &snapshot["observation"];
        let root = reconstruct(original, table.config())?;
        let cards: Vec<_> = (0..52).filter(|c| !root.board.contains(c)).collect();
        let pairs: Vec<_> = (0..cards.len())
            .flat_map(|i| (i + 1..cards.len()).map(move |j| (i, j)))
            .map(|(i, j)| [cards[i], cards[j]])
            .collect();
        let menu = SearchMenu::parse(original.get("search_menu"))?;
        let backend = exact::Backend::parse(original.get("belief_backend"))?;
        if backend == exact::Backend::Dense {
            return Err("saved profile backend unsupported".into());
        }
        let mut tree = Tree::new(&root.hand, root.live, menu, SUPPORTED_NODES);
        tree.compile(&mut root.hand.clone())?;
        let profile: Vec<Vec<f64>> =
            serde_json::from_value(snapshot["profile"].clone()).map_err(|e| e.to_string())?;
        if profile_digest(&profile)
            != snapshot["binding"]["profile_sha256"]
                .as_str()
                .ok_or("saved profile digest missing")?
        {
            return Err("saved profile digest mismatch".into());
        }
        let (weights, _) = likelihoods(&root, &pairs, |obs| blueprint_row(obs, table, tables))?;
        let mut solver = Solver::new(
            exact::make(&root, &pairs, &weights, tree.nodes.clone(), backend)?,
            vec![None; tree.nodes.len()],
        )?;
        let quality = solver.quality(&profile)?;
        let target = quality_target(original.get("target"), root.hand.pot() as f64 / 100.)?;
        let met = gains(&quality).iter().all(|g| *g <= target);
        let work = &snapshot["binding"]["work"];
        let sweeps = uint(&work["sweeps"])?;
        if sweeps == 0
            || sweeps > uint(&original["sweeps"])?
            || !array(&original["checkpoints"])?.contains(&json!(sweeps))
        {
            return Err("saved profile work mismatch".into());
        }
        let result = json!({"checkpoints":[{"target_met":met}],"algorithm":original["algorithm"],
            "law":{"law":if backend==exact::Backend::Prefix{exact::EXACT_LAW}else{LAW}},
            "sweeps":sweeps,"requested_sweeps":original["sweeps"],"target_bb":target});
        let cap = Self::new(root, tree, pairs, profile, original.clone(), &result)?;
        if cap.metadata != snapshot["binding"] || cap.installed != snapshot["installed_search"] {
            return Err("saved profile binding/quality mismatch".into());
        }
        Ok(cap)
    }

    pub(super) fn new(
        root: PublicRoot,
        tree: Tree,
        pairs: Vec<[u8; 2]>,
        profile: Vec<Vec<f64>>,
        original: Value,
        result: &Value,
    ) -> Result<Self, String> {
        if profile.iter().flatten().any(|p| !p.is_finite() || *p < 0.) {
            return Err("nonfinite or negative retained profile".into());
        }
        let installed = result["checkpoints"]
            .as_array()
            .and_then(|a| a.last())
            .and_then(|c| c["target_met"].as_bool())
            .ok_or("missing retained quality")?;
        let bytes: usize = profile.iter().map(|r| r.len() * 8).sum::<usize>()
            + tree
                .paths
                .iter()
                .map(|p| p.len() * std::mem::size_of::<Action>())
                .sum::<usize>()
            + tree
                .menus
                .iter()
                .map(|p| p.len() * std::mem::size_of::<Action>())
                .sum::<usize>()
            + pairs.len() * 2;
        let metadata = json!({"root_sha256":digest(&serde_json::to_vec(&public(&original)).unwrap()),
            "profile_sha256":profile_digest(&profile), "search_menu":tree.menu.name(),
            "belief_law":result["law"]["law"],"algorithm":result["algorithm"],"work":{
                "requested_sweeps":result["requested_sweeps"],"sweeps":result["sweeps"],
                "target_bb":result["target_bb"],"checkpoints":original["checkpoints"]},
            "game":"three-player-100bb-50-100-v1", "production_menu":"min-pot-conditional-jam-v1",
            "cards":crate::cards::EQUITY_DESCRIPTOR,"k50_sha256":crate::cards::EQUITY_K50_SHA256,
            "retained_payload_bytes":bytes,
            "bytes_scope":"profile f64 payload, paths, menus and holding cards; excludes allocator/engine/JSON metadata"});
        Ok(Self {
            root,
            tree,
            pairs,
            profile,
            original,
            metadata,
            installed,
        })
    }
    fn replay(&self, v: &Value) -> Result<(Hand, Vec<Action>), String> {
        fields(
            v,
            &[
                "format", "button", "board", "seat", "hole", "actions", "players", "legal",
            ],
        )?;
        for key in ["format", "button", "board", "seat"] {
            if v[key] != self.original[key] {
                return Err(format!("retained {key} identity differs"));
            }
        }
        let h = array(&v["hole"])?;
        if h.len() != 2 {
            return Err("own holding required".into());
        }
        let mut hole = [card(&h[0])?, card(&h[1])?];
        hole.sort_unstable();
        if hole != self.root.hole {
            return Err("retained own holding differs".into());
        }
        let original = array(&self.original["actions"])?;
        let actions = array(&v["actions"])?;
        if actions.len() > 256 || !actions.starts_with(original) {
            return Err("retained history does not extend root".into());
        }
        let mut hand = self.root.hand.clone();
        let mut path = Vec::new();
        for e in &actions[original.len()..] {
            let a = array(e)?;
            if a.len() != 5
                || hand.street() != Street::River
                || hand.actor().is_none()
                || uint(&a[0])? as usize != hand.actor().unwrap()
                || uint(&a[1])? != Street::River as u64
            {
                return Err("invalid retained river actor/history".into());
            }
            let action = Action {
                kind: kind(&a[2])?,
                raise_to: uint(&a[3])?,
            };
            hand.apply_mut(action)?;
            let paid = hand.history().iter().rev().find_map(|e| match e {
                Event::Action { paid, .. } => Some(*paid),
                _ => None,
            });
            if paid != Some(uint(&a[4])?) {
                return Err("retained payment differs".into());
            }
            path.push(action);
        }
        if hand.actor() != Some(self.root.seat) || hand.finished() {
            return Err("retained acting hero required".into());
        }
        let players: Vec<_> = hand
            .players()
            .iter()
            .map(|p| json!([p.stack, p.street_bet, p.contributed, p.folded]))
            .collect();
        if v["players"] != json!(players) {
            return Err("retained player snapshot differs".into());
        }
        let legal = hand.legal().ok_or("retained legal actions missing")?;
        if v["legal"]
            != json!({"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to})
        {
            return Err("retained legal bounds differ".into());
        }
        Ok((hand, path))
    }
    fn row(&self, id: usize) -> Result<&[f64], String> {
        let hero = self
            .root
            .live
            .iter()
            .position(|s| *s == self.root.seat)
            .unwrap();
        match self.tree.nodes[id] {
            Node::Decision { actor, .. } if actor == hero => (),
            _ => return Err("retained profile actor differs".into()),
        }
        let holding = self
            .pairs
            .iter()
            .position(|h| *h == self.root.hole)
            .ok_or("retained holding missing")?;
        let k = self.tree.menus[id].len();
        self.profile[id]
            .get(holding * k..(holding + 1) * k)
            .ok_or("retained row shape differs".into())
    }
}

#[derive(Clone)]
struct Active {
    hand_id: String,
    handle: String,
    captured: Option<Arc<Captured>>,
    // The unsupported-zero-reach case still retains a validated public root.
    fallback_root: Option<Arc<Captured>>,
    last_actions: Vec<Value>,
    off_tree: bool,
    fallback_reason: Option<String>,
}

/// Single-owner session state. Opaque handles are transport metadata only.
/// First omitted public edge, including overlap between cap and all-in causes.
pub(super) fn first_off_tree(root: &Hand, tree: &Tree, path: &[Action]) -> Result<Value, String> {
    let mut before = root.clone();
    for (i, action) in path.iter().enumerate() {
        if !tree.paths.iter().any(|p| p == &path[..=i]) {
            let actor = before.actor().ok_or("off-tree actor missing")?;
            let player = &before.players()[actor];
            let raises = before
                .history()
                .iter()
                .filter(|e| {
                    matches!(e,
                Event::Action{street:Street::River,action,..} if action.kind==Kind::Raise)
                })
                .count();
            return Ok(
                json!({"path":path[..i].iter().map(|a|json!([a.kind.name(),a.raise_to])).collect::<Vec<_>>(),
                "actor":actor,"action":[action.kind.name(),action.raise_to],"raises_before":raises,
                "cap_reached":match tree.menu {SearchMenu::Capped(cap)=>raises>=cap,
                    SearchMenu::RootCheckMinOpen|SearchMenu::RootMinResponses=>raises>=3,SearchMenu::Full=>false},"all_in":action.kind==Kind::Raise&&action.raise_to==player.stack+player.street_bet}),
            );
        }
        before.apply_mut(*action)?;
    }
    Ok(Value::Null)
}

pub struct SessionStore {
    model: String,
    nonce: String,
    generation: u64,
    active: Option<Active>,
}
impl SessionStore {
    /// Offline counterfactual branch: immutable profile bytes are shared, while
    /// history progress and the sticky fallback latch belong to this copy.
    /// No solver work or action RNG is advanced by copying a validated session.
    pub fn evaluation_fork(&self) -> Self {
        Self {
            model: self.model.clone(),
            nonce: self.nonce.clone(),
            generation: self.generation,
            active: self.active.clone(),
        }
    }
    pub fn new(model: &str) -> Result<Self, String> {
        if model.len() != 64 || !model.bytes().all(|x| x.is_ascii_hexdigit()) {
            return Err("invalid verified model digest".into());
        }
        let mut nonce = [0u8; 32];
        File::open("/dev/urandom")
            .and_then(|mut f| f.read_exact(&mut nonce))
            .map_err(|e| e.to_string())?;
        Ok(Self {
            model: model.into(),
            nonce: digest(&nonce),
            generation: 0,
            active: None,
        })
    }
    fn check<'a>(&'a self, v: &Value) -> Result<&'a Active, String> {
        let a = self.active.as_ref().ok_or("no active retained hand")?;
        if v["handle"].as_str() != Some(&a.handle) || v["hand_id"].as_str() != Some(&a.hand_id) {
            return Err("stale retained handle or hand identity".into());
        }
        Ok(a)
    }
    pub fn request(
        &mut self,
        v: &Value,
        table: &PolicyTable,
        tables: &EquityTables,
    ) -> Result<Value, String> {
        match v["mode"].as_str() {
            Some("retained-begin") => {
                fields(v, &["mode", "hand_id", "observation"])?;
                if self.active.is_some() {
                    return Err("release the previous retained hand first".into());
                }
                let id = v["hand_id"]
                    .as_str()
                    .filter(|x| !x.is_empty() && x.len() <= 128)
                    .ok_or("public hand_id required")?;
                let observation = &v["observation"];
                if observation.get("mode").is_some_and(|m| m != "solve") {
                    return Err("retained begin requires solve".into());
                }
                let mut captured = None;
                let result = request_impl(observation, table, tables, Some(&mut captured));
                let (mut out, cap, reason) = match result {
                    Ok(out) => {
                        let cap = Arc::new(captured.ok_or("retained capture missing")?);
                        let reason = (!cap.installed)
                            .then(|| "declared-game quality target not met".to_string());
                        (out, cap, reason)
                    }
                    Err(e)
                        if e == "own holding has zero modeled root reach"
                            || e.starts_with("unsupported ") =>
                    {
                        let root = reconstruct(observation, table.config())?;
                        let mut obs = root.hand.observe(root.seat)?;
                        obs.hole = root.hole;
                        let (p, tag) = blueprint_row(&obs, table, tables)?;
                        let actions = multi_holdem::menu(&obs)
                            .iter()
                            .map(|(_, a)| json!([a.kind.name(), a.raise_to]))
                            .collect::<Vec<_>>();
                        let tree = Tree::new(
                            &root.hand,
                            root.live,
                            SearchMenu::parse(observation.get("search_menu"))?,
                            SUPPORTED_NODES,
                        );
                        let cap = Arc::new(Captured {
                            root,
                            tree,
                            pairs: Vec::new(),
                            profile: Vec::new(),
                            original: observation.clone(),
                            metadata: json!({"root_sha256":digest(&serde_json::to_vec(&public(observation)).unwrap()),
                                "profile_sha256":Value::Null,"retained_payload_bytes":0,"belief_law":LAW}),
                            installed: false,
                        });
                        (
                            json!({"probabilities":p,"actions":actions,"lookup_tag":tag}),
                            cap,
                            Some(e),
                        )
                    }
                    Err(e) => return Err(e),
                };
                out["produced_root_strategy"] = if cap.profile.is_empty() {
                    Value::Null
                } else {
                    json!({"actions":out["actions"],"probabilities":out["probabilities"]})
                };
                // Nonconverged root must play the actual blueprint, never its unconverged profile.
                if reason.is_some() {
                    let mut obs = cap.root.hand.observe(cap.root.seat)?;
                    obs.hole = cap.root.hole;
                    let (p, tag) = blueprint_row(&obs, table, tables)?;
                    out["probabilities"] = json!(p);
                    out["lookup_tag"] = json!(tag);
                    out["actions"] = json!(multi_holdem::menu(&obs)
                        .iter()
                        .map(|(_, a)| json!([a.kind.name(), a.raise_to]))
                        .collect::<Vec<_>>());
                }
                self.generation += 1;
                let handle = digest(format!("{}:{}", self.nonce, self.generation).as_bytes());
                self.active = Some(Active {
                    hand_id: id.into(),
                    handle: handle.clone(),
                    captured: cap.installed.then(|| cap.clone()),
                    fallback_root: (!cap.installed).then(|| cap.clone()),
                    last_actions: array(&observation["actions"])?.clone(),
                    off_tree: false,
                    fallback_reason: reason.clone(),
                });
                out["session"] = json!({"handle":handle,"hand_id":id,"model_sha256":self.model,"binding":cap.metadata,
                    "installed_search":cap.installed,"fallback_reason":reason});
                Ok(out)
            }
            Some("retained-continue") => {
                fields(v, &["mode", "hand_id", "handle", "observation"])?;
                let mut a = self.check(v)?.clone();
                let cap = a.captured.as_ref().or(a.fallback_root.as_ref()).unwrap();
                let observation = &v["observation"];
                let actions = array(&observation["actions"])?;
                if !actions.starts_with(&a.last_actions) {
                    return Err("retained history rollback or branch switch".into());
                }
                let (hand, path) = cap.replay(observation)?;
                let node = cap.tree.paths.iter().position(|p| *p == path);
                let mut off_tree_entry = Value::Null;
                // Repeated requests for the same public history must return the
                // same diagnostics, even after fallback has already latched.
                if node.is_none() && cap.installed {
                    off_tree_entry = first_off_tree(&cap.root.hand, &cap.tree, &path)?;
                }
                if node.is_none() && cap.installed {
                    a.off_tree = true;
                    a.fallback_reason = Some("off-tree action; blueprint for rest of river".into());
                }
                let (p, actions, tag) = if cap.installed && !a.off_tree {
                    let id = node.unwrap();
                    (cap.row(id)?.to_vec(), cap.tree.menus[id].clone(), None)
                } else {
                    let mut obs = hand.observe(cap.root.seat)?;
                    obs.hole = cap.root.hole;
                    let (p, tag) = blueprint_row(&obs, table, tables)?;
                    (
                        p,
                        multi_holdem::menu(&obs)
                            .into_iter()
                            .map(|(_, a)| a)
                            .collect(),
                        Some(tag),
                    )
                };
                a.last_actions = actions_json(observation)?;
                let out = json!({"probabilities":p,"actions":actions.iter().map(|a|json!([a.kind.name(),a.raise_to])).collect::<Vec<_>>(),
                    "installed_search":cap.installed&&!a.off_tree,"fallback_reason":a.fallback_reason,"lookup_tag":tag,
                    "profile_sha256":cap.metadata["profile_sha256"],"solver_advances":0,"off_tree_entry":off_tree_entry});
                self.active = Some(a);
                Ok(out)
            }
            Some("retained-audit") => {
                fields(v, &["mode", "hand_id", "handle"])?;
                let active = self.check(v)?.clone();
                let Some(cap) = active.captured.as_ref() else {
                    return Ok(
                        json!({"installed_search":false,"checked_rows":0,"solver_advances":0}),
                    );
                };
                let mut count = 0;
                let mut h = Sha256::new();
                let tick = Instant::now();
                for (i, path) in cap.tree.paths.iter().enumerate() {
                    if !matches!(cap.tree.nodes[i],Node::Decision{actor,..} if cap.root.live[actor]==cap.root.seat)
                    {
                        continue;
                    }
                    let obs = observation_after(cap, path)?;
                    // Each independent counterfactual path starts at the same validated root.
                    let mut store = SessionStore {
                        model: self.model.clone(),
                        nonce: self.nonce.clone(),
                        generation: self.generation,
                        active: Some(active.clone()),
                    };
                    let response=store.request(&json!({"mode":"retained-continue","handle":active.handle,"hand_id":active.hand_id,"observation":obs}),table,tables)?;
                    let p = response["probabilities"]
                        .as_array()
                        .ok_or("missing continuation row")?;
                    let expected = cap.row(i)?;
                    if p.len() != expected.len()
                        || p.iter()
                            .zip(expected)
                            .any(|(a, b)| a.as_f64().unwrap().to_bits() != b.to_bits())
                        || response["solver_advances"] != 0
                        || response["installed_search"] != true
                    {
                        return Err("retained original-profile equality failed".into());
                    }
                    h.update((i as u64).to_le_bytes());
                    for p in expected {
                        h.update(p.to_bits().to_le_bytes());
                    }
                    count += 1;
                }
                Ok(
                    json!({"installed_search":true,"checked_rows":count,"solver_advances":0,"rows_sha256":format!("{:x}",h.finalize()),
                    "seconds":tick.elapsed().as_secs_f64(),"profile_sha256":cap.metadata["profile_sha256"]}),
                )
            }
            Some("retained-export-profile") => {
                fields(v, &["mode", "hand_id", "handle"])?;
                let active = self.check(v)?;
                if active.off_tree {
                    return Err("export requires original retained root".into());
                }
                let cap = active
                    .captured
                    .as_ref()
                    .or(active.fallback_root.as_ref())
                    .unwrap();
                if cap.profile.is_empty() {
                    return Err("root has no saved solver profile".into());
                }
                Ok(cap.snapshot(&self.model))
            }
            Some("diagnose-saved-profile") => {
                fields(v, &["mode", "snapshot_path", "snapshot_sha256"])?;
                let path = std::path::Path::new(
                    v["snapshot_path"]
                        .as_str()
                        .ok_or("snapshot path required")?,
                );
                if !path.is_absolute() {
                    return Err("absolute saved profile path required".into());
                }
                let mut file = File::open(path).map_err(|e| e.to_string())?;
                let mut bytes = Vec::new();
                std::io::Read::by_ref(&mut file)
                    .take(16 * 1024 * 1024 + 1)
                    .read_to_end(&mut bytes)
                    .map_err(|e| e.to_string())?;
                if bytes.len() > 16 * 1024 * 1024 {
                    return Err("saved profile exceeds 16 MiB".into());
                }
                if digest(&bytes)
                    != v["snapshot_sha256"]
                        .as_str()
                        .ok_or("snapshot SHA256 required")?
                {
                    return Err("saved snapshot SHA256 mismatch".into());
                }
                let snapshot: Value = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
                let cap = Captured::restore(&snapshot, &self.model, table, tables)?;
                harms::diagnose(
                    &cap.root,
                    &cap.pairs,
                    &cap.tree,
                    &cap.profile,
                    cap.installed,
                    table,
                    tables,
                )
            }
            Some("retained-harm-diagnosis") => {
                // #384's fixed-profile response diagnosis, on the live retained
                // root rather than a saved snapshot. It never advances the solver.
                fields(v, &["mode", "hand_id", "handle"])?;
                let active = self.check(v)?;
                if active.off_tree {
                    return Err("harm diagnosis requires original retained root".into());
                }
                let cap = active
                    .captured
                    .as_ref()
                    .or(active.fallback_root.as_ref())
                    .unwrap();
                if cap.profile.is_empty() {
                    return Err("root has no saved solver profile".into());
                }
                harms::diagnose(
                    &cap.root,
                    &cap.pairs,
                    &cap.tree,
                    &cap.profile,
                    cap.installed,
                    table,
                    tables,
                )
            }
            Some("retained-full-menu-audit") => {
                fields(v, &["mode", "hand_id", "handle"])?;
                let active = self.check(v)?;
                let cap = active
                    .captured
                    .as_ref()
                    .or(active.fallback_root.as_ref())
                    .unwrap();
                if active.off_tree {
                    return Err("offline root audit requires original retained root".into());
                }
                exact::audit(
                    &cap.root,
                    &cap.pairs,
                    &cap.tree,
                    &cap.profile,
                    &cap.original,
                    cap.installed,
                    table,
                    tables,
                )
            }
            Some("retained-release") => {
                fields(v, &["mode", "hand_id", "handle"])?;
                self.check(v)?;
                self.active = None;
                Ok(json!({"released":true}))
            }
            _ => super::request(v, table, tables),
        }
    }
}
fn actions_json(v: &Value) -> Result<Vec<Value>, String> {
    Ok(array(&v["actions"])?.clone())
}
fn observation_after(cap: &Captured, path: &[Action]) -> Result<Value, String> {
    let mut hand = cap.root.hand.clone();
    let mut actions = array(&cap.original["actions"])?.clone();
    for a in path {
        let actor = hand.actor().ok_or("path after settlement")?;

        hand.apply_mut(*a)?;
        actions.push(json!([
            actor,
            Street::River as u64,
            a.kind.name(),
            a.raise_to,
            hand.history()
                .iter()
                .rev()
                .find_map(|e| match e {
                    Event::Action { paid, .. } => Some(*paid),
                    _ => None,
                })
                .unwrap()
        ]));
    }
    let legal = hand.legal().ok_or("path is terminal")?;
    Ok(
        json!({"format":"nplayer-live-river-v1","button":hand.button(),"board":cap.root.board,"seat":cap.root.seat,"hole":cap.root.hole,
        "actions":actions,"players":hand.players().iter().map(|p|json!([p.stack,p.street_bet,p.contributed,p.folded])).collect::<Vec<_>>(),
        "legal":{"check":legal.check,"call_amount":legal.call_amount,"raise_to":legal.raise_to}}),
    )
}

#[cfg(test)]
mod tests;
