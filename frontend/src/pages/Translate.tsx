import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { X, Loader2, Copy, Check } from "lucide-react";
import EtherealTorusFlow from "@/components/EtherealTorusFlow";
import { QuizDialog } from "@/components/QuizDialog";

interface TranslationResult {
  [language: string]: [string, string, string][];
}

interface QuizData {
  quiz_attempt_id: number;
  question: string;
  options: string[];
  question_type: string;
  phrase_id: number;
}

interface QuizResult {
  was_correct: boolean;
  correct_answer: string;
  user_answer: string;
}

export default function Translate() {
  const { languages, loading: languagesLoading, error: languagesError } = useLanguageContext();
  const { user } = useAuth();
  const navigate = useNavigate();

  // Track selected language for each input
  const [lang1, setLang1] = useState("ru");
  const [lang2, setLang2] = useState("en");
  const [lang3, setLang3] = useState("de");

  // Track text values for each textarea
  const [text1, setText1] = useState("");
  const [text2, setText2] = useState("");
  const [text3, setText3] = useState("");

  // Track structured translations for each field
  const [translations1, setTranslations1] = useState<[string, string, string][] | null>(null);
  const [translations2, setTranslations2] = useState<[string, string, string][] | null>(null);
  const [translations3, setTranslations3] = useState<[string, string, string][] | null>(null);

  // Track which field was last edited (determines source language)
  const [sourceField, setSourceField] = useState<1 | 2 | 3 | null>(null);

  // Track translation state
  const [translating, setTranslating] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);

  // Track copied state
  const [copiedField, setCopiedField] = useState<1 | 2 | 3 | null>(null);

  // Quiz state
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizData, setQuizData] = useState<QuizData | null>(null);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Get browser/OS language
  const getBrowserLanguage = (): string => {
    const browserLang = navigator.language.split('-')[0];
    return browserLang;
  };

  // Get native language based on auth state
  const getNativeLanguage = (): string => {
    if (user && user.primary_language_code) {
      const userLang = languages.find(l => l.code === user.primary_language_code);
      return userLang ? userLang.en_name : "English";
    } else {
      const browserLangCode = getBrowserLanguage();
      const browserLang = languages.find(l => l.code === browserLangCode);
      return browserLang ? browserLang.en_name : "English";
    }
  };

  // Helper function to get language name by code
  const getLanguageName = (code: string) => {
    const lang = languages.find((l) => l.code === code);
    return lang ? lang.en_name : code;
  };

  // Initialize languages on mount
  useEffect(() => {
    if (languages.length === 0) return;

    const popularLanguages = ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"];
    const browserLangCode = getBrowserLanguage();

    if (user && user.primary_language_code && user.translator_languages) {
      const primaryLang = user.primary_language_code;
      const translatorLangs = user.translator_languages.filter(
        (lang: string) => lang !== primaryLang
      );

      setLang1(primaryLang);
      setLang2(translatorLangs[0] || "en");
      setLang3(translatorLangs[1] || "de");
    } else {
      const primaryLang = browserLangCode;
      const otherLangs = popularLanguages.filter(
        lang => lang !== primaryLang && languages.some(l => l.code === lang)
      );

      setLang1(primaryLang);
      setLang2(otherLangs[0] || "es");
      setLang3(otherLangs[1] || "de");
    }
  }, [languages, user]);

  // Function to call translation API
  const translateText = async (
    text: string,
    sourceLang: string,
    targetLangs: string[]
  ) => {
    try {
      setTranslating(true);
      setTranslationError(null);

      const response = await fetch("/translation/translate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          source_language: getLanguageName(sourceLang),
          target_languages: targetLangs.map(getLanguageName),
          native_language: getNativeLanguage(),
          model: "gpt-4.1-mini",
        }),
      });

      const data = await response.json();

      if (data.success) {
        return {
          translations: data.translations,
          source_info: data.source_info
        };
      } else {
        setTranslationError(data.error || "Translation failed");
        return null;
      }
    } catch (error) {
      setTranslationError(
        error instanceof Error ? error.message : "Network error"
      );
      return null;
    } finally {
      setTranslating(false);
    }
  };

  // Handle text change with debouncing
  const handleTextChange = (
    fieldNumber: 1 | 2 | 3,
    value: string
  ) => {
    if (fieldNumber === 1) setText1(value);
    else if (fieldNumber === 2) setText2(value);
    else setText3(value);

    if (fieldNumber === 1) setTranslations1(null);
    else if (fieldNumber === 2) setTranslations2(null);
    else setTranslations3(null);

    setSourceField(fieldNumber);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!value.trim()) {
      if (fieldNumber === 1) {
        setText2("");
        setText3("");
      } else if (fieldNumber === 2) {
        setText1("");
        setText3("");
      } else {
        setText1("");
        setText2("");
      }
      return;
    }

    debounceTimerRef.current = setTimeout(async () => {
      const sourceLang = fieldNumber === 1 ? lang1 : fieldNumber === 2 ? lang2 : lang3;
      const targetLangs =
        fieldNumber === 1
          ? [lang2, lang3]
          : fieldNumber === 2
          ? [lang1, lang3]
          : [lang1, lang2];

      const result = await translateText(value, sourceLang, targetLangs);

      if (result) {
        const { translations, source_info } = result;

        const targetLangNames = targetLangs.map(getLanguageName);
        const translatedTexts = targetLangNames.map((langName) => {
          const translation = translations[langName];
          if (!translation || !Array.isArray(translation) || translation.length === 0) return "";
          return translation[0][0];
        });

        const structuredTranslations = targetLangNames.map((langName) => {
          const translation = translations[langName];
          return translation || [];
        });

        const sourceInfoArray = source_info ? [source_info] : null;

        if (fieldNumber === 1) {
          setText2(translatedTexts[0]);
          setText3(translatedTexts[1]);
          setTranslations1(sourceInfoArray);
          setTranslations2(structuredTranslations[0]);
          setTranslations3(structuredTranslations[1]);
        } else if (fieldNumber === 2) {
          setText1(translatedTexts[0]);
          setText3(translatedTexts[1]);
          setTranslations1(structuredTranslations[0]);
          setTranslations2(sourceInfoArray);
          setTranslations3(structuredTranslations[1]);
        } else {
          setText1(translatedTexts[0]);
          setText2(translatedTexts[1]);
          setTranslations1(structuredTranslations[0]);
          setTranslations2(structuredTranslations[1]);
          setTranslations3(sourceInfoArray);
        }
      }
    }, 1000);
  };

  // Clear field function
  const clearField = (fieldNumber: 1 | 2 | 3) => {
    setText1("");
    setText2("");
    setText3("");
    setTranslations1(null);
    setTranslations2(null);
    setTranslations3(null);
    setSourceField(null);
    setTranslationError(null);
  };

  // Copy field function
  const copyField = async (fieldNumber: 1 | 2 | 3) => {
    const text = fieldNumber === 1 ? text1 : fieldNumber === 2 ? text2 : text3;

    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldNumber);

      setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  // Quiz handlers
  const handleQuizSubmit = (answer: string) => {
    if (!quizData) return;

    // For now, using mock logic (backend API will provide the correct answer)
    const isCorrect = answer === "cat"; // This will come from backend

    const result: QuizResult = {
      was_correct: isCorrect,
      correct_answer: "cat", // This will come from backend
      user_answer: answer,
    };

    setQuizResult(result);
    console.log("Quiz result:", result);
  };

  const handleQuizSkip = () => {
    setShowQuiz(false);
    setQuizData(null);
    setQuizResult(null);
  };

  const handleQuizContinue = () => {
    // Reset to show new quiz
    setQuizResult(null);
    // In real app, this would fetch a new quiz from backend
    // For now, just close the dialog
    setShowQuiz(false);
    setQuizData(null);
  };

  return (
    <div>
      {/* EtherealTorusFlow Animation Background - Only for logged-out users */}
      {!user && (
        <div className="absolute left-0 w-full flex justify-center pointer-events-none z-0" style={{ top: '-96px' }}>
          <EtherealTorusFlow />
        </div>
      )}

      {/* Hero Text - Only for logged-out users */}
      {!user && (
        <div className="w-full my-8 pt-24">
          <div className="w-full flex flex-col items-center justify-center">
            <h2 className="w-full text-6xl md:text-7xl lg:text-8xl font-medium text-center px-8">
              Translate once.<br />Remember forever.
            </h2>
            <p className="w-full text-lg md:text-xl lg:text-2xl py-10 px-8 text-center">Translator for those who use more than two languages daily<br />
            with AI-powered quizzes increasing active vocabulary.</p>
            <Button
              onClick={() => navigate("/login")}
              className="h-9 px-4 py-2 shadow-sm"
            >
              Get Started
            </Button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="w-full pt-12 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
          {/* First Input */}
          <div className="flex flex-col gap-6">
            {user ? (
              <div className="text-base font-medium text-left">
                {getLanguageName(lang1)}
              </div>
            ) : (
              <Select value={lang1} onValueChange={setLang1} disabled={languagesLoading}>
                <SelectTrigger className="h-9 bg-background">
                  <SelectValue placeholder={languagesLoading ? "Loading languages..." : "Select language"} />
                </SelectTrigger>
                <SelectContent>
                  {languagesError ? (
                    <SelectItem value="error" disabled>Error loading languages</SelectItem>
                  ) : (
                    languages.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.en_name} ({lang.original_name})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            )}

            <div className="relative">
              <Textarea
                value={text1}
                onChange={(e) => handleTextChange(1, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang1)}`}
                className={`h-60 resize-none bg-background pr-10 text-xl ${
                  sourceField === 1 ? "ring-2 ring-primary" : ""
                } ${translating && sourceField === 1 ? "opacity-50" : ""}`}
                disabled={translating && sourceField !== 1}
              />
              {text1 && (
                <>
                  <button
                    onClick={() => clearField(1)}
                    className="absolute top-2 right-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Clear field"
                  >
                    <X className="h-5 w-5 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => copyField(1)}
                    className="absolute bottom-2 left-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Copy to clipboard"
                  >
                    {copiedField === 1 ? (
                      <Check className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <Copy className="h-5 w-5 text-muted-foreground" />
                    )}
                  </button>
                </>
              )}
              {translating && sourceField === 1 && (
                <div className="absolute bottom-2 right-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>

            {translations1 && translations1.length > 0 && (
              <div className="flex flex-col gap-3 p-4 rounded-md border border-border bg-muted/30 text-left gap-y-6">
                {translations1.map(([word, grammarInfo, context], index) => (
                  <div key={index} className="flex flex-col gap-2">
                    <div className="text-base font-medium">{word}</div>
                    <div className="text-xs text-muted-foreground">{grammarInfo}</div>
                    <div className="text-sm text-muted-foreground">{context}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Second Input */}
          <div className="flex flex-col gap-6">
            {user ? (
              <div className="text-base font-medium text-left">
                {getLanguageName(lang2)}
              </div>
            ) : (
              <Select value={lang2} onValueChange={setLang2} disabled={languagesLoading}>
                <SelectTrigger className="h-9 bg-background">
                  <SelectValue placeholder={languagesLoading ? "Loading languages..." : "Select language"} />
                </SelectTrigger>
                <SelectContent>
                  {languagesError ? (
                    <SelectItem value="error" disabled>Error loading languages</SelectItem>
                  ) : (
                    languages.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.en_name} ({lang.original_name})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            )}

            <div className="relative">
              <Textarea
                value={text2}
                onChange={(e) => handleTextChange(2, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang2)}`}
                className={`h-60 resize-none bg-background pr-10 text-xl ${
                  sourceField === 2 ? "ring-2 ring-primary" : ""
                } ${translating && sourceField === 2 ? "opacity-50" : ""}`}
                disabled={translating && sourceField !== 2}
              />
              {text2 && (
                <>
                  <button
                    onClick={() => clearField(2)}
                    className="absolute top-2 right-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Clear field"
                  >
                    <X className="h-5 w-5 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => copyField(2)}
                    className="absolute bottom-2 left-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Copy to clipboard"
                  >
                    {copiedField === 2 ? (
                      <Check className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <Copy className="h-5 w-5 text-muted-foreground" />
                    )}
                  </button>
                </>
              )}
              {translating && sourceField === 2 && (
                <div className="absolute bottom-2 right-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>

            {translations2 && translations2.length > 0 && (
              <div className="flex flex-col gap-3 p-4 rounded-md border border-border bg-muted/30 text-left gap-y-6">
                {translations2.map(([word, grammarInfo, context], index) => (
                  <div key={index} className="flex flex-col gap-2">
                    <div className="text-base font-medium">{word}</div>
                    <div className="text-xs text-muted-foreground">{grammarInfo}</div>
                    <div className="text-sm text-muted-foreground">{context}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Third Input */}
          <div className="flex flex-col gap-6">
            {user ? (
              <div className="text-base font-medium text-left">
                {getLanguageName(lang3)}
              </div>
            ) : (
              <Select value={lang3} onValueChange={setLang3} disabled={languagesLoading}>
                <SelectTrigger className="h-9 bg-background">
                  <SelectValue placeholder={languagesLoading ? "Loading languages..." : "Select language"} />
                </SelectTrigger>
                <SelectContent>
                  {languagesError ? (
                    <SelectItem value="error" disabled>Error loading languages</SelectItem>
                  ) : (
                    languages.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.en_name} ({lang.original_name})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            )}

            <div className="relative">
              <Textarea
                value={text3}
                onChange={(e) => handleTextChange(3, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang3)}`}
                className={`h-60 resize-none bg-background pr-10 text-xl ${
                  sourceField === 3 ? "ring-2 ring-primary" : ""
                } ${translating && sourceField === 3 ? "opacity-50" : ""}`}
                disabled={translating && sourceField !== 3}
              />
              {text3 && (
                <>
                  <button
                    onClick={() => clearField(3)}
                    className="absolute top-2 right-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Clear field"
                  >
                    <X className="h-5 w-5 text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => copyField(3)}
                    className="absolute bottom-2 left-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
                    aria-label="Copy to clipboard"
                  >
                    {copiedField === 3 ? (
                      <Check className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <Copy className="h-5 w-5 text-muted-foreground" />
                    )}
                  </button>
                </>
              )}
              {translating && sourceField === 3 && (
                <div className="absolute bottom-2 right-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>

            {translations3 && translations3.length > 0 && (
              <div className="flex flex-col gap-3 p-4 rounded-md border border-border bg-muted/30 text-left gap-y-6">
                {translations3.map(([word, grammarInfo, context], index) => (
                  <div key={index} className="flex flex-col gap-2">
                    <div className="text-base font-medium">{word}</div>
                    <div className="text-xs text-muted-foreground">{grammarInfo}</div>
                    <div className="text-sm text-muted-foreground">{context}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {translationError && (
          <div className="mt-6 p-4 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">
              Translation error: {translationError}
            </p>
          </div>
        )}

        {/* Test Quiz Button - For testing only */}
        {user && (
          <div className="mt-6 flex justify-center">
            <Button
              onClick={() => {
                const testQuiz: QuizData = {
                  quiz_attempt_id: 1,
                  question: "What is the English translation of 'Katze'?",
                  options: ["cat", "dog", "house", "tree"],
                  question_type: "multiple_choice_target",
                  phrase_id: 123,
                };
                setQuizData(testQuiz);
                setShowQuiz(true);
                setQuizResult(null);
              }}
              variant="outline"
            >
              Test Quiz Dialog
            </Button>
          </div>
        )}
      </main>

      {/* How it works section - Only for logged-out users */}
      {!user && (
        <section className="w-full py-16 mt-16">
          <h2 className="text-4xl font-medium text-left mb-12">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold text-left">1</div>
              <p className="text-lg">Set your native language and foreign languages that you learn and use.</p>
            </div>

            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold text-left">2</div>
              <p className="text-lg">Enter a word in any language and receive a translation to your other languages.</p>
            </div>

            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold text-left">3</div>
              <p className="text-lg">Solve quizzes about the words that you have translated in order to remember them.</p>
            </div>
          </div>
        </section>
      )}

      {/* Problems it solves section - Only for logged-out users */}
      {!user && (
        <section className="w-full py-16 mt-16">
          <h2 className="text-4xl font-medium text-left mb-12">Problems it solves</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex flex-col text-left gap-4">
              <h3 className="text-2xl font-semibold">Multi-directional Translation: <br />Stop switching translation directions.</h3>
              <p className="text-lg">You speak one language at home, another on the street, and English at work. But your translator only shows two languages at a time. With Minin, type a word in any of your languages and instantly see translations in all the others. No more switching directions. No more juggling tabs. Just search once and see all languages that you use daily side by side.</p>
            </div>

            <div className="flex flex-col text-left gap-4">
              <h3 className="text-2xl font-semibold">Bookmarks don't teach you. Quizzes do: <br />Stop looking up the same words.</h3>
              <p className="text-lg">You look up this word for the third time this month. You even saved it, but favorites lists don't help you remember — they just pile up. Minin is different. After every few searches, you get a quick and smart quiz on words you've looked up. The app tracks what you have learned, and what you keep forgetting and turns translations into lasting & active vocabulary.</p>
            </div>
          </div>
        </section>
      )}

      {/* Large minin branding - For logged-out users */}
      {!user && (
        <section className="w-full py-0">
          <h2 className="w-full text-[120px] md:text-[160px] lg:text-[480px] font-bold text-center">minin</h2>
          <p className="text-lg">Designed and Developed by<a href='http://linkedin.com/in/aleksandr.sudin'> Sasha — Hire me!</a></p>
        </section>
      )}

      {/* Quiz Dialog */}
      {quizData && (
        <QuizDialog
          open={showQuiz}
          onOpenChange={setShowQuiz}
          quizData={quizData}
          onSubmit={handleQuizSubmit}
          onSkip={handleQuizSkip}
          onContinue={handleQuizContinue}
          result={quizResult}
        />
      )}
    </div>
  );
}