import { NextResponse } from 'next/server'

const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

/**
 * GET /api/hint/warm
 *
 * Sends a minimal inference request to the HuggingFace Inference Endpoint
 * to wake the container from scale-to-zero sleep.
 * Called on dashboard page mount.
 */
export async function GET() {
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 10000) // 10s — enough to trigger wake

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