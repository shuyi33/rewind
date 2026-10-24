import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import CreateStory from './pages/CreateStory'
import Editor from './pages/Editor'
import MyWorks from './pages/MyWorks'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/create" element={<CreateStory />} />
      <Route path="/editor/:id" element={<Editor />} />
      <Route path="/works" element={<MyWorks />} />
    </Routes>
  )
}
