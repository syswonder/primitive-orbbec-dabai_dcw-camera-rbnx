#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Dependency-free helpers for constructing Orbbec Dabai DCW ROS launch arguments.

Split out of main.py so the multi-camera selector logic (serial_number /
usb_port) can be unit-tested without a live ROS 2 stack, and so the
argument-building rules stay in one place regardless of which lifecycle
callback calls _spawn_orbbec.

Scope note — DCW vs Gemini 330:
    The sister package `primitive-orbbec-camera` (Gemini 330 series) also
    exposes a `device_preset` selector. DCW's dabai_dcw.launch.py does NOT
    declare a `device_preset` launch arg (see
    src/OrbbecSDK_ROS2/orbbec_camera/launch/dabai_dcw.launch.py: the only
    device-picking args are `serial_number` / `usb_port` / `device_num` /
    `vendor_id` / `product_id`; there is no preset system on Dabai firmware).
    Forwarding `device_preset:=...` to `ros2 launch` on DCW would fail with
    "Included launch description has no argument named 'device_preset'".
    So this module only exports `device_selector_args`, and main.py refuses
    (with a one-shot warning) to silently accept `device_preset` when it is
    set in the manifest — this makes DCW/Gemini config drift loud instead
    of the field mysteriously not taking effect.
"""

from __future__ import annotations


# Fields the DCW driver supports for pinning to a specific physical camera
# when multiple Orbbec devices are plugged into the same host. `product_id`
# and `vendor_id` are model-level filters (0x2bc5 = Orbbec USB VID) and are
# intentionally NOT exposed here — they are not per-instance selectors and
# would only matter if someone mixed vendors on the same USB bus.
_SUPPORTED_SELECTOR_KEYS: tuple[str, ...] = ("serial_number", "usb_port")

# Fields the Gemini 330 driver supports but DCW does NOT. Kept as data so
# the "you set a Gemini-only knob on DCW" warning in main.py can be updated
# from a single place if upstream ever grows more of these.
UNSUPPORTED_ON_DCW: tuple[str, ...] = ("device_preset",)


def device_selector_args(cfg: dict) -> list[str]:
    """Return explicit Orbbec device selectors from a Robonix config.

    The upstream launch file accepts both values as strings and treats an
    empty value as "any device" (its own default), so we simply omit any
    key that is unset / blank / whitespace-only. That preserves the
    single-camera auto-discovery behaviour when the user hasn't opted in.

    Iteration order is fixed (serial_number before usb_port) so callers
    can rely on a stable argv layout — makes launch logs diff-able across
    deploys and matches the ordering used by primitive-orbbec-camera on
    the Gemini side.
    """
    args: list[str] = []
    for key in _SUPPORTED_SELECTOR_KEYS:
        value = cfg.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value:
            args.append(f"{key}:={value}")
    return args
