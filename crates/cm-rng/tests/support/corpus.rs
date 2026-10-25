use cm_rng::{Rng, State, Table, WORDS, crt_step};
use std::sync::OnceLock;
static OUTPUT: OnceLock<Vec<u8>> = OnceLock::new();
fn read(bytes: &[u8], at: &mut usize) -> u32 {
    let word = u32::from_le_bytes(bytes[*at..*at + 4].try_into().unwrap());
    *at += 4;
    word
}
fn state(bytes: &[u8], at: &mut usize) -> State {
    State {
        cursor: read(bytes, at) as i32,
        offset: read(bytes, at),
        crt: read(bytes, at),
    }
}
fn emit(output: &mut Vec<u8>, words: &[u32]) {
    for word in words {
        output.extend(word.to_le_bytes());
    }
}
fn run() -> Vec<u8> {
    let input = include_bytes!("../../fixtures/corpus.bin");
    let mut at = 0;
    let crt_count = read(input, &mut at);
    let bounded_count = read(input, &mut at);
    let sequential_count = read(input, &mut at);
    assert_eq!(
        (crt_count, bounded_count, sequential_count),
        (1024, 2570, 512)
    );
    let mut output = Vec::new();
    let mut wrong_arithmetic = 0;
    for _ in 0..crt_count {
        let before = read(input, &mut at);
        let expected = read(input, &mut at);
        let after = read(input, &mut at);
        let mut actual = before;
        let value = crt_step(&mut actual);
        assert_eq!((value, actual), (expected, after));
        emit(&mut output, &[value, actual]);
        wrong_arithmetic += u32::from(before.wrapping_mul(0x343fc).wrapping_add(0x269ec3) != after);
    }
    let mut seed = 0x10203968;
    let words: Vec<u32> = (0..WORDS).map(|_| crt_step(&mut seed)).collect();
    let table = Table::new(&words).unwrap();
    assert_eq!(
        table.identity(),
        [
            0xbe, 0xfd, 0xec, 0x88, 0xf8, 0x02, 0x58, 0x2b, 0xba, 0x74, 0x50, 0xe4, 0x18, 0xaa,
            0xa3, 0x98, 0x37, 0x03, 0x6c, 0x8d, 0x03, 0x88, 0x10, 0x15, 0x8c, 0xfc, 0x7a, 0x99,
            0x8b, 0xe1, 0xb3, 0xdb
        ]
    );
    let mut prior = None;
    let mut continued: Option<[u8; 52]> = None;
    let mut wrong_wrap = 0;
    let mut extra_draw = 0;
    let mut zero_mutation = 0;
    for index in 0..bounded_count {
        let bound = read(input, &mut at) as i32;
        let initial = state(input, &mut at);
        let expected = read(input, &mut at) as i32;
        let final_state = state(input, &mut at);
        let mut rng = Rng::new(table, initial).unwrap();
        let value = rng.next_bounded(bound).unwrap();
        assert_eq!((value, rng.state()), (expected, final_state));
        emit(
            &mut output,
            &[
                value as u32,
                rng.state().cursor as u32,
                rng.state().offset,
                rng.state().crt,
            ],
        );
        if index >= bounded_count - sequential_count {
            if let Some(previous) = prior {
                assert_eq!(previous, initial);
            }
            if let Some(checkpoint) = continued {
                let mut restored = Rng::restore(table, &checkpoint).unwrap();
                assert_eq!(restored.next_bounded(bound).unwrap(), value);
                assert_eq!(restored.state(), final_state);
            }
            continued = Some(rng.checkpoint());
            output.extend(rng.checkpoint());
            prior = Some(final_state);
        }
        // Independent deliberately faulty transitions: detect using ALL state fields.
        let mut bad = initial;
        if bound != 0 {
            bad.cursor += 1;
            if bad.cursor >= WORDS as i32 - 1 {
                bad.cursor = 0;
                bad.offset = crt_step(&mut bad.crt);
            }
            wrong_wrap += u32::from(bad != final_state);
            bad = final_state;
            crt_step(&mut bad.crt);
            extra_draw += u32::from(bad != final_state);
        } else {
            bad.cursor += 1;
            zero_mutation += u32::from(bad != final_state);
        }
    }
    assert_eq!(at, input.len());
    assert!(wrong_arithmetic > 0 && wrong_wrap > 0 && extra_draw > 0 && zero_mutation > 0);
    emit(
        &mut output,
        &[wrong_arithmetic, wrong_wrap, extra_draw, zero_mutation],
    );
    output
}
#[unsafe(no_mangle)]
pub extern "C" fn corpus_run() -> usize {
    OUTPUT.get_or_init(run).len()
}
#[unsafe(no_mangle)]
pub extern "C" fn corpus_ptr() -> *const u8 {
    OUTPUT.get_or_init(run).as_ptr()
}

pub fn bytes() -> &'static [u8] {
    OUTPUT.get_or_init(run)
}
