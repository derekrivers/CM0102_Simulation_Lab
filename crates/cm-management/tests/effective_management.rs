use cm_management::Engine;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
const FIXTURE: &str = include_str!("fixtures/synthetic-effective-plan.json");
fn request(engine: &mut Engine, operation: Value) -> Value {
    engine.request(&serde_json::to_vec(&operation).unwrap())
}
fn import(engine: &mut Engine) -> Value {
    request(
        engine,
        json!({"action":"import_effective_reference","fixture":FIXTURE}),
    )
}
fn command(kind: &str, id: &str, revision: u32, value: i32) -> Value {
    let action = match kind {
        "lookup" => "effective_plan_command",
        "select" => "human_command",
        "option" => "registry_option_command",
        _ => panic!("kind"),
    };
    let mut c = json!({"session_id":"synthetic-human-regression-effective-session-v1","command_id":id,"expected_revision":revision,"club_id":7});
    c[if kind == "option" { "value" } else { "slot" }] = json!(value);
    json!({"action":action,"command":c})
}
fn seal(mut envelope: Value, payload: Value) -> Value {
    let encoded = serde_json::to_string(&payload).unwrap();
    envelope["payload_bytes"] = json!(encoded.len());
    envelope["payload_sha256"] = json!(format!("{:x}", Sha256::digest(encoded.as_bytes())));
    envelope["payload"] = json!(encoded);
    json!({"action":"load","save":envelope.to_string()})
}
#[test]
fn connected_retained_oracle_matches_branch_location_and_every_effect() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/pc-r7-retained-effective-plan-v1.json"
    ))
    .unwrap();
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    assert_eq!(initial["ok"], true);
    assert_eq!(initial["state"]["schema_version"], 5);
    assert_eq!(initial["effective_plan_result"], Value::Null);
    for (i, c) in oracle["cases"].as_array().unwrap().iter().enumerate() {
        let kind = c["kind"].as_str().unwrap();
        let r = request(
            &mut engine,
            command(
                kind,
                &format!("oracle-{i}"),
                i as u32,
                c["value"].as_i64().unwrap() as i32,
            ),
        );
        assert_eq!(r["ok"], true);
        assert_eq!(r["state"]["selected_slot"], c["selected_slot"]);
        assert_eq!(r["state"]["option_two"], c["option_two"]);
        assert_eq!(r["state"]["fixture"], initial["state"]["fixture"]);
        let mut writes = c["ordered_writes"].clone();
        for w in writes.as_array_mut().unwrap() {
            w["registry_index"] = json!(15);
        }
        assert_eq!(r["result"]["ordered_writes"], writes);
        if kind == "lookup" {
            let mut location = c["location"].clone();
            if location["kind"] == "human_registry" {
                location["registry_index"] = json!(15);
            }
            assert_eq!(r["result"]["location"], location);
            assert_eq!(r["result"]["branch"], c["branch"]);
            assert_eq!(r["result"]["requested_slot"], c["value"]);
            assert_eq!(r["result"]["old_slot"], c["previous_slot"]);
            assert_eq!(r["result"]["new_slot"], c["selected_slot"]);
            assert_eq!(r["effective_plan_result"], r["result"]);
        }
    }
}
#[test]
fn lookup_is_explicit_and_three_commands_share_retry_history() {
    let mut engine = Engine::default();
    import(&mut engine);
    let first = command("lookup", "first", 0, 1);
    let one = request(&mut engine, first.clone());
    assert_eq!(one["result"]["branch"], "ordinary_fallback");
    assert_eq!(one["result"]["ordered_writes"], json!([]));
    assert_eq!(one["state"]["revision"], 1);
    let two = request(&mut engine, command("option", "option", 1, 1));
    assert_eq!(two["effective_plan_result"], one["result"]);
    assert_eq!(
        request(&mut engine, json!({"action":"state"}))["state"],
        two["state"]
    );
    assert_eq!(request(&mut engine, first)["result"], one["result"]);
    assert_eq!(
        request(&mut engine, command("select", "first", 0, 1))["error"],
        "command-id-conflict"
    );
    let three = request(&mut engine, command("lookup", "third", 2, 1));
    assert_eq!(three["result"]["branch"], "registry_option_enabled");
    assert_eq!(three["result"]["location"]["byte_offset"], 7885);
    let repeat = request(&mut engine, command("lookup", "repeat", 3, 1));
    assert_eq!(
        repeat["result"]["ordered_writes"],
        three["result"]["ordered_writes"]
    );
    assert_eq!(repeat["state"]["revision"], 4);
}
#[test]
fn invalid_command_and_fixture_inputs_reject_atomically() {
    let mut engine = Engine::default();
    assert_eq!(
        request(&mut engine, command("lookup", "old", 0, 0))["error"],
        "unsupported-command"
    );
    let initial = import(&mut engine);
    let mut invalid = vec![];
    for kind in ["lookup", "select", "option"] {
        for value in [-1, 2, 256, i32::MAX] {
            invalid.push(command(kind, "invalid", 0, value));
        }
    }
    invalid.push(command("lookup", "bad id", 0, 0));
    invalid.push(command("lookup", "stale", 1, 0));
    let mut club = command("lookup", "club", 0, 0);
    club["command"]["club_id"] = json!(8);
    invalid.push(club);
    let mut session = command("lookup", "session", 0, 0);
    session["command"]["session_id"] = json!("wrong");
    invalid.push(session);
    for field in [
        "first_bank_count",
        "second_bank_count",
        "selected_plan",
        "mapping_row_sha256",
        "first_bank_sha256",
        "second_bank_sha256",
    ] {
        let mut fixture: Value = serde_json::from_str(FIXTURE).unwrap();
        fixture["ordinary"][field] = if field.ends_with("sha256") {
            json!("0".repeat(64))
        } else {
            json!(99)
        };
        invalid.push(json!({"action":"import_effective_reference","fixture":fixture.to_string()}));
    }
    let mut changed: Value = serde_json::from_str(FIXTURE).unwrap();
    changed["registry"]["guard_9a01"] = json!(0);
    invalid.push(json!({"action":"import_effective_reference","fixture":changed.to_string()}));
    changed = serde_json::from_str(FIXTURE).unwrap();
    changed["extra"] = json!(1);
    invalid.push(json!({"action":"import_effective_reference","fixture":changed.to_string()}));
    for op in invalid {
        let result = request(&mut engine, op);
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], initial["state"]);
    }
}
#[test]
fn save_replay_rejects_resealed_history_and_preserves_continuation() {
    let mut engine = Engine::default();
    import(&mut engine);
    let prefix = [
        command("lookup", "a", 0, 1),
        command("option", "b", 1, 1),
        command("lookup", "c", 2, 1),
        command("select", "d", 3, 0),
    ];
    for op in prefix.clone() {
        assert_eq!(request(&mut engine, op)["ok"], true);
    }
    let saved = request(&mut engine, json!({"action":"save"}));
    let continuation = command("lookup", "next", 4, 1);
    let expected = request(&mut engine, continuation.clone());
    assert_eq!(
        request(&mut engine, json!({"action":"load","save":saved["result"]}))["state"],
        saved["state"]
    );
    assert_eq!(
        request(&mut engine, json!({"action":"save"}))["result"],
        saved["result"]
    );
    assert_eq!(request(&mut engine, continuation), expected);
    let current = request(&mut engine, json!({"action":"save"}));
    let envelope: Value = serde_json::from_str(current["result"].as_str().unwrap()).unwrap();
    let payload: Value = serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
    for index in 0..10 {
        let mut p = payload.clone();
        match index {
            0 => p["selected_slot"] = json!(0),
            1 => p["option_two"] = json!(0),
            2 => p["schema_version"] = json!(4),
            3 => p["events"][0]["location"]["index"] = json!(1),
            4 => p["events"][0]["branch"] = json!("registry_option_enabled"),
            5 => p["records"][2]["result"]["ordered_writes"][0]["width"] = json!(2),
            6 => p["records"].as_array_mut().unwrap().reverse(),
            7 => {
                let record = p["records"][0].clone();
                p["records"].as_array_mut().unwrap().push(record);
            }
            8 => p["fixture"]["ordinary"]["first_bank_sha256"] = json!("0".repeat(64)),
            9 => p["session_id"] = json!("other"),
            _ => unreachable!(),
        }
        let result = request(&mut engine, seal(envelope.clone(), p));
        assert_eq!(result["ok"], false, "tamper {index}");
        assert_eq!(result["state"], current["state"]);
    }
}
#[test]
fn version_one_through_four_roundtrip_without_migration() {
    let mut engine = Engine::default();
    let fixtures = [
        (
            "import_reference",
            include_str!("fixtures/synthetic-managers-v1.json"),
        ),
        (
            "import_human_reference",
            include_str!("fixtures/synthetic-human-registry.json"),
        ),
        (
            "import_registry_reference",
            include_str!("fixtures/synthetic-registry-producer.json"),
        ),
    ];
    let legacy = include_str!("fixtures/legacy-plan-v1.json");
    let mut saves = vec![legacy.to_string()];
    for (action, fixture) in fixtures {
        assert_eq!(
            request(&mut engine, json!({"action":action,"fixture":fixture}))["ok"],
            true
        );
        saves.push(
            request(&mut engine, json!({"action":"save"}))["result"]
                .as_str()
                .unwrap()
                .to_string(),
        );
    }
    for (i, save) in saves.iter().enumerate() {
        assert_eq!(import(&mut engine)["ok"], true);
        let loaded = request(&mut engine, json!({"action":"load","save":save}));
        assert_eq!(loaded["state"]["schema_version"], i + 1);
        assert!(loaded.get("effective_plan_result").is_none());
        assert_eq!(
            request(&mut engine, command("lookup", "unsupported", 0, 0))["error"],
            "unsupported-command"
        );
        assert_eq!(
            request(&mut engine, json!({"action":"save"}))["result"],
            *save
        );
    }
}
#[test]
fn capacity_and_retry_at_limit() {
    let mut engine = Engine::default();
    import(&mut engine);
    let first = command("lookup", "cap-0", 0, 0);
    for i in 0..256 {
        assert_eq!(
            request(&mut engine, command("lookup", &format!("cap-{i}"), i, 0))["ok"],
            true
        );
    }
    let before = request(&mut engine, json!({"action":"state"}));
    assert_eq!(request(&mut engine, first)["state"], before["state"]);
    let rejected = request(&mut engine, command("option", "over", 256, 1));
    assert_eq!(rejected["error"], "command-capacity");
    assert_eq!(rejected["state"], before["state"]);
}
