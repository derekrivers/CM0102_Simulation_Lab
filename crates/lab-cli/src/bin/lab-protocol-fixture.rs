use serde_json::{Value, json};
use std::env;
use std::fs;
use std::io::{self, Read, Write};
use std::process::Command;
use std::thread;
use std::time::Duration;

fn main() {
    if let Err(error) = run() {
        eprintln!("lab-protocol-fixture: {error}");
        std::process::exit(2);
    }
}

fn run() -> Result<(), String> {
    let mode = env::args()
        .nth(1)
        .or_else(|| env::var("LAB_SCENARIO_ID").ok())
        .unwrap_or_else(|| "valid".to_owned());
    let attempt_id = env::var("LAB_ATTEMPT_ID").unwrap_or_else(|_| "fixture-attempt".to_owned());
    let stop_condition =
        env::var("LAB_EXPECTED_STOP_CONDITION").unwrap_or_else(|_| "fixture-complete".to_owned());
    if env::var("LAB_REQUEST_TRANSPORT").as_deref() == Ok("stdin-json-v1") {
        let mut input = String::new();
        io::stdin()
            .read_to_string(&mut input)
            .map_err(|error| format!("read request from stdin: {error}"))?;
        let request: Value = serde_json::from_str(&input)
            .map_err(|error| format!("parse request from stdin: {error}"))?;
        if request["attempt_id"] != attempt_id {
            return Err("stdin request attempt_id does not match adapter environment".to_owned());
        }
    }

    match mode.as_str() {
        "valid" | "valid-replay" => valid(&attempt_id, &stop_condition),
        "check-env" => {
            if env::var_os("LAB_TEST_SECRET").is_some() {
                terminal(&attempt_id, 1, "failed", "invalid-input", &stop_condition)
            } else {
                valid(&attempt_id, &stop_condition)
            }
        }
        "out-of-order" => {
            handshake(&attempt_id)?;
            terminal(
                &attempt_id,
                2,
                "succeeded",
                "completed-target",
                &stop_condition,
            )
        }
        "missing-terminal" => handshake(&attempt_id),
        "wrong-terminal-stop" => {
            handshake(&attempt_id)?;
            terminal(
                &attempt_id,
                1,
                "succeeded",
                "completed-target",
                "wrong-stop",
            )
        }
        "wrong-handshake" => {
            frame(
                &attempt_id,
                0,
                "handshake",
                json!({
                    "backend_kind": env::var("LAB_BACKEND_KIND").unwrap_or_default(),
                    "source_revision": "0".repeat(40),
                    "executable_sha256": env::var("LAB_EXECUTABLE_SHA256").unwrap_or_default(),
                    "capabilities": []
                }),
            )?;
            terminal(
                &attempt_id,
                1,
                "succeeded",
                "completed-target",
                &stop_condition,
            )
        }
        "failed-terminal" => {
            handshake(&attempt_id)?;
            terminal(&attempt_id, 1, "failed", "crash", &stop_condition)
        }
        "output-cap" => io::stdout()
            .write_all(&vec![b'x'; 1024 * 1024 + 1])
            .map_err(|error| format!("write oversized stdout: {error}")),
        "oversize-line" => frame(
            &attempt_id,
            0,
            "handshake",
            json!({"padding": "x".repeat(65 * 1024)}),
        ),
        "timeout-group" => {
            let child = Command::new("/bin/sleep")
                .arg("30")
                .spawn()
                .map_err(|error| format!("spawn timeout child: {error}"))?;
            fs::write("child.pid", format!("{}\n", child.id()))
                .map_err(|error| format!("write child PID: {error}"))?;
            loop {
                thread::sleep(Duration::from_secs(30));
            }
        }
        "timeout-escaped" => {
            let child = Command::new("/usr/bin/setsid")
                .args(["/bin/sleep", "30"])
                .spawn()
                .map_err(|error| format!("spawn timeout escaped descendant: {error}"))?;
            fs::write("child.pid", format!("{}\n", child.id()))
                .map_err(|error| format!("write escaped descendant PID: {error}"))?;
            loop {
                thread::sleep(Duration::from_secs(30));
            }
        }
        "escaped-descendant" => {
            let child = Command::new("/usr/bin/setsid")
                .args(["/bin/sleep", "30"])
                .spawn()
                .map_err(|error| format!("spawn escaped descendant: {error}"))?;
            fs::write("child.pid", format!("{}\n", child.id()))
                .map_err(|error| format!("write escaped descendant PID: {error}"))?;
            valid(&attempt_id, &stop_condition)
        }
        "spawn-marker" => {
            fs::write("spawned.marker", b"spawned\n")
                .map_err(|error| format!("write spawn marker: {error}"))?;
            valid(&attempt_id, &stop_condition)
        }
        "malformed" => io::stdout()
            .write_all(b"not-json\n")
            .map_err(|error| format!("write malformed frame: {error}")),
        _ => Err(format!("unknown fixture mode {mode:?}")),
    }
}

fn valid(attempt_id: &str, stop_condition: &str) -> Result<(), String> {
    eprintln!("synthetic fixture diagnostic");
    handshake(attempt_id)?;
    frame(
        attempt_id,
        1,
        "progress",
        json!({"checkpoint": "synthetic"}),
    )?;
    terminal(
        attempt_id,
        2,
        "succeeded",
        "completed-target",
        stop_condition,
    )
}

fn handshake(attempt_id: &str) -> Result<(), String> {
    frame(
        attempt_id,
        0,
        "handshake",
        json!({
            "backend_kind": env::var("LAB_BACKEND_KIND").unwrap_or_default(),
            "source_revision": env::var("LAB_SOURCE_REVISION").unwrap_or_default(),
            "executable_sha256": env::var("LAB_EXECUTABLE_SHA256").unwrap_or_default(),
            "capabilities": []
        }),
    )
}

fn terminal(
    attempt_id: &str,
    sequence: u64,
    execution_status: &str,
    reason: &str,
    stop_condition: &str,
) -> Result<(), String> {
    frame(
        attempt_id,
        sequence,
        "terminal",
        json!({
            "execution_status": execution_status,
            "reason": reason,
            "stop_condition": stop_condition
        }),
    )
}

fn frame(attempt_id: &str, sequence: u64, kind: &str, payload: Value) -> Result<(), String> {
    let value = json!({
        "protocol_version": 1,
        "attempt_id": attempt_id,
        "sequence": sequence,
        "kind": kind,
        "payload": payload
    });
    let mut stdout = io::stdout().lock();
    serde_json::to_writer(&mut stdout, &value)
        .map_err(|error| format!("serialize frame: {error}"))?;
    stdout
        .write_all(b"\n")
        .and_then(|()| stdout.flush())
        .map_err(|error| format!("write frame: {error}"))
}
