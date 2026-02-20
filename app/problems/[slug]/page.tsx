'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useParams, useRouter } from 'next/navigation'
import CodeEditor from '@/components/CodeEditor'
import Console from '@/components/Console'
import usePyodide from '@/hooks/usePyodide'
import { formatTitle } from '@/utils/formatTitle'

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

  // Problem state
  const [problem, setProblem] = useState<Problem | null>(null)
  const [loading, setLoading] = useState(true)
  const [code, setCode] = useState('')

  // Pyodide
  const { runTests, output, isLoading: pyodideLoading, isRunning, testSummary } = usePyodide()

  // Submit state
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Hint state
  const [hints, setHints] = useState<string[]>([])
  const [hintsUsed, setHintsUsed] = useState(0)
  const [isRequestingHint, setIsRequestingHint] = useState(false)
  const [hintError, setHintError] = useState<string | null>(null)

  // Show Answer state
  const [solutionCode, setSolutionCode] = useState<string | null>(null)
  const [showSolution, setShowSolution] = useState(false)
  const canShowAnswer = hintsUsed >= 3

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
    }

    if (slug) fetchProblem()
  }, [slug])

  // Run tests

  const handleRun = useCallback(async () => {
    if (!problem) return
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
  // Calls /api/hint (server-side route) which forwards to HuggingFace.

  const handleRequestHint = useCallback(async () => {
    if (!problem || isRequestingHint) return
    setIsRequestingHint(true)
    setHintError(null)

    // Retry logic for cold starts (503) and timeouts (504)
    const MAX_RETRIES = 2
    let lastError = ''

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        const response = await fetch('/api/hint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            problem_description: problem.description,
            user_code: code,
            previous_hints: hints,
          }),
        })

        const data = await response.json()

        if (response.ok && data.hint) {
          setHints((prev) => [...prev, data.hint])
          setHintsUsed((prev) => prev + 1)
          setIsRequestingHint(false)
          return
        }

        // Retryable errors: cold start or timeout
        if (response.status === 503 || response.status === 504) {
          lastError = data.error || 'Model is warming up...'
          if (attempt < MAX_RETRIES) {
            await new Promise((r) => setTimeout(r, 3000 * (attempt + 1)))
            continue
          }
        }

        // Non-retryable error
        lastError = data.error || 'Failed to get hint.'
        break
      } catch (err) {
        lastError = 'Network error. Please check your connection.'
        if (attempt < MAX_RETRIES) {
          await new Promise((r) => setTimeout(r, 2000))
          continue
        }
        break
      }
    }

    setHintError(lastError)
    setIsRequestingHint(false)
  }, [problem, code, hints, isRequestingHint])

  // Show answer

  const handleShowAnswer = useCallback(async () => {
    if (!problem || !canShowAnswer) return

    if (!solutionCode) {
      const { data, error } = await supabase
        .from('content_problems')
        .select('solution_code')
        .eq('id', problem.id)
        .single()

      if (error || !data) {
        console.error('Failed to fetch solution:', error)
        return
      }

      setSolutionCode(data.solution_code)
    }

    setShowSolution(true)
  }, [problem, canShowAnswer, solutionCode, supabase])

  // Render

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading problem...</p>
      </div>
    )
  }

  if (!problem) return null

  const difficultyColor =
    problem.difficulty === 'Easy'
      ? 'text-green-600 bg-green-50'
      : problem.difficulty === 'Medium'
        ? 'text-yellow-600 bg-yellow-50'
        : 'text-red-600 bg-red-50'

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center shadow-sm shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Dashboard
          </button>
          <h1 className="text-lg font-bold text-gray-800">{formatTitle(problem.slug)}</h1>
          <span className={`text-xs font-medium px-2 py-1 rounded ${difficultyColor}`}>
            {problem.difficulty}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {problem.tags.map((tag) => (
            <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              {tag}
            </span>
          ))}
        </div>
      </header>

      {/* Workspace */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-0 overflow-hidden min-h-0">
        {/* Left: Problem description + Hints */}
        <div className="border-r border-gray-200 overflow-y-auto p-6 flex flex-col">
          {/* Description */}
          <div className="flex-1">
            <h2 className="text-lg font-semibold mb-4">Problem Description</h2>
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed bg-white p-4 rounded border">
              {problem.description}
            </pre>
          </div>

          {/* Hints section */}
          <div className="mt-6 border-t pt-4 space-y-3">
            <div className="flex items-center gap-3">
              <button
                onClick={handleRequestHint}
                disabled={isRequestingHint || isSubmitted}
                className={`px-4 py-2 text-sm rounded-md font-medium transition-colors ${
                  isRequestingHint || isSubmitted
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                }`}
              >
                {isRequestingHint
                  ? 'PACT is thinking...'
                  : `Get Hint (${hintsUsed} used)`}
              </button>

              <button
                onClick={handleShowAnswer}
                disabled={!canShowAnswer || isSubmitted}
                className={`px-4 py-2 text-sm rounded-md font-medium transition-colors ${
                  canShowAnswer && !isSubmitted
                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
                title={!canShowAnswer ? `Use ${3 - hintsUsed} more hint(s) to unlock` : undefined}
              >
                {canShowAnswer ? 'Show Answer' : `Show Answer (${3 - hintsUsed} more hints needed)`}
              </button>
            </div>

            {/* Hint error */}
            {hintError && (
              <div className="bg-red-50 border border-red-200 rounded-md px-4 py-3 text-sm text-red-700">
                {hintError}
              </div>
            )}

            {/* Display hints */}
            {hints.length > 0 && (
              <div className="space-y-2">
                {hints.map((hint, i) => (
                  <div
                    key={i}
                    className="bg-purple-50 border border-purple-200 rounded-md px-4 py-3 text-sm text-purple-800"
                  >
                    <span className="font-medium">Hint {i + 1}:</span> {hint}
                  </div>
                ))}
              </div>
            )}

            {/* Display solution */}
            {showSolution && solutionCode && (
              <div className="bg-orange-50 border border-orange-200 rounded-md p-4">
                <p className="text-sm font-medium text-orange-800 mb-2">Reference Solution:</p>
                <pre className="text-sm text-gray-800 font-mono whitespace-pre-wrap bg-white rounded p-3 border">
                  {solutionCode}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Right: Editor + Console */}
        <div className="flex flex-col overflow-hidden min-h-0">
          {/* Editor toolbar */}
          <div className="flex justify-between items-center px-4 py-2 bg-white border-b shrink-0">
            <h2 className="font-semibold text-gray-700 text-sm">Solution</h2>
            <div className="flex items-center gap-2">
              {isSubmitted && (
                <span className="text-sm text-green-600 font-medium mr-2">
                  ✓ Submitted!
                </span>
              )}

              <button
                onClick={handleRun}
                disabled={pyodideLoading || isRunning}
                className={`px-4 py-1.5 rounded-md text-sm font-medium text-white transition-all ${
                  pyodideLoading || isRunning
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {pyodideLoading ? 'Loading...' : isRunning ? 'Running...' : 'Run ▶'}
              </button>

              <button
                onClick={handleSubmit}
                disabled={!testSummary?.allPassed || isSubmitted || isSubmitting}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                  testSummary?.allPassed && !isSubmitted
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
            />
          </div>

          {/* Console output */}
          <div className="h-48 border-t shrink-0">
            <Console
              output={output}
              isLoading={pyodideLoading}
              className="bg-black text-green-400 font-mono p-4 h-full overflow-y-auto"
            />
          </div>
        </div>
      </main>
    </div>
  )
}