import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Check, X, Loader2 } from "lucide-react"

export interface QuizData {
  quiz_attempt_id: number
  question: string
  options: string[] | null  // null for text input questions
  question_type: string
  phrase_id: number
}

export interface QuizResult {
  was_correct: boolean
  correct_answer: string
  user_answer: string
}

export interface QuizDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  quizData: QuizData
  onSubmit: (answer: string) => void
  onSkip: () => void
  onContinue?: () => void
  result?: QuizResult | null
  isLoading?: boolean
}

export function QuizDialog({
  open,
  onOpenChange,
  quizData,
  onSubmit,
  onSkip,
  onContinue,
  result,
  isLoading = false,
}: QuizDialogProps) {
  const [textAnswer, setTextAnswer] = React.useState("")

  // Reset text answer when quiz changes
  React.useEffect(() => {
    setTextAnswer("")
  }, [quizData.quiz_attempt_id])

  const handleAnswerClick = (answer: string) => {
    if (!result) {
      onSubmit(answer)
    }
  }

  const handleTextSubmit = () => {
    if (!result && textAnswer.trim()) {
      onSubmit(textAnswer.trim())
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !result && textAnswer.trim()) {
      handleTextSubmit()
    }
  }

  const getButtonIcon = (option: string) => {
    if (!result) return null

    // Show check icon for correct answer
    if (result.correct_answer === option) {
      return <Check className="h-6 w-6 ml-auto flex-shrink-0 stroke-[2.5]" />
    }

    // Show X icon for incorrect selection
    if (result.user_answer === option && !result.was_correct) {
      return <X className="h-6 w-6 ml-auto flex-shrink-0 stroke-[2.5]" />
    }

    return null
  }

  const getButtonTextClassName = (option: string) => {
    // Strikethrough for incorrect answer
    if (result && result.user_answer === option && !result.was_correct) {
      return "line-through"
    }
    return ""
  }

  const getButtonClassName = (option: string) => {
    const baseClasses = "w-full h-auto py-4 px-4 text-lg font-normal justify-start hover:bg-accent hover:border-accent-foreground/20"

    if (!result) return baseClasses

    // Correct answer gets primary border
    if (result.correct_answer === option) {
      return `${baseClasses} border-primary border-2 disabled:opacity-100`
    }

    // Incorrect selection keeps normal style
    if (result.user_answer === option && !result.was_correct) {
      return `${baseClasses} disabled:opacity-100`
    }

    // Unselected options (wrong) look more disabled
    return `${baseClasses} disabled:opacity-40`
  }

  const getFeedbackMessage = () => {
    if (!result) {
      // Reserve space to prevent jumping
      return (
        <div className="p-4 bg-transparent rounded-lg min-h-[68px]">
          <p className="text-sm text-transparent leading-relaxed">
            Keep practicing! "house" is incorrect. The correct answer is "placeholder".
          </p>
        </div>
      )
}

    if (result.was_correct) {
      return (
        <div className="p-4 bg-muted rounded-lg min-h-[68px]">
          <p className="text-sm text-foreground leading-relaxed">
            Good job! <strong>"{result.user_answer}"</strong> is the correct answer.
          </p>
        </div>
      )
    } else {
      return (
        <div className="p-4 bg-muted rounded-lg min-h-[68px]">
          <p className="text-sm text-foreground leading-relaxed">
            Keep practicing! <strong>"{result.user_answer}"</strong> is incorrect. The correct answer is <strong>"{result.correct_answer}"</strong>.
          </p>
        </div>
      )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold">
            Quiz
          </DialogTitle>
          <DialogDescription className="text-base">
            Test your knowledge and improve your vocabulary.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-6 flex items-center justify-center min-h-[300px]">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="py-6 space-y-4">
            <h3 className="text-2xl font-semibold mb-6 text-foreground leading-relaxed">
              {quizData.question}
            </h3>

            {quizData.options === null ? (
              // Text input question
              <div className="space-y-4">
                <Input
                  type="text"
                  placeholder="Type your answer..."
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={!!result}
                  className="text-lg py-6"
                  autoFocus
                />

                {!result && (
                  <Button
                    onClick={handleTextSubmit}
                    disabled={!textAnswer.trim()}
                    className="w-full py-6 text-lg"
                  >
                    Submit Answer
                  </Button>
                )}

                {result && (
                  <div className="p-4 rounded-lg bg-muted border border-border">
                    <div className="flex items-center gap-2 mb-2">
                      {result.was_correct ? (
                        <>
                          <Check className="h-5 w-5 text-foreground" />
                          <span className="font-semibold text-foreground">Correct!</span>
                        </>
                      ) : (
                        <>
                          <X className="h-5 w-5 text-foreground" />
                          <span className="font-semibold text-foreground">Incorrect</span>
                        </>
                      )}
                    </div>
                    <p className="text-sm text-foreground">
                      Your answer: <strong className={result.was_correct ? '' : 'line-through'}>{result.user_answer}</strong>
                    </p>
                    {!result.was_correct && (
                      <p className="text-sm text-foreground mt-1">
                        Correct answer: <strong>{result.correct_answer}</strong>
                      </p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              // Multiple choice question
              <>
                <div className="flex flex-col gap-3">
                  {quizData.options.map((option, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      onClick={() => handleAnswerClick(option)}
                      disabled={!!result}
                      className={getButtonClassName(option)}
                    >
                      <span className={getButtonTextClassName(option)}>
                        {option}
                      </span>
                      {getButtonIcon(option)}
                    </Button>
                  ))}
                </div>

                {getFeedbackMessage()}
              </>
            )}
          </div>
        )}

        <DialogFooter className="gap-2 sm:justify-between">
          {!result ? (
            <Button
              variant="outline"
              onClick={onSkip}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              Skip for now
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
                className="w-full sm:w-auto"
              >
                Back to Translator
              </Button>
              {onContinue && (
                <Button
                  variant="default"
                  onClick={onContinue}
                  disabled={isLoading}
                  className="w-full sm:w-auto"
                >
                  Continue practicing
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}