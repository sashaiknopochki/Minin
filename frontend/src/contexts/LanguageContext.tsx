import {createContext, useContext, type ReactNode } from 'react';
import type { Language } from '@/types/language';
import { useLanguages } from '@/hooks/useLanguages';

interface LanguageContextType {
  languages: Language[];
  loading: boolean;
  error: string | null;
  clearCache: () => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const languagesData = useLanguages();

  return (
    <LanguageContext.Provider value={languagesData}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguageContext() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguageContext must be used within a LanguageProvider');
  }
  return context;
}
