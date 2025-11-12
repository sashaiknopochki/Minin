# Authentication
POST   /auth/google/login
POST   /auth/logout
GET    /auth/user

# Translation
POST   /api/translate
GET    /api/search-history
DELETE /api/phrases/{id}

# Learning
GET    /api/quiz/next
POST   /api/quiz/answer
GET    /api/progress
GET    /api/learned-phrases

# Settings
GET    /api/languages
PUT    /api/user/settings
PUT    /api/user/primary-language