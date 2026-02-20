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
 *
 * Authentication is verified via the Supabase session cookie.
 */
export async function POST(request: NextRequest) {
    // verify auth
    const supabase = await createClient()
    const {
        data: { user },
    } = await supabase.auth.getUser()

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // parse request body
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

    // build single-turn ChatML convo

    // Previous hints are included as context within the ONE user message - mirroring training data

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

    const messages = [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userMessage },
    ]

    // calls Hugging Face Inference Endpoint
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 30000) // 30s timeout

        const response = await fetch(`${HF_ENDPOINT_URL}/v1/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${HF_TOKEN}`,
            },
            body: JSON.stringify({
                model: 'tgi',
                messages,
                max_tokens: 300,
                temperature: 0.7,
                top_p: 0.9,
            }),
            signal: controller.signal,
        })

        clearTimeout(timeout)

        // process response
        if (response.status === 503) {
            // Container is cold-starting
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

        // OpenAI-compatible format: data.choices[0].message.content
        const hint = data?.choices?.[0]?.message?.content?.trim()

        if (!hint) {
            console.error('Unexpected HF response format:', JSON.stringify(data))
            return NextResponse.json(
                { error: 'Received empty response from model.' },
                { status: 502 }
            )
        }

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