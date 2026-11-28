# Security policy

## Supported versions

Only the latest release on `main` gets fixes.

## Reporting a vulnerability

Please report privately: open the repository's **Security** tab and choose **Report a vulnerability** (GitHub private security advisory). Do not open a public issue for security problems.

Include what you found, how to reproduce it, and the impact. You can expect an acknowledgement within a few days.

## What is in scope

- The local review app (`video-studio-core/app/server.py`): it binds to 127.0.0.1 only, requires a per-session token on every request, confines file access to the `--root` folder and runs subprocesses without a shell. Bypasses of any of these are in scope.
- Path handling, subprocess calls and downloads in the engine scripts.
- Anything that sends user footage or data off the machine. The pack is designed to run fully locally; only model and font downloads go to the network.

## Your footage

Video Studio processes media on your own computer. It does not upload footage anywhere. Never attach private footage to public issues.
