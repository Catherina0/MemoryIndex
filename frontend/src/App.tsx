import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ContentDetailPage from './pages/ContentDetailPage'
import DashboardPage from './pages/DashboardPage'
import ArchiveListPage from './pages/ArchiveListPage'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/archives" element={<ArchiveListPage />} />
          <Route path="/content/:id" element={<ContentDetailPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
