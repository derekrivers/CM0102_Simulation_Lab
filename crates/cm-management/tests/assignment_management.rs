use cm_management::Engine;
use cm_management::assignment::AssignmentFixture;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn fixture() -> Value {
    serde_json::from_str(include_str!("fixtures/synthetic-assignment.json")).unwrap()
}
fn request(engine: &mut Engine, operation: Value) -> Value {
    engine.request(&serde_json::to_vec(&operation).unwrap())
}
fn import(engine: &mut Engine) -> Value {
    request(
        engine,
        json!({"action":"import_assignment_reference","fixture":fixture().to_string()}),
    )
}
fn command(read: bool, id: &str, revision: u32, staff_id: i64) -> Value {
    let mut c = json!({"session_id":"synthetic-assignment-regression-assignment-session-v1",
        "command_id":id,"expected_revision":revision,"club_id":7,"slot":0});
    if !read {
        c["staff_id"] = json!(staff_id);
    }
    json!({"action":if read {"assignment_readback_command"} else {"assignment_command"},"command":c})
}
fn save(engine: &mut Engine) -> Value {
    request(engine, json!({"action":"save"}))
}
fn resealed(envelope: &Value, payload: Value) -> Value {
    let mut envelope = envelope.clone();
    let encoded = serde_json::to_string(&payload).unwrap();
    envelope["payload_bytes"] = json!(encoded.len());
    envelope["payload_sha256"] = json!(format!("{:x}", Sha256::digest(encoded.as_bytes())));
    envelope["payload"] = json!(encoded);
    json!({"action":"load","save":envelope.to_string()})
}

#[test]
fn exact_fixture_identity_and_explicit_original_effects() {
    let f = AssignmentFixture::parse(&fixture().to_string()).unwrap();
    assert_eq!(
        f.fingerprint().unwrap(),
        "2c3e22cb65f6bd6f0f4cb48da7e0ed4a92a2ddc04d191682335c204f40490599"
    );
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    assert_eq!(initial["ok"], true);
    assert_eq!(initial["state"]["schema_version"], 6);
    assert_eq!(initial["state"]["mapping"], json!(vec![-1; 20]));
    assert_eq!(initial["assignment_readback_result"], Value::Null);
    let empty = request(&mut engine, command(true, "empty", 0, 0));
    assert_eq!(empty["result"]["readback"], json!({"kind":"Empty"}));
    assert_eq!(empty["result"]["ordered_writes"], json!([]));
    // Fresh commands correspond to original assignment, repeated assignment and replacement.
    for (i, staff_id) in [11, 11, 22, 11].into_iter().enumerate() {
        let revision = 1 + i as u32 * 2;
        let before = request(&mut engine, json!({"action":"state"}));
        let r = request(
            &mut engine,
            command(false, &format!("assign-{i}"), revision, staff_id),
        );
        assert_eq!(r["ok"], true);
        assert_eq!(r["result"]["kind"], "AssignmentMade");
        assert_eq!(r["result"]["original_return"], 1);
        assert_eq!(r["result"]["old_staff_id"], before["state"]["mapping"][0]);
        assert_eq!(r["result"]["new_staff_id"], staff_id);
        assert_eq!(
            r["result"]["ordered_writes"],
            json!([{
                "row_mode":0,"byte_offset":2,"width":4,"value":staff_id,
            }])
        );
        assert_eq!(r["result"]["rng_draws"], 0);
        assert_eq!(
            r["assignment_readback_result"],
            before["assignment_readback_result"]
        );
        assert_eq!(r["state"]["fixture"], initial["state"]["fixture"]);
        let mut mapping = vec![-1; 20];
        mapping[0] = staff_id;
        assert_eq!(r["state"]["mapping"], json!(mapping));
        let read = request(
            &mut engine,
            command(true, &format!("read-{i}"), revision + 1, 0),
        );
        assert_eq!(read["result"]["kind"], "AssignmentReadBack");
        assert_eq!(
            read["result"]["readback"],
            json!({"kind":"StaffId","staff_id":staff_id})
        );
        assert_eq!(read["result"]["ordered_writes"], json!([]));
        assert_eq!(read["result"]["rng_draws"], 0);
        assert_eq!(read["state"]["mapping"], r["state"]["mapping"]);
        assert_eq!(read["assignment_readback_result"], read["result"]);
        assert_eq!(
            request(&mut engine, json!({"action":"state"})),
            json!({
                "ok":true,"result":null,"state":read["state"],"plan_locations":[],
                "assignment_readback_result":read["result"],
            })
        );
    }
}

#[test]
fn transport_retry_and_new_assignment_are_distinct() {
    let mut engine = Engine::default();
    import(&mut engine);
    let op = command(false, "first", 0, 11);
    let first = request(&mut engine, op.clone());
    let second = request(&mut engine, command(false, "second", 1, 11));
    assert_eq!(second["state"]["revision"], 2);
    assert_eq!(
        second["result"]["ordered_writes"],
        first["result"]["ordered_writes"]
    );
    let retry = request(&mut engine, op.clone());
    assert_eq!(retry["result"], first["result"]);
    assert_eq!(retry["state"], second["state"]);
    for conflict in [
        command(true, "first", 0, 0),
        command(false, "first", 0, 22),
        command(false, "first", 2, 11),
    ] {
        let rejected = request(&mut engine, conflict);
        assert_eq!(rejected["error"], "command-id-conflict");
        assert_eq!(rejected["state"], second["state"]);
    }
    let saved = save(&mut engine);
    let mut restored = Engine::default();
    assert_eq!(
        request(
            &mut restored,
            json!({"action":"load","save":saved["result"]})
        )["ok"],
        true
    );
    assert_eq!(request(&mut restored, op)["result"], first["result"]);
    let read = command(true, "read", 2, 0);
    assert_eq!(
        request(&mut restored, read.clone()),
        request(&mut engine, read)
    );
}

#[test]
fn host_restrictions_reject_atomically_without_original_rejection_claim() {
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    let mut invalid = vec![];
    for read in [false, true] {
        for slot in [-1, 1, 19, 20, 256, i32::MAX] {
            let mut op = command(read, "slot", 0, 11);
            op["command"]["slot"] = json!(slot);
            invalid.push(op);
        }
        for (field, value) in [
            ("session_id", json!("wrong")),
            ("command_id", json!("")),
            ("command_id", json!("x".repeat(65))),
            ("command_id", json!("bad id")),
            ("expected_revision", json!(1)),
            ("club_id", json!(8)),
            ("unknown", json!(0)),
        ] {
            let mut op = command(read, "invalid", 0, 11);
            op["command"][field] = value;
            invalid.push(op);
        }
    }
    for id in [-1, 0, 12, 99, i32::MAX as i64, u32::MAX as i64, i64::MAX] {
        invalid.push(command(false, "member", 0, id));
    }
    // Integer widths are parsed before admission; no narrowing may alias slot zero/member 11.
    let mut oversized = command(false, "wide", 0, 11);
    oversized["command"]["slot"] = json!(4_294_967_296u64);
    invalid.push(oversized);
    invalid.push(json!({"action":"human_command","command":{
        "session_id":"synthetic-assignment-regression-assignment-session-v1",
        "command_id":"old","expected_revision":0,"club_id":7,"slot":0,
    }}));
    invalid.push(json!({"action":"command","command":{
        "session_id":"fictional-club-session-v1","command_id":"old",
        "expected_revision":0,"club_id":0,"plan_id":1,
    }}));
    for op in invalid {
        let result = request(&mut engine, op);
        assert_eq!(result["ok"], false);
        assert_eq!(result["state"], initial["state"]);
        assert_eq!(result["assignment_readback_result"], Value::Null);
    }
}

#[test]
fn fixture_mutation_hybrid_relabel_and_bad_shapes_never_admit() {
    let mut engine = Engine::default();
    let initial = import(&mut engine);
    for (field, value) in [
        ("schema_version", json!(2)),
        ("origin", json!("captured-bosman-two-member-assignment")),
        ("origin", json!("captured-bosman-human-registry")),
        ("specimen_sha256", json!("0".repeat(64))),
        ("source_capture_sha256", json!("0".repeat(64))),
        ("image_sha256", json!("0".repeat(64))),
        ("heap_sha256", json!("0".repeat(64))),
        ("backend_revision", json!("0".repeat(40))),
        ("club_id", json!(8)),
        ("manager_staff_id", json!(11)),
        ("members", json!([11, 11])),
        ("members", json!([22, 11])),
        ("members", json!([11, 2_147_483_648u32])),
        ("members", json!([11, 23])),
        ("members", json!([11])),
        ("row_mode", json!(1)),
        ("cache_count", json!(1)),
        ("mapping", json!(vec![-1; 19])),
        ("mapping", json!(vec![4_294_967_295u32; 20])),
        ("unknown", json!(1)),
    ] {
        let mut changed = fixture();
        changed[field] = value;
        let result = request(
            &mut engine,
            json!({"action":"import_assignment_reference","fixture":changed.to_string()}),
        );
        assert_eq!(result["ok"], false, "field {field}");
        assert_eq!(result["state"], initial["state"]);
    }
    let mut nonempty = fixture();
    nonempty["mapping"][0] = json!(11);
    assert_eq!(
        request(
            &mut engine,
            json!({"action":"import_assignment_reference","fixture":nonempty.to_string()})
        )["ok"],
        false
    );
    let huge = request(
        &mut engine,
        json!({"action":"import_assignment_reference","fixture":" ".repeat(65537)}),
    );
    assert_eq!(huge["error"], "fixture-too-large");
    assert_eq!(huge["state"], initial["state"]);
}

#[test]
fn save_replay_validates_all_state_history_and_continuation() {
    let mut engine = Engine::default();
    import(&mut engine);
    for op in [
        command(true, "empty", 0, 0),
        command(false, "a", 1, 11),
        command(true, "r", 2, 0),
        command(false, "b", 3, 22),
    ] {
        assert_eq!(request(&mut engine, op)["ok"], true);
    }
    let saved = save(&mut engine);
    let continuation = command(false, "next", 4, 11);
    let expected = request(&mut engine, continuation.clone());
    assert_eq!(
        request(&mut engine, json!({"action":"load","save":saved["result"]}))["state"],
        saved["state"]
    );
    assert_eq!(save(&mut engine)["result"], saved["result"]);
    assert_eq!(request(&mut engine, continuation), expected);
    let current = save(&mut engine);
    let envelope: Value = serde_json::from_str(current["result"].as_str().unwrap()).unwrap();
    let payload: Value = serde_json::from_str(envelope["payload"].as_str().unwrap()).unwrap();
    for index in 0..22 {
        let mut p = payload.clone();
        match index {
            0 => p["mapping"][0] = json!(22),
            1 => p["mapping"][1] = json!(11),
            2 => p["schema_version"] = json!(5),
            3 => p["profile"] = json!("synthetic-assignment-regression-slot-zero-v2"),
            4 => p["fixture_sha256"] = json!("0".repeat(64)),
            5 => p["session_id"] = json!("other"),
            6 => p["revision"] = json!(99),
            7 => p["fixture"]["cache_count"] = json!(1),
            8 => p["fixture"]["members"] = json!([11, 23]),
            9 => p["fixture"]["mapping"][0] = json!(11),
            10 => p["events"][0]["readback"] = json!({"kind":"StaffId","staff_id":11}),
            11 => p["events"][1]["ordered_writes"][0]["width"] = json!(2),
            12 => p["events"][1]["original_return"] = json!(0),
            13 => p["events"][1]["rng_draws"] = json!(1),
            14 => p["records"][1]["result"]["ordered_writes"][0]["value"] = json!(22),
            15 => p["records"][1]["command"]["command"]["staff_id"] = json!(22),
            16 => p["records"].as_array_mut().unwrap().reverse(),
            17 => {
                let r = p["records"][0].clone();
                p["records"].as_array_mut().unwrap().push(r);
            }
            18 => {
                p["events"].as_array_mut().unwrap().pop();
            }
            19 => p["records"][1]["command"]["command"]["slot"] = json!(256),
            20 => p["records"][1]["command"]["command"]["expected_revision"] = json!(2),
            21 => p["unknown"] = json!(0),
            _ => unreachable!(),
        }
        let result = request(&mut engine, resealed(&envelope, p));
        assert_eq!(result["ok"], false, "resealed tamper {index}");
        assert_eq!(result["state"], current["state"]);
    }
    let mut bad_envelope = envelope.clone();
    bad_envelope["schema_version"] = json!(5);
    let r = request(
        &mut engine,
        json!({"action":"load","save":bad_envelope.to_string()}),
    );
    assert_eq!(r["ok"], false);
    assert_eq!(r["state"], current["state"]);
}

#[test]
fn capacity_rejects_new_command_but_retry_still_succeeds() {
    let mut engine = Engine::default();
    import(&mut engine);
    let first_op = command(false, "cap-0", 0, 11);
    let first = request(&mut engine, first_op.clone());
    for i in 1..256 {
        assert_eq!(
            request(&mut engine, command(i % 2 == 0, &format!("cap-{i}"), i, 11))["ok"],
            true
        );
    }
    let before = save(&mut engine);
    let retry = request(&mut engine, first_op);
    assert_eq!(retry["result"], first["result"]);
    assert_eq!(retry["state"], before["state"]);
    let over = request(&mut engine, command(true, "over", 256, 0));
    assert_eq!(over["error"], "command-capacity");
    assert_eq!(over["state"], before["state"]);
    let mut restored = Engine::default();
    assert_eq!(
        request(
            &mut restored,
            json!({"action":"load","save":before["result"]})
        )["state"],
        before["state"]
    );
}

#[test]
fn versions_one_through_five_preserve_bytes_and_profile_isolation() {
    let mut engine = Engine::default();
    let mut old_saves = vec![include_str!("fixtures/legacy-plan-v1.json").to_string()];
    for (action, fixture) in [
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
        (
            "import_effective_reference",
            include_str!("fixtures/synthetic-effective-plan.json"),
        ),
    ] {
        import(&mut engine);
        let result = request(&mut engine, json!({"action":action,"fixture":fixture}));
        assert_eq!(result["ok"], true);
        assert!(result.get("assignment_readback_result").is_none());
        assert_eq!(
            request(&mut engine, command(false, "unsupported", 0, 11))["error"],
            "unsupported-command"
        );
        old_saves.push(save(&mut engine)["result"].as_str().unwrap().to_string());
    }
    for (i, old_save) in old_saves.iter().enumerate() {
        import(&mut engine);
        let old = request(&mut engine, json!({"action":"load","save":old_save}));
        assert_eq!(old["ok"], true);
        assert_eq!(old["state"]["schema_version"], i + 1);
        assert!(old.get("assignment_readback_result").is_none());
        for read in [false, true] {
            assert_eq!(
                request(&mut engine, command(read, "unsupported", 0, 11))["error"],
                "unsupported-command"
            );
        }
        assert_eq!(save(&mut engine)["result"], *old_save);
    }
    import(&mut engine);
    let reset = request(&mut engine, json!({"action":"reset"}));
    assert_eq!(reset["state"]["schema_version"], 1);
    assert!(reset.get("assignment_readback_result").is_none());
    assert_eq!(
        request(&mut engine, command(true, "unsupported", 0, 0))["error"],
        "unsupported-command"
    );
}
