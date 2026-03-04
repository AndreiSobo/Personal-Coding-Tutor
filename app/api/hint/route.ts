import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

const SYSTEM_PROMPT =
    'You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers.'

/**
 * POST /api/hint
 *
 * Accepts: { problem_description, user_code, previous_hints }
 * Returns: { hint } or { error }
 */
export async function POST(request: NextRequest) {
    // ── 1. Verify the user is authenticated ──────────────────────
    const supabase = await createClient()
    const {
        data: { user },
    } = await supabase.auth.getUser()

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // ── 2. Parse the request body ────────────────────────────────
    let body: {
        problem_description: string
        user_code: string
        previous_hints: string[]
    }

    try {
        body = await request.json()
    } catch {
        return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
    }

    const { problem_description, user_code, previous_hints = [] } = body

    if (!problem_description || !user_code) {
        return NextResponse.json(
            { error: 'Missing problem_description or user_code' },
            { status: 400 }
        )
    }

    // ── 3. Build the user message (single-turn) ──────────────────
    // The model was fine-tuned on single-turn conversations only.
    // Previous hints are included as context within the user message.

    let userMessage =
        `Problem:\n${problem_description}\n\nMy code:\n\`\`\`python\n${user_code}\n\`\`\``

    if (previous_hints.length > 0) {
        const hintsContext = previous_hints
            .map((h, i) => `${i + 1}. ${h}`)
            .join('\n')
        userMessage +=
            `\n\nI have already received the following hints:\n${hintsContext}\n\nThese hints were not enough. Can you give me a different hint that approaches the problem from another angle?`
    } else {
        userMessage += `\n\nCan you give me a hint?`
    }

    // ── 4. Construct the ChatML prompt manually ──────────────────
    // Qwen 2.5 uses ChatML format: <|im_start|>role\ncontent<|im_end|>
    // The prompt ends with <|im_start|>assistant\n to trigger generation.

    const prompt = [
        `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>`,
        `<|im_start|>user\n${userMessage}<|im_end|>`,
        `<|im_start|>assistant\n`,
    ].join('\n')

    // ── 5. Call the HuggingFace Inference Endpoint ───────────────
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 30000) // 30s timeout

        const response = await fetch(HF_ENDPOINT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${HF_TOKEN}`,
            },
            body: JSON.stringify({
                inputs: prompt,
                parameters: {
                    max_new_tokens: 300,
                    temperature: 0.7,
                    top_p: 0.9,
                    return_full_text: false,
                },
            }),
            signal: controller.signal,
        })

        clearTimeout(timeout)

        // ── 6. Handle response ───────────────────────────────────────
        if (response.status === 503) {
            return NextResponse.json(
                { error: 'Model is warming up. Please try again in a few seconds.' },
                { status: 503 }
            )
        }

        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error')
            console.error(`HF endpoint error (${response.status}):`, errorText)
            return NextResponse.json(
                { error: 'Failed to generate hint. Please try again.' },
                { status: 502 }
            )
        }

        const data = await response.json()

        // Default Engine returns: [{"generated_text": "..."}]
        let hint = data?.[0]?.generated_text?.trim()

        if (!hint) {
            console.error('Unexpected HF response format:', JSON.stringify(data))
            return NextResponse.json(
                { error: 'Received empty response from model.' },
                { status: 502 }
            )
        }

        // Clean up: remove any trailing ChatML tokens the model may generate
        hint = hint.replace(/<\|im_end\|>/g, '').trim()

        return NextResponse.json({ hint })
    } catch (err: any) {
        if (err.name === 'AbortError') {
            return NextResponse.json(
                { error: 'Request timed out. The model may be starting up — please try again.' },
                { status: 504 }
            )
        }

        console.error('Hint API error:', err)
        return NextResponse.json(
            { error: 'Something went wrong. Please try again.' },
            { status: 500 }
        )
    }
}