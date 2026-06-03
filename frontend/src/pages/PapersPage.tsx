import { useState } from 'react'
import { searchPapers } from '../api/client'
import type { Paper } from '../api/types'

function PaperCard({ paper }: { paper: Paper }) {
  const authorsLabel = paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '')

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm text-gray-900 leading-snug">{paper.title}</h3>

          <p className="text-xs text-gray-500 mt-1">
            {authorsLabel}
            {paper.year && <span> &middot; {paper.year}</span>}
            {paper.venue && <span> &middot; {paper.venue}</span>}
          </p>

          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="bg-mentis-50 text-mentis-700 text-xs px-2 py-0.5 rounded-full font-medium">
              {paper.source}
            </span>
            {paper.citation_count != null && (
              <span className="text-xs text-gray-400">{paper.citation_count.toLocaleString()} citations</span>
            )}
            {paper.doi && (
              <span className="text-xs text-gray-400 truncate">DOI: {paper.doi}</span>
            )}
          </div>
        </div>

        {paper.doi && (
          <a
            href={`https://doi.org/${paper.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Open via DOI"
            className="shrink-0 text-gray-400 hover:text-mentis-600 transition-colors mt-0.5"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        )}
      </div>
    </div>
  )
}

export default function PapersPage() {
  const [query, setQuery] = useState('')
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const handleSearch = async () => {
    const q = query.trim()
    if (!q || loading) return
    setLoading(true)
    setError(null)
    try {
      const res = await searchPapers(q)
      setPapers(res.papers)
      setSearched(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">Papers</h1>

        {/* Search bar */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search papers by keyword, author, or topic…"
            className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-mentis-500 focus:border-transparent"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 px-5 py-2.5 bg-mentis-600 text-white text-sm rounded-xl hover:bg-mentis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="2" x2="12" y2="6" /><line x1="12" y1="18" x2="12" y2="22" />
                <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" /><line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
                <line x1="2" y1="12" x2="6" y2="12" /><line x1="18" y1="12" x2="22" y2="12" />
                <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" /><line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            )}
            Search
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {papers.length > 0 ? (
          <>
            <p className="text-xs text-gray-500 mb-3">{papers.length} result{papers.length !== 1 ? 's' : ''}</p>
            <div className="space-y-3">
              {papers.map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </div>
          </>
        ) : searched && !loading ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No papers found for &ldquo;{query}&rdquo;</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
