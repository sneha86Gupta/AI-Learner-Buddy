# AI-Learner-Buddy
AI Learner Buddy is an AI-powered course creation and learning platform. It allows users to generate structured courses, chapters, and detailed chapter content dynamically using AI. Built with Flask, SQLite, and Google’s Generative AI, it provides an intuitive interface for managing personalized learning journeys.
## 📌 Features So Far

- **User Authentication**
  - Register, login, and logout functionality.
  - Password hashing for security.
- **Course Management**
  - Create new courses with a title, difficulty level, and number of chapters.
  - View a list of created courses.
- **Chapter Management**
  - Auto-generate chapter titles using AI.
  - View a list of chapters for each course.
- **Content Generation**
  - Generate detailed content for each chapter dynamically via AI.
- **Navigation**
  - Dashboard showing all courses and basic statistics.
  - Structured navigation between dashboard, courses, chapters, and content.
- **Responsive UI**
  - Modern interface built using HTML, CSS, and Bootstrap.

---

## 🛠 Tech Stack

- **Backend:** Python, Flask  
- **Frontend:** HTML, CSS, Bootstrap  
- **Database:** SQLite  
- **AI Integration:** Google Generative AI API  
- **Authentication:** Flask sessions, password hashing with Werkzeug  

---

## 📁 Project Structure

AI-Learner-Buddy/
│
├── app.py # Main Flask app for dashboard, chapters, content
├── auth.py # Authentication (login, register, logout)
├── ai_api.py # AI helper functions for course/chapter generation
├── templates/ # HTML template files
│ ├── main.html
│ ├── dashboard.html
│ ├── chapters.html
│ ├── content.html
│ ├── login.html
│ ├── register.html
│ └── ...
├── static/ # CSS, JS, images
├── users.db # SQLite database file
└── README.md # Project documentation
---
##📷 Example Output
### Dashboard  
Shows total courses, completed courses, in-progress courses, and a course generator form.
![Dashboard Screenshot](static/images/dashboard.png)

---
