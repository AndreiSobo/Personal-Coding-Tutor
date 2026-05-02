'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import ThemeToggle from '@/components/ThemeToggle'

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'] as const

// Curated list of the most common tags from the dataset
const TAGS = [
  'Array',
  'String',
  'Hash Table',
  'Dynamic Programming',
  'Math',
  'Sorting',
  'Greedy',
  'Binary Search',
  'Two Pointers',
  'Tree',
  'Graph',
  'Matrix',
  'Bit Manipulation',
  'Depth-First Search',
  'Breadth-First Search',
  'Heap (Priority Queue)',
] as const

export default function DashboardPage() {
  const [difficulty, setDifficulty] = useState<string>('Easy')
  const [tag, setTag] = useState<string>('')
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const router = useRouter()
  const supabase = createClient()

  // Wake the PACT model container on dashboard load
  useEffect(() => {
    fetch('/api/hint/warm').catch(() => { })
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  const handleFindProblem = async () => {
    setIsSearching(true)
    setError(null)

    try {
      const { data, error: rpcError } = await supabase.rpc('get_random_unsolved_problem', {
        p_difficulty: difficulty,
        p_tag: tag || null,
      })

      if (rpcError) {
        console.error('RPC error:', rpcError)
        setError('Something went wrong. Please try again.')
        return
      }

      // RPC returns an array (SETOF), take the first result
      const problem = Array.isArray(data) ? data[0] : data

      if (!problem) {
        setError(
          tag
            ? `No unsolved ${difficulty} problems with tag "${tag}" found. Try a different combination or remove the tag filter.`
            : `You've solved all ${difficulty} problems! Try a different difficulty.`
        )
        return
      }

      // Navigate to the problem workspace
      router.push(`/problems/${problem.slug}`)
    } catch (err) {
      console.error('Error finding problem:', err)
      setError('Something went wrong. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center shadow-sm">
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">PACT</h1>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <button
            onClick={handleLogout}
            className="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Find a Problem</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">Select a difficulty and optionally a topic to get started.</p>
          </div>

          {/* Difficulty selection */}
          <div>
            <label className="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">Difficulty</label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium border transition-colors ${difficulty === d
                    ? d === 'Easy'
                      ? 'bg-green-100 dark:bg-green-900/40 border-green-500 text-green-800 dark:text-green-300'
                      : d === 'Medium'
                        ? 'bg-yellow-100 dark:bg-yellow-900/40 border-yellow-500 text-yellow-800 dark:text-yellow-300'
                        : 'bg-red-100 dark:bg-red-900/40 border-red-500 text-red-800 dark:text-red-300'
                    : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Tag selection */}
          <div>
            <label className="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
              Topic <span className="text-gray-500 dark:text-gray-400 font-normal">(optional)</span>
            </label>
            <select
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Any topic</option>
              {TAGS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-200 text-sm rounded-md px-4 py-3">
              {error}
            </div>
          )}

          {/* Find Problem button */}
          <button
            onClick={handleFindProblem}
            disabled={isSearching}
            className={`w-full py-3 rounded-md font-medium text-white transition-all ${isSearching
              ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg'
              }`}
          >
            {isSearching ? 'Searching...' : 'Find Problem →'}
          </button>
        </div>
      </main>
    </div>
  )
}