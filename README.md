# PACT - Personal AI Coding Tutor

Coding assistants like Copilot are trained to show the answer to a coding question. This can reduce user involvment in the learning process. Coding platforms like LeetCode or HackerRank offer coding problems and the environment for it, but only test user answers on a pass/fail condition. For my Final Year Project I decided to build a webapp that fills the gap between these platforms.

PACT is a modern web-based interactive coding environment that helps users learn programming through an AI-powered tutor (PACT). PACT uses a custom fine-tuned Qwen 2.5 model to provide Socratic guidance - hints and leading questions - rather than direct answers, promoting learning.

The WebApp can be accessed here: https://personal-coding-tutor.vercel.app/

## Features

- **Browser-Based Python Execution**: Run Python code locally using Pyodide (WebAssembly).
- **AI Socratic Tutor**: Custom model provides hints based on current code context.
- **Monaco Code Editor**: Professional IDE experience.
- **Secure Authentication**: User management powered by Supabase.
- **No Backend Execution**: Code runs entirely in the browser for privacy and speed

## Technology Stack

### Web Application
- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, Tailwind CSS
- **Backend/Auth**: Supabase (PostgreSQL)
- **Runtime**: Pyodide (CPython in WASM)

### Machine Learning Pipeline
- **Model**: Qwen 2.5 7B Instruct (Fine-tuned via QLoRA)
- **Data**: Synthetic Socratic dataset generated via Claude/GPT-4
- **Inference**: Hugging Face Inference Endpoints

## Project Structure

```
personal-coding-tutor/
├── app/                  # Next.js App Router (Frontend)
│   ├── dashboard/        # Main coding workspace
│   ├── login/            # Authentication
│   └── api/              # API routes for inference proxy
├── components/           # React components (Editor, Console)
├── hooks/                # Custom hooks (Pyodide runtime)
├── scripts/              # ML Pipeline (Dataset, Training, Eval)
│   ├── dataset/          # Synthetic data generation
│   ├── training/         # QLoRA fine-tuning scripts
│   └── evaluation/       # LLM-as-a-judge benchmarking
├── utils/                # Utilities (Supabase client)
└── documentation/        # Detailed architecture docs
```

## Documentation

For detailed information on architecture, ML training methodology, and design decisions see [documentation/documentation.md](documentation/documentation.md).

For instructions on reproducing the ML model training see [scripts/README.md](scripts/README.md).

