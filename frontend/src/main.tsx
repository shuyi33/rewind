import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { I18nProvider } from './i18n'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'
import './styles/extra.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
      <App />
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>,
)
