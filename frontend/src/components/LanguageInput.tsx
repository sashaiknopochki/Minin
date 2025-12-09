import { Textarea } from "@/components/ui/textarea";
import { X, Loader2, Copy, Check } from "lucide-react";

interface LanguageInputProps {
  languageName: string;
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  onCopy: () => void;
  isSource: boolean;
  isTranslating: boolean;
  isCopied: boolean;
  placeholder: string;
  spellingSuggestion: string | null;
  onSpellingSuggestionClick: (correction: string) => void;
  translations: [string, string, string][] | null;
  showLanguageName?: boolean; // Optional prop to control language name visibility
}

export function LanguageInput({
  languageName,
  value,
  onChange,
  onClear,
  onCopy,
  isSource,
  isTranslating,
  isCopied,
  placeholder,
  spellingSuggestion,
  onSpellingSuggestionClick,
  translations,
  showLanguageName = true // Default to true for backward compatibility
}: LanguageInputProps) {
  return (
    <div className="flex flex-col gap-6">
      {showLanguageName && (
        <div className="text-base font-medium text-left">
          {languageName}
        </div>
      )}

      <div className="relative">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`h-60 resize-none bg-background pr-10 text-xl ${
            isSource ? "ring-2 ring-primary" : ""
          } ${isTranslating && isSource ? "opacity-50" : ""}`}
          disabled={isTranslating && !isSource}
        />
        {value && (
          <>
            <button
              onClick={onClear}
              className="absolute top-2 right-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
              aria-label="Clear field"
            >
              <X className="h-5 w-5 text-muted-foreground" />
            </button>
            <button
              onClick={onCopy}
              className="absolute bottom-2 left-2 h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted transition-colors"
              aria-label="Copy to clipboard"
            >
              {isCopied ? (
                <Check className="h-5 w-5 text-muted-foreground" />
              ) : (
                <Copy className="h-5 w-5 text-muted-foreground" />
              )}
            </button>
          </>
        )}
        {isTranslating && isSource && (
          <div className="absolute bottom-2 right-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Spelling Suggestion */}
      {spellingSuggestion && (
        <div className="text-sm text-muted-foreground text-left">
          Did you mean{" "}
          <button
            onClick={() => onSpellingSuggestionClick(spellingSuggestion)}
            className="text-primary hover:underline font-medium cursor-pointer"
          >
            {spellingSuggestion}
          </button>
          ?
        </div>
      )}

      {/* Translations */}
      {translations && translations.length > 0 && (
        <div className="flex flex-col gap-3 p-4 rounded-md border border-border bg-muted/30 text-left gap-y-6">
          {translations.map(([word, grammarInfo, context], index) => (
            <div key={index} className="flex flex-col gap-2">
              <div className="text-base font-medium">{word}</div>
              <div className="text-xs text-muted-foreground">{grammarInfo}</div>
              <div className="text-sm text-muted-foreground">{context}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}