export function sanitize(s: unknown, limit = 3000): string {
    return String(s || '').slice(0, limit).replace(/`/g, "'")
}

export function buildUserMessage(params: {
    problem_description: string
    user_code: string
    previous_hints: string[]
    error_message: string
    execution_attempted: boolean | undefined
}): string {
    const { problem_description, user_code, previous_hints, error_message, execution_attempted } = params

    let msg = `Problem:\n${problem_description}\n\nMy code:\n\`\`\`python\n${user_code}\n\`\`\``

    if (previous_hints.length > 0) {
        const ctx = previous_hints.map((h, i) => `${i + 1}. ${h}`).join('\n')
        msg += `\n\nI have already received the following hints:\n${ctx}\n\nThese hints were not enough. Can you give me a different hint that approaches the problem from another angle?`
    } else {
        msg += `\n\nMy code is not passing the tests. Please analyze my code against the problem description, identify the exact logical or syntax error, and give me a specific, guiding Socratic hint that points me toward the flaw without revealing the direct solution.`
    }

    if (execution_attempted === false) {
        msg += `\n\nNote: The user's code was NOT executed yet. No runtime error is available. Please focus on static analysis.`
    } else if (error_message) {
        msg += `\n\nTerminal error output:\n\`\`\`\n${error_message}\n\`\`\`\nPlease use this error to give a more targeted hint.`
    }

    return msg
}