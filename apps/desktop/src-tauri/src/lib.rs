//! The desktop shell.
//!
//! The shell is a **window** and a **local server**. It has no game
//! logic of its own: the game is the clone's own web client, and the
//! shell points a web view at it.
//!
//! ## Where the game comes from
//!
//! Two ways, and the choice is the shell's first job:
//!
//! - **local** — the shell starts the project's own server on
//!   `127.0.0.1` and points the web view at it. The player needs
//!   nothing installed: the server ships with the app.
//! - **remote** — the shell is given a server's address with
//!   `--server <url>` and points the web view at that. The player
//!   plays against somebody else's server.
//!
//! ## No Flash
//!
//! The shell loads a **web view**, and the client it loads is the
//! clone's own. There is no SWF, no Flash Player and no Flash browser
//! anywhere in the app, and `scripts/check-no-flash.mjs` proves it by
//! scanning what would be shipped.
//!
//! ## The window
//!
//! The game was built for a 760 by 600 stage, and the client's own
//! `TutorialMain` carries those numbers. The window is that size, and
//! it will not go below it.

pub mod certificate;

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

/// The default port the local server listens on.
pub const DEFAULT_LOCAL_PORT: u16 = 8080;

/// The file-name prefix of the packaged server's sidecar. Tauri adds the
/// target triple and, on Windows, `.exe` to `bundle.externalBin`.
pub const SIDECAR_PREFIX: &str = "swl-server";
/// The server's entry point in development, run from the repository.
pub const DEV_SERVER_SCRIPT: &str = "apps/server/src/main.ts";
/// The bundled server's entry, relative to the app's resource directory.
pub const SIDECAR_ENTRY: &str = "server/runtime/start.mjs";

/// The port the client was built for, in the client's own terms.
pub const STAGE_WIDTH: u32 = 760;
/// The height, in the client's own terms.
pub const STAGE_HEIGHT: u32 = 600;

/// Where the game is played.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ServerTarget {
    /// The shell's own server, on the loopback interface.
    Local { port: u16 },
    /// Somebody else's server.
    Remote { url: String },
}

impl ServerTarget {
    /// The address the web view is pointed at.
    pub fn url(&self) -> String {
        match self {
            ServerTarget::Local { port } => format!("http://127.0.0.1:{port}/"),
            ServerTarget::Remote { url } => url.clone(),
        }
    }

    /// Whether the shell has to start a server.
    pub fn is_local(&self) -> bool {
        matches!(self, ServerTarget::Local { .. })
    }
}

/// Read the server target from the command line.
///
/// `--server <url>` picks a remote server. Anything else is the local
/// one, and `--port <n>` picks its port.
pub fn resolve_server_target(args: &[String]) -> ServerTarget {
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--server" | "-s" => {
                if let Some(url) = args.get(index + 1) {
                    return ServerTarget::Remote {
                        url: normalise_url(url),
                    };
                }
            }
            "--port" | "-p" => {
                if let Some(port) = args.get(index + 1).and_then(|value| value.parse().ok()) {
                    return ServerTarget::Local { port };
                }
            }
            _ => {}
        }
        index += 1;
    }
    ServerTarget::Local {
        port: DEFAULT_LOCAL_PORT,
    }
}

/// A URL with a trailing slash, so the web view's relative paths work.
fn normalise_url(url: &str) -> String {
    let trimmed = url.trim();
    if trimmed.ends_with('/') {
        trimmed.to_string()
    } else {
        format!("{trimmed}/")
    }
}

/// How to start the local server.
///
/// In a **bundled** app the server is a sidecar beside the executable.
/// In **development** it is the project's own Node server, run from the
/// repository.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ServerCommand {
    /// A sidecar binary, with its arguments.
    Sidecar { program: String, args: Vec<String> },
    /// The Node server, run from the repository.
    Development { program: String, script: String },
}

impl ServerCommand {
    /// The command that starts the server.
    pub fn to_command(&self) -> Command {
        match self {
            ServerCommand::Sidecar { program, args } => {
                let mut command = Command::new(program);
                command.args(args);
                command
            }
            ServerCommand::Development { program, script } => {
                let mut command = Command::new(program);
                command.arg(script);
                command
            }
        }
    }
}

/// Choose how the local server starts.
///
/// `packaged` is `!tauri::is_dev()`. A packaged build has no repository and
/// cannot assume `node` is on the player's PATH, so it runs the sidecar
/// Tauri placed beside the executable. Development keeps the repository's
/// own Node server, which is the path the tests and CI exercise.
pub fn server_command(packaged: bool, exe_dir: &Path, resource_dir: &Path) -> ServerCommand {
    if !packaged {
        return development_command();
    }

    // `externalBin` puts the binary beside the executable, named with the
    // target triple. Find it rather than hard-coding a triple the build
    // machine may not match.
    let program = find_sidecar(exe_dir).unwrap_or_else(|| {
        exe_dir.join(format!("{SIDECAR_PREFIX}{}", std::env::consts::EXE_SUFFIX))
    });
    ServerCommand::Sidecar {
        program: program.to_string_lossy().into_owned(),
        args: vec![resource_dir
            .join(SIDECAR_ENTRY)
            .to_string_lossy()
            .into_owned()],
    }
}

/// The sidecar beside an executable, if there is one.
fn find_sidecar(exe_dir: &Path) -> Option<PathBuf> {
    let mut found: Vec<PathBuf> = std::fs::read_dir(exe_dir)
        .ok()?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.is_file()
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with(SIDECAR_PREFIX))
        })
        .collect();
    found.sort();
    found.into_iter().next()
}

/// The local server, as a child process.
pub struct LocalServer {
    child: Child,
    port: u16,
}

impl LocalServer {
    /// Start the server and wait for it to answer.
    pub fn start(command: ServerCommand, port: u16, timeout: Duration) -> Result<Self, String> {
        let mut child = command
            .to_command()
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|error| format!("could not start the local server: {error}"))?;

        if !wait_for_health(port, timeout) {
            // The server is not answering, so it is stopped rather than
            // left running in the background.
            let _ = child.kill();
            return Err(format!(
                "the local server did not answer on port {port} within {timeout:?}"
            ));
        }

        Ok(LocalServer { child, port })
    }

    /// The port it is on.
    pub fn port(&self) -> u16 {
        self.port
    }
}

impl Drop for LocalServer {
    fn drop(&mut self) {
        // The server does not outlive the window.
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Wait for the server's health check to answer.
fn wait_for_health(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if health_check(port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    false
}

/// Ask the server whether it is alive.
///
/// The request is written by hand, so the shell needs no HTTP client.
fn health_check(port: u16) -> bool {
    let address = format!("127.0.0.1:{port}");
    let mut socket = match TcpStream::connect(address) {
        Ok(socket) => socket,
        Err(_) => return false,
    };
    let _ = socket.set_read_timeout(Some(Duration::from_millis(500)));
    let _ = socket.set_write_timeout(Some(Duration::from_millis(500)));
    if socket
        .write_all(b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut buffer = [0_u8; 256];
    match socket.read(&mut buffer) {
        Ok(count) => {
            let response = String::from_utf8_lossy(&buffer[..count]);
            response.contains("200") && response.contains("ok")
        }
        Err(_) => false,
    }
}

/// The shell's state, which the front end can ask about.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ShellState {
    /// Where the game is played.
    pub server_url: String,
    /// Whether the shell started the server itself.
    pub local: bool,
    /// What the shell found when it checked the remote server's
    /// certificate. It is `None` for the local server, which has no
    /// certificate.
    pub certificate: Option<certificate::CertificateReport>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let args: Vec<String> = std::env::args().collect();
    let target = resolve_server_target(&args);
    // Tauri sets `custom-protocol` for a packaged build. That, rather than
    // the optimisation level, is what decides where the server lives.
    let packaged = !tauri::is_dev();

    // The remote server's **certificate** is checked before the web
    // view is pointed at it, and the address is shown to the player.
    // A certificate that does not verify means the shell does not
    // connect: it is better to say why than to fail in a web view.
    let (report, failure) = match &target {
        ServerTarget::Remote { url } => match certificate::parse_remote(url) {
            Ok(server) => {
                match certificate::check_certificate(&server, certificate::DEFAULT_TIMEOUT) {
                    Ok(report) => (Some(report), None),
                    Err(error) => (None, Some(error)),
                }
            }
            Err(error) => (None, Some(error)),
        },
        ServerTarget::Local { .. } => (None, None),
    };

    let state = ShellState {
        server_url: target.url(),
        local: target.is_local(),
        certificate: report.clone(),
    };
    // The closure needs its own copy, because the state is managed with
    // the builder and the two cannot both take it.
    let server_url = state.server_url.clone();
    let local = target.is_local();

    let mut builder = tauri::Builder::default();

    builder = builder.manage(state);
    builder = builder.invoke_handler(tauri::generate_handler![shell_state]);

    builder = builder.setup(move |app| {
        use tauri::Manager;

        // The local server is started before the window is pointed at it,
        // so the first request the client makes does not fail.
        if local {
            if let ServerTarget::Local { port } = target {
                let exe_dir = std::env::current_exe()
                    .ok()
                    .and_then(|path| path.parent().map(Path::to_path_buf))
                    .unwrap_or_default();
                let resource_dir = app.path().resource_dir().unwrap_or_default();
                let command = server_command(packaged, &exe_dir, &resource_dir);
                let server = LocalServer::start(command, port, Duration::from_secs(30))
                    .map_err(std::io::Error::other)?;
                app.manage(server);
            }
        }

        if let Some(window) = app.get_webview_window("main") {
            // The title carries the address the player is about to play
            // against, and what the check found. The title is set
            // **before** the navigation, so the player sees the address
            // before the game connects.
            if let Some(report) = &report {
                let _ = window.set_title(&format!("{} \u{2014} {}", report.address, report.note));
            }
            match &failure {
                Some(error) => {
                    // The certificate did not verify, so the shell does
                    // not connect.
                    let _ = window.set_title(&format!("The server was not checked: {error}"));
                }
                None => {
                    if let Ok(url) = tauri::Url::parse(server_url.as_str()) {
                        let _ = window.navigate(url);
                    }
                }
            }
        }

        Ok(())
    });

    builder
        .run(tauri::generate_context!())
        .expect("the shell could not start");
}

/// The command that starts the server in development.
fn development_command() -> ServerCommand {
    ServerCommand::Development {
        program: "node".to_string(),
        script: DEV_SERVER_SCRIPT.to_string(),
    }
}

/// The shell's state, for the front end.
#[tauri::command]
fn shell_state(state: tauri::State<'_, ShellState>) -> ShellState {
    state.inner().clone()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    #[test]
    fn the_local_server_is_the_default() {
        let target = resolve_server_target(&args(&[]));
        assert_eq!(
            target,
            ServerTarget::Local {
                port: DEFAULT_LOCAL_PORT
            }
        );
        assert!(target.is_local());
        assert_eq!(target.url(), "http://127.0.0.1:8080/");
    }

    #[test]
    fn a_remote_server_is_read_from_the_command_line() {
        let target = resolve_server_target(&args(&["--server", "https://play.example"]));
        assert_eq!(
            target,
            ServerTarget::Remote {
                url: "https://play.example/".to_string()
            }
        );
        assert!(!target.is_local());
    }

    #[test]
    fn a_remote_url_keeps_its_trailing_slash() {
        let target = resolve_server_target(&args(&["--server", "https://play.example/"]));
        assert_eq!(target.url(), "https://play.example/");
    }

    #[test]
    fn a_port_is_read_from_the_command_line() {
        let target = resolve_server_target(&args(&["--port", "9090"]));
        assert_eq!(target, ServerTarget::Local { port: 9090 });
        assert_eq!(target.url(), "http://127.0.0.1:9090/");
    }

    #[test]
    fn an_unknown_argument_is_ignored() {
        let target = resolve_server_target(&args(&["--verbose", "--port", "1234"]));
        assert_eq!(target, ServerTarget::Local { port: 1234 });
    }

    #[test]
    fn a_missing_server_argument_falls_back_to_the_local_one() {
        let target = resolve_server_target(&args(&["--server"]));
        assert_eq!(
            target,
            ServerTarget::Local {
                port: DEFAULT_LOCAL_PORT
            }
        );
    }

    #[test]
    fn the_window_is_the_client_own_stage() {
        // The client's own numbers: `PRIOR_STAGE_WIDTH` and
        // `PRIOR_STAGE_HEIGHT` in `TutorialMain.as`.
        assert_eq!(STAGE_WIDTH, 760);
        assert_eq!(STAGE_HEIGHT, 600);
    }

    #[test]
    fn a_command_that_does_not_exist_fails_rather_than_hanging() {
        let command = ServerCommand::Sidecar {
            program: "no-such-binary-at-all".to_string(),
            args: vec![],
        };
        let result = LocalServer::start(command, 1, Duration::from_millis(200));
        assert!(result.is_err());
    }

    #[test]
    fn a_packaged_local_server_uses_the_sidecar() {
        let bin = tempfile::tempdir().unwrap();
        let resources = tempfile::tempdir().unwrap();
        let sidecar = bin.path().join("swl-server-x86_64-pc-windows-msvc");
        std::fs::write(&sidecar, b"a stand-in for the bundled runtime").unwrap();

        let command = server_command(true, bin.path(), resources.path());
        let ServerCommand::Sidecar { program, args } = command else {
            panic!("a packaged shell must use the sidecar, not node and the source tree");
        };
        assert_eq!(program.as_str(), sidecar.to_string_lossy().as_ref());
        assert_eq!(
            args,
            vec![resources
                .path()
                .join(SIDECAR_ENTRY)
                .to_string_lossy()
                .into_owned()]
        );
    }

    #[test]
    fn a_development_local_server_uses_the_repository_script() {
        let bin = tempfile::tempdir().unwrap();
        let resources = tempfile::tempdir().unwrap();
        let command = server_command(false, bin.path(), resources.path());
        assert_eq!(
            command,
            ServerCommand::Development {
                program: "node".to_string(),
                script: DEV_SERVER_SCRIPT.to_string(),
            }
        );
    }

    #[test]
    fn a_missing_sidecar_still_selects_a_sidecar_path() {
        let bin = tempfile::tempdir().unwrap();
        let resources = tempfile::tempdir().unwrap();
        let command = server_command(true, bin.path(), resources.path());
        let ServerCommand::Sidecar { program, .. } = command else {
            panic!("a packaged shell must not fall back to the development command");
        };
        assert!(program.contains(SIDECAR_PREFIX), "program was {program}");
    }

    #[test]
    fn a_sidecar_command_runs_the_configured_binary() {
        let dir = tempfile::tempdir().unwrap();
        let program = dir.path().join("swl-server-x86_64-pc-windows-msvc");
        let entry = dir.path().join("start.mjs");
        let program = program.to_string_lossy().into_owned();
        let entry = entry.to_string_lossy().into_owned();
        let command = ServerCommand::Sidecar {
            program: program.clone(),
            args: vec![entry.clone()],
        }
        .to_command();
        // `Command`'s Debug prints the program and its arguments, with
        // the same escaping as a string literal.
        let rendered = format!("{command:?}");
        assert!(rendered.contains(&format!("{program:?}")));
        assert!(rendered.contains(&format!("{entry:?}")));
    }
}
