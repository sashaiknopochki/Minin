import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import LanguageManager from "@/components/LanguageManager";

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [quizFrequency, setQuizFrequency] = useState<number>(
    user?.quiz_frequency ?? 5
  );
  const [isUpdatingFrequency, setIsUpdatingFrequency] = useState(false);

  // Quiz type preferences state
  const [enableContextualQuiz, setEnableContextualQuiz] = useState<boolean>(
    user?.enable_contextual_quiz ?? true
  );
  const [enableDefinitionQuiz, setEnableDefinitionQuiz] = useState<boolean>(
    user?.enable_definition_quiz ?? true
  );
  const [enableSynonymQuiz, setEnableSynonymQuiz] = useState<boolean>(
    user?.enable_synonym_quiz ?? true
  );
  const [isUpdatingQuizPreferences, setIsUpdatingQuizPreferences] = useState(false);

  const handleQuizFrequencyChange = async (value: string) => {
    const newFrequency = parseInt(value);
    setQuizFrequency(newFrequency);
    setIsUpdatingFrequency(true);

    try {
      const response = await fetch("/settings/quiz-frequency", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ quiz_frequency: newFrequency }),
      });

      const data = await response.json();

      if (!data.success) {
        console.error("Failed to update quiz frequency:", data.error);
        alert("Failed to update quiz frequency. Please try again.");
        // Revert to previous value if update failed
        setQuizFrequency(user?.quiz_frequency ?? 5);
      }
    } catch (error) {
      console.error("Error updating quiz frequency:", error);
      alert("An error occurred while updating quiz frequency. Please try again.");
      // Revert to previous value if update failed
      setQuizFrequency(user?.quiz_frequency ?? 5);
    } finally {
      setIsUpdatingFrequency(false);
    }
  };

  const handleQuizPreferenceChange = async (
    preferenceKey: string,
    newValue: boolean,
    setterFunction: React.Dispatch<React.SetStateAction<boolean>>,
    previousValue: boolean
  ) => {
    setterFunction(newValue);
    setIsUpdatingQuizPreferences(true);

    try {
      const response = await fetch("/settings/quiz-preferences", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ [preferenceKey]: newValue }),
      });

      const data = await response.json();

      if (!data.success) {
        console.error("Failed to update quiz preference:", data.error);
        alert("Failed to update quiz preference. Please try again.");
        // Revert to previous value if update failed
        setterFunction(previousValue);
      }
    } catch (error) {
      console.error("Error updating quiz preference:", error);
      alert("An error occurred while updating quiz preference. Please try again.");
      // Revert to previous value if update failed
      setterFunction(previousValue);
    } finally {
      setIsUpdatingQuizPreferences(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);

    try {
      const response = await fetch("/settings/account", {
        method: "DELETE",
        credentials: "include",
      });

      const data = await response.json();

      if (data.success) {
        // Close the dialog
        setDeleteDialogOpen(false);

        // Logout and redirect to home
        await logout();
        navigate("/");
      } else {
        console.error("Failed to delete account:", data.error);
        alert("Failed to delete account. Please try again.");
        setIsDeleting(false);
      }
    } catch (error) {
      console.error("Error deleting account:", error);
      alert("An error occurred while deleting your account. Please try again.");
      setIsDeleting(false);
    }
  };

  if (!user) {
    return (
      <div className="w-full py-8">
        <h1 className="text-4xl font-bold mb-8 text-left">Profile</h1>
        <div className="w-full rounded-md border py-16 px-4">
          <p className="text-lg text-muted-foreground text-left">
            Please sign in to view your profile.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full py-8">
      <h1 className="text-4xl font-bold mb-8 text-left">Profile</h1>

      <div className="space-y-6 max-w-3xl mx-auto">
        {/* Learning Section */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle className="text-left">Learning</CardTitle>
              <CardDescription className="text-left">
                Customize your learning experience.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Quiz Frequency Setting */}
              <div className="flex items-center gap-3 text-left">
                <p className="text-foreground">
                  Show quizzes about previously searched words every
                </p>
                <Select
                  value={quizFrequency.toString()}
                  onValueChange={handleQuizFrequencyChange}
                  disabled={isUpdatingFrequency}
                >
                  <SelectTrigger className="w-[70px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1</SelectItem>
                    <SelectItem value="3">3</SelectItem>
                    <SelectItem value="5">5</SelectItem>
                    <SelectItem value="10">10</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-foreground">translations.</p>
              </div>

              <Separator />

              {/* Quiz Type Preferences Section */}
              <div className="space-y-4">
                <div className="text-left">
                  <h3 className="text-sm font-semibold">Advanced Question Types</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Choose which types of advanced questions to include in your practice.
                    Basic and intermediate questions cannot be disabled.
                  </p>
                </div>

                {/* Contextual Questions Toggle */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5 text-left">
                    <Label htmlFor="contextual" className="text-sm font-medium">
                      Contextual Questions
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Translate words within sentence context
                    </p>
                  </div>
                  <Switch
                    id="contextual"
                    checked={enableContextualQuiz}
                    onCheckedChange={(checked) =>
                      handleQuizPreferenceChange(
                        "enable_contextual_quiz",
                        checked,
                        setEnableContextualQuiz,
                        enableContextualQuiz
                      )
                    }
                    disabled={isUpdatingQuizPreferences}
                  />
                </div>

                {/* Definition Questions Toggle */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5 text-left">
                    <Label htmlFor="definition" className="text-sm font-medium">
                      Definition Questions
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Match words to their definitions
                    </p>
                  </div>
                  <Switch
                    id="definition"
                    checked={enableDefinitionQuiz}
                    onCheckedChange={(checked) =>
                      handleQuizPreferenceChange(
                        "enable_definition_quiz",
                        checked,
                        setEnableDefinitionQuiz,
                        enableDefinitionQuiz
                      )
                    }
                    disabled={isUpdatingQuizPreferences}
                  />
                </div>

                {/* Synonym Questions Toggle */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5 text-left">
                    <Label htmlFor="synonym" className="text-sm font-medium">
                      Synonym Questions
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Identify synonyms and related words
                    </p>
                  </div>
                  <Switch
                    id="synonym"
                    checked={enableSynonymQuiz}
                    onCheckedChange={(checked) =>
                      handleQuizPreferenceChange(
                        "enable_synonym_quiz",
                        checked,
                        setEnableSynonymQuiz,
                        enableSynonymQuiz
                      )
                    }
                    disabled={isUpdatingQuizPreferences}
                  />
                </div>

                {/* Info Note */}
                <div className="rounded-lg bg-muted p-3 text-left">
                  <p className="text-sm text-muted-foreground">
                    <strong>Note:</strong> If all advanced question types are disabled,
                    the system will automatically enable them all to ensure you can still
                    progress to the advanced learning stage.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Languages Section */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle className="text-left">Languages</CardTitle>
              <CardDescription className="text-left">
                Manage your primary language and learning languages. Reorder languages here to change the order of columns on the Translate page.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LanguageManager />
            </CardContent>
          </Card>
        </section>

        {/* Account Section */}
        <section>
          <Card>
            <CardHeader className="text-left">
              <CardTitle>Account</CardTitle>
              <CardDescription className="text-left">
                Manage your account data.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-foreground text-left">
                You can delete your account with all your search history and learning progress.
              </p>

              <div className="text-left">
                <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="destructive" size="sm">
                      Delete Account
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader className="text-left">
                      <DialogTitle>Delete Account</DialogTitle>
                      <DialogDescription className="text-left">
                        This action cannot be undone.
                      </DialogDescription>
                    </DialogHeader>

                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle className="text-left">Warning</AlertTitle>
                      <AlertDescription className="text-left">
                        Deleting your account will permanently remove all your data,
                        including:
                        <ul className="list-disc list-inside mt-2 space-y-1 text-left">
                          <li>All search history</li>
                          <li>All practice progress</li>
                          <li>Learning statistics</li>
                          <li>Account settings</li>
                        </ul>
                      </AlertDescription>
                    </Alert>

                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setDeleteDialogOpen(false)}
                        disabled={isDeleting}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={handleDeleteAccount}
                        disabled={isDeleting}
                      >
                        {isDeleting ? "Deleting..." : "Delete My Account"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}