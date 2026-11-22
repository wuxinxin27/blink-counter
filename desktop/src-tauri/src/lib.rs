use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WindowEvent,
};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tauri_plugin_notification::NotificationExt;

fn show_main_window(app: &AppHandle, always_on_top: bool) {
    #[cfg(target_os = "macos")]
    {
        let _ = app.set_activation_policy(tauri::ActivationPolicy::Regular);
    }
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.set_skip_taskbar(false);
        let _ = window.unminimize();
        let _ = window.show();
        if always_on_top {
            let _ = window.set_always_on_top(true);
        }
        let _ = window.set_focus();
    }
}

fn hide_main_to_tray(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.set_always_on_top(false);
        let _ = window.set_skip_taskbar(true);
        let _ = window.hide();
    }
    #[cfg(target_os = "macos")]
    {
        let _ = app.set_activation_policy(tauri::ActivationPolicy::Accessory);
    }
}

#[tauri::command]
fn surface_alert(app: AppHandle, title: String, body: String, bring_to_front: bool) {
    let _ = app.notification().builder().title(&title).body(&body).show();

    if bring_to_front {
        show_main_window(&app, true);
    }
}

#[tauri::command]
fn release_always_on_top(app: AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.set_always_on_top(false);
    }
}

#[tauri::command]
fn minimize_to_tray(app: AppHandle) {
    hide_main_to_tray(&app);
}

#[tauri::command]
fn update_tray_tooltip(app: AppHandle, text: String) {
    if let Some(tray) = app.tray_by_id("main-tray") {
        let _ = tray.set_tooltip(Some(&text));
    }
}

#[tauri::command]
fn get_autostart(app: AppHandle) -> bool {
    app.autolaunch().is_enabled().unwrap_or(false)
}

#[tauri::command]
fn set_autostart(app: AppHandle, enabled: bool) -> Result<bool, String> {
    let manager = app.autolaunch();
    if enabled {
        manager.enable().map_err(|e| e.to_string())?;
    } else {
        manager.disable().map_err(|e| e.to_string())?;
    }
    Ok(manager.is_enabled().unwrap_or(enabled))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec!["--autostart"]),
        ))
        .setup(|app| {
            let show_item =
                MenuItem::with_id(app, "show", "Show Blink Counter", true, None::<&str>)?;
            let break_item =
                MenuItem::with_id(app, "break_now", "Start 20s Eye Break", true, None::<&str>)?;
            let quit_item =
                MenuItem::with_id(app, "quit", "Quit Blink Counter", true, None::<&str>)?;

            let menu = Menu::with_items(app, &[&show_item, &break_item, &quit_item])?;

            let mut tray_builder = TrayIconBuilder::with_id("main-tray")
                .menu(&menu)
                .tooltip("Blink Counter — Eye Wellness")
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        show_main_window(app, false);
                    }
                    "break_now" => {
                        show_main_window(app, false);
                        let _ = app.emit("tray-start-break", ());
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                hide_main_to_tray(app);
                            } else {
                                show_main_window(app, false);
                            }
                        }
                    }
                });

            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }

            let _ = tray_builder.build(app)?;

            // When auto-launched at OS login, start quietly in the status bar / tray only
            if std::env::args().any(|arg| arg == "--autostart") {
                hide_main_to_tray(app.handle());
            }

            Ok(())
        })
        .on_window_event(|window, event| match event {
            // Closing window hides to status bar / system tray only (no Dock / taskbar icon)
            WindowEvent::CloseRequested { api, .. } => {
                api.prevent_close();
                hide_main_to_tray(window.app_handle());
            }
            // Minimizing window also tucks it into status bar / system tray only
            WindowEvent::Resized(_) => {
                if window.is_visible().unwrap_or(false) && window.is_minimized().unwrap_or(false) {
                    hide_main_to_tray(window.app_handle());
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            surface_alert,
            release_always_on_top,
            minimize_to_tray,
            update_tray_tooltip,
            get_autostart,
            set_autostart,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Blink Counter desktop application");
}
