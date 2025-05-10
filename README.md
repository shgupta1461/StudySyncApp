# 📚 StudySync – Collaborative Study Session Scheduler & Resource Share

## 🎯 Objective
**StudySync** is a web application designed to streamline collaborative learning. It enables authenticated users to create and manage study sessions, propose time slots, vote on convenient timings, share study materials, and give post-session feedback — all in one platform.

---

## 🧪 Scenario
Students often waste time coordinating schedules and exchanging notes through scattered channels. StudySync eliminates this by centralizing session planning, scheduling, and resource sharing.

---

## 👥 User Role: `user`
All users can:
- Host or join study sessions
- Share and access session-specific resources
- Provide feedback after sessions

---

## 🔐 Authentication & Authorization
- **Email/Password** based login
- Only **invited participants** can vote and access session resources

---

## 🧱 Core Modules

### 1. **Session Creation & Slot Proposals**
- Hosts define session topics and invite participants
- Participants can propose time slots
- Host finalizes one based on voting

### 2. **Voting & Confirmation**
- Invitees vote on preferred time slots
- **Majority wins**; if no clear winner, host decides
- Automated email notification confirms the final session time

### 3. **Resource Library**
- Each session has a shared space for:
  - Uploading notes, links, and PDFs
  - Timestamped uploads and downloads

### 4. **Calendar Integration**
- Sessions are shown in a **calendar view**
- Option to sync with **Google Calendar**

### 5. **Post-Session Feedback**
- Participants can submit a **rating and comments**
- Analytics dashboard shows:
  - Session durations
  - Topic popularity
  - Average ratings

---

## 💻 Tech Stack

| Layer               | Tech Used                             |
|---------------------|----------------------------------------|
| **Frontend**         | Streamlit                             |
| **Backend**          | Python                                |
| **Database**         | MongoDB (via `pymongo`)               |
| **Authentication**   | Email/Password                        |
| **Email Service**    | SendGrid                              |
| **Calendar API**     | Google Calendar API                   |
| **File Storage**     | Cloudinary                            |
| **Deployment**       | Streamlit Cloud                       |

---

## 🚀 Deployment

The app is deployed using [**Streamlit Cloud**](https://streamlit.io/cloud):

- Push your code to a GitHub repo.
- Connect the repo to Streamlit Cloud.
- Add the following **environment variables**:
  - `MONGO_URI`
  - `SENDGRID_API_KEY`
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `CLOUDINARY_CLOUD_NAME`
  - `CLOUDINARY_API_KEY`
  - `CLOUDINARY_API_SECRET`
- Set the `main` file as `streamlit_app.py` or your entry file.

Access App at https://studysyncapp.streamlit.app
---

## 📌 To Do
- [ ] Role-based dashboards (admin, student)
- [ ] Real-time chat within sessions
- [ ] Recurring session scheduler
- [ ] Push notifications

---

## 📧 Contact
For issues or feature requests, please raise an issue or reach out to the developer.

---

