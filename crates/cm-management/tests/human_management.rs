use cm_management::{Engine, World};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
const FIXTURE: &str = include_str!("fixtures/synthetic-human-registry.json");
fn request(engine: &mut Engine, op: Value) -> Value {
    engine.request(&serde_json::to_vec(&op).unwrap())
}
fn import(engine: &mut Engine) -> Value {
    request(
        engine,
        json!({"action":"import_human_reference","fixture":FIXTURE}),
    )
}
fn command(id: &str, revision: u32, slot: i32) -> Value {
    json!({"action":"human_command","command":{"session_id":"synthetic-human-regression-session-v1",
          "command_id":id,"expected_revision":revision,"club_id":7,"slot":slot}})
}
#[test]
fn matches_original_ordered_effects_locations_and_repeated_write() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/human-registry-oracle-v1.json"
    ))
    .unwrap();
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    assert_eq!(initial["ok"], true);
    for (revision, case) in oracle["cases"].as_array().unwrap().iter().enumerate() {
        let response = request(
            &mut engine,
            command(
                &format!("oracle-{revision}"),
                revision as u32,
                case["option"].as_i64().unwrap() as i32,
            ),
        );
        assert_eq!(response["ok"], true);
        assert_eq!(response["human_slot_location"], case["location"]);
        assert_eq!(response["result"]["old_slot"], case["previous_slot"]);
        assert_eq!(response["result"]["new_slot"], case["selected_slot"]);
        let actual = &response["result"]["ordered_writes"][0];
        let expected = &case["ordered_writes"][0];
        for field in ["registry_offset", "width", "value"] {
            assert_eq!(actual[field], expected[field]);
        }
        assert_eq!(actual["registry_index"], 15);
        assert_eq!(response["state"]["fixture"], initial["state"]["fixture"]);
        assert_eq!(response["plan_locations"], json!([]));
    }
}
#[test]
fn invalid_commands_and_cross_profile_operations_are_atomic() {
    let mut engine = Engine::default();
    let legacy = request(&mut engine, command("not-supported", 0, 0));
    assert_eq!(legacy["error"], "unsupported-command");
    let initial = import(&mut engine);
    let mut wrong_club = command("club", 0, 0);
    wrong_club["command"]["club_id"] = json!(8);
    let mut wrong_session = command("session", 0, 0);
    wrong_session["command"]["session_id"] = json!("wrong");
    for op in [
        command("negative", 0, -1),
        command("upper", 0, 2),
        command("wide", 0, 65537),
        command("stale", 1, 0),
        command("bad id", 0, 0),
        wrong_club,
        wrong_session,
        json!({"action":"command","command":{"session_id":"synthetic-human-regression-session-v1",
                   "command_id":"legacy","expected_revision":0,"club_id":7,"plan_id":0}}),
    ] {
        let result = request(&mut engine, op);
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], initial["state"]);
    }
}
#[test]
fn save_reload_replay_dedup_continuation_and_cross_profile_switching() {
    let mut engine = Engine::default();
    import(&mut engine);
    let first = command("first", 0, 1);
    request(&mut engine, first.clone());
    let save = request(&mut engine, json!({"action":"save"}));
    let next = command("next", 1, 0);
    let expected = request(&mut engine, next.clone());
    request(&mut engine, json!({"action":"reset"}));
    let restored = request(&mut engine, json!({"action":"load","save":save["result"]}));
    assert_eq!(restored["state"], save["state"]);
    let duplicate = request(&mut engine, first);
    assert_eq!(duplicate["state"], restored["state"]);
    let conflict = request(&mut engine, command("first", 0, 0));
    assert_eq!(conflict["error"], "command-id-conflict");
    assert_eq!(conflict["state"], restored["state"]);
    assert_eq!(request(&mut engine, next), expected);
    let legacy = include_str!("fixtures/legacy-plan-v1.json");
    assert_eq!(World::load(legacy).unwrap().save().unwrap(), legacy);
    let old = request(&mut engine, json!({"action":"load","save":legacy}));
    assert_eq!(old["state"]["schema_version"], 1);
    assert!(old.get("human_slot_location").is_none());
    assert_eq!(
        request(&mut engine, json!({"action":"save"}))["result"],
        legacy
    );
    request(&mut engine, json!({"action":"load","save":save["result"]}));
    let ordinary = include_str!("fixtures/synthetic-managers-v1.json");
    let switched = request(
        &mut engine,
        json!({"action":"import_reference","fixture":ordinary}),
    );
    assert_eq!(switched["state"]["schema_version"], 2);
    assert!(switched.get("human_slot_location").is_none());
}
#[test]
fn checksum_repaired_state_event_and_fixture_corruption_still_rejects() {
    let mut engine = Engine::default();
    import(&mut engine);
    request(&mut engine, command("first", 0, 1));
    let save = request(&mut engine, json!({"action":"save"}));
    let original: Value = serde_json::from_str(save["result"].as_str().unwrap()).unwrap();
    for path in [
        "/schema_version",
        "/revision",
        "/selected_slot",
        "/events/0/new_slot",
        "/events/0/ordered_writes/0/registry_offset",
        "/records/0/result/ordered_writes/0/width",
        "/fixture/registry_index",
        "/fixture/manager_id",
    ] {
        let mut envelope = original.clone();
        let mut payload: Value =
            serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
        *payload.pointer_mut(path).unwrap() = json!(999);
        let encoded = payload.to_string();
        envelope["payload_bytes"] = json!(encoded.len());
        envelope["payload_sha256"] = json!(format!("{:x}", Sha256::digest(encoded.as_bytes())));
        envelope["payload"] = json!(encoded);
        let result = request(
            &mut engine,
            json!({"action":"load","save":envelope.to_string()}),
        );
        assert_eq!(result["ok"], false, "{path}");
        assert_eq!(result["state"], save["state"]);
    }
}
#[test]
fn unqualified_fixture_and_origin_cannot_self_admit() {
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    for (key, value) in [
        ("origin", json!("captured-bosman-human-registry")),
        ("club_id", json!(8)),
        ("registry_index", json!(14)),
        ("selected_slot", json!(1)),
        ("registry_row_sha256", json!("c".repeat(64))),
        ("staff_count", json!(0)),
        ("manager_id", json!(83)),
    ] {
        let mut fixture: Value = serde_json::from_str(FIXTURE).unwrap();
        fixture[key] = value;
        let result = request(
            &mut engine,
            json!({"action":"import_human_reference","fixture":fixture.to_string()}),
        );
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], initial["state"]);
    }
}
#[test]
fn command_capacity_stops_mutation_but_retains_retry() {
    let mut engine = Engine::default();
    import(&mut engine);
    for revision in 0..256 {
        assert_eq!(
            request(
                &mut engine,
                command(&format!("c{revision}"), revision, (revision % 2) as i32)
            )["ok"],
            true
        );
    }
    let before = request(&mut engine, json!({"action":"state"}));
    let full = request(&mut engine, command("full", 256, 0));
    assert_eq!(full["error"], "command-capacity");
    assert_eq!(full["state"], before["state"]);
    assert_eq!(
        request(&mut engine, command("c0", 0, 0))["state"],
        before["state"]
    );
}

#[test]
fn fresh_capture_identity_does_not_authorize_hybrid_fixture_or_resealed_save() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/fresh-human-registry-oracle-v1.json"
    ))
    .unwrap();
    // Keep all entity/count fields fictional; public capture hashes alone must
    // not turn this structurally valid projection into an admitted real fixture.
    let mut hybrid: Value = serde_json::from_str(FIXTURE).unwrap();
    hybrid["origin"] = json!("captured-bosman-human-registry");
    hybrid["source_capture_sha256"] = oracle["capture"]["source_capture_sha256"].clone();
    hybrid["registry_row_sha256"] = oracle["state"]["registry_row_sha256"].clone();
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    let rejected = request(
        &mut engine,
        json!({"action":"import_human_reference","fixture":hybrid.to_string()}),
    );
    assert_eq!(rejected["error"], "unqualified-human-fixture");
    assert_eq!(rejected["state"], initial["state"]);
    let saved = request(&mut engine, json!({"action":"save"}));
    let mut envelope: Value = serde_json::from_str(saved["result"].as_str().unwrap()).unwrap();
    let mut payload: Value = serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
    payload["fixture"] = hybrid;
    let encoded = payload.to_string();
    envelope["payload_bytes"] = json!(encoded.len());
    envelope["payload_sha256"] = json!(format!("{:x}", Sha256::digest(encoded.as_bytes())));
    envelope["payload"] = json!(encoded);
    let rejected = request(
        &mut engine,
        json!({"action":"load","save":envelope.to_string()}),
    );
    assert_eq!(rejected["error"], "unqualified-human-fixture");
    assert_eq!(rejected["state"], initial["state"]);
}
