'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useParams, useRouter } from 'next/navigation'
import CodeEditor from '@/components/CodeEditor'
import Console from '@/components/Console'
import usePyodide from '@/hooks/usePyodide'
import { formatTitle } from '@/utils/formatTitle'
import ThemeToggle from '@/components/ThemeToggle'
import { useTheme } from '@/components/ThemeProvider'

interface Problem {
  id: string
  slug: string
  difficulty: string
  tags: string[]
  description: string
  starter_code: string
  entry_point: string
  input_output: { input: string; output: string }[]
}

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>()
  const router = useRouter()
  const supabase = createClient()
  const { theme } = useTheme()

  // Problem state
  const [problem, setProblem] = useState<Problem | null>(null)
  const [loading, setLoading] = useState(true)
  const [code, setCode] = useState('')

  // Pyodide
  const { runTests, output, isLoading: pyodideLoading, isRunning, testSummary } = usePyodide()

  // Mobile tab
  const [activeTab, setActiveTab] = useState<'problem' | 'code'>('problem')

  // Submit state
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Progress tracking
  const [solvedCount, setSolvedCount] = useState<number | null>(null)

  // Hint state
  const [hints, setHints] = useState<string[]>([])
  const [streamingHint, setStreamingHint] = useState<string>('') // NEW: Holds the active stream text
  const [hintsUsed, setHintsUsed] = useState(0)
  const [isRequestingHint, setIsRequestingHint] = useState(false)
  const [hintError, setHintError] = useState<string | null>(null)
  const [hintMessage, setHintMessage] = useState<string | null>(null)
  // Tracks whether the user has run their code at least once
  const [lastRunAttempted, setLastRunAttempted] = useState(false)

  // Show Answer state
  const [solutionCode, setSolutionCode] = useState<string | null>(null)
  const [showSolution, setShowSolution] = useState(false)
  const [solutionError, setSolutionError] = useState<string | null>(null)
  const canShowAnswer = hintsUsed >= 3

  // Clear the "all tests passed" message when the user re-runs code and it no longer passes
  useEffect(() => {
    if (!testSummary?.allPassed) setHintMessage(null)
  }, [testSummary])

  // Fetch problem on mount
  useEffect(() => {
    async function fetchProblem() {
      const { data, error } = await supabase
        .from('content_problems')
        .select('id, slug, difficulty, tags, description, starter_code, entry_point, input_output')
        .eq('slug', slug)
        .single()

      if (error || !data) {
        console.error('Error fetching problem:', error)
        router.push('/dashboard')
        return
      }

      setProblem(data as Problem)
      setCode(data.starter_code || '')
      setLoading(false)

      // Count how many problems of this difficulty the user has already solved
      const { data: { user } } = await supabase.auth.getUser()
      if (user) {
        const { count } = await supabase
          .from('user_progress')
          .select('id, content_problems!inner(difficulty)', { count: 'exact', head: true })
          .eq('user_id', user.id)
          .eq('content_problems.difficulty', data.difficulty)
        setSolvedCount(count ?? 0)
      }
    }

    if (slug) fetchProblem()
  }, [slug])

  // Run tests
  const handleRun = useCallback(async () => {
    if (!problem) return
    setLastRunAttempted(true)
    await runTests(code, problem.entry_point, problem.input_output)
  }, [code, problem, runTests])

  // Submit
  const handleSubmit = useCallback(async () => {
    if (!problem || !testSummary?.allPassed || isSubmitted) return
    setIsSubmitting(true)

    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/login')
        return
      }

      const { error } = await supabase
        .from('user_progress')
        .upsert(
          {
            user_id: user.id,
            problem_id: problem.id,
            hints_used: hintsUsed,
          },
          { onConflict: 'user_id,problem_id' }
        )

      if (error) {
        console.error('Submit error:', error)
        return
      }

      setIsSubmitted(true)
    } catch (err) {
      console.error('Submit failed:', err)
    } finally {
      setIsSubmitting(false)
    }
  }, [problem, testSummary, isSubmitted, hintsUsed, supabase, router])

  // Request Hint
  const handleRequestHint = useCallback(async () => {
    if (!problem || isRequestingHint) return

    if (testSummary?.allPassed) {
      setHintMessage('All tests passed — your code is correct! No hints needed.')
      return
    }

    setIsRequestingHint(true)
    setHintError(null)
    setHintMessage(null)

    const execution_attempted = lastRunAttempted || output.length > 0 || !!testSummary
    const firstTestError = testSummary?.results?.find((r) => r.error)
    const rawError = firstTestError?.error || output.find((l) => l.startsWith('Error:') || l.includes('Error —'))?.replace(/^Error:\s*/, '') || ''
    const sanitize = (s: string, limit = 3000) => String(s || '').slice(0, limit).replace(/`/g, "'")
    const error_message = sanitize(rawError)
    const console_tail = sanitize(output.slice(-20).join('\n'))

    try {
      // 1. PRIMARY: Try Vercel Backend (Hugging Face GPU)
      const hfResponse = await fetch('/api/hint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_description: problem.description,
          user_code: code,
          previous_hints: hints,
          error_message,
          console_tail,
          execution_attempted,
        }),
      })

      if (hfResponse.ok) {
        const data = await hfResponse.json()
        if (data.hint) {
          setHints((prev) => [...prev, data.hint])
          setHintsUsed((prev) => prev + 1)
          setIsRequestingHint(false)
          return
        }
      }

      // If HF fails, purposefully throw an error to trigger the Azure Fallback
      throw new Error("Primary HF endpoint unavailable.")

    } catch (err) {
      console.warn("Primary endpoint failed. Falling back directly to Azure CPU...", err)

      // 2. FALLBACK: Direct Browser-to-Azure Streaming
      try {
        const AZURE_URL = process.env.NEXT_PUBLIC_AZURE_ENDPOINT_URL!
        const AZURE_TOKEN = process.env.NEXT_PUBLIC_AZURE_TOKEN!

        // Rebuild the prompt for Azure
        const SYSTEM_PROMPT = `You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers.\n\nCRITICAL RULES:\n1. The student is coding in a LeetCode-style environment.\n2. All code MUST be wrapped in a 'class Solution:' and use 'self' in the method signature.\n3. Do NOT treat the class structure, the 'self' parameter, or the lack of object instantiation as a bug.\n4. Ignore the class boilerplate entirely and focus ONLY on the algorithmic logic and internal syntax of the method itself.`

        let userMessage = `Problem:\n${problem.description}\n\nMy code:\n\`\`\`python\n${code}\n\`\`\``
        if (hints.length > 0) {
          const hintsContext = hints.map((h, i) => `${i + 1}. ${h}`).join('\n')
          userMessage += `\n\nI have already received the following hints:\n${hintsContext}\n\nThese hints were not enough. Can you give me a different hint that approaches the problem from another angle?`
        } else {
          userMessage += `\n\nMy code is not passing the tests. Please analyze my code against the problem description, identify the exact logical or syntax error, and give me a specific, guiding Socratic hint that points me toward the flaw without revealing the direct solution.`
        }
        if (execution_attempted === false) {
          userMessage += `\n\nNote: The user's code was NOT executed yet. No runtime error is available. Please focus on static analysis.`
        } else if (error_message) {
          userMessage += `\n\nTerminal error output:\n\`\`\`\n${error_message}\n\`\`\`\nPlease use this error to give a more targeted hint.`
        }

        const rawPrompt = `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n${userMessage}<|im_end|>\n<|im_start|>assistant\n`

        const azureResponse = await fetch(AZURE_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${AZURE_TOKEN}`
          },
          body: JSON.stringify({
            inputs: rawPrompt,
            parameters: { max_new_tokens: 200, temperature: 0.3, top_p: 0.9 }
          })
        })

        if (!azureResponse.ok || !azureResponse.body) {
          throw new Error('Fallback Azure endpoint unavailable.')
        }


        const reader = azureResponse.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let done = false
        let streamedText = ''

        while (!done) {
          const { value, done: readerDone } = await reader.read()
          done = readerDone
          if (value) {
            streamedText += decoder.decode(value, { stream: true })
            setStreamingHint(streamedText)
          }
        }

        setHints((prev) => [...prev, streamedText.trim()])
        setHintsUsed((prev) => prev + 1)
        setStreamingHint('')
        setIsRequestingHint(false)

      } catch (azureErr) {
        setHintError('Both AI engines are currently unavailable. Please try again later.')
        setIsRequestingHint(false)
      }
    }
  }, [problem, code, hints, isRequestingHint, output, testSummary, lastRunAttempted])

  // Show answer
  const handleShowAnswer = useCallback(async () => {
    if (!problem || !canShowAnswer) return
    setSolutionError(null)

    if (!solutionCode) {
      const { data, error } = await supabase
        .from('content_problems')
        .select('solution_code')
        .eq('id', problem.id)
        .single()

      if (error || !data) {
        console.error('Failed to fetch solution:', error)
        setSolutionError('Could not load the solution. Please try again.')
        return
      }

      if (!data.solution_code) {
        setSolutionError('No reference solution is available for this problem.')
        return
      }

      setSolutionCode(data.solution_code)
    }

    setShowSolution(true)
  }, [problem, canShowAnswer, solutionCode, supabase])

  // Render
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <p className="text-gray-600 dark:text-gray-400">Loading problem...</p>
      </div>
    )
  }

  if (!problem) return null

  const difficultyColor =
    problem.difficulty === 'Easy'
      ? 'text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/40'
      : problem.difficulty === 'Medium'
        ? 'text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/40'
        : 'text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/40'

  return (
    <div className="h-dvh bg-gray-50 dark:bg-gray-950 flex flex-col transition-colors overflow-hidden">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex justify-between items-center shadow-sm shrink-0 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium shrink-0"
          >
            ← <span className="hidden sm:inline">Dashboard</span>
          </button>
          <h1 className="text-sm font-bold text-gray-900 dark:text-gray-100 truncate">{formatTitle(problem.slug)}</h1>
          <span className={`text-xs font-medium px-2 py-0.5 rounded shrink-0 ${difficultyColor}`}>
            {problem.difficulty}
          </span>
          {solvedCount !== null && (
            <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0 hidden sm:inline">
              {solvedCount} {problem.difficulty.toLowerCase()} solved
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Tags hidden on mobile to save space */}
          <div className="hidden md:flex items-center gap-2">
            {problem.tags.map((tag) => (
              <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-2 py-1 rounded">
                {tag}
              </span>
            ))}
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Mobile tab bar — only visible below lg */}
      <div className="lg:hidden flex border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shrink-0">
        <button
          onClick={() => setActiveTab('problem')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'problem'
            ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
        >
          Problem
        </button>
        <button
          onClick={() => setActiveTab('code')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${activeTab === 'code'
            ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
        >
          Code
        </button>
      </div>

      {/* Workspace */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-0 overflow-hidden min-h-0">
        {/* Left: Problem description + Hints */}
        <div className={`border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-4 lg:p-6 flex flex-col bg-white dark:bg-gray-900 ${activeTab === 'problem' ? 'block' : 'hidden'} lg:block`}>
          {/* Description */}
          <div className="flex-1">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Problem Description</h2>
            <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-sans leading-relaxed bg-gray-50 dark:bg-gray-800 p-4 rounded border border-gray-200 dark:border-gray-700">
              {problem.description}
            </pre>
          </div>

          {/* Solved count on mobile (below tags are hidden in header) */}
          {solvedCount !== null && (
            <p className="sm:hidden mt-4 text-xs text-gray-500 dark:text-gray-400">
              {solvedCount} {problem.difficulty.toLowerCase()} problems solved
            </p>
          )}

          {/* Tags on mobile */}
          <div className="md:hidden flex flex-wrap gap-2 mt-3">
            {problem.tags.map((tag) => (
              <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-2 py-1 rounded">
                {tag}
              </span>
            ))}
          </div>

          {/* Hints section */}
          <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleRequestHint}
                disabled={isRequestingHint || isSubmitted}
                className={`px-4 py-2 text-sm rounded-md font-medium transition-colors ${isRequestingHint || isSubmitted
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                  : 'bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/60'
                  }`}
              >
                {isRequestingHint && !streamingHint
                  ? 'PACT is thinking...'
                  : `Get Hint (${hintsUsed} used)`}
              </button>

              <button
                onClick={handleShowAnswer}
                disabled={!canShowAnswer || isSubmitted}
                className={`px-4 py-2 text-sm rounded-md font-medium transition-colors ${canShowAnswer && !isSubmitted
                  ? 'bg-orange-100 dark:bg-orange-900/40 text-orange-800 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-900/60'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                  }`}
                title={!canShowAnswer ? `Use ${3 - hintsUsed} more hint(s) to unlock` : undefined}
              >
                {canShowAnswer ? 'Show Answer' : `Show Answer (${3 - hintsUsed} more hints needed)`}
              </button>
            </div>

            {/* All-tests-passed success message */}
            {hintMessage && (
              <div className="bg-green-50 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-md px-4 py-3 text-sm text-green-800 dark:text-green-300">
                {hintMessage}
              </div>
            )}

            {/* Hint error */}
            {hintError && (
              <div className="bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-md px-4 py-3 text-sm text-red-800 dark:text-red-300">
                {hintError}
              </div>
            )}

            {/* Display static hints */}
            {hints.length > 0 && (
              <div className="space-y-2">
                {hints.map((hint, i) => (
                  <div
                    key={i}
                    className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-md px-4 py-3 text-sm text-purple-900 dark:text-purple-200"
                  >
                    <span className="font-medium">Hint {i + 1}:</span> {hint}
                  </div>
                ))}
              </div>
            )}

            {/* Display currently STREAMING hint */}
            {streamingHint && (
              <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-md px-4 py-3 text-sm text-purple-900 dark:text-purple-200">
                <span className="font-medium">Hint {hintsUsed}:</span> {streamingHint}
                <span className="animate-pulse font-bold ml-1">_</span>
              </div>
            )}

            {/* Display solution */}
            {showSolution && solutionCode && (
              <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700 rounded-md p-4">
                <p className="text-sm font-medium text-orange-900 dark:text-orange-300 mb-2">Reference Solution:</p>
                <pre className="text-sm text-gray-900 dark:text-gray-100 font-mono whitespace-pre-wrap bg-white dark:bg-gray-800 rounded p-3 border border-gray-200 dark:border-gray-700">
                  {solutionCode}
                </pre>
              </div>
            )}

            {/* Solution fetch error */}
            {solutionError && (
              <div className="bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-md px-4 py-3 text-sm text-red-800 dark:text-red-300">
                {solutionError}
              </div>
            )}
          </div>
        </div>

        {/* Right: Editor + Console */}
        <div className={`flex flex-col overflow-hidden min-h-0 ${activeTab === 'code' ? 'flex' : 'hidden'} lg:flex`}>
          {/* Editor toolbar */}
          <div className="flex justify-between items-center px-4 py-2 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shrink-0">
            <h2 className="font-semibold text-gray-700 dark:text-gray-200 text-sm">Solution</h2>
            <div className="flex items-center gap-2">
              {isSubmitted && (
                <span className="text-sm text-green-700 dark:text-green-400 font-medium mr-2">
                  ✓ Submitted!
                </span>
              )}

              <button
                onClick={handleRun}
                disabled={pyodideLoading || isRunning}
                className={`px-4 py-1.5 rounded-md text-sm font-medium text-white transition-all ${pyodideLoading || isRunning
                  ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700'
                  }`}
              >
                {pyodideLoading ? 'Loading...' : isRunning ? 'Running...' : 'Run ▶'}
              </button>

              <button
                onClick={handleSubmit}
                disabled={!testSummary?.allPassed || isSubmitted || isSubmitting}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${testSummary?.allPassed && !isSubmitted
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                  }`}
              >
                {isSubmitting ? 'Submitting...' : isSubmitted ? 'Submitted ✓' : 'Submit'}
              </button>
            </div>
          </div>

          {/* Code editor */}
          <div className="flex-1 min-h-0">
            <CodeEditor
              initialCode={code}
              onChange={(val) => setCode(val || '')}
              className="h-full w-full overflow-hidden"
              editorTheme={theme === 'dark' ? 'vs-dark' : 'vs'}
            />
          </div>

          {/* Console output */}
          <div className="h-40 lg:h-48 border-t border-gray-200 dark:border-gray-700 shrink-0">
            <Console
              output={output}
              isLoading={pyodideLoading}
            />
          </div>
        </div>
      </main>
    </div>
  )
}