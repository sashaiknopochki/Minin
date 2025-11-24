import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLanguageContext } from "@/contexts/LanguageContext";

export default function HomePage() {
  const { languages, loading, error } = useLanguageContext();

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
          {/* Russian Input */}
          <div className="flex flex-col gap-6">
            <Select defaultValue="ru" disabled={loading}>
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
              placeholder="Введите текст на русском"
              className="h-40 resize-none bg-background"
            />
          </div>

          {/* English Input */}
          <div className="flex flex-col gap-6">
            <Select defaultValue="en" disabled={loading}>
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
              placeholder="Enter a text in English"
              className="h-40 resize-none bg-background"
            />
          </div>

          {/* German Input */}
          <div className="flex flex-col gap-6">
            <Select defaultValue="de" disabled={loading}>
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
              placeholder="Gib einen Text auf Deutsch ein"
              className="h-40 resize-none bg-background"
            />
          </div>
        </div>
      </main>
    </div>
  );
}