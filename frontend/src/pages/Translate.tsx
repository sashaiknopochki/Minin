import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import EtherealTorusFlow from "@/components/EtherealTorusFlow";
import { QuizDialog } from "@/components/QuizDialog";
import { LanguageInput } from "@/components/LanguageInput";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

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

interface LanguageField {
  id: string;
  languageCode: string;
  text: string;
  translations: [string, string, string][] | null;
  spellingSuggestion: string | null;
}

export default function Translate() {
  const {
    languages,
    loading: languagesLoading,
    error: languagesError,
  } = useLanguageContext();
  const { user } = useAuth();
  const navigate = useNavigate();

  // Array-based state for dynamic language fields
  const [fields, setFields] = useState<LanguageField[]>([]);
  const [sourceFieldId, setSourceFieldId] = useState<string | null>(null);
  const [copiedFieldId, setCopiedFieldId] = useState<string | null>(null);

  // Track translation state
  const [translating, setTranslating] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);

  // Quiz state
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizData, setQuizData] = useState<QuizData | null>(null);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [quizLoading, setQuizLoading] = useState(false);

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Get browser/OS language
  const getBrowserLanguage = (): string => {
    const browserLang = navigator.language.split("-")[0];
    return browserLang;
  };

  // Get native language based on auth state
  const getNativeLanguage = (): string => {
    if (user && user.primary_language_code) {
      const userLang = languages.find(
        (l) => l.code === user.primary_language_code,
      );
      return userLang ? userLang.en_name : "English";
    } else {
      const browserLangCode = getBrowserLanguage();
      const browserLang = languages.find((l) => l.code === browserLangCode);
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

    if (user && user.primary_language_code && user.translator_languages) {
      // Build fields: primary + all translator languages
      const allLangCodes = [
        user.primary_language_code,
        ...user.translator_languages,
      ];

      const initialFields = allLangCodes.map((code, index) => ({
        id: `field-${index}`,
        languageCode: code,
        text: "",
        translations: null,
        spellingSuggestion: null,
      }));

      setFields(initialFields);
    } else {
      // Guest users: default to 3 languages
      const browserLangCode = getBrowserLanguage();
      const popularLanguages = [
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "zh",
        "ja",
        "ko",
      ];
      const otherLangs = popularLanguages.filter(
        (lang) =>
          lang !== browserLangCode && languages.some((l) => l.code === lang),
      );

      const guestLangs = [
        browserLangCode,
        otherLangs[0] || "es",
        otherLangs[1] || "de",
      ];
      const guestFields = guestLangs.map((code, index) => ({
        id: `field-${index}`,
        languageCode: code,
        text: "",
        translations: null,
        spellingSuggestion: null,
      }));

      setFields(guestFields);
    }
  }, [languages, user]);

  // Function to call translation API
  const translateText = async (
    text: string,
    sourceLang: string,
    targetLangs: string[],
  ) => {
    try {
      setTranslating(true);
      setTranslationError(null);

      const response = await apiFetch("/translation/translate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          source_language: getLanguageName(sourceLang),
          target_languages: targetLangs.map(getLanguageName),
          native_language: getNativeLanguage(),
          // Let backend choose model based on LLM_PROVIDER env var
        }),
      });

      const data = await response.json();

      // Debug: Log quiz trigger information
      console.log("Translation response:", {
        should_show_quiz: data.should_show_quiz,
        quiz_phrase_id: data.quiz_phrase_id,
        searches_until_next_quiz: data.searches_until_next_quiz,
        spelling_issue: data.spelling_issue,
      });

      if (data.success) {
        // Check for spelling issue
        if (data.spelling_issue) {
          return {
            spellingIssue: true,
            sentWord: data.sent_word,
            correctWord: data.correct_word,
          };
        }

        return {
          spellingIssue: false,
          translations: data.translations,
          source_info: data.source_info,
          shouldShowQuiz: data.should_show_quiz,
          quizPhraseId: data.quiz_phrase_id,
        };
      } else {
        setTranslationError(data.error || "Translation failed");
        return null;
      }
    } catch (error) {
      setTranslationError(
        error instanceof Error ? error.message : "Network error",
      );
      return null;
    } finally {
      setTranslating(false);
    }
  };

  // Handle spelling suggestion click
  const handleSpellingSuggestionClick = (
    fieldId: string,
    correctWord: string,
  ) => {
    // Clear all spelling suggestions and update text
    setFields((prev) =>
      prev.map((f) =>
        f.id === fieldId
          ? { ...f, text: correctWord, spellingSuggestion: null }
          : { ...f, spellingSuggestion: null },
      ),
    );

    setSourceFieldId(fieldId);

    // Trigger translation with the correct word
    const sourceField = fields.find((f) => f.id === fieldId);
    if (!sourceField) return;

    const targetLangs = fields
      .filter((f) => f.id !== fieldId)
      .map((f) => f.languageCode);

    translateText(correctWord, sourceField.languageCode, targetLangs).then(
      (result) => {
        if (result && !result.spellingIssue) {
          const { translations, source_info, shouldShowQuiz, quizPhraseId } =
            result;

          const otherFields = fields.filter((f) => f.id !== fieldId);
          const targetLangNames = targetLangs.map(getLanguageName);

          const translatedTexts = targetLangNames.map((langName) => {
            const translation = translations[langName];
            if (
              !translation ||
              !Array.isArray(translation) ||
              translation.length === 0
            )
              return "";
            return translation[0][0];
          });

          const structuredTranslations = targetLangNames.map((langName) => {
            return translations[langName] || [];
          });

          const sourceInfoArray = source_info ? [source_info] : null;

          setFields((prev) =>
            prev.map((f) => {
              if (f.id === fieldId) {
                return { ...f, translations: sourceInfoArray };
              } else {
                const index = otherFields.findIndex((of) => of.id === f.id);
                return {
                  ...f,
                  text: translatedTexts[index] || "",
                  translations: structuredTranslations[index] || null,
                };
              }
            }),
          );

          if (user && shouldShowQuiz && quizPhraseId) {
            setTimeout(() => {
              fetchAndShowQuiz(quizPhraseId);
            }, 2500);
          }
        }
      },
    );
  };

  // Handle text change with debouncing
  const handleTextChange = (fieldId: string, value: string) => {
    // Update the specific field and clear all spelling suggestions
    setFields((prev) =>
      prev.map((f) =>
        f.id === fieldId
          ? { ...f, text: value, translations: null, spellingSuggestion: null }
          : { ...f, spellingSuggestion: null },
      ),
    );

    setSourceFieldId(fieldId);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!value.trim()) {
      // Clear all other fields
      setFields((prev) => prev.map((f) => ({ ...f, text: "" })));
      return;
    }

    debounceTimerRef.current = setTimeout(async () => {
      const sourceField = fields.find((f) => f.id === fieldId);
      if (!sourceField) return;

      // Get all other languages as targets
      const targetLangs = fields
        .filter((f) => f.id !== fieldId)
        .map((f) => f.languageCode);

      const result = await translateText(
        value,
        sourceField.languageCode,
        targetLangs,
      );

      if (result) {
        // Handle spelling issue
        if (result.spellingIssue) {
          setFields((prev) =>
            prev.map((f) =>
              f.id === fieldId
                ? { ...f, spellingSuggestion: result.correctWord }
                : { ...f, spellingSuggestion: null },
            ),
          );
          return;
        }

        const { translations, source_info, shouldShowQuiz, quizPhraseId } =
          result;

        // Distribute translations to all fields
        const otherFields = fields.filter((f) => f.id !== fieldId);
        const targetLangNames = targetLangs.map(getLanguageName);

        const translatedTexts = targetLangNames.map((langName) => {
          const translation = translations[langName];
          if (
            !translation ||
            !Array.isArray(translation) ||
            translation.length === 0
          )
            return "";
          return translation[0][0];
        });

        const structuredTranslations = targetLangNames.map((langName) => {
          return translations[langName] || [];
        });

        const sourceInfoArray = source_info ? [source_info] : null;

        setFields((prev) =>
          prev.map((f) => {
            if (f.id === fieldId) {
              return { ...f, translations: sourceInfoArray };
            } else {
              const index = otherFields.findIndex((of) => of.id === f.id);
              return {
                ...f,
                text: translatedTexts[index] || "",
                translations: structuredTranslations[index] || null,
              };
            }
          }),
        );

        // Trigger quiz after delay if needed (only for logged-in users)
        if (user && shouldShowQuiz && quizPhraseId) {
          setTimeout(() => {
            fetchAndShowQuiz(quizPhraseId);
          }, 2500);
        }
      }
    }, 1000);
  };

  // Clear field function
  const clearField = () => {
    // Clear ALL fields (maintains current behavior)
    setFields((prev) =>
      prev.map((f) => ({
        ...f,
        text: "",
        translations: null,
        spellingSuggestion: null,
      })),
    );
    setSourceFieldId(null);
    setTranslationError(null);
  };

  // Copy field function
  const copyField = async (fieldId: string) => {
    const field = fields.find((f) => f.id === fieldId);
    if (!field?.text) return;

    try {
      await navigator.clipboard.writeText(field.text);
      setCopiedFieldId(fieldId);

      setTimeout(() => {
        setCopiedFieldId(null);
      }, 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  // Handle language change (guest users only)
  const handleLanguageChange = (fieldId: string, newLanguageCode: string) => {
    setFields((prev) =>
      prev.map((f) =>
        f.id === fieldId ? { ...f, languageCode: newLanguageCode } : f,
      ),
    );
  };

  // Fetch and show quiz from backend
  const fetchAndShowQuiz = async (phraseId: number) => {
    try {
      console.log("Fetching quiz from:", `/quiz/next?phrase_id=${phraseId}`);
      const response = await apiFetch(`/quiz/next?phrase_id=${phraseId}`);

      console.log("Quiz response status:", response.status);
      console.log(
        "Quiz response headers:",
        response.headers.get("content-type"),
      );

      // Log raw response text first to see what we're getting
      const responseText = await response.text();
      console.log(
        "Quiz response body (first 200 chars):",
        responseText.substring(0, 200),
      );

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error("Failed to parse response as JSON:", parseError);
        console.error("Response was:", responseText.substring(0, 500));
        return;
      }

      if (response.ok) {
        const quizData: QuizData = {
          quiz_attempt_id: data.quiz_attempt_id,
          question: data.question,
          options: data.options,
          question_type: data.question_type,
          phrase_id: data.phrase_id,
        };

        setQuizData(quizData);
        setShowQuiz(true);
        setQuizResult(null);
      } else {
        // Silently skip if no quiz available (404 error)
        console.log("No quiz available:", data.error);
      }
    } catch (error) {
      console.error("Failed to fetch quiz:", error);
    }
  };

  // Quiz handlers
  const handleQuizSubmit = async (answer: string) => {
    if (!quizData) return;

    try {
      const response = await apiFetch("/quiz/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quiz_attempt_id: quizData.quiz_attempt_id,
          user_answer: answer,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        const result: QuizResult = {
          was_correct: data.was_correct,
          correct_answer: data.correct_answer,
          user_answer: answer,
        };

        setQuizResult(result);
      } else {
        console.error("Failed to submit quiz answer:", data.error);
      }
    } catch (error) {
      console.error("Failed to submit quiz answer:", error);
    }
  };

  const handleQuizSkip = async () => {
    if (!quizData) return;

    try {
      await apiFetch("/quiz/skip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phrase_id: quizData.phrase_id,
        }),
      });
    } catch (error) {
      console.error("Failed to skip quiz:", error);
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
      console.log("Fetching next quiz...");
      const response = await apiFetch("/quiz/next");

      console.log("Next quiz response status:", response.status);

      // Log raw response text first to see what we're getting
      const responseText = await response.text();
      console.log(
        "Next quiz response (first 200 chars):",
        responseText.substring(0, 200),
      );

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error(
          "Failed to parse next quiz response as JSON:",
          parseError,
        );
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
          phrase_id: data.phrase_id,
        };

        setQuizData(newQuizData);
        // Keep showQuiz true so dialog stays open
      } else {
        // No more quizzes available, close dialog
        console.log("No more quizzes available:", data.error);
        setShowQuiz(false);
        setQuizData(null);
      }
    } catch (error) {
      console.error("Failed to fetch next quiz:", error);
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
        <div
          className="absolute left-0 w-full flex justify-center pointer-events-none z-0"
          style={{ top: "-96px" }}
        >
          <EtherealTorusFlow />
        </div>
      )}

      {/* Hero Text - Only for logged-out users */}
      {!user && (
        <div className="w-full my-8 pt-24">
          <div className="w-full flex flex-col items-center justify-center">
            <h2 className="w-full text-5xl md:text-6xl lg:text-7xl font-normal font-baskerville leading-tight text-center px-8">
              Translate once.
            </h2>
            <h2 className="w-full text-5xl md:text-6xl lg:text-7xl font-normal font-baskerville leading-tight text-center px-8 pt-3">
              Remember forever.
            </h2>
            <p className="w-full text-lg md:text-xl lg:text-2xl py-10 px-8 text-center">
              Translator for those who use more than two languages daily
              <br />
              with AI-powered quizzes increasing active vocabulary.
            </p>
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
        <div
          className={cn(
            "grid gap-6 md:gap-8",
            fields.length === 2
              ? "grid-cols-1 md:grid-cols-2"
              : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
          )}
        >
          {fields.map((field) => (
            <div key={field.id} className="flex flex-col gap-2">
              {/* Language selector for non-authenticated users */}
              {!user && (
                <Select
                  value={field.languageCode}
                  onValueChange={(value) =>
                    handleLanguageChange(field.id, value)
                  }
                  disabled={languagesLoading}
                >
                  <SelectTrigger className="h-9 bg-background">
                    <SelectValue
                      placeholder={
                        languagesLoading
                          ? "Loading languages..."
                          : "Select language"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {languagesError ? (
                      <SelectItem value="error" disabled>
                        Error loading languages
                      </SelectItem>
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

              {/* Language Input */}
              <LanguageInput
                languageName={getLanguageName(field.languageCode)}
                languageCode={field.languageCode}
                value={field.text}
                onChange={(value) => handleTextChange(field.id, value)}
                onClear={clearField}
                onCopy={() => copyField(field.id)}
                isSource={sourceFieldId === field.id}
                isTranslating={translating}
                isCopied={copiedFieldId === field.id}
                placeholder={`Enter text in ${getLanguageName(field.languageCode)}`}
                spellingSuggestion={field.spellingSuggestion}
                onSpellingSuggestionClick={(correction) =>
                  handleSpellingSuggestionClick(field.id, correction)
                }
                translations={field.translations}
                showLanguageName={!!user}
              />
            </div>
          ))}
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
          <h2 className="text-4xl font-bold font-baskerville leading-snug text-left mb-12">
            How it works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold font-baskerville leading-relaxed text-left">
                1
              </div>
              <p className="text-lg">
                Set your native language and foreign languages that you learn
                and use.
              </p>
            </div>

            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold font-baskerville leading-relaxed text-left">
                2
              </div>
              <p className="text-lg">
                Enter a word in any language and receive a translation to your
                other languages.
              </p>
            </div>

            <div className="flex flex-col items-center text-left gap-4">
              <div className="text-3xl font-bold font-baskerville leading-relaxed text-left">
                3
              </div>
              <p className="text-lg">
                Solve quizzes about the words that you have translated in order
                to remember them.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Quiz Cards section - Only for logged-out users */}
      {!user && (
        <section className="w-full py-16 mt-16">
          <h2 className="text-4xl font-bold font-baskerville leading-snug text-left mb-12">
            Try sample quizzes
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Beginner Quiz Card */}
            <div className="flex flex-col text-left gap-4 p-6 rounded-lg border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <span className="px-3 py-1 text-sm font-medium bg-gray-100 text-gray-800 rounded-full">
                  Beginner
                </span>
                <span className="text-sm text-muted-foreground">
                  Multiple Choice
                </span>
              </div>
              <h3 className="text-xl font-semibold mt-2">
                What does "Katze" mean in English?
              </h3>
              <div className="flex flex-col gap-2 mt-2">
                <div className="p-3 rounded-md border border-border hover:bg-muted/50 cursor-pointer transition-colors">
                  A) Dog
                </div>
                <div className="p-3 rounded-md border border-border hover:bg-muted/50 cursor-pointer transition-colors">
                  B) Cat
                </div>
                <div className="p-3 rounded-md border border-border hover:bg-muted/50 cursor-pointer transition-colors">
                  C) Bird
                </div>
                <div className="p-3 rounded-md border border-border hover:bg-muted/50 cursor-pointer transition-colors">
                  D) Fish
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Master basic vocabulary with simple recognition quizzes
              </p>
            </div>

            {/* Intermediate Quiz Card */}
            <div className="flex flex-col text-left gap-4 p-6 rounded-lg border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <span className="px-3 py-1 text-sm font-medium bg-gray-100 text-gray-800 rounded-full">
                  Intermediate
                </span>
                <span className="text-sm text-muted-foreground">
                  Fill in the Blank
                </span>
              </div>
              <h3 className="text-xl font-semibold mt-2">
                Complete the sentence:
              </h3>
              <div className="flex flex-col gap-3 mt-2">
                <p className="text-lg">Ich _____ gerne Bücher.</p>
                <p className="text-sm text-muted-foreground italic">
                  (I like to read books)
                </p>
                <div className="p-3 rounded-md border border-border bg-muted/30">
                  <input
                    type="text"
                    placeholder="Type your answer..."
                    className="w-full bg-transparent outline-none"
                    disabled
                  />
                </div>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Practice active recall with context-based questions
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Problems it solves section - Only for logged-out users */}
      {!user && (
        <section className="w-full py-16 mt-16">
          <h2 className="text-4xl font-bold font-baskerville leading-snug text-left mb-12">
            Problems it solves
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex flex-col text-left gap-4">
              <h3 className="text-2xl font-semibold">
                Multi-directional Translation: <br />
                Stop switching translation directions.
              </h3>
              <p className="text-lg">
                You speak one language at home, another on the street, and
                English at work. But your translator only shows two languages at
                a time. With Minin, type a word in any of your languages and
                instantly see translations in all the others. No more switching
                directions. No more juggling tabs. Just search once and see all
                languages that you use daily side by side.
              </p>
            </div>

            <div className="flex flex-col text-left gap-4">
              <h3 className="text-2xl font-semibold">
                Bookmarks don't teach you. Quizzes do: <br />
                Stop looking up the same words.
              </h3>
              <p className="text-lg">
                You look up this word for the third time this month. You even
                saved it, but favorites lists don't help you remember — they
                just pile up. Minin is different. After every few searches, you
                get a quick and smart quiz on words you've looked up. The app
                tracks what you have learned, and what you keep forgetting and
                turns translations into lasting & active vocabulary.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Large minin branding - For logged-out users */}
      {!user && (
        <section className="w-full py-0">
          <h2 className="w-full text-[120px] md:text-[160px] lg:text-[480px] font-bold text-center">
            minin
          </h2>
          <p className="text-lg">
            Designed and Developed by
            <a href="http://linkedin.com/in/aleksandr.sudin">
              {" "}
              Sasha — Hire me!
            </a>
          </p>
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
