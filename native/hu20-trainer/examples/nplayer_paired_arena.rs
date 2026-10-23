//! Controlled focal-policy comparisons; legacy nplayer_arena is unchanged.
#[path = "support/nplayer_paired_host.rs"]
mod host;
fn main() {
    if let Err(error) = host::run() {
        eprintln!("nplayer_paired_arena: {error}");
        std::process::exit(2);
    }
}
