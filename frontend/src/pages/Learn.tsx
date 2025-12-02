import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { QuizDialog } from '@/components/QuizDialog'

export default function Learn() {
  const [showQuiz, setShowQuiz] = useState(false)
  const [quizResult, setQuizResult] = useState(null)

  const testQuiz = {
    quiz_attempt_id: 1,
    question: "What is the English translation of 'Katze'?",
    options: ["cat", "dog", "house", "tree"],
    question_type: "multiple_choice_target",
    phrase_id: 123,
  }

  const handleAnswerSubmit = (answer: string) => {
    const isCorrect = answer === "cat"

    const result = {
      was_correct: isCorrect,
      correct_answer: "cat",
      user_answer: answer,
    }

    setQuizResult(result)
    console.log("Result:", result)
  }

  const handleContinue = () => {
    // Reset result to show a new quiz
    setQuizResult(null)
    // In real app, this would fetch a new quiz question from backend
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
        onSubmit={handleAnswerSubmit}
        onSkip={() => setShowQuiz(false)}
        onContinue={handleContinue}
        result={quizResult}
      />
    </div>
  );
}