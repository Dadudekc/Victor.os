# PowerShell script to run the duplicate directory merger

# Ensure we're in the project root
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not available in the PATH"
    exit 1
}

# Function to confirm merge execution
function Confirm-MergePlan {
    $confirmation = Read-Host "Would you like to execute the merge plan? (y/N)"
    return $confirmation -eq "y"
}

# First run without execution to generate merge plan
Write-Host "Analyzing directories for duplicates..."
python scripts/merge_duplicate_dirs.py

# Check if merge_plan.json was created
if (Test-Path "merge_plan.json") {
    # Display the merge plan
    Write-Host "`nMerge Plan:"
    Get-Content "merge_plan.json" | ConvertFrom-Json | ForEach-Object {
        $_.merge_groups | ForEach-Object {
            Write-Host "`nPrimary Directory: $($_.primary_dir)"
            Write-Host "Duplicates:"
            $_.duplicates | ForEach-Object {
                Write-Host "  - $($_.path) (similarity: $($_.similarity))"
            }
        }
    }
    
    # Ask for confirmation to execute
    if (Confirm-MergePlan) {
        Write-Host "`nExecuting merge plan..."
        python scripts/merge_duplicate_dirs.py --execute
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Merge completed successfully!"
        } else {
            Write-Error "Merge failed with exit code $LASTEXITCODE"
        }
    } else {
        Write-Host "Merge cancelled."
    }
} else {
    Write-Host "No duplicates found or error generating merge plan."
} 