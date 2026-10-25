use cm_management::reference::{ReferenceFixture, resolve_plan};
use cm_management::{Engine, World};

#[test]
fn rust_bank_resolution_matches_all_qualified_original_cases() {
    let oracle: serde_json::Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/manager-bound-plan-oracle-v1.json"
    ))
    .unwrap();
    let mut engine = Engine::default();
    import(&mut engine, FIXTURE);
    for (revision, case) in oracle["cases"].as_array().unwrap().iter().enumerate() {
        let label = case["club_label"].as_u64().unwrap() as usize;
        let plan = case["plan_index"].as_i64().unwrap() as i32;
        let result = request(
            &mut engine,
            command(
                &format!("original-{revision}"),
                revision as u32,
                [10, 20, 30][label],
                plan,
            ),
        );
        assert_eq!(result["ok"], true);
        assert_eq!(result["state"]["clubs"][label]["selected_plan"], plan);
        assert_eq!(
            result["plan_locations"][label]["location"],
            serde_json::json!({
                "bank":if case["lookup_bank"]==0 {"first"}else{"second"},
                "index":case["lookup_bank_index"],"byte_offset":case["lookup_byte_offset"]
            })
        );
    }
}

const FIXTURE: &str = include_str!("fixtures/synthetic-managers-v1.json");
fn request(engine: &mut Engine, value: serde_json::Value) -> serde_json::Value {
    engine.request(&serde_json::to_vec(&value).unwrap())
}
fn import(engine: &mut Engine, fixture: &str) -> serde_json::Value {
    request(
        engine,
        serde_json::json!({"action":"import_reference","fixture":fixture}),
    )
}
fn command(id: &str, revision: u32, club: u32, plan: i32) -> serde_json::Value {
    serde_json::json!({"action":"command","command":{"session_id":"synthetic-regression-club-session-v1","command_id":id,"expected_revision":revision,"club_id":club,"plan_id":plan}})
}

#[test]
fn manager_binding_sparse_club_selection_and_both_bank_boundaries() {
    let mut engine = Engine::default();
    let initial = import(&mut engine, FIXTURE);
    assert_eq!(initial["ok"], true);
    assert_eq!(initial["state"]["schema_version"], 2);
    for (revision, (plan, bank, index)) in [
        (0, "first", 0),
        (16, "first", 16),
        (17, "second", 0),
        (44, "second", 27),
    ]
    .into_iter()
    .enumerate()
    {
        let actual = request(
            &mut engine,
            command(&format!("boundary-{revision}"), revision as u32, 20, plan),
        );
        assert_eq!(actual["ok"], true);
        assert_eq!(
            actual["plan_locations"][1]["location"],
            serde_json::json!({"bank":bank,"index":index,"byte_offset":index*6371})
        );
        assert_eq!(
            actual["state"]["clubs"][0]["selected_plan"],
            initial["state"]["clubs"][0]["selected_plan"]
        );
        assert_eq!(actual["state"]["reference"], initial["state"]["reference"]);
    }
    let before = request(&mut engine, serde_json::json!({"action":"state"}));
    for bad in [
        command("negative", 4, 20, -1),
        command("upper", 4, 20, 45),
        command("missing", 4, 21, 0),
        command("stale", 0, 20, 0),
    ] {
        let result = request(&mut engine, bad);
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], before["state"]);
    }
}

#[test]
fn fixture_spoofing_and_unsupported_manager_paths_preserve_current_world() {
    let mut engine = Engine::default();
    import(&mut engine, FIXTURE);
    let before = request(&mut engine, serde_json::json!({"action":"state"}));
    for (field, value) in [
        ("manager_id", serde_json::json!(84)),
        ("id", serde_json::json!(35)),
        ("name", serde_json::json!("forged")),
        ("selected_plan", serde_json::json!(-1)),
    ] {
        let mut tampered: serde_json::Value = serde_json::from_str(FIXTURE).unwrap();
        tampered["clubs"][0][field] = value;
        let result = import(&mut engine, &tampered.to_string());
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], before["state"]);
    }
    let mut spoof: serde_json::Value = serde_json::from_str(FIXTURE).unwrap();
    spoof["origin"] = serde_json::json!("captured-bosman");
    assert_eq!(import(&mut engine, &spoof.to_string())["ok"], false);
    assert!(ReferenceFixture::parse("{}").is_err());
    assert!(resolve_plan(17, 28, -1).is_err());
    assert!(resolve_plan(17, 28, 45).is_err());
    assert!(resolve_plan(u32::MAX, 1, 0).is_err());
}

#[test]
fn old_v1_save_is_unchanged_and_v2_reloads_fixture_and_deduplication() {
    let legacy = include_str!("fixtures/legacy-plan-v1.json");
    assert_eq!(World::load(legacy).unwrap().save().unwrap(), legacy);
    let mut engine = Engine::default();
    import(&mut engine, FIXTURE);
    let first = command("first", 0, 30, 17);
    request(&mut engine, first.clone());
    let saved = request(&mut engine, serde_json::json!({"action":"save"}));
    let envelope: serde_json::Value =
        serde_json::from_str(saved["result"].as_str().unwrap()).unwrap();
    assert_eq!(envelope["schema_version"], 2);
    let next = command("next", 1, 10, 44);
    let expected = request(&mut engine, next.clone());
    let restored = request(
        &mut engine,
        serde_json::json!({"action":"load","save":saved["result"]}),
    );
    let duplicate = request(&mut engine, first);
    assert_eq!(duplicate["state"], restored["state"]);
    assert_eq!(request(&mut engine, next), expected);
    let mut forged = envelope;
    forged["schema_version"] = serde_json::json!(1);
    let before = request(&mut engine, serde_json::json!({"action":"state"}));
    let bad = request(
        &mut engine,
        serde_json::json!({"action":"load","save":forged.to_string()}),
    );
    assert_eq!(bad["ok"], false);
    assert_eq!(bad["state"], before["state"]);
}
