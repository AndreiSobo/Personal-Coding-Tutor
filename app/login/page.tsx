'use client'

import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { createClient } from '@/utils/supabase/client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import ThemeToggle from '@/components/ThemeToggle'
import { useTheme } from '@/components/ThemeProvider'

export default function LoginPage() {
    const supabase = createClient()
    const router = useRouter()
    const [isMounted, setIsMounted] = useState(false)
    const { theme } = useTheme()

    useEffect(() => {
        setIsMounted(true)
        // Check if user is already logged in
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
            if (session) {
                router.push('/') // Redirect to home if logged in
            }
        })

        return () => subscription.unsubscribe()
    }, [supabase, router])

    if (!isMounted) return null

    return (
        <div className="flex min-h-screen flex-col items-center justify-center py-2 bg-gray-50 dark:bg-gray-950 transition-colors">
            {/* Theme toggle — top-right corner */}
            <div className="absolute top-4 right-4">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-md p-8 bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                <h1 className="mb-4 text-2xl font-bold text-center text-gray-900 dark:text-gray-100">Welcome to PACT</h1>
                <Auth
                    supabaseClient={supabase}
                    appearance={{ theme: ThemeSupa }}
                    theme={theme === 'dark' ? 'dark' : 'default'}
                    providers={[]}
                    redirectTo={`${window.location.origin}/auth/callback`}
                />
            </div>
        </div>
    )
}