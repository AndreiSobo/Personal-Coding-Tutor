import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Supabase BEFORE importing the route, otherwise it will import the correct one
vi.mock('@/utils/supabase/server', () => ({
    createClient: vi.fn(),
}))

import { POST } from './route'
import { createClient } from '@/utils/supabase/server'

// Helper: build a NextRequest with a JSON body
function makeRequest(body: object): NextRequest {
    return new NextRequest('http://localhost/api/hint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
}

// Helper: make createClient return a specific user (or null)
function mockUser(user: object | null) {
    vi.mocked(createClient).mockResolvedValue({
        auth: { getUser: vi.fn().mockResolvedValue({ data: { user } }) },
    } as any)
}

const validBody = {
    problem_description: 'Two Sum',
    user_code: 'class Solution:\n    def twoSum(self): pass',
    previous_hints: [],
    error_message: '',
    console_tail: '',
    execution_attempted: true,
}

beforeEach(() => {
    vi.restoreAllMocks()
    // Reset the HF env vars so the route doesn't crash on undefined
    process.env.HF_ENDPOINT_URL = 'https://fake-hf-endpoint.com'
    process.env.HF_TOKEN = 'fake-token'
})

describe('POST /api/hint', () => {

    it('returns 401 when user is not authenticated', async () => {
        mockUser(null)
        const res = await POST(makeRequest(validBody))
        expect(res.status).toBe(401)
        const json = await res.json()
        expect(json.error).toBe('Unauthorized')
    })

    it('returns 400 when request body is not valid JSON', async () => {
        mockUser({ id: 'user-123' })
        const req = new NextRequest('http://localhost/api/hint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: 'this is not json',
        })
        const res = await POST(req)
        expect(res.status).toBe(400)
        const json = await res.json()
        expect(json.error).toBe('Invalid request body')
    })

    it('returns a hint when HF endpoint responds successfully', async () => {
        mockUser({ id: 'user-123' })
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: true,
            json: async () => [{ generated_text: 'Have you considered the edge case where the array is empty?' }],
        }))
        const res = await POST(makeRequest(validBody))
        expect(res.status).toBe(200)
        const json = await res.json()
        expect(json.hint).toContain('edge case')
    })

    it('returns 503 when HF endpoint fails', async () => {
        mockUser({ id: 'user-123' })
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: false,
            status: 503,
        }))
        const res = await POST(makeRequest(validBody))
        expect(res.status).toBe(503)
        const json = await res.json()
        expect(json.error).toContain('unavailable')
    })

    it('returns 503 when HF endpoint times out', async () => {
        mockUser({ id: 'user-123' })
        // Simulate a network timeout by returning a rejected promise
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('The operation was aborted', 'AbortError')))
        const res = await POST(makeRequest(validBody))
        expect(res.status).toBe(503)
    })

})