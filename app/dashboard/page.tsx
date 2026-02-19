'use client'

import { useState } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'

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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center shadow-sm">
        <h1 className="text-xl font-bold text-gray-800 tracking-tight">PACT</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-red-600 hover:text-red-800 font-medium"
        >
          Sign Out
        </button>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">Find a Problem</h2>
            <p className="text-gray-500 mt-1">Select a difficulty and optionally a topic to get started.</p>
          </div>

          {/* Difficulty selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Difficulty</label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium border transition-colors ${
                    difficulty === d
                      ? d === 'Easy'
                        ? 'bg-green-100 border-green-500 text-green-700'
                        : d === 'Medium'
                          ? 'bg-yellow-100 border-yellow-500 text-yellow-700'
                          : 'bg-red-100 border-red-500 text-red-700'
                      : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Tag selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Topic <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <select
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-md px-4 py-3">
              {error}
            </div>
          )}

          {/* Find Problem button */}
          <button
            onClick={handleFindProblem}
            disabled={isSearching}
            className={`w-full py-3 rounded-md font-medium text-white transition-all ${
              isSearching
                ? 'bg-gray-400 cursor-not-allowed'
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