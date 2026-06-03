import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import PapersPage from './pages/PapersPage'
import DocumentsPage from './pages/DocumentsPage'
import HarvestPage from './pages/HarvestPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<ChatPage />} />
        <Route path="/papers" element={<PapersPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/harvest" element={<HarvestPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
