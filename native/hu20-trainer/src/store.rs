//! The training table, stored compactly.
//!
//! A `HashMap<Key, Node>` spends 112 bytes on every slot, whatever the menu's length, and
//! leaves up to half its slots empty after each doubling: about 415 bytes per entry at HU100's
//! 39M-node peak. Here each shard keeps one record per entry in a segmented array of 8-byte
//! words, and a hash index of 32-bit record positions. A record is the entry's fixed fields
//! (4 words) followed by its regrets and its average at their actual length, so a lookup reads
//! the index and then one contiguous record.
//!
//! Keys stored only from opponent visits never receive regrets, which stay exactly +0.0, so their
//! records have no regret words. When an entry's first regret differs from +0.0 its record moves
//! to a longer one; the shorter record goes on a free list by length and is reused by the next
//! record of that length. A frozen table adds no keys, so once a shard's free records exceed both
//! `COMPACT_MIN` words (256 KiB) and 1/16 of its words, the shard rewrites its live records
//! contiguously; below that size the free records are bounded by `COMPACT_MIN` per shard
//! (16 MiB over all shards). Segments grow by fixed chunks,
//! so memory grows in proportion to entries instead of in doublings, and nothing is moved when a
//! shard grows.
//!
//! Both trainers use it. Each entry carries one opaque 32-bit `meta` (the HU discount stamp, the
//! n-player owner and street), and averages are optional for streets the n-player trainer does
//! not average.
//!
//! Shards split keys by their first byte, so sorting each shard and writing them in order
//! gives the checkpoint's sorted rows without sorting the whole table at once.

use crate::cfr::{Key, Lookup, Node, MAX_ACTIONS};
use crate::gz::Gzip;
use hashbrown::HashTable;
use rayon::prelude::*;

pub const SHARDS: usize = 64;
/// Checkpoint rows per parallel formatting piece.
const SAVE_PIECE: usize = 16_384;

/// Regrets of keys without stored ones: `Node::empty`'s.
static ZEROS: [f64; MAX_ACTIONS] = [0.0; MAX_ACTIONS];
/// The end of a free list.
const NONE: u32 = u32::MAX;
/// Words of a record's fixed fields: key (2), visits, then meta | code << 32 | len << 48 | flags << 56.
const HEAD: usize = 4;
/// The longest record.
const RECORD: usize = HEAD + 2 * MAX_ACTIONS;
const HAS_AVERAGE: u64 = 1 << 56;
const HAS_REGRETS: u64 = 1 << 57;

/// Fixed-size chunks, so growth never copies or doubles existing items.
struct Segments<T, const SHIFT: u32> {
    chunks: Vec<Vec<T>>,
}

/// Copies keep every chunk's full capacity, so a copy also grows without moving items.
impl<T: Copy, const SHIFT: u32> Clone for Segments<T, SHIFT> {
    fn clone(&self) -> Self {
        let mut chunks = Vec::with_capacity(self.chunks.capacity());
        for chunk in &self.chunks {
            let mut copy = Vec::with_capacity(Self::CHUNK);
            copy.extend_from_slice(chunk);
            chunks.push(copy);
        }
        Segments { chunks }
    }
}

impl<T: Copy, const SHIFT: u32> Segments<T, SHIFT> {
    const CHUNK: usize = 1 << SHIFT;

    fn new() -> Self {
        Segments { chunks: Vec::new() }
    }

    /// The position of `items`, kept contiguous inside one chunk.
    fn push(&mut self, items: &[T]) -> u32 {
        debug_assert!(items.len() <= Self::CHUNK);
        if self.chunks.last().map_or(true, |c| c.len() + items.len() > Self::CHUNK) {
            self.chunks.push(Vec::with_capacity(Self::CHUNK));
        }
        let chunk = self.chunks.len() - 1;
        let last = &mut self.chunks[chunk];
        let position = (chunk << SHIFT) + last.len();
        last.extend_from_slice(items);
        u32::try_from(position).expect("a table shard outgrew 32-bit positions")
    }

    fn get(&self, position: u32, len: usize) -> &[T] {
        let (chunk, offset) = ((position >> SHIFT) as usize, position as usize & (Self::CHUNK - 1));
        &self.chunks[chunk][offset..offset + len]
    }

    fn get_mut(&mut self, position: u32, len: usize) -> &mut [T] {
        let (chunk, offset) = ((position >> SHIFT) as usize, position as usize & (Self::CHUNK - 1));
        &mut self.chunks[chunk][offset..offset + len]
    }

    fn allocation_size(&self) -> usize {
        self.chunks.capacity() * std::mem::size_of::<Vec<T>>()
            + self.chunks.iter().map(|c| c.capacity() * std::mem::size_of::<T>()).sum::<usize>()
    }
}

/// Record words. Values are `f64`; the fixed fields are stored as `f64::from_bits` and read back
/// with `to_bits`, which round-trip every bit pattern since no arithmetic touches them.
type Words = Segments<f64, 15>;

/// Bytes of one entry's fixed fields.
pub const ENTRY_BYTES: usize = HEAD * 8;

/// Heap bytes the table owns, by part; `records` includes unused chunk capacity and free records.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Allocation {
    pub index: usize,
    pub records: usize,
}

impl Allocation {
    pub fn total(self) -> usize {
        self.index + self.records
    }
}

/// A stored entry, or one to store; `average` is `None` where none is kept.
#[derive(Clone, Copy, Debug)]
pub struct View<'a> {
    pub code: u16,
    pub meta: u32,
    pub visits: u64,
    pub regrets: &'a [f64],
    pub average: Option<&'a [f64]>,
}

/// Keys are uniform BLAKE2b digests; the bytes after the shard byte are the hash.
fn hash(key: &Key) -> u64 {
    u64::from_le_bytes(key[8..16].try_into().unwrap())
}

/// A record's fixed fields, decoded.
#[derive(Clone, Copy)]
struct Head {
    visits: u64,
    meta: u32,
    code: u16,
    len: usize,
    average: bool,
    regrets: bool,
}

impl Head {
    fn words(self) -> usize {
        HEAD + self.len * (self.average as usize + self.regrets as usize)
    }

    fn packed(self) -> f64 {
        let flags = if self.average { HAS_AVERAGE } else { 0 } | if self.regrets { HAS_REGRETS } else { 0 };
        f64::from_bits(self.meta as u64 | (self.code as u64) << 32 | (self.len as u64) << 48 | flags)
    }
}

/// A record laid out in a buffer before it is stored.
fn record(key: &Key, head: Head, regrets: &[f64], average: Option<&[f64]>) -> ([f64; RECORD], usize) {
    let mut words = [0.0; RECORD];
    words[0] = f64::from_bits(u64::from_le_bytes(key[..8].try_into().unwrap()));
    words[1] = f64::from_bits(hash(key));
    words[2] = f64::from_bits(head.visits);
    words[3] = head.packed();
    let mut at = HEAD;
    if head.regrets {
        words[at..at + head.len].copy_from_slice(regrets);
        at += head.len;
    }
    if let Some(a) = average {
        words[at..at + head.len].copy_from_slice(a);
        at += head.len;
    }
    debug_assert_eq!(at, head.words());
    (words, at)
}

/// Free words that trigger a compaction once they also exceed 1/16 of a shard's record words.
const COMPACT_MIN: usize = 1 << 15;

#[derive(Clone)]
pub struct Shard {
    index: HashTable<u32>,
    words: Words,
    /// The first free record of each length, chained through the records' first words.
    free: [u32; RECORD + 1],
    /// Words in free records, and words ever appended (free records included).
    free_words: usize,
    used_words: usize,
}

impl Shard {
    fn new() -> Shard {
        Shard { index: HashTable::new(), words: Segments::new(), free: [NONE; RECORD + 1], free_words: 0, used_words: 0 }
    }

    fn key(&self, p: u32) -> Key {
        let w = self.words.get(p, 2);
        let mut key = [0u8; 16];
        key[..8].copy_from_slice(&w[0].to_bits().to_le_bytes());
        key[8..].copy_from_slice(&w[1].to_bits().to_le_bytes());
        key
    }

    fn head(&self, p: u32) -> Head {
        let w = self.words.get(p, HEAD);
        let packed = w[3].to_bits();
        Head {
            visits: w[2].to_bits(),
            meta: packed as u32,
            code: (packed >> 32) as u16,
            len: (packed >> 48) as u8 as usize,
            average: packed & HAS_AVERAGE != 0,
            regrets: packed & HAS_REGRETS != 0,
        }
    }

    fn find(&self, key: &Key) -> Option<u32> {
        let words = &self.words;
        self.index.find(hash(key), |&p| {
            let w = words.get(p, 2);
            w[1].to_bits() == hash(key) && w[0].to_bits().to_le_bytes() == key[..8]
        }).copied()
    }

    fn view(&self, p: u32) -> View<'_> {
        let h = self.head(p);
        let regrets = if h.regrets { self.words.get(p + HEAD as u32, h.len) } else { &ZEROS[..h.len] };
        let average = h.average.then(|| self.words.get(p + (HEAD + if h.regrets { h.len } else { 0 }) as u32, h.len));
        View { code: h.code, meta: h.meta, visits: h.visits, regrets, average }
    }

    fn node(&self, p: u32) -> Node {
        let v = self.view(p);
        let n = v.regrets.len();
        let mut node = Node { stamp: v.meta, visits: v.visits, ..Node::empty(v.code, n) };
        node.regrets[..n].copy_from_slice(v.regrets);
        node.average[..n].copy_from_slice(v.average.expect("HU entries keep averages"));
        node
    }

    /// Stores `words`, reusing a free record of the same length when there is one.
    fn allocate(&mut self, words: &[f64]) -> u32 {
        let head = self.free[words.len()];
        if head == NONE {
            self.used_words += words.len();
            return self.words.push(words);
        }
        let slot = self.words.get_mut(head, words.len());
        self.free[words.len()] = slot[0].to_bits() as u32;
        slot.copy_from_slice(words);
        self.free_words -= words.len();
        head
    }

    fn release(&mut self, p: u32, len: usize) {
        self.words.get_mut(p, 1)[0] = f64::from_bits(self.free[len] as u64);
        self.free[len] = p;
        self.free_words += len;
    }

    /// Rewrites every live record contiguously, in position order, and drops the free lists:
    /// a frozen table adds no keys, so nothing else reuses the records left by moves.
    /// Returns the new position of the record at `keep`.
    fn compact(&mut self, keep: u32) -> u32 {
        let mut old: Vec<u32> = self.index.iter().copied().collect();
        old.sort_unstable();
        let mut words = Words::new();
        let mut used = 0;
        let new: Vec<u32> = old.iter().map(|&p| {
            let len = self.head(p).words();
            used += len;
            words.push(self.words.get(p, len))
        }).collect();
        let moved = |p: u32| new[old.binary_search(&p).expect("indexed record")];
        for p in self.index.iter_mut() {
            *p = moved(*p);
        }
        let keep = moved(keep);
        self.used_words = used;
        self.words = words;
        self.free = [NONE; RECORD + 1];
        self.free_words = 0;
        keep
    }

    /// Stores a new entry; regret words only when some regret differs from +0.0.
    fn add(&mut self, key: Key, entry: View) -> u32 {
        let n = entry.regrets.len();
        debug_assert!((1..=MAX_ACTIONS).contains(&n) && entry.average.map_or(true, |a| a.len() == n));
        let head = Head { visits: entry.visits, meta: entry.meta, code: entry.code, len: n, average: entry.average.is_some(),
            regrets: entry.regrets.iter().any(|r| r.to_bits() != 0) };
        let (words, len) = record(&key, head, entry.regrets, entry.average);
        let p = self.allocate(&words[..len]);
        let all = &self.words;
        self.index.insert_unique(hash(&key), p, |&q| all.get(q, 2)[1].to_bits());
        p
    }

    fn add_node(&mut self, key: Key, node: &Node) -> u32 {
        let n = node.len as usize;
        self.add(key, View { code: node.code, meta: node.stamp, visits: node.visits, regrets: &node.regrets[..n], average: Some(&node.average[..n]) })
    }

    /// Writes the regrets of the entry at `p`, moving it to a record with regret words once one
    /// differs from +0.0, and returns its position.
    fn set_regrets(&mut self, p: u32, regrets: &[f64]) -> u32 {
        let h = self.head(p);
        if h.regrets {
            self.words.get_mut(p + HEAD as u32, h.len).copy_from_slice(regrets);
            return p;
        }
        if regrets.iter().all(|r| r.to_bits() == 0) {
            return p;
        }
        let key = self.key(p);
        let average = self.view(p).average.map(|a| {
            let mut copy = [0.0; MAX_ACTIONS];
            copy[..a.len()].copy_from_slice(a);
            copy
        });
        let (words, len) = record(&key, Head { regrets: true, ..h }, regrets, average.as_ref().map(|a| &a[..h.len]));
        self.release(p, h.words());
        let q = self.allocate(&words[..len]);
        *self.index.find_mut(hash(&key), |&r| r == p).expect("indexed") = q;
        if self.free_words >= COMPACT_MIN && self.free_words * 16 > self.used_words {
            return self.compact(q);
        }
        q
    }

    fn set_head(&mut self, p: u32, visits: u64, meta: u32) {
        let h = Head { visits, meta, ..self.head(p) };
        let w = self.words.get_mut(p, HEAD);
        w[2] = f64::from_bits(visits);
        w[3] = h.packed();
    }

    fn store(&mut self, p: u32, node: &Node) {
        let h = self.head(p);
        let n = h.len;
        debug_assert!(node.code == h.code && node.len as usize == n);
        let at = p + (HEAD + if h.regrets { n } else { 0 }) as u32;
        self.words.get_mut(at, n).copy_from_slice(&node.average[..n]);
        let p = self.set_regrets(p, &node.regrets[..n]);
        self.set_head(p, node.visits, node.stamp);
    }

    /// Applies `update` to `key`'s node, created as `fresh` when the key is new.
    pub fn update(&mut self, key: Key, fresh: impl FnOnce() -> Node, update: impl FnOnce(&mut Node)) {
        let (p, mut node) = match self.find(&key) {
            Some(p) => (p, self.node(p)),
            None => {
                let node = fresh();
                (self.add_node(key, &node), node)
            }
        };
        update(&mut node);
        self.store(p, &node);
    }

    /// Adds `delta`'s regrets, averages and visits to `key`'s entry, or stores `delta` as it is
    /// when the key is new.
    pub fn merge(&mut self, key: Key, delta: View) {
        let Some(p) = self.find(&key) else {
            self.add(key, delta);
            return;
        };
        let h = self.head(p);
        let n = h.len;
        assert_eq!((h.code, n, h.meta, h.average), (delta.code, delta.regrets.len(), delta.meta, delta.average.is_some()),
            "a merged entry changed its menu, meta or average scope");
        let mut regrets = [0.0; MAX_ACTIONS];
        for ((sum, stored), inc) in regrets.iter_mut().zip(self.view(p).regrets).zip(delta.regrets) {
            *sum = stored + inc;
            assert!(sum.is_finite());
        }
        if let Some(increments) = delta.average {
            let at = p + (HEAD + if h.regrets { n } else { 0 }) as u32;
            for (sum, inc) in self.words.get_mut(at, n).iter_mut().zip(increments) {
                *sum += inc;
                assert!(sum.is_finite());
            }
        }
        let p = self.set_regrets(p, &regrets[..n]);
        self.set_head(p, h.visits + delta.visits, h.meta);
    }

    pub fn contains(&self, key: &Key) -> bool {
        self.find(key).is_some()
    }

    pub fn len(&self) -> usize {
        self.index.len()
    }

    pub fn allocation(&self) -> Allocation {
        Allocation { index: self.index.allocation_size(), records: self.words.allocation_size() }
    }

    /// Bytes of stored regrets and stored averages.
    pub fn payload_bytes(&self) -> (usize, usize) {
        self.index.iter().fold((0, 0), |(regrets, average), &p| {
            let h = self.head(p);
            let bytes = h.len * 8;
            (regrets + if h.regrets { bytes } else { 0 }, average + if h.average { bytes } else { 0 })
        })
    }

    /// Record positions in key order; 4 bytes per entry, since every shard's order is alive while saving.
    pub fn order(&self) -> Vec<u32> {
        let mut order: Vec<u32> = self.index.iter().copied().collect();
        order.sort_unstable_by(|&a, &b| self.key(a).cmp(&self.key(b)));
        order
    }

    /// The key and node at a position from `order`.
    pub fn row(&self, p: u32) -> (Key, Node) {
        (self.key(p), self.node(p))
    }

    /// The key and entry at a position from `order`.
    pub fn row_view(&self, p: u32) -> (Key, View<'_>) {
        (self.key(p), self.view(p))
    }

    /// Entries in key order.
    fn sorted(&self) -> impl Iterator<Item = (Key, Node)> + '_ {
        self.order().into_iter().map(move |p| self.row(p))
    }

    fn sorted_views(&self) -> impl Iterator<Item = (Key, View<'_>)> + '_ {
        self.order().into_iter().map(move |p| self.row_view(p))
    }
}

/// The table, split by key so deltas merge and apply in parallel.
#[derive(Clone)]
pub struct Store(pub Vec<Shard>);

impl Store {
    pub fn new() -> Store {
        Store((0..SHARDS).map(|_| Shard::new()).collect())
    }

    pub fn shard(key: &Key) -> usize {
        key[0] as usize * SHARDS / 256
    }

    pub fn len(&self) -> usize {
        self.0.iter().map(Shard::len).sum()
    }

    pub fn get(&self, key: &Key) -> Option<Node> {
        let shard = &self.0[Self::shard(key)];
        shard.find(key).map(|p| shard.node(p))
    }

    pub fn view(&self, key: &Key) -> Option<View<'_>> {
        let shard = &self.0[Self::shard(key)];
        shard.find(key).map(|p| shard.view(p))
    }

    pub fn contains(&self, key: &Key) -> bool {
        self.0[Self::shard(key)].contains(key)
    }

    /// Adds a new key's node; false if the key is already stored.
    pub fn insert(&mut self, key: Key, node: Node) -> bool {
        let shard = &mut self.0[Self::shard(&key)];
        if shard.find(&key).is_some() {
            return false;
        }
        shard.add_node(key, &node);
        true
    }

    /// Adds a new key's entry; false if the key is already stored.
    pub fn insert_view(&mut self, key: Key, entry: View) -> bool {
        let shard = &mut self.0[Self::shard(&key)];
        if shard.find(&key).is_some() {
            return false;
        }
        shard.add(key, entry);
        true
    }

    pub fn merge(&mut self, key: Key, delta: View) {
        self.0[Self::shard(&key)].merge(key, delta);
    }

    /// Heap bytes the shards own.
    pub fn allocation(&self) -> Allocation {
        self.0.iter().map(Shard::allocation).fold(Allocation::default(), |a, b| Allocation {
            index: a.index + b.index,
            records: a.records + b.records,
        })
    }

    pub fn payload_bytes(&self) -> (usize, usize) {
        self.0.iter().map(Shard::payload_bytes).fold((0, 0), |a, b| (a.0 + b.0, a.1 + b.1))
    }

    /// Entries the hash indexes hold before they grow.
    pub fn index_capacity(&self) -> usize {
        self.0.iter().map(|s| s.index.capacity()).sum()
    }

    /// Every entry, in no particular order.
    pub fn iter(&self) -> impl Iterator<Item = (Key, Node)> + '_ {
        self.0.iter().flat_map(|s| s.index.iter().map(move |&p| s.row(p)))
    }

    /// Every entry in key order, sorting one shard at a time.
    pub fn sorted(&self) -> impl Iterator<Item = (Key, Node)> + '_ {
        self.0.iter().flat_map(Shard::sorted)
    }

    pub fn views(&self) -> impl Iterator<Item = (Key, View<'_>)> + '_ {
        self.0.iter().flat_map(|s| s.index.iter().map(move |&p| s.row_view(p)))
    }

    pub fn sorted_views(&self) -> impl Iterator<Item = (Key, View<'_>)> + '_ {
        self.0.iter().flat_map(Shard::sorted_views)
    }

    /// `head`, then one `row` per entry in key order: shards sorted and rows formatted in parallel.
    pub fn write_sorted(&self, file: std::fs::File, gzip: Gzip, head: &[u8],
                        row: impl Fn(&Shard, u32, &mut Vec<u8>) + Sync) -> std::io::Result<std::fs::File> {
        let orders: Vec<Vec<u32>> = self.0.par_iter().map(Shard::order).collect();
        let pieces: Vec<(usize, std::ops::Range<usize>)> = orders.iter().enumerate()
            .flat_map(|(s, order)| (0..order.len()).step_by(SAVE_PIECE).map(move |i| (s, i..(i + SAVE_PIECE).min(order.len()))))
            .collect();
        crate::gz::write_ordered(file, gzip, head, &pieces, |(s, range), out| {
            for &p in &orders[*s][range.clone()] {
                row(&self.0[*s], p, out);
            }
        })
    }
}

impl Default for Store {
    fn default() -> Store {
        Store::new()
    }
}

impl Lookup for Store {
    fn regrets(&self, key: &Key) -> Option<(u16, &[f64])> {
        let shard = &self.0[Self::shard(key)];
        shard.find(key).map(|p| {
            let v = shard.view(p);
            (v.code, v.regrets)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn node(code: u16, len: usize, regrets: &[f64], average: &[f64], visits: u64) -> Node {
        let mut node = Node { visits, ..Node::empty(code, len) };
        node.regrets[..len].copy_from_slice(regrets);
        node.average[..len].copy_from_slice(average);
        node
    }

    fn bits(node: &Node) -> (u16, u8, Vec<u64>, Vec<u64>, u64, u32) {
        let n = node.len as usize;
        (node.code, node.len, node.regrets[..n].iter().map(|v| v.to_bits()).collect(),
         node.average[..n].iter().map(|v| v.to_bits()).collect(), node.visits, node.stamp)
    }

    fn view_bits(v: View) -> (u16, u32, u64, Vec<u64>, Option<Vec<u64>>) {
        (v.code, v.meta, v.visits, v.regrets.iter().map(|r| r.to_bits()).collect(),
         v.average.map(|a| a.iter().map(|x| x.to_bits()).collect()))
    }

    fn has_regrets(store: &Store, key: &Key) -> bool {
        let shard = &store.0[Store::shard(key)];
        shard.head(shard.find(key).unwrap()).regrets
    }

    #[test]
    fn stores_nodes_exactly_and_allocates_regrets_only_when_needed() {
        let mut store = Store::new();
        let opponent = node(0b110, 2, &[0.0, 0.0], &[3.5, 1.0], 0);
        let negative_zero = node(0b11, 2, &[-0.0, 0.0], &[0.0, 0.0], 1);
        assert!(store.insert([1; 16], opponent));
        assert!(store.insert([2; 16], negative_zero));
        assert!(!store.insert([1; 16], opponent), "duplicate keys are rejected");
        assert_eq!(bits(&store.get(&[1; 16]).unwrap()), bits(&opponent));
        assert_eq!(bits(&store.get(&[2; 16]).unwrap()), bits(&negative_zero), "-0.0 keeps its sign");
        assert!(!has_regrets(&store, &[1; 16]) && has_regrets(&store, &[2; 16]));
        let (code, regrets) = store.regrets(&[1; 16]).unwrap();
        assert_eq!((code, regrets.len()), (0b110, 2));
        // A first traverser visit gives an opponent-only key its regret storage.
        let shard = &mut store.0[Store::shard(&[1; 16])];
        shard.update([1; 16], || unreachable!(), |n| { n.regrets[1] = -2.25; n.visits = 1; n.stamp = 7; });
        let expected = node(0b110, 2, &[0.0, -2.25], &[3.5, 1.0], 1);
        assert_eq!(bits(&store.get(&[1; 16]).unwrap()), bits(&Node { stamp: 7, ..expected }));
        assert!(has_regrets(&store, &[1; 16]));
        assert!(store.get(&[3; 16]).is_none() && store.regrets(&[3; 16]).is_none());
    }

    #[test]
    fn merge_adds_exactly_and_keeps_absent_averages_absent() {
        let mut store = Store::new();
        let delta = |regrets: &'static [f64], average: Option<&'static [f64]>, visits| View { code: 0b111, meta: 0x0201, visits, regrets, average };
        // New keys are stored as given, including -0.0.
        store.merge([5; 16], delta(&[-0.0, 0.0, 0.0], None, 0));
        assert_eq!(view_bits(store.view(&[5; 16]).unwrap()), view_bits(delta(&[-0.0, 0.0, 0.0], None, 0)));
        // +0.0 regrets keep no storage until a sum differs from +0.0.
        store.merge([6; 16], delta(&[0.0, 0.0, 0.0], Some(&[1.0, 0.5, 0.0]), 0));
        assert!(!has_regrets(&store, &[6; 16]));
        store.merge([6; 16], delta(&[0.0, -0.0, 0.0], Some(&[0.25, 0.0, 2.0]), 0));
        assert!(!has_regrets(&store, &[6; 16]), "+0.0 + -0.0 is +0.0");
        store.merge([6; 16], delta(&[1.5, -2.0, 0.0], Some(&[0.0, 0.0, 0.0]), 1));
        assert!(has_regrets(&store, &[6; 16]));
        store.merge([6; 16], delta(&[0.25, 0.0, 3.0], Some(&[1.0, 1.0, 1.0]), 2));
        assert_eq!(view_bits(store.view(&[6; 16]).unwrap()),
            view_bits(delta(&[1.75, -2.0, 3.0], Some(&[2.25, 1.5, 3.0]), 3)));
        // Entries without averages move too.
        store.merge([5; 16], delta(&[0.5, 0.0, 0.0], None, 4));
        assert_eq!(view_bits(store.view(&[5; 16]).unwrap()), view_bits(delta(&[0.5, 0.0, 0.0], None, 4)));
    }

    #[test]
    #[should_panic(expected = "average scope")]
    fn merge_rejects_a_changed_entry() {
        let mut store = Store::new();
        store.merge([7; 16], View { code: 0b11, meta: 1, visits: 0, regrets: &[0.0, 0.0], average: None });
        store.merge([7; 16], View { code: 0b11, meta: 2, visits: 0, regrets: &[0.0, 0.0], average: None });
    }

    #[test]
    fn moved_records_are_reused_by_the_next_record_of_their_length() {
        let mut store = Store::new();
        let shard = &mut store.0[0];
        let delta = |regrets: &'static [f64], visits| View { code: 0b111, meta: 3, visits, regrets, average: Some(&[1.0, 2.0, 3.0]) };
        // One key, then its move to a longer record; the next short record takes the freed one.
        let mut key = [0u8; 16];
        key[8] = 1;
        shard.merge(key, delta(&[0.0; 3], 0));
        let short = shard.find(&key).unwrap();
        shard.merge(key, delta(&[1.0, 0.0, 0.0], 1));
        let long = shard.find(&key).unwrap();
        assert_ne!(short, long);
        let before = shard.allocation();
        let mut other = key;
        other[8] = 2;
        shard.merge(other, delta(&[0.0; 3], 0));
        assert_eq!(shard.find(&other), Some(short), "the freed record is reused");
        assert_eq!(shard.allocation(), before);
        // Both entries read back exactly after the move and the reuse.
        let a = shard.view(shard.find(&key).unwrap());
        assert_eq!(view_bits(a), view_bits(View { code: 0b111, meta: 3, visits: 1, regrets: &[1.0, 0.0, 0.0], average: Some(&[2.0, 4.0, 6.0]) }));
        let b = shard.view(shard.find(&other).unwrap());
        assert_eq!(view_bits(b), view_bits(delta(&[0.0; 3], 0)));
        assert_eq!(store.len(), 2);
    }

    #[test]
    fn a_frozen_table_compacts_the_records_its_moves_leave_behind() {
        // Opponent-only keys that all gain regrets later, with no new keys: nothing reuses the
        // short records, so only compaction keeps the shard near its live size.
        let mut store = Store::new();
        let key = |i: u32| {
            let mut k = [0u8; 16];
            k[8..12].copy_from_slice(&i.to_le_bytes());
            k[12..].copy_from_slice(&i.wrapping_mul(0x9E37_79B9).to_le_bytes());
            k
        };
        let count = 100_000u32;
        let average = [0.5, 1.5, 2.5];
        for i in 0..count {
            assert!(store.insert_view(key(i), View { code: 0b111, meta: i, visits: 0, regrets: &[0.0; 3], average: Some(&average) }));
        }
        let shard = &mut store.0[0];
        let check = |shard: &Shard| {
            let live: usize = shard.index.iter().map(|&p| shard.head(p).words()).sum();
            assert!(shard.free_words < COMPACT_MIN || shard.free_words * 16 <= shard.used_words, "free records pile up");
            assert_eq!(shard.used_words, live + shard.free_words);
            live
        };
        for i in 0..count {
            let regrets = [i as f64, -1.0, 0.0];
            shard.merge(key(i), View { code: 0b111, meta: i, visits: 1, regrets: &regrets, average: Some(&average) });
            if i % 4096 == 0 {
                check(shard);
            }
        }
        let live = check(shard);
        assert!(shard.free_words * 8 < count as usize * 8 * 7, "compaction ran");
        let chunk = Words::CHUNK * 8;
        assert!(shard.allocation().records <= (live + COMPACT_MIN.max(live / 16)) * 8 + 2 * chunk,
            "records {} for {} live bytes", shard.allocation().records, live * 8);
        // New keys after the compactions, enough to drain any free list: none may land on a live record.
        let fresh = |i: u32| key(count + i);
        for i in 0..20_000 {
            assert!(store.insert_view(fresh(i), View { code: 0b111, meta: i, visits: 0, regrets: &[0.0; 3], average: Some(&average) }));
        }
        let shard = &store.0[0];
        for i in 0..count {
            let v = shard.view(shard.find(&key(i)).unwrap());
            assert_eq!(view_bits(v), view_bits(View { code: 0b111, meta: i, visits: 1, regrets: &[i as f64, -1.0, 0.0], average: Some(&[1.0, 3.0, 5.0]) }));
        }
        for i in 0..20_000 {
            let v = shard.view(shard.find(&fresh(i)).unwrap());
            assert_eq!(view_bits(v), view_bits(View { code: 0b111, meta: i, visits: 0, regrets: &[0.0; 3], average: Some(&average) }));
        }
        check(shard);
        assert_eq!(store.len(), count as usize + 20_000);
        let sorted: Vec<Key> = store.sorted().map(|(k, _)| k).collect();
        assert!(sorted.windows(2).all(|w| w[0] < w[1]) && sorted.len() == count as usize + 20_000);
    }

    #[test]
    fn many_keys_survive_index_growth_moves_and_sort_by_key() {
        let mut store = Store::new();
        let key = |i: u64| {
            let mut k = [0u8; 16];
            // Spread keys over shards and hashes like digests, with some chunk-crossing menus.
            let x = i.wrapping_mul(0x9E3779B97F4A7C15);
            k[..8].copy_from_slice(&x.to_be_bytes());
            k[8..].copy_from_slice(&x.rotate_left(29).to_le_bytes());
            k
        };
        let count = 50_000u64;
        for i in 0..count {
            let len = 1 + (i % 5) as usize;
            let average: Vec<f64> = (0..len).map(|j| (i * 7 + j as u64) as f64 - 3.0).collect();
            // Every third key starts without regrets.
            let regrets = if i % 3 == 0 { vec![0.0; len] } else { average.clone() };
            assert!(store.insert(key(i), node((1u16 << len) - 1, len, &regrets, &average, i)));
        }
        assert_eq!(store.len(), count as usize);
        // Updates and merges after growth, some moving records.
        for i in (0..count).step_by(7) {
            let len = 1 + (i % 5) as usize;
            store.0[Store::shard(&key(i))].update(key(i), || unreachable!(), |n| { n.visits += 1; n.regrets[0] += 0.5; });
            let ones = vec![1.0; len];
            store.merge(key(i), View { code: (1u16 << len) - 1, meta: 0, visits: 1, regrets: &ones, average: Some(&ones) });
        }
        let clone = store.clone();
        for i in (0..count).step_by(97) {
            for s in [&store, &clone] {
                let n = s.get(&key(i)).unwrap();
                let touched = i % 7 == 0;
                let len = 1 + (i % 5) as usize;
                assert_eq!((n.visits, n.len as usize), (i + if touched { 2 } else { 0 }, len));
                let last = (i * 7 + len as u64 - 1) as f64 - 3.0 + if touched { 1.0 } else { 0.0 };
                assert_eq!(n.average[len - 1], last);
                let first_regret = if i % 3 == 0 { 0.0 } else { (i * 7) as f64 - 3.0 } + if touched { 1.5 } else { 0.0 };
                assert_eq!(n.regrets[0], first_regret);
            }
        }
        let sorted: Vec<Key> = store.sorted().map(|(k, _)| k).collect();
        assert_eq!(sorted.len(), count as usize);
        assert!(sorted.windows(2).all(|w| w[0] < w[1]));
        let views: Vec<Key> = store.sorted_views().map(|(k, _)| k).collect();
        assert_eq!(views, sorted);
    }
}
