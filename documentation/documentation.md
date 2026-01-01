# PACT - Personal AI Coding Tutor
## Project Documentation

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Frontend Architecture](#frontend-architecture)
4. [Authentication & Database](#authentication--database)
5. [Component Deep Dive](#component-deep-dive)
6. [Middleware & Request Handling](#middleware--request-handling)
7. [Styling System](#styling-system)
8. [Python Execution Engine](#python-execution-engine)
9. [Project Structure](#project-structure)
10. [Future Considerations](#future-considerations)

---

## Project Overview

**PACT (Personal AI Coding Tutor)** is a web-based interactive coding environment designed to help users learn programming through a custom fine-tuned small language model. The platform enables users to:
- Write and execute Python code directly in the browser
- View real-time output in a terminal-style console
- Authenticate securely with persistent sessions
- Access their personalized coding workspace

The frontend serves as an interactive IDE where users can practice coding problems, receive AI guidance, and iterate on solutions—all without needing local Python installation.

---

## Technology Stack

### Core Framework: Next.js 16
**Why Next.js?**
- **Server-Side Rendering (SSR)**: Enables fast initial page loads and SEO optimization
- **App Router**: Modern file-based routing with React Server Components support
- **API Routes**: Built-in backend endpoints for authentication callbacks
- **Middleware Support**: Edge-compatible request interception for auth checks
- **TypeScript Support**: First-class TypeScript integration out of the box

### Runtime: Node.js
**Why Node.js?**
- Required by Next.js for server-side operations
- Handles server components, middleware execution, and build processes
- Provides npm ecosystem access for dependency management
- Enables serverless function deployment on platforms like Vercel

### UI Library: React 19
**Why React?**
- Component-based architecture for reusable UI elements
- Virtual DOM for efficient updates
- Hooks for state management (useState, useEffect, useRef)
- Client/Server component distinction in Next.js App Router
- Large ecosystem and community support

---

## Frontend Architecture

### App Router Structure

The project uses Next.js 16's **App Router** (not Pages Router), which organizes routes based on folder structure:

```
app/
├── layout.tsx          # Root layout (wraps all pages)
├── page.tsx            # Homepage route (/)
├── globals.css         # Global styles
├── auth/
│   └── callback/
│       └── route.ts    # OAuth callback handler (API route)
├── dashboard/
│   └── page.tsx        # Protected workspace (/dashboard)
└── login/
    └── page.tsx        # Login page (/login)
```

#### Key Routes:
- **`/`** ([page.tsx](app/page.tsx)): Landing page (currently default Next.js template)
- **`/login`** ([login/page.tsx](app/login/page.tsx)): Authentication UI with Supabase Auth
- **`/dashboard`** ([dashboard/page.tsx](app/dashboard/page.tsx)): Main coding workspace (protected route)
- **`/auth/callback`** ([auth/callback/route.ts](app/auth/callback/route.ts)): Handles OAuth redirect and session exchange

### Client vs. Server Components

**Server Components (Default):**
- [layout.tsx](app/layout.tsx): Renders on server, loads Pyodide script
- Authentication checks in middleware

**Client Components (`'use client'`):**
- [dashboard/page.tsx](app/dashboard/page.tsx): Uses React hooks (useState, custom hooks)
- [login/page.tsx](app/login/page.tsx): Interactive authentication UI
- [CodeEditor.tsx](components/CodeEditor.tsx): Monaco Editor requires browser APIs
- [usePyodide.ts](hooks/usePyodide.ts): Manages browser-based Python runtime

**Why This Split?**
- Server components reduce bundle size and enable fast initial renders
- Client components handle interactivity, state, and browser-specific APIs
- Authentication can be checked server-side before sending HTML to client

---

## Authentication & Database

### Supabase: The Backend-as-a-Service Choice

**Why Supabase?**
Supabase was chosen over custom backend solutions for several reasons:

1. **Authentication Out-of-the-Box**
   - Pre-built email/password authentication
   - OAuth providers (Google, GitHub, etc.) with minimal config
   - JWT-based session management
   - Row-level security (RLS) for database queries

2. **PostgreSQL Database**
   - Scalable relational database
   - Real-time subscriptions (future feature: collaborative coding)
   - Built-in user tables and auth schema

3. **No Backend Maintenance**
   - No need to build custom auth endpoints
   - Automatic session refresh and expiration handling
   - HTTPS, security patches, and infrastructure managed by Supabase

4. **Developer Experience**
   - Simple JavaScript SDK (`@supabase/supabase-js`)
   - TypeScript support
   - Works seamlessly with Next.js SSR and middleware

### Supabase Integration Architecture

The project uses **three Supabase client patterns** based on execution context:

#### 1. Browser Client ([utils/supabase/client.ts](utils/supabase/client.ts))
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
    return createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
}
```

**Used in:** Client Components (login page, dashboard logout)

**How it works:**
- Reads/writes cookies directly in the browser
- Uses public anonymous key (safe to expose)
- Handles auth state changes with `onAuthStateChange()`

**Example Usage:**
```tsx
// In login/page.tsx
const supabase = createClient()
const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
    if (session) {
        router.push('/') // Redirect on login
    }
})
```

#### 2. Server Client ([utils/supabase/server.ts](utils/supabase/server.ts))
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
    const cookieStore = await cookies()
    
    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() { return cookieStore.getAll() },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) =>
                        cookieStore.set(name, value, options)
                    )
                }
            }
        }
    )
}
```

**Used in:** Server Components, API Routes, Server Actions

**How it works:**
- Accesses Next.js cookies() API (server-side only)
- Can read user session during SSR
- Used in [auth/callback/route.ts](app/auth/callback/route.ts) to exchange OAuth code for session

**Example Usage:**
```typescript
// In auth/callback/route.ts
const supabase = await createClient()
const { error } = await supabase.auth.exchangeCodeForSession(code)
```

#### 3. Middleware Client ([utils/supabase/middleware.ts](utils/supabase/middleware.ts))
```typescript
export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({ request: { headers: request.headers } })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() { return request.cookies.getAll() },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => {
                        request.cookies.set(name, value)
                        response.cookies.set(name, value, options)
                    })
                }
            }
        }
    )

    await supabase.auth.getUser() // Refreshes session if expired
    return response
}
```

**Used in:** [middleware.ts](middleware.ts)

**How it works:**
- Runs on **every request** before it reaches pages
- Reads session cookies from incoming request
- Calls `getUser()` to refresh expired sessions
- Sets updated cookies in response
- Ensures user session stays alive across navigation

### Authentication Flow

#### Login Flow:
1. User visits `/login`
2. [login/page.tsx](app/login/page.tsx) renders Supabase `<Auth>` component
3. User submits email/password
4. Supabase API creates session and sends magic link or OAuth redirect
5. User clicks link → redirected to `/auth/callback?code=XXX`
6. [auth/callback/route.ts](app/auth/callback/route.ts) exchanges code for session
7. Session cookies are set
8. User redirected to `/` (or `/dashboard`)

#### Session Validation:
1. User navigates to any route
2. [middleware.ts](middleware.ts) intercepts request
3. [updateSession()](utils/supabase/middleware.ts) refreshes session if needed
4. Updated cookies sent back to browser
5. Page renders with valid session

#### Logout Flow:
1. User clicks "Sign Out" button in dashboard
2. `supabase.auth.signOut()` called (client-side)
3. Session cookies cleared
4. User redirected to `/login`

---

## Component Deep Dive

### 1. CodeEditor Component ([components/CodeEditor.tsx](components/CodeEditor.tsx))

**Purpose:** Provides a Monaco Editor instance for writing Python code

**Key Implementation Details:**

```tsx
import Editor, { loader } from '@monaco-editor/react'

loader.config({
    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.46.0/min/vs' }
})
```

**Why CDN Configuration?**
- Monaco Editor uses Web Workers internally
- Next.js tries to bundle worker files → causes errors
- Using CDN bypasses Next.js bundling for worker scripts
- Ensures editor loads correctly in production

**Props:**
- `initialCode`: Default Python code shown on load
- `onChange`: Callback fired when user types (updates parent state)

**Monaco Options:**
```tsx
options={{
    minimap: { enabled: false },        // Disables code minimap
    fontSize: 14,                        // Readable text size
    scrollBeyondLastLine: false,         // No empty space at bottom
    automaticLayout: true,               // Auto-resize on container change
    padding: { top: 16 }                 // Top padding for aesthetics
}}
```

**Tailwind Styling:**
- `h-[60vh]`: 60% viewport height for vertical space
- `border border-gray-300 rounded-lg`: Clean bordered container
- `shadow-sm`: Subtle shadow for depth

### 2. Console Component ([components/Console.tsx](components/Console.tsx))

**Purpose:** Displays Python execution output in terminal style

**Props:**
- `output: string[]`: Array of output lines from Python execution
- `isLoading?: boolean`: Shows loading state while Pyodide initializes

**Styling Choices:**
```tsx
className="bg-black text-green-400 font-mono"
```
- **Black background**: Classic terminal aesthetic
- **Green text**: Retro terminal look (like old CRT monitors)
- **Monospace font**: Aligns code output properly

**Loading State:**
```tsx
{isLoading ? (
    <div className="text-yellow-500 animate-pulse">Initializing Python Engine...</div>
) : ...}
```
- Shows yellow pulsing text while Pyodide loads (~30-50 MB download)

**Output Rendering:**
```tsx
{output.map((line, i) => (
    <div key={i} className="whitespace-pre-wrap">{line}</div>
))}
```
- `whitespace-pre-wrap`: Preserves spaces/tabs from Python print statements
- Maps each line separately for proper formatting

### 3. Dashboard Page ([app/dashboard/page.tsx](app/dashboard/page.tsx))

**Purpose:** Main coding workspace where users write and run Python

**State Management:**
```tsx
const [code, setCode] = useState("print('Hello from PACT!')\n...")
const { runPython, output, isLoading, isRunning } = usePyodide()
```

**Component Structure:**
```
Header (logout button)
└── Main Grid
    ├── Left Column: CodeEditor + Run Button
    └── Right Column: Console
```

**Run Button Logic:**
```tsx
<button
    onClick={() => runPython(code)}
    disabled={isLoading || isRunning}
    className={isLoading || isRunning ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'}
>
    {isRunning ? 'Running...' : 'Run Code ▶'}
</button>
```
- Disables while Pyodide is loading or code is running
- Shows visual feedback with text and color changes

**Grid Layout:**
```tsx
<main className="grid grid-cols-1 lg:grid-cols-2 gap-6">
```
- **Mobile (< 1024px)**: Single column (editor above console)
- **Desktop (≥ 1024px)**: Two columns side-by-side
- `gap-6`: 1.5rem spacing between columns

### 4. Login Page ([app/login/page.tsx](app/login/page.tsx))

**Purpose:** Handles user authentication with Supabase Auth UI

**Hydration Fix:**
```tsx
const [isMounted, setIsMounted] = useState(false)
useEffect(() => { setIsMounted(true) }, [])
if (!isMounted) return null
```
- Prevents React hydration mismatch
- Auth component uses browser APIs not available during SSR
- Waits for client-side mount before rendering

**Auth State Listener:**
```tsx
useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
        if (session) router.push('/')
    })
    return () => subscription.unsubscribe()
}, [])
```
- Listens for login events
- Automatically redirects to home when user logs in
- Cleans up subscription on unmount

**Supabase Auth Component:**
```tsx
<Auth
    supabaseClient={supabase}
    appearance={{ theme: ThemeSupa }}
    theme="light"
    providers={[]}
    redirectTo={`${window.location.origin}/auth/callback`}
/>
```
- Pre-built email/password form
- `providers={[]}`: Disables OAuth (can add `['google', 'github']` later)
- Redirects to callback route after authentication

---

## Middleware & Request Handling

### Next.js Middleware ([middleware.ts](middleware.ts))

**Purpose:** Intercepts all requests to refresh user sessions automatically

```typescript
export async function middleware(request: NextRequest) {
    return await updateSession(request)
}

export const config = {
    matcher: [
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
```

**How Middleware Works:**
1. **Runs on Edge Runtime**: Near-instant execution
2. **Executes Before Pages**: Can redirect or modify requests
3. **Path Matching**: Only runs on dynamic routes (excludes static assets)
4. **Cookie Management**: Can read and set cookies in request/response

**Matcher Explanation:**
- `(?!_next/static|_next/image|favicon.ico)`: Excludes Next.js internal files
- `(?!.*\\.(?:svg|png|jpg|...))`: Excludes image files
- Runs on: `/`, `/login`, `/dashboard`, `/api/*`, etc.

**Why This Is Critical:**
- Supabase sessions expire after 1 hour by default
- Middleware calls `supabase.auth.getUser()` → triggers refresh
- User stays logged in across page navigation
- No manual token refresh needed in components

**Without Middleware:**
- User would be logged out after 1 hour
- Would need manual refresh logic in every page
- Worse user experience

---

## Styling System

### Tailwind CSS Configuration

#### Why Tailwind?
- **Utility-First**: No need to write custom CSS classes
- **Responsive Design**: Built-in breakpoints (`sm:`, `md:`, `lg:`, `xl:`)
- **Consistency**: Enforced design system (spacing, colors, typography)
- **Performance**: Purges unused styles in production
- **Developer Velocity**: Rapid prototyping without context switching

#### Configuration ([tailwind.config.ts](tailwind.config.ts))
```typescript
content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./utils/**/*.{js,ts,jsx,tsx,mdx}",
]
```
- Tells Tailwind to scan these directories for class names
- Only includes CSS for classes actually used
- Reduces bundle size significantly

#### Global Styles ([app/globals.css](app/globals.css))
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: #ffffff;
  --foreground: #171717;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}
```
- Includes Tailwind's layers (base, components, utilities)
- Defines CSS variables for theming
- Supports dark mode via system preferences

### Common Tailwind Patterns Used

#### Layout:
```tsx
className="min-h-screen flex flex-col"
```
- `min-h-screen`: Minimum 100vh height
- `flex flex-col`: Vertical flexbox layout

#### Responsive Grid:
```tsx
className="grid grid-cols-1 lg:grid-cols-2 gap-6"
```
- Mobile: 1 column
- Desktop (1024px+): 2 columns
- Gap: 1.5rem spacing

#### Button States:
```tsx
className="bg-green-600 hover:bg-green-700 shadow-md hover:shadow-lg transition-all"
```
- Base: Green background with medium shadow
- Hover: Darker green with larger shadow
- `transition-all`: Smooth animation

#### Terminal Styling:
```tsx
className="bg-black text-green-400 font-mono overflow-y-auto"
```
- Black background, green text, monospace font
- `overflow-y-auto`: Scrollable if content exceeds height

---

## Python Execution Engine

### Pyodide: Python in the Browser

**What is Pyodide?**
- CPython compiled to WebAssembly (WASM)
- Runs Python entirely in browser (no server needed)
- Includes NumPy, Pandas, Matplotlib, and 100+ packages
- ~30-50 MB download (loads once, cached by browser)

**Why Pyodide?**
- **Security**: No server-side code execution risk
- **Cost**: No backend infrastructure for running Python
- **Latency**: Instant execution (no network round-trip)
- **Offline**: Works without internet after initial load
- **Scalability**: Runs on user's machine

### Loading Pyodide ([app/layout.tsx](app/layout.tsx))
```tsx
<Script
    src="https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js"
    strategy="beforeInteractive"
/>
```
- `strategy="beforeInteractive"`: Loads before React hydration
- Ensures `window.loadPyodide` is available when components mount

### usePyodide Hook ([hooks/usePyodide.ts](hooks/usePyodide.ts))

**Purpose:** Manages Pyodide lifecycle and code execution

**Initialization:**
```tsx
useEffect(() => {
    const initPyodide = async () => {
        while (typeof window.loadPyodide === 'undefined') {
            await new Promise((resolve) => setTimeout(resolve, 100))
        }
        const py = await window.loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
        })
        setPyodide(py)
        setIsLoading(false)
    }
    initPyodide()
}, [])
```
- Polls for `loadPyodide` function (from CDN script)
- Downloads Pyodide runtime (~30 MB)
- Sets `isLoading` to false when ready

**Code Execution:**
```tsx
const runPython = async (code: string) => {
    if (!pyodide) return
    setIsRunning(true)
    setOutput([])

    try {
        pyodide.setStdout({
            batched: (msg: string) => {
                setOutput((prev) => [...prev, msg])
            }
        })
        await pyodide.runPythonAsync(code)
    } catch (error: any) {
        setOutput((prev) => [...prev, `Error: ${error.message}`])
    } finally {
        setIsRunning(false)
    }
}
```

**How It Works:**
1. **Stdout Redirection**: Captures `print()` statements
2. **Async Execution**: Uses `runPythonAsync()` for async code support
3. **Error Handling**: Catches Python exceptions and displays them
4. **State Updates**: Appends output lines to state array

**Example Execution:**
```python
print('Hello')
for i in range(3):
    print(i)
```

Output array:
```javascript
['Hello\n', '0\n', '1\n', '2\n']
```

---

## Project Structure

### Directory Layout

```
personal-coding-tutor/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # Root layout (loads Pyodide)
│   ├── page.tsx              # Homepage (landing)
│   ├── globals.css           # Global styles + Tailwind
│   ├── auth/
│   │   └── callback/
│   │       └── route.ts      # OAuth callback handler
│   ├── dashboard/
│   │   └── page.tsx          # Main workspace (protected)
│   └── login/
│       └── page.tsx          # Login UI
│
├── components/               # Reusable React components
│   ├── CodeEditor.tsx        # Monaco editor wrapper
│   └── Console.tsx           # Terminal output display
│
├── hooks/                    # Custom React hooks
│   └── usePyodide.ts         # Pyodide initialization & execution
│
├── utils/                    # Helper functions
│   └── supabase/
│       ├── client.ts         # Browser Supabase client
│       ├── middleware.ts     # Middleware Supabase client
│       └── server.ts         # Server Supabase client
│
├── documentation/
│   └── documentation.md      # This file
│
├── public/                   # Static assets
│
├── middleware.ts             # Route middleware (session refresh)
├── next.config.ts            # Next.js configuration
├── tailwind.config.ts        # Tailwind configuration
├── tsconfig.json             # TypeScript configuration
├── package.json              # Dependencies
└── package-lock.json         # Locked dependency versions
```

### Key Files Explained

| File | Purpose |
|------|---------|
| [middleware.ts](middleware.ts) | Intercepts requests to refresh Supabase sessions |
| [app/layout.tsx](app/layout.tsx) | Root layout, loads Pyodide script |
| [app/dashboard/page.tsx](app/dashboard/page.tsx) | Main workspace with editor and console |
| [components/CodeEditor.tsx](components/CodeEditor.tsx) | Monaco editor for Python code |
| [components/Console.tsx](components/Console.tsx) | Terminal-style output display |
| [hooks/usePyodide.ts](hooks/usePyodide.ts) | Manages Pyodide runtime and execution |
| [utils/supabase/client.ts](utils/supabase/client.ts) | Browser-side Supabase client |
| [utils/supabase/server.ts](utils/supabase/server.ts) | Server-side Supabase client |
| [utils/supabase/middleware.ts](utils/supabase/middleware.ts) | Middleware session refresh logic |

---

## Future Considerations

### Potential Enhancements

1. **AI Model Integration**
   - Add API route to call custom fine-tuned model
   - Display AI hints/suggestions in sidebar
   - Track user progress and adapt difficulty

2. **Code Persistence**
   - Save user code to Supabase database
   - Load previous sessions on login
   - Version history with undo/redo

3. **Collaborative Features**
   - Real-time code sharing (Supabase Realtime)
   - Multiplayer debugging sessions
   - Instructor/student mode

4. **Enhanced Python Support**
   - Install additional Pyodide packages dynamically
   - Support for file uploads (CSV, images)
   - Matplotlib chart rendering in console

5. **Testing & Validation**
   - Unit test runner for code challenges
   - Automated test case validation
   - Progress tracking and achievements

6. **Protected Routes**
   - Add server-side auth checks in dashboard
   - Redirect unauthorized users to login
   - Role-based access control (admin, student, instructor)

### Scalability Notes

**Current Limitations:**
- Pyodide has ~10-20 MB memory limit
- Cannot run long-running Python processes
- No multi-file project support

**When to Migrate to Backend Python:**
- If users need GPU acceleration (ML models)
- If code needs to persist longer than browser session
- If security requires sandboxed execution
- If packages exceed Pyodide's available libraries

---

## Development Commands

```bash
# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

---

## Environment Variables Required

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Store these in `.env.local` (not committed to git).

---

## Conclusion

This project demonstrates a modern, production-ready Next.js application with:
- **Authentication**: Supabase for secure user management
- **Interactive IDE**: Monaco Editor + Pyodide for browser-based Python
- **Responsive Design**: Tailwind CSS with mobile-first approach
- **SSR & Middleware**: Next.js App Router for optimal performance
- **Type Safety**: Full TypeScript coverage

The architecture prioritizes developer experience, user security, and future extensibility—making it an excellent reference for building educational coding platforms.
