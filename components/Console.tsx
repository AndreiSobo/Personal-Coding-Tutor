interface ConsoleProps {
    output: string[]
    isLoading?: boolean
    className?: string
}

export default function Console({ output, isLoading, className }: ConsoleProps) {
    return (
        <div className={className || "bg-black text-green-400 font-mono p-4 rounded-lg h-[60vh] overflow-y-auto border border-gray-700 shadow-inner"}>
            <div className="text-gray-500 mb-2 border-b border-gray-700 pb-1">Output Console</div>

            {isLoading ? (
                <div className="text-yellow-500 animate-pulse">Initializing Python Engine...</div>
            ) : (
                <>
                    {output.map((line, i) => (
                        <div key={i} className="whitespace-pre-wrap">{line}</div>
                    ))}
                    {output.length === 0 && <span className="text-gray-600 italic">Ready to execute.</span>}
                </>
            )}
        </div>
    )
}