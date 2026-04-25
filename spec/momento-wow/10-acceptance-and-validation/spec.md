# Step 10 — Acceptance and Validation

## Scope

This step specifies end-to-end acceptance criteria, a test matrix, and a verification plan for the complete Momento Wow feature set. It covers:
- Feature-level acceptance criteria
- Integration test scenarios
- Cross-feature interaction matrix
- Regression checklist
- Manual testing plan

This step does NOT cover:
- Unit test specifications for individual functions (covered in Steps 02, 06)
- Component-level tests (covered in Steps 03, 05, 08)
- CI/CD configuration

## Context

The Momento Wow feature set adds three capabilities (Authenticity Score, Sample Document, Export) that layer onto existing components. Validation must ensure that:
1. Each feature works correctly in isolation
2. Features work together (e.g., score appears in both UI and PDF)
3. Existing functionality is not regressed (upload flow, polling, result display)

## Requirements

### 1) End-to-End User Journeys

The following journeys MUST pass without errors:

#### Journey 1: First-Time Visitor (Sample Document)
1. User opens the application for the first time
2. User sees the file dropzone with "Try with example" button visible
3. User clicks "Try with example"
4. Sample PDF appears in the dropzone as a selected file
5. User clicks Submit
6. Job appears in Recent Analyses table as "queued"
7. Job transitions to "running" (visible in real-time)
8. Job transitions to "succeeded"
9. User expands the job row
10. Authenticity Score is visible with a number and color semaphore
11. Classification breakdown is visible below the score
12. Reference details are expandable
13. Export CSV and Export PDF buttons are visible in the panel footer
14. User clicks Export CSV → file downloads
15. User clicks Export PDF → loading state shown → file downloads

#### Journey 2: Returning User (Own Document)
1. User uploads their own PDF
2. Analysis completes
3. Authenticity Score is visible and reflects the actual classification breakdown
4. User exports PDF → report contains correct score, summary, and reference details
5. User exports CSV → spreadsheet contains all references with correct columns

#### Journey 3: Language Switching
1. User completes an analysis (or uses sample)
2. User switches language from EN to ES
3. Authenticity Score band label updates to Spanish
4. Export buttons update labels to Spanish
5. User exports PDF → PDF content is in Spanish (labels, disclaimer)
6. User switches to PT → same behavior in Portuguese

#### Journey 4: Theme Switching
1. User completes an analysis in light mode
2. Authenticity Score displays with adequate contrast
3. User switches to dark mode
4. Score, buttons, and all components maintain readable contrast

### 2) Feature Interaction Matrix

The following cross-feature interactions MUST be verified:

| Feature A | Feature B | Interaction | Verification |
|-----------|-----------|-------------|--------------|
| Score | Export PDF | Score appears in PDF | PDF Section 2 matches UI score |
| Score | Export CSV | Score NOT in CSV | CSV contains per-reference data only |
| Sample Doc | Score | Sample produces medium-band score | Score is 50-79 with amber semaphore |
| Sample Doc | Export | Can export sample results | Both CSV and PDF download correctly |
| Score | i18n | Labels translate | Band label matches selected language |
| Export PDF | i18n | PDF content translates | Labels and disclaimer in selected language |
| Export CSV | i18n | Column headers stay English | Headers are fixed; data may contain localized content |

### 3) Regression Checklist

The following existing behaviors MUST NOT be regressed:

- [ ] File upload via drag-and-drop still works
- [ ] File upload via file picker still works
- [ ] File validation (size, type) still works
- [ ] Submit button appears after file selection
- [ ] Upload progress is shown
- [ ] Job appears in Recent Analyses after submission
- [ ] Polling updates status in real-time
- [ ] Expanding a succeeded job shows reference details
- [ ] Expanding a failed job shows error message
- [ ] Expanding a running job shows current stage
- [ ] Remove button deletes job from list and localStorage
- [ ] Page refresh preserves job history in localStorage
- [ ] Expired token transitions job to expired status
- [ ] Dark mode / light mode toggle works
- [ ] Language toggle (EN/ES/PT) works
- [ ] No TypeScript errors (`tsc --noEmit` passes)
- [ ] Existing tests pass (`vitest run` passes)

### 4) Automated Test Requirements

The following automated tests MUST exist:

#### Unit Tests
- `computeScore` — all cases from Step 02 acceptance criteria (minimum 6 test cases)
- `buildCsvString` — all cases from Step 06 acceptance criteria (minimum 5 test cases)

#### Type Checking
- `tsc --noEmit` MUST pass with zero errors

#### Existing Test Suite
- All existing vitest tests MUST continue to pass
- i18n key synchronization test MUST pass with the new keys

### 5) Manual Testing Plan

The following MUST be verified manually in a browser:

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Sample button visible | Open app with no file selected | "Try with example" button is visible in dropzone |
| Sample triggers upload | Click "Try with example" | File "sample-references.pdf" appears in dropzone |
| Sample end-to-end | Submit sample → wait for completion | Score visible, references classified, export available |
| Score colors | Complete analysis with varied results | Green for high, amber for medium, red for low |
| CSV content | Export CSV → open in spreadsheet | 13 columns, correct data, proper escaping |
| PDF content | Export PDF → open in PDF viewer | 5 sections, score colored, references listed |
| PDF multi-page | Analyze document with 20+ references → export PDF | PDF has multiple pages with page numbers |
| Dark mode | Toggle dark mode with expanded results | All components readable, adequate contrast |
| Mobile view | View on 375px width viewport | Score, buttons, and content fit without horizontal scroll |
| Offline sample | Disconnect network → click "Try with example" | Error message shown, dropzone returns to empty state |

### 6) Performance Criteria

| Metric | Threshold | How to Measure |
|--------|-----------|----------------|
| Initial page load | No increase > 10 KB | Bundle analysis before/after |
| Score computation | < 1 ms | Unit test timing |
| CSV generation (30 refs) | < 100 ms | Unit test timing |
| PDF generation (30 refs) | < 5 seconds | Manual timing in browser |
| PDF library load (first click) | < 3 seconds on 3G | Network tab in DevTools with throttling |

## Acceptance Criteria

- All 4 user journeys pass end-to-end without errors
- All feature interactions in the matrix are verified
- All regression checklist items pass
- All automated tests pass (`tsc --noEmit`, `vitest run`)
- All manual tests produce expected results
- Performance criteria are met

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User exports results of a job that later transitions to expired | Export is from the cached result; file is valid |
| User opens app in private/incognito window | All features work; localStorage is per-session |
| User has JavaScript disabled | App does not work (expected; Next.js requires JS) |
| Browser does not support Blob/download API | Export buttons may not work; this is acceptable for very old browsers |
| User has ad blocker that blocks font loading | PDF uses standard fonts; should still work |

## Dependencies

- All previous steps (01-09) MUST be implemented before end-to-end validation
