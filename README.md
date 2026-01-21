# PACT - Personal AI Coding Tutor

A modern web-based interactive coding environment that helps users learn programming through an AI-powered tutor. Write and execute Python code directly in your browser with real-time output and feedback.

The WebApp can be accessed here: https://personal-coding-tutor.vercel.app/

## Features

- **Browser-Based Python Execution**: Run Python code instantly using Pyodide (WebAssembly)
- **Monaco Code Editor**: Professional IDE experience with syntax highlighting and IntelliSense
- **Real-Time Console Output**: Terminal-style display for code execution results
- **Secure Authentication**: User management powered by Supabase
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **No Backend Required**: Python runs entirely in the browser - no server-side execution

## Technology Stack

- **Framework**: Next.js 16 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS
- **Authentication**: Supabase Auth
- **Database**: Supabase (PostgreSQL)
- **Python Runtime**: Pyodide (CPython in WebAssembly)
- **Code Editor**: Monaco Editor
- **Language**: TypeScript

## Getting Started

### Prerequisites

- Node.js 18+ installed
- A Supabase account and project ([create one here](https://supabase.com))

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd personal-coding-tutor
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:

Create a `.env.local` file in the root directory:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Get these values from your Supabase project settings:
- Go to [Supabase Dashboard](https://supabase.com/dashboard)
- Select your project
- Navigate to Settings → API
- Copy the Project URL and anon/public key

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

### First Time Setup

1. Navigate to `/login` to create an account
2. Check your email for the confirmation link (or use magic link) - this step can be disabled from the Supabase interface
3. Once authenticated, you'll be redirected to the homepage
4. Visit `/dashboard` to access the coding workspace

## Project Structure

```
personal-coding-tutor/
├── app/                      # Next.js App Router
│   ├── dashboard/           # Main coding workspace
│   ├── login/               # Authentication page
│   └── auth/callback/       # OAuth callback handler
├── components/              # Reusable React components
│   ├── CodeEditor.tsx      # Monaco editor wrapper
│   └── Console.tsx         # Terminal output display
├── hooks/                   # Custom React hooks
│   └── usePyodide.ts       # Python runtime management
├── utils/supabase/         # Supabase client utilities
└── documentation/          # Detailed project documentation
```

## Usage

1. **Write Code**: Use the Monaco editor on the left to write Python code
2. **Run Code**: Click the "Run Code" button to execute
3. **View Output**: See results in the console on the right
4. **Iterate**: Modify your code and run again

### Example Code

```python
# Try this in the editor!
print('Hello from PACT!')

for i in range(5):
    print(f'Count: {i}')

import math
print(f'Pi is approximately {math.pi:.2f}')
```

## Available Commands

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm start            # Start production server
npm run lint         # Run ESLint
```

## Documentation

For detailed documentation including:
- Architecture decisions and rationale
- Component deep-dive explanations
- Authentication flow diagrams
- Styling system guide
- Future enhancement ideas

See [documentation/documentation.md](documentation/documentation.md)

## Key Technologies Explained

### Pyodide
Pyodide is CPython compiled to WebAssembly, allowing Python to run directly in the browser. It includes popular packages like NumPy, Pandas, and Matplotlib.

### Supabase
Provides authentication, database, and real-time features without managing backend infrastructure. Uses PostgreSQL with row-level security.

### Next.js App Router
Modern React framework with server-side rendering, file-based routing, and built-in API routes.

## Deployment

The easiest way to deploy is using [Vercel](https://vercel.com):

1. Push your code to GitHub
2. Import the repository in Vercel
3. Add environment variables in Vercel project settings
4. Deploy

Vercel will automatically:
- Build your Next.js app
- Set up CDN and edge functions
- Provide HTTPS and custom domains

See [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for other platforms.

## Contributing

Contributions are welcome! Areas for improvement:
- AI model integration for coding hints
- Code persistence to database
- Additional Python package support
- Collaborative coding features
- Unit test runner for challenges

## License

MIT License - see LICENSE file for details

## Support

For questions or issues, please open an issue on GitHub.
