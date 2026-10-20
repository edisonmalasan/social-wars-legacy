// The desktop shell's entry point.
//
// The shell is a library with a thin binary, so that the whole of it can
// be tested without opening a window.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    swl_desktop_lib::run()
}
