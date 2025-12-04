import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Projects } from './pages/Projects'
import { Imports } from './pages/Imports'
import { Collections } from './pages/Collections'
import { Settings } from './pages/Settings'
import { Workers } from './pages/Workers'
import { Logs } from './pages/Logs'
import { BatchJobs } from './pages/BatchJobs'
import { ToastProvider } from './components/ui/toast'

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/imports" element={<Imports />} />
            <Route path="/collections" element={<Collections />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/workers" element={<Workers />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/batch" element={<BatchJobs />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ToastProvider>
  )
}

export default App
