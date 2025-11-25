import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { X, Loader2, Copy, Check } from "lucide-react";

interface TranslationResult {
  [language: string]: [string, string][];
}

export default function HomePage() {
  const { languages, loading: languagesLoading, error: languagesError } = useLanguageContext();

  // Track selected language for each input
  const [lang1, setLang1] = useState("ru");
  const [lang2, setLang2] = useState("en");
  const [lang3, setLang3] = useState("de");

  // Track text values for each textarea
  const [text1, setText1] = useState("");
  const [text2, setText2] = useState("");
  const [text3, setText3] = useState("");

  // Track which field was last edited (determines source language)
  const [sourceField, setSourceField] = useState<1 | 2 | 3 | null>(null);

  // Track translation state
  const [translating, setTranslating] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);

  // Track copied state
  const [copiedField, setCopiedField] = useState<1 | 2 | 3 | null>(null);

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Helper function to get language name by code
  const getLanguageName = (code: string) => {
    const lang = languages.find((l) => l.code === code);
    return lang ? lang.en_name : code;
  };

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
          native_language: "English", // TODO: Get from user settings
          model: "gpt-4.1-mini",
        }),
      });

      const data = await response.json();

      if (data.success) {
        return data.translations;
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
    // Update the text state
    if (fieldNumber === 1) setText1(value);
    else if (fieldNumber === 2) setText2(value);
    else setText3(value);

    // Set this field as the source
    setSourceField(fieldNumber);

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // If text is empty, clear other fields
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

    // Set new timer for auto-translate after 1 second
    debounceTimerRef.current = setTimeout(async () => {
      const sourceLang = fieldNumber === 1 ? lang1 : fieldNumber === 2 ? lang2 : lang3;
      const targetLangs =
        fieldNumber === 1
          ? [lang2, lang3]
          : fieldNumber === 2
          ? [lang1, lang3]
          : [lang1, lang2];

      const translations = await translateText(value, sourceLang, targetLangs);

      if (translations) {
        // Extract first translation for each language
        const targetLangNames = targetLangs.map(getLanguageName);
        const translatedTexts = targetLangNames.map((langName) => {
          const translation = translations[langName];
          return translation && translation[0] ? translation[0][0] : "";
        });

        // Update target fields
        if (fieldNumber === 1) {
          setText2(translatedTexts[0]);
          setText3(translatedTexts[1]);
        } else if (fieldNumber === 2) {
          setText1(translatedTexts[0]);
          setText3(translatedTexts[1]);
        } else {
          setText1(translatedTexts[0]);
          setText2(translatedTexts[1]);
        }
      }
    }, 1000);
  };

  // Clear field function
  const clearField = (fieldNumber: 1 | 2 | 3) => {
    if (fieldNumber === 1) {
      setText1("");
      setText2("");
      setText3("");
    } else if (fieldNumber === 2) {
      setText1("");
      setText2("");
      setText3("");
    } else {
      setText1("");
      setText2("");
      setText3("");
    }
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

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  return (
    <div>
      {/* Header */}
      <header className="w-full py-3">
        <div className="flex items-baseline justify-between">
          {/* Logo and Navigation */}
          <div className="flex items-baseline gap-4 sm:gap-6 md:gap-10">
            <h1 className="text-4xl font-bold text-foreground">minin</h1>

            <Tabs defaultValue="translate" className="w-auto">
              <TabsList className="h-auto bg-transparent p-0 gap-1">
                <TabsTrigger
                  value="translate"
                  className="px-4 py-2 data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:font-bold"
                >
                  Translate
                </TabsTrigger>
                <TabsTrigger
                  value="learn"
                  className="px-4 py-2 data-[state=active]:bg-transparent data-[state=active]:shadow-none"
                >
                  Learn
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Sign In Button */}
          <Button className="h-9 px-4 py-2 shadow-sm">
            Sign In
          </Button>
        </div>
      </header>

      {/* Main Content - Language Inputs */}
      <main className="w-full pt-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
          {/* First Input */}
          <div className="flex flex-col gap-6">
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

            <div className="relative">
              <Textarea
                value={text1}
                onChange={(e) => handleTextChange(1, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang1)}`}
                className={`h-40 resize-none bg-background pr-10 text-xl ${
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
          </div>

          {/* Second Input */}
          <div className="flex flex-col gap-6">
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

            <div className="relative">
              <Textarea
                value={text2}
                onChange={(e) => handleTextChange(2, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang2)}`}
                className={`h-40 resize-none bg-background pr-10 text-xl ${
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
          </div>

          {/* Third Input */}
          <div className="flex flex-col gap-6">
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

            <div className="relative">
              <Textarea
                value={text3}
                onChange={(e) => handleTextChange(3, e.target.value)}
                placeholder={`Enter text in ${getLanguageName(lang3)}`}
                className={`h-40 resize-none bg-background pr-10 text-xl ${
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
      </main>
    </div>
  );
}