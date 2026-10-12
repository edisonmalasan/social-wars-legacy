#!/usr/bin/env python3
"""Server v1 constants: protocol name, loopback host, and its own TCP port.

**Design D7 — v1 listens on its own loopback port.**  The port is deliberately
distinct from both ports the repository already binds:

====================== ====== ==============================================
surface                port   evidence
====================== ====== ==============================================
legacy Flask server     5055  ``server.py:40-43``
Compatibility API v0    5056  ``apps/compat-api/compat_service.py:937``
**Server v1**          **5057** this module
====================== ====== ==============================================

``RESERVED_PORTS`` exists so that the distinctness is a *checked* property
rather than a comment: :func:`assert_port_is_distinct` raises when
:data:`DEFAULT_PORT` collides with a port the repository already owns, and
``tests/test_settings.py`` calls it.  ``netsh interface ipv4 show
excludedportrange protocol=tcp`` on the verified host reports ``5357`` and no
range containing 5057, so 5057 is bindable here; that is a measurement of one
host and not a guarantee about any other.

Nothing else in this module is behaviour.  The exit codes are ``run.py``'s
process-level contract, not a gameplay claim.
"""

from __future__ import annotations

from typing import Tuple

PROTOCOL = "server-v1"

# Loopback only.  There is deliberately no host option, for the same reason
# ``apps/compat-api/run.py`` has none: a server that can be pointed at a
# routable interface is a server that can be reached from off-host.
HOST = "127.0.0.1"

DEFAULT_PORT = 5057

#: Ports the repository already binds, so a collision is detectable.
RESERVED_PORTS: Tuple[int, ...] = (5055, 5056)

# ``run.py`` process exit codes.
EXIT_OK = 0
EXIT_ENVIRONMENT = 2
EXIT_PORT_BUSY = 3
EXIT_SERVER = 4

#: Environment variable overrides, mirroring the Compatibility API's shape.
PORT_ENV = "SERVER_V1_PORT"
CORPUS_ENV = "SERVER_V1_CORPUS"

#: Temporary-directory prefix for a corpus v1 created and owns.
TEMP_PREFIX = "socialwars-server-v1-"


def assert_port_is_distinct() -> None:
    """Raise when :data:`DEFAULT_PORT` is one the repository already uses."""
    if DEFAULT_PORT in RESERVED_PORTS:
        raise AssertionError(
            "Server v1 port %d collides with a reserved port %r"
            % (DEFAULT_PORT, list(RESERVED_PORTS))
        )
    if DEFAULT_PORT == 5055 or DEFAULT_PORT == 5056:
        raise AssertionError(
            "Server v1 must not reuse a legacy or v0 port (design D7); got %d"
            % DEFAULT_PORT
        )


__all__ = [
    "CORPUS_ENV",
    "DEFAULT_PORT",
    "EXIT_ENVIRONMENT",
    "EXIT_OK",
    "EXIT_PORT_BUSY",
    "EXIT_SERVER",
    "HOST",
    "PORT_ENV",
    "PROTOCOL",
    "RESERVED_PORTS",
    "TEMP_PREFIX",
    "assert_port_is_distinct",
]
