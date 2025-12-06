'use client' // This must be a client component now

import { useState } from 'react'
import CodeEditor from '@/components/CodeEditor'
import Console from '@/components/Console'
import usePyodide from '@/hooks/usePyodide'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
    const [code, setCode] = useState("print('Hello from PACT!')\n\nfor i in range(5):\n    print(f'Counting: {i}')")
    const { runPython, output, isLoading, isRunning } = usePyodide()
    const router = useRouter()
    const supabase = createClient()

    // Simple logout logic
    const handleLogout = async () => {
        await supabase.auth.signOut()
        router.push('/login')
    }

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            {/* Header */}
            <header className="bg-white border-b px-6 py-4 flex justify-between items-center shadow-sm">
                <h1 className="text-xl font-bold text-gray-800 tracking-tight">PACT Workspace</h1>
                <button
                    onClick={handleLogout}
                    className="text-sm text-red-600 hover:text-red-800 font-medium"
                >
                    Sign Out
                </button>
            </header>

            {/* Workspace Grid */}
            <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Left Col: Editor */}
                <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center">
                        <h2 className="font-semibold text-gray-700">Python Editor</h2>
                        <button
                            onClick={() => runPython(code)}
                            disabled={isLoading || isRunning}
                            className={`px-6 py-2 rounded-md font-medium text-white transition-all ${isLoading || isRunning
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-green-600 hover:bg-green-700 shadow-md hover:shadow-lg'
                                }`}
                        >
                            {isRunning ? 'Running...' : 'Run Code ▶'}
                        </button>
                    </div>
                    <CodeEditor initialCode={code} onChange={(val) => setCode(val || "")} />
                </div>

                {/* Right Col: Output */}
                <div className="flex flex-col gap-4">
                    <h2 className="font-semibold text-gray-700">Terminal</h2>
                    <Console output={output} isLoading={isLoading} />
                </div>

            </main>
        </div>
    )
}