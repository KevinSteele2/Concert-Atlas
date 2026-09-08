@echo off
cd /d "%~dp0"
start "" pythonw -m viz.build_map
