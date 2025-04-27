# PowerShell - Run as Administrator

Write-Host "=== Installing Remote Access Tools ==="

# 1. Install Chocolatey (if not installed)
if (-Not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

# 2. Install RustDesk
choco install rustdesk -y
Write-Host "`n[✔] RustDesk installed. Open it and set up unattended access (password + enable auto-start)."

# 3. Install Tailscale
choco install tailscale -y
Write-Host "`n[✔] Tailscale installed. Login using your preferred Google/Microsoft/GitHub account."
Start-Process "C:\Program Files (x86)\Tailscale IPN\tailscale.exe" "up"

# 4. OPTIONAL: WSL + tmate for terminal access (if WSL installed)
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "`n[~] WSL Detected. Installing tmate..."
    wsl sudo apt update && wsl sudo apt install -y tmate
    Write-Host "`n[✔] You can now run 'wsl tmate' for instant terminal sharing."
}

# 5. Setup RustDesk auto-start (if not already configured)
$rustdeskPath = "$Env:ProgramFiles\RustDesk\rustdesk.exe"
$startupFolder = "$Env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = Join-Path $startupFolder "RustDesk.lnk"

if (-Not (Test-Path $shortcutPath)) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $rustdeskPath
    $shortcut.Save()
    Write-Host "`n[✔] RustDesk auto-start enabled at login."
}

Write-Host "`n=== Setup Complete ==="
Write-Host "RustDesk: Use your device ID + password to connect"
Write-Host "Tailscale: Use https://login.tailscale.com to get private VPN access to this machine" 