#[path = "../tests/support/corpus.rs"]
mod corpus;
fn main() {
    #[cfg(not(target_arch = "wasm32"))]
    {
        use std::io::Write;
        std::io::stdout().write_all(corpus::bytes()).unwrap();
    }
}
