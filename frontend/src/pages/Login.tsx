import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import { apiFetch } from "@/lib/api";

// Use the same CredentialResponse type from GoogleSignInButton
interface CredentialResponse {
  credential: string;
}

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  // Redirect to home if already logged in
  useEffect(() => {
    if (user) {
      navigate("/");
    }
  }, [user, navigate]);

  // Handle Google Sign-In success
  const handleGoogleSignIn = async (response: CredentialResponse) => {
    try {
      const result = await apiFetch("/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ credential: response.credential }),
      });

      const data = await result.json();

      if (data.success && data.user) {
        login(data.user);
        navigate("/");
      } else {
        console.error("Sign-in failed:", data.error);
      }
    } catch (error) {
      console.error("Sign-in error:", error);
    }
  };

  // Handle Google Sign-In error
  const handleGoogleSignInError = () => {
    console.error("Google Sign-In failed");
  };

  return (
    <div className="bg-muted flex min-h-svh flex-col items-center justify-center gap-6 p-1 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        {/* Logo/Branding <a href="/" className="flex items-center gap-2 self-center font-medium">
           <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-md text-xl font-bold">
            m
          </div>
          minin
        </a>*/}

        {/* Login Card */}
        <div className="flex flex-col gap-6 rounded-lg border bg-background p-6 shadow-lg">
          <div className="flex flex-col gap-2 text-center">
            <h1 className="text-lg font-semibold leading-7">
              Welcome to Minin
            </h1>
            <p className="text-sm text-muted-foreground leading-5">
              Multi-language translator that teaches you as you search with
              AI-powered quizzes to help you build active vocabulary.
            </p>
          </div>

          <div className="flex flex-col gap-2 w-full">
            <GoogleSignInButton
              onSuccess={handleGoogleSignIn}
              onError={handleGoogleSignInError}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
