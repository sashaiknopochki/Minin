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

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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

      <div className="space-y-6">
        {/* Learning Section */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle className="text-left">Learning</CardTitle>
              <CardDescription className="text-left">

              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-left">
                Your learning statistics and progress will be displayed here.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Languages Section */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle className="text-left">Languages</CardTitle>
              <CardDescription className="text-left">

              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-left">
                Configure your primary language and translation targets here.
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Account Section */}
        <section>
          <Card>
            <CardHeader className="text-left">
              <CardTitle>Account</CardTitle>
              <CardDescription className="text-left">

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