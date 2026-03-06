# PACT — Personal AI Coding Tutor
## Project Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Machine Learning Pipeline](#4-machine-learning-pipeline)
5. [Database Design](#5-database-design)
6. [Data Seeding Pipeline](#6-data-seeding-pipeline)
7. [Authentication System](#7-authentication-system)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Python Execution Engine](#9-python-execution-engine)
10. [Hint API — The Backend](#10-hint-api--the-backend)
11. [Deployment](#11-deployment)
12. [Project Structure](#12-project-structure)
13. [Environment Variables](#13-environment-variables)
14. [Development Commands](#14-development-commands)
15. [Known Limitations](#15-known-limitations)

---

## 1. Project Overview

PACT (Personal AI Coding Tutor) is a full-stack web application that serves coding problems, executes Python code in the browser, validates solutions against test cases, and provides Socratic hints from a custom fine-tuned language model. The complete user flow is:

1. User logs in via Supabase authentication
2. Selects a difficulty (Easy/Medium/Hard) and optionally a topic tag
3. The system returns a random unsolved problem from a database of 2,641 LeetCode problems
4. User writes Python code in a Monaco editor
5. Clicks "Run" to validate their code against up to 10 test cases, executed client-side via Pyodide (WebAssembly)
6. If stuck, clicks "Get Hint" to receive a Socratic hint from the PACT model — a fine-tuned Qwen 2.5 7B that guides through questions rather than giving answers
7. After 3+ hints, the option to view the reference solution unlocks
8. Once all tests pass, the user submits — the problem is recorded as solved and excluded from future selections

What sets PACT apart from generic LLM-based tutors is its custom machine learning pipeline. Instead of using frontier models that tend to reveal solutions directly, PACT uses a QLoRA fine-tuned model specifically trained on a synthetic dataset of Socratic coding dialogues, evaluated using an LLM-as-judge framework to ensure it guides without leaking answers.

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | Next.js (App Router) | 16.0.7 | Full-stack React framework with server-side rendering and API routes |
| Frontend | React | 19.2.0 | UI rendering with hooks-based state management |
| Code Editor | Monaco Editor | 0.46.0+ | Browser-based code editor (same engine as VS Code) |
| Python Runtime | Pyodide | 0.25.0 | CPython compiled to WebAssembly — runs Python entirely in the browser |
| Auth & Database | Supabase | @supabase/ssr 0.8.0 | PostgreSQL database, JWT authentication, Row Level Security |
| Styling | Tailwind CSS | 3.4.17 | Utility-first CSS framework |
| Language | TypeScript | 5.x | Type-safe JavaScript across all frontend and server code |
| Hosting | Vercel | — | Deploys Next.js with automatic serverless function creation |
| AI Model | Qwen 2.5 7B Instruct (QLoRA + AWQ) | — | Fine-tuned Socratic coding tutor |
| Inference | HuggingFace Inference Endpoints | — | GPU-backed model serving (Nvidia T4, AWS eu-west-1) |
| Dataset | newfacade/LeetCodeDataset | train split | 2,641 coding problems with test cases |

---

## 3. System Architecture

The application has three distinct execution environments:

**Browser (Client)**
Everything the user interacts with runs here: the React UI, Monaco editor, Pyodide Python runtime, and test execution. The browser communicates with two backends — Supabase for data and authentication, and the Vercel serverless function for hints.

**Vercel (Server)**
When deployed, Next.js API routes (files inside `app/api/`) become serverless functions on Vercel's infrastructure. These are small, isolated programs that run on-demand on Vercel's servers. The `/api/hint` route is the critical one — it acts as a secure proxy between the browser and HuggingFace, keeping the API token hidden. The browser calls `https://personal-coding-tutor.vercel.app/api/hint`, Vercel's serverless function executes, calls HuggingFace with the secret token, and returns the result. The user never sees the HuggingFace URL or token.

**HuggingFace Inference Endpoint (GPU)**
The fine-tuned PACT model runs on a dedicated Nvidia T4 GPU instance. It accepts text prompts and returns generated text. The endpoint is set to private (requires an authentication token) and uses scale-to-zero — after 15 minutes of inactivity, the container shuts down to save costs and cold-starts on the next request.

The request flow for a hint:

```
Browser                    Vercel Serverless           HuggingFace Endpoint
  │                            │                            │
  │  POST /api/hint            │                            │
  │  {problem, code, hints}    │                            │
  │ ──────────────────────────>│                            │
  │                            │  Verify auth (Supabase)    │
  │                            │  Build ChatML prompt       │
  │                            │                            │
  │                            │  POST / (with HF_TOKEN)    │
  │                            │  {inputs: prompt}          │
  │                            │ ──────────────────────────>│
  │                            │                            │  Model inference
  │                            │   [{generated_text: "..."}]│
  │                            │ <──────────────────────────│
  │                            │                            │
  │  {hint: "..."}             │  Strip ChatML tokens       │
  │ <──────────────────────────│  Return hint               │
  │                            │                            │
  │  Display hint card         │                            │
```

---

## 4. Machine Learning Pipeline

The ML pipeline is located in the `scripts/` directory and operates independently of the web application. It was run offline to produce the model now deployed on HuggingFace.

### 4.1 Dataset Generation (`scripts/dataset/`)

High-quality Socratic tutoring data does not exist at scale, so a synthetic dataset was generated:

1. **Source Problems**: LeetCode-style coding problems provided the problem descriptions and correct solutions.
2. **Synthetic Errors**: Claude Sonnet 4.5 (Anthropic) generated realistic student errors for each problem — logic bugs, off-by-one errors, wrong data structure choices, syntax mistakes.
3. **Socratic Hints**: For each buggy code sample, Claude generated a pedagogical hint that guides the student toward identifying the issue without revealing the fix or providing code.
4. **Validation**: GPT-5.2 acted as an independent validator, checking that (a) the buggy code actually fails, (b) the hint is genuinely helpful, and (c) the hint does not leak the solution.
5. **Rejection Sampling**: Examples failing validation were discarded. The final dataset contains 227 validated examples in ChatML JSONL format, achieving a 79.1% validation pass rate.

Each training example follows this structure:

```json
{
  "messages": [
    {"role": "system", "content": "You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers."},
    {"role": "user", "content": "Problem: [description]\n\nMy code:\n```python\n[buggy code]\n```\n\n[description of issue]\n\nCan you give me a hint?"},
    {"role": "assistant", "content": "[Socratic hint — questions and guidance, no code]"}
  ]
}
```

### 4.2 Model Training (`scripts/training/`)

- **Base Model**: `Qwen/Qwen2.5-7B-Instruct` — chosen for strong coding reasoning and efficient size
- **Technique**: QLoRA (Quantized Low-Rank Adaptation) — loads the base model in 4-bit precision and trains small adapter weights, reducing VRAM requirements to fit on an RTX 4090
- **Training Infrastructure**: RunPod with RTX 4090 GPU
- **Libraries**: torch 2.4.0, transformers 4.44.0, trl 0.10.1, peft, bitsandbytes
- **Training Progress**: Loss decreased from ~1.1 to ~0.2 over the training run
- **Post-Training**: LoRA adapters merged into base model, then quantised using AWQ (Activation-aware Weight Quantisation) for faster inference. The final model is uploaded to HuggingFace Hub as `AndreiSobo/pact-qwen-tutor-awq`.

### 4.3 Evaluation (`scripts/evaluation/`)

An LLM-as-judge framework evaluates the model's responses using five metrics:

| Metric | Type | What It Measures |
|--------|------|-----------------|
| Code Leakage Rate | Binary (%) | Does the response contain executable code that solves the problem? |
| Direct Answer Rate | Binary (%) | Does the response explicitly state the fix? |
| Socratic Quality | Scale (1-5) | How well does it guide through questions? |
| Helpfulness | Scale (1-5) | Would this actually help a student? |
| Factual Correctness | Binary (%) | Is the technical content accurate? |

Results comparing the original and AWQ-quantised models:

| Model | Code Leakage | Direct Answer | Socratic Quality | Helpfulness | Factual Correctness |
|-------|-------------|---------------|------------------|-------------|-------------------|
| Original (fp16) | 0.0% | 0.0% | 4.478 | 2.521 | 82.6% |
| Quantised (AWQ) | 0.0% | 0.0% | 4.347 | 2.739 | 60.9% |

Both models achieve zero code leakage and zero direct answers, confirming the Socratic fine-tuning is effective. The quantised model trades some factual correctness for faster inference, which is acceptable for the tutoring use case.

---

## 5. Database Design

### Supabase Project

The database is a managed PostgreSQL instance hosted by Supabase.

### Tables

#### `content_problems`
Stores all 2,641 coding problems. Read-only for authenticated users (no INSERT/UPDATE/DELETE policies).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Auto-generated. Kept over LeetCode question_id for Supabase FK compatibility |
| `slug` | text (UNIQUE) | URL identifier, e.g. `two-sum`. Used for routing and as upsert conflict target |
| `question_id` | integer (indexed) | LeetCode problem number. Display ordering only |
| `difficulty` | text | CHECK constraint: `Easy`, `Medium`, `Hard` |
| `tags` | jsonb | Array of strings, e.g. `["Array", "Hash Table"]`. GIN-indexed for `@>` queries |
| `description` | text | Problem statement shown to users |
| `starter_code` | text | Pre-filled in the Monaco editor |
| `solution_code` | text | Reference solution. Never sent on initial page load |
| `entry_point` | text | e.g. `Solution().twoSum` — used by the test harness to call the user's function |
| `input_output` | jsonb | Array of `{input: string, output: string}` pairs for test validation |
| `test_code` | text | Full Python assertion code from the dataset. Kept as a server-side fallback |

#### `user_progress`
One row per solved problem per user.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → auth.users) | Enforced via RLS |
| `problem_id` | UUID (FK → content_problems) | |
| `hints_used` | integer | Default 0. How many hints before solving |
| `solved_at` | timestamptz | Default `now()` |

**Constraint**: UNIQUE(user_id, problem_id) — prevents duplicate submissions.

### RPC Function

`get_random_unsolved_problem` is a PostgreSQL function called via Supabase RPC. It accepts a difficulty and optional tag, filters out problems the current user has already solved (via a NOT IN subquery on `user_progress`), and returns one random result. Uses SECURITY DEFINER to access `user_progress` via `auth.uid()`.

### Row Level Security

| Table | Operation | Rule |
|-------|-----------|------|
| `content_problems` | SELECT | Any authenticated user |
| `content_problems` | INSERT/UPDATE/DELETE | None (service_role only) |
| `user_progress` | SELECT | `auth.uid() = user_id` |
| `user_progress` | INSERT | `auth.uid() = user_id` |
| `user_progress` | UPDATE/DELETE | None |

### Indexes

```sql
CREATE INDEX idx_problems_difficulty ON content_problems(difficulty);
CREATE INDEX idx_problems_question_id ON content_problems(question_id);
CREATE INDEX idx_problems_tags ON content_problems USING GIN(tags);
CREATE UNIQUE INDEX idx_problems_slug ON content_problems(slug);
```

---

## 6. Data Seeding Pipeline

**Script**: `scripts/database/seed_problems.py`

Loads the train split of `newfacade/LeetCodeDataset` (2,641 problems) from HuggingFace and batch-upserts them into Supabase.

**Running the seeder**:
```bash
pip install datasets supabase
export SUPABASE_URL="https://lrmzvbyyqdlgxziapmwc.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="the-service-role-key"
python scripts/database/seed_problems.py
```

**Key design decisions**:
- Batch size of 100 rows per upsert (100x fewer API calls than row-by-row)
- UPSERT on slug makes the script idempotent — safe to re-run
- Uses service_role key (not anon key) to bypass RLS for admin operations
- The `prompt` field from the dataset is not stored — only 4 distinct values exist, so the most comprehensive variant is hardcoded in the frontend

**Result**: 638 Easy, 1,397 Medium, 606 Hard problems across 20+ topic tags.

---

## 7. Authentication System

### How It Works

Supabase handles authentication using JWTs stored in HTTP cookies. The system uses three Supabase client patterns depending on where the code runs:

**Browser Client** (`utils/supabase/client.ts`): Used in `'use client'` components. Reads and writes cookies directly in the browser. Handles login, logout, and client-side data queries.

**Server Client** (`utils/supabase/server.ts`): Used in Server Components and API routes. Accesses cookies via Next.js `cookies()` API. This is what the `/api/hint` route uses to verify the user is authenticated.

**Middleware Client** (`utils/supabase/middleware.ts`): Runs on every incoming request before any page renders. Its sole job is to call `supabase.auth.getUser()`, which refreshes the session if the JWT is close to expiring. Without this, users would be silently logged out after Supabase's default 1-hour token lifetime.

### Login Flow

1. User visits `/login`, which renders the Supabase Auth UI component
2. User enters email and password
3. Supabase creates a session and redirects to `/auth/callback?code=XXX`
4. The callback route (`app/auth/callback/route.ts`) exchanges the code for a session
5. Session cookies are set in the browser
6. User is redirected to `/` (which redirects to `/dashboard`)

### Session Persistence

The middleware (`middleware.ts`) matches all dynamic routes via a regex pattern that excludes static assets. On every navigation, it refreshes the session token. This means the user stays logged in as long as they're actively using the app, without any manual token management in components.

### Logout

The dashboard's "Sign Out" button calls `supabase.auth.signOut()`, which clears the session cookies. The user is then redirected to `/login`.

---

## 8. Frontend Architecture

### Routing

The project uses Next.js App Router, where the folder structure defines the routes:

| Route | File | Type | Purpose |
|-------|------|------|---------|
| `/` | `app/page.tsx` | Server | Redirects to `/dashboard` |
| `/login` | `app/login/page.tsx` | Client | Authentication UI |
| `/dashboard` | `app/dashboard/page.tsx` | Client | Problem finder (difficulty + tag selection) |
| `/problems/[slug]` | `app/problems/[slug]/page.tsx` | Client | Problem workspace (editor, tests, hints, submit) |
| `/api/hint` | `app/api/hint/route.ts` | Server (API) | Proxies hint requests to HuggingFace |
| `/api/hint/warm` | `app/api/hint/warm/route.ts` | Server (API) | Wakes the HF container |
| `/auth/callback` | `app/auth/callback/route.ts` | Server (API) | OAuth session exchange |

### Client vs Server Components

Files marked with `'use client'` run in the browser and can use React hooks, browser APIs, and interactive features. Files without this directive are Server Components — they render on the server and send HTML to the client.

The split in this project:
- **Server**: `layout.tsx` (loads Pyodide script tag), `page.tsx` (redirect), `auth/callback/route.ts`, API routes
- **Client**: `dashboard/page.tsx`, `problems/[slug]/page.tsx`, `login/page.tsx`, `CodeEditor.tsx`, `Console.tsx`, `usePyodide.ts`

The reason for this split is that the dashboard and problem pages use React state (useState, useCallback), browser APIs (Pyodide, Monaco), and interactive event handlers — none of which work in Server Components.

### Dashboard Page (`app/dashboard/page.tsx`)

The entry point to the application after login. Presents three difficulty buttons (Easy/Medium/Hard, colour-coded green/yellow/red) and a dropdown of 16 curated topic tags. The "Find Problem" button calls the `get_random_unsolved_problem` RPC function and navigates to `/problems/[slug]`.

On mount, a fire-and-forget `fetch('/api/hint/warm')` pings the HuggingFace endpoint to wake the container, so it's ready by the time the user needs a hint.

### Problem Workspace (`app/problems/[slug]/page.tsx`)

Two-column layout: problem description + hints on the left, code editor + console on the right.

**State management** (all via React hooks):
- `problem`: fetched from Supabase on mount (excludes `solution_code`)
- `code`: current editor content
- `hints` / `hintsUsed`: array of received hints and count
- `hintError`: error message from failed hint requests
- `testSummary`: structured pass/fail results from the test runner
- `isSubmitted`: prevents re-submission
- `solutionCode` / `showSolution`: fetched on demand after 3 hints

**Key interactions**:
- "Run" → calls `runTests()` from the Pyodide hook
- "Get Hint" → calls `fetch('/api/hint')` with retry logic for cold starts
- "Show Answer" → unlocked after 3 hints, fetches `solution_code` from Supabase on demand
- "Submit" → enabled only when all tests pass, upserts into `user_progress`

### Components

**CodeEditor** (`components/CodeEditor.tsx`): Wraps `@monaco-editor/react` with Python syntax highlighting. Monaco is loaded from CDN (`cdn.jsdelivr.net`) rather than bundled, because Monaco uses Web Workers internally and Next.js bundling breaks them.

**Console** (`components/Console.tsx`): Renders an array of output strings in a terminal-style black background with green monospace text. Shows a yellow pulsing "Initialising Python Engine..." message while Pyodide loads.

---

## 9. Python Execution Engine

### Pyodide

Pyodide is CPython compiled to WebAssembly. It runs Python entirely in the browser — no server-side code execution. This means no infrastructure costs, no security risks from executing user code on a server, and instant execution with no network latency.

Pyodide is loaded from CDN in `app/layout.tsx` with `strategy="beforeInteractive"`, ensuring the script is available before React components mount.

### The `usePyodide` Hook (`hooks/usePyodide.ts`)

Manages the Pyodide lifecycle and exposes two execution modes:

**`runPython(code)`**: Free-form execution for experimentation. Captures `print()` output via stdout redirection.

**`runTests(code, entryPoint, inputOutput)`**: Validates user code against structured test cases. This is the primary execution mode in the problem workspace.

### Python Preamble

Every execution is preceded by a preamble providing the runtime environment LeetCode problems expect. This was sourced from the `prompt` column in the dataset. Analysis revealed only 4 distinct variants across all 2,641 problems, all subsets of the same comprehensive preamble. Rather than storing this per-problem, the most comprehensive variant is hardcoded as a constant.

The preamble includes:
- All standard library imports (`typing`, `collections`, `itertools`, `heapq`, `bisect`, `math`, `functools`, `operator`)
- `TreeNode` and `ListNode` class definitions
- `tree_node()` and `list_node()` helper functions (convert Python lists to tree/linked list structures)
- `is_same_tree()` and `is_same_list()` comparison utilities
- Literal aliases: `null = None`, `true = True`, `false = False`

### Test Harness

The dataset stores test cases as Python expression strings:
- Input: `"nums = [3,3], target = 6"`
- Output: `"[0, 1]"`

The harness uses `eval()` to execute these naturally:
```python
eval(f"Solution().twoSum(nums = [3,3], target = 6)")
```

A maximum of 10 test cases are run per execution (configurable via `MAX_TEST_CASES`) to keep the browser responsive. The total count is shown to the user.

### The String Escaping Bug and Fix

A critical bug was encountered during development. Test inputs containing quoted strings (e.g., `firstWord = "ij"`) broke when embedded inside triple-quoted Python strings for JSON parsing. The initial approach:
```javascript
// BROKEN — quotes in test data break the triple-quote boundary
const harness = `__test_cases = json.loads('''${testCasesJson}''')`
```

The fix uses Pyodide's JavaScript-to-Python globals bridge:
```javascript
pyodide.globals.set('__pact_test_json', JSON.stringify(testSlice))
```

This transfers data as a native JavaScript string to a Python variable, completely bypassing string escaping. The Python side reads it with `json.loads(__pact_test_json)`.

---

## 10. Hint API — The Backend

### Why a Server-Side Proxy?

The HuggingFace Inference Endpoint is private — it requires an authentication token. If the browser called HuggingFace directly, the token would be visible in network requests and anyone could extract it. Instead, the browser calls a Next.js API route on the same domain, which makes the HuggingFace call server-side.

### `/api/hint/route.ts`

This is a Next.js API route that becomes a Vercel serverless function when deployed. It:

1. **Verifies authentication**: Creates a server-side Supabase client, reads the session cookies from the incoming request, and calls `getUser()`. Returns 401 if the session is expired or missing.

2. **Parses the request**: Expects `{ problem_description, user_code, previous_hints }` in the POST body.

3. **Builds the ChatML prompt**: The model was fine-tuned on single-turn conversations (system + one user message + one assistant response). Previous hints are included as numbered context inside the user message, not as separate conversation turns, because the model was never trained on multi-turn dialogue. The prompt uses Qwen's ChatML tokens:
   ```
   <|im_start|>system
   You are PACT, a Socratic Python coding tutor...<|im_end|>
   <|im_start|>user
   Problem: [description]

   My code:
   ```python
   [code]
   ```

   [Previous hints if any]

   Can you give me a hint?<|im_end|>
   <|im_start|>assistant
   ```

4. **Calls HuggingFace**: POSTs to the endpoint root URL with `{"inputs": prompt, "parameters": {max_new_tokens: 300, temperature: 0.7, top_p: 0.9, return_full_text: false}}`. The `return_full_text: false` parameter ensures only the generated response is returned, not the entire prompt echoed back.

5. **Processes the response**: The Default Engine returns `[{"generated_text": "..."}]`. The function extracts the text, strips any trailing `<|im_end|>` tokens, and returns `{ hint: "..." }`.

6. **Error handling**: 503 → container cold-starting. 404/502 → endpoint issue. AbortError → 30-second timeout exceeded. All errors return structured JSON with descriptive messages.

### `/api/hint/warm/route.ts`

A GET endpoint that pings the HuggingFace `/health` path to wake the container. Called fire-and-forget from the dashboard on mount. Times out after 5 seconds (we don't need the result). The HuggingFace endpoint uses scale-to-zero (15 minutes idle → shutdown), so this preemptive wake-up ensures the model is ready by the time the user reaches a problem and requests a hint.

### Client-Side Retry Logic

The `handleRequestHint` function in the problem page retries up to 2 times for 503 (cold start) and 504 (timeout) errors, with increasing backoff (3 seconds, then 6 seconds). Non-retryable errors (400, 401, 502) are displayed immediately as a red error card below the hint buttons.

---

## 11. Deployment

### Vercel

The application is deployed to Vercel via GitHub integration. When code is pushed to the `main` branch, Vercel automatically builds and deploys. The production URL is `https://personal-coding-tutor.vercel.app`.

Vercel splits the Next.js codebase into two categories:
- **Static/client**: React pages, components, CSS, and client-side JavaScript are compiled into bundles and served from Vercel's CDN
- **Serverless functions**: Files inside `app/api/` become isolated functions that run on Vercel's servers on demand

Environment variables (`HF_ENDPOINT_URL`, `HF_TOKEN`) are configured in the Vercel dashboard under Settings → Environment Variables. These are only available to serverless functions and are never included in client-side bundles. Importantly, Vercel does not pick up new environment variables on existing deployments — a redeploy is required after adding or changing variables.

The `.env.local` file (used for local development) is gitignored and never reaches Vercel.

### HuggingFace Inference Endpoint

- **Model**: `AndreiSobo/pact-qwen-tutor-awq`
- **Instance**: AWS eu-west-1, Nvidia T4 (16 GB VRAM), $0.50/hour while running
- **Scale-to-zero**: After 15 minutes of no activity, the container shuts down. Cold start takes approximately 2 minutes (downloading model weights + initialising).
- **Authentication**: Private endpoint, requires HuggingFace access token in the `Authorization` header
- **API format**: Default Engine — `POST /` with `{"inputs": "...", "parameters": {...}}`, returns `[{"generated_text": "..."}]`

---

## 12. Project Structure

```
personal-coding-tutor/
├── app/                              # Next.js App Router
│   ├── layout.tsx                    # Root layout — loads Pyodide script from CDN
│   ├── page.tsx                      # / → redirects to /dashboard
│   ├── globals.css                   # Tailwind CSS base + theme variables
│   ├── api/
│   │   └── hint/
│   │       ├── route.ts              # POST /api/hint — proxies to HuggingFace (serverless function)
│   │       └── warm/
│   │           └── route.ts          # GET /api/hint/warm — wakes the HF container
│   ├── auth/
│   │   └── callback/
│   │       └── route.ts              # OAuth code → session exchange
│   ├── dashboard/
│   │   └── page.tsx                  # Problem finder (difficulty + tag → random problem)
│   ├── login/
│   │   └── page.tsx                  # Supabase Auth UI
│   └── problems/
│       └── [slug]/
│           └── page.tsx              # Problem workspace (editor, tests, hints, submit)
│
├── components/
│   ├── CodeEditor.tsx                # Monaco Editor wrapper (CDN-loaded)
│   └── Console.tsx                   # Terminal-style output display
│
├── hooks/
│   └── usePyodide.ts                 # Pyodide init, runPython, runTests, Python preamble
│
├── utils/
│   ├── formatTitle.ts                # "two-sum" → "Two Sum"
│   └── supabase/
│       ├── client.ts                 # Browser Supabase client
│       ├── server.ts                 # Server/API route Supabase client
│       └── middleware.ts             # Middleware session refresh client
│
├── scripts/
│   ├── database/
│   │   └── seed_problems.py          # HuggingFace dataset → Supabase seeding
│   ├── dataset/                      # Synthetic dataset generation scripts
│   ├── training/                     # QLoRA fine-tuning scripts
│   ├── evaluation/                   # LLM-as-judge evaluation scripts
│   ├── notebooks/                    # Local inference testing notebooks
│   ├── data/                         # JSONL datasets and intermediate files
│   ├── .env                          # API keys for ML pipeline (OpenAI, Anthropic, HF, WandB)
│   └── README.md                     # ML pipeline documentation
│
├── documentation/
│   └── documentation.md              # This file
│
├── middleware.ts                      # Root middleware — refreshes Supabase sessions on every request
├── next.config.ts                    # Next.js configuration
├── tailwind.config.ts                # Tailwind CSS configuration
├── tsconfig.json                     # TypeScript configuration
├── package.json                      # Dependencies and scripts
└── .env.local                        # Local environment variables (gitignored)
```

---

## 13. Environment Variables

### Web Application (`.env.local`)

| Variable | Scope | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Client + Server | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client + Server | Public anon key (safe to expose — security is enforced by RLS) |
| `HF_ENDPOINT_URL` | Server only | HuggingFace Inference Endpoint URL |
| `HF_TOKEN` | Server only | HuggingFace access token |

Variables prefixed with `NEXT_PUBLIC_` are embedded in the client-side JavaScript bundle and visible to users. Variables without this prefix exist only in server-side code (API routes, Server Components) and are never sent to the browser.

For production: these must be set in the Vercel dashboard (Settings → Environment Variables), not just in `.env.local`.

### ML Pipeline (`scripts/.env`)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API for dataset generation |
| `OPENAI_API_KEY` | GPT-4o for dataset validation |
| `HF_TOKEN` | Model upload to HuggingFace Hub |
| `WANDB_API_KEY` | Training run tracking (Weights & Biases) |

### Database Seeding

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin key that bypasses RLS (never in frontend code) |

---

## 14. Development Commands

```bash
# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server (requires build first)
npm start

# Type check without emitting
npx tsc --noEmit

# Seed the database
cd scripts && python database/seed_problems.py
```

---

## 15. Known Limitations


**Pyodide memory**: Pyodide has a ~10-20 MB memory limit. Long-running or memory-intensive Python programs may fail.

**No code persistence**: Refreshing the page loses the user's code. Local storage or database-backed drafts would solve this. Is considered as issues to address.

**Single file only**: The editor supports one Python file. Multi-file projects are not supported.

**Cold starts**: The HuggingFace endpoint takes ~2 minutes to cold-start. The warm-up ping on dashboard load mitigates this, but users who navigate directly to a problem URL may experience a delay on their first hint.