# Install Log

- `brew install ffmpeg`
- `./venv/bin/python -m pip install playwright`
- `./venv/bin/python -m playwright install chromium`

No additional install for subtitle fix; patched FFmpeg caption path handling in production script.

No install: browser-native caption overlay used because installed FFmpeg lacks subtitle filter.
