mod backend;
use std::sync::Mutex;
use tauri::Manager;

struct AppState {
    sidecars: Mutex<Option<backend::Sidecars>>,
    django_port: Mutex<u16>,
}

#[tauri::command]
fn get_django_port(state: tauri::State<AppState>) -> u16 {
    *state.django_port.lock().unwrap()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .setup(|app| {
            // Register state up front with port 0 (= "not ready yet") so the
            // window can open and render a splash instead of blocking the UI
            // thread on the Postgres + Django boot.
            app.manage(AppState {
                sidecars: Mutex::new(None),
                django_port: Mutex::new(0),
            });

            // Run the heavy startup off the main/UI thread.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                match backend::start(&handle) {
                    Ok((sc, dj_port)) => {
                        let state = handle.state::<AppState>();
                        *state.sidecars.lock().unwrap() = Some(sc);
                        *state.django_port.lock().unwrap() = dj_port;
                        println!("Finora backend ready on 127.0.0.1:{dj_port}");
                    }
                    Err(e) => {
                        eprintln!("sidecar startup failed: {e}");
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<AppState>();
                let taken = state.sidecars.lock().unwrap().take();
                if let Some(mut sc) = taken {
                    backend::stop(&mut sc);
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_django_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}