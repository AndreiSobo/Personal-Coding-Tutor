import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

const HF_ENDPOINT_URL = process.env.HF_ENDPOINT_URL!
const HF_TOKEN = process.env.HF_TOKEN!

const SYSTEM_PROMPT = `You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers.

CRITICAL RULES:
1. The student is coding in a LeetCode-style environment. 
2. All code MUST be wrapped in a 'class Solution:' and use 'self' in the method signature. 
3. Do NOT treat the class structure, the 'self' parameter, or the lack of object instantiation as a bug. 
4. Ignore the class boilerplate entirely and focus ONLY on the algorithmic logic and internal syntax of the method itself.`

export async function POST(request: NextRequest) {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

    let body;
    try { body = await request.json() }
    catch { return NextResponse.json({ error: 'Invalid request body' }, { status: 400 }) }

    const { problem_description, user_code, previous_hints = [], error_message, console_tail, execution_attempted } = body

    const sanitize = (s: unknown, limit = 3000) => String(s || '').slice(0, limit).replace(/`/g, "'")
    const safeError = sanitize(error_message)
    const safeConsole = sanitize(console_tail)

    let userMessage = `Problem:\n${problem_description}\n\nMy code:\n\`\`\`python\n${user_code}\n\`\`\``

    if (previous_hints.length > 0) {
        const hintsContext = previous_hints.map((h: string, i: number) => `${i + 1}. ${h}`).join('\n')
        userMessage += `\n\nI have already received the following hints:\n${hintsContext}\n\nThese hints were not enough. Can you give me a different hint that approaches the problem from another angle?`
    } else {
        userMessage += `\n\nMy code is not passing the tests. Please analyze my code against the problem description, identify the exact logical or syntax error, and give me a specific, guiding Socratic hint that points me toward the flaw without revealing the direct solution.`
    }

    if (execution_attempted === false) {
        userMessage += `\n\nNote: The user's code was NOT executed yet. No runtime error is available. Please focus on static analysis.`
    } else if (safeError) {
        userMessage += `\n\nTerminal error output:\n\`\`\`\n${safeError}\n\`\`\`\nPlease use this error to give a more targeted hint.`
    }

    const prompt = [
        `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>`,
        `<|im_start|>user\n${userMessage}<|im_end|>`,
        `<|im_start|>assistant\n`,
    ].join('\n')

    try {
        // FAIL FAST: Give Hugging Face exactly 10 seconds to respond. 
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000)

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

        clearTimeout(timeoutId)

        if (!hfResponse.ok) throw new Error(`HF HTTP Error: ${hfResponse.status}`)

        const data = await hfResponse.json()
        let hint = data?.[0]?.generated_text?.trim()
        if (!hint) throw new Error('Empty response')

        hint = hint.replace(/<\|im_end\|>/g, '').trim()
        return NextResponse.json({ hint })

    } catch (error: any) {
        // If HF is paused or times out after 10s, immediately return a 503 to trigger the frontend fallback
        console.warn("Primary HF Endpoint failed or timed out. Instructing client to use Azure Fallback.")
        return NextResponse.json({ error: "Primary engine unavailable. Triggering fallback." }, { status: 503 })
    }
}