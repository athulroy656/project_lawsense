const API_BASE = "http://127.0.0.1:8000/api";

const getHeaders = (isMultipart = false) => {
  const token = localStorage.getItem('access_token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!isMultipart) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
};

const handleResponse = async (res) => {
  if (res.status === 401) {
    // Token expired or invalid
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error("You must be logged in to perform this action.");
  }

  if (!res.ok) {
    let errorData = {};
    try {
      errorData = await res.json();
    } catch (e) {
      // Response was not JSON
    }

    // 1. Try to find a direct error message in common keys
    let message = errorData.detail || errorData.error || errorData.message;

    // 2. Handle DRF field-specific validation errors: { "field": ["Error msg"] }
    if (!message && typeof errorData === 'object' && Object.keys(errorData).length > 0) {
      const firstKey = Object.keys(errorData)[0];
      const val = errorData[firstKey];

      if (Array.isArray(val) && val.length > 0) {
        // e.g. "Email: Enter a valid email address."
        // Beautify the key: 'confirm_password' -> 'Confirm Password'
        const cleanKey = firstKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        // If key is non_field_errors, just show the message
        if (firstKey === 'non_field_errors') {
          message = val[0];
        } else {
          message = `${cleanKey}: ${val[0]}`;
        }
      } else if (typeof val === 'string') {
        message = val;
      }
    }

    // 3. Fallback to status codes if no message found
    if (!message) {
      switch (res.status) {
        case 400:
          message = "Please check the form fields and try again.";
          break;
        case 403:
          message = "You do not have permission to perform this action.";
          break;
        case 404:
          message = "The requested resource was not found.";
          break;
        case 500:
          message = "Server error. Please try again later.";
          break;
        default:
          message = `Request failed (${res.status}). Please try again.`;
      }
    }

    throw new Error(message);
  }

  if (res.status === 204) return null;
  return await res.json();
};

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return handleResponse(res);
}

export async function register(username, email, password, confirm_password) {
  const res = await fetch(`${API_BASE}/auth/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password, confirm_password })
  });
  return handleResponse(res);
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents/`, {
    headers: getHeaders()
  });
  return handleResponse(res);
}

export async function fetchClauses(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/clauses/`, {
    headers: getHeaders()
  });
  return handleResponse(res);
}

export async function fetchRiskSummary(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/risk-summary/`, {
    headers: getHeaders()
  });
  return handleResponse(res);
}

export async function fetchDocumentReport(documentId, includeAI = false, docTypeOverride = null) {
  let url = `${API_BASE}/documents/${documentId}/report/`;
  const params = new URLSearchParams();

  if (includeAI) params.append('ai_summary', 'true');
  if (docTypeOverride && docTypeOverride !== 'AUTO') params.append('document_type_override', docTypeOverride);

  const queryString = params.toString();
  if (queryString) url += `?${queryString}`;

  const res = await fetch(url, {
    headers: getHeaders()
  });
  return handleResponse(res);
}

export async function uploadDocument(file, title, documentType, inputMethod, pastedText) {
  const formData = new FormData();
  if (inputMethod === "file" && file) {
    formData.append("file", file);
  } else if (inputMethod === "text" && pastedText) {
    formData.append("pasted_text", pastedText);
  }

  if (title) formData.append("title", title);
  if (documentType) formData.append("document_type", documentType);
  formData.append("input_method", inputMethod);

  const res = await fetch(`${API_BASE}/documents/upload/`, {
    method: "POST",
    headers: getHeaders(true), // isMultipart = true
    body: formData,
  });
  return handleResponse(res);
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${API_BASE}/documents/${documentId}/`, {
    method: "DELETE",
    headers: getHeaders()
  });
  return handleResponse(res);
}

export async function askQuestion(question, documentId) {
  const res = await fetch(`${API_BASE}/ask/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ question, document_id: documentId }),
  });
  return handleResponse(res);
}
