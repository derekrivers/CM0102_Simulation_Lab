//! Direct human registry selector + resolver; see PC_R4_HUMAN_REGISTRY.md.
//! Preinitialized immutable binding only. No outer-getter/holiday or match claim.
use crate::{MAX_BYTES, MAX_COMMANDS, Save, hash};
use serde::{Deserialize, Serialize};

pub const PRIVATE_FIXTURE_SHA256: &str =
    "986a2f582095c698413a6ab617a8c487bf0dfb78a7b7e953f7d83b282af7dc6d";
// Independently reviewed R5 projection; separate from retained-state identity.
pub const FRESH_PRIVATE_FIXTURE_SHA256: &str =
    "15697cfbb10725a20c50a8bb290ff8fe85fd05c572d8f7302d4ddbc95e842dc2";
pub const SYNTHETIC_FIXTURE_SHA256: &str =
    "c51b2e88302b512340454ce969c079c376b9ea3563ce777335556e6a449f5603";
const SPECIMEN: &str = "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct HumanRegistryFixture {
    pub schema_version: u32,
    pub origin: String,
    pub source_capture_sha256: String,
    pub specimen_sha256: String,
    pub club_count: u32,
    pub ordinary_club_limit: u32,
    pub staff_count: u32,
    pub registry_count: u32,
    pub club_id: u32,
    pub manager_id: u32,
    pub registry_index: u32,
    pub selected_slot: u8,
    pub registry_row_sha256: String,
}
impl HumanRegistryFixture {
    pub fn parse(encoded: &str) -> Result<Self, String> {
        if encoded.len() > 65536 {
            return Err("fixture-too-large".into());
        }
        let fixture: Self = serde_json::from_str(encoded).map_err(|_| "invalid-human-fixture")?;
        fixture.validate()?;
        Ok(fixture)
    }
    pub fn fingerprint(&self) -> Result<String, String> {
        let value = serde_json::to_value(self).map_err(|_| "invalid-human-fixture")?;
        Ok(hash(
            &serde_json::to_vec(&value).map_err(|_| "invalid-human-fixture")?,
        ))
    }
    pub fn validate(&self) -> Result<(), String> {
        let hex = |s: &str| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit());
        if self.schema_version != 1
            || self.specimen_sha256 != SPECIMEN
            || !hex(&self.source_capture_sha256)
            || !hex(&self.registry_row_sha256)
            || self.club_count > 100_000
            || self.ordinary_club_limit == 0
            || self.ordinary_club_limit > self.club_count
            || self.club_id >= self.ordinary_club_limit
            || self.staff_count < 17
            || self.staff_count > 1_000_000
            || self.registry_count != 16
            || self.registry_index >= self.registry_count
            || self.manager_id < self.staff_count - 16
            || self.manager_id >= self.staff_count
            || self.registry_index != self.manager_id - (self.staff_count - 16)
            || self.selected_slot > 1
        {
            return Err("unsupported-human-domain".into());
        }
        let fingerprint = self.fingerprint()?;
        let admitted = match self.origin.as_str() {
            "captured-bosman-human-registry" => {
                fingerprint == PRIVATE_FIXTURE_SHA256 || fingerprint == FRESH_PRIVATE_FIXTURE_SHA256
            }
            "synthetic-human-regression" => fingerprint == SYNTHETIC_FIXTURE_SHA256,
            _ => false,
        };
        if !admitted {
            return Err("unqualified-human-fixture".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct HumanCommand {
    pub session_id: String,
    pub command_id: String,
    pub expected_revision: u32,
    pub club_id: u32,
    pub slot: i32,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RegistryWrite {
    pub registry_index: u32,
    pub registry_offset: u32,
    pub width: u8,
    pub value: u8,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct HumanEvent {
    pub kind: String,
    pub revision: u32,
    pub club_id: u32,
    pub old_slot: u8,
    pub new_slot: u8,
    pub ordered_writes: Vec<RegistryWrite>,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct HumanRecord {
    command: HumanCommand,
    result: HumanEvent,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct HumanSlotLocation {
    registry_index: u32,
    slot: u8,
    byte_offset: u32,
}
/// No public construction or deserialization bypasses fixture and replay admission.
/// ```compile_fail
/// let world: cm_management::human::HumanWorld = serde_json::from_str("{}").unwrap();
/// ```
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct HumanWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: HumanRegistryFixture,
    selected_slot: u8,
    events: Vec<HumanEvent>,
    records: Vec<HumanRecord>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LoadedHumanWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: HumanRegistryFixture,
    selected_slot: u8,
    events: Vec<HumanEvent>,
    records: Vec<HumanRecord>,
}
impl HumanWorld {
    pub fn from_fixture(fixture: HumanRegistryFixture) -> Result<Self, String> {
        fixture.validate()?;
        Ok(Self {
            schema_version: 3,
            profile: format!("{}-direct-human-slot-v1", fixture.origin),
            fixture_sha256: fixture.fingerprint()?,
            session_id: format!("{}-session-v1", fixture.origin),
            revision: 0,
            selected_slot: fixture.selected_slot,
            fixture,
            events: vec![],
            records: vec![],
        })
    }
    pub fn location(&self) -> HumanSlotLocation {
        HumanSlotLocation {
            registry_index: self.fixture.registry_index,
            slot: self.selected_slot,
            byte_offset: u32::from(self.selected_slot) * 7885,
        }
    }
    pub fn apply(&mut self, command: HumanCommand) -> Result<HumanEvent, String> {
        if command.session_id != self.session_id {
            return Err("wrong-session".into());
        }
        if command.command_id.is_empty()
            || command.command_id.len() > 64
            || !command
                .command_id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"-_".contains(&c))
        {
            return Err("invalid-command-id".into());
        }
        if let Some(record) = self
            .records
            .iter()
            .find(|r| r.command.command_id == command.command_id)
        {
            return if record.command == command {
                Ok(record.result.clone())
            } else {
                Err("command-id-conflict".into())
            };
        }
        if command.expected_revision != self.revision {
            return Err("stale-revision".into());
        }
        if self.records.len() >= MAX_COMMANDS {
            return Err("command-capacity".into());
        }
        if command.club_id != self.fixture.club_id {
            return Err("unknown-club".into());
        }
        let slot = u8::try_from(command.slot).map_err(|_| "unsupported-human-slot")?;
        if slot > 1 {
            return Err("unsupported-human-slot".into());
        }
        let event = HumanEvent {
            kind: "HumanSlotSelected".into(),
            revision: self.revision + 1,
            club_id: command.club_id,
            old_slot: self.selected_slot,
            new_slot: slot,
            ordered_writes: vec![RegistryWrite {
                registry_index: self.fixture.registry_index,
                registry_offset: 0x9a69,
                width: 1,
                value: slot,
            }],
        };
        self.selected_slot = slot;
        self.revision += 1;
        self.events.push(event.clone());
        self.records.push(HumanRecord {
            command,
            result: event.clone(),
        });
        Ok(event)
    }
    pub fn save(&self) -> Result<String, String> {
        let payload = serde_json::to_string(self).map_err(|e| e.to_string())?;
        serde_json::to_string(&Save {
            magic: "CM-PLAN-SLICE".into(),
            schema_version: 3,
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
            || save.schema_version != 3
            || save.payload.len() != save.payload_bytes
            || hash(save.payload.as_bytes()) != save.payload_sha256
        {
            return Err("save-integrity".into());
        }
        let data: LoadedHumanWorld =
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
            events: data.events,
            records: data.records,
        };
        if replay != candidate {
            return Err("unsupported-or-inconsistent-state".into());
        }
        Ok(candidate)
    }
}
