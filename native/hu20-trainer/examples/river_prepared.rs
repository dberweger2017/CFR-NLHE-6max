//! Persistent JSONL transport for the opt-in prepared river prototype.
use serde_json::{json, Value};
use std::io::{self, BufRead, Read, Write};
use std::time::Instant;
fn main() -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::BufWriter::new(io::stdout().lock());
    loop {
        let mut line = Vec::new();
        let n = (&mut input)
            .take(16 * 1024 * 1024 + 1)
            .read_until(b'\n', &mut line)?;
        if n == 0 {
            break;
        }
        if n > 16 * 1024 * 1024 {
            writeln!(
                output,
                "{}",
                json!({"status":"error","error":"prepared request exceeds 16 MiB"})
            )?;
            output.flush()?;
            break;
        }
        let started = Instant::now();
        let request = serde_json::from_slice::<Value>(&line).map_err(|e| e.to_string());
        let parse = started.elapsed().as_secs_f64();
        let response = match request.and_then(|v| hu20_trainer::river::request(&v)) {
            Ok(result) => json!({"status":"ok","json_parse_seconds":parse,"result":result}),
            Err(error) => json!({"status":"error","error":error}),
        };
        serde_json::to_writer(&mut output, &response)?;
        output.write_all(b"\n")?;
        output.flush()?;
    }
    Ok(())
}
