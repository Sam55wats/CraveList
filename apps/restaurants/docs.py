API_ENDPOINTS = {
    "health": {
        "method": "GET",
        "path": "/api/health/",
        "auth": "public",
        "description": "Confirms the backend is running.",
    },
    "auth": [
        {
            "method": "GET",
            "path": "/api/auth/csrf/",
            "auth": "public",
            "description": "Sets and returns a CSRF token for session requests.",
        },
        {
            "method": "POST",
            "path": "/api/auth/register/",
            "auth": "public",
            "description": "Creates a user and logs them in.",
        },
        {
            "method": "POST",
            "path": "/api/auth/login/",
            "auth": "public",
            "description": "Logs a user in with username and password.",
        },
        {
            "method": "POST",
            "path": "/api/auth/logout/",
            "auth": "required",
            "description": "Logs out the current user.",
        },
        {
            "method": "GET",
            "path": "/api/auth/me/",
            "auth": "required",
            "description": "Returns the current logged-in user.",
        },
    ],
    "restaurants": [
        {
            "method": "GET",
            "path": "/api/restaurants/",
            "auth": "public",
            "description": "Lists searchable read-only restaurants.",
        },
        {
            "method": "GET",
            "path": "/api/restaurants/location-suggestions/",
            "auth": "public",
            "description": "Returns location suggestions from restaurant data.",
        },
        {
            "method": "GET",
            "path": "/api/external-restaurants/search/",
            "auth": "public",
            "description": "Searches a configured restaurant provider.",
        },
        {
            "method": "POST",
            "path": "/api/external-restaurants/import/",
            "auth": "required",
            "description": "Imports one provider restaurant into CraveList.",
        },
        {
            "method": "POST",
            "path": "/api/external-restaurants/import-and-save/",
            "auth": "required",
            "description": "Imports one provider restaurant and saves it to the user's list.",
        },
    ],
    "personal_restaurants": [
        {
            "method": "GET/POST/PATCH/DELETE",
            "path": "/api/my-restaurants/",
            "auth": "required",
            "description": "Manages the current user's bookmarked and visited restaurants.",
        },
        {
            "method": "GET",
            "path": "/api/recommendations/",
            "auth": "required",
            "description": "Returns deterministic recommendations from saved, unvisited restaurants.",
        },
    ],
    "social": [
        {
            "method": "GET",
            "path": "/api/users/",
            "auth": "public",
            "description": "Lists public user profiles with follow status and stats.",
        },
        {
            "method": "GET",
            "path": "/api/users/<id>/restaurants/",
            "auth": "public",
            "description": "Lists a user's public visited and rated restaurants.",
        },
        {
            "method": "GET/POST/DELETE",
            "path": "/api/follows/",
            "auth": "required",
            "description": "Manages follow relationships.",
        },
        {
            "method": "GET",
            "path": "/api/feed/",
            "auth": "required",
            "description": "Lists recent rated restaurants from followed users.",
        },
    ],
    "photos": [
        {
            "method": "GET/POST/DELETE",
            "path": "/api/my-restaurant-photos/",
            "auth": "mixed",
            "description": "Lists public photos and lets authenticated users upload/delete their own photos.",
        }
    ],
}
