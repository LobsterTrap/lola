# Tasks: Interactive CLI Prompts

**Input**: Design documents from `/specs/001-interactive-prompts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-commands.md, quickstart.md

**Tests**: Tests are included — this feature modifies CLI command signatures and runtime behaviour, requiring regression coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add the InquirerPy dependency and scaffold the new prompts module

- [x] T001 Add `InquirerPy>=0.3.4` to `[project.dependencies]` in pyproject.toml and run `uv sync`
- [x] T002 Create (NEW) src/lola/prompts.py with `is_interactive()`, `select_assistants()`, `select_module()`, and `select_marketplace()` functions per specs/001-interactive-prompts/quickstart.md. Include single-item early-return in `select_assistants()` (auto-select when only one assistant available) and `select_module()` (auto-select when only one module available)
- [x] T003 Create (NEW) tests/test_prompts.py with unit tests: mock `sys.stdin.isatty` for `is_interactive()`; mock `InquirerPy.inquirer.checkbox` for `select_assistants()`; mock `InquirerPy.inquirer.select` for `select_module()` and `select_marketplace()`; test single-item early-return for both `select_assistants()` and `select_module()`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No additional foundational work — prompts.py from Phase 1 IS the foundation. All user stories depend on Phase 1 completion.

**Checkpoint**: `src/lola/prompts.py` exists and passes its unit tests. `uv sync` has resolved InquirerPy.

---

## Phase 3: User Story 1 — Interactive Assistant & Module Selection on Install (Priority: P1) 🎯 MVP

**Goal**: When `lola install` is run without `-a` (and optionally without a module name), present interactive pickers instead of silently using defaults or erroring.

**Independent Test**: Run `lola install` with a registered module and no `-a` flag in a real terminal — verify a checkbox prompt appears for assistant selection. Run `lola install` with no arguments — verify a module picker appears first.

### Implementation for User Story 1

- [x] T004 [US1] Change `module_name` from required positional to optional (`required=False, default=None`) in `install_cmd` Click decorator at `@click.argument("module_name")` (line 638) in src/lola/cli/install.py
- [x] T005 [US1] Add module picker logic at top of `install_cmd` body: if `module_name is None` and `is_interactive()` → call `select_module(registered_names)`; if cancelled (None) → print message and `raise SystemExit(130)`; if not interactive → print error and `raise SystemExit(1)` in src/lola/cli/install.py
- [x] T006 [US1] Replace `assistants_to_install = [assistant] if assistant else list(TARGETS.keys())` (line 769) with interactive branch: if `assistant` given → use it; elif `is_interactive()` → `select_assistants()`; else → all assistants (preserve non-interactive default) in src/lola/cli/install.py
- [x] T007 [US1] Handle empty selection from `select_assistants()` — print "[yellow]No assistants selected. Cancelled.[/yellow]" and `raise SystemExit(130)` in src/lola/cli/install.py
- [x] T008 [US1] Update `install_cmd` docstring and help text to reflect optional module_name and interactive assistant selection in src/lola/cli/install.py
- [x] T009 [US1] Add tests for install without module_name (interactive: mocked picker returns value; non-interactive: expect SystemExit(1); cancelled: expect SystemExit(130)) in tests/test_cli_install.py
- [x] T010 [P] [US1] Add tests for install without `-a` flag (interactive: mocked `select_assistants` returns subset; verify only those assistants installed; explicit `-a` flag: verify `select_assistants` is NOT called) in tests/test_cli_install.py
- [x] T011 [P] [US1] Add test for user cancelling assistant picker (mocked `select_assistants` returns []; verify no installation occurs, exit code 130) in tests/test_cli_install.py

**Checkpoint**: `lola install` works with interactive pickers for both module and assistant selection. Cancellation yields exit 130. Existing explicit-flag usage unchanged. All tests pass.

---

## Phase 4: User Story 2 — Interactive Module Selection on Uninstall (Priority: P2)

**Goal**: When `lola uninstall` is run without a module name, present a single-select picker of installed modules instead of erroring.

**Independent Test**: Install a module, then run `lola uninstall` with no arguments in a real terminal — verify a module picker appears showing the installed module name.

### Implementation for User Story 2

- [x] T012 [US2] Change `module_name` from required positional to optional (`required=False, default=None`) in `uninstall_cmd` Click decorator at `@click.argument("module_name")` (line 806) in src/lola/cli/install.py
- [x] T013 [US2] Add module picker logic at top of `uninstall_cmd` body: if `module_name is None` and `is_interactive()` → gather installed module names from registry → call `select_module()`; if cancelled (None) → `raise SystemExit(130)`; if not interactive → print error and `raise SystemExit(1)` in src/lola/cli/install.py
- [x] T014 [US2] Handle empty registry (no modules installed) — print "[yellow]No modules installed.[/yellow]" and return (exit 0), skipping the picker, in src/lola/cli/install.py
- [x] T015 [US2] Update `uninstall_cmd` docstring and help text to reflect optional module_name in src/lola/cli/install.py
- [x] T016 [US2] Add tests for uninstall without module_name (interactive: mocked picker; non-interactive: SystemExit(1); cancelled: SystemExit(130); no modules: message shown, exit 0) in tests/test_cli_install.py

**Checkpoint**: `lola uninstall` works with interactive module picker. Cancellation yields exit 130. Existing explicit-argument usage unchanged. All tests pass.

---

## Phase 5: User Story 3 — Interactive Marketplace Selection (Priority: P3)

**Goal**: When a module name matches entries in multiple marketplaces, present an interactive select list with descriptions instead of a numbered `click.prompt`.

**Independent Test**: Configure two marketplaces that both contain a module named "test-module", then run `lola install test-module` — verify an interactive select list appears showing both marketplace options with versions and descriptions.

### Implementation for User Story 3

- [x] T017 [US3] Refactor `MarketplaceRegistry.select_marketplace()` in src/lola/market/manager.py: remove `click.prompt` and numbered-list printing; delegate to `prompts.select_marketplace(matches)` for multi-match case; keep early return for single match
- [x] T018 [US3] Handle cancellation (None return from `prompts.select_marketplace`) in `MarketplaceRegistry.select_marketplace()` — return None to caller in src/lola/market/manager.py
- [x] T019 [US3] Handle None return from `registry.select_marketplace()` in install_cmd marketplace resolution flow (line 722) — print cancellation message and `raise SystemExit(130)` in src/lola/cli/install.py
- [x] T020 [US3] Update marketplace selection tests: replace `monkeypatch.setattr("click.prompt", ...)` with mocked `prompts.select_marketplace` in tests/test_market_manager.py (lines 750, 784); verify display includes marketplace name, version, and description
- [x] T021 [P] [US3] Add test for marketplace selection cancellation (mocked `prompts.select_marketplace` returns None; verify no installation) in tests/test_market_manager.py

**Checkpoint**: Marketplace conflict resolution uses an interactive select list. Cancellation is clean. Existing single-marketplace auto-selection unchanged. All tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cleanup

- [x] T022 Run `ruff check src tests` and `ruff format src tests` — fix any issues in src/lola/prompts.py and modified files
- [x] T023 Run `basedpyright src` — fix any type errors in src/lola/prompts.py and modified files
- [x] T024 Run full test suite with `pytest --tb=short -q` — verify all 554+ existing tests still pass alongside new tests (covers FR-008 backward compatibility and SC-004)
- [x] T025 [P] Verify CLAUDE.md at project root includes InquirerPy entry in Active Technologies for 001-interactive-prompts
- [x] T026 [P] Verify specs/001-interactive-prompts/spec.md contains FR-010 (module picker on install without module name)
- [ ] T027 Manual smoke test: run `lola install` and `lola uninstall` interactively in a real terminal to confirm prompts render correctly, keyboard navigation works (FR-005: arrow keys, Space, Enter, Escape/Ctrl+C), and cancellation yields exit 130 (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — checkpoint only
- **US1 Install Pickers (Phase 3)**: Depends on Phase 1 (prompts.py must exist)
- **US2 Uninstall Picker (Phase 4)**: Depends on Phase 1 only — can run in parallel with Phase 3
- **US3 Marketplace Picker (Phase 5)**: Depends on Phase 1 only — can run in parallel with Phases 3 & 4
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on prompts.py only. No dependency on US2 or US3.
- **User Story 2 (P2)**: Depends on prompts.py only. No dependency on US1 or US3. Uses the same `select_module()` function.
- **User Story 3 (P3)**: Depends on prompts.py only. No dependency on US1 or US2. Uses `select_marketplace()`.

### Within Each User Story

- Click decorator change → body logic change → cancellation handling → docstring → tests
- Tests can be written in parallel with implementation if mocking approach is known (it is — see research.md Decision 7)

### Parallel Opportunities

- T003, T002 are sequential (T002 creates the module, T003 tests it)
- T009, T010, T011 are parallelizable (different test functions, no shared state)
- T020, T021 are parallelizable (different test scenarios)
- Phases 3, 4, and 5 can all start after Phase 1 completes — all modify different sections of install.py and different test files
- T022, T023 are sequential (fix linting before type-checking)
- T025, T026 are parallelizable (checking different files)

---

## Parallel Example: User Story 1

```text
# After T006 and T007 (core install logic), launch tests in parallel:
Task T009: "Add tests for install without module_name in tests/test_cli_install.py"
Task T010: "Add tests for install without -a flag in tests/test_cli_install.py"
Task T011: "Add test for user cancelling assistant picker in tests/test_cli_install.py"
```

## Parallel Example: Across User Stories

```text
# After Phase 1 completes, launch all three user stories in parallel:
Task T004-T011: "US1 — Install pickers in src/lola/cli/install.py"
Task T012-T016: "US2 — Uninstall picker in src/lola/cli/install.py"
Task T017-T021: "US3 — Marketplace picker in src/lola/market/manager.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 3: User Story 1 (T004-T011)
3. **STOP and VALIDATE**: Test `lola install` interactively — both with and without module name and `-a` flag
4. Deploy/demo if ready — this is the highest-impact change

### Incremental Delivery

1. Phase 1 → Foundation ready
2. Add US1 (Phase 3) → Test independently → Interactive install works (MVP!)
3. Add US2 (Phase 4) → Test independently → Interactive uninstall works
4. Add US3 (Phase 5) → Test independently → Marketplace picker works
5. Phase 6 → Polish and final validation
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- US2 and US3 modify different functions/files than US1 and can proceed in parallel
- All three stories share `src/lola/prompts.py` (read-only after Phase 1) — no conflict
- Cancellation convention: exit code 130 (128 + SIGINT) per SC-005 and contracts/cli-commands.md
- Commit after each phase checkpoint
- Stop at any checkpoint to validate the story independently
