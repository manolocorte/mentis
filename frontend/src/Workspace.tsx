import { useEffect, useState } from 'react'
import {
  ChevronRight,
  FileDown,
  FileText,
  FlaskConical,
  Image as ImageIcon,
  Library as LibraryIcon,
  Loader2,
  Moon,
  NotebookPen,
  Paperclip,
  Pencil,
  Plus,
  SlidersHorizontal,
  Sun,
  Trash2,
  UploadCloud,
} from 'lucide-react'
import ChatPage from './pages/ChatPage'
import type { Message } from './pages/ChatPage'
import {
  compileProject,
  createConversation,
  createProject,
  deleteConversation,
  deleteFile,
  deleteProject,
  fileUrl,
  getConversationMessages,
  getLibrary,
  getSourceProviders,
  listConversations,
  listFiles,
  listProjects,
  renameConversation,
  renameProject,
  updateBrief,
  updateProjectSources,
  uploadFiles,
} from './api/client'
import type {
  Conversation,
  LibrarySource,
  Project,
  ProjectFile,
  SourceProvider,
  StoredMessage,
} from './api/types'

function toMessages(stored: StoredMessage[]): Message[] {
  return stored.map((m) =>
    m.role === 'user'
      ? { role: 'user', content: m.content }
      : { role: 'assistant', content: m.content, tools: [], citations: [], status: 'done' },
  )
}

function HoverIcon({ label, onClick, children }: { label: string; onClick: (e: React.MouseEvent) => void; children: React.ReactNode }) {
  return (
    <button
      title={label}
      aria-label={label}
      onClick={(e) => { e.stopPropagation(); onClick(e) }}
      className="p-1 rounded text-stone-500 hover:text-stone-100 hover:bg-stone-700/60"
    >
      {children}
    </button>
  )
}

function ToolLink({ active, onClick, icon, children, disabled }: {
  active?: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode; disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-1.5 py-1 rounded text-[0.7rem] tracking-wide transition-colors disabled:opacity-50 ${
        active ? 'text-mentis-300' : 'text-stone-500 hover:text-stone-200'
      }`}
    >
      {icon}
      {children}
    </button>
  )
}

function PanelHeading({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-5">
      <h2 className="font-serif text-2xl text-stone-900 dark:text-stone-100">{title}</h2>
      {sub && <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">{sub}</p>}
    </div>
  )
}

function LibraryPanel({ sources }: { sources: LibrarySource[] }) {
  return (
    <div className="h-full overflow-y-auto px-10 py-8">
      <PanelHeading title="Library" sub="DOI-verified sources gathered across this project." />
      {sources.length === 0 ? (
        <p className="text-sm text-stone-400">No sources yet — run a research or draft request.</p>
      ) : (
        <ul className="max-w-3xl divide-y divide-stone-200 dark:divide-stone-800 border-y border-stone-200 dark:border-stone-800">
          {sources.map((s, i) => (
            <li key={i} className="py-3">
              <p className="text-[0.92rem] text-stone-800 dark:text-stone-100 leading-snug">
                {s.doi ? (
                  <a href={`https://doi.org/${s.doi}`} target="_blank" rel="noopener noreferrer"
                    className="hover:text-mentis-700 dark:hover:text-mentis-300 hover:underline underline-offset-2">{s.title}</a>
                ) : s.title}
              </p>
              <p className="font-mono text-[0.7rem] text-stone-500 mt-1">
                {[s.authors, s.year, s.venue].filter(Boolean).join('  ·  ')}
                {s.verified
                  ? <span className="text-mentis-600 dark:text-mentis-400">  ·  verified</span>
                  : <span className="text-amber-600">  ·  unverified</span>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function humanSize(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function FilesPanel({
  projectId,
  files,
  onUpload,
  onDelete,
}: {
  projectId: string
  files: ProjectFile[]
  onUpload: (files: File[]) => void
  onDelete: (name: string) => void
}) {
  const [drag, setDrag] = useState(false)
  return (
    <div className="h-full overflow-y-auto px-10 py-8">
      <PanelHeading title="Files" sub="Data and figures for this project. The Analyst reads uploads and saves results here." />

      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); onUpload(Array.from(e.dataTransfer.files)) }}
        className={`max-w-3xl flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 cursor-pointer transition-colors ${
          drag
            ? 'border-mentis-400 bg-mentis-50 dark:bg-stone-800'
            : 'border-stone-300 dark:border-stone-700 hover:border-mentis-300 dark:hover:border-mentis-700'
        }`}
      >
        <UploadCloud size={26} className="text-mentis-600 dark:text-mentis-400" />
        <p className="text-sm text-stone-600 dark:text-stone-300">
          Drop files here, or <span className="text-mentis-700 dark:text-mentis-300 underline underline-offset-2">browse</span>
        </p>
        <p className="font-mono text-[0.65rem] text-stone-400">Spreadsheets · CSV · images</p>
        <input
          type="file"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) onUpload(Array.from(e.target.files)); e.currentTarget.value = '' }}
        />
      </label>

      {files.length === 0 ? (
        <p className="text-sm text-stone-400 mt-6">No files yet.</p>
      ) : (
        <ul className="max-w-3xl mt-6 grid grid-cols-2 gap-3">
          {files.map((f) => (
            <li key={f.name}
              className="group relative flex items-center gap-3 rounded-lg border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 p-3">
              {f.kind === 'image' ? (
                <img src={fileUrl(projectId, f.name)} alt={f.name}
                  className="w-12 h-12 rounded object-cover border border-stone-200 dark:border-stone-700 shrink-0" />
              ) : (
                <div className="w-12 h-12 rounded bg-stone-100 dark:bg-stone-800 flex items-center justify-center shrink-0">
                  <FileText size={20} className="text-stone-400" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <a href={fileUrl(projectId, f.name)} target="_blank" rel="noopener noreferrer"
                  className="block text-sm text-stone-800 dark:text-stone-100 truncate hover:text-mentis-700 dark:hover:text-mentis-300">
                  {f.name}
                </a>
                <p className="font-mono text-[0.65rem] text-stone-400 mt-0.5 flex items-center gap-1">
                  {f.kind === 'image' && <ImageIcon size={11} />}
                  {humanSize(f.size)}
                </p>
              </div>
              <button onClick={() => onDelete(f.name)} title="Delete file"
                className="opacity-0 group-hover:opacity-100 p-1 rounded text-stone-400 hover:text-red-600 hover:bg-stone-100 dark:hover:bg-stone-800">
                <Trash2 size={14} />
              </button>
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
    <div className="h-full overflow-y-auto px-10 py-8">
      <PanelHeading title="Sources" sub={`Where the Researcher gathers sources for “${project.name}”. Applies to the next message.`} />
      <ul className="max-w-xl space-y-2">
        {providers.map((s) => (
          <li key={s.key}>
            <label className={`flex items-center gap-3 rounded-lg border px-4 py-3 cursor-pointer transition-colors ${
              s.available
                ? 'border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 hover:border-mentis-300 dark:hover:border-mentis-700'
                : 'border-stone-200 dark:border-stone-800 opacity-60 cursor-not-allowed'}`}>
              <input type="checkbox" checked={enabled.has(s.key)} disabled={!s.available}
                onChange={() => onToggle(s.key)} className="accent-mentis-600 w-4 h-4" />
              <div className="flex-1">
                <p className="text-sm text-stone-800 dark:text-stone-100">
                  {s.label}
                  {s.free && <span className="font-mono text-[0.65rem] text-stone-400 ml-2">FREE</span>}
                </p>
                {!s.available && <p className="text-xs text-amber-600 mt-0.5">unavailable — no API key configured</p>}
              </div>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}

function EmptyState({ title, actionLabel, onAction }: { title: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center">
      <p className="font-serif text-xl text-stone-500 dark:text-stone-400 mb-4">{title}</p>
      {actionLabel && onAction && (
        <button onClick={onAction}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-mentis-600 hover:bg-mentis-700 text-white rounded-lg text-sm">
          <Plus size={15} /> {actionLabel}
        </button>
      )}
    </div>
  )
}

export default function Workspace() {
  const [projects, setProjects] = useState<Project[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [convsByProject, setConvsByProject] = useState<Record<string, Conversation[]>>({})
  const [libByProject, setLibByProject] = useState<Record<string, LibrarySource[]>>({})
  const [filesByProject, setFilesByProject] = useState<Record<string, ProjectFile[]>>({})
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [initialMessages, setInitialMessages] = useState<Message[]>([])
  const [view, setView] = useState<'chat' | 'library' | 'sources' | 'files'>('chat')
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
    const [{ conversations }, { sources }, { files }] = await Promise.all([
      listConversations(pid),
      getLibrary(pid),
      listFiles(pid),
    ])
    setConvsByProject((m) => ({ ...m, [pid]: conversations }))
    setLibByProject((m) => ({ ...m, [pid]: sources }))
    setFilesByProject((m) => ({ ...m, [pid]: files }))
    return conversations
  }

  async function refreshFiles(pid: string) {
    const { files } = await listFiles(pid)
    setFilesByProject((m) => ({ ...m, [pid]: files }))
  }

  function openFiles(pid: string) {
    setActiveProjectId(pid)
    setView('files')
    refreshFiles(pid)
  }

  async function handleUploadFiles(pid: string, files: File[]) {
    if (!files.length) return
    try {
      await uploadFiles(pid, files)
      await refreshFiles(pid)
    } catch (e) {
      alert('Upload failed: ' + (e instanceof Error ? e.message : 'error'))
    }
  }

  async function handleDeleteFile(pid: string, name: string) {
    if (!window.confirm(`Delete "${name}"?`)) return
    await deleteFile(pid, name)
    await refreshFiles(pid)
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
    <div className="flex h-screen bg-stone-50 dark:bg-stone-950">
      {/* Sidebar — deep warm ink in both themes */}
      <aside className="w-72 bg-stone-900 text-stone-200 flex flex-col shrink-0 border-r border-stone-800">
        <div className="px-5 py-4 flex items-center justify-between border-b border-stone-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-mentis-600 flex items-center justify-center">
              <FlaskConical size={17} className="text-white" />
            </div>
            <div className="leading-tight">
              <p className="font-serif text-[1.05rem] text-stone-50">Mentis</p>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.18em] text-stone-500">Research workspace</p>
            </div>
          </div>
          <button onClick={newProject} title="New project"
            className="p-1.5 rounded-md text-stone-400 hover:text-stone-100 hover:bg-stone-800">
            <Plus size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {projects.length === 0 && (
            <p className="px-5 py-3 text-xs text-stone-500 leading-relaxed">
              No projects yet. Create one to start researching and drafting.
            </p>
          )}
          {projects.map((p) => {
            const isOpen = expanded.has(p.id)
            const convs = convsByProject[p.id] || []
            return (
              <div key={p.id} className="px-2">
                {/* Project row */}
                <div
                  className="group flex items-center gap-1 px-2 py-1.5 rounded-md hover:bg-stone-800/60 cursor-pointer"
                  onClick={() => toggleExpand(p.id)}
                >
                  <ChevronRight size={14} className={`text-stone-500 shrink-0 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
                  <span className="flex-1 text-sm text-stone-200 truncate">{p.name}</span>
                  <span className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                    <HoverIcon label="New conversation" onClick={() => newConversation(p.id)}><Plus size={14} /></HoverIcon>
                    <HoverIcon label="Rename project" onClick={() => handleRenameProject(p)}><Pencil size={13} /></HoverIcon>
                    <HoverIcon label="Delete project" onClick={() => handleDeleteProject(p)}><Trash2 size={13} /></HoverIcon>
                  </span>
                </div>

                {isOpen && (
                  <div className="ml-3.5 pl-2 border-l border-stone-800">
                    {convs.map((c) => {
                      const active = c.id === activeConvId && view === 'chat'
                      return (
                        <div key={c.id}
                          className={`group flex items-center px-2 py-1 rounded-md cursor-pointer text-[0.82rem] ${
                            active ? 'bg-stone-800 text-stone-50' : 'text-stone-400 hover:bg-stone-800/50 hover:text-stone-200'}`}
                          onClick={() => openConversation(p.id, c.id)}>
                          <span className="flex-1 truncate">{c.title}</span>
                          <span className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5">
                            <HoverIcon label="Rename conversation" onClick={() => handleRenameConversation(p.id, c)}><Pencil size={12} /></HoverIcon>
                            <HoverIcon label="Delete conversation" onClick={() => handleDeleteConversation(p.id, c)}><Trash2 size={12} /></HoverIcon>
                          </span>
                        </div>
                      )
                    })}

                    {/* Project tools */}
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      <ToolLink active={view === 'library' && activeProjectId === p.id} onClick={() => openLibrary(p.id)}
                        icon={<LibraryIcon size={13} />}>Library · {(libByProject[p.id] || []).length}</ToolLink>
                      <ToolLink active={view === 'files' && activeProjectId === p.id} onClick={() => openFiles(p.id)}
                        icon={<Paperclip size={13} />}>Files · {(filesByProject[p.id] || []).length}</ToolLink>
                      <ToolLink active={view === 'sources' && activeProjectId === p.id} onClick={() => openSources(p.id)}
                        icon={<SlidersHorizontal size={13} />}>Sources</ToolLink>
                      <ToolLink onClick={() => editBrief(p.id)} icon={<NotebookPen size={13} />}>Brief</ToolLink>
                    </div>
                    <div className="mb-1.5 flex items-center gap-1 pl-1.5">
                      <span className="font-mono text-[0.6rem] uppercase tracking-wider text-stone-600">Compile</span>
                      <ToolLink onClick={() => doCompile(p.id, 'pdf')} disabled={compiling === p.id}
                        icon={compiling === p.id ? <Loader2 size={13} className="animate-spin" /> : <FileDown size={13} />}>
                        {compiling === p.id ? 'Working' : 'PDF'}
                      </ToolLink>
                      <ToolLink onClick={() => doCompile(p.id, 'docx')} disabled={compiling === p.id}
                        icon={<FileDown size={13} />}>Word</ToolLink>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="px-4 py-3 border-t border-stone-800">
          <button onClick={() => setDark((d) => !d)}
            className="flex items-center gap-2 text-xs text-stone-400 hover:text-stone-100">
            {dark ? <Sun size={14} /> : <Moon size={14} />}
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        {!activeProjectId && view === 'chat' ? (
          <EmptyState title="Create a project to begin" actionLabel="New project" onAction={newProject} />
        ) : view === 'sources' && activeProjectId && projects.find((p) => p.id === activeProjectId) ? (
          <SourcesPanel
            project={projects.find((p) => p.id === activeProjectId)!}
            providers={providers}
            onToggle={(key) => toggleSource(activeProjectId, key)}
          />
        ) : view === 'library' && activeProjectId ? (
          <LibraryPanel sources={libByProject[activeProjectId] || []} />
        ) : view === 'files' && activeProjectId ? (
          <FilesPanel
            projectId={activeProjectId}
            files={filesByProject[activeProjectId] || []}
            onUpload={(files) => handleUploadFiles(activeProjectId, files)}
            onDelete={(name) => handleDeleteFile(activeProjectId, name)}
          />
        ) : activeConvId ? (
          <ChatPage
            key={activeConvId}
            conversationId={activeConvId}
            initialMessages={initialMessages}
            onTitle={updateConvTitle}
            projectId={activeProjectId ?? undefined}
            onFilesChanged={() => activeProjectId && refreshFiles(activeProjectId)}
          />
        ) : (
          <EmptyState
            title="No conversation open"
            actionLabel={activeProjectId ? 'New conversation' : undefined}
            onAction={activeProjectId ? () => newConversation(activeProjectId) : undefined}
          />
        )}
      </main>
    </div>
  )
}
