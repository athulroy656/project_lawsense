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

        let message = errorData.detail || errorData.error || errorData.message;

        if (!message && typeof errorData === 'object' && Object.keys(errorData).length > 0) {
            const firstKey = Object.keys(errorData)[0];
            const val = errorData[firstKey];

            if (Array.isArray(val) && val.length > 0) {
                const cleanKey = firstKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                if (firstKey === 'non_field_errors') {
                    message = val[0];
                } else {
                    message = `${cleanKey}: ${val[0]}`;
                }
            } else if (typeof val === 'string') {
                message = val;
            }
        }

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

// Admin API functions
export async function checkAdminStatus() {
    const res = await fetch(`${API_BASE}/admin/me/`, {
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function fetchAdminOverview() {
    const res = await fetch(`${API_BASE}/admin/overview/`, {
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function fetchAdminDocumentTypes() {
    const res = await fetch(`${API_BASE}/admin/document-types/`, {
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function fetchAdminSystemHealth() {
    const res = await fetch(`${API_BASE}/admin/system-health/`, {
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function fetchAdminRecentDocuments() {
    const res = await fetch(`${API_BASE}/admin/recent-documents/`, {
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function adminDeleteDocument(id) {
    const res = await fetch(`${API_BASE}/admin/documents/${id}/delete/`, {
        method: 'DELETE',
        headers: getHeaders()
    });
    if (res.status === 204) return null;
    return handleResponse(res);
}

export async function adminRerunDocument(id) {
    const res = await fetch(`${API_BASE}/admin/documents/${id}/rerun/`, {
        method: 'POST',
        headers: getHeaders()
    });
    return handleResponse(res);
}

export async function fetchAdminUsers(page = 1, pageSize = 25, search = "") {
    let url = `${API_BASE}/admin/users/?page=${page}&page_size=${pageSize}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const res = await fetch(url, {
        headers: getHeaders()
    });
    return handleResponse(res);
}
