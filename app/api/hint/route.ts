// /app/api/hint/route.ts

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

const AZURE_ENDPOINT_URL = process.env.AZURE_ENDPOINT_URL!
const AZURE_TOKEN = process.env.AZURE_TOKEN!
const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

const SYSTEM_PROMPT = `You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers.

CRITICAL RULES:
1. The student is coding in a LeetCode-style environment. 
2. All code MUST be wrapped in a 'class Solution:' and use 'self' in the method signature. 
3. Do NOT treat the class structure, the 'self' parameter, or the lack of object instantiation as a bug. 
4. Ignore the class boilerplate entirely and focus ONLY on the algorithmic logic and internal syntax of the method itself.`

// Attempts inference against a given endpoint.
// Returns the generated text string on success, or null on any failure.
// Null triggers the fallback to the next backend.

async function callInference(
    endpointUrl: string,
    token: string,
    prompt: string,
    parameters: object
): Promise<{ text: string | null; status: number | null }> {
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 30000)

        const response = await fetch(endpointUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                inputs: prompt,
                parameters,
            }),
            signal: controller.signal,
        })

        clearTimeout(timeout)

        // Return the status code alongside null so the caller can
        // distinguish a 503 warming-up response from a hard failure
        if (!response.ok) {
            return { text: null, status: response.status }
        }

        const data = await response.json()
        const text = data?.[0]?.generated_text?.trim() || null
        return { text, status: 200 }

    } catch (err: any) {
        if (err.name === 'AbortError') {
            // Timeout — treat as 504
            return { text: null, status: 504 }
        }
        // Network error, VM unreachable, etc.
        return { text: null, status: null }
    }
}

/**
 * POST /api/hint
 *
 * Accepts: { problem_description, user_code, previous_hints }
 * Returns: { hint } or { error }
 */
export async function POST(request: NextRequest) {
    // Verify the user is authenticated
    const supabase = await createClient()
    const {
        data: { user },
    } = await supabase.auth.getUser()

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Parse the request body
    let body: {
        problem_description: string
        user_code: string
        previous_hints: string[]
        error_message?: string
        console_tail?: string
        execution_attempted?: boolean
        execution_reason?: string
    }

    try {
        body = await request.json()
    } catch {
        return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
    }

    const {
        problem_description,
        user_code,
        previous_hints = [],
        error_message,
        console_tail,
        execution_attempted,
    } = body

    // Sanitize runtime context: truncate to 3000 chars and strip backticks to avoid ChatML injection
    const sanitize = (s: unknown, limit = 3000) =>
        String(s || '').slice(0, limit).replace(/`/g, "'")
    const safeError = sanitize(error_message)
    const safeConsole = sanitize(console_tail)

    if (!problem_description || !user_code) {
        return NextResponse.json(
            { error: 'Missing problem_description or user_code' },
            { status: 400 }
        )
    }

    // Build the user message (single-turn)
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
        userMessage += `\n\nMy code is not passing the tests. Please analyze my code against the problem description, identify the exact logical or syntax error, and give me a specific, guiding Socratic hint that points me toward the flaw without revealing the direct solution.`
    }

    // Append execution context so the LLM can give a more targeted hint
    if (execution_attempted === false) {
        userMessage += `\n\nNote: The user's code was NOT executed yet. No runtime error is available. Please focus on static analysis: look for syntax issues, logic flaws, and encourage the user to run their code first.`
    } else if (safeError) {
        userMessage += `\n\nTerminal error output:\n\`\`\`\n${safeError}\n\`\`\`\nPlease use this error to give a more targeted hint.`
    } else if (safeConsole) {
        userMessage += `\n\nRecent console output:\n\`\`\`\n${safeConsole}\n\`\`\``
    }

    // Construct the ChatML prompt
    // Qwen 2.5 uses ChatML format: <|im_start|>role\ncontent<|im_end|>
    // The prompt ends with <|im_start|>assistant\n to trigger generation.
    const prompt = [
        `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>`,
        `<|im_start|>user\n${userMessage}<|im_end|>`,
        `<|im_start|>assistant\n`,
    ].join('\n')

    const parameters = {
        max_new_tokens: 300,
        temperature: 0.3,
        top_p: 0.9,
        return_full_text: false,
    }


    const azureResult = await callInference(AZURE_ENDPOINT_URL, AZURE_TOKEN, prompt, parameters)

    console.log('Azure result status:', azureResult.status)
    console.log('Azure result text:', azureResult.text)

    if (!azureResult.text) {
        return NextResponse.json(
            { error: `Azure inference failed with status: ${azureResult.status}` },
            { status: 502 }
        )
    }

    const hint = azureResult.text.replace(/<\|im_end\|>/g, '').trim()
    return NextResponse.json({ hint })

}
