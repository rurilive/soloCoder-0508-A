import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import AdvancedA from './pages/AdvancedA'
import AdvancedB from './pages/AdvancedB'
import Services from './pages/Services'
import Consulting from './pages/Consulting'
import Support from './pages/Support'
import About from './pages/About'
import './App.css'

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="app">
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="products" element={<Products />} />
              <Route path="products/list" element={<ProductList />} />
              <Route path="products/detail" element={<ProductDetail />} />
              <Route path="products/advanced/a" element={<AdvancedA />} />
              <Route path="products/advanced/b" element={<AdvancedB />} />
              <Route path="services" element={<Services />} />
              <Route path="services/consulting" element={<Consulting />} />
              <Route path="services/support" element={<Support />} />
              <Route path="about" element={<About />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
