import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Scan from './pages/Scan'
import Report from './pages/Report'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/scan/:reportId" element={<Scan />} />
      <Route path="/report/:reportId" element={<Report />} />
    </Routes>
  )
}
