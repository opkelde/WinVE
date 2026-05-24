# Shadowing the official webrtcvad hook because it fails to find package metadata on Windows when installed via webrtcvad-wheels.
# This empty hook prevents PyInstaller from crashing.
