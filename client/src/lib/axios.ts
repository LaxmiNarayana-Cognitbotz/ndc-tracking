import axios from "axios";
import { toast } from "sonner";

const api = axios.create({
  baseURL: import.meta.env.BASE_URL, // Resolves to '/ndc/' from vite base config
});

// Request interceptor for API calls
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for API calls
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Skip global toast if request configured skipGlobalToast
    if ((error.config as any)?.skipGlobalToast) {
      return Promise.reject(error);
    }

    // Determine the error message
    let message =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      "An unexpected API error occurred.";

    // Simplify error message for internal server errors to avoid exposing internal traceback/DB details
    if (error.response?.status === 500) {
      message = "An unexpected server error occurred. Please try again later.";
    }

    // Display global error toast
    toast.error(`Error: ${message}`, {
      description: error.response?.status ? `Status code: ${error.response.status}` : "Network error",
    });

    return Promise.reject(error);
  }
);

export default api;
