//! Persistent, explicitly opted-in legal river pilot. No arena or action RNG.
use hu20_trainer::{cards::EquityTables, multi_policy::PolicyTable, river::live};
use serde_json::{json, Value};
use std::{
    io::{self, BufRead, Read, Write},
    path::Path,
    time::Instant,
};
fn run() -> Result<(), String> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 4 {
        return Err("river_live K50 POLICY SHA256".into());
    }
    let tick = Instant::now();
    let (table, load) = PolicyTable::load_profiled(Path::new(&a[2]), &a[3], false)?;
    let tables = EquityTables::load(Path::new(&a[1]), false)?;
    let mut output = io::BufWriter::new(io::stdout().lock());
    writeln!(output,"{}",json!({"status":"ready","model_sha256":a[3],"policy_load_seconds":load.total_seconds,"model_and_k50_load_seconds":tick.elapsed().as_secs_f64(),"rows":table.rows.len()})).map_err(|e|e.to_string())?;
    output.flush().map_err(|e| e.to_string())?;
    let mut input = io::stdin().lock();
    let mut sessions = live::SessionStore::new(&a[3])?;
    loop {
        let mut line = Vec::new();
        let n = (&mut input)
            .take(1024 * 1024 + 1)
            .read_until(b'\n', &mut line)
            .map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        if n > 1024 * 1024 {
            return Err("legal river request exceeds 1 MiB".into());
        }
        let tick = Instant::now();
        let value = serde_json::from_slice::<Value>(&line)
            .map_err(|e| e.to_string())
            .and_then(|v| sessions.request(&v, &table, tables));
        let response = match value {
            Ok(result) => json!({"status":"ok","result":result}),
            Err(error)
                if error.contains("nonfinite")
                    || error.contains("invalid blueprint")
                    || error.contains("blueprint key/menu") =>
            {
                return Err(error);
            }
            Err(error) => json!({"status":"unsupported","reason":error}),
        };
        // Timer excludes serialization but includes parsing and the complete
        // native path. The caller measures transport/serialization as well.
        let mut response = response;
        response["worker_seconds_before_serialization"] = json!(tick.elapsed().as_secs_f64());
        serde_json::to_writer(&mut output, &response).map_err(|e| e.to_string())?;
        output.write_all(b"\n").map_err(|e| e.to_string())?;
        output.flush().map_err(|e| e.to_string())?;
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("river_live: {error}");
        std::process::exit(2);
    }
}
