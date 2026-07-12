# primitive-orbbec-dabai_dcw-camera-rbnx

Robonix package wrapping the **Orbbec Dabai DCW** RGBD camera. Owns the `primitive/camera/*` namespace. Exposes the camera's RGB + depth + camera_info streams under generic contracts so consumers (grasp / detection / scene / vision skills) resolve topic names through atlas — no hardcoded `/camera/color/image_raw` paths on the consumer side.

Catalog name: `robonix.primitive.orbbec.dabai_dcw.camera`.

## Capability surface

| Contract                                | Mode       | Transport | Source / handler                                            |
| --------------------------------------- | ---------- | --------- | ----------------------------------------------------------- |
| `robonix/primitive/camera/driver`       | rpc        | gRPC      | `Driver(CMD_INIT, config_json)` — lifecycle gate            |
| `robonix/primitive/camera/rgb`          | topic_out  | ROS 2     | `/<camera_name>/color/image_raw` (sensor_msgs/Image)        |
| `robonix/primitive/camera/depth`        | topic_out  | ROS 2     | `/<camera_name>/depth/image_raw` (sensor_msgs/Image; HW-aligned to color when `depth_registration=true`) |
| `robonix/primitive/camera/camera_info`  | topic_out  | ROS 2     | `/<camera_name>/color/camera_info` (sensor_msgs/CameraInfo) |

`camera_info` is **package-locally defined** (see `capabilities/primitive/camera/camera_info.v1.toml`) because the robonix global tree does not ship that contract yet; codegen + atlas merge package-level capabilities automatically. It is required by the grasp pipeline: `service-grasp-pose-rbnx` back-projects 2D bbox centers into 3D using `fx / fy / cx / cy` + distortion.

Aspirational contracts (`extrinsics`, `snapshot`, `depth_snapshot`) listed in the global `capabilities/primitive/camera/` are intentionally **not** declared here — per the packaging rules, manifest entries must correspond to real `declare_ros2_*/@cap.mcp(...)` handlers.

## Boot ordering

Boot this **before** any consumer of `primitive/camera/*`. In the vertical-grasp pipeline `service-object-detect-rbnx` and `service-grasp-pose-rbnx` both query atlas at their own `Driver(CMD_INIT)` time and fail if `rgb / depth / camera_info` are not declared yet — rbnx-cli has no defer/retry.

## Driver-init lifecycle

`start.sh` brings up the atlas bridge — no ROS spawn. The bridge opens a gRPC server, registers the provider, declares only `primitive/camera/driver` (auto-emitted by the framework when codegen produces a `Driver` Servicer), then blocks on `Driver(CMD_INIT, config_json)`.

When `rbnx boot` invokes Init it passes the manifest's `config:` block as JSON. The handler:

1. parses cfg (camera name, resolution / fps, `depth_registration`, USB pin, sentinel timeout);
2. spawns `ros2 launch orbbec_camera dabai_dcw.launch.py …`;
3. waits for the first `sensor_msgs/Image` on the configured RGB topic (sentinel);
4. declares `primitive/camera/{rgb, depth, camera_info}` on atlas, and returns ok.

Atlas only ever advertises endpoints we've confirmed are publishing. `CMD_DEACTIVATE` / `CMD_SHUTDOWN` kill the orbbec subprocess. Idempotent.

If the camera is not connected or the driver stalls, the sentinel times out and Init returns `state="error"`.

## Layout

```
primitive-orbbec-dabai_dcw-camera-rbnx/
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

To drive Init manually (without `rbnx boot`): from any robonix gRPC client, call the camera's `Driver` service with `command=0` (CMD_INIT) and `config_json='{}'`. The handler returns `ok=true` after the first RGB frame is observed, then declares the three topic_out streams.

## Verification

```bash
rbnx caps | grep camera
# Expected: orbbec_camera provider with
#   robonix/primitive/camera/{driver, rgb, depth, camera_info}

ros2 topic hz /camera/color/image_raw           # ~10 Hz with default fps
ros2 topic hz /camera/depth/image_raw           # ~10 Hz
ros2 topic echo /camera/color/camera_info --once  # K, D, R, P intrinsics
```

## Vendor / upstream

`src/OrbbecSDK_ROS2/` is a verbatim copy of [orbbec/OrbbecSDK_ROS2](https://github.com/orbbec/OrbbecSDK_ROS2). The Dabai DCW firmware-blob SDK ships under `orbbec_camera/SDK/{include,lib}/`. If anything diverges from upstream, drop a `*.patch` alongside `src/` documenting the diff.

## License

This package: Apache-2.0. Vendored OrbbecSDK_ROS2: see its LICENSE file.
