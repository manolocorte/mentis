import { useEffect, useState } from 'react'
import ChatPage from './pages/ChatPage'
import type { Message } from './pages/ChatPage'
import {
  compileProject,
  createConversation,
  createProject,
  deleteConversation,
  deleteProject,
  getConversationMessages,
  getLibrary,
  getSourceProviders,
  listConversations,
  listProjects,
  renameConversation,
  renameProject,
  updateBrief,
  updateProjectSources,
} from './api/client'
import type { Conversation, LibrarySource, Project, SourceProvider, StoredMessage } from './api/types'

function toMessages(stored: StoredMessage[]): Message[] {
  return stored.map((m) =>
    m.role === 'user'
      ? { role: 'user', content: m.content }
      : { role: 'assistant', content: m.content, tools: [], citations: [], status: 'done' },
  )
}

function IconBtn({ label, onClick, children }: { label: string; onClick: (e: React.MouseEvent) => void; children: React.ReactNode }) {
  return (
    <button title={label} aria-label={label}
      onClick={(e) => { e.stopPropagation(); onClick(e) }}
      className="px-1 text-mentis-300 hover:text-white text-xs leading-none">
      {children}
    </button>
  )
}

function LibraryPanel({ sources }: { sources: LibrarySource[] }) {
  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-1">Project library</h2>
      <p className="text-sm text-gray-400 mb-4">DOI-verified sources gathered across this project.</p>
      {sources.length === 0 ? (
        <p className="text-sm text-gray-400">No sources yet — run a research/draft request.</p>
      ) : (
        <ul className="space-y-2 max-w-3xl">
          {sources.map((s, i) => (
            <li key={i} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3">
              <p className="text-sm text-gray-800 dark:text-gray-100">
                {s.doi ? <a href={`https://doi.org/${s.doi}`} target="_blank" rel="noopener noreferrer" className="text-mentis-700 dark:text-mentis-300 hover:underline">{s.title}</a> : s.title}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {s.authors} · {s.year} · {s.venue || '—'}
                {s.verified ? <span className="text-mentis-700"> · ✓ verified</span> : <span className="text-amber-600"> · unverified</span>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SourcesPanel({ project, providers, onToggle }: { project: Project; providers: SourceProvider[]; onToggle: (key: string) => void }) {
  const enabled = new Set(project.sources || [])
  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-1">Sources — {project.name}</h2>
      <p className="text-sm text-gray-400 mb-4">Choose where the Researcher gathers sources for this project. Changes apply to the next message.</p>
      <ul className="space-y-2 max-w-xl">
        {providers.map((s) => (
          <li key={s.key} className="flex items-center gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3">
            <input type="checkbox" checked={enabled.has(s.key)} disabled={!s.available}
              onChange={() => onToggle(s.key)} className="accent-mentis-600 w-4 h-4" />
            <div className="flex-1">
              <p className="text-sm text-gray-800 dark:text-gray-100">
                {s.label}{s.free && <span className="text-xs text-mentis-600"> · free</span>}
              </p>
              {!s.available && <p className="text-xs text-amber-600">unavailable — no API key configured</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Workspace() {
  const [projects, setProjects] = useState<Project[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [convsByProject, setConvsByProject] = useState<Record<string, Conversation[]>>({})
  const [libByProject, setLibByProject] = useState<Record<string, LibrarySource[]>>({})
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [initialMessages, setInitialMessages] = useState<Message[]>([])
  const [view, setView] = useState<'chat' | 'library' | 'sources'>('chat')
  const [providers, setProviders] = useState<SourceProvider[]>([])
  const [dark, setDark] = useState<boolean>(() => localStorage.getItem('mentis-theme') === 'dark')
  const [compiling, setCompiling] = useState<string | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('mentis-theme', dark ? 'dark' : 'light')
  }, [dark])

  useEffect(() => {
    getSourceProviders().then(({ sources }) => setProviders(sources))
    listProjects().then(async ({ projects }) => {
      setProjects(projects)
      if (projects.length) {
        const pid = projects[0].id
        setExpanded(new Set([pid]))
        const convs = await loadProject(pid)
        if (convs.length) await openConversation(pid, convs[0].id)
        else setActiveProjectId(pid)
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function refreshProjects() {
    const { projects } = await listProjects()
    setProjects(projects)
  }

  async function loadProject(pid: string): Promise<Conversation[]> {
    const [{ conversations }, { sources }] = await Promise.all([listConversations(pid), getLibrary(pid)])
    setConvsByProject((m) => ({ ...m, [pid]: conversations }))
    setLibByProject((m) => ({ ...m, [pid]: sources }))
    return conversations
  }

  async function toggleExpand(pid: string) {
    const isOpen = expanded.has(pid)
    setExpanded((prev) => {
      const next = new Set(prev)
      isOpen ? next.delete(pid) : next.add(pid)
      return next
    })
    if (!isOpen && !convsByProject[pid]) await loadProject(pid)
  }

  async function openConversation(pid: string, cid: string) {
    const { messages } = await getConversationMessages(cid)
    setInitialMessages(toMessages(messages))
    setActiveProjectId(pid)
    setActiveConvId(cid)
    setView('chat')
    setExpanded((prev) => new Set(prev).add(pid))
  }

  async function newProject() {
    const name = window.prompt('New project name', 'Untitled paper')
    if (!name) return
    const project = await createProject(name)
    const conv = await createConversation(project.id, 'New conversation')
    await refreshProjects()
    setConvsByProject((m) => ({ ...m, [project.id]: [conv] }))
    await openConversation(project.id, conv.id)
  }

  async function handleRenameProject(p: Project) {
    const name = window.prompt('Rename project', p.name)
    if (!name) return
    await renameProject(p.id, name)
    await refreshProjects()
  }

  async function handleDeleteProject(p: Project) {
    if (!window.confirm(`Delete project "${p.name}" and all its conversations?`)) return
    await deleteProject(p.id)
    setConvsByProject((m) => { const n = { ...m }; delete n[p.id]; return n })
    if (activeProjectId === p.id) { setActiveProjectId(null); setActiveConvId(null); setView('chat') }
    await refreshProjects()
  }

  async function newConversation(pid: string) {
    const conv = await createConversation(pid)
    await loadProject(pid)
    await openConversation(pid, conv.id)
  }

  async function handleRenameConversation(pid: string, c: Conversation) {
    const title = window.prompt('Rename conversation', c.title)
    if (!title) return
    await renameConversation(c.id, title)
    await loadProject(pid)
  }

  async function handleDeleteConversation(pid: string, c: Conversation) {
    if (!window.confirm(`Delete conversation "${c.title}"?`)) return
    await deleteConversation(c.id)
    const convs = await loadProject(pid)
    if (activeConvId === c.id) {
      if (convs.length) await openConversation(pid, convs[0].id)
      else { setActiveConvId(null); setView('chat') }
    }
  }

  async function openLibrary(pid: string) {
    const { sources } = await getLibrary(pid)
    setLibByProject((m) => ({ ...m, [pid]: sources }))
    setActiveProjectId(pid)
    setView('library')
  }

  async function editBrief(pid: string) {
    const p = projects.find((x) => x.id === pid)
    const brief = window.prompt('Project brief (topic, scope, angle, target journal)', p?.brief || '')
    if (brief === null) return
    await updateBrief(pid, brief)
    await refreshProjects()
  }

  function openSources(pid: string) {
    setActiveProjectId(pid)
    setView('sources')
  }

  async function doCompile(pid: string, format: 'pdf' | 'docx') {
    setCompiling(pid)
    try {
      await compileProject(pid, format)
    } catch (e) {
      alert('Compile failed: ' + (e instanceof Error ? e.message : 'error'))
    } finally {
      setCompiling(null)
    }
  }

  async function toggleSource(pid: string, key: string) {
    const p = projects.find((x) => x.id === pid)
    if (!p) return
    const cur = new Set(p.sources || [])
    cur.has(key) ? cur.delete(key) : cur.add(key)
    await updateProjectSources(pid, Array.from(cur))
    await refreshProjects()
  }

  function updateConvTitle(cid: string, title: string) {
    setConvsByProject((m) => {
      const n: Record<string, Conversation[]> = {}
      for (const pid of Object.keys(m)) n[pid] = m[pid].map((c) => (c.id === cid ? { ...c, title } : c))
      return n
    })
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      <aside className="w-64 bg-mentis-800 text-white flex flex-col shrink-0">
        <div className="px-5 py-4 border-b border-mentis-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-white rounded-md flex items-center justify-center">
              <span className="text-mentis-800 font-bold text-sm">M</span>
            </div>
            <div>
              <p className="font-semibold text-sm leading-tight">Mentis</p>
              <p className="text-mentis-300 text-xs leading-tight">Research workspace</p>
            </div>
          </div>
          <button onClick={newProject} title="New project" className="text-mentis-200 hover:text-white text-xl leading-none">+</button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {projects.length === 0 && <p className="px-4 py-2 text-xs text-mentis-400">No projects yet — click + to create one.</p>}
          {projects.map((p) => {
            const isOpen = expanded.has(p.id)
            const convs = convsByProject[p.id] || []
            return (
              <div key={p.id}>
                {/* Project row */}
                <div className="group flex items-center px-2 py-1.5 mx-1 rounded-lg hover:bg-mentis-700 cursor-pointer"
                  onClick={() => toggleExpand(p.id)}>
                  <span className="w-4 text-mentis-300 text-xs">{isOpen ? '▾' : '▸'}</span>
                  <span className="flex-1 text-sm truncate">{p.name}</span>
                  <span className="opacity-0 group-hover:opacity-100 flex items-center">
                    <IconBtn label="New conversation" onClick={() => newConversation(p.id)}>＋</IconBtn>
                    <IconBtn label="Rename project" onClick={() => handleRenameProject(p)}>✎</IconBtn>
                    <IconBtn label="Delete project" onClick={() => handleDeleteProject(p)}>🗑</IconBtn>
                  </span>
                </div>

                {/* Conversations + project tools */}
                {isOpen && (
                  <div className="ml-4 border-l border-mentis-700 pl-1">
                    {convs.map((c) => (
                      <div key={c.id}
                        className={`group flex items-center px-2 py-1 mx-1 rounded-lg cursor-pointer text-sm ${
                          c.id === activeConvId && view === 'chat' ? 'bg-mentis-600' : 'hover:bg-mentis-700 text-mentis-100'}`}
                        onClick={() => openConversation(p.id, c.id)}>
                        <span className="flex-1 truncate">{c.title}</span>
                        <span className="opacity-0 group-hover:opacity-100 flex items-center">
                          <IconBtn label="Rename conversation" onClick={() => handleRenameConversation(p.id, c)}>✎</IconBtn>
                          <IconBtn label="Delete conversation" onClick={() => handleDeleteConversation(p.id, c)}>🗑</IconBtn>
                        </span>
                      </div>
                    ))}
                    <div className="flex items-center gap-3 px-3 py-1 text-xs text-mentis-300">
                      <button onClick={() => openLibrary(p.id)}
                        className={`hover:text-white ${view === 'library' && activeProjectId === p.id ? 'text-white' : ''}`}>
                        📚 Library ({(libByProject[p.id] || []).length})
                      </button>
                      <button onClick={() => openSources(p.id)}
                        className={`hover:text-white ${view === 'sources' && activeProjectId === p.id ? 'text-white' : ''}`}>
                        ⚙ Sources
                      </button>
                      <button onClick={() => editBrief(p.id)} className="hover:text-white">✎ Brief</button>
                    </div>
                    <div className="flex items-center gap-3 px-3 pb-1 text-xs text-mentis-300">
                      <span className="text-mentis-400">Whitepaper →</span>
                      <button onClick={() => doCompile(p.id, 'pdf')} disabled={compiling === p.id}
                        className="hover:text-white disabled:opacity-50">
                        {compiling === p.id ? '⏳ Compiling…' : '📄 PDF'}
                      </button>
                      <button onClick={() => doCompile(p.id, 'docx')} disabled={compiling === p.id}
                        className="hover:text-white disabled:opacity-50">Word</button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="px-3 py-2 border-t border-mentis-700">
          <button onClick={() => setDark((d) => !d)} className="text-xs text-mentis-200 hover:text-white">
            {dark ? '☀️ Light mode' : '🌙 Dark mode'}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        {!activeProjectId && view === 'chat' ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-400">
            <p className="text-lg font-light mb-2">Create a project to begin</p>
            <button onClick={newProject} className="px-4 py-2 bg-mentis-600 text-white rounded-lg text-sm hover:bg-mentis-700">New project</button>
          </div>
        ) : view === 'sources' && activeProjectId && projects.find((p) => p.id === activeProjectId) ? (
          <SourcesPanel
            project={projects.find((p) => p.id === activeProjectId)!}
            providers={providers}
            onToggle={(key) => toggleSource(activeProjectId, key)}
          />
        ) : view === 'library' && activeProjectId ? (
          <LibraryPanel sources={libByProject[activeProjectId] || []} />
        ) : activeConvId ? (
          <ChatPage key={activeConvId} conversationId={activeConvId} initialMessages={initialMessages} onTitle={updateConvTitle} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-400">
            <p className="text-lg font-light mb-2">No conversation open</p>
            {activeProjectId && (
              <button onClick={() => newConversation(activeProjectId)} className="px-4 py-2 bg-mentis-600 text-white rounded-lg text-sm hover:bg-mentis-700">New conversation</button>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
