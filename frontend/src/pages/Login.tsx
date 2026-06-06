import { useState } from 'react'
import { FlaskConical, Loader2, LogIn } from 'lucide-react'
import { login } from '../api/client'

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password || busy) return
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50 dark:bg-stone-950 px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-md bg-mentis-600 flex items-center justify-center">
            <FlaskConical size={20} className="text-white" />
          </div>
          <div className="leading-tight">
            <p className="font-serif text-xl text-stone-900 dark:text-stone-50">Mentis</p>
            <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-stone-500">Research workspace</p>
          </div>
        </div>

        <form
          onSubmit={submit}
          className="rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 p-6 shadow-sm"
        >
          <h1 className="font-serif text-lg text-stone-800 dark:text-stone-100 mb-5">Sign in</h1>

          <label className="block text-xs font-mono uppercase tracking-wider text-stone-500 mb-1">Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            className="w-full mb-4 rounded-lg border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-stone-800 text-stone-800 dark:text-stone-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500/40 focus:border-mentis-500"
          />

          <label className="block text-xs font-mono uppercase tracking-wider text-stone-500 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full mb-5 rounded-lg border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-stone-800 text-stone-800 dark:text-stone-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500/40 focus:border-mentis-500"
          />

          {error && (
            <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={busy || !username || !password}
            className="w-full inline-flex items-center justify-center gap-2 bg-mentis-600 hover:bg-mentis-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg py-2.5 text-sm transition-colors"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
