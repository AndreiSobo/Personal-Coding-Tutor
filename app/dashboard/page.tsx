import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
    const supabase = await createClient()

    // 1. Check if user is logged in
    const {
        data: { user },
    } = await supabase.auth.getUser()

    if (!user) {
        return redirect('/login')
    }

    // 2. Define the Sign Out Action
    const signOut = async () => {
        'use server'
        const supabase = await createClient()
        await supabase.auth.signOut()
        return redirect('/login')
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center p-10">
            <div className="max-w-md w-full bg-white p-8 rounded-lg shadow-md border text-center">
                <h1 className="text-3xl font-bold mb-4">Dashboard</h1>

                <div className="bg-blue-50 p-4 rounded-md mb-6">
                    <p className="text-gray-600">Logged in as:</p>
                    <span className="font-mono text-blue-600 font-bold">{user.email}</span>
                </div>

                {/* 3. The Sign Out Button Form */}
                <form action={signOut}>
                    <button
                        className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded w-full transition duration-150"
                        type="submit"
                    >
                        Sign Out
                    </button>
                </form>
            </div>
        </div>
    )
}