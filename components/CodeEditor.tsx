'use client'

import Editor, { loader } from '@monaco-editor/react'
import { useEffect, useState } from 'react'

// Configure the loader explicitly to use the CDN
loader.config({
    paths: {
        vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.46.0/min/vs',
    },
})

const LG_BREAKPOINT = 1024

interface CodeEditorProps {
    initialCode?: string
    onChange?: (value: string | undefined) => void
    className?: string
    editorTheme?: string
}

export default function CodeEditor({ initialCode = "# Type your code...", onChange, className, editorTheme = 'vs-dark' }: CodeEditorProps) {
    const [isMobile, setIsMobile] = useState(false)
    const [code, setCode] = useState(initialCode)

    useEffect(() => {
        const mql = window.matchMedia(`(max-width: ${LG_BREAKPOINT - 1}px)`)
        setIsMobile(mql.matches)
        const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
        mql.addEventListener('change', handler)
        return () => mql.removeEventListener('change', handler)
    }, [])

    const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setCode(e.target.value)
        onChange?.(e.target.value)
    }

    const containerClass = className || "h-[60vh] w-full border border-gray-300 rounded-lg overflow-hidden shadow-sm"

    if (isMobile) {
        return (
            <div className={containerClass}>
                <textarea
                    value={code}
                    onChange={handleTextareaChange}
                    spellCheck={false}
                    autoCorrect="off"
                    autoCapitalize="none"
                    autoComplete="off"
                    className="w-full h-full resize-none bg-gray-950 text-green-100 font-mono text-sm p-4 outline-none leading-relaxed"
                    style={{ tabSize: 4 }}
                />
            </div>
        )
    }

    return (
        <div className={containerClass}>
            <Editor
                height="100%"
                defaultLanguage="python"
                defaultValue={initialCode}
                theme={editorTheme}
                options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    padding: { top: 16 }
                }}
                onChange={onChange}
            />
        </div>
    )
}
