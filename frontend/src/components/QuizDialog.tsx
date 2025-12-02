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

export interface QuizData {
  quiz_attempt_id: number
  question: string
  options: string[]
  question_type: string
  phrase_id: number
}

export interface QuizDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  quizData: QuizData
  onSubmit: (answer: string) => void
  onSkip: () => void
}

export function QuizDialog({
  open,
  onOpenChange,
  quizData,
  onSubmit,
  onSkip,
}: QuizDialogProps) {
  const handleAnswerClick = (answer: string) => {
    onSubmit(answer)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">
            Quiz Time!
          </DialogTitle>
          <DialogDescription className="text-base">
            Test your knowledge and improve your vocabulary
          </DialogDescription>
        </DialogHeader>

        <div className="py-6">
          <h3 className="text-lg font-semibold mb-6 text-foreground leading-relaxed">
            {quizData.question}
          </h3>

          <div className="flex flex-col gap-3">
            {quizData.options.map((option, index) => (
              <Button
                key={index}
                variant="outline"
                onClick={() => handleAnswerClick(option)}
                className="w-full h-auto py-4 px-4 text-base font-normal justify-start hover:bg-accent hover:border-accent-foreground/20"
              >
                {option}
              </Button>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onSkip}
            className="w-full sm:w-auto"
          >
            Skip for now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}