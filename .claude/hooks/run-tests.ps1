# Auto-test hook: runs relevant tests when backend Python files change
# Called by Claude Code PostToolUse hook after Edit/Write operations

param([string]$FilePath)

# Only trigger for backend Python files (not test files themselves)
if ($FilePath -notmatch 'backend[\\/]app[\\/].*\.py$') {
    exit 0
}

# Skip if it's a test file being edited
if ($FilePath -match 'backend[\\/]tests[\\/]') {
    exit 0
}

# Extract the module path relative to backend/app/
$relativePath = $FilePath -replace '.*backend[\\/]app[\\/]', ''
$modulePath = $relativePath -replace '\.py$', '' -replace '[\\/]', '.'

# Map source files to test files
$testDir = "c:\repos\filaops\backend\tests"
$moduleName = [System.IO.Path]::GetFileNameWithoutExtension($FilePath)

# Look for matching test files
$testFiles = @()

# Check services tests
if ($FilePath -match 'services[\\/]') {
    $testFiles += Get-ChildItem -Path "$testDir\services" -Filter "test_*$moduleName*" -ErrorAction SilentlyContinue
    $testFiles += Get-ChildItem -Path "$testDir\unit" -Filter "test_*$moduleName*" -ErrorAction SilentlyContinue
}

# Check endpoint tests
if ($FilePath -match 'endpoints[\\/]') {
    $testFiles += Get-ChildItem -Path "$testDir\api" -Filter "test_*$moduleName*" -Recurse -ErrorAction SilentlyContinue
}

# Check model tests
if ($FilePath -match 'models[\\/]') {
    # Models are tested indirectly via integration tests - run a quick smoke test
    $testFiles += Get-ChildItem -Path "$testDir\integration" -Filter "test_full_business_cycle*" -ErrorAction SilentlyContinue
}

if ($testFiles.Count -eq 0) {
    Write-Host "AUTO-TEST: No matching tests found for $moduleName"
    exit 0
}

# Run matching tests
Set-Location "c:\repos\filaops\backend"
$testPaths = ($testFiles | ForEach-Object { $_.FullName }) -join " "

Write-Host "AUTO-TEST: Running tests for $moduleName..."
& .\venv\Scripts\python.exe -m pytest $testFiles.FullName -v --tb=short -x --no-header -q 2>&1

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "AUTO-TEST: TESTS FAILED for $moduleName" -ForegroundColor Red
} else {
    Write-Host "AUTO-TEST: All tests passed for $moduleName" -ForegroundColor Green
}

exit $exitCode
