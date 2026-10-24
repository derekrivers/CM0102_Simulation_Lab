use lab_cli::{comparator, process_contract};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::env;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

const EXPECTED_COMMIT: &str = "2bb558ef6a6bcdbd304dd1a6a4cf156c6707007c";
const EXPECTED_REPOSITORY: &str = "https://github.com/maxevans60/cm0102-function-map";
const EXPECTED_EXECUTABLE_SHA256: &str =
    "0c78e7da6d0bcb4603fa179449bbe6d1b6b5e1c627a22c445d14d489bd9bff86";
const IMPORT_VERSION: &str = "b0-map-import-v1";

#[derive(Clone, Copy, Debug)]
struct TableSpec {
    name: &'static str,
    path: &'static str,
    required: &'static [&'static str],
}

const TABLES: &[TableSpec] = &[
    TableSpec {
        name: "broad",
        path: "map/function-files.tsv",
        required: &["address", "category", "file", "method", "instructions"],
    },
    TableSpec {
        name: "function",
        path: "map/functions.tsv",
        required: &[
            "address",
            "size",
            "doc",
            "name",
            "convention",
            "purpose",
            "confidence",
            "model",
        ],
    },
    TableSpec {
        name: "name",
        path: "map/names.tsv",
        required: &["address", "file", "name", "confidence", "model", "cited_in"],
    },
    TableSpec {
        name: "not-high",
        path: "map/not-high.tsv",
        required: &["address", "file", "name", "confidence", "reason"],
    },
    TableSpec {
        name: "global",
        path: "data-map/globals.tsv",
        required: &[
            "address",
            "size",
            "type",
            "name",
            "readers",
            "writers",
            "confidence",
            "model",
            "cited_in",
        ],
    },
    TableSpec {
        name: "data",
        path: "data-map/data.tsv",
        required: &[
            "address",
            "size",
            "doc",
            "type",
            "name",
            "description",
            "confidence",
            "model",
            "readers",
            "writers",
        ],
    },
];

#[derive(Debug)]
struct ImportError(String);

impl std::fmt::Display for ImportError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for ImportError {}

type ImportResult<T> = Result<T, ImportError>;

#[derive(Debug)]
struct TableData {
    spec: TableSpec,
    sha256: String,
    headers: Vec<String>,
    records: Vec<Value>,
    addresses: Vec<u32>,
    duplicate_addresses: Vec<DuplicateAddress>,
    invalid_addresses: Vec<InvalidAddress>,
}

#[derive(Debug)]
struct DuplicateAddress {
    address: u32,
    raw_addresses: Vec<String>,
    rows: Vec<usize>,
    conflicting: bool,
}

#[derive(Debug)]
struct InvalidAddress {
    row: usize,
    raw: String,
}

#[derive(Debug)]
struct PeImage {
    sha256: String,
    file_size: usize,
    image_base: u32,
    image_size: u32,
    entry_point: u32,
    sections: Vec<PeSection>,
}

#[derive(Debug)]
struct PeSection {
    name: String,
    address: u32,
    virtual_size: u32,
    raw_size: u32,
    characteristics: u32,
}

impl PeSection {
    fn contains(&self, address: u32) -> bool {
        let size = self.virtual_size.max(self.raw_size);
        address >= self.address && address < self.address.saturating_add(size)
    }

    fn is_code(&self) -> bool {
        self.characteristics & 0x2000_0000 != 0
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("lab-cli: {error}");
        std::process::exit(2);
    }
}

fn run() -> ImportResult<()> {
    let mut args = env::args().skip(1);
    let command = args.next().ok_or_else(|| ImportError(usage().to_owned()))?;
    if command == "--help" || command == "-h" {
        println!("{}", usage());
        return Ok(());
    }
    match command.as_str() {
        "import-map" => run_import_map(args),
        "validate-run" => run_validate_request(args),
        "execute-process" => run_execute_process(args),
        "compare-observations" => run_compare_observations(args),
        _ => Err(ImportError(format!(
            "unknown command `{command}`\n\n{}",
            usage()
        ))),
    }
}

fn run_compare_observations(mut args: impl Iterator<Item = String>) -> ImportResult<()> {
    let mut request = None;
    let mut left_bundle = None;
    let mut right_bundle = None;
    let mut output_dir = None;
    while let Some(arg) = args.next() {
        let target = match arg.as_str() {
            "--request" if request.is_none() => &mut request,
            "--left-bundle" if left_bundle.is_none() => &mut left_bundle,
            "--right-bundle" if right_bundle.is_none() => &mut right_bundle,
            "--output-dir" if output_dir.is_none() => &mut output_dir,
            "--help" | "-h" => {
                println!("{}", usage());
                return Ok(());
            }
            "--request" | "--left-bundle" | "--right-bundle" | "--output-dir" => {
                return Err(ImportError(format!("duplicate {arg} argument")));
            }
            _ => {
                return Err(ImportError(format!(
                    "unknown argument `{arg}`\n\n{}",
                    usage()
                )));
            }
        };
        *target = Some(required_path_value(&mut args, &arg)?);
    }
    comparator::compare_observations(
        &request.ok_or_else(|| ImportError("--request is required".to_owned()))?,
        &left_bundle.ok_or_else(|| ImportError("--left-bundle is required".to_owned()))?,
        &right_bundle.ok_or_else(|| ImportError("--right-bundle is required".to_owned()))?,
        &output_dir.ok_or_else(|| ImportError("--output-dir is required".to_owned()))?,
    )
    .map_err(ImportError)?;
    println!("comparison completed");
    Ok(())
}

fn run_import_map(mut args: impl Iterator<Item = String>) -> ImportResult<()> {
    let mut source = None;
    let mut lock = None;
    let mut output = None;
    let mut executable = None;
    while let Some(arg) = args.next() {
        let target = match arg.as_str() {
            "--source-dir" | "--source" => &mut source,
            "--lock-manifest" | "--lock" => &mut lock,
            "--output" | "-o" => &mut output,
            "--executable" => &mut executable,
            "--help" | "-h" => {
                println!("{}", usage());
                return Ok(());
            }
            _ => {
                return Err(ImportError(format!(
                    "unknown argument `{arg}`\n\n{}",
                    usage()
                )));
            }
        };
        let value = args
            .next()
            .ok_or_else(|| ImportError(format!("missing value for `{arg}`")))?;
        *target = Some(PathBuf::from(value));
    }
    let source = source.ok_or_else(|| ImportError("--source-dir is required".to_owned()))?;
    let lock = lock.ok_or_else(|| ImportError("--lock-manifest is required".to_owned()))?;
    let output = output.ok_or_else(|| ImportError("--output is required".to_owned()))?;
    import_map(&source, &lock, &output, executable.as_deref())
}

fn run_validate_request(mut args: impl Iterator<Item = String>) -> ImportResult<()> {
    let mut request = None;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--request" if request.is_none() => {
                request = Some(required_path_value(&mut args, &arg)?);
            }
            "--help" | "-h" => {
                println!("{}", usage());
                return Ok(());
            }
            "--request" => return Err(ImportError("duplicate --request argument".to_owned())),
            _ => {
                return Err(ImportError(format!(
                    "unknown argument `{arg}`\n\n{}",
                    usage()
                )));
            }
        }
    }
    let request = request.ok_or_else(|| ImportError("--request is required".to_owned()))?;
    let report = process_contract::validate_request_file(&request).map_err(ImportError)?;
    println!("{report}");
    Ok(())
}

fn run_execute_process(mut args: impl Iterator<Item = String>) -> ImportResult<()> {
    let mut request = None;
    let mut backend_executable = None;
    let mut backend_config = None;
    let mut attempt_dir = None;
    while let Some(arg) = args.next() {
        let target = match arg.as_str() {
            "--request" if request.is_none() => &mut request,
            "--backend-executable" if backend_executable.is_none() => &mut backend_executable,
            "--backend-config" if backend_config.is_none() => &mut backend_config,
            "--attempt-dir" if attempt_dir.is_none() => &mut attempt_dir,
            "--help" | "-h" => {
                println!("{}", usage());
                return Ok(());
            }
            "--request" | "--backend-executable" | "--backend-config" | "--attempt-dir" => {
                return Err(ImportError(format!("duplicate {arg} argument")));
            }
            _ => {
                return Err(ImportError(format!(
                    "unknown argument `{arg}`\n\n{}",
                    usage()
                )));
            }
        };
        *target = Some(required_path_value(&mut args, &arg)?);
    }
    let request = request.ok_or_else(|| ImportError("--request is required".to_owned()))?;
    let backend_executable = backend_executable
        .ok_or_else(|| ImportError("--backend-executable is required".to_owned()))?;
    let attempt_dir =
        attempt_dir.ok_or_else(|| ImportError("--attempt-dir is required".to_owned()))?;
    process_contract::execute_process(
        &request,
        &backend_executable,
        backend_config.as_deref(),
        &attempt_dir,
    )
    .map_err(ImportError)?;
    println!("execution succeeded");
    Ok(())
}

fn required_path_value(
    args: &mut impl Iterator<Item = String>,
    argument: &str,
) -> ImportResult<PathBuf> {
    args.next()
        .map(PathBuf::from)
        .ok_or_else(|| ImportError(format!("missing value for `{argument}`")))
}

fn usage() -> &'static str {
    "Usage:\n  lab-cli import-map --source-dir DIR --lock-manifest FILE --output FILE [--executable FILE]\n  lab-cli validate-run --request FILE\n  lab-cli execute-process --request FILE --backend-executable FILE [--backend-config FILE] --attempt-dir DIR\n  lab-cli compare-observations --request FILE --left-bundle FILE --right-bundle FILE --output-dir NEW_DIR\n\nImports pinned function-map evidence, validates or executes a bounded local protocol request, or compares verified observation bundles. Bosman-native execution requires a private --backend-config; synthetic execution rejects one."
}

fn import_map(
    source: &Path,
    lock_path: &Path,
    output: &Path,
    executable: Option<&Path>,
) -> ImportResult<()> {
    let lock_bytes = fs::read(lock_path)
        .map_err(|e| ImportError(format!("read lock manifest {}: {e}", lock_path.display())))?;
    let lock_json: Value = serde_json::from_slice(&lock_bytes)
        .map_err(|e| ImportError(format!("parse lock manifest {}: {e}", lock_path.display())))?;
    let function_map_lock = verify_lock_identity(&lock_json)?;
    verify_checkout_commit(source)?;

    let mut tables = Vec::with_capacity(TABLES.len());
    for spec in TABLES {
        let path = source.join(spec.path);
        let bytes =
            fs::read(&path).map_err(|e| ImportError(format!("read {}: {e}", path.display())))?;
        let sha256 = digest(&bytes);
        let files = function_map_lock
            .get("files")
            .and_then(Value::as_object)
            .ok_or_else(|| ImportError("sources.function_map.files must be an object".into()))?;
        let lock_file = files
            .get(spec.path)
            .ok_or_else(|| ImportError(format!("lock manifest has no entry for {}", spec.path)))?;
        verify_file_lock(spec, lock_file, &sha256, &bytes)?;
        tables.push(parse_table(*spec, &bytes, sha256)?);
    }

    let invalid: Vec<_> = tables
        .iter()
        .flat_map(|table| {
            table
                .invalid_addresses
                .iter()
                .map(move |item| (table.spec.path, item))
        })
        .collect();
    if !invalid.is_empty() {
        let mut message = String::from("invalid hexadecimal address(es):");
        for (path, item) in invalid {
            let _ = write!(message, " {path}:row {}={:?};", item.row, item.raw);
        }
        return Err(ImportError(message));
    }

    let pe = executable.map(read_pe).transpose()?;
    let address_validation = match &pe {
        Some(image) => validate_addresses(&tables, image)?,
        None => Value::String("pending_executable".into()),
    };
    let reconciliation = reconciliation(&tables);
    let mut root = Map::new();
    root.insert(
        "import_version".into(),
        Value::String(IMPORT_VERSION.into()),
    );
    root.insert("address_validation".into(), address_validation);
    root.insert(
        "source_identity".into(),
        source_identity(&tables, pe.is_some()),
    );
    root.insert("table_metadata".into(), table_metadata(&tables));
    root.insert("records".into(), records(&tables));
    root.insert("reconciliation".into(), reconciliation);

    let serialized = serde_json::to_string_pretty(&Value::Object(root))
        .map_err(|e| ImportError(format!("serialize import artifact: {e}")))?;
    let mut bytes = serialized.into_bytes();
    bytes.push(b'\n');
    if let Some(parent) = output.parent()
        && !parent.as_os_str().is_empty()
    {
        fs::create_dir_all(parent).map_err(|e| {
            ImportError(format!("create output directory {}: {e}", parent.display()))
        })?;
    }
    fs::write(output, bytes)
        .map_err(|e| ImportError(format!("write output {}: {e}", output.display())))?;
    Ok(())
}

fn read_pe(path: &Path) -> ImportResult<PeImage> {
    let bytes = fs::read(path)
        .map_err(|error| ImportError(format!("read executable {}: {error}", path.display())))?;
    let sha256 = digest(&bytes);
    if sha256 != EXPECTED_EXECUTABLE_SHA256 {
        return Err(ImportError(format!(
            "executable SHA-256 mismatch: expected {EXPECTED_EXECUTABLE_SHA256}, actual {sha256}"
        )));
    }
    parse_pe(&bytes, sha256)
}

fn parse_pe(bytes: &[u8], sha256: String) -> ImportResult<PeImage> {
    if bytes.get(..2) != Some(b"MZ") {
        return Err(ImportError("executable has no DOS MZ signature".into()));
    }
    let pe_offset = read_u32(bytes, 0x3c)? as usize;
    if bytes.get(pe_offset..pe_offset.saturating_add(4)) != Some(b"PE\0\0") {
        return Err(ImportError("executable has no PE signature".into()));
    }
    let machine = read_u16(bytes, pe_offset + 4)?;
    if machine != 0x014c {
        return Err(ImportError(format!(
            "executable PE machine is {machine:#06x}, expected i386 0x014c"
        )));
    }
    let section_count = read_u16(bytes, pe_offset + 6)? as usize;
    let optional_size = read_u16(bytes, pe_offset + 20)? as usize;
    let optional = pe_offset + 24;
    if read_u16(bytes, optional)? != 0x010b {
        return Err(ImportError("executable optional header is not PE32".into()));
    }
    let entry_rva = read_u32(bytes, optional + 16)?;
    let image_base = read_u32(bytes, optional + 28)?;
    let image_size = read_u32(bytes, optional + 56)?;
    let mut sections = Vec::with_capacity(section_count);
    let section_table = optional
        .checked_add(optional_size)
        .ok_or_else(|| ImportError("PE section table offset overflow".into()))?;
    for index in 0..section_count {
        let offset = section_table
            .checked_add(index.saturating_mul(40))
            .ok_or_else(|| ImportError("PE section offset overflow".into()))?;
        let name_bytes = bytes
            .get(offset..offset.saturating_add(8))
            .ok_or_else(|| ImportError("truncated PE section header".into()))?;
        let name_end = name_bytes.iter().position(|byte| *byte == 0).unwrap_or(8);
        let name = std::str::from_utf8(&name_bytes[..name_end])
            .map_err(|_| ImportError("PE section name is not ASCII/UTF-8".into()))?
            .to_owned();
        let virtual_size = read_u32(bytes, offset + 8)?;
        let virtual_address = read_u32(bytes, offset + 12)?;
        let raw_size = read_u32(bytes, offset + 16)?;
        let characteristics = read_u32(bytes, offset + 36)?;
        let address = image_base
            .checked_add(virtual_address)
            .ok_or_else(|| ImportError("PE section VA overflow".into()))?;
        sections.push(PeSection {
            name,
            address,
            virtual_size,
            raw_size,
            characteristics,
        });
    }
    let entry_point = image_base
        .checked_add(entry_rva)
        .ok_or_else(|| ImportError("PE entry-point VA overflow".into()))?;
    Ok(PeImage {
        sha256,
        file_size: bytes.len(),
        image_base,
        image_size,
        entry_point,
        sections,
    })
}

fn read_u16(bytes: &[u8], offset: usize) -> ImportResult<u16> {
    let value = bytes
        .get(offset..offset.saturating_add(2))
        .ok_or_else(|| ImportError("truncated PE header".into()))?;
    Ok(u16::from_le_bytes([value[0], value[1]]))
}

fn read_u32(bytes: &[u8], offset: usize) -> ImportResult<u32> {
    let value = bytes
        .get(offset..offset.saturating_add(4))
        .ok_or_else(|| ImportError("truncated PE header".into()))?;
    Ok(u32::from_le_bytes([value[0], value[1], value[2], value[3]]))
}

fn validate_addresses(tables: &[TableData], image: &PeImage) -> ImportResult<Value> {
    let mut table_results = Map::new();
    for table in tables {
        let requires_code = matches!(table.spec.name, "broad" | "function" | "name" | "not-high");
        let valid = table
            .addresses
            .iter()
            .filter(|address| {
                image.sections.iter().any(|section| {
                    section.contains(**address) && (!requires_code || section.is_code())
                })
            })
            .count();
        if valid != table.addresses.len() {
            return Err(ImportError(format!(
                "{} has {} address(es) outside the expected PE section class",
                table.spec.path,
                table.addresses.len() - valid
            )));
        }
        let mut result = Map::new();
        result.insert(
            "rows".into(),
            Value::Number((table.addresses.len() as u64).into()),
        );
        result.insert("validated".into(), Value::Number((valid as u64).into()));
        result.insert(
            "required_section_class".into(),
            Value::String(if requires_code { "code" } else { "mapped" }.into()),
        );
        table_results.insert(table.spec.name.into(), Value::Object(result));
    }

    let mut executable = Map::new();
    executable.insert("sha256".into(), Value::String(image.sha256.clone()));
    executable.insert(
        "file_size".into(),
        Value::Number((image.file_size as u64).into()),
    );
    executable.insert("format".into(), Value::String("PE32-i386".into()));
    executable.insert("image_base".into(), Value::Number(image.image_base.into()));
    executable.insert("image_size".into(), Value::Number(image.image_size.into()));
    executable.insert(
        "entry_point_va".into(),
        Value::Number(image.entry_point.into()),
    );
    executable.insert(
        "sections".into(),
        Value::Array(
            image
                .sections
                .iter()
                .map(|section| {
                    let mut value = Map::new();
                    value.insert("name".into(), Value::String(section.name.clone()));
                    value.insert("address".into(), Value::Number(section.address.into()));
                    value.insert(
                        "virtual_size".into(),
                        Value::Number(section.virtual_size.into()),
                    );
                    value.insert("raw_size".into(), Value::Number(section.raw_size.into()));
                    value.insert("code".into(), Value::Bool(section.is_code()));
                    Value::Object(value)
                })
                .collect(),
        ),
    );

    let mut validation = Map::new();
    validation.insert("status".into(), Value::String("validated".into()));
    validation.insert("executable".into(), Value::Object(executable));
    validation.insert("tables".into(), Value::Object(table_results));
    Ok(Value::Object(validation))
}

fn parse_table(spec: TableSpec, bytes: &[u8], sha256: String) -> ImportResult<TableData> {
    let text = std::str::from_utf8(bytes)
        .map_err(|e| ImportError(format!("{} is not UTF-8: {e}", spec.path)))?;
    let mut lines = text.lines();
    let header_line = lines
        .next()
        .ok_or_else(|| ImportError(format!("{} is empty; missing header", spec.path)))?;
    let headers: Vec<String> = header_line.split('\t').map(str::to_owned).collect();
    let header_set: BTreeSet<&str> = headers.iter().map(String::as_str).collect();
    let missing: Vec<_> = spec
        .required
        .iter()
        .copied()
        .filter(|required| !header_set.contains(required))
        .collect();
    if !missing.is_empty() {
        return Err(ImportError(format!(
            "{} missing required header column(s): {}",
            spec.path,
            missing.join(", ")
        )));
    }
    if headers.iter().any(|header| header.is_empty()) {
        return Err(ImportError(format!(
            "{} has an empty header column",
            spec.path
        )));
    }
    if headers.len() != header_set.len() {
        return Err(ImportError(format!(
            "{} has duplicate header columns",
            spec.path
        )));
    }

    let mut records = Vec::new();
    let mut addresses = Vec::new();
    let mut invalid_addresses = Vec::new();
    let address_index = headers
        .iter()
        .position(|header| header == "address")
        .unwrap();
    for (zero_based, line) in lines.enumerate() {
        let row = zero_based + 2;
        if line.is_empty() {
            continue;
        }
        let values: Vec<&str> = line.split('\t').collect();
        if values.len() != headers.len() {
            return Err(ImportError(format!(
                "{} row {} has {} fields; expected {}",
                spec.path,
                row,
                values.len(),
                headers.len()
            )));
        }
        let raw_address = values[address_index].to_owned();
        let canonical_address = parse_hex_address(&raw_address);
        if let Some(address) = canonical_address {
            addresses.push(address);
        } else {
            invalid_addresses.push(InvalidAddress {
                row,
                raw: raw_address.clone(),
            });
        }
        let mut fields = Map::new();
        for (header, value) in headers.iter().zip(values) {
            fields.insert(header.clone(), Value::String(value.to_owned()));
        }
        let mut record = Map::new();
        record.insert("source_path".into(), Value::String(spec.path.into()));
        record.insert("row_number".into(), Value::Number(row.into()));
        record.insert("raw_address".into(), Value::String(raw_address));
        if let Some(address) = canonical_address {
            record.insert("canonical_address".into(), Value::Number(address.into()));
        }
        record.insert("fields".into(), Value::Object(fields));
        record.insert("imported_hypothesis".into(), Value::Bool(true));
        record.insert("status".into(), Value::String("imported-hypothesis".into()));
        records.push(Value::Object(record));
    }

    let mut by_address: BTreeMap<u32, Vec<(usize, String, String)>> = BTreeMap::new();
    for (index, record) in records.iter().enumerate() {
        let Some(address) = record["canonical_address"]
            .as_u64()
            .map(|value| value as u32)
        else {
            continue;
        };
        let row = record["row_number"].as_u64().unwrap_or((index + 2) as u64) as usize;
        let raw = record["raw_address"]
            .as_str()
            .unwrap_or_default()
            .to_owned();
        by_address.entry(address).or_default().push((
            row,
            raw,
            serde_json::to_string(&record["fields"]).unwrap_or_default(),
        ));
    }
    let duplicate_addresses = by_address
        .into_iter()
        .filter_map(|(address, rows)| {
            if rows.len() < 2 {
                return None;
            }
            let conflicting = rows
                .iter()
                .map(|(_, _, fields)| fields)
                .collect::<BTreeSet<_>>()
                .len()
                > 1;
            Some(DuplicateAddress {
                address,
                raw_addresses: rows.iter().map(|(_, raw, _)| raw.clone()).collect(),
                rows: rows.into_iter().map(|(row, _, _)| row).collect(),
                conflicting,
            })
        })
        .collect();

    Ok(TableData {
        spec,
        sha256,
        headers,
        records,
        addresses,
        duplicate_addresses,
        invalid_addresses,
    })
}

#[cfg(test)]
fn is_hex_address(value: &str) -> bool {
    parse_hex_address(value).is_some()
}

fn parse_hex_address(value: &str) -> Option<u32> {
    let digits = value
        .strip_prefix("0x")
        .or_else(|| value.strip_prefix("0X"))?;
    if digits.is_empty() || !digits.chars().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    u64::from_str_radix(digits, 16)
        .ok()
        .filter(|address| *address <= u64::from(u32::MAX))
        .map(|address| address as u32)
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn verify_lock_identity(lock: &Value) -> ImportResult<&Map<String, Value>> {
    let root = lock
        .as_object()
        .ok_or_else(|| ImportError("lock manifest must be an object".into()))?;
    if root.get("schema_version").and_then(Value::as_u64) != Some(1) {
        return Err(ImportError(
            "lock manifest schema_version must be the number 1".into(),
        ));
    }
    let sources = root
        .get("sources")
        .and_then(Value::as_object)
        .ok_or_else(|| ImportError("lock manifest sources must be an object".into()))?;
    let source = sources
        .get("function_map")
        .and_then(Value::as_object)
        .ok_or_else(|| {
            ImportError("lock manifest sources.function_map must be an object".into())
        })?;
    let commit = source
        .get("commit")
        .and_then(Value::as_str)
        .ok_or_else(|| ImportError("lock manifest function_map.commit must be a string".into()))?;
    if commit != EXPECTED_COMMIT {
        return Err(ImportError(format!(
            "function-map commit mismatch: lock has {commit}, expected {EXPECTED_COMMIT}"
        )));
    }
    let repository = source
        .get("repository")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            ImportError("lock manifest function_map.repository must be a string".into())
        })?;
    if repository != EXPECTED_REPOSITORY {
        return Err(ImportError(format!(
            "function-map repository mismatch: lock has {repository}, expected {EXPECTED_REPOSITORY}"
        )));
    }
    if !source.get("files").is_some_and(Value::is_object) {
        return Err(ImportError(
            "lock manifest function_map.files must be an object".into(),
        ));
    }
    Ok(source)
}

fn verify_checkout_commit(source: &Path) -> ImportResult<()> {
    let source_text = source.to_string_lossy();
    let result = Command::new("git")
        .args(["-C", source_text.as_ref(), "rev-parse", "HEAD"])
        .output()
        .map_err(|e| ImportError(format!("verify function-map checkout commit: {e}")))?;
    if !result.status.success() {
        let detail = String::from_utf8_lossy(&result.stderr).trim().to_owned();
        return Err(ImportError(format!(
            "source directory is not a readable git checkout: {}",
            if detail.is_empty() {
                "git rev-parse HEAD failed"
            } else {
                &detail
            }
        )));
    }
    let actual = String::from_utf8_lossy(&result.stdout).trim().to_owned();
    if actual != EXPECTED_COMMIT {
        return Err(ImportError(format!(
            "function-map checkout commit mismatch: source has {actual}, expected {EXPECTED_COMMIT}"
        )));
    }
    Ok(())
}

fn verify_file_lock(
    spec: &TableSpec,
    entry: &Value,
    actual_sha: &str,
    bytes: &[u8],
) -> ImportResult<()> {
    let entry = entry
        .as_object()
        .ok_or_else(|| ImportError(format!("lock entry for {} must be an object", spec.path)))?;
    let expected_sha = entry
        .get("sha256")
        .and_then(Value::as_str)
        .ok_or_else(|| ImportError(format!("lock entry for {} is missing sha256", spec.path)))?;
    if !expected_sha.eq_ignore_ascii_case(actual_sha) {
        return Err(ImportError(format!(
            "sha256 mismatch for {}: lock has {}, actual {}",
            spec.path, expected_sha, actual_sha
        )));
    }
    let expected_count = entry.get("rows").and_then(Value::as_u64).ok_or_else(|| {
        ImportError(format!(
            "lock entry for {} rows must be a number",
            spec.path
        ))
    })?;
    let actual_count = bytes
        .split(|byte| *byte == b'\n')
        .skip(1)
        .filter(|line| !line.is_empty() && *line != b"\r")
        .count() as u64;
    if expected_count != actual_count {
        return Err(ImportError(format!(
            "row-count mismatch for {}: lock has {}, actual {}",
            spec.path, expected_count, actual_count
        )));
    }
    Ok(())
}

fn source_identity(tables: &[TableData], executable_validated: bool) -> Value {
    let mut source = Map::new();
    source.insert(
        "repository".into(),
        Value::String(EXPECTED_REPOSITORY.into()),
    );
    source.insert("commit".into(), Value::String(EXPECTED_COMMIT.into()));
    source.insert(
        "address_identity".into(),
        Value::String(
            if executable_validated {
                "validated_va_against_official_3.9.68_pe32"
            } else {
                "raw_hex_until_executable_validation"
            }
            .into(),
        ),
    );
    source.insert(
        "files".into(),
        Value::Array(
            tables
                .iter()
                .map(|table| {
                    let mut file = Map::new();
                    file.insert("path".into(), Value::String(table.spec.path.into()));
                    file.insert("sha256".into(), Value::String(table.sha256.clone()));
                    file.insert(
                        "rows".into(),
                        Value::Number((table.records.len() as u64).into()),
                    );
                    Value::Object(file)
                })
                .collect(),
        ),
    );
    Value::Object(source)
}

fn table_metadata(tables: &[TableData]) -> Value {
    Value::Array(
        tables
            .iter()
            .map(|table| {
                let mut metadata = Map::new();
                metadata.insert("name".into(), Value::String(table.spec.name.into()));
                metadata.insert("source_path".into(), Value::String(table.spec.path.into()));
                metadata.insert(
                    "headers".into(),
                    Value::Array(table.headers.iter().cloned().map(Value::String).collect()),
                );
                metadata.insert(
                    "row_count".into(),
                    Value::Number((table.records.len() as u64).into()),
                );
                metadata.insert(
                    "extra_columns".into(),
                    Value::Array(
                        extra_columns(table)
                            .into_iter()
                            .map(Value::String)
                            .collect(),
                    ),
                );
                Value::Object(metadata)
            })
            .collect(),
    )
}

fn extra_columns(table: &TableData) -> Vec<String> {
    let required: BTreeSet<&str> = table.spec.required.iter().copied().collect();
    table
        .headers
        .iter()
        .filter(|header| !required.contains(header.as_str()))
        .cloned()
        .collect()
}

fn records(tables: &[TableData]) -> Value {
    let mut object = Map::new();
    for table in tables {
        object.insert(table.spec.name.into(), Value::Array(table.records.clone()));
    }
    Value::Object(object)
}

fn reconciliation(tables: &[TableData]) -> Value {
    let by_name: HashMap<&str, &TableData> = tables
        .iter()
        .map(|table| (table.spec.name, table))
        .collect();
    let mut result = Map::new();
    for name in ["broad", "function", "name", "not-high", "global", "data"] {
        if let Some(table) = by_name.get(name) {
            result.insert(name.into(), table_reconciliation(table));
        }
    }
    result.insert("named".into(), table_reconciliation(by_name["function"]));
    let broad = by_name["broad"].addresses.iter().collect::<BTreeSet<_>>();
    let function = by_name["function"]
        .addresses
        .iter()
        .collect::<BTreeSet<_>>();
    let names = by_name["name"].addresses.iter().collect::<BTreeSet<_>>();
    let not_high = by_name["not-high"]
        .addresses
        .iter()
        .collect::<BTreeSet<_>>();
    let global = by_name["global"].addresses.iter().collect::<BTreeSet<_>>();
    let data = by_name["data"].addresses.iter().collect::<BTreeSet<_>>();
    let mut unmatched = Map::new();
    unmatched.insert(
        "broad_not_in_function".into(),
        Value::Number((broad.difference(&function).count() as u64).into()),
    );
    unmatched.insert(
        "function_not_in_broad".into(),
        Value::Number((function.difference(&broad).count() as u64).into()),
    );
    unmatched.insert(
        "function_not_in_name".into(),
        Value::Number((function.difference(&names).count() as u64).into()),
    );
    unmatched.insert(
        "name_not_in_function".into(),
        Value::Number((names.difference(&function).count() as u64).into()),
    );
    unmatched.insert(
        "not_high_not_in_broad".into(),
        Value::Number((not_high.difference(&broad).count() as u64).into()),
    );
    unmatched.insert(
        "global_not_in_data".into(),
        Value::Number((global.difference(&data).count() as u64).into()),
    );
    unmatched.insert(
        "data_not_in_global".into(),
        Value::Number((data.difference(&global).count() as u64).into()),
    );
    result.insert("unmatched".into(), Value::Object(unmatched));
    let mut duplicates = Map::new();
    for table in tables {
        let entries: Vec<Value> = table
            .duplicate_addresses
            .iter()
            .map(|duplicate| {
                let mut item = Map::new();
                item.insert("address".into(), Value::Number(duplicate.address.into()));
                item.insert(
                    "raw_addresses".into(),
                    Value::Array(
                        duplicate
                            .raw_addresses
                            .iter()
                            .cloned()
                            .map(Value::String)
                            .collect(),
                    ),
                );
                item.insert(
                    "rows".into(),
                    Value::Array(
                        duplicate
                            .rows
                            .iter()
                            .map(|row| Value::Number((*row as u64).into()))
                            .collect(),
                    ),
                );
                item.insert("conflicting".into(), Value::Bool(duplicate.conflicting));
                Value::Object(item)
            })
            .collect();
        duplicates.insert(table.spec.name.into(), Value::Array(entries));
    }
    result.insert("duplicates".into(), Value::Object(duplicates));
    Value::Object(result)
}

fn table_reconciliation(table: &TableData) -> Value {
    let duplicate_rows: usize = table
        .duplicate_addresses
        .iter()
        .map(|duplicate| duplicate.rows.len())
        .sum();
    let conflicting = table
        .duplicate_addresses
        .iter()
        .filter(|duplicate| duplicate.conflicting)
        .count();
    let mut value = Map::new();
    value.insert(
        "rows".into(),
        Value::Number((table.records.len() as u64).into()),
    );
    value.insert(
        "unique_addresses".into(),
        Value::Number((table.addresses.iter().collect::<BTreeSet<_>>().len() as u64).into()),
    );
    value.insert(
        "duplicate_address_count".into(),
        Value::Number((table.duplicate_addresses.len() as u64).into()),
    );
    value.insert(
        "duplicate_row_count".into(),
        Value::Number((duplicate_rows as u64).into()),
    );
    value.insert(
        "conflicting_duplicate_count".into(),
        Value::Number((conflicting as u64).into()),
    );
    Value::Object(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_upper_and_lower_hex_addresses() {
        assert!(is_hex_address("0x401000"));
        assert!(is_hex_address("0XABC"));
        assert!(!is_hex_address("401000"));
        assert!(!is_hex_address("0x"));
        assert!(!is_hex_address("0xZZ"));
    }

    #[test]
    fn lock_requires_the_canonical_function_map_entry() {
        let value: Value = serde_json::json!({
            "schema_version": 1,
            "sources": {
                "function_map": {
                    "repository": EXPECTED_REPOSITORY,
                    "commit": EXPECTED_COMMIT,
                    "files": { "map/functions.tsv": { "sha256": "x", "rows": 1 } }
                }
            }
        });
        let source = verify_lock_identity(&value).unwrap();
        assert!(source["files"]["map/functions.tsv"].is_object());
    }

    #[test]
    fn shadow_file_entry_cannot_bypass_canonical_hash() {
        let bytes = b"address\tcategory\tfile\tmethod\tinstructions\n0x1\tgame\ta.cpp\tf\t1\n";
        let value: Value = serde_json::json!({
            "schema_version": 1,
            "sources": {
                "function_map": {
                    "repository": EXPECTED_REPOSITORY,
                    "commit": EXPECTED_COMMIT,
                    "files": { "map/function-files.tsv": { "sha256": "00", "rows": 1 } }
                },
                "untrusted_shadow": {
                    "files": { "map/function-files.tsv": { "sha256": digest(bytes), "rows": 1 } }
                }
            }
        });
        let source = verify_lock_identity(&value).unwrap();
        let error = verify_file_lock(
            &TABLES[0],
            &source["files"]["map/function-files.tsv"],
            &digest(bytes),
            bytes,
        )
        .unwrap_err();
        assert!(error.to_string().contains("sha256 mismatch"));
    }

    #[test]
    fn parser_preserves_extra_columns_and_row_identity() {
        let bytes =
            b"address\tcategory\tfile\tmethod\tinstructions\textra\n0x1\tgame\ta.cpp\tf\t1\tkept\n";
        let table = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(table.records[0]["source_path"], "map/function-files.tsv");
        assert_eq!(table.records[0]["row_number"], 2);
        assert_eq!(table.records[0]["fields"]["extra"], "kept");
        assert_eq!(table.records[0]["status"], "imported-hypothesis");
    }

    #[test]
    fn parser_rejects_missing_required_header() {
        let bytes = b"address\tcategory\tfile\tmethod\n0x1\tgame\ta.cpp\tf\n";
        let error = parse_table(TABLES[0], bytes, digest(bytes)).unwrap_err();
        assert!(error.to_string().contains("missing required header"));
        assert!(error.to_string().contains("instructions"));
    }

    #[test]
    fn parser_records_malformed_address_for_import_failure() {
        let bytes = b"address\tcategory\tfile\tmethod\tinstructions\nnot-hex\tgame\ta.cpp\tf\t1\n";
        let table = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(table.invalid_addresses[0].raw, "not-hex");
        assert_eq!(table.invalid_addresses[0].row, 2);
    }

    #[test]
    fn parser_surfaces_duplicate_addresses() {
        let bytes = b"address\tcategory\tfile\tmethod\tinstructions\n0x1\tgame\ta.cpp\tf\t1\n0x1\tgame\ta.cpp\tg\t2\n";
        let table = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(table.duplicate_addresses.len(), 1);
        assert!(table.duplicate_addresses[0].conflicting);
    }

    #[test]
    fn duplicate_rows_keep_physical_lines_and_equivalent_hex_spellings_collide() {
        let bytes = b"address\tcategory\tfile\tmethod\tinstructions\n0x1\tgame\ta.cpp\tf\t1\n\n0X01\tgame\ta.cpp\tg\t2\n";
        let table = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(table.duplicate_addresses.len(), 1);
        assert_eq!(table.duplicate_addresses[0].address, 1);
        assert_eq!(table.duplicate_addresses[0].rows, vec![2, 4]);
        assert_eq!(
            table.duplicate_addresses[0].raw_addresses,
            vec!["0x1", "0X01"]
        );
    }

    #[test]
    fn addresses_outside_u32_are_invalid() {
        let bytes =
            b"address\tcategory\tfile\tmethod\tinstructions\n0x100000000\tgame\ta.cpp\tf\t1\n";
        let table = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(table.invalid_addresses[0].raw, "0x100000000");
    }

    #[test]
    fn serializing_the_same_records_is_byte_stable() {
        let bytes =
            b"address\tcategory\tfile\tmethod\tinstructions\textra\n0x1\tgame\ta.cpp\tf\t1\tkept\n";
        let first = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        let second = parse_table(TABLES[0], bytes, digest(bytes)).unwrap();
        assert_eq!(
            serde_json::to_vec(&first.records).unwrap(),
            serde_json::to_vec(&second.records).unwrap()
        );
    }

    #[test]
    fn lock_hash_and_row_count_drift_is_rejected() {
        let bytes = b"address\tcategory\tfile\tmethod\tinstructions\n0x1\tgame\ta.cpp\tf\t1\n";
        let hash_error = verify_file_lock(
            &TABLES[0],
            &serde_json::json!({"sha256": "00", "rows": 1}),
            &digest(bytes),
            bytes,
        )
        .unwrap_err();
        assert!(hash_error.to_string().contains("sha256 mismatch"));
        let count_error = verify_file_lock(
            &TABLES[0],
            &serde_json::json!({"sha256": digest(bytes), "rows": 2}),
            &digest(bytes),
            bytes,
        )
        .unwrap_err();
        assert!(count_error.to_string().contains("row-count mismatch"));
    }

    #[test]
    fn reconciliation_keeps_broad_named_and_global_denominators_separate() {
        let broad = parse_table(
            TABLES[0],
            b"address\tcategory\tfile\tmethod\tinstructions\n0x1\tg\tf\tm\t1\n0x2\tg\tf\tm\t1\n",
            "a".into(),
        )
        .unwrap();
        let function = parse_table(TABLES[1], b"address\tsize\tdoc\tname\tconvention\tpurpose\tconfidence\tmodel\n0x1\t1\td\tn\tc\tp\th\tm\n", "b".into()).unwrap();
        let name = parse_table(
            TABLES[2],
            b"address\tfile\tname\tconfidence\tmodel\tcited_in\n0x1\tf\tn\th\tm\t\n",
            "c".into(),
        )
        .unwrap();
        let not_high = parse_table(
            TABLES[3],
            b"address\tfile\tname\tconfidence\treason\n0x2\tf\tn\tl\tr\n",
            "d".into(),
        )
        .unwrap();
        let global = parse_table(TABLES[4], b"address\tsize\ttype\tname\treaders\twriters\tconfidence\tmodel\tcited_in\n0x3\t1\tt\tn\t\t\th\tm\t\n", "e".into()).unwrap();
        let data = parse_table(TABLES[5], b"address\tsize\tdoc\ttype\tname\tdescription\tconfidence\tmodel\treaders\twriters\n0x4\t1\td\tt\tn\td\th\tm\t\t\n", "f".into()).unwrap();
        let value = reconciliation(&[broad, function, name, not_high, global, data]);
        assert_eq!(value["broad"]["rows"], 2);
        assert_eq!(value["function"]["rows"], 1);
        assert_eq!(value["named"]["rows"], 1);
        assert_eq!(value["global"]["rows"], 1);
        assert_eq!(value["data"]["rows"], 1);
    }

    #[test]
    fn parses_a_minimal_i386_pe32_section_map() {
        let mut bytes = vec![0_u8; 0x200];
        bytes[0..2].copy_from_slice(b"MZ");
        bytes[0x3c..0x40].copy_from_slice(&0x80_u32.to_le_bytes());
        bytes[0x80..0x84].copy_from_slice(b"PE\0\0");
        bytes[0x84..0x86].copy_from_slice(&0x014c_u16.to_le_bytes());
        bytes[0x86..0x88].copy_from_slice(&1_u16.to_le_bytes());
        bytes[0x94..0x96].copy_from_slice(&0x00e0_u16.to_le_bytes());
        bytes[0x98..0x9a].copy_from_slice(&0x010b_u16.to_le_bytes());
        bytes[0xa8..0xac].copy_from_slice(&0x1000_u32.to_le_bytes());
        bytes[0xb4..0xb8].copy_from_slice(&0x0040_0000_u32.to_le_bytes());
        bytes[0xd0..0xd4].copy_from_slice(&0x3000_u32.to_le_bytes());
        let section = 0x178;
        bytes[section..section + 5].copy_from_slice(b".text");
        bytes[section + 8..section + 12].copy_from_slice(&0x100_u32.to_le_bytes());
        bytes[section + 12..section + 16].copy_from_slice(&0x1000_u32.to_le_bytes());
        bytes[section + 16..section + 20].copy_from_slice(&0x200_u32.to_le_bytes());
        bytes[section + 36..section + 40].copy_from_slice(&0x6000_0020_u32.to_le_bytes());

        let image = parse_pe(&bytes, "fixture".into()).unwrap();
        assert_eq!(image.image_base, 0x0040_0000);
        assert_eq!(image.entry_point, 0x0040_1000);
        assert!(image.sections[0].contains(0x0040_11ff));
        assert!(!image.sections[0].contains(0x0040_1200));
        assert!(image.sections[0].is_code());
    }

    #[test]
    fn pe_parser_rejects_truncated_and_wrong_architecture_inputs() {
        assert!(parse_pe(b"not a PE", "fixture".into()).is_err());
        let mut bytes = vec![0_u8; 0x100];
        bytes[0..2].copy_from_slice(b"MZ");
        bytes[0x3c..0x40].copy_from_slice(&0x40_u32.to_le_bytes());
        bytes[0x40..0x44].copy_from_slice(b"PE\0\0");
        bytes[0x44..0x46].copy_from_slice(&0x8664_u16.to_le_bytes());
        let error = parse_pe(&bytes, "fixture".into()).unwrap_err();
        assert!(error.to_string().contains("expected i386"));
    }
}
