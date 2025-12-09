import { useState, useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { Button } from "@/components/ui/button";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Check, ChevronsUpDown, GripVertical, X, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Language } from "@/types/language";

// Sortable Language Item Component
function SortableLanguageItem({
  code,
  language,
  onDelete,
}: {
  code: string;
  language: Language;
  onDelete: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: code });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-center gap-3 p-3 rounded-md border bg-card",
        "hover:bg-accent transition-colors"
      )}
    >
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing"
        aria-label={`Drag to reorder ${language.en_name}`}
        role="button"
        tabIndex={0}
      >
        <GripVertical className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">
          {language.en_name} ({language.original_name})
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={onDelete}
        className="h-8 w-8"
        aria-label={`Remove ${language.en_name} from learning languages`}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}

export default function LanguageManager() {
  const { user, checkAuth } = useAuth();
  const { languages, loading: languagesLoading } = useLanguageContext();

  // Local state for optimistic updates - ensure safe initialization
  const [primaryLanguage, setPrimaryLanguage] = useState<string>(() =>
    user?.primary_language_code || ""
  );
  const [learningLanguages, setLearningLanguages] = useState<string[]>(() =>
    Array.isArray(user?.translator_languages) ? user.translator_languages : []
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Track open state for combobox popovers
  const [primaryOpen, setPrimaryOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  // Drag-and-drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Detect changes
  const hasChanges = useMemo(() => {
    if (!user) return false;
    const primaryChanged = primaryLanguage !== user.primary_language_code;
    const learningChanged =
      JSON.stringify(learningLanguages) !==
      JSON.stringify(user.translator_languages);
    return primaryChanged || learningChanged;
  }, [primaryLanguage, learningLanguages, user]);

  // Handle primary language change
  const handlePrimaryLanguageChange = (newCode: string) => {
    setPrimaryLanguage(newCode);
    // Auto-remove from learning languages if present
    setLearningLanguages((prev) => prev.filter((code) => code !== newCode));
    setError(null);
  };

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setLearningLanguages((items) => {
        const oldIndex = items.indexOf(active.id as string);
        const newIndex = items.indexOf(over.id as string);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  // Handle delete learning language
  const handleDeleteLearningLanguage = (code: string) => {
    setLearningLanguages((prev) => prev.filter((lang) => lang !== code));
    setError(null);
  };

  // Handle add learning language
  const handleAddLearningLanguage = (code: string) => {
    if (learningLanguages.length >= 5) {
      setError("You can add up to 5 learning languages");
      return;
    }
    setLearningLanguages((prev) => [...prev, code]);
    setAddOpen(false);
    setError(null);
  };

  // Handle save
  const handleSave = async () => {
    if (learningLanguages.length === 0) {
      setError("Please add at least one learning language");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch("/auth/update-languages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          primary_language_code: primaryLanguage,
          translator_languages: learningLanguages,
        }),
      });

      const data = await response.json();

      if (data.success) {
        await checkAuth(); // Refresh AuthContext
        setSuccessMessage("Languages updated successfully");
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        throw new Error(data.error || "Failed to save languages");
      }
    } catch (err) {
      // Revert to original values
      setPrimaryLanguage(user?.primary_language_code || "");
      setLearningLanguages(user?.translator_languages || []);
      setError(
        err instanceof Error ? err.message : "Network error. Please try again."
      );
    } finally {
      setIsSaving(false);
    }
  };

  // Filter available languages for adding
  const availableToAdd = languages.filter(
    (lang) =>
      lang.code !== primaryLanguage && !learningLanguages.includes(lang.code)
  );

  // Show loading state while languages are being fetched
  if (languagesLoading) {
    return (
      <p className="text-muted-foreground text-left">
        Loading languages...
      </p>
    );
  }

  // Show sign-in message if user is not authenticated
  if (!user) {
    return (
      <p className="text-muted-foreground text-left">
        Please sign in to manage your languages.
      </p>
    );
  }

  return (
    <div className="space-y-6 text-left">
      {/* Primary Language Section */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Primary Language</label>
        <Popover open={primaryOpen} onOpenChange={setPrimaryOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={primaryOpen}
              className="w-full justify-between"
              disabled={languagesLoading}
            >
              {primaryLanguage
                ? (() => {
                    const lang = languages.find((l) => l.code === primaryLanguage);
                    return lang
                      ? `${lang.en_name} (${lang.original_name})`
                      : "Select primary language";
                  })()
                : "Select primary language"}
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-full p-0" align="start">
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
                        handlePrimaryLanguageChange(lang.code);
                        setPrimaryOpen(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          primaryLanguage === lang.code
                            ? "opacity-100"
                            : "opacity-0"
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

      {/* Learning Languages Section */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Learning Languages <span className="text-muted-foreground font-normal">(Drag to reorder)</span>
        </label>

        {/* Learning languages list with drag-and-drop */}
        {learningLanguages.length === 0 ? (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              No learning languages added yet.
            </p>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={learningLanguages}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {learningLanguages.map((code) => {
                  const language = languages.find((lang) => lang.code === code);
                  if (!language) return null;

                  return (
                    <SortableLanguageItem
                      key={code}
                      code={code}
                      language={language}
                      onDelete={() => handleDeleteLearningLanguage(code)}
                    />
                  );
                })}
              </div>
            </SortableContext>
          </DndContext>
        )}

        {/* Add Language Button */}
        <Popover open={addOpen} onOpenChange={setAddOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              disabled={learningLanguages.length >= 5 || availableToAdd.length === 0}
              className="w-auto"
            >
              + Add Language
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-full p-0" align="start">
            <Command>
              <CommandInput placeholder="Search language..." />
              <CommandList>
                <CommandEmpty>No language found.</CommandEmpty>
                <CommandGroup>
                  {availableToAdd.map((lang) => (
                    <CommandItem
                      key={lang.code}
                      value={`${lang.en_name} ${lang.original_name}`}
                      onSelect={() => handleAddLearningLanguage(lang.code)}
                    >
                      {lang.en_name} ({lang.original_name})
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>

      {/* Success Message */}
      {successMessage && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            {successMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Save Button */}
      {hasChanges && (
        <Button onClick={handleSave} disabled={isSaving} className="w-auto">
          {isSaving ? "Saving..." : "Save Changes"}
        </Button>
      )}
    </div>
  );
}