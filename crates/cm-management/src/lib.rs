//! Bounded synthetic-state tactical-plan selection; see PC_R3_MANAGEMENT.md.
//! No original UI, formation contents or saved-game compatibility is claimed.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const PROFILE: &str = "synthetic-null-owner-plan-selection-v1";
const SESSION: &str = "fictional-club-session-v1";
const MAX_BYTES: usize = 1_048_576;
const MAX_COMMANDS: usize = 256;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Club {
    pub id: u32,
    pub name: String,
    pub selected_plan: u16,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Player {
    pub id: u32,
    pub club_id: u32,
    pub name: String,
    pub position: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub id: u16,
    pub name: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Command {
    pub session_id: String,
    pub command_id: String,
    pub expected_revision: u32,
    pub club_id: u32,
    pub plan_id: i32,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub kind: String,
    pub revision: u32,
    pub club_id: u32,
    pub old_plan: u16,
    pub new_plan: u16,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub command: Command,
    pub result: Event,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct World {
    pub schema_version: u32,
    pub profile: String,
    pub fixture_sha256: String,
    pub session_id: String,
    pub revision: u32,
    pub clubs: Vec<Club>,
    pub players: Vec<Player>,
    pub plans: Vec<Plan>,
    pub events: Vec<Event>,
    pub records: Vec<Record>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Save {
    magic: String,
    schema_version: u32,
    payload_bytes: usize,
    payload_sha256: String,
    payload: String,
}

fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

impl Default for World {
    fn default() -> Self {
        let clubs = ["Northbridge", "Westford", "Eastmere", "Southbank"]
            .iter()
            .enumerate()
            .map(|(id, name)| Club {
                id: id as u32,
                name: (*name).into(),
                selected_plan: 0,
            })
            .collect();
        let players = [
            ("Alex Vale", "GK"),
            ("Morgan Reed", "DF"),
            ("Casey Brook", "MF"),
            ("Jamie Ash", "FW"),
        ]
        .iter()
        .enumerate()
        .map(|(id, (name, position))| Player {
            id: id as u32,
            club_id: 0,
            name: (*name).into(),
            position: (*position).into(),
        })
        .collect();
        let plans = (0..5)
            .map(|id| Plan {
                id,
                name: format!("Research plan {}", id + 1),
            })
            .collect();
        let mut world = Self {
            schema_version: 1,
            profile: PROFILE.into(),
            fixture_sha256: String::new(),
            session_id: SESSION.into(),
            revision: 0,
            clubs,
            players,
            plans,
            events: vec![],
            records: vec![],
        };
        // Identity binds the supported fixture including all names/references, before any commands.
        world.fixture_sha256 = hash(&serde_json::to_vec(&world).expect("fixed fixture serializes"));
        world
    }
}

impl World {
    pub fn apply(&mut self, command: Command) -> Result<Event, String> {
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
        let plan = u16::try_from(command.plan_id).map_err(|_| "unsupported-plan")?;
        if usize::from(plan) >= self.plans.len() {
            return Err("unsupported-plan".into());
        }
        let club = self
            .clubs
            .get(command.club_id as usize)
            .filter(|c| c.id == command.club_id)
            .ok_or("unknown-club")?;
        let event = Event {
            kind: "PlanSelected".into(),
            revision: self.revision + 1,
            club_id: club.id,
            old_plan: club.selected_plan,
            new_plan: plan,
        };
        self.clubs[command.club_id as usize].selected_plan = plan;
        self.revision += 1;
        self.events.push(event.clone());
        self.records.push(Record {
            command,
            result: event.clone(),
        });
        Ok(event)
    }

    pub fn save(&self) -> Result<String, String> {
        let payload = serde_json::to_string(self).map_err(|e| e.to_string())?;
        serde_json::to_string(&Save {
            magic: "CM-PLAN-SLICE".into(),
            schema_version: 1,
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
            || save.schema_version != 1
            || save.payload.len() != save.payload_bytes
            || hash(save.payload.as_bytes()) != save.payload_sha256
        {
            return Err("save-integrity".into());
        }
        let candidate: World =
            serde_json::from_str(&save.payload).map_err(|_| "invalid-save-payload")?;
        if candidate.records.len() > MAX_COMMANDS {
            return Err("command-capacity".into());
        }
        // Reconstruct the admitted state and validate every reference, profile, event and dedup record.
        // No decoded world is committed until this full comparison succeeds.
        let mut replay = World::default();
        for record in &candidate.records {
            replay.apply(record.command.clone())?;
        }
        if replay != candidate {
            return Err("unsupported-or-inconsistent-state".into());
        }
        Ok(candidate)
    }
}

#[derive(Deserialize)]
#[serde(tag = "action", rename_all = "snake_case", deny_unknown_fields)]
pub enum Operation {
    Reset {},
    State {},
    Command { command: Command },
    Save {},
    Load { save: String },
}

#[derive(Default)]
pub struct Engine {
    world: World,
}
impl Engine {
    pub fn request(&mut self, bytes: &[u8]) -> serde_json::Value {
        let result = if bytes.len() > MAX_BYTES {
            Err("request-too-large".into())
        } else {
            serde_json::from_slice::<Operation>(bytes).map_err(|_| "invalid-request".into())
        };
        let result = result.and_then(|op| match op {
            Operation::Reset {} => {
                self.world = World::default();
                Ok(serde_json::Value::Null)
            }
            Operation::State {} => Ok(serde_json::Value::Null),
            Operation::Command { command } => self
                .world
                .apply(command)
                .map(|e| serde_json::to_value(e).expect("event")),
            Operation::Save {} => self.world.save().map(serde_json::Value::String),
            Operation::Load { save } => World::load(&save).map(|world| {
                self.world = world;
                serde_json::Value::Null
            }),
        });
        match result {
            Ok(value) => serde_json::json!({"ok":true,"result":value,"state":self.world}),
            Err(error) => serde_json::json!({"ok":false,"error":error,"state":self.world}),
        }
    }
}

#[cfg(target_arch = "wasm32")]
mod wasm {
    use super::*;
    use std::cell::RefCell;
    thread_local! {
        static ENGINE: RefCell<Engine> = RefCell::new(Engine::default());
        static INPUT: RefCell<Vec<u8>> = RefCell::new(vec![0; MAX_BYTES]);
        static OUTPUT: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
    }
    #[unsafe(no_mangle)]
    pub extern "C" fn input_ptr() -> *mut u8 {
        INPUT.with(|b| b.borrow_mut().as_mut_ptr())
    }
    #[unsafe(no_mangle)]
    pub extern "C" fn request(length: usize) -> usize {
        let response = if length > MAX_BYTES {
            serde_json::json!({"ok":false,"error":"request-too-large"})
        } else {
            INPUT.with(|b| ENGINE.with(|e| e.borrow_mut().request(&b.borrow()[..length])))
        };
        OUTPUT.with(|b| {
            *b.borrow_mut() = serde_json::to_vec(&response).expect("response");
            b.borrow().len()
        })
    }
    #[unsafe(no_mangle)]
    pub extern "C" fn output_ptr() -> *const u8 {
        OUTPUT.with(|b| b.borrow().as_ptr())
    }
}
