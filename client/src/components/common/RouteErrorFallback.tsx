import { useRouteError, useNavigate, Link } from "react-router";
import { AlertTriangle, FileQuestion, RefreshCcw, Home } from "lucide-react";

export function RouteErrorFallback() {
  const error: any = useRouteError();
  const navigate = useNavigate();

  // Check if it's a 404 Not Found error
  const is404 = error?.status === 404 || error?.statusText === "Not Found";

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-card border border-border rounded-lg shadow-lg p-8 text-center space-y-6">
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
          {is404 ? (
            <FileQuestion className="w-8 h-8 text-primary" />
          ) : (
            <AlertTriangle className="w-8 h-8 text-destructive" />
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            {is404 ? "Page Not Found" : "Something went wrong"}
          </h1>
          <p className="text-muted-foreground">
            {is404
              ? "The page you are looking for does not exist or has been moved."
              : "An unexpected application error occurred."}
          </p>
        </div>

        {/* Show error trace/message in development mode */}
        {import.meta.env.DEV && error && (
          <div className="bg-muted p-4 rounded text-left overflow-auto max-h-48 text-xs font-mono text-muted-foreground border border-border">
            <p className="font-semibold text-foreground mb-1">
              {error.status ? `Status: ${error.status} ${error.statusText || ""}` : "Error Message:"}
            </p>
            {error.message || error.data || String(error)}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          {is404 ? (
            <Link
              to="/"
              className="inline-flex items-center justify-center gap-2 w-full bg-primary text-primary-foreground font-medium px-4 py-2.5 rounded-[4px] hover:bg-primary/90 transition-colors"
            >
              <Home className="w-4 h-4" />
              Go to Home
            </Link>
          ) : (
            <>
              <button
                onClick={handleReload}
                className="inline-flex items-center justify-center gap-2 w-full bg-primary text-primary-foreground font-medium px-4 py-2.5 rounded-[4px] hover:bg-primary/90 transition-colors"
              >
                <RefreshCcw className="w-4 h-4" />
                Reload Page
              </button>
              <button
                onClick={() => navigate(-1)}
                className="inline-flex items-center justify-center gap-2 w-full bg-secondary text-secondary-foreground border border-border font-medium px-4 py-2.5 rounded-[4px] hover:bg-secondary/80 transition-colors"
              >
                Go Back
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
