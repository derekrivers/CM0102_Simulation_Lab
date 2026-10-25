#[path = "support/corpus.rs"]
mod corpus;
#[test]
fn original_instruction_corpus_and_checkpoints() {
    assert_eq!(corpus::bytes().len(), 75952);
}
