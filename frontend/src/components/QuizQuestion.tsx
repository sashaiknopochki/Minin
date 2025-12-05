import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Check, X } from "lucide-react"

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

export interface QuizQuestionProps {
  quizData: QuizData
  onSubmit: (answer: string) => void
  result?: QuizResult | null
  isLoading?: boolean
}

export function QuizQuestion({
  quizData,
  onSubmit,
  result,
  isLoading = false,
}: QuizQuestionProps) {
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
            <div className="p-4 bg-muted rounded-lg border">
              <div className="flex items-center gap-2 mb-2">
                {result.was_correct ? (
                  <>
                    <Check className="h-5 w-5" />
                    <span className="font-semibold">Correct!</span>
                  </>
                ) : (
                  <>
                    <X className="h-5 w-5" />
                    <span className="font-semibold">Incorrect</span>
                  </>
                )}
              </div>
              <p className="text-sm">
                Your answer: <strong className={result.was_correct ? '' : 'line-through'}>{result.user_answer}</strong>
              </p>
              {!result.was_correct && (
                <p className="text-sm mt-1">
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
  )
}