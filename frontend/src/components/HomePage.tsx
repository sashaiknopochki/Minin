import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLanguageContext } from "@/contexts/LanguageContext";

export default function HomePage() {
  const { languages, loading, error } = useLanguageContext();

  // Track selected language for each input
  const [lang1, setLang1] = useState("ru");
  const [lang2, setLang2] = useState("en");
  const [lang3, setLang3] = useState("de");

  // Helper function to get language name by code
  const getLanguageName = (code: string) => {
    const lang = languages.find((l) => l.code === code);
    return lang ? lang.en_name : code;
  };

  return (
    <div>
      {/* Header */}
      <header className="w-full py-3">
        <div className="flex items-baseline justify-between">
          {/* Logo and Navigation */}
          <div className="flex items-baseline gap-4 sm:gap-6 md:gap-10">
            <h1 className="text-2xl font-bold text-foreground">minin</h1>

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
            <Select value={lang1} onValueChange={setLang1} disabled={loading}>
              <SelectTrigger className="h-9 bg-background">
                <SelectValue placeholder={loading ? "Loading languages..." : "Select language"} />
              </SelectTrigger>
              <SelectContent>
                {error ? (
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

            <Textarea
              placeholder={`Enter a text in ${getLanguageName(lang1)}`}
              className="h-40 resize-none bg-background"
            />
          </div>

          {/* Second Input */}
          <div className="flex flex-col gap-6">
            <Select value={lang2} onValueChange={setLang2} disabled={loading}>
              <SelectTrigger className="h-9 bg-background">
                <SelectValue placeholder={loading ? "Loading languages..." : "Select language"} />
              </SelectTrigger>
              <SelectContent>
                {error ? (
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

            <Textarea
              placeholder={`Enter a text in ${getLanguageName(lang2)}`}
              className="h-40 resize-none bg-background"
            />
          </div>

          {/* Third Input */}
          <div className="flex flex-col gap-6">
            <Select value={lang3} onValueChange={setLang3} disabled={loading}>
              <SelectTrigger className="h-9 bg-background">
                <SelectValue placeholder={loading ? "Loading languages..." : "Select language"} />
              </SelectTrigger>
              <SelectContent>
                {error ? (
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

            <Textarea
              placeholder={`Enter a text in ${getLanguageName(lang3)}`}
              className="h-40 resize-none bg-background"
            />
          </div>
        </div>
      </main>
    </div>
  );
}