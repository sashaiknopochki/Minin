import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import { Card, CardContent } from "@/components/ui/card";
import {
  QuizQuestion,
  type QuizData,
  type QuizResult,
} from "@/components/QuizQuestion";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguageContext } from "@/contexts/LanguageContext";
import { Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function Practice() {
  const { user } = useAuth();
  const { getLanguageName } = useLanguageContext();
  const [searchParams, setSearchParams] = useSearchParams();

  // Get filter values from URL params
  const selectedStage = searchParams.get("stage") || "all";
  const selectedLanguage = searchParams.get("language") || "all";
  const dueForReview = searchParams.get("due") === "true";

  // Quiz state
  const [quizData, setQuizData] = useState<QuizData | null>(null);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPosition, setCurrentPosition] = useState(0);

  // Session tracking
  const [seenPhraseIds, setSeenPhraseIds] = useState<number[]>([]);
  const [sessionComplete, setSessionComplete] = useState(false);

  // User languages
  const userLanguages = user?.translator_languages || [];
  const primaryLanguage = user?.primary_language_code || "en";

  // Combine all languages (primary + translator languages)
  const allLanguages = [
    primaryLanguage,
    ...userLanguages.filter((lang: string) => lang !== primaryLanguage),
  ];

  // Fetch next question
  const fetchNextQuestion = async () => {
    if (!user) return;

    setLoading(true);
    try {
      const excludeIds = seenPhraseIds.join(",");
      const params = new URLSearchParams({
        stage: selectedStage,
        language_code: selectedLanguage,
        due_for_review: dueForReview.toString(),
        ...(excludeIds && { exclude_phrase_ids: excludeIds }),
      });

      const response = await apiFetch(`/quiz/practice/next?${params}`, {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch practice question");
      }

      const data = await response.json();

      // Check if session is complete (no more phrases)
      if (data.quiz_attempt_id === null) {
        setSessionComplete(true);
        setQuizData(null);
        return;
      }

      setQuizData(data);
      setCurrentPosition(data.current_position);
      setTotalCount(data.total_matching);
      setQuizResult(null); // Reset result for new question
      setSessionComplete(false);
    } catch (error) {
      console.error("Error fetching practice question:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle answer submission
  const handleQuizSubmit = async (answer: string) => {
    if (!quizData) return;

    setLoading(true);
    try {
      const response = await apiFetch("/quiz/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          quiz_attempt_id: quizData.quiz_attempt_id,
          user_answer: answer,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit answer");
      }

      const data = await response.json();
      setQuizResult({
        was_correct: data.was_correct,
        correct_answer: data.correct_answer,
        user_answer: answer,
      });
    } catch (error) {
      console.error("Error submitting answer:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle skip
  const handleSkip = async () => {
    if (!quizData) return;

    try {
      const response = await apiFetch("/quiz/skip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          phrase_id: quizData.phrase_id,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to skip question");
      }

      // Add to seen phrases and fetch next
      setSeenPhraseIds((prev) => [...prev, quizData.phrase_id]);
      setQuizResult(null);
      fetchNextQuestion();
    } catch (error) {
      console.error("Error skipping question:", error);
    }
  };

  // Handle continue (after answering)
  const handleContinue = () => {
    if (!quizData) return;

    // Add to seen phrases and fetch next
    setSeenPhraseIds((prev) => [...prev, quizData.phrase_id]);
    setQuizResult(null);
    fetchNextQuestion();
  };

  // Handle stage filter change
  const handleStageChange = (stage: string) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set("stage", stage);
    setSearchParams(newParams);

    // Reset session
    setSeenPhraseIds([]);
    setCurrentPosition(0);
    setSessionComplete(false);
  };

  // Handle language filter change
  const handleLanguageChange = (language: string) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set("language", language);
    setSearchParams(newParams);

    // Reset session
    setSeenPhraseIds([]);
    setCurrentPosition(0);
    setSessionComplete(false);
  };

  // Handle due filter change
  const handleDueFilterChange = (due: boolean) => {
    const newParams = new URLSearchParams(searchParams);
    if (due) {
      newParams.set("due", "true");
    } else {
      newParams.delete("due");
    }
    setSearchParams(newParams);

    // Reset session
    setSeenPhraseIds([]);
    setCurrentPosition(0);
    setSessionComplete(false);
  };

  // Fetch first question when filters change
  useEffect(() => {
    if (user) {
      fetchNextQuestion();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStage, selectedLanguage, dueForReview, user]);

  return (
    <div className="w-full py-8">
      {/* Header */}
      <h1 className="text-4xl font-bold mb-8 text-left">Practice</h1>

      {/* Filters Section */}
      <div className="mb-16 flex flex-wrap items-center gap-x-8 gap-y-4">
        {/* Language Filter */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground mr-2">
            Filter by language:
          </span>
          <ButtonGroup>
            <Button
              variant={selectedLanguage === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => handleLanguageChange("all")}
            >
              All languages
            </Button>
            {allLanguages.map((langCode) => (
              <Button
                key={langCode}
                variant={selectedLanguage === langCode ? "default" : "outline"}
                size="sm"
                onClick={() => handleLanguageChange(langCode)}
              >
                {getLanguageName(langCode)}
              </Button>
            ))}
          </ButtonGroup>
        </div>

        {/* Stage Filter */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground mr-2">
            Filter by stage:
          </span>
          <ButtonGroup>
            <Button
              variant={selectedStage === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => handleStageChange("all")}
            >
              All
            </Button>
            <Button
              variant={selectedStage === "basic" ? "default" : "outline"}
              size="sm"
              onClick={() => handleStageChange("basic")}
            >
              Basic
            </Button>
            <Button
              variant={selectedStage === "intermediate" ? "default" : "outline"}
              size="sm"
              onClick={() => handleStageChange("intermediate")}
            >
              Intermediate
            </Button>
            <Button
              variant={selectedStage === "advanced" ? "default" : "outline"}
              size="sm"
              onClick={() => handleStageChange("advanced")}
            >
              Advanced
            </Button>
          </ButtonGroup>
        </div>

        {/* Due for Review Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground mr-2">
            Due today only:
          </span>
          <Button
            variant={dueForReview ? "default" : "outline"}
            size="sm"
            onClick={() => handleDueFilterChange(!dueForReview)}
          >
            {dueForReview ? "On" : "Off"}
          </Button>
        </div>
      </div>

      {/* Progress Indicator */}
      {!sessionComplete && totalCount > 0 && currentPosition > 0 && (
        <div className="mb-4 text-sm text-muted-foreground">
          Question {currentPosition} of {totalCount}
        </div>
      )}

      {/* Quiz Question Area */}
      <div className="max-w-md mx-auto">
        <Card>
          <CardContent>
            {/* Loading State */}
            {loading && !quizData && (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )}

            {/* Empty State (no phrases match filters) */}
            {!loading && totalCount === 0 && !sessionComplete && !quizData && (
              <div className="text-center py-16">
                <p className="text-lg text-muted-foreground">
                  No phrases match your current filters.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Try adjusting your selection or practice some more to unlock
                  new phrases!
                </p>
              </div>
            )}

            {/* Session Complete State */}
            {sessionComplete && (
              <div className="text-center py-16">
                <h2 className="text-2xl font-bold mb-4">Great work!</h2>
                <p className="text-lg text-muted-foreground mb-6">
                  You've completed all {seenPhraseIds.length} phrases matching
                  these filters.
                </p>
                <Button
                  onClick={() => {
                    setSeenPhraseIds([]);
                    setCurrentPosition(0);
                    setSessionComplete(false);
                    fetchNextQuestion();
                  }}
                >
                  Start Over
                </Button>
              </div>
            )}

            {/* Active Quiz */}
            {!loading && !sessionComplete && quizData && (
              <>
                <QuizQuestion
                  quizData={quizData}
                  onSubmit={handleQuizSubmit}
                  result={quizResult}
                  isLoading={loading}
                />

                {/* Action Buttons */}
                <div className="mt-6 flex gap-2">
                  {!quizResult ? (
                    <Button
                      variant="outline"
                      onClick={handleSkip}
                      disabled={loading}
                    >
                      Skip for now
                    </Button>
                  ) : (
                    <Button
                      variant="default"
                      onClick={handleContinue}
                      disabled={loading}
                    >
                      Next question
                    </Button>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
