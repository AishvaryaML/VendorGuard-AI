import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Sends a vendor URL to the backend for privacy policy discovery.
 * @param {string} url - The vendor website URL to analyze.
 * @returns {Promise<object>} The backend's analysis response.
 */
export async function analyzeVendor(url) {
  const response = await apiClient.post("/analyze", { url });
  return response.data;
}

export default apiClient;
