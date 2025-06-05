# scripts/refactor/restructure_project.ps1

Write-Host "🔧 Restructuring Dream.OS Project" -ForegroundColor Cyan

# Error handling
$ErrorActionPreference = "Stop"

# Step 1: Tag & Cut — remove legacy copies
Write-Host "📦 Archiving and removing legacy script copies..." -ForegroundColor Yellow
try {
    git tag archive-legacy
} catch {
    Write-Host "⚠️ Tag already exists or git not available." -ForegroundColor Yellow
}
if (Test-Path "archive/archived_scripts") {
    Remove-Item -Recurse -Force "archive/archived_scripts"
}
if (Test-Path "scripts/maintenance") {
    Remove-Item -Recurse -Force "scripts/maintenance"
}

# Step 2: Flatten calibration/validation nesting
Write-Host "📁 Flattening calibration and validation directories..." -ForegroundColor Yellow
$calibrationPath = "src/dreamos/tools/calibration/calibration"
$validationPath = "src/dreamos/tools/validation/validation"

if (Test-Path $calibrationPath) {
    Get-ChildItem -Path $calibrationPath | Move-Item -Destination "src/dreamos/tools/calibration/"
    Remove-Item -Recurse -Force $calibrationPath
} else {
    Write-Host "No nested calibration files found." -ForegroundColor Gray
}

if (Test-Path $validationPath) {
    Get-ChildItem -Path $validationPath | Move-Item -Destination "src/dreamos/tools/validation/"
    Remove-Item -Recurse -Force $validationPath
} else {
    Write-Host "No nested validation files found." -ForegroundColor Gray
}

# Step 3: Merge runtime scraper into source tree
Write-Host "🔗 Merging runtime scraper modules..." -ForegroundColor Yellow
$scraperSource = "runtime/modules/chatgpt_scraper"
$scraperDest = "src/dreamos/modules/scraper"

if (Test-Path $scraperSource) {
    New-Item -ItemType Directory -Force -Path "src/dreamos/modules"
    Move-Item -Path $scraperSource -Destination $scraperDest
} else {
    Write-Host "No scraper module found in runtime." -ForegroundColor Gray
}

# Step 4: Vendor external grammar bundles
Write-Host "📦 Vendoring tree-sitter grammars..." -ForegroundColor Yellow
$grammarsPath = "runtime/tree-sitter-grammars"
if (Test-Path $grammarsPath) {
    New-Item -ItemType Directory -Force -Path "vendor"
    Move-Item -Path $grammarsPath -Destination "vendor/"
} else {
    Write-Host "No tree-sitter-grammars folder found." -ForegroundColor Gray
}

# Step 5: Consolidate CLI tools
Write-Host "🛠️ Unifying CLI entrypoints..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "src/dreamos/cli"
Get-ChildItem -Path "." -Filter "*.py" -File | Where-Object { $_.Name -ne "setup.py" } | ForEach-Object {
    try {
        Move-Item -Path $_.FullName -Destination "src/dreamos/cli/" -Force -ErrorAction Stop
    } catch {
        Write-Host "⚠️ Could not move $($_.Name): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
if (-not (Test-Path "src/dreamos/cli/__main__.py")) {
    New-Item -ItemType File -Force -Path "src/dreamos/cli/__main__.py"
}

# Step 6: CI gate — detect new duplicates
Write-Host "🔍 Running duplicate hash scan..." -ForegroundColor Yellow
try {
    python src/dreamos/tools/maintenance/find_duplicate_tasks.py
} catch {
    Write-Host "⚠️ Duplicate task scanner not found or failed." -ForegroundColor Yellow
}

Write-Host "✅ Restructure complete." -ForegroundColor Green
