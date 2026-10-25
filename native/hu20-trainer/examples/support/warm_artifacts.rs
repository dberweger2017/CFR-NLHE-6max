//! Ordered reproduction sink: retain initial bytes, compare/hash repeat bytes
//! without creating a second raw tree. Only diagnostic output uses this module.
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    cell::RefCell,
    collections::BTreeMap,
    fs::File,
    io::{self, BufReader, BufWriter, Read, Write},
    path::{Path, PathBuf},
};

enum Destination {
    File(File),
    Compare(BufReader<File>),
}
pub struct Sink {
    target: Destination,
    hash: Sha256,
    bytes: u64,
    relative: String,
    failure: PathBuf,
}
impl Sink {
    fn mismatch(&self, reason: &str, actual: &[u8], expected: &[u8]) -> io::Error {
        // Output chunks are bounded by the writer; retain first mismatch bytes,
        // offset and file identity even when the stream is not valid JSON yet.
        let hex = |v: &[u8]| v.iter().map(|b| format!("{b:02x}")).collect::<String>();
        let context = json!({"file":self.relative,"offset":self.bytes,"reason":reason,
            "actual_chunk_hex":hex(actual),"expected_chunk_hex":hex(expected)});
        if let Ok(mut file) = File::options()
            .write(true)
            .create_new(true)
            .open(&self.failure)
        {
            let _ = writeln!(file, "{context}");
            let _ = file.sync_all();
        }
        io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "reproduction mismatch in {} at byte {}: {reason}",
                self.relative, self.bytes
            ),
        )
    }
}
impl Write for Sink {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        let n = match &mut self.target {
            Destination::File(file) => file.write(bytes)?,
            Destination::Compare(reader) => {
                let mut expected = vec![0; bytes.len()];
                let mut read = 0;
                while read < bytes.len() {
                    let n = reader.read(&mut expected[read..])?;
                    if n == 0 {
                        break;
                    }
                    read += n;
                }
                if read != bytes.len() {
                    return Err(self.mismatch("initial stream shorter", bytes, &expected[..read]));
                }
                if expected != bytes {
                    return Err(self.mismatch("bytes differ", bytes, &expected));
                }
                bytes.len()
            }
        };
        self.hash.update(&bytes[..n]);
        self.bytes += n as u64;
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> {
        match &mut self.target {
            Destination::File(f) => f.flush(),
            Destination::Compare(_) => Ok(()),
        }
    }
}
pub type Output = BufWriter<Sink>;
pub struct Artifacts {
    pub root: PathBuf,
    reference: Option<PathBuf>,
    receipts: RefCell<BTreeMap<String, Value>>,
}
impl Artifacts {
    pub fn new(root: &Path, reference: Option<&Path>) -> Self {
        Self {
            root: root.into(),
            reference: reference.map(Path::to_path_buf),
            receipts: RefCell::new(BTreeMap::new()),
        }
    }
    pub fn fresh(&self, path: &Path) -> Result<Output, String> {
        let relative = path
            .strip_prefix(&self.root)
            .map_err(|e| e.to_string())?
            .to_str()
            .ok_or("nonUTF8output")?
            .replace('\\', "/");
        let target = if let Some(reference) = &self.reference {
            Destination::Compare(BufReader::new(
                File::open(reference.join(&relative)).map_err(|e| e.to_string())?,
            ))
        } else {
            Destination::File(
                File::options()
                    .write(true)
                    .create_new(true)
                    .open(path)
                    .map_err(|e| e.to_string())?,
            )
        };
        Ok(BufWriter::new(Sink {
            target,
            hash: Sha256::new(),
            bytes: 0,
            relative,
            failure: self.root.join("comparison-failure.json"),
        }))
    }
    pub fn finish(&self, mut out: Output) -> Result<(), String> {
        out.flush().map_err(|e| e.to_string())?;
        let sink = out.get_mut();
        match &mut sink.target {
            Destination::File(file) => file.sync_all().map_err(|e| e.to_string())?,
            Destination::Compare(reader) => {
                let mut tail = [0];
                if reader.read(&mut tail).map_err(|e| e.to_string())? != 0 {
                    return Err(sink
                        .mismatch("initial stream has trailing bytes", &[], &tail)
                        .to_string());
                }
            }
        }
        self.receipts.borrow_mut().insert(
            sink.relative.clone(),
            json!({"bytes":sink.bytes,"sha256":format!("{:x}",sink.hash.clone().finalize())}),
        );
        Ok(())
    }
    pub fn sha(&self, path: &Path) -> Result<String, String> {
        let relative = path
            .strip_prefix(&self.root)
            .map_err(|e| e.to_string())?
            .to_str()
            .ok_or("nonUTF8output")?
            .replace('\\', "/");
        self.receipts
            .borrow()
            .get(&relative)
            .and_then(|v| v["sha256"].as_str())
            .map(str::to_owned)
            .ok_or("artifact not closed".into())
    }
    pub fn manifest(&self) -> Value {
        json!({"format":"nplayer-warm-artifact-receipts-v1","files":*self.receipts.borrow()})
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn directories() -> (PathBuf, PathBuf, PathBuf) {
        let parent = std::env::temp_dir().join(format!(
            "warm-artifact-test-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let a = parent.join("a");
        let b = parent.join("b");
        std::fs::create_dir(&parent).unwrap();
        std::fs::create_dir(&a).unwrap();
        std::fs::create_dir(&b).unwrap();
        (parent, a, b)
    }
    #[test]
    fn streamed_reproduction_has_identical_receipts_without_duplicate_payload() {
        let (parent, a, b) = directories();
        let bytes = vec![b'x'; 100000];
        let initial = Artifacts::new(&a, None);
        let mut out = initial.fresh(&a.join("sample")).unwrap();
        out.write_all(&bytes).unwrap();
        initial.finish(out).unwrap();
        let repeat = Artifacts::new(&b, Some(&a));
        let mut out = repeat.fresh(&b.join("sample")).unwrap();
        for chunk in bytes.chunks(13) {
            out.write_all(chunk).unwrap();
        }
        repeat.finish(out).unwrap();
        assert_eq!(initial.manifest(), repeat.manifest());
        assert!(!b.join("sample").exists());
        std::fs::remove_dir_all(parent).unwrap();
    }
    #[test]
    fn mismatch_is_preserved_and_truncation_is_rejected() {
        let (parent, a, b) = directories();
        std::fs::write(a.join("sample"), b"abc").unwrap();
        let repeat = Artifacts::new(&b, Some(&a));
        let mut out = repeat.fresh(&b.join("sample")).unwrap();
        out.write_all(b"abd").unwrap();
        assert!(repeat.finish(out).unwrap_err().contains("bytes differ"));
        assert!(b.join("comparison-failure.json").exists());
        let c = parent.join("c");
        std::fs::create_dir(&c).unwrap();
        let repeat = Artifacts::new(&c, Some(&a));
        let mut out = repeat.fresh(&c.join("sample")).unwrap();
        out.write_all(b"ab").unwrap();
        assert!(repeat.finish(out).unwrap_err().contains("trailing"));
        std::fs::remove_dir_all(parent).unwrap();
    }
}
