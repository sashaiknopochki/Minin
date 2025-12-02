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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, XCircle } from "lucide-react"

export interface QuizResult {
  was_correct: boolean
  correct_answer: string
  explanation: string
  stage_advanced: boolean
  new_stage: string
}

export interface QuizResultDialogProps {
  open: boolean
  onClose: () => void
  result: QuizResult
}

export function QuizResultDialog({
  open,
  onClose,
  result,
}: QuizResultDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold">
            Quiz Result
          </DialogTitle>
          <DialogDescription className="text-base">
            {result.was_correct
              ? "Great job! Keep up the excellent work."
              : "Keep practicing to improve your skills."}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Result Alert */}
          <Alert variant={result.was_correct ? "default" : "destructive"}>
            {result.was_correct ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertTitle>
              {result.was_correct ? "Correct!" : "Incorrect"}
            </AlertTitle>
            <AlertDescription>
              {result.was_correct ? (
                <span>Your answer was correct.</span>
              ) : (
                <span>
                  The correct answer is: <strong>{result.correct_answer}</strong>
                </span>
              )}
            </AlertDescription>
          </Alert>

          {/* Explanation */}
          {result.explanation && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground leading-relaxed">
                {result.explanation}
              </p>
            </div>
          )}

          {/* Stage Advancement Celebration */}
          {result.stage_advanced && (
            <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg">
              <h4 className="font-semibold text-primary mb-2">
                Congratulations! You've advanced!
              </h4>
              <p className="text-sm text-muted-foreground mb-3">
                Your learning progress has improved to a new stage.
              </p>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">New stage:</span>
                <Badge variant="default" className="text-sm">
                  {result.new_stage}
                </Badge>
              </div>
            </div>
          )}

          {/* Current Stage (if not advanced) */}
          {!result.stage_advanced && result.new_stage && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Current stage:</span>
              <Badge variant="secondary" className="text-sm">
                {result.new_stage}
              </Badge>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button onClick={onClose} className="w-full sm:w-auto">
            Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}