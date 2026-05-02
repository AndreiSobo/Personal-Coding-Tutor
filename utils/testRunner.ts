import type { TestResult, TestSummary } from '@/hooks/usePyodide'

export function parseTestResults(
    capturedOutput: string[],
    totalTestCount: number
): TestSummary | null {
    const resultsStart = capturedOutput.indexOf('__PACT_TEST_RESULTS__')
    const resultsEnd = capturedOutput.indexOf('__PACT_TEST_RESULTS_END__')

    if (resultsStart === -1 || resultsEnd === -1) return null

    const resultLines = capturedOutput.slice(resultsStart + 1, resultsEnd)
    const results: TestResult[] = resultLines.map((line) => {
        try {
            return JSON.parse(line)
        } catch {
            return { index: -1, passed: false, error: `Failed to parse: ${line}` }
        }
    })

    const passed = results.filter((r) => r.passed).length
    return {
        passed,
        failed: results.length - passed,
        total: totalTestCount,
        results,
        allPassed: passed === results.length && results.length > 0,
    }
}

export function formatTestOutput(summary: TestSummary, maxTestCases: number): string[] {
    const outputLines: string[] = []

    if (summary.allPassed) {
        outputLines.push(`✓ All ${summary.passed}/${Math.min(maxTestCases, summary.total)} tests passed!`)
        if (summary.total > maxTestCases) {
            outputLines.push(`  (${maxTestCases} of ${summary.total} total tests run)`)
        }
    } else {
        outputLines.push(`✗ ${summary.passed}/${summary.results.length} tests passed`)
        outputLines.push('')

        const failures = summary.results.filter((r) => !r.passed).slice(0, 3)
        for (const f of failures) {
            if (f.error) {
                outputLines.push(`  Test ${f.index + 1}: Error — ${f.error}`)
                if (f.prints) outputLines.push(`    Printed: ${f.prints}`)
            } else {
                outputLines.push(`  Test ${f.index + 1}: FAILED`)
                if (f.prints) outputLines.push(`    Printed: ${f.prints}`)
                outputLines.push(`    Expected: ${f.expected}`)
                outputLines.push(`    Got:      ${f.actual}`)
            }
            outputLines.push('')
        }

        const remaining = summary.results.filter((r) => !r.passed).length - failures.length
        if (remaining > 0) {
            outputLines.push(`  ... and ${remaining} more failing test(s)`)
        }
    }

    return outputLines
}