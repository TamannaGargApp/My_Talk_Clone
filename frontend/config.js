// Local development: http://localhost:8000
// Production: replace with your public Render backend URL, without a trailing slash.
window.API_BASE_URL =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "";
