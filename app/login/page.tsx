'use client'

import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { createClient } from '@/utils/supabase/client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
    const supabase = createClient()
    const router = useRouter()
    const [isMounted, setIsMounted] = useState(false)

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
        <div className="flex min-h-screen flex-col items-center justify-center py-2">
            <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md border">
                <h1 className="mb-4 text-2xl font-bold text-center">Welcome to PACT</h1>
                <Auth
                    supabaseClient={supabase}
                    appearance={{ theme: ThemeSupa }}
                    theme="light"
                    providers={[]}
                    redirectTo={`${window.location.origin}/auth/callback`}
                />
            </div>
        </div>
    )
}