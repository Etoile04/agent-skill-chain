# Phase 1.2: Real Task Data Collection

## Goal
Run 3 real complex tasks through the full plan→exec→writeback→UCB loop to accumulate empirical data.

## Task Selection Criteria
- ≥ 3 steps each
- Different domains (coding, integration, data)
- Has relevant skill cards or error patterns in the system
- Verifiable completion criteria

## Tasks

### Task 1: Multi-format Document Converter
- Domain: coding / tooling
- Complexity: medium (4-5 steps)
- Create a script that converts markdown docs to multiple formats (HTML, PDF, plain text)
- Tests: exec tools, file operations, dependency management

### Task 2: Feishu API Integration Test Suite
- Domain: integration / API
- Complexity: medium-high (5-6 steps)
- Build a test harness for Feishu API endpoints with proper auth
- Tests: API calls, error handling, rate limiting awareness

### Task 3: Skill Card Validator Pipeline
- Domain: data / validation
- Complexity: medium (3-4 steps)
- Build a validator that checks all skill-cards against schema
- Tests: schema validation, error reporting, batch processing

## Process
Each task follows:
1. Planning Agent → StepPlan JSON
2. Execution Agent (per step) → StepResult JSON
3. Writeback Pipeline → update learnings + skill cards
4. UCB Update → update usage stats
5. Quality Eval → score the planning quality
