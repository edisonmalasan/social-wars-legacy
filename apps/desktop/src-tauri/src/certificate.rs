//! The remote server's certificate.
//!
//! The shell can be pointed at somebody else's server with
//! `--server <url>`. Before the game connects, the shell checks that
//! server's **certificate**, and it shows the player the address it is
//! about to connect to and what it found.
//!
//! ## What the check is
//!
//! A real TLS handshake against the **operating system's own roots**.
//! That is the same trust the web view would use, and it is the check
//! that matters: a certificate that does not verify, or that has
//! expired, or that is for somebody else's host, fails the handshake
//! and the shell refuses to connect.
//!
//! The certificate's **fingerprint** is read as well, because it is the
//! one thing a player can compare against the server operator's own
//! answer.
//!
//! ## What it is not
//!
//! It is not a replacement for the web view's own validation, and it is
//! not a pinning implementation. It is the shell saying, out loud, what
//! it is about to do.

use std::sync::{Arc, Mutex};

use rustls::client::danger::{HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier};
use rustls::client::WebPkiServerVerifier;
use rustls::pki_types::{CertificateDer, ServerName, UnixTime};
use rustls::{DigitallySignedStruct, Error as TlsError, SignatureScheme};

/// How long the shell waits for the handshake.
pub const DEFAULT_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(10);

/// A remote server, as the shell understands it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RemoteServer {
    /// The scheme: `http` or `https`.
    pub scheme: String,
    /// The host.
    pub host: String,
    /// The port.
    pub port: u16,
}

impl RemoteServer {
    /// The address, as a player would read it.
    pub fn address(&self) -> String {
        if self.scheme == "https" && self.port == 443 {
            format!("{}://{}", self.scheme, self.host)
        } else {
            format!("{}://{}:{}", self.scheme, self.host, self.port)
        }
    }

    /// Whether the connection is encrypted.
    pub fn is_secure(&self) -> bool {
        self.scheme == "https"
    }
}

/// The default port for a scheme.
pub fn default_port(scheme: &str) -> u16 {
    match scheme {
        "https" => 443,
        _ => 80,
    }
}

/// A remote server, from a URL.
///
/// The URL is parsed **by hand** rather than with a URL library: the
/// shell needs three things from it — the scheme, the host and the
/// port — and a dependency that parses URLs is a dependency that has
/// to be kept up to date.
pub fn parse_remote(url: &str) -> Result<RemoteServer, String> {
    let trimmed = url.trim();
    let (scheme, rest) = match trimmed.split_once("://") {
        Some((scheme, rest)) => (scheme.to_ascii_lowercase(), rest),
        None => return Err(format!("\"{trimmed}\" is not an address with a scheme")),
    };
    if scheme != "http" && scheme != "https" {
        return Err(format!("\"{scheme}\" is not a scheme the shell speaks"));
    }

    // The path, the query and the fragment are not the server's
    // address, and the web view's own path is the client's.
    let authority = rest.split(['/', '?', '#']).next().unwrap_or_default();

    // The credentials, if any, are not part of the address.
    let authority = match authority.rsplit_once('@') {
        Some((_, host)) => host,
        None => authority,
    };

    if authority.is_empty() {
        return Err(format!("\"{trimmed}\" has no host"));
    }

    // An IPv6 address is in brackets.
    let (host, port_text) = if let Some(stripped) = authority.strip_prefix('[') {
        match stripped.split_once(']') {
            Some((host, after)) => {
                let port = after
                    .strip_prefix(':')
                    .and_then(|value| value.parse::<u16>().ok());
                (host.to_string(), port)
            }
            None => return Err(format!("\"{trimmed}\" has an unclosed bracket")),
        }
    } else {
        match authority.rsplit_once(':') {
            Some((host, port)) => {
                let port = port.parse::<u16>().ok();
                (host.to_string(), port)
            }
            None => (authority.to_string(), None),
        }
    };

    if host.is_empty() {
        return Err(format!("\"{trimmed}\" has no host"));
    }

    let port = port_text.unwrap_or_else(|| default_port(&scheme));
    Ok(RemoteServer { scheme, host, port })
}

/// What the shell found when it checked a server.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct CertificateReport {
    /// The address the shell is about to connect to.
    pub address: String,
    /// Whether the connection is encrypted.
    pub secure: bool,
    /// The certificate's fingerprint, in the form players compare.
    pub fingerprint: Option<String>,
    /// Whether the certificate verified.
    pub verified: bool,
    /// A note, for the player.
    pub note: String,
}

/// The verifier that keeps the certificate.
///
/// It does the real verification — the web PKI check against the
/// operating system's roots — and it keeps the end-entity certificate
/// so that the shell can read its fingerprint.
#[derive(Debug)]
struct CapturingVerifier {
    /// The real verifier.
    inner: Arc<WebPkiServerVerifier>,
    /// The certificate that was offered.
    seen: Arc<Mutex<Option<CertificateDer<'static>>>>,
}

impl ServerCertVerifier for CapturingVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        intermediates: &[CertificateDer<'_>],
        server_name: &ServerName<'_>,
        ocsp_response: &[u8],
        now: UnixTime,
    ) -> Result<ServerCertVerified, TlsError> {
        *self.seen.lock().expect("the certificate's lock") = Some(end_entity.clone().into_owned());
        self.inner
            .verify_server_cert(end_entity, intermediates, server_name, ocsp_response, now)
    }

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, TlsError> {
        self.inner.verify_tls12_signature(message, cert, dss)
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, TlsError> {
        self.inner.verify_tls13_signature(message, cert, dss)
    }

    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        self.inner.supported_verify_schemes()
    }
}

/// The fingerprint of a certificate, in the form players compare.
///
/// The SHA-256 of the certificate's bytes, one byte per group, in
/// lower case and separated by colons — the same shape OpenSSL prints,
/// so it can be compared with a server operator's own answer.
pub fn fingerprint(certificate: &CertificateDer<'_>) -> String {
    let digest = ring::digest::digest(&ring::digest::SHA256, certificate.as_ref());
    digest
        .as_ref()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<Vec<String>>()
        .join(":")
}

/// Check a server's certificate.
///
/// The handshake is a real one, against the operating system's own
/// roots, so a certificate that does not verify fails here rather than
/// in the web view.
pub fn check_certificate(
    server: &RemoteServer,
    timeout: std::time::Duration,
) -> Result<CertificateReport, String> {
    if !server.is_secure() {
        // There is no certificate to check on a plain connection, and
        // the shell says so rather than pretending.
        return Ok(CertificateReport {
            address: server.address(),
            secure: false,
            fingerprint: None,
            verified: false,
            note: "This address is not encrypted. The traffic is in the clear.".to_string(),
        });
    }

    let roots = rustls_native_certs::load_native_certs()
        .map_err(|error| format!("the operating system's roots could not be read: {error}"))?;
    if roots.is_empty() {
        return Err("the operating system has no certificate roots".to_string());
    }

    let provider = Arc::new(rustls::crypto::ring::default_provider());
    // The roots are added one at a time, because `rustls` keeps them as
    // its own trust anchors and does the conversion itself.
    let mut store = rustls::RootCertStore::empty();
    for certificate in roots {
        store
            .add(certificate)
            .map_err(|error| format!("a certificate root was not usable: {error}"))?;
    }
    let verifier =
        WebPkiServerVerifier::builder_with_provider(Arc::new(store), Arc::clone(&provider))
            .build()
            .map_err(|error| format!("the certificate roots are not usable: {error}"))?;

    let seen: Arc<Mutex<Option<CertificateDer<'static>>>> = Arc::new(Mutex::new(None));
    let config = rustls::ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .map_err(|error| format!("no TLS version could be chosen: {error}"))?
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(CapturingVerifier {
            inner: verifier,
            seen: Arc::clone(&seen),
        }))
        .with_no_client_auth();

    let name = ServerName::try_from(server.host.clone())
        .map_err(|_| format!("\"{}\" is not a name a certificate can be for", server.host))?;
    let connection = rustls::ClientConnection::new(Arc::new(config), name)
        .map_err(|error| format!("the connection could not be set up: {error}"))?;

    let address = format!("{}:{}", server.host, server.port);
    let socket_address = address
        .parse()
        .map_err(|_| format!("\"{address}\" is not an address"))?;
    let socket = std::net::TcpStream::connect_timeout(&socket_address, timeout)
        .map_err(|error| format!("{address} could not be reached: {error}"))?;
    socket
        .set_read_timeout(Some(timeout))
        .map_err(|error| format!("the read timeout could not be set: {error}"))?;
    socket
        .set_write_timeout(Some(timeout))
        .map_err(|error| format!("the write timeout could not be set: {error}"))?;

    // The handshake, which fails if the certificate is not genuine.
    let mut stream = rustls::StreamOwned::new(connection, socket);
    while stream.conn.is_handshaking() {
        stream
            .conn
            .complete_io(&mut stream.sock)
            .map_err(|error| format!("the certificate did not verify: {error}"))?;
    }

    let certificate = seen
        .lock()
        .expect("the certificate's lock")
        .as_ref()
        .map(|certificate| fingerprint(certificate));

    Ok(CertificateReport {
        address: server.address(),
        secure: true,
        fingerprint: certificate,
        verified: true,
        note: "The certificate verified against the operating system's roots.".to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_url_is_taken_apart() {
        let server = parse_remote("https://play.example").unwrap();
        assert_eq!(server.scheme, "https");
        assert_eq!(server.host, "play.example");
        assert_eq!(server.port, 443);
        assert!(server.is_secure());
    }

    #[test]
    fn a_port_is_read() {
        let server = parse_remote("http://127.0.0.1:9090").unwrap();
        assert_eq!(server.port, 9090);
        assert!(!server.is_secure());
    }

    #[test]
    fn the_path_is_not_part_of_the_address() {
        let server = parse_remote("https://play.example/some/path?a=1").unwrap();
        assert_eq!(server.host, "play.example");
        assert_eq!(server.port, 443);
    }

    #[test]
    fn an_ipv6_address_is_read() {
        let server = parse_remote("https://[::1]:8443").unwrap();
        assert_eq!(server.host, "::1");
        assert_eq!(server.port, 8443);
    }

    #[test]
    fn a_scheme_is_required() {
        assert!(parse_remote("play.example").is_err());
    }

    #[test]
    fn an_unknown_scheme_is_refused() {
        assert!(parse_remote("ftp://play.example").is_err());
    }

    #[test]
    fn a_host_is_required() {
        assert!(parse_remote("https://").is_err());
    }

    #[test]
    fn the_address_is_read_the_way_a_player_would() {
        let server = parse_remote("https://play.example").unwrap();
        assert_eq!(server.address(), "https://play.example");
        let local = parse_remote("http://127.0.0.1:9090").unwrap();
        assert_eq!(local.address(), "http://127.0.0.1:9090");
    }

    #[test]
    fn a_plain_address_says_it_is_not_encrypted() {
        let server = parse_remote("http://play.example").unwrap();
        let report = check_certificate(&server, DEFAULT_TIMEOUT).unwrap();
        assert!(!report.secure);
        assert!(!report.verified);
        assert!(report.fingerprint.is_none());
        assert!(report.note.contains("not encrypted"));
    }

    #[test]
    fn an_unreachable_server_is_an_error_rather_than_a_panic() {
        let server = parse_remote("https://127.0.0.1:1").unwrap();
        assert!(check_certificate(&server, std::time::Duration::from_millis(500)).is_err());
    }

    #[test]
    fn a_fingerprint_is_in_pairs() {
        // A certificate's bytes, so the fingerprint has a shape: the
        // SHA-256, one byte per group, the way OpenSSL prints it.
        let certificate = CertificateDer::from(vec![0_u8; 32]);
        let printed = fingerprint(&certificate);
        assert_eq!(printed.split(':').count(), 32);
        assert_eq!(printed.len(), 32 * 3 - 1);
        for group in printed.split(':') {
            assert_eq!(group.len(), 2);
            assert!(group
                .chars()
                .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()));
        }
    }

    #[test]
    fn the_fingerprint_is_the_hash_of_the_certificate() {
        // The same bytes give the same fingerprint, and different bytes
        // do not: that is what makes it worth comparing.
        let one = fingerprint(&CertificateDer::from(vec![1_u8; 32]));
        let two = fingerprint(&CertificateDer::from(vec![2_u8; 32]));
        assert_ne!(one, two);
        assert_eq!(one, fingerprint(&CertificateDer::from(vec![1_u8; 32])));
    }
}
