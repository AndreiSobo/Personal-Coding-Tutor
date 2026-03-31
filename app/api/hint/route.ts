// /app/api/hint/route.ts

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

// Maximize Vercel timeout to give the CPU stream as much runway as possible
export const maxDuration = 60;

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


/**
 * POST /api/hint
 *
 * Accepts: { problem_description, user_code, previous_hints }
 * Returns: JSON { hint } (from HF) OR a ReadableStream (from Azure)
 */
export async function POST(request: NextRequest) {
    // 1. Verify Authentication
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // 2. Parse and Sanitize Request
    let body;
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

    const sanitize = (s: unknown, limit = 3000) => String(s || '').slice(0, limit).replace(/`/g, "'")
    const safeError = sanitize(error_message)
    const safeConsole = sanitize(console_tail)

    if (!problem_description || !user_code) {
        return NextResponse.json({ error: 'Missing problem_description or user_code' }, { status: 400 })
    }

    // 3. Construct Prompt (Single-turn ChatML)
    let userMessage = `Problem:\n${problem_description}\n\nMy code:\n\`\`\`python\n${user_code}\n\`\`\``

    if (previous_hints.length > 0) {
        const hintsContext = previous_hints.map((h: string, i: number) => `${i + 1}. ${h}`).join('\n')
        userMessage += `\n\nI have already received the following hints:\n${hintsContext}\n\nThese hints were not enough. Can you give me a different hint that approaches the problem from another angle?`
    } else {
        userMessage += `\n\nMy code is not passing the tests. Please analyze my code against the problem description, identify the exact logical or syntax error, and give me a specific, guiding Socratic hint that points me toward the flaw without revealing the direct solution.`
    }

    if (execution_attempted === false) {
        userMessage += `\n\nNote: The user's code was NOT executed yet. No runtime error is available. Please focus on static analysis: look for syntax issues, logic flaws, and encourage the user to run their code first.`
    } else if (safeError) {
        userMessage += `\n\nTerminal error output:\n\`\`\`\n${safeError}\n\`\`\`\nPlease use this error to give a more targeted hint.`
    } else if (safeConsole) {
        userMessage += `\n\nRecent console output:\n\`\`\`\n${safeConsole}\n\`\`\``
    }

    const prompt = [
        `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>`,
        `<|im_start|>user\n${userMessage}<|im_end|>`,
        `<|im_start|>assistant\n`,
    ].join('\n')


    // ==========================================
    // INFERENCE PIPELINE: FAILOVER ARCHITECTURE
    // ==========================================

    // ATTEMPT 1: Hugging Face GPU (Synchronous JSON)
    try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 15000) // Fail fast (15s)

        const hfResponse = await fetch(HF_ENDPOINT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${HF_TOKEN}`,
            },
            body: JSON.stringify({
                inputs: prompt,
                parameters: { max_new_tokens: 300, temperature: 0.3, top_p: 0.9, return_full_text: false },
            }),
            signal: controller.signal,
        })

        clearTimeout(timeout)

        if (!hfResponse.ok) {
            throw new Error(`HF Failed with status: ${hfResponse.status}`)
        }

        const data = await hfResponse.json()
        let hint = data?.[0]?.generated_text?.trim()

        if (!hint) throw new Error('Empty response from HF.')

        hint = hint.replace(/<\|im_end\|>/g, '').trim()

        // SUCCESS: Return standard JSON
        return NextResponse.json({ hint })

    } catch (hfError: any) {
        console.warn('⚠️ Hugging Face Primary failed, falling back to Azure CPU Stream...', hfError.message)

        // ATTEMPT 2: Azure CPU (Streaming)
        try {
            const azureResponse = await fetch(AZURE_ENDPOINT_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${AZURE_TOKEN}`,
                },
                body: JSON.stringify({
                    inputs: prompt,
                    parameters: { max_new_tokens: 200, temperature: 0.3, top_p: 0.9 },
                }),
            })

            if (!azureResponse.ok) {
                return NextResponse.json(
                    { error: 'Both Primary (GPU) and Fallback (CPU) engines are unavailable.' },
                    { status: 502 }
                )
            }

            // SUCCESS: Return the raw ReadableStream directly to the frontend
            return new Response(azureResponse.body, {
                headers: {
                    'Content-Type': 'text/plain; charset=utf-8',
                    'Cache-Control': 'no-cache',
                },
            })

        } catch (azureError) {
            console.error('🚨 Azure Fallback also failed:', azureError)
            return NextResponse.json(
                { error: 'Critical failure: Could not connect to any inference engine.' },
                { status: 500 }
            )
        }
    }
}