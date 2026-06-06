import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import Workspace from './Workspace'
import Login from './pages/Login'
import { getAuthStatus, getMe, getToken, logout, setUnauthorizedHandler } from './api/client'

type Gate = 'loading' | 'login' | 'ready'

export default function App() {
  const [gate, setGate] = useState<Gate>('loading')
  const [authRequired, setAuthRequired] = useState(false)

  useEffect(() => {
    setUnauthorizedHandler(() => setGate('login'))
    getAuthStatus()
      .then(async ({ auth_required }) => {
        setAuthRequired(auth_required)
        if (!auth_required) return setGate('ready')
        if (!getToken()) return setGate('login')
        try {
          await getMe()
          setGate('ready')
        } catch {
          setGate('login')
        }
      })
      .catch(() => setGate('ready')) // backend unreachable: let the workspace surface the error
  }, [])

  if (gate === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-stone-50 dark:bg-stone-950">
        <Loader2 className="animate-spin text-mentis-600" />
      </div>
    )
  }
  if (gate === 'login') return <Login onSuccess={() => setGate('ready')} />

  return (
    <Workspace
      onLogout={
        authRequired
          ? async () => {
              await logout()
              setGate('login')
            }
          : undefined
      }
    />
  )
}
