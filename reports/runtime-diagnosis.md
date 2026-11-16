# Chẩn đoán runtime giai đoạn 3

Ngày 12/11/2026; không restart Docker Desktop/WSL, không đổi socket hệ thống, group membership hoặc Docker config. Bằng chứng giai đoạn 2 được bảo toàn trong [stage3-baseline-state.json](stage3-baseline-state.json).

## Quan sát

- [Windows](stage3-diagnosis-windows.json): CLI qua context desktop-linux trả version28.1.1 trong khoảng 0,05 giây.
- [Python WSL ban đầu](stage3-diagnosis-wsl.json): `/usr/bin/docker` là ELF, resolve tới `/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker`; context default. Version probe timeout5 giây, stdout null; GET/version tới `/var/run/docker.sock` cũng timeout. Không có DOCKER_HOST/CONTEXT/API_VERSION override.
- [Socket thường](stage3-socket-probes.json): `/run/docker.sock` timeout; socket Desktop được bảo vệ không cho tài khoản thường tiếp cận trực tiếp.
- [Socket root chỉ đọc](stage3-socket-probes-root.json): proxy distro Ubuntu-22.04 và host Docker proxy trả HTTP200/version28.1.1 nhanh; socket mặc định vẫn timeout. Socket build trả404, không dùng làm engine endpoint.
- [Probe WSL trực tiếp về sau](stage3-diagnosis-wsl-direct.json): một lần trả nhanh. Tuy nhiên [Python WSL sau đó](stage3-diagnosis-wsl-after.json) và [preflight mặc định sau smoke](stage3-preflight-default-after.json) vẫn chưa đạt. Không diễn giải một lần thành công thành sửa triệt để.

Bằng chứng khoanh vùng đường routing/socket/integration mặc định WSL, không cho thấy toàn bộ Docker engine bị ngừng. Không phải chỉ một lỗi Python stdout: socket HTTP độc lập cũng timeout. Chưa xác định vì sao đường mặc định bị kẹt/gián đoạn hoặc vì sao một probe trực tiếp thành công.

## Khắc phục có phạm vi

`scripts/with_runtime_proxy.py` dùng root chỉ để mở proxy Desktop được bảo vệ, tạo Unix socket tạm mode0600 cho user tamle. Lệnh benchmark chạy dưới tài khoản thường, DOCKER_HOST override chỉ nằm trong môi trường lệnh, DOCKER_CONTEXT được bỏ trong phạm vi đó. Relay bị đóng và thư mục tạm được dọn sau khi lệnh kết thúc; không có listener TCP hoặc service nền thường trú.

[Preflight scoped](stage3-preflight-scoped-proxy.json) đạt khoảng0,25 giây; [ba health check](stage3-health-sequence.json) trong cùng scope đều đạt. CLI thật của Harbor đi qua relay, không chỉ một API probe thay thế. [Bốn smoke](stage3-smoke-summary.json) đều pass. Đây là workaround đã kiểm định trong phạm vi tác vụ, không phải sửa socket mặc định hoặc đảm bảo ổn định dài hạn.

Không tự bật root relay cho model runner. Muốn dùng profile này về sau phải chốt quyền vận hành và lifecycle, luôn giữ verifier không mạng/không credentials. Default WSL preflight chưa đạt vẫn chặn chạy thông thường.

## Giới hạn subprocess

`runtime_process.py` dùng capture qua file, wait có timeout và process group do tác vụ tạo. Tránh chờ EOF vô hạn khi descendant giữ pipe. Trên POSIX chỉ dừng group của lệnh này; không kill mọi docker/python/wsl. Preflight ghi từng bước và elapsed, deadline45 giây, CLI10 giây; deadline process gồm một khoảng cleanup ngắn. Các bước đọc filesystem tại chỗ kiểm deadline giữa bước, không phải hard real-time guarantee cho I/O kernel bị treo.

Executor oracle/nop có job deadline riêng, lưu log và fail hữu hạn; không đổi task timeout hoặc gán infrastructure deadline thành model reward0. Windows helper chỉ quản lý tiến trình trực tiếp; không tuyên bố guarantee Unix process-group áp dụng cho Windows.
