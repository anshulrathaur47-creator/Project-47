# Installs all Video Studio skills into %USERPROFILE%\.claude\skills (Claude Code personal skills)
$Dest = if ($args[0]) { $args[0] } else { Join-Path $env:USERPROFILE ".claude\skills" }
$Src = Join-Path $PSScriptRoot "plugins\video-studio\skills"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Get-ChildItem $Src -Directory | ForEach-Object {
  $t = Join-Path $Dest $_.Name
  if (Test-Path $t) { Remove-Item $t -Recurse -Force }
  Copy-Item $_.FullName $t -Recurse
  Write-Host "installed $($_.Name)"
}
Write-Host ""
Write-Host "Now install the tools once:"
Write-Host "  pip install faster-whisper playwright numpy pillow opencv-contrib-python mediapipe fastapi uvicorn fonttools"
Write-Host "  python -m playwright install chromium"
Write-Host "  winget install ffmpeg"
Write-Host "Check: python `"$Dest\video-studio-core\scripts\check_env.py`""
