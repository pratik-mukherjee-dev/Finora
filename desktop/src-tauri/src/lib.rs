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
        .setup(|app| {
            let handle = app.handle().clone();
            let (sc, dj_port) = backend::start(&handle).expect("sidecar startup failed");
            app.manage(AppState {
                sidecars: Mutex::new(Some(sc)),
                django_port: Mutex::new(dj_port),
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
