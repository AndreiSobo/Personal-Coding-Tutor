interface ConsoleProps {
    output: string[]
    isLoading?: boolean
    className?: string
}

export default function Console({ output, isLoading, className }: ConsoleProps) {
    return (
        <div className={className || "bg-gray-950 text-green-400 font-mono p-4 h-full overflow-y-auto border-t border-gray-700"}>
            <div className="text-gray-500 mb-2 border-b border-gray-700 pb-1 text-xs uppercase tracking-wide">Output Console</div>

            {isLoading ? (
                <div className="text-yellow-400 animate-pulse">Initializing Python Engine...</div>
            ) : (
                <>
                    {output.map((line, i) => (
                        <div key={i} className="whitespace-pre-wrap">{line}</div>
                    ))}
                    {output.length === 0 && <span className="text-gray-500 italic">Ready to execute.</span>}
                </>
            )}
        </div>
    )
}