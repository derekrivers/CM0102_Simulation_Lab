use std::io::{self, Read};
fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).expect("input");
    let operations: Vec<serde_json::Value> = serde_json::from_str(&input).expect("operation array");
    let mut engine = cm_management::Engine::default();
    let results: Vec<_> = operations
        .iter()
        .map(|op| engine.request(&serde_json::to_vec(op).expect("op")))
        .collect();
    println!("{}", serde_json::to_string(&results).expect("results"));
}
