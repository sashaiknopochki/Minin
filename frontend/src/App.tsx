import { useAuth } from './contexts/AuthContext'
import HomePage from './components/HomePage'
import LanguageSetup from './components/LanguageSetup'
import './App.css'

function App() {
  const { user, loading } = useAuth()

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  // Check if user needs onboarding (logged in but no languages set)
  const needsOnboarding = user && (!user.translator_languages || user.translator_languages.length === 0)

  if (needsOnboarding) {
    return <LanguageSetup />
  }

  return <HomePage />
}

export default App
