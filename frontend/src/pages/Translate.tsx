import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import EtherealTorusFlow from "@/components/EtherealTorusFlow";
import { QuizDialog } from "@/components/QuizDialog";
import { LanguageInput } from "@/components/LanguageInput";

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

  // Spelling suggestion state
  const [spellingSuggestion1, setSpellingSuggestion1] = useState<string | null>(null);
  const [spellingSuggestion2, setSpellingSuggestion2] = useState<string | null>(null);
  const [spellingSuggestion3, setSpellingSuggestion3] = useState<string | null>(null);

  // Quiz state
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizData, setQuizData] = useState<QuizData | null>(null);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [quizLoading, setQuizLoading] = useState(false);

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

      // Debug: Log quiz trigger information
      console.log('Translation response:', {
        should_show_quiz: data.should_show_quiz,
        quiz_phrase_id: data.quiz_phrase_id,
        searches_until_next_quiz: data.searches_until_next_quiz,
        spelling_issue: data.spelling_issue
      });

      if (data.success) {
        // Check for spelling issue
        if (data.spelling_issue) {
          return {
            spellingIssue: true,
            sentWord: data.sent_word,
            correctWord: data.correct_word
          };
        }

        return {
          spellingIssue: false,
          translations: data.translations,
          source_info: data.source_info,
          shouldShowQuiz: data.should_show_quiz,
          quizPhraseId: data.quiz_phrase_id
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

  // Handle spelling suggestion click
  const handleSpellingSuggestionClick = (fieldNumber: 1 | 2 | 3, correctWord: string) => {
    // Clear spelling suggestions
    setSpellingSuggestion1(null);
    setSpellingSuggestion2(null);
    setSpellingSuggestion3(null);

    // Update the text field with correct word
    if (fieldNumber === 1) setText1(correctWord);
    else if (fieldNumber === 2) setText2(correctWord);
    else setText3(correctWord);

    // Trigger translation with the correct word
    setSourceField(fieldNumber);

    // Call translation directly
    const sourceLang = fieldNumber === 1 ? lang1 : fieldNumber === 2 ? lang2 : lang3;
    const targetLangs =
      fieldNumber === 1
        ? [lang2, lang3]
        : fieldNumber === 2
        ? [lang1, lang3]
        : [lang1, lang2];

    translateText(correctWord, sourceLang, targetLangs).then(result => {
      if (result && !result.spellingIssue) {
        const { translations, source_info, shouldShowQuiz, quizPhraseId } = result;

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

        if (user && shouldShowQuiz && quizPhraseId) {
          setTimeout(() => {
            fetchAndShowQuiz(quizPhraseId);
          }, 2500);
        }
      }
    });
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

    // Clear ALL spelling suggestions when any input changes
    setSpellingSuggestion1(null);
    setSpellingSuggestion2(null);
    setSpellingSuggestion3(null);

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
        // Check for spelling issue
        if (result.spellingIssue) {
          // Set spelling suggestion for the source field
          if (fieldNumber === 1) {
            setSpellingSuggestion1(result.correctWord);
            setSpellingSuggestion2(null);
            setSpellingSuggestion3(null);
          } else if (fieldNumber === 2) {
            setSpellingSuggestion1(null);
            setSpellingSuggestion2(result.correctWord);
            setSpellingSuggestion3(null);
          } else {
            setSpellingSuggestion1(null);
            setSpellingSuggestion2(null);
            setSpellingSuggestion3(result.correctWord);
          }
          return;
        }

        const { translations, source_info, shouldShowQuiz, quizPhraseId } = result;

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

        // Trigger quiz after delay if needed (only for logged-in users)
        console.log('Quiz trigger check:', {
          user: !!user,
          shouldShowQuiz,
          quizPhraseId,
          willTrigger: !!(user && shouldShowQuiz && quizPhraseId)
        });

        if (user && shouldShowQuiz && quizPhraseId) {
          console.log('Setting quiz timeout...');
          setTimeout(() => {
            console.log('Fetching quiz now for phrase:', quizPhraseId);
            fetchAndShowQuiz(quizPhraseId);
          }, 2500); // 2.5 second delay
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

    // Clear all spelling suggestions when clearing
    setSpellingSuggestion1(null);
    setSpellingSuggestion2(null);
    setSpellingSuggestion3(null);
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

  // Fetch and show quiz from backend
  const fetchAndShowQuiz = async (phraseId: number) => {
    try {
      console.log('Fetching quiz from:', `/quiz/next?phrase_id=${phraseId}`);
      const response = await fetch(`/quiz/next?phrase_id=${phraseId}`);

      console.log('Quiz response status:', response.status);
      console.log('Quiz response headers:', response.headers.get('content-type'));

      // Log raw response text first to see what we're getting
      const responseText = await response.text();
      console.log('Quiz response body (first 200 chars):', responseText.substring(0, 200));

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        console.error('Response was:', responseText.substring(0, 500));
        return;
      }

      if (response.ok) {
        const quizData: QuizData = {
          quiz_attempt_id: data.quiz_attempt_id,
          question: data.question,
          options: data.options,
          question_type: data.question_type,
          phrase_id: data.phrase_id
        };

        setQuizData(quizData);
        setShowQuiz(true);
        setQuizResult(null);
      } else {
        // Silently skip if no quiz available (404 error)
        console.log('No quiz available:', data.error);
      }
    } catch (error) {
      console.error('Failed to fetch quiz:', error);
    }
  };

  // Quiz handlers
  const handleQuizSubmit = async (answer: string) => {
    if (!quizData) return;

    try {
      const response = await fetch('/quiz/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quiz_attempt_id: quizData.quiz_attempt_id,
          user_answer: answer
        })
      });

      const data = await response.json();

      if (response.ok) {
        const result: QuizResult = {
          was_correct: data.was_correct,
          correct_answer: data.correct_answer,
          user_answer: answer
        };

        setQuizResult(result);
      } else {
        console.error('Failed to submit quiz answer:', data.error);
      }
    } catch (error) {
      console.error('Failed to submit quiz answer:', error);
    }
  };

  const handleQuizSkip = async () => {
    if (!quizData) return;

    try {
      await fetch('/quiz/skip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phrase_id: quizData.phrase_id
        })
      });
    } catch (error) {
      console.error('Failed to skip quiz:', error);
    } finally {
      // Always close the dialog
      setShowQuiz(false);
      setQuizData(null);
      setQuizResult(null);
    }
  };

  const handleQuizContinue = async () => {
    // Reset result and show loading
    setQuizResult(null);
    setQuizLoading(true);

    // Fetch next quiz (without phrase_id to get any eligible phrase)
    try {
      console.log('Fetching next quiz...');
      const response = await fetch('/quiz/next');

      console.log('Next quiz response status:', response.status);

      // Log raw response text first to see what we're getting
      const responseText = await response.text();
      console.log('Next quiz response (first 200 chars):', responseText.substring(0, 200));

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error('Failed to parse next quiz response as JSON:', parseError);
        // No more quizzes available, close dialog
        setShowQuiz(false);
        setQuizData(null);
        return;
      }

      if (response.ok) {
        const newQuizData: QuizData = {
          quiz_attempt_id: data.quiz_attempt_id,
          question: data.question,
          options: data.options,
          question_type: data.question_type,
          phrase_id: data.phrase_id
        };

        setQuizData(newQuizData);
        // Keep showQuiz true so dialog stays open
      } else {
        // No more quizzes available, close dialog
        console.log('No more quizzes available:', data.error);
        setShowQuiz(false);
        setQuizData(null);
      }
    } catch (error) {
      console.error('Failed to fetch next quiz:', error);
      // Close dialog on error
      setShowQuiz(false);
      setQuizData(null);
    } finally {
      setQuizLoading(false);
    }
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
          {/* Language selector for non-authenticated users */}
          {!user && (
            <>
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
            </>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8 mt-6">
          {/* First Input */}
          <LanguageInput
            languageName={getLanguageName(lang1)}
            value={text1}
            onChange={(value) => handleTextChange(1, value)}
            onClear={() => clearField(1)}
            onCopy={() => copyField(1)}
            isSource={sourceField === 1}
            isTranslating={translating}
            isCopied={copiedField === 1}
            placeholder={`Enter text in ${getLanguageName(lang1)}`}
            spellingSuggestion={spellingSuggestion1}
            onSpellingSuggestionClick={(correction) => handleSpellingSuggestionClick(1, correction)}
            translations={translations1}
          />

          {/* Second Input */}
          <LanguageInput
            languageName={getLanguageName(lang2)}
            value={text2}
            onChange={(value) => handleTextChange(2, value)}
            onClear={() => clearField(2)}
            onCopy={() => copyField(2)}
            isSource={sourceField === 2}
            isTranslating={translating}
            isCopied={copiedField === 2}
            placeholder={`Enter text in ${getLanguageName(lang2)}`}
            spellingSuggestion={spellingSuggestion2}
            onSpellingSuggestionClick={(correction) => handleSpellingSuggestionClick(2, correction)}
            translations={translations2}
          />

          {/* Third Input */}
          <LanguageInput
            languageName={getLanguageName(lang3)}
            value={text3}
            onChange={(value) => handleTextChange(3, value)}
            onClear={() => clearField(3)}
            onCopy={() => copyField(3)}
            isSource={sourceField === 3}
            isTranslating={translating}
            isCopied={copiedField === 3}
            placeholder={`Enter text in ${getLanguageName(lang3)}`}
            spellingSuggestion={spellingSuggestion3}
            onSpellingSuggestionClick={(correction) => handleSpellingSuggestionClick(3, correction)}
            translations={translations3}
          />
        </div>

        {/* Error Message */}
        {translationError && (
          <div className="mt-6 p-4 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">
              Translation error: {translationError}
            </p>
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
          isLoading={quizLoading}
        />
      )}
    </div>
  );
}