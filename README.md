# GPU Monitor (Windows EXE + Remote Linux)

This app runs a local web UI on Windows and pulls GPU status from a remote Linux server over SSH. The UI refreshes every second and presents a mac-style dashboard with an `nvidia-smi`-like table.

## Quick start (dev)

1. Install Python 3.10+ on Windows.
2. Install dependencies:

```
pip install -r requirements.txt
```

3. Create `config.json` in the project root (or next to the EXE when packaged). Use `config.example.json` as a template.
4. Run the server:

```
python -m app.main
```

The app opens your browser at `http://127.0.0.1:8787` by default.

## Config

Create `config.json` next to the EXE. Required values:

- `server_host`
- `server_user`
- `server_password` or `server_key_path`

Optional values:

- `server_port` (default: 22)
- `poll_interval` in seconds (default: 1.0, minimum: 0.5)
- `local_host` (default: 127.0.0.1)
- `local_port` (default: 8787)
- `ssh_connect_timeout` (default: 5)
- `ssh_command_timeout` (default: 5)
- `allow_unknown_hosts` (default: true)

You can also provide config via env vars:

- `GPU_SERVER_HOST`
- `GPU_SERVER_USER`
- `GPU_SERVER_PASSWORD`
- `GPU_SERVER_KEY_PATH`
- `GPU_SERVER_PORT`
- `GPU_POLL_INTERVAL`
- `GPU_LOCAL_HOST`
- `GPU_LOCAL_PORT`
- `GPU_SSH_CONNECT_TIMEOUT`
- `GPU_SSH_COMMAND_TIMEOUT`
- `GPU_SSH_ALLOW_UNKNOWN_HOSTS`
- `GPU_MONITOR_CONFIG` (path to config.json)

## Build EXE (manual)

```
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --name gpu-monitor --add-data "app/static;static" run.py
```

Copy `config.example.json` to `dist/config.json` and edit it before running the EXE.

## Security note

If possible, use SSH keys instead of passwords. `allow_unknown_hosts=true` makes setup easy but is less secure. Set it to `false` if you want strict host key checks.
