'use client'

import Editor, { loader } from '@monaco-editor/react'

// 1. Configure the loader explicitly to use the CDN
// This prevents Next.js from intercepting the internal worker files
loader.config({
    paths: {
        vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.46.0/min/vs',
    },
})

interface CodeEditorProps {
    initialCode?: string
    onChange?: (value: string | undefined) => void
    className?: string
    editorTheme?: string
}

export default function CodeEditor({ initialCode = "# Type your code...", onChange, className, editorTheme = 'vs-dark' }: CodeEditorProps) {
    return (
        <div className={className || "h-[60vh] w-full border border-gray-300 rounded-lg overflow-hidden shadow-sm"}>
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