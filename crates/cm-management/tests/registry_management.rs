use cm_management::Engine;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
const FIXTURE: &str = include_str!("fixtures/synthetic-registry-producer.json");
#[test]
fn matches_qualified_original_producer_and_mixed_ordered_effects() {
    let oracle: Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/human-registry-producer-oracle-v1.json"
    ))
    .unwrap();
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    assert_eq!(initial["ok"], true);
    for (i, case) in oracle["producer_cases"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let result = request(
            &mut engine,
            command(
                &format!("original-{i}"),
                i as u32,
                case["value"].as_i64().unwrap() as i32,
                false,
            ),
        );
        assert_eq!(result["ok"], true);
        assert_eq!(result["result"]["old_value"], case["previous_value"]);
        assert_eq!(result["result"]["new_value"], case["new_value"]);
        let mut writes = case["ordered_writes"].clone();
        for write in writes.as_array_mut().unwrap() {
            write["registry_index"] = json!(15);
        }
        assert_eq!(result["result"]["ordered_writes"], writes);
        assert_eq!(result["state"]["selected_slot"], 0);
        assert_eq!(result["state"]["fixture"], initial["state"]["fixture"]);
    }
    import(&mut engine);
    for (i, case) in oracle["mixed_cases"].as_array().unwrap().iter().enumerate() {
        let slot = case["kind"] == "HumanSlotSelected";
        let result = request(
            &mut engine,
            command(
                &format!("mixed-{i}"),
                i as u32,
                case[if slot { "slot" } else { "value" }].as_i64().unwrap() as i32,
                slot,
            ),
        );
        assert_eq!(result["ok"], true);
        assert_eq!(result["state"]["selected_slot"], case["selected_slot"]);
        assert_eq!(result["state"]["option_two"], case["option_two"]);
        let mut writes = case["ordered_writes"].clone();
        for write in writes.as_array_mut().unwrap() {
            write["registry_index"] = json!(15);
        }
        assert_eq!(result["result"]["ordered_writes"], writes);
        assert_eq!(result["state"]["fixture"], initial["state"]["fixture"]);
    }
}
fn request(engine: &mut Engine, op: Value) -> Value {
    engine.request(&serde_json::to_vec(&op).unwrap())
}
fn import(engine: &mut Engine) -> Value {
    request(
        engine,
        json!({"action":"import_registry_reference","fixture":FIXTURE}),
    )
}
fn command(id: &str, revision: u32, value: i32, slot: bool) -> Value {
    let mut c = json!({"session_id":"synthetic-human-regression-registry-session-v1","command_id":id,"expected_revision":revision,"club_id":7});
    c[if slot { "slot" } else { "value" }] = json!(value);
    json!({"action":if slot {"human_command"} else {"registry_option_command"},"command":c})
}
#[test]
fn mixed_producers_preserve_independent_bytes_and_share_retry_scope() {
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    assert_eq!(initial["ok"], true);
    let first = command("option", 0, 1, false);
    let one = request(&mut engine, first.clone());
    assert_eq!(
        one["result"]["ordered_writes"],
        json!([{"registry_index":15,"registry_offset":0x9b25,"width":1,"value":1}])
    );
    assert_eq!(one["state"]["selected_slot"], 0);
    let two = request(&mut engine, command("slot", 1, 1, true));
    assert_eq!(two["state"]["option_two"], 1);
    assert_eq!(two["state"]["selected_slot"], 1);
    let three = request(&mut engine, command("repeat", 2, 1, false));
    assert_eq!(three["result"]["old_value"], 1);
    assert_eq!(three["result"]["new_value"], 1);
    assert_eq!(
        three["result"]["ordered_writes"],
        one["result"]["ordered_writes"]
    );
    assert_eq!(three["state"]["fixture"], initial["state"]["fixture"]);
    assert_eq!(request(&mut engine, first)["state"], three["state"]);
    let conflict = request(&mut engine, command("option", 0, 1, true));
    assert_eq!(conflict["error"], "command-id-conflict");
    assert_eq!(conflict["state"], three["state"]);
}
#[test]
fn invalid_envelopes_values_and_capabilities_are_atomic() {
    let mut engine = Engine::default();
    assert_eq!(
        request(&mut engine, command("old", 0, 0, false))["error"],
        "unsupported-command"
    );
    let before = import(&mut engine);
    let mut club = command("club", 0, 0, false);
    club["command"]["club_id"] = json!(8);
    let mut session = command("session", 0, 0, false);
    session["command"]["session_id"] = json!("wrong");
    let mut option = command("index", 0, 0, false);
    option["command"]["option"] = json!(3);
    for op in [
        command("neg", 0, -1, false),
        command("upper", 0, 2, false),
        command("wide", 0, 256, false),
        command("bad id", 0, 0, false),
        command("stale", 1, 0, false),
        club,
        session,
        option,
        json!({"action":"command","command":{"session_id":"synthetic-human-regression-registry-session-v1","command_id":"ordinary","expected_revision":0,"club_id":7,"plan_id":0}}),
    ] {
        let result = request(&mut engine, op);
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], before["state"]);
    }
}
#[test]
fn mixed_replay_preserves_exact_save_and_legacy_versions() {
    let mut engine = Engine::default();
    import(&mut engine);
    let first = command("first", 0, 1, false);
    request(&mut engine, first.clone());
    request(&mut engine, command("second", 1, 1, true));
    let saved = request(&mut engine, json!({"action":"save"}));
    let next = command("next", 2, 0, false);
    let expected = request(&mut engine, next.clone());
    request(&mut engine, json!({"action":"reset"}));
    let restored = request(&mut engine, json!({"action":"load","save":saved["result"]}));
    assert_eq!(restored["state"], saved["state"]);
    assert_eq!(
        request(&mut engine, json!({"action":"save"}))["result"],
        saved["result"]
    );
    assert_eq!(request(&mut engine, first)["state"], saved["state"]);
    assert_eq!(request(&mut engine, next), expected);
    for op in [
        json!({"action":"load","save":include_str!("fixtures/legacy-plan-v1.json")}),
        json!({"action":"import_reference","fixture":include_str!("fixtures/synthetic-managers-v1.json")}),
        json!({"action":"import_human_reference","fixture":include_str!("fixtures/synthetic-human-registry.json")}),
    ] {
        let old = request(&mut engine, op);
        let old_save = request(&mut engine, json!({"action":"save"}));
        request(&mut engine, json!({"action":"load","save":saved["result"]}));
        let loaded = request(
            &mut engine,
            json!({"action":"load","save":old_save["result"]}),
        );
        assert_eq!(loaded["state"], old["state"]);
        assert_eq!(
            request(&mut engine, json!({"action":"save"}))["result"],
            old_save["result"]
        );
        assert_eq!(
            request(&mut engine, command("unavailable", 0, 0, false))["error"],
            "unsupported-command"
        );
    }
}
#[test]
fn repaired_save_and_hybrid_fixture_cannot_bypass_admission_or_replay() {
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    for path in [
        "/guard_9a01",
        "/option_two",
        "/human/selected_slot",
        "/human/registry_index",
    ] {
        let mut fixture: Value = serde_json::from_str(FIXTURE).unwrap();
        *fixture.pointer_mut(path).unwrap() = json!(1);
        if path == "/guard_9a01" {
            *fixture.pointer_mut(path).unwrap() = json!(0);
        }
        let rejected = request(
            &mut engine,
            json!({"action":"import_registry_reference","fixture":fixture.to_string()}),
        );
        assert_eq!(rejected["ok"], false);
        assert_eq!(rejected["state"], initial["state"]);
    }
    request(&mut engine, command("first", 0, 1, false));
    request(&mut engine, command("second", 1, 1, true));
    let saved = request(&mut engine, json!({"action":"save"}));
    let original: Value = serde_json::from_str(saved["result"].as_str().unwrap()).unwrap();
    for path in [
        "/schema_version",
        "/profile",
        "/fixture_sha256",
        "/session_id",
        "/revision",
        "/selected_slot",
        "/option_two",
        "/fixture/guard_9a01",
        "/fixture/option_two",
        "/events/0/new_value",
        "/events/0/ordered_writes/0/registry_offset",
        "/records/0/result/ordered_writes/0/width",
        "/records/1/command/command/slot",
    ] {
        let mut envelope = original.clone();
        let mut payload: Value =
            serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
        *payload.pointer_mut(path).unwrap() = json!(999);
        let text = payload.to_string();
        envelope["payload_bytes"] = json!(text.len());
        envelope["payload_sha256"] = json!(format!("{:x}", Sha256::digest(text.as_bytes())));
        envelope["payload"] = json!(text);
        let rejected = request(
            &mut engine,
            json!({"action":"load","save":envelope.to_string()}),
        );
        assert_eq!(rejected["ok"], false, "{path}");
        assert_eq!(rejected["state"], saved["state"]);
    }
}
#[test]
fn combined_capacity_retains_both_command_retries() {
    let mut engine = Engine::default();
    import(&mut engine);
    for i in 0..256 {
        assert_eq!(
            request(
                &mut engine,
                command(&format!("c{i}"), i, (i % 2) as i32, i % 2 == 1)
            )["ok"],
            true
        );
    }
    let before = request(&mut engine, json!({"action":"state"}));
    let full = request(&mut engine, command("full", 256, 0, false));
    assert_eq!(full["error"], "command-capacity");
    assert_eq!(full["state"], before["state"]);
    for op in [command("c0", 0, 0, false), command("c1", 1, 1, true)] {
        assert_eq!(request(&mut engine, op)["state"], before["state"]);
    }
}

#[test]
fn valid_width_resealed_forgery_and_reordered_records_fail_replay() {
    let mut engine = Engine::default();
    import(&mut engine);
    request(&mut engine, command("one", 0, 1, false));
    request(&mut engine, command("two", 1, 1, true));
    let saved = request(&mut engine, json!({"action":"save"}));
    let envelope: Value = serde_json::from_str(saved["result"].as_str().unwrap()).unwrap();
    let payload: Value = serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
    let mut variants = vec![];
    for path in [
        "/option_two",
        "/selected_slot",
        "/events/0/new_value",
        "/records/0/result/new_value",
        "/events/0/ordered_writes/0/value",
        "/records/0/command/command/value",
    ] {
        let mut forged = payload.clone();
        *forged.pointer_mut(path).unwrap() = json!(0);
        variants.push(forged);
    }
    let mut reordered = payload.clone();
    reordered["records"].as_array_mut().unwrap().swap(0, 1);
    variants.push(reordered);
    let mut duplicated = payload.clone();
    duplicated["records"][1] = duplicated["records"][0].clone();
    variants.push(duplicated);
    let mut omitted = payload.clone();
    omitted["events"].as_array_mut().unwrap().remove(0);
    variants.push(omitted);
    for forged in variants {
        let mut repaired = envelope.clone();
        let text = forged.to_string();
        repaired["payload_bytes"] = json!(text.len());
        repaired["payload_sha256"] = json!(format!("{:x}", Sha256::digest(text.as_bytes())));
        repaired["payload"] = json!(text);
        let rejected = request(
            &mut engine,
            json!({"action":"load","save":repaired.to_string()}),
        );
        assert_eq!(rejected["ok"], false);
        assert_eq!(rejected["state"], saved["state"]);
    }
}
