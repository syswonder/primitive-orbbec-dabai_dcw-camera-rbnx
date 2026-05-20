# OrbbecSDK_rbnx

Robonix package wrapping the **Orbbec Dabai DCW** RGBD camera. Owns
the `primitive/camera/*` namespace for the `piper_grasp` deploy.
Exposes the camera's RGB + depth + camera_info streams under generic
contracts so consumers (yolo_world, yolo_grasp, scene, any vision
skill) resolve topic names through atlas — no hardcoded
`/camera/color/image_raw` paths on the consumer side.

## Boot ordering

This is the **camera primitive** for the piper_grasp deploy. Boot it
**before** any consumer of `primitive/camera/*` — Stage 4's
`yolo_world_rbnx` and `yolo_grasp_rbnx` will both query atlas at
their own `Driver(CMD_INIT)` time and fail if rgb / depth /
camera_info aren't declared yet (rbnx-cli has no defer/retry).

## Capability surface

| Contract                                  | Mode      | Transport | Source / handler                                 |
| ----------------------------------------- | --------- | --------- | ------------------------------------------------ |
| `robonix/primitive/camera/driver`         | rpc       | gRPC      | `Driver(CMD_INIT, config_json)` — lifecycle gate |
| `robonix/primitive/camera/rgb`            | topic_out | ROS 2     | `/<cam>/color/image_raw` (sensor_msgs/Image)     |
| `robonix/primitive/camera/depth`          | topic_out | ROS 2     | `/<cam>/depth/image_raw` (HW-aligned to color when `depth_registration=true`) |
| `robonix/primitive/camera/camera_info`    | topic_out | ROS 2     | `/<cam>/color/camera_info` (sensor_msgs/CameraInfo) |

`camera_info` is **package-locally defined** (see
`capabilities/primitive/camera/camera_info.v1.toml`) because the
robonix global tree doesn't ship that contract; codegen + atlas merge
package-level capabilities automatically. It exists because Stage 4B's
`yolo_grasp_rbnx` does depth back-projection and needs fx/fy/cx/cy +
distortion.

Aspirational contracts (`extrinsics`, `snapshot`, `depth_snapshot`)
listed in the global `capabilities/primitive/camera/` are
intentionally **not** declared here — per the new packaging rules,
manifest entries must correspond to real
`declare_ros2_*/@cap.mcp(...)` handlers.

## Driver-init lifecycle

`start.sh` brings up the atlas bridge (Python). The bridge registers
the provider, declares only `primitive/camera/driver` (auto-emitted
by the framework when codegen produces a `Driver` Servicer), then
blocks on `Driver(CMD_INIT, config_json)`.

When `rbnx boot` invokes Init it passes the manifest's `config:`
block as JSON. The handler parses cfg (camera name, resolution / FPS,
`depth_registration`, USB pin), spawns
`ros2 launch orbbec_camera dabai_dcw.launch.py …`, waits for the first
frame on the configured RGB topic, declares
`primitive/camera/{rgb, depth, camera_info}` on atlas, and returns
ok. Atlas only ever advertises endpoints we've confirmed are
publishing.

## Layout

```
OrbbecSDK_rbnx/
├── package_manifest.yaml
├── capabilities/
│   └── primitive/camera/camera_info.v1.toml   # package-local contract
├── orbbec_camera/
│   ├── __init__.py
│   └── main.py                                # lifecycle + sentinel
├── scripts/
│   ├── build.sh                               # colcon build src + rbnx codegen
│   └── start.sh                               # source ROS, exec main
└── src/
    └── OrbbecSDK_ROS2/                        # VENDORED orbbec/OrbbecSDK_ROS2
        ├── orbbec_camera/                     # ROS 2 driver pkg
        ├── orbbec_camera_msgs/
        └── orbbec_description/
```

## Config (passed via `Driver(CMD_INIT, config_json)`)

```yaml
camera_name:        camera        # ROS namespace; topic prefix
depth_registration: true          # HW-align depth to color frame
enable_d2c_viewer:  false         # debug RViz; off in deploy
color_width:        640
color_height:       480
color_fps:          10            # dabai_dcw firmware default
depth_width:        640
depth_height:       400
depth_fps:          10
serial_number:      ""            # pin to specific device when multiple connected
usb_port:           ""
sentinel_timeout_s: 30.0          # max wait for first RGB frame in on_activate
# Topic-name overrides (rarely needed):
# rgb_topic:          /<camera_name>/color/image_raw
# depth_topic:        /<camera_name>/depth/image_raw
# camera_info_topic:  /<camera_name>/color/camera_info
```

## Build / run standalone

```bash
bash scripts/build.sh                           # colcon build vendored src + rbnx codegen
ROBONIX_ATLAS=127.0.0.1:50051 \
    bash scripts/start.sh                       # registers, awaits Init
```

To drive Init manually (without `rbnx boot`): from any robonix gRPC
client, call the camera's `Driver` service with `command=0` (CMD_INIT)
and `config_json='{}'`. The handler returns `ok=true` after the first
RGB frame is observed, then declares the three topic_out streams.

## Verification (Stage 1 deliverable)

After `rbnx boot` from `piper_grasp_deploy/`:

```bash
rbnx caps | grep camera
# Expected: orbbec_camera provider with
#   robonix/primitive/camera/{driver, rgb, depth, camera_info}

ros2 topic hz /camera/color/image_raw          # ~10 Hz with default fps
ros2 topic hz /camera/depth/image_raw          # ~10 Hz
ros2 topic echo /camera/color/camera_info --once  # K, D, R, P intrinsics
```

## Vendor / upstream

`src/OrbbecSDK_ROS2/` is a verbatim copy of
[orbbec/OrbbecSDK_ROS2](https://github.com/orbbec/OrbbecSDK_ROS2) at
the version that worked on the Jetson with the original
`/Users/howenliu/lab/grasp/driver/OrbbecSDK_ROS2` layout. The Dabai
DCW firmware-blob SDK ships under
`orbbec_camera/SDK/{include,lib}/`. If anything diverges from
upstream, drop a `*.patch` alongside `src/` documenting the diff.

## License

This package: Apache-2.0 (matches OrbbecSDK_ROS2 upstream).
