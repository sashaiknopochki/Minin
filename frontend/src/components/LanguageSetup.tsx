import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { X, Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

export default function LanguageSetup() {
  const { languages, loading: languagesLoading } = useLanguageContext();
  const { user, checkAuth } = useAuth();

  const [nativeLanguage, setNativeLanguage] = useState<string>("");
  const [learningLanguages, setLearningLanguages] = useState<string[]>([]);
  const [availableLanguages, setAvailableLanguages] = useState<typeof languages>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track open state for combobox popovers
  const [nativeOpen, setNativeOpen] = useState(false);
  const [learningOpen, setLearningOpen] = useState<boolean[]>([]);

  // Initialize with browser language as default
  useEffect(() => {
    if (languages.length === 0) return;

    const browserLang = navigator.language.split('-')[0];
    const browserLanguage = languages.find(l => l.code === browserLang);

    if (browserLanguage && !nativeLanguage) {
      setNativeLanguage(browserLanguage.code);
    }
  }, [languages, nativeLanguage]);

  // Update available languages for learning (exclude native language)
  useEffect(() => {
    if (!nativeLanguage) {
      setAvailableLanguages(languages);
      return;
    }

    const filtered = languages.filter(l => l.code !== nativeLanguage);
    setAvailableLanguages(filtered);

    // Remove native language from learning languages if it was selected
    setLearningLanguages(prev => prev.filter(lang => lang !== nativeLanguage));
  }, [nativeLanguage, languages]);

  const addLearningLanguage = () => {
    if (learningLanguages.length >= 5) {
      setError("You can add up to 5 learning languages");
      return;
    }

    // Find first available language not already selected
    const nextLanguage = availableLanguages.find(
      lang => !learningLanguages.includes(lang.code)
    );

    if (nextLanguage) {
      setLearningLanguages([...learningLanguages, nextLanguage.code]);
      setError(null);
    }
  };

  const removeLearningLanguage = (code: string) => {
    setLearningLanguages(learningLanguages.filter(lang => lang !== code));
    setError(null);
  };

  const updateLearningLanguage = (index: number, newCode: string) => {
    const updated = [...learningLanguages];
    updated[index] = newCode;
    setLearningLanguages(updated);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!nativeLanguage) {
      setError("Please select your native language");
      return;
    }

    // Filter out empty strings from learning languages
    const validLearningLanguages = learningLanguages.filter(lang => lang !== '');

    if (validLearningLanguages.length === 0) {
      setError("Please add at least one learning language");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch("/auth/update-languages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          primary_language_code: nativeLanguage,
          translator_languages: validLearningLanguages,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Refresh user data to trigger navigation to HomePage
        await checkAuth();
      } else {
        setError(data.error || "Failed to save languages");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

      // Auto-add initial learning languages based on browser language
  useEffect(() => {
    if (learningLanguages.length === 0 && availableLanguages.length > 0 && nativeLanguage) {
      // If native language is NOT English, first learning language is English
      if (nativeLanguage !== 'en' && availableLanguages.some(l => l.code === 'en')) {
        setLearningLanguages(['en', '']);
      }
      // If native language IS English, first learning language is Spanish
      else if (nativeLanguage === 'en' && availableLanguages.some(l => l.code === 'es')) {
        setLearningLanguages(['es', '']);
      }
      // Fallback: just add one empty slot
      else {
        setLearningLanguages(['']);
      }
    }
  }, [availableLanguages, learningLanguages.length, nativeLanguage]);

  return (
    <div className="w-full flex items-center justify-center bg-secondary py-16">
      <Card className="w-full max-w-xl">
        <CardHeader className="text-left">
          <CardTitle className="text-2xl">Choose languages</CardTitle>
          <CardDescription className="text-base py-2">
            Please choose languages that you're using daily. The choice will be used for translations and quizzes to increase your active vocabulary.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 text-left">
          {/* Native Language Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Choose your native language</label>
            <Popover open={nativeOpen} onOpenChange={setNativeOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={nativeOpen}
                  className="w-full justify-between"
                  disabled={languagesLoading}
                >
                  {nativeLanguage
                    ? languages.find((lang) => lang.code === nativeLanguage)?.en_name
                    : "Choose your native language"}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0">
                <Command>
                  <CommandInput placeholder="Search language..." />
                  <CommandList>
                    <CommandEmpty>No language found.</CommandEmpty>
                    <CommandGroup>
                      {languages.map((lang) => (
                        <CommandItem
                          key={lang.code}
                          value={`${lang.en_name} ${lang.original_name}`}
                          onSelect={() => {
                            setNativeLanguage(lang.code);
                            setNativeOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              nativeLanguage === lang.code ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {lang.en_name} ({lang.original_name})
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Learning Languages */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Choose languages that you're learning</label>
            <div className="space-y-3">
              {learningLanguages.map((langCode, index) => {
                const availableForThisSlot = availableLanguages.filter(
                  l => l.code === langCode || !learningLanguages.includes(l.code)
                );

                const isOpen = learningOpen[index] || false;
                const setIsOpen = (open: boolean) => {
                  const newOpen = [...learningOpen];
                  newOpen[index] = open;
                  setLearningOpen(newOpen);
                };

                return (
                  <div key={index} className="flex items-center gap-2">
                    <Popover open={isOpen} onOpenChange={setIsOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          role="combobox"
                          aria-expanded={isOpen}
                          className="flex-1 justify-between"
                          disabled={languagesLoading}
                        >
                          {langCode && langCode !== ''
                            ? availableLanguages.find((lang) => lang.code === langCode)?.en_name
                            : "Select a language"}
                          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-full p-0">
                        <Command>
                          <CommandInput placeholder="Search language..." />
                          <CommandList>
                            <CommandEmpty>No language found.</CommandEmpty>
                            <CommandGroup>
                              {availableForThisSlot.map((lang) => (
                                <CommandItem
                                  key={lang.code}
                                  value={`${lang.en_name} ${lang.original_name}`}
                                  onSelect={() => {
                                    updateLearningLanguage(index, lang.code);
                                    setIsOpen(false);
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "mr-2 h-4 w-4",
                                      langCode === lang.code ? "opacity-100" : "opacity-0"
                                    )}
                                  />
                                  {lang.en_name} ({lang.original_name})
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeLearningLanguage(langCode)}
                      className="shrink-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                );
              })}

              {learningLanguages.length < 5 && (
                <Button
                  variant="outline"
                  onClick={addLearningLanguage}
                  className="w-auto"
                  disabled={languagesLoading || availableLanguages.length === learningLanguages.length}
                >
                  Add language
                </Button>
              )}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            onClick={handleSubmit}
            disabled={saving || !nativeLanguage || learningLanguages.length === 0}
            className="w-auto !mt-8"
          >
            {saving ? "Saving..." : "Set languages"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}