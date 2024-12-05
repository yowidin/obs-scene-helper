# OBS Scene Helper

A dedicated tool to ensure that an OBS recording session is updated to match the current display configuration.
It also keeps track of the screen lock, pausing recording when the screen is locked and resuming when the screen
is unlocked.

# Building

Build the standalone app with

```shell
pyinstaller osh_spec.py
```

Note: on Windows you will need both the `osh.exe` and the `osh-display-list.exe` binaries to be in the same directory.