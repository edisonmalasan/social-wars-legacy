#!/usr/bin/env python3
"""Settings and the loopback port (tasks 1.4 and 3.3)."""

from __future__ import annotations

import unittest

import harness  # noqa: F401  (path setup)
import server_v1_settings as settings


class PortDistinctnessTests(unittest.TestCase):
    """v1 binds a port the repository does not already own (design D7)."""

    def test_the_port_is_distinct_from_both_existing_surfaces(self) -> None:
        self.assertNotIn(settings.DEFAULT_PORT, settings.RESERVED_PORTS)
        settings.assert_port_is_distinct()

    def test_the_reserved_ports_are_the_two_the_repository_already_binds(self) -> None:
        # 5055 is ``server.py``'s legacy port and 5056 is
        # ``apps/compat-api/compat_service.py``'s.  Written out rather than
        # derived, so a change to the reservation list is a test failure instead
        # of a silently-accepted overlap.
        self.assertEqual((5055, 5056), settings.RESERVED_PORTS)
        self.assertEqual("127.0.0.1", settings.HOST)

    def test_the_distinctness_assertion_can_fail(self) -> None:
        """A colliding port must raise, not pass quietly."""
        original = settings.DEFAULT_PORT
        try:
            settings.DEFAULT_PORT = 5056
            with self.assertRaises(AssertionError) as caught:
                settings.assert_port_is_distinct()
            self.assertIn("5056", str(caught.exception))
        finally:
            settings.DEFAULT_PORT = original
        settings.assert_port_is_distinct()

    def test_a_second_collision_path_is_independently_checked(self) -> None:
        """The literal guard catches what the membership guard cannot.

        ``RESERVED_PORTS`` is a module constant, so a future edit that removed
        5056 from it would make the membership check vacuous.  The explicit
        literal check is what makes that edit detectable, and this test proves
        it fires independently.
        """
        original = settings.DEFAULT_PORT
        original_reserved = settings.RESERVED_PORTS
        try:
            settings.DEFAULT_PORT = 5055
            settings.RESERVED_PORTS = (9999,)  # membership check now passes
            with self.assertRaises(AssertionError) as caught:
                settings.assert_port_is_distinct()
            self.assertIn("5055", str(caught.exception))
        finally:
            settings.DEFAULT_PORT = original
            settings.RESERVED_PORTS = original_reserved


class EnumerationPlantControlTests(unittest.TestCase):
    """Task 1.4's control: the port enumeration must see a plant on its own port.

    Without this, ``assert_port_free`` could report *free* for a port something
    is listening on — the assertion mechanism itself broken — and every
    containment result in this line would still read as a pass.  The control
    makes the enumeration demonstrably sensitive before it is trusted.
    """

    def test_the_enumeration_sees_a_plant_on_v1s_own_port(self) -> None:
        # (1) the enumeration reports free with nothing planted;
        self.assertTrue(harness.port_is_free(settings.HOST, settings.DEFAULT_PORT))
        # (2) plant a real listener on that exact port;
        with harness.PlantedListener(settings.HOST, settings.DEFAULT_PORT):
            # (3) the same enumeration must report NOT free;
            self.assertFalse(
                harness.port_is_free(settings.HOST, settings.DEFAULT_PORT),
                "the port enumeration did not see a listener on v1's own port, so "
                "a containment check using it could not fail",
            )
            self.assertRaises(
                harness.ContainmentError, harness.assert_port_free, settings.HOST, settings.DEFAULT_PORT
            )
        # (4) and free again once the plant is gone, so the check is repeatable.
        self.assertTrue(harness.port_is_free(settings.HOST, settings.DEFAULT_PORT))

    def test_the_control_is_re_runnable(self) -> None:
        """Two consecutive plant/unplant cycles behave identically.

        Task 3.3 asks for re-running rather than trusting a single pass, and a
        control that only worked once would be exactly the kind of evidence
        that becomes worthless silently.
        """
        for _ in range(2):
            with harness.PlantedListener(settings.HOST, settings.DEFAULT_PORT):
                self.assertFalse(harness.port_is_free(settings.HOST, settings.DEFAULT_PORT))
            self.assertTrue(harness.port_is_free(settings.HOST, settings.DEFAULT_PORT))


class ProtocolConstantTests(unittest.TestCase):
    def test_the_protocol_name_is_pinned(self) -> None:
        self.assertEqual("server-v1", settings.PROTOCOL)

    def test_the_exit_codes_are_distinct(self) -> None:
        codes = [
            settings.EXIT_OK,
            settings.EXIT_ENVIRONMENT,
            settings.EXIT_PORT_BUSY,
            settings.EXIT_SERVER,
        ]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
