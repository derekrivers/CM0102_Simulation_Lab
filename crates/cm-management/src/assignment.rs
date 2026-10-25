//! Bounded two-member slot-zero assignment and explicit readback.
//! Original assignment/readback is qualified only for the immutable retained domain.
//! Host command history and saves are Rust mechanisms, not original save behavior.
use crate::{MAX_BYTES, MAX_COMMANDS, Save, hash};
use serde::{Deserialize, Serialize};

// Independently admitted exact projection; see
// docs/research/evidence/pc-r10-bounded-projection-review-v1.json.
const PRIVATE_FIXTURES: &[&str] =
    &["39ec04463f83c893e3ab702a6d29d31bd95ee925b06d7a3e70d149a85e9075ea"];
const SYNTHETIC_FIXTURES: &[&str] =
    &["2c3e22cb65f6bd6f0f4cb48da7e0ed4a92a2ddc04d191682335c204f40490599"];

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AssignmentFixture {
    pub schema_version: u32,
    pub origin: String,
    pub specimen_sha256: String,
    pub source_capture_sha256: String,
    pub image_sha256: String,
    pub heap_sha256: String,
    pub backend_revision: String,
    pub club_id: u32,
    pub manager_staff_id: u32,
    pub members: [u32; 2],
    pub row_mode: u8,
    pub cache_count: u8,
    pub mapping: [i32; 20],
}
impl AssignmentFixture {
    pub fn parse(encoded: &str) -> Result<Self, String> {
        if encoded.len() > 65536 {
            return Err("fixture-too-large".into());
        }
        let fixture: Self =
            serde_json::from_str(encoded).map_err(|_| "invalid-assignment-fixture")?;
        fixture.validate()?;
        Ok(fixture)
    }
    pub fn fingerprint(&self) -> Result<String, String> {
        Ok(hash(
            &serde_json::to_vec(
                &serde_json::to_value(self).map_err(|_| "invalid-assignment-fixture")?,
            )
            .map_err(|_| "invalid-assignment-fixture")?,
        ))
    }
    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != 1
            || self.row_mode != 0
            || self.cache_count != 0
            || self.mapping != [-1; 20]
            || self.members[0] >= self.members[1]
            || self.members[1] > i32::MAX as u32
            || self.members.contains(&self.manager_staff_id)
        {
            return Err("unsupported-assignment-domain".into());
        }
        let fingerprint = self.fingerprint()?;
        let admitted = match self.origin.as_str() {
            "captured-bosman-two-member-assignment" => {
                PRIVATE_FIXTURES.contains(&fingerprint.as_str())
            }
            "synthetic-assignment-regression" => SYNTHETIC_FIXTURES.contains(&fingerprint.as_str()),
            _ => false,
        };
        if !admitted {
            return Err("unqualified-assignment-fixture".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AssignmentCommand {
    pub session_id: String,
    pub command_id: String,
    pub expected_revision: u32,
    pub club_id: u32,
    pub slot: i32,
    pub staff_id: i64,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AssignmentReadbackCommand {
    pub session_id: String,
    pub command_id: String,
    pub expected_revision: u32,
    pub club_id: u32,
    pub slot: i32,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(
    tag = "action",
    content = "command",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum AssignmentAction {
    AssignmentCommand(AssignmentCommand),
    AssignmentReadbackCommand(AssignmentReadbackCommand),
}
impl AssignmentAction {
    fn envelope(&self) -> (&str, &str, u32, u32, i32) {
        match self {
            Self::AssignmentCommand(c) => (
                &c.session_id,
                &c.command_id,
                c.expected_revision,
                c.club_id,
                c.slot,
            ),
            Self::AssignmentReadbackCommand(c) => (
                &c.session_id,
                &c.command_id,
                c.expected_revision,
                c.club_id,
                c.slot,
            ),
        }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AssignmentWrite {
    pub row_mode: u8,
    pub byte_offset: u32,
    pub width: u8,
    pub value: i32,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", deny_unknown_fields)]
pub enum AssignmentReadback {
    Empty {},
    StaffId { staff_id: u32 },
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", deny_unknown_fields)]
pub enum AssignmentEvent {
    AssignmentMade {
        revision: u32,
        club_id: u32,
        slot: i32,
        old_staff_id: i32,
        new_staff_id: u32,
        original_return: u32,
        ordered_writes: Vec<AssignmentWrite>,
        rng_draws: u32,
    },
    AssignmentReadBack {
        revision: u32,
        club_id: u32,
        slot: i32,
        readback: AssignmentReadback,
        ordered_writes: Vec<AssignmentWrite>,
        rng_draws: u32,
    },
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct AssignmentRecord {
    command: AssignmentAction,
    result: AssignmentEvent,
}

/// Admission and replay cannot be bypassed through public deserialization.
/// ```compile_fail
/// let world: cm_management::assignment::AssignmentWorld = serde_json::from_str("{}").unwrap();
/// ```
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct AssignmentWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: AssignmentFixture,
    mapping: [i32; 20],
    events: Vec<AssignmentEvent>,
    records: Vec<AssignmentRecord>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LoadedAssignmentWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: AssignmentFixture,
    mapping: [i32; 20],
    events: Vec<AssignmentEvent>,
    records: Vec<AssignmentRecord>,
}
impl AssignmentWorld {
    pub fn from_fixture(fixture: AssignmentFixture) -> Result<Self, String> {
        fixture.validate()?;
        Ok(Self {
            schema_version: 6,
            profile: format!("{}-slot-zero-v1", fixture.origin),
            session_id: format!("{}-assignment-session-v1", fixture.origin),
            fixture_sha256: fixture.fingerprint()?,
            revision: 0,
            mapping: fixture.mapping,
            fixture,
            events: vec![],
            records: vec![],
        })
    }
    /// Historical last explicit read, never an implicit original readback.
    pub fn last_readback(&self) -> Option<&AssignmentEvent> {
        self.events
            .iter()
            .rev()
            .find(|event| matches!(event, AssignmentEvent::AssignmentReadBack { .. }))
    }
    pub fn apply(&mut self, command: AssignmentAction) -> Result<AssignmentEvent, String> {
        let (session, id, expected_revision, club, slot) = command.envelope();
        if session != self.session_id {
            return Err("wrong-session".into());
        }
        if id.is_empty()
            || id.len() > 64
            || !id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"-_".contains(&c))
        {
            return Err("invalid-command-id".into());
        }
        if let Some(record) = self.records.iter().find(|r| r.command.envelope().1 == id) {
            return if record.command == command {
                Ok(record.result.clone())
            } else {
                Err("command-id-conflict".into())
            };
        }
        if expected_revision != self.revision {
            return Err("stale-revision".into());
        }
        if self.records.len() >= MAX_COMMANDS {
            return Err("command-capacity".into());
        }
        if club != self.fixture.club_id {
            return Err("unknown-club".into());
        }
        // Host restrictions do not claim parity with original diagnostic paths.
        if slot != 0 {
            return Err("unsupported-assignment-slot".into());
        }
        let revision = self.revision + 1;
        let event = match &command {
            AssignmentAction::AssignmentCommand(c) => {
                let staff_id = u32::try_from(c.staff_id)
                    .ok()
                    .filter(|id| self.fixture.members.contains(id))
                    .ok_or("unsupported-assignment-member")?;
                AssignmentEvent::AssignmentMade {
                    revision,
                    club_id: club,
                    slot,
                    old_staff_id: self.mapping[0],
                    new_staff_id: staff_id,
                    original_return: 1,
                    ordered_writes: vec![AssignmentWrite {
                        row_mode: 0,
                        byte_offset: 2,
                        width: 4,
                        value: staff_id as i32,
                    }],
                    rng_draws: 0,
                }
            }
            AssignmentAction::AssignmentReadbackCommand(_) => AssignmentEvent::AssignmentReadBack {
                revision,
                club_id: club,
                slot,
                readback: if self.mapping[0] == -1 {
                    AssignmentReadback::Empty {}
                } else {
                    AssignmentReadback::StaffId {
                        staff_id: self.mapping[0] as u32,
                    }
                },
                ordered_writes: vec![],
                rng_draws: 0,
            },
        };
        if let AssignmentEvent::AssignmentMade { new_staff_id, .. } = &event {
            self.mapping[0] = *new_staff_id as i32;
        }
        self.revision = revision;
        self.events.push(event.clone());
        self.records.push(AssignmentRecord {
            command,
            result: event.clone(),
        });
        Ok(event)
    }
    pub fn save(&self) -> Result<String, String> {
        let payload = serde_json::to_string(self).map_err(|e| e.to_string())?;
        serde_json::to_string(&Save {
            magic: "CM-PLAN-SLICE".into(),
            schema_version: 6,
            payload_bytes: payload.len(),
            payload_sha256: hash(payload.as_bytes()),
            payload,
        })
        .map_err(|e| e.to_string())
    }
    pub fn load(encoded: &str) -> Result<Self, String> {
        if encoded.len() > MAX_BYTES {
            return Err("save-too-large".into());
        }
        let save: Save = serde_json::from_str(encoded).map_err(|_| "invalid-save-envelope")?;
        if save.magic != "CM-PLAN-SLICE"
            || save.schema_version != 6
            || save.payload.len() != save.payload_bytes
            || hash(save.payload.as_bytes()) != save.payload_sha256
        {
            return Err("save-integrity".into());
        }
        let data: LoadedAssignmentWorld =
            serde_json::from_str(&save.payload).map_err(|_| "invalid-save-payload")?;
        if data.records.len() > MAX_COMMANDS {
            return Err("command-capacity".into());
        }
        let mut replay = Self::from_fixture(data.fixture.clone())?;
        for record in &data.records {
            replay.apply(record.command.clone())?;
        }
        let candidate = Self {
            schema_version: data.schema_version,
            profile: data.profile,
            fixture_sha256: data.fixture_sha256,
            session_id: data.session_id,
            revision: data.revision,
            fixture: data.fixture,
            mapping: data.mapping,
            events: data.events,
            records: data.records,
        };
        if replay != candidate {
            return Err("unsupported-or-inconsistent-state".into());
        }
        Ok(candidate)
    }
}
