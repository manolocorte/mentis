import { useState } from 'react'
import { postHarvest } from '../api/client'
import type { HarvestResponse } from '../api/types'

export default function HarvestPage() {
  const [query, setQuery] = useState('')
  const [maxResults, setMaxResults] = useState(20)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<HarvestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || loading) return
    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const res = await postHarvest({ query: q, max_results: maxResults })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Harvest failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Harvest</h1>
        <p className="text-sm text-gray-500 mb-8">
          Submit a search query to fetch and ingest papers into the document store.
        </p>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5">
          {/* Query */}
          <div>
            <label htmlFor="harvest-query" className="block text-sm font-medium text-gray-700 mb-1.5">
              Search query
            </label>
            <textarea
              id="harvest-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              placeholder="e.g. absorption refrigeration CO2 biobased solvents"
              className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-mentis-500 focus:border-transparent"
            />
          </div>

          {/* Max results */}
          <div>
            <label htmlFor="max-results" className="block text-sm font-medium text-gray-700 mb-1.5">
              Max results
              <span className="ml-2 text-mentis-600 font-semibold">{maxResults}</span>
            </label>
            <input
              id="max-results"
              type="range"
              min={1}
              max={100}
              step={1}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-full accent-mentis-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>1</span>
              <span>100</span>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-mentis-600 text-white text-sm font-medium rounded-xl hover:bg-mentis-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="2" x2="12" y2="6" /><line x1="12" y1="18" x2="12" y2="22" />
                  <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" /><line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
                  <line x1="2" y1="12" x2="6" y2="12" /><line x1="18" y1="12" x2="22" y2="12" />
                  <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" /><line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
                </svg>
                Harvesting…
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Start harvest
              </>
            )}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="mt-6 p-5 bg-mentis-50 border border-mentis-200 rounded-xl">
            <div className="flex items-start gap-3">
              <svg
                className="text-mentis-600 mt-0.5 shrink-0"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <div>
                <p className="text-sm font-semibold text-mentis-800">
                  {result.enqueued} paper{result.enqueued !== 1 ? 's' : ''} enqueued
                </p>
                <p className="text-sm text-mentis-700 mt-0.5">{result.message}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
