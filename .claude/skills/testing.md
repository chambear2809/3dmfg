# /test - Run Tests & Coverage Analysis

## When to Use
Run this skill after making changes to backend code, or to check test coverage on specific modules.

## What It Does
1. Runs the test suite against changed or specified modules
2. Reports coverage for the files that matter
3. Flags untested code paths in critical business logic

## Execution Steps

### Step 1: Identify What Changed
```bash
cd c:\repos\filaops\backend
git diff --name-only HEAD -- app/
```
If no changes, ask the user which module to analyze.

### Step 2: Run Tests with Coverage on Changed Modules
For each changed module, run targeted coverage:
```bash
cd c:\repos\filaops\backend
python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing -x
```

For a specific module (e.g., inventory_service):
```bash
python -m pytest tests/ -v --tb=short --cov=app/services/inventory_service --cov-report=term-missing
```

### Step 3: Analyze Results
Report:
- **Pass/Fail**: How many tests passed vs failed
- **Coverage**: Line coverage % for changed files
- **Missing lines**: Which lines lack coverage (from `term-missing`)
- **Risk assessment**: Flag any untested paths in:
  - Cost calculations ($/KG conversions)
  - Inventory movements (allocations, reservations)
  - Financial transactions (GL entries, journal balancing)
  - State transitions (order statuses, operation statuses)

### Step 4: Recommendations
If coverage is below 60% on a changed file:
- Identify the top 3 untested functions
- Suggest specific test cases that would cover them
- Reference existing test patterns from `tests/services/test_transaction_service.py`

## Test Categories
Use pytest markers to run specific categories:
```bash
# Unit tests only (fast)
python -m pytest tests/ -v -m unit

# Integration tests (requires DB)
python -m pytest tests/ -v -m integration

# All tests
python -m pytest tests/ -v
```

## Database Safety
Tests run against `filaops_test` database. NEVER run tests pointing at `filaops_prod`.
Verify with: `echo $DB_NAME` or check `backend/.env`.
