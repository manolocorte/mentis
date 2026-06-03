import { useState, useEffect } from 'react'
import { getDocuments } from '../api/client'
import type { Document } from '../api/types'

function statusBadge(status: string) {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium'
  switch (status.toLowerCase()) {
    case 'ready':
    case 'indexed':
      return `${base} bg-green-100 text-green-700`
    case 'processing':
    case 'pending':
      return `${base} bg-yellow-100 text-yellow-700`
    case 'error':
    case 'failed':
      return `${base} bg-red-100 text-red-700`
    default:
      return `${base} bg-gray-100 text-gray-600`
  }
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getDocuments()
      setDocuments(res.documents)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchDocuments()
  }, [])

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">Documents</h1>
          <button
            onClick={() => void fetchDocuments()}
            disabled={loading}
            className="flex items-center gap-1.5 text-sm text-mentis-600 hover:text-mentis-700 disabled:opacity-50 transition-colors"
          >
            <svg
              className={loading ? 'animate-spin' : ''}
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
            </svg>
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-2">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {/* Table */}
        {!loading && documents.length > 0 && (
          <div className="overflow-hidden border border-gray-200 rounded-xl shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Chunks
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate" title={doc.title}>
                      {doc.title}
                    </td>
                    <td className="px-4 py-3">
                      <span className={statusBadge(doc.status)}>{doc.status}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right tabular-nums">
                      {doc.chunk_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDate(doc.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && documents.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            <svg
              className="mx-auto mb-4 text-gray-300"
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm">No documents yet. Use Harvest to ingest papers.</p>
          </div>
        )}
      </div>
    </div>
  )
}
