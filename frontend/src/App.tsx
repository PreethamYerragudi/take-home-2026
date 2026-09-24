import { Link, Route, Routes } from "react-router-dom"

import { CatalogPage } from "@/pages/CatalogPage"
import { ProductPage } from "@/pages/ProductPage"

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Channel3 Store
          </Link>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/product/:slug" element={<ProductPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
