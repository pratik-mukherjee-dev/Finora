use std::fs;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::time::Duration;
use serde_json::json;
use tauri::{AppHandle, Manager};

pub struct Sidecars {
    pub postgres: Option<Child>,
    pub django: Option<Child>,
    pub pg_ctl: PathBuf,
    pub pgdata: PathBuf,
}

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().port()
}

/// Returns (Sidecars, django_port).
pub fn start(app: &AppHandle) -> Result<(Sidecars, u16), String> {
//     let res = app.path().resource_dir().map_err(|e| e.to_string())?;
    let res = resources_root(app);
    let pg_bin = res.join("pgsql/bin");
    let initdb = pg_bin.join("initdb.exe");
    let pg_ctl = pg_bin.join("pg_ctl.exe");
    let psql = pg_bin.join("psql.exe");
    let backend_exe = res.join("backend/finora-backend.exe");
    // Diagnostics: fail loudly with the actual resolved paths.
    if !pg_bin.is_dir() {
        return Err(format!("pg_bin dir not found: {}", pg_bin.display()));
    }
    if !initdb.is_file() {
        return Err(format!("initdb.exe not found: {}", initdb.display()));
    }
    if !backend_exe.is_file() {
        return Err(format!("backend exe not found: {}", backend_exe.display()));
    }

    let data = app.path().app_data_dir().map_err(|e| e.to_string())?;
    fs::create_dir_all(&data).map_err(|e| e.to_string())?;
    let pgdata = data.join("pgdata");
    let runtime_json = data.join("runtime.json");

    let pg_port = free_port();
    let dj_port = free_port();

    // 1. initdb on first launch
    let first = !pgdata.exists();
    if first {
        let pwfile = data.join("pgpw.txt");
        fs::write(&pwfile, "finora").map_err(|e| e.to_string())?;
        let st = Command::new(&initdb)
            .current_dir(&pg_bin)
            .args(["-D", pgdata.to_str().unwrap(), "-U", "finora",
                   "--auth=md5", &format!("--pwfile={}", pwfile.to_str().unwrap()),
                   "-E", "UTF8"])
            .status()
            .map_err(|e| format!("initdb spawn failed (cwd={}): {}", pg_bin.display(), e))?;
        let _ = fs::remove_file(&pwfile);
        if !st.success() { return Err("initdb failed".into()); }
    }

    // 2. start postgres on the chosen port (TCP on localhost)
    let pg = Command::new(&pg_ctl)
        .current_dir(&pg_bin)
        .args(["-D", pgdata.to_str().unwrap(),
               "-o", &format!("-p {} -h 127.0.0.1", pg_port),
               "-w", "start"])
        .spawn().map_err(|e| e.to_string())?;

    std::thread::sleep(Duration::from_millis(2000));

    // 3. first-launch: create DB + pg_trgm extension
    if first {
        let _ = Command::new(&psql)
            .current_dir(&pg_bin)
            .env("PGPASSWORD", "finora")
            .args(["-h", "127.0.0.1", "-p", &pg_port.to_string(),
                   "-U", "finora", "-d", "postgres",
                   "-c", "CREATE DATABASE finora;"])
            .status();
        let _ = Command::new(&psql)
            .current_dir(&pg_bin)
            .env("PGPASSWORD", "finora")
            .args(["-h", "127.0.0.1", "-p", &pg_port.to_string(),
                   "-U", "finora", "-d", "finora",
                   "-c", "CREATE EXTENSION IF NOT EXISTS pg_trgm;"])
            .status();
    }

    // 4. write runtime.json for Django
    let cfg = json!({
        "db_name": "finora", "db_user": "finora", "db_password": "finora",
        "db_host": "127.0.0.1", "db_port": pg_port
    });
    fs::write(&runtime_json, cfg.to_string()).map_err(|e| e.to_string())?;

    // 5. spawn Django (add pg_bin to PATH so libpq DLLs resolve)
    //    FINORA_DEV_MODE is derived from the Rust compile-time debug flag:
    //    - `cargo tauri dev`   (debug)   → "1" → license self-service enabled
    //    - `cargo tauri build` (release) → "0" → license endpoints locked
    let dev_mode = if cfg!(debug_assertions) { "1" } else { "0" };
    let path_var = std::env::var("PATH").unwrap_or_default();
    let new_path = format!("{};{}", pg_bin.to_str().unwrap(), path_var);
    let dj = Command::new(&backend_exe)
        .env("FINORA_RUNTIME_CONFIG", runtime_json.to_str().unwrap())
        .env("DJANGO_PORT", dj_port.to_string())
        .env("FINORA_DEV_MODE", dev_mode)
        .env("PATH", new_path)
        .spawn().map_err(|e| e.to_string())?;

    // 6. wait until Django actually serves the health endpoint (not just an open socket)
    let health_url = format!("http://127.0.0.1:{}/health/", dj_port);
    let mut ready = false;
    for _ in 0..60 {
        match ureq::get(&health_url).timeout(Duration::from_millis(1500)).call() {
            Ok(resp) if resp.status() == 200 => { ready = true; break; }
            _ => std::thread::sleep(Duration::from_millis(500)),
        }
    }
    if !ready {
        return Err("Django did not become healthy within timeout".into());
    }


    Ok((Sidecars { postgres: Some(pg), django: Some(dj), pg_ctl, pgdata }, dj_port))
}

pub fn stop(s: &mut Sidecars) {
    if let Some(mut d) = s.django.take() { let _ = d.kill(); }
    let mut cmd = Command::new(&s.pg_ctl);
    if let Some(dir) = s.pg_ctl.parent() {
        cmd.current_dir(dir);
    }
    let _ = cmd
        .args(["-D", s.pgdata.to_str().unwrap(), "-m", "fast", "stop"])
        .status();
    if let Some(mut p) = s.postgres.take() { let _ = p.kill(); }
}


fn resources_root(app: &AppHandle) -> PathBuf {
    // In dev, resources aren't copied to target/. Use the source tree.
    #[cfg(debug_assertions)]
    {
        let _ = app;
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources")
    }
    #[cfg(not(debug_assertions))]
    {
        app.path().resource_dir().unwrap().join("resources")
    }
}
