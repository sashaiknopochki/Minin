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
import { Loader2 } from "lucide-react"
import { QuizQuestion, type QuizData, type QuizResult } from "./QuizQuestion"

export type { QuizData, QuizResult }

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
          <QuizQuestion
            quizData={quizData}
            onSubmit={onSubmit}
            result={result}
            isLoading={isLoading}
          />
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
                  Next question
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}