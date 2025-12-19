/**
 * API Configuration
 *
 * In development: Uses relative URLs (e.g., "/api/...") which are proxied by Vite to localhost:5001
 * In production: Uses VITE_API_URL from environment variables to point to the deployed backend
 */

// Get the API base URL from environment variables
// In production, this should be set to your backend URL (e.g., https://your-backend.run.app)
// In development, this will be undefined and we'll use relative URLs with Vite's proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || "";

/**
 * Constructs the full API URL for a given endpoint
 * @param endpoint - The API endpoint path (e.g., "/api/languages")
 * @returns The full URL to use for the API call
 */
export function getApiUrl(endpoint: string): string {
  // If API_BASE_URL is set (production), use it
  // Otherwise, use relative URL (development with Vite proxy)
  return API_BASE_URL ? `${API_BASE_URL}${endpoint}` : endpoint;
}

/**
 * Wrapper around fetch that automatically uses the correct API URL
 * and handles common authentication errors
 * @param endpoint - The API endpoint path
 * @param options - Standard fetch options
 * @returns Promise with the fetch response
 */
export async function apiFetch(
  endpoint: string,
  options?: RequestInit,
): Promise<Response> {
  const url = getApiUrl(endpoint);

  // Always include credentials for cookie-based auth
  const fetchOptions: RequestInit = {
    ...options,
    credentials: "include",
  };

  const response = await fetch(url, fetchOptions);

  // If we get a 401 (Unauthorized) and we're not already on the login page,
  // redirect to login
  if (response.status === 401 && !window.location.pathname.includes("/login")) {
    console.warn(
      "Session expired or not authenticated. Redirecting to login...",
    );
    window.location.href = "/login";
    throw new Error("Authentication required");
  }

  return response;
}
