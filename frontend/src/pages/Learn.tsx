import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { QuizDialog } from '@/components/QuizDialog'

export default function Learn() {
  const [showQuiz, setShowQuiz] = useState(false)

  const testQuiz = {
    quiz_attempt_id: 1,
    question: "What is the English translation of 'Katze'?",
    options: ["cat", "dog", "house", "tree"],
    question_type: "multiple_choice_target",
    phrase_id: 123,
  }

  return (
    <div className="w-full py-8">
      <h1 className="text-4xl font-bold mb-8">Learn</h1>
      <div className="flex flex-col items-center justify-center py-16 px-4 gap-4">
        <p className="text-lg text-muted-foreground text-center">
          Quiz feature coming soon! Practice vocabulary from your search history.
        </p>

        <Button onClick={() => setShowQuiz(true)} size="lg">
          Test Quiz Dialog
        </Button>
      </div>

      <QuizDialog
        open={showQuiz}
        onOpenChange={setShowQuiz}
        quizData={testQuiz}
        onSubmit={(answer) => {
          console.log("Selected:", answer)
          alert(`You chose: ${answer}`)
          setShowQuiz(false)
        }}
        onSkip={() => {
          alert("Quiz skipped")
          setShowQuiz(false)
        }}
      />
    </div>
  );
}