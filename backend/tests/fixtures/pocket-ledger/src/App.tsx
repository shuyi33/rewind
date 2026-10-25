import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import CreateEntry from './pages/CreateEntry'
import Charts from './pages/Charts'
import Archive from './pages/Archive'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/create" element={<CreateEntry />} />
      <Route path="/charts/:id" element={<Charts />} />
      <Route path="/archive" element={<Archive />} />
    </Routes>
  )
}
