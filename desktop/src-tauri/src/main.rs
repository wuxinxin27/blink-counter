#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    blink_counter_lib::run();
}
