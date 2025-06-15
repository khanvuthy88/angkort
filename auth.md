# Authentication API Documentation

This document outlines the authentication system and available endpoints for the API.

## Overview

The authentication system uses JWT (JSON Web Tokens) for secure user authentication. It implements a token-based authentication flow with both access and refresh tokens.

## Token Types

- **Access Token**: Short-lived token (30 minutes) used for API access
- **Refresh Token**: Long-lived token (7 days) used to obtain new access tokens

## Endpoints

### Login

```http
POST /api/login
```

Authenticates a user and returns access and refresh tokens.

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

### Refresh Token

```http
POST /api/refresh
```

Generates a new access token using a valid refresh token.

**Request Body:**

```json
{
  "refresh_token": "string"
}
```

**Response:**

```json
{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

### Logout

```http
POST /api/logout
```

Invalidates the current access token and logs out the user.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "message": "Successfully logged out"
}
```

## Token Validation

All protected endpoints require a valid access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

The token validation checks:

1. Token presence and format
2. Token expiration
3. User existence in the database

## Error Responses

### 401 Unauthorized

```json
{
  "error": "Missing or invalid Authorization header"
}
```

or

```json
{
  "error": "Token has expired"
}
```

or

```json
{
  "error": "Invalid token"
}
```

### 400 Bad Request

```json
{
  "error": "Invalid username or password"
}
```

or

```json
{
  "message": "Access token missing"
}
```

## Security Notes

1. Access tokens expire after 30 minutes
2. Refresh tokens expire after 7 days
3. Tokens are signed using HS256 algorithm
4. The system uses a secure secret key stored in system parameters
5. All tokens are stored in the database for tracking and invalidation

## Implementation Details

The authentication system is implemented using:

- JWT for token generation and validation
- Odoo's built-in user authentication
- Token storage in the `res.user.token` model
- Secure password hashing and validation

## Best Practices

1. Always use HTTPS in production
2. Store tokens securely on the client side
3. Implement token refresh before access token expiration
4. Clear tokens on logout
5. Monitor for suspicious activity
