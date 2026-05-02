import { describe, it, expect } from 'vitest'
import { sanitize, buildUserMessage } from './hint'

describe('sanitize', () => {
    it('converts null and undefined to empty string', () => {
        expect(sanitize(null)).toBe('')
        expect(sanitize(undefined)).toBe('')
    })

    it('truncates to the default limit of 3000 chars', () => {
        const long = 'a'.repeat(5000)
        expect(sanitize(long).length).toBe(3000)
    })

    it('respects a custom limit', () => {
        expect(sanitize('hello world', 5)).toBe('hello')
    })

    it('replaces backticks with single quotes', () => {
        expect(sanitize('use `eval()` carefully')).toBe("use 'eval()' carefully")
    })
})

describe('buildUserMessage', () => {
    const base = {
        problem_description: 'Two Sum',
        user_code: 'class Solution:\n    def twoSum(self): pass',
        previous_hints: [],
        error_message: '',
        execution_attempted: true as boolean | undefined,
    }

    it('includes problem description and code', () => {
        const msg = buildUserMessage(base)
        expect(msg).toContain('Two Sum')
        expect(msg).toContain('twoSum')
    })

    it('asks for first hint when no previous hints', () => {
        const msg = buildUserMessage(base)
        expect(msg).toContain('identify the exact logical or syntax error')
    })

    it('asks for a different angle when previous hints exist', () => {
        const msg = buildUserMessage({ ...base, previous_hints: ['Check your loop bounds'] })
        expect(msg).toContain('different hint that approaches the problem from another angle')
        expect(msg).toContain('1. Check your loop bounds')
    })

    it('adds static analysis note when execution was not attempted', () => {
        const msg = buildUserMessage({ ...base, execution_attempted: false })
        expect(msg).toContain('NOT executed yet')
    })

    it('appends error trace when execution was attempted and error exists', () => {
        const msg = buildUserMessage({ ...base, error_message: 'IndexError: list index out of range' })
        expect(msg).toContain('IndexError: list index out of range')
        expect(msg).toContain('Terminal error output')
    })

    it('does not append error section when execution_attempted is false even with an error', () => {
        const msg = buildUserMessage({ ...base, execution_attempted: false, error_message: 'SomeError' })
        expect(msg).not.toContain('Terminal error output')
        expect(msg).toContain('NOT executed yet')
    })
})