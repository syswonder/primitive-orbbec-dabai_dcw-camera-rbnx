# SPDX-License-Identifier: Apache-2.0
"""Unit tests for orbbec_camera.launch_config.

These tests deliberately import the module directly rather than going
through orbbec_camera/__init__.py so the launch-arg logic can be
exercised without pulling in robonix_api, ROS 2, or any subprocess
side effects. That means `python3 -m unittest discover tests` should
pass on a plain venv with no ROS 2 sourced.
"""
import unittest

from orbbec_camera.launch_config import (
    UNSUPPORTED_ON_DCW,
    device_selector_args,
)


class DeviceSelectorArgsTest(unittest.TestCase):
    def test_omits_selectors_for_single_camera_auto_discovery(self):
        # Empty cfg / blank strings must not emit any launch arg — an
        # empty `serial_number:=` on the argv would still get forwarded
        # to ros2 launch and read as "must match a device with empty
        # serial", which never matches. Auto-discovery is a strict
        # omission, not an empty-string opt-out.
        self.assertEqual(device_selector_args({}), [])
        self.assertEqual(
            device_selector_args({"serial_number": "", "usb_port": "  "}),
            [],
        )

    def test_forwards_serial_number(self):
        self.assertEqual(
            device_selector_args({"serial_number": "CP123456"}),
            ["serial_number:=CP123456"],
        )

    def test_forwards_usb_port(self):
        # usb_port values from `lsusb` are shaped like "2-3" (bus-port);
        # keep them verbatim, dabai_dcw.launch.py parses that format.
        self.assertEqual(
            device_selector_args({"usb_port": "2-3"}),
            ["usb_port:=2-3"],
        )

    def test_preserves_both_selectors_in_upstream_argument_order(self):
        # Ordering must be stable (serial_number before usb_port) so
        # spawned-orbbec log lines diff cleanly across deploys, and so
        # multi-camera regressions can be triaged from argv alone.
        # Also verifies numeric values get str()'d (rare, but ROS launch
        # only accepts strings).
        self.assertEqual(
            device_selector_args({"usb_port": "2-3", "serial_number": 1234}),
            ["serial_number:=1234", "usb_port:=2-3"],
        )

    def test_ignores_unknown_keys(self):
        # Only the two DCW-supported selectors are emitted; other keys
        # in the cfg (product_id, camera_name, etc.) are for main.py to
        # handle, not this helper.
        self.assertEqual(
            device_selector_args({
                "camera_name": "front_camera",
                "product_id": "0x0666",
                "serial_number": "AB12",
            }),
            ["serial_number:=AB12"],
        )


class UnsupportedOnDcwTest(unittest.TestCase):
    def test_device_preset_is_listed_as_unsupported(self):
        # Guardrail: if someone re-adds device_preset support later they
        # must remove it from this tuple, which will force them to look
        # at main.py's _warn_unsupported_keys() at the same time. That's
        # exactly the review coupling we want — the "warn" path and the
        # "actually forward" path must not diverge silently.
        self.assertIn("device_preset", UNSUPPORTED_ON_DCW)


if __name__ == "__main__":
    unittest.main()
