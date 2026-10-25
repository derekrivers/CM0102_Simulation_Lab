//! Admission for reviewed reference projections; raw captures stay outside Git.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const PRIVATE_FIXTURE_SHA256: &str =
    "b68bfba221cccc84a92cfa63804487e206b3858be635e988738c5fc701c29711";
// A separate, redistributable fictional fixture exercises the same admission path.
pub const SYNTHETIC_FIXTURE_SHA256: &str =
    "162a95a541093ebe6af32cbbb2005eaeb62ee41580e7e53e9f9283da550b941b";
const SPECIMEN: &str = "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ReferenceClub {
    pub id: u32,
    pub name: String,
    pub manager_id: u32,
    pub manager_name: String,
    pub selected_plan: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ReferenceFixture {
    pub schema_version: u32,
    pub origin: String,
    pub source_capture_sha256: String,
    pub specimen_sha256: String,
    pub club_count: u32,
    pub staff_count: u32,
    pub ordinary_club_limit: u32,
    pub first_bank_count: u32,
    pub second_bank_count: u32,
    pub clubs: Vec<ReferenceClub>,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct PlanLocation {
    pub bank: &'static str,
    pub index: u32,
    pub byte_offset: u32,
}

/// The admitted ordinary-club bank path of original VA 00896660.
pub fn resolve_plan(first: u32, second: u32, plan: i32) -> Result<PlanLocation, String> {
    let total = first.checked_add(second).ok_or("invalid-bank-counts")?;
    if first == 0 || second == 0 || total > 32768 {
        return Err("invalid-bank-counts".into());
    }
    let plan = u32::try_from(plan).map_err(|_| "unsupported-plan")?;
    if plan >= total {
        return Err("unsupported-plan".into());
    }
    let (bank, index) = if plan < first {
        ("first", plan)
    } else {
        ("second", plan - first)
    };
    Ok(PlanLocation {
        bank,
        index,
        byte_offset: index * 6371,
    })
}

fn valid_name(name: &str) -> bool {
    !name.is_empty() && name.len() <= 128 && !name.chars().any(char::is_control)
}

impl ReferenceFixture {
    pub fn parse(encoded: &str) -> Result<Self, String> {
        if encoded.len() > 65536 {
            return Err("fixture-too-large".into());
        }
        let fixture: Self =
            serde_json::from_str(encoded).map_err(|_| "invalid-reference-fixture")?;
        fixture.validate()?;
        Ok(fixture)
    }

    pub fn fingerprint(&self) -> Result<String, String> {
        // Value's sorted map keys define the same compact UTF-8 canonical form as the extractor.
        let value = serde_json::to_value(self).map_err(|_| "invalid-reference-fixture")?;
        let bytes = serde_json::to_vec(&value).map_err(|_| "invalid-reference-fixture")?;
        Ok(format!("{:x}", Sha256::digest(bytes)))
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != 1
            || self.specimen_sha256 != SPECIMEN
            || self.source_capture_sha256.len() != 64
            || !self
                .source_capture_sha256
                .bytes()
                .all(|c| c.is_ascii_hexdigit())
            || self.ordinary_club_limit == 0
            || self.ordinary_club_limit > self.club_count
            || self.club_count > 100_000
            || self.staff_count < 17
            || self.staff_count > 1_000_000
            || self.clubs.len() != 3
        {
            return Err("unsupported-reference-domain".into());
        }
        for (index, club) in self.clubs.iter().enumerate() {
            if club.id >= self.ordinary_club_limit
                || club.manager_id >= self.staff_count - 16
                || !valid_name(&club.name)
                || !valid_name(&club.manager_name)
                || self.clubs[..index].iter().any(|other| other.id == club.id)
            {
                return Err("unsupported-club-manager-binding".into());
            }
            resolve_plan(
                self.first_bank_count,
                self.second_bank_count,
                club.selected_plan,
            )?;
        }
        let fingerprint = self.fingerprint()?;
        let accepted = match self.origin.as_str() {
            "captured-bosman" => fingerprint == PRIVATE_FIXTURE_SHA256,
            "synthetic-regression" => fingerprint == SYNTHETIC_FIXTURE_SHA256,
            _ => false,
        };
        if !accepted {
            return Err("unqualified-reference-fixture".into());
        }
        Ok(())
    }
}
