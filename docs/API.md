# API Documentation - AI Error Solver Backend

## 🔗 Base URLs

- **Local Development**: `http://localhost:8000`
- **Production**: `http://YOUR_EC2_IP:8000`
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)

## 🔑 Authentication

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 2592000
}
```

### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "student|instructor"
}
```

## 🏥 Health & Status

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "AI Error Solver Backend is running"
}
```

### Root Endpoint
```http
GET /
```

**Response:**
```json
{
  "message": "Server is running"
}
```

## 📚 Project Management API

### List Projects
```http
GET /api/v1/project/
Authorization: Bearer YOUR_JWT_TOKEN
```

### Create Project
```http
POST /api/v1/project/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "name": "string",
  "description": "string",
  "github_url": "string"
}
```

### Get Project Details
```http
GET /api/v1/project/{project_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### Upload Project Files
```http
POST /api/v1/project/{project_id}/upload
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

file: [ZIP_FILE]
```

## 🔍 Indexing API

### Create Index
```http
POST /api/v1/index/create
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "project_id": "string",
  "branch": "main"
}
```

### Search Index
```http
POST /api/v1/index/search
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "query": "string",
  "project_id": "string",
  "limit": 10
}
```

## 🎓 Student Analysis API

### Analyze Student Code
```http
POST /api/v1/student/analyze
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

file: [ZIP_FILE]
instructor_project_id: string
```

**Response:**
```json
{
  "analysis_id": "string",
  "errors": [
    {
      "file": "string",
      "line": 0,
      "error_type": "string",
      "description": "string",
      "suggestion": "string",
      "fixed_code": "string"
    }
  ],
  "summary": {
    "total_errors": 0,
    "files_analyzed": 0,
    "similarity_score": 0.85
  }
}
```

### Get Analysis Results
```http
GET /api/v1/student/analysis/{analysis_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### List Student Analyses
```http
GET /api/v1/student/analyses
Authorization: Bearer YOUR_JWT_TOKEN
```

## 📊 User Management API

### Get User Profile
```http
GET /api/v1/user/profile
Authorization: Bearer YOUR_JWT_TOKEN
```

### Update User Profile
```http
PUT /api/v1/user/profile
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "email": "string",
  "full_name": "string"
}
```

## 🔐 Authentication Headers

Include this header in all authenticated requests:
```http
Authorization: Bearer YOUR_JWT_TOKEN
```

## 📝 Request/Response Examples

### Complete Student Analysis Flow

1. **Login**:
```bash
curl -X POST "http://YOUR_EC2_IP:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "student1", "password": "password123"}'
```

2. **Upload Student Code**:
```bash
curl -X POST "http://YOUR_EC2_IP:8000/api/v1/student/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@student_code.zip" \
  -F "instructor_project_id=proj_123"
```

3. **Get Analysis Results**:
```bash
curl -X GET "http://YOUR_EC2_IP:8000/api/v1/student/analysis/analysis_123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Error Analysis Response Example
```json
{
  "analysis_id": "analysis_456",
  "student_id": "student_123",
  "instructor_project_id": "proj_789",
  "created_at": "2024-01-15T10:30:00Z",
  "errors": [
    {
      "file": "src/main.py",
      "line": 25,
      "column": 10,
      "error_type": "syntax_error",
      "severity": "high",
      "description": "Missing closing parenthesis in function call",
      "suggestion": "Add closing parenthesis ')' at the end of line 25",
      "fixed_code": "result = calculate_sum(a, b)",
      "instructor_reference": {
        "file": "src/main.py",
        "line": 25,
        "code": "result = calculate_sum(a, b)"
      }
    },
    {
      "file": "src/utils.py",
      "line": 15,
      "column": 1,
      "error_type": "logic_error",
      "severity": "medium",
      "description": "Variable 'counter' is used before assignment",
      "suggestion": "Initialize 'counter' variable before using it",
      "fixed_code": "counter = 0\nfor item in items:",
      "instructor_reference": {
        "file": "src/utils.py",
        "line": 14,
        "code": "counter = 0"
      }
    }
  ],
  "summary": {
    "total_errors": 2,
    "syntax_errors": 1,
    "logic_errors": 1,
    "style_errors": 0,
    "files_analyzed": 5,
    "lines_analyzed": 150,
    "similarity_score": 0.87,
    "completion_percentage": 85
  },
  "recommendations": [
    "Review Python syntax basics",
    "Pay attention to variable initialization",
    "Use a code formatter like Black"
  ]
}
```

## 🚨 Error Responses

### Standard Error Format
```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

### Authentication Errors
```json
{
  "detail": "Could not validate credentials",
  "error_code": "INVALID_TOKEN"
}
```

### Validation Errors
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 📱 Rate Limits

- **Analysis API**: 10 requests per minute per user
- **Authentication**: 5 login attempts per minute per IP
- **File Upload**: Maximum file size 50MB

## 🔧 SDKs and Examples

### Python Client Example
```python
import requests

# Authentication
login_response = requests.post(
    "http://YOUR_EC2_IP:8000/api/v1/auth/login",
    json={"username": "student1", "password": "password123"}
)
token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Upload and analyze code
with open("student_code.zip", "rb") as f:
    files = {"file": f}
    data = {"instructor_project_id": "proj_123"}
    
    response = requests.post(
        "http://YOUR_EC2_IP:8000/api/v1/student/analyze",
        headers=headers,
        files=files,
        data=data
    )
    
analysis = response.json()
print(f"Analysis ID: {analysis['analysis_id']}")
print(f"Total errors found: {analysis['summary']['total_errors']}")
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const API_BASE = 'http://YOUR_EC2_IP:8000';

// Login
async function login(username, password) {
  const response = await axios.post(`${API_BASE}/api/v1/auth/login`, {
    username,
    password
  });
  return response.data.access_token;
}

// Analyze student code
async function analyzeCode(token, filePath, instructorProjectId) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  form.append('instructor_project_id', instructorProjectId);
  
  const response = await axios.post(
    `${API_BASE}/api/v1/student/analyze`,
    form,
    {
      headers: {
        ...form.getHeaders(),
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return response.data;
}

// Usage
(async () => {
  const token = await login('student1', 'password123');
  const analysis = await analyzeCode(token, 'student_code.zip', 'proj_123');
  console.log('Analysis completed:', analysis.analysis_id);
})();
```

## 📊 WebSocket Support (Future Feature)

Real-time analysis updates will be available via WebSocket:
```javascript
const ws = new WebSocket('ws://YOUR_EC2_IP:8000/ws/analysis/{analysis_id}');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Analysis progress:', update.progress);
};
```

---

## 🔗 Interactive Documentation

Visit `http://YOUR_EC2_IP:8000/docs` for interactive API documentation where you can:
- Try all endpoints directly
- See real request/response examples
- Generate code snippets
- Test authentication flows
