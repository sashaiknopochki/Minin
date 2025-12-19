import * as React from "react";
import { QuizDialog, type QuizData } from "./QuizDialog";
import { Button } from "@/components/ui/button";

/**
 * Test component for QuizDialog - allows you to preview the dialog in the browser
 *
 * To use:
 * 1. Import this in your main App.tsx or a route
 * 2. Open browser dev tools (F12)
 * 3. Use responsive design mode to test mobile/tablet views
 */
export function QuizDialogTest() {
  const [open, setOpen] = React.useState(false);

  // Sample quiz data for testing
  const sampleQuizData: QuizData = {
    quiz_attempt_id: 1,
    question: "What is the English translation of 'Katze'?",
    options: ["cat", "dog", "house", "tree"],
    question_type: "multiple_choice_target",
    phrase_id: 123,
  };

  const handleSubmit = (answer: string) => {
    console.log("Submitted answer:", answer);
    alert(`You selected: ${answer}`);
    setOpen(false);
  };

  const handleSkip = () => {
    console.log("Quiz skipped");
    alert("Quiz skipped!");
    setOpen(false);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8 p-8 bg-background">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">QuizDialog Component Test</h1>
        <p className="text-muted-foreground max-w-md">
          Click the button below to open the quiz dialog. Test on different
          screen sizes using your browser's responsive design mode (F12 → Device
          toolbar).
        </p>
      </div>

      <Button onClick={() => setOpen(true)} size="lg">
        Open Quiz Dialog
      </Button>

      <div className="mt-8 p-6 border rounded-lg max-w-2xl space-y-4 bg-card">
        <h2 className="text-xl font-semibold">Testing Instructions:</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
          <li>Open browser DevTools (F12 or Cmd+Option+I on Mac)</li>
          <li>
            Click the device toolbar icon or press Cmd+Shift+M (Mac) /
            Ctrl+Shift+M (Windows)
          </li>
          <li>
            Select different devices:
            <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
              <li>
                <strong>Mobile:</strong> iPhone SE (375px), iPhone 12 Pro
                (390px)
              </li>
              <li>
                <strong>Tablet:</strong> iPad (768px), iPad Pro (1024px)
              </li>
              <li>
                <strong>Desktop:</strong> Responsive 1200px+
              </li>
            </ul>
          </li>
          <li>
            Open the quiz dialog and verify:
            <ul className="list-disc list-inside ml-6 mt-2 space-y-1">
              <li>Dialog is full-width on mobile with proper padding</li>
              <li>Buttons stack vertically on mobile</li>
              <li>Dialog is centered with max-width on tablet/desktop</li>
              <li>All text is readable at different sizes</li>
            </ul>
          </li>
        </ol>
      </div>

      <QuizDialog
        open={open}
        onOpenChange={setOpen}
        quizData={sampleQuizData}
        onSubmit={handleSubmit}
        onSkip={handleSkip}
      />
    </div>
  );
}
