use std::io::{Read, Write};

fn main() {
    println!("ready");
    std::io::stdout().flush().expect("flush readiness");
    let mut byte = [0u8; 1];
    std::io::stdin()
        .read_exact(&mut byte)
        .expect("wait for replacement");
    println!(
        "{}",
        lab_cli::comparator::live_executable_sha256().expect("hash live executable")
    );
}
