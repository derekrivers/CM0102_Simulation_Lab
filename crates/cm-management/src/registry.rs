//! Fixed option-2 producer over an admitted initialized registry row.
//! No implicit outer-getter, lifecycle or gameplay interpretation.
use crate::human::{
    HumanCommand, HumanRegistryFixture, HumanSlotLocation, HumanWorld, RegistryWrite,
};
use crate::{MAX_BYTES, MAX_COMMANDS, Save, hash};
use serde::{Deserialize, Serialize};

// Independently projected and replay-qualified; see HUMAN_REGISTRY_PRODUCER.md.
const PRIVATE_FIXTURES: &[&str] = &[
    "cc7e3483d1ba7dfd36516f500362f20c63fd23a703f26e9cf20490f0251b616f",
    "e5411188dcb8fe67187930a56c7c224294182bdcef3b684d34d0b8456ee94a5b",
];
const SYNTHETIC_FIXTURES: &[&str] =
    &["f4fd4d0ddea2476728074256bb8cc3a3149c8884ed4a18ccc2716f6d471b2cd8"];

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RegistryFixture {
    pub schema_version: u32,
    pub human: HumanRegistryFixture,
    pub guard_9a01: u32,
    pub option_two: u8,
}
impl RegistryFixture {
    pub fn parse(encoded: &str) -> Result<Self, String> {
        if encoded.len() > 65536 {
            return Err("fixture-too-large".into());
        }
        let fixture: Self =
            serde_json::from_str(encoded).map_err(|_| "invalid-registry-fixture")?;
        fixture.validate()?;
        Ok(fixture)
    }
    pub fn fingerprint(&self) -> Result<String, String> {
        Ok(hash(
            &serde_json::to_vec(
                &serde_json::to_value(self).map_err(|_| "invalid-registry-fixture")?,
            )
            .map_err(|_| "invalid-registry-fixture")?,
        ))
    }
    pub fn validate(&self) -> Result<(), String> {
        self.human.validate()?;
        if self.schema_version != 2 || self.guard_9a01 > 1 || self.option_two > 1 {
            return Err("unsupported-registry-domain".into());
        }
        let fingerprint = self.fingerprint()?;
        let admitted = match self.human.origin.as_str() {
            "captured-bosman-human-registry" => PRIVATE_FIXTURES.contains(&fingerprint.as_str()),
            "synthetic-human-regression" => SYNTHETIC_FIXTURES.contains(&fingerprint.as_str()),
            _ => false,
        };
        if !admitted {
            return Err("unqualified-registry-fixture".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RegistryOptionCommand {
    pub session_id: String,
    pub command_id: String,
    pub expected_revision: u32,
    pub club_id: u32,
    pub value: i32,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(
    tag = "action",
    content = "command",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum RegistryAction {
    HumanCommand(HumanCommand),
    RegistryOptionCommand(RegistryOptionCommand),
}
impl RegistryAction {
    fn envelope(&self) -> (&str, &str, u32, u32) {
        match self {
            Self::HumanCommand(c) => (&c.session_id, &c.command_id, c.expected_revision, c.club_id),
            Self::RegistryOptionCommand(c) => {
                (&c.session_id, &c.command_id, c.expected_revision, c.club_id)
            }
        }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", deny_unknown_fields)]
pub enum RegistryEvent {
    HumanSlotSelected {
        revision: u32,
        club_id: u32,
        old_slot: u8,
        new_slot: u8,
        ordered_writes: Vec<RegistryWrite>,
    },
    RegistryOptionTwoSet {
        revision: u32,
        club_id: u32,
        old_value: u8,
        new_value: u8,
        ordered_writes: Vec<RegistryWrite>,
    },
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct RegistryRecord {
    command: RegistryAction,
    result: RegistryEvent,
}

/// Admission and replay cannot be bypassed through public deserialization.
/// ```compile_fail
/// let world: cm_management::registry::RegistryWorld = serde_json::from_str("{}").unwrap();
/// ```
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct RegistryWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: RegistryFixture,
    selected_slot: u8,
    option_two: u8,
    events: Vec<RegistryEvent>,
    records: Vec<RegistryRecord>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LoadedRegistryWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: RegistryFixture,
    selected_slot: u8,
    option_two: u8,
    events: Vec<RegistryEvent>,
    records: Vec<RegistryRecord>,
}
impl RegistryWorld {
    pub fn from_fixture(fixture: RegistryFixture) -> Result<Self, String> {
        fixture.validate()?;
        Ok(Self {
            schema_version: 4,
            profile: format!("{}-human-registry-producer-v1", fixture.human.origin),
            session_id: format!("{}-registry-session-v1", fixture.human.origin),
            fixture_sha256: fixture.fingerprint()?,
            revision: 0,
            selected_slot: fixture.human.selected_slot,
            option_two: fixture.option_two,
            fixture,
            events: vec![],
            records: vec![],
        })
    }
    pub fn location(&self) -> HumanSlotLocation {
        HumanWorld::slot_location(self.fixture.human.registry_index, self.selected_slot)
    }
    pub fn apply(&mut self, command: RegistryAction) -> Result<RegistryEvent, String> {
        let (session, id, revision, club) = command.envelope();
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
        if revision != self.revision {
            return Err("stale-revision".into());
        }
        if self.records.len() >= MAX_COMMANDS {
            return Err("command-capacity".into());
        }
        if club != self.fixture.human.club_id {
            return Err("unknown-club".into());
        }
        let (offset, value) = match &command {
            RegistryAction::HumanCommand(c) => (
                0x9a69,
                u8::try_from(c.slot)
                    .ok()
                    .filter(|v| *v <= 1)
                    .ok_or("unsupported-human-slot")?,
            ),
            RegistryAction::RegistryOptionCommand(c) => (
                0x9b25,
                u8::try_from(c.value)
                    .ok()
                    .filter(|v| *v <= 1)
                    .ok_or("unsupported-registry-option")?,
            ),
        };
        let writes = vec![RegistryWrite {
            registry_index: self.fixture.human.registry_index,
            registry_offset: offset,
            width: 1,
            value,
        }];
        let event = match &command {
            RegistryAction::HumanCommand(_) => RegistryEvent::HumanSlotSelected {
                revision: self.revision + 1,
                club_id: club,
                old_slot: self.selected_slot,
                new_slot: value,
                ordered_writes: writes,
            },
            RegistryAction::RegistryOptionCommand(_) => RegistryEvent::RegistryOptionTwoSet {
                revision: self.revision + 1,
                club_id: club,
                old_value: self.option_two,
                new_value: value,
                ordered_writes: writes,
            },
        };
        match &command {
            RegistryAction::HumanCommand(_) => self.selected_slot = value,
            RegistryAction::RegistryOptionCommand(_) => self.option_two = value,
        }
        self.revision += 1;
        self.events.push(event.clone());
        self.records.push(RegistryRecord {
            command,
            result: event.clone(),
        });
        Ok(event)
    }
    pub fn save(&self) -> Result<String, String> {
        let payload = serde_json::to_string(self).map_err(|e| e.to_string())?;
        serde_json::to_string(&Save {
            magic: "CM-PLAN-SLICE".into(),
            schema_version: 4,
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
            || save.schema_version != 4
            || save.payload.len() != save.payload_bytes
            || hash(save.payload.as_bytes()) != save.payload_sha256
        {
            return Err("save-integrity".into());
        }
        let data: LoadedRegistryWorld =
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
            selected_slot: data.selected_slot,
            option_two: data.option_two,
            events: data.events,
            records: data.records,
        };
        if replay != candidate {
            return Err("unsupported-or-inconsistent-state".into());
        }
        Ok(candidate)
    }
}
