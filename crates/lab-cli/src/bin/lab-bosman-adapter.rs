fn main() {
    if let Err(error) = lab_cli::bosman_adapter::run() {
        eprintln!("lab-bosman-adapter: {error}");
        std::process::exit(2);
    }
}
