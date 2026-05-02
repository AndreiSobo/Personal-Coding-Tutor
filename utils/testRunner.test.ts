import { describe, it, expect } from 'vitest'
import { parseTestResults, formatTestOutput } from './testRunner'

const makeOutput = (results: object[]) => [
    '__PACT_TEST_RESULTS__',
    ...results.map((r) => JSON.stringify(r)),
    '__PACT_TEST_RESULTS_END__',
]

describe('parseTestResults', () => {
    it('returns null when markers are missing', () => {
        expect(parseTestResults(['some', 'output'], 3)).toBeNull()
    })

    it('sets allPassed true when all results pass', () => {
        const output = makeOutput([
            { index: 0, passed: true },
            { index: 1, passed: true },
        ])
        const summary = parseTestResults(output, 2)
        expect(summary?.allPassed).toBe(true)
        expect(summary?.passed).toBe(2)
    })

    it('sets allPassed false when any result fails', () => {
        const output = makeOutput([
            { index: 0, passed: true },
            { index: 1, passed: false, expected: '[1]', actual: '[0]' },
        ])
        const summary = parseTestResults(output, 2)
        expect(summary?.allPassed).toBe(false)
        expect(summary?.passed).toBe(1)
        expect(summary?.failed).toBe(1)
    })

    it('never sets allPassed true when there are 0 results', () => {
        // Critical: empty run should NOT look like a pass
        const output = makeOutput([])
        const summary = parseTestResults(output, 5)
        expect(summary?.allPassed).toBe(false)
    })

    it('handles a malformed JSON line gracefully', () => {
        const output = [
            '__PACT_TEST_RESULTS__',
            'not valid json',
            '__PACT_TEST_RESULTS_END__',
        ]
        const summary = parseTestResults(output, 1)
        expect(summary?.results[0].error).toContain('Failed to parse')
        expect(summary?.allPassed).toBe(false)
    })
})

describe('formatTestOutput', () => {
    it('shows success message when all tests pass', () => {
        const summary = { passed: 3, failed: 0, total: 3, results: [], allPassed: true }
        const lines = formatTestOutput(summary, 10)
        expect(lines[0]).toContain('✓')
        expect(lines[0]).toContain('3/3')
    })

    it('shows capped-count notice when total exceeds maxTestCases', () => {
        const summary = { passed: 10, failed: 0, total: 80, results: [], allPassed: true }
        const lines = formatTestOutput(summary, 10)
        expect(lines.some((l) => l.includes('10 of 80'))).toBe(true)
    })

    it('shows failure line for each failing test (max 3)', () => {
        const results = [
            { index: 0, passed: false, expected: '[1]', actual: '[0]' },
            { index: 1, passed: false, expected: '[2]', actual: '[1]' },
            { index: 2, passed: false, expected: '[3]', actual: '[2]' },
            { index: 3, passed: false, expected: '[4]', actual: '[3]' },
        ]
        const summary = { passed: 0, failed: 4, total: 4, results, allPassed: false }
        const lines = formatTestOutput(summary, 10)
        expect(lines.some((l) => l.includes('... and 1 more'))).toBe(true)
    })
})