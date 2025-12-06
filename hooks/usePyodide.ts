'use client'

import { useEffect, useState, useRef } from 'react'

declare global {
    interface Window {
        loadPyodide: any
    }
}

export default function usePyodide() {
    const [pyodide, setPyodide] = useState<any>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [output, setOutput] = useState<string[]>([])
    const [isRunning, setIsRunning] = useState(false)

    // Initialize Pyodide on load
    useEffect(() => {
        const initPyodide = async () => {
            try {
                // Wait for the script to load (check window object)
                while (typeof window.loadPyodide === 'undefined') {
                    await new Promise((resolve) => setTimeout(resolve, 100))
                }

                const py = await window.loadPyodide({
                    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
                })

                setPyodide(py)
                setIsLoading(false)
                console.log("Pyodide ready")
            } catch (err) {
                console.error("Failed to load Pyodide:", err)
                setIsLoading(false)
            }
        }

        initPyodide()
    }, [])

    // The Run Function
    const runPython = async (code: string) => {
        if (!pyodide) return
        setIsRunning(true)
        setOutput([]) // Clear previous output

        try {
            // 1. Redirect stdout (print) to our array
            pyodide.setStdout({
                batched: (msg: string) => {
                    setOutput((prev) => [...prev, msg])
                }
            })

            // 2. Run the code
            await pyodide.runPythonAsync(code)

        } catch (error: any) {
            setOutput((prev) => [...prev, `Error: ${error.message}`])
        } finally {
            setIsRunning(false)
        }
    }

    return { runPython, output, isLoading, isRunning }
}