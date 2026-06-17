use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

/// Handle to the Python sidecar so we can terminate it on app exit.
struct Backend(Mutex<Option<Child>>);

/// Launch the Python sidecar.
///
/// Dev: run the project's venv Python directly (fast iteration, no bundling).
/// Release packaging will instead use a PyInstaller sidecar binary (milestone 4);
/// that path is intentionally not wired yet.
fn spawn_backend() -> Option<Child> {
    #[cfg(debug_assertions)]
    {
        // CARGO_MANIFEST_DIR = <repo>/desktop/src-tauri at compile time.
        let backend_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("backend");
        let python = backend_dir.join(".venv").join("bin").join("python");
        match Command::new(&python)
            .args(["-m", "app.main", "--port", "8765"])
            .current_dir(&backend_dir)
            .spawn()
        {
            Ok(child) => return Some(child),
            Err(e) => eprintln!("Failed to spawn backend ({:?}): {e}", python),
        }
    }
    None
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            app.manage(Backend(Mutex::new(spawn_backend())));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(backend) = app_handle.try_state::<Backend>() {
                    if let Some(child) = backend.0.lock().unwrap().as_mut() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
