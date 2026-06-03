import { NavLink, Outlet } from 'react-router-dom'

interface NavItem {
  to: string
  label: string
  icon: string // inline SVG path data
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: 'Chat',
    icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  },
  {
    to: '/papers',
    label: 'Papers',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  },
  {
    to: '/documents',
    label: 'Documents',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    to: '/harvest',
    label: 'Harvest',
    icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
  },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-52 bg-mentis-800 text-white flex flex-col shrink-0">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-mentis-700">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-white rounded-md flex items-center justify-center">
              <span className="text-mentis-800 font-bold text-sm leading-none">M</span>
            </div>
            <div>
              <p className="text-white font-semibold text-sm leading-tight">Mentis</p>
              <p className="text-mentis-300 text-xs leading-tight">Research Assistant</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-mentis-600 text-white'
                    : 'text-mentis-200 hover:bg-mentis-700 hover:text-white'
                }`
              }
            >
              <svg
                className="shrink-0"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={icon} />
              </svg>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-mentis-700">
          <p className="text-mentis-400 text-xs">Powered by Claude</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
