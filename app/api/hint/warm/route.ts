import { NextResponse } from 'next/server'

const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

/**
 * GET /api/hint/warm
 *
 * Sends a minimal inference request to the HuggingFace Inference Endpoint
 * to wake the container from scale-to-zero sleep.
 *
 * A GET to /health does NOT trigger scale-up — only actual inference
 * requests (POST to root) wake the container. This sends the smallest
 * possible prompt with max_new_tokens: 1 to minimise compute cost.
 *
 * Called fire-and-forget from the dashboard page on mount.
 * Returns quickly regardless of whether the endpoint is ready.
 */
export async function GET() {
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 10000) // 10s — enough to trigger wake, not wait for full start

        const response = await fetch(HF_ENDPOINT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${HF_TOKEN}`,
            },
            body: JSON.stringify({
                inputs: 'Hi',
                parameters: {
                    max_new_tokens: 1,
                },
            }),
            signal: controller.signal,
        })

        clearTimeout(timeout)

        return NextResponse.json({
            status: response.ok ? 'warm' : 'warming',
            code: response.status,
        })
    } catch {
        // Timeout or network error — container is waking up, which is the goal
        return NextResponse.json({ status: 'warming' })
    }
}