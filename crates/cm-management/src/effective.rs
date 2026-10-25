//! Explicit connected effective-plan lookup over independently admitted snapshots.
//! Rendering never executes the side-effecting original lookup.
use crate::human::{HumanCommand, HumanSlotLocation, HumanWorld, RegistryWrite};
use crate::registry::{RegistryFixture, RegistryOptionCommand};
use crate::{MAX_BYTES, MAX_COMMANDS, Save, hash};
use serde::{Deserialize, Serialize};

// Independently admitted exact projections; see PC_R7_EFFECTIVE_PLAN.md.
const PRIVATE_FIXTURES: &[&str] = &[
    "25464b62ef384947465583f38824091d0aeb1a76a901b3e6f9a74f4e08e80aa9",
    "e7304d465638b1cfccb0ac337f38fd72f364a47632b494a96f4ba6771de4391f",
];
const SYNTHETIC_FIXTURES: &[&str] =
    &["950b8ed556adc847a9f81d302278e624286b98f5fde03a9f29204be08ca11584"];

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct OrdinaryProjection {
    pub first_bank_count: u32,
    pub second_bank_count: u32,
    pub selected_plan: i32,
    pub mapping_row_sha256: String,
    pub first_bank_sha256: String,
    pub second_bank_sha256: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct EffectiveFixture {
    pub schema_version: u32,
    pub registry: RegistryFixture,
    pub ordinary: OrdinaryProjection,
}
impl EffectiveFixture {
    pub fn parse(encoded: &str) -> Result<Self, String> {
        if encoded.len() > 65536 {
            return Err("fixture-too-large".into());
        }
        let fixture: Self =
            serde_json::from_str(encoded).map_err(|_| "invalid-effective-fixture")?;
        fixture.validate()?;
        Ok(fixture)
    }
    pub fn fingerprint(&self) -> Result<String, String> {
        Ok(hash(
            &serde_json::to_vec(
                &serde_json::to_value(self).map_err(|_| "invalid-effective-fixture")?,
            )
            .map_err(|_| "invalid-effective-fixture")?,
        ))
    }
    pub fn validate(&self) -> Result<(), String> {
        self.registry.validate()?;
        if self.schema_version != 3
            || self.ordinary.first_bank_count != 17
            || self.ordinary.second_bank_count != 28
            || self.ordinary.selected_plan != 0
        {
            return Err("unsupported-effective-domain".into());
        }
        let fingerprint = self.fingerprint()?;
        let admitted = match self.registry.human.origin.as_str() {
            "captured-bosman-human-registry" => PRIVATE_FIXTURES.contains(&fingerprint.as_str()),
            "synthetic-human-regression" => SYNTHETIC_FIXTURES.contains(&fingerprint.as_str()),
            _ => false,
        };
        if !admitted {
            return Err("unqualified-effective-fixture".into());
        }
        Ok(())
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum EffectiveLocation {
    OrdinaryBank {
        bank: String,
        index: u32,
        byte_offset: u32,
    },
    HumanRegistry {
        registry_index: u32,
        slot: u8,
        byte_offset: u32,
    },
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(
    tag = "action",
    content = "command",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum EffectiveAction {
    HumanCommand(HumanCommand),
    EffectivePlanCommand(HumanCommand),
    RegistryOptionCommand(RegistryOptionCommand),
}
impl EffectiveAction {
    fn envelope(&self) -> (&str, &str, u32, u32) {
        match self {
            Self::HumanCommand(c) | Self::EffectivePlanCommand(c) => {
                (&c.session_id, &c.command_id, c.expected_revision, c.club_id)
            }
            Self::RegistryOptionCommand(c) => {
                (&c.session_id, &c.command_id, c.expected_revision, c.club_id)
            }
        }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", deny_unknown_fields)]
pub enum EffectiveEvent {
    EffectivePlanLookedUp {
        revision: u32,
        club_id: u32,
        requested_slot: u8,
        old_slot: u8,
        new_slot: u8,
        option_two: u8,
        branch: String,
        location: EffectiveLocation,
        ordered_writes: Vec<RegistryWrite>,
    },

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
struct EffectiveRecord {
    command: EffectiveAction,
    result: EffectiveEvent,
}

/// Admission and replay cannot be bypassed through public deserialization.
/// ```compile_fail
/// let world: cm_management::effective::EffectiveWorld = serde_json::from_str("{}").unwrap();
/// ```
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct EffectiveWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: EffectiveFixture,
    selected_slot: u8,
    option_two: u8,
    events: Vec<EffectiveEvent>,
    records: Vec<EffectiveRecord>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LoadedEffectiveWorld {
    schema_version: u32,
    profile: String,
    fixture_sha256: String,
    session_id: String,
    revision: u32,
    fixture: EffectiveFixture,
    selected_slot: u8,
    option_two: u8,
    events: Vec<EffectiveEvent>,
    records: Vec<EffectiveRecord>,
}
impl EffectiveWorld {
    pub fn from_fixture(fixture: EffectiveFixture) -> Result<Self, String> {
        fixture.validate()?;
        Ok(Self {
            schema_version: 5,
            profile: format!("{}-effective-plan-v1", fixture.registry.human.origin),
            session_id: format!("{}-effective-session-v1", fixture.registry.human.origin),
            fixture_sha256: fixture.fingerprint()?,
            revision: 0,
            selected_slot: fixture.registry.human.selected_slot,
            option_two: fixture.registry.option_two,
            fixture,
            events: vec![],
            records: vec![],
        })
    }
    pub fn location(&self) -> HumanSlotLocation {
        HumanWorld::slot_location(
            self.fixture.registry.human.registry_index,
            self.selected_slot,
        )
    }
    /// Historical result of the last explicit lookup, never an implicit lookup.
    pub fn last_lookup(&self) -> Option<&EffectiveEvent> {
        self.events
            .iter()
            .rev()
            .find(|event| matches!(event, EffectiveEvent::EffectivePlanLookedUp { .. }))
    }
    pub fn apply(&mut self, command: EffectiveAction) -> Result<EffectiveEvent, String> {
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
        if club != self.fixture.registry.human.club_id {
            return Err("unknown-club".into());
        }
        let value = match &command {
            EffectiveAction::HumanCommand(c) | EffectiveAction::EffectivePlanCommand(c) => {
                u8::try_from(c.slot)
                    .ok()
                    .filter(|v| *v <= 1)
                    .ok_or("unsupported-human-slot")?
            }
            EffectiveAction::RegistryOptionCommand(c) => u8::try_from(c.value)
                .ok()
                .filter(|v| *v <= 1)
                .ok_or("unsupported-registry-option")?,
        };
        let write = |offset| {
            vec![RegistryWrite {
                registry_index: self.fixture.registry.human.registry_index,
                registry_offset: offset,
                width: 1,
                value,
            }]
        };
        let revision = self.revision + 1;
        let event = match &command {
            EffectiveAction::HumanCommand(_) => EffectiveEvent::HumanSlotSelected {
                revision,
                club_id: club,
                old_slot: self.selected_slot,
                new_slot: value,
                ordered_writes: write(0x9a69),
            },
            EffectiveAction::RegistryOptionCommand(_) => EffectiveEvent::RegistryOptionTwoSet {
                revision,
                club_id: club,
                old_value: self.option_two,
                new_value: value,
                ordered_writes: write(0x9b25),
            },
            EffectiveAction::EffectivePlanCommand(_) => {
                let fallback = self.fixture.registry.guard_9a01 != 0 && self.option_two == 0;
                let (branch, location, new_slot, writes) = if fallback {
                    (
                        "ordinary_fallback",
                        EffectiveLocation::OrdinaryBank {
                            bank: "first".into(),
                            index: 0,
                            byte_offset: 0,
                        },
                        self.selected_slot,
                        vec![],
                    )
                } else {
                    (
                        if self.fixture.registry.guard_9a01 == 0 {
                            "registry_guard_zero"
                        } else {
                            "registry_option_enabled"
                        },
                        EffectiveLocation::HumanRegistry {
                            registry_index: self.fixture.registry.human.registry_index,
                            slot: value,
                            byte_offset: u32::from(value) * 7885,
                        },
                        value,
                        write(0x9a69),
                    )
                };
                EffectiveEvent::EffectivePlanLookedUp {
                    revision,
                    club_id: club,
                    requested_slot: value,
                    old_slot: self.selected_slot,
                    new_slot,
                    option_two: self.option_two,
                    branch: branch.into(),
                    location,
                    ordered_writes: writes,
                }
            }
        };
        match &event {
            EffectiveEvent::HumanSlotSelected { new_slot, .. }
            | EffectiveEvent::EffectivePlanLookedUp { new_slot, .. } => {
                self.selected_slot = *new_slot
            }
            EffectiveEvent::RegistryOptionTwoSet { new_value, .. } => self.option_two = *new_value,
        }
        self.revision += 1;
        self.events.push(event.clone());
        self.records.push(EffectiveRecord {
            command,
            result: event.clone(),
        });
        Ok(event)
    }
    pub fn save(&self) -> Result<String, String> {
        let payload = serde_json::to_string(self).map_err(|e| e.to_string())?;
        serde_json::to_string(&Save {
            magic: "CM-PLAN-SLICE".into(),
            schema_version: 5,
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
            || save.schema_version != 5
            || save.payload.len() != save.payload_bytes
            || hash(save.payload.as_bytes()) != save.payload_sha256
        {
            return Err("save-integrity".into());
        }
        let data: LoadedEffectiveWorld =
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
