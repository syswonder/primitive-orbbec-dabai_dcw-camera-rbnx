#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
PKG="${RBNX_PACKAGE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PKG"

# ─── debug: source state at entry (rbnx-cli prepends an outer
# `source <pkg>/rbnx-build/ws/install/setup.bash; ...; bash this`
# wrapper, so AMENT_PREFIX_PATH should already include our overlay) ─
echo "[orbbec_camera/start] PKG=$PKG" >&2
echo "[orbbec_camera/start] entry AMENT_PREFIX_PATH heads:" >&2
printf '  %s\n' ${AMENT_PREFIX_PATH//:/ } 2>&1 | head -5 >&2
echo "[orbbec_camera/start] entry: ros2 pkg prefix orbbec_camera => $(ros2 pkg prefix orbbec_camera 2>&1 || echo MISSING)" >&2
echo "[orbbec_camera/start] setup.bash exists? $(test -f "$PKG/rbnx-build/ws/install/setup.bash" && echo YES || echo NO)" >&2

ROS_DISTRO="${ROS_DISTRO:-humble}"
# shellcheck disable=SC1091
set +u; source "/opt/ros/${ROS_DISTRO}/setup.bash"; set -u
if [[ -f "$PKG/rbnx-build/ws/install/setup.bash" ]]; then
    # shellcheck disable=SC1091
    set +u; source "$PKG/rbnx-build/ws/install/setup.bash"; set -u
fi

echo "[orbbec_camera/start] post-source: ros2 pkg prefix orbbec_camera => $(ros2 pkg prefix orbbec_camera 2>&1 || echo MISSING)" >&2

if ROBONIX_API="$(rbnx path robonix-api 2>/dev/null)"; then
    export PYTHONPATH="$ROBONIX_API:$PKG:${PYTHONPATH:-}"
fi
# robonix_api auto-bootstraps codegen paths from the caller frame, but
# be explicit so a bare `python3 -m orbbec_camera.main` (without
# robonix_api's stack-walk fallback) still finds atlas_pb2.
export PYTHONPATH="$PKG/rbnx-build/codegen/proto_gen:${PYTHONPATH:-}"

exec python3 -m orbbec_camera.main
