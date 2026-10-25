use cm_management::{Command, Engine, World};
fn command(id: &str, rev: u32, club: u32, plan: i32) -> Command {
    Command {
        session_id: "fictional-club-session-v1".into(),
        command_id: id.into(),
        expected_revision: rev,
        club_id: club,
        plan_id: plan,
    }
}
#[test]
fn original_corpus_row_and_selection_equality() {
    let oracle: serde_json::Value = serde_json::from_str(include_str!(
        "../../../docs/research/evidence/plan-selection-oracle-v1.json"
    ))
    .unwrap();
    let mut world = World::default();
    for (i, case) in oracle["cases"].as_array().unwrap().iter().enumerate() {
        let club = case["club_id"].as_u64().unwrap() as u32;
        let plan = case["selected_plan"].as_i64().unwrap() as i32;
        let before = world.clone();
        let event = world
            .apply(command(&format!("oracle-{i}"), i as u32, club, plan))
            .unwrap();
        assert_eq!(event.new_plan as i32, plan);
        for row in 0..4 {
            assert_eq!(
                world.clubs[row].selected_plan,
                if row == club as usize {
                    plan as u16
                } else {
                    before.clubs[row].selected_plan
                }
            );
        }
        assert_eq!(world.players, before.players);
        assert_eq!(world.plans, before.plans);
        assert_eq!(
            case["ordered_writes"],
            serde_json::json!([{"offset":club*0x91,"width":2,"value":plan}])
        );
    }
}
#[test]
fn invalid_actions_are_atomic_and_retries_survive_reload() {
    let mut world = World::default();
    let first = command("first", 0, 0, 4);
    let event = world.apply(first.clone()).unwrap();
    for bad in [
        command("negative", 1, 0, -1),
        command("wide", 1, 0, 65536),
        command("missing", 1, 99, 0),
        command("stale", 0, 0, 0),
        command("first", 0, 0, 3),
    ] {
        let before = world.clone();
        assert!(world.apply(bad).is_err());
        assert_eq!(world, before);
    }
    let save = world.save().unwrap();
    let mut restored = World::load(&save).unwrap();
    assert_eq!(restored.apply(first).unwrap(), event);
    assert_eq!(restored, world);
    let next = command("next", 1, 2, 3);
    assert_eq!(
        world.apply(next.clone()).unwrap(),
        restored.apply(next).unwrap()
    );
    assert_eq!(restored, world);
}
#[test]
fn resealed_tampered_state_and_corrupt_envelopes_are_rejected() {
    use sha2::{Digest, Sha256};
    let world = World::default();
    let save = world.save().unwrap();
    let mut envelope: serde_json::Value = serde_json::from_str(&save).unwrap();
    let mut payload: serde_json::Value =
        serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
    payload["players"][0]["club_id"] = serde_json::json!(999);
    let data = serde_json::to_string(&payload).unwrap();
    envelope["payload"] = serde_json::json!(data);
    envelope["payload_bytes"] = serde_json::json!(data.len());
    envelope["payload_sha256"] =
        serde_json::json!(format!("{:x}", Sha256::digest(data.as_bytes())));
    assert!(World::load(&envelope.to_string()).is_err());
    assert!(World::load(&save.replace("CM-PLAN-SLICE", "WRONG")).is_err());
    let mut engine = Engine::default();
    let before = engine.request(br#"{"action":"state"}"#);
    assert_eq!(
        engine.request(br#"{"action":"load","save":"corrupt"}"#)["state"],
        before["state"]
    );
    assert!(
        !engine.request(br#"{"action":"state","unknown":true}"#)["ok"]
            .as_bool()
            .unwrap()
    );
}
