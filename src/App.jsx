import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import AdvancedA from './pages/AdvancedA'
import AdvancedB from './pages/AdvancedB'
import Consulting from './pages/Consulting'
import Support from './pages/Support'
import About from './pages/About'
import './App.css'

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="app">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/products" element={<Products />} />
              <Route path="/products/list" element={<ProductList />} />
              <Route path="/products/detail" element={<ProductDetail />} />
              <Route path="/products/advanced/a" element={<AdvancedA />} />
              <Route path="/products/advanced/b" element={<AdvancedB />} />
              <Route path="/services/consulting" element={<Consulting />} />
              <Route path="/services/support" element={<Support />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
