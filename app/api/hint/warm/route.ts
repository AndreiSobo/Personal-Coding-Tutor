import { NextResponse } from 'next/server'

const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

/**
 * GET /api/hint/warm
 *
 * Pings HuggingFace Inference Endpoint to wake the container

 * Returns regardless of whether the endpoint is ready.
 */
export async function GET() {
    try {
        // Minimal chat completion
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 5000) // 5s

        const response = await fetch(`${HF_ENDPOINT_URL}/health`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${HF_TOKEN}`,
            },
            signal: controller.signal,
        })

        clearTimeout(timeout)

        return NextResponse.json({
            status: response.ok ? 'warm' : 'warming',
            code: response.status,
        })
    } catch {
        // Timeout or network error — container is likely cold-starting
        return NextResponse.json({ status: 'warming' })
    }
}