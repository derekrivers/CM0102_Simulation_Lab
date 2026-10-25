//! Qualified small-bound RNG slice; see docs/research/PC_R1_RNG.md.
#![no_std]
use sha2::{Digest, Sha256};

pub const WORDS: usize = 51_000;
pub const CHECKPOINT_BYTES: usize = 52;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    TableLength,
    TableWord,
    Cursor,
    Offset,
    Bound,
    Checkpoint,
    TableIdentity,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct State {
    pub cursor: i32,
    pub offset: u32,
    pub crt: u32,
}
impl State {
    pub fn validate(self) -> Result<Self, Error> {
        if !(-1..WORDS as i32).contains(&self.cursor) {
            return Err(Error::Cursor);
        }
        if self.offset > 65535 {
            return Err(Error::Offset);
        }
        Ok(self)
    }
}
/// Wrapping 32-bit CRT transition. No ambient seed is consulted.
pub fn crt_step(state: &mut u32) -> u32 {
    *state = state.wrapping_mul(0x343fd).wrapping_add(0x269ec3);
    (*state >> 16) & 0x7fff
}
#[derive(Clone, Copy)]
pub struct Table<'a> {
    words: &'a [u32],
    identity: [u8; 32],
}
impl<'a> Table<'a> {
    pub fn new(words: &'a [u32]) -> Result<Self, Error> {
        if words.len() != WORDS {
            return Err(Error::TableLength);
        }
        if words.iter().any(|&word| word > 32767) {
            return Err(Error::TableWord);
        }
        let mut hash = Sha256::new();
        for word in words {
            hash.update(word.to_le_bytes());
        }
        Ok(Self {
            words,
            identity: hash.finalize().into(),
        })
    }
    pub fn identity(&self) -> [u8; 32] {
        self.identity
    }
}
pub struct Rng<'a> {
    table: Table<'a>,
    state: State,
}
impl<'a> Rng<'a> {
    pub fn new(table: Table<'a>, state: State) -> Result<Self, Error> {
        Ok(Self {
            table,
            state: state.validate()?,
        })
    }
    pub fn state(&self) -> State {
        self.state
    }
    pub fn next_bounded(&mut self, bound: i32) -> Result<i32, Error> {
        if !(-65535..=65535).contains(&bound) {
            return Err(Error::Bound);
        }
        if bound == 0 {
            return Ok(0);
        }
        let mut next = self.state;
        next.cursor += 1;
        if next.cursor == WORDS as i32 {
            next.cursor = 0;
            next.offset = crt_step(&mut next.crt) & 0xffff;
        }
        // The admitted word/offset domain excludes signed-IDIV overflow.
        let dividend = next
            .offset
            .wrapping_add(self.table.words[next.cursor as usize]) as i32;
        let remainder = dividend % bound;
        let result = if bound < 0 { -remainder } else { remainder };
        self.state = next;
        Ok(result)
    }
    /// CMRG, little-endian version 1, SHA-256(table LE words), cursor, offset, CRT.
    pub fn checkpoint(&self) -> [u8; CHECKPOINT_BYTES] {
        let mut bytes = [0; CHECKPOINT_BYTES];
        bytes[..4].copy_from_slice(b"CMRG");
        bytes[4..8].copy_from_slice(&1u32.to_le_bytes());
        bytes[8..40].copy_from_slice(&self.table.identity);
        bytes[40..44].copy_from_slice(&self.state.cursor.to_le_bytes());
        bytes[44..48].copy_from_slice(&self.state.offset.to_le_bytes());
        bytes[48..52].copy_from_slice(&self.state.crt.to_le_bytes());
        bytes
    }
    pub fn restore(table: Table<'a>, bytes: &[u8]) -> Result<Self, Error> {
        if bytes.len() != CHECKPOINT_BYTES
            || &bytes[..4] != b"CMRG"
            || bytes[4..8] != 1u32.to_le_bytes()
        {
            return Err(Error::Checkpoint);
        }
        if bytes[8..40] != table.identity {
            return Err(Error::TableIdentity);
        }
        let word = |start| u32::from_le_bytes(bytes[start..start + 4].try_into().unwrap());
        Self::new(
            table,
            State {
                cursor: word(40) as i32,
                offset: word(44),
                crt: word(48),
            },
        )
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unsupported_inputs_are_atomic() {
        let mut words = [0; WORDS];
        assert!(matches!(Table::new(&words[..1]), Err(Error::TableLength)));
        words[99] = 32768;
        assert!(matches!(Table::new(&words), Err(Error::TableWord)));
        words[99] = 0;
        let table = Table::new(&words).unwrap();
        for cursor in [-2, 51000, i32::MAX] {
            assert!(matches!(
                Rng::new(
                    table,
                    State {
                        cursor,
                        offset: 0,
                        crt: 0
                    }
                ),
                Err(Error::Cursor)
            ));
        }
        assert!(matches!(
            Rng::new(
                table,
                State {
                    cursor: 0,
                    offset: 65536,
                    crt: 0
                }
            ),
            Err(Error::Offset)
        ));
        let mut rng = Rng::new(
            table,
            State {
                cursor: 50999,
                offset: 65535,
                crt: u32::MAX,
            },
        )
        .unwrap();
        let before = rng.checkpoint();
        for bound in [i32::MIN, -65536, 65536, i32::MAX] {
            assert_eq!(rng.next_bounded(bound), Err(Error::Bound));
            assert_eq!(rng.checkpoint(), before);
        }
        assert_eq!(rng.next_bounded(0), Ok(0));
        assert_eq!(rng.checkpoint(), before);
        for pos in [0, 4, 8, 40, 44] {
            let mut bad = before;
            bad[pos] = 255;
            if pos == 40 {
                bad[41..44].fill(127);
            }
            if pos == 44 {
                bad[45..48].fill(255);
            }
            assert!(Rng::restore(table, &bad).is_err());
        }
        assert!(Rng::restore(table, &before[..51]).is_err());
        words[0] = 1;
        assert!(matches!(
            Rng::restore(Table::new(&words).unwrap(), &before),
            Err(Error::TableIdentity)
        ));
    }
}
