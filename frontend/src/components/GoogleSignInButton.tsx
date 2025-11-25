import { useEffect, useRef } from "react";

interface GoogleSignInButtonProps {
  onSuccess?: (response: google.accounts.id.CredentialResponse) => void;
  onError?: () => void;
}

// Extend the Window interface to include google
declare global {
  interface Window {
    google?: typeof google;
  }
}

export default function GoogleSignInButton({
  onSuccess,
  onError
}: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Wait for Google Identity Services to load
    const initializeGoogleSignIn = () => {
      if (window.google && buttonRef.current) {
        window.google.accounts.id.initialize({
          client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID",
          callback: (response: google.accounts.id.CredentialResponse) => {
            if (onSuccess) {
              onSuccess(response);
            }
          },
          error_callback: () => {
            if (onError) {
              onError();
            }
          },
        });

        window.google.accounts.id.renderButton(
          buttonRef.current,
          {
            theme: "outline",
            size: "large",
            width: buttonRef.current.offsetWidth,
            text: "signin_with",
          }
        );
      }
    };

    // Check if Google script is already loaded
    if (window.google) {
      initializeGoogleSignIn();
    } else {
      // Wait for the script to load
      const checkGoogleLoaded = setInterval(() => {
        if (window.google) {
          clearInterval(checkGoogleLoaded);
          initializeGoogleSignIn();
        }
      }, 100);

      return () => clearInterval(checkGoogleLoaded);
    }
  }, [onSuccess, onError]);

  return <div ref={buttonRef} className="w-full" />;
}
