"use strict";

function guidanceErrorMessage(error) {
  if (error instanceof TypeError) {
    return "Could not reach the local backend. Start FastAPI on 127.0.0.1:8000 (on Windows, run start-api.cmd), then try again.";
  }
  return error instanceof Error && error.message
    ? error.message
    : "The backend could not explain this finding. Please try again.";
}

function showGuidanceError(container, error, documentRef = globalThis.document) {
  const message = documentRef.createElement("p");
  message.className = "error-message";
  message.setAttribute("role", "alert");
  message.textContent = guidanceErrorMessage(error);
  container.replaceChildren(message);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { guidanceErrorMessage, showGuidanceError };
} else {
  globalThis.A11yLens = globalThis.A11yLens || {};
  Object.assign(globalThis.A11yLens, { guidanceErrorMessage, showGuidanceError });
}
