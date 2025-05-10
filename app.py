import streamlit as st
import pandas as pd
from auth import (create_user, authenticate_user, insert_session, 
                  get_sessions_for_user, get_sessions_hosted_by, propose_slots_to_session, 
                  get_proposed_slots, finalize_slot, get_session_by_id, 
                  get_resources, add_resource)
from bson.objectid import ObjectId
from cloudinary_config import cloudinary
import cloudinary.uploader
from datetime import datetime, timedelta
from collections import Counter
import base64
import os
import sendgrid
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import pickle
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


st.set_page_config(page_title="StudySync", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# 
# --- Sidebar ---
with st.sidebar:
    if not st.session_state.authenticated:
        st.title("🔐 Login / Register")
        auth_mode = st.radio("Choose Action", ["Login", "Register"], key="auth_mode")
    else:
        st.title("📚StudySync")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()

# --- Main Area ---
if not st.session_state.authenticated:
    st.title(f"{st.session_state.auth_mode}")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Submit"):
        if st.session_state.auth_mode == "Login":
            if authenticate_user(email, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.page = "dashboard"
                st.success("✅ Logged in")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        else:  # Register mode
            ok = create_user(email, password)
            if ok:
                st.success("✅ Registered successfully. Please login.... ")
            else:
                st.error("❌ Registration failed")

else:
    if st.session_state.page == "dashboard":
        load_dotenv()
        st.title("📚 StudySync Dashboard")
        st.write(f"Welcome, {st.session_state.user_email.split('@')[0].title()}!")

        # CSS styling for cards
        st.markdown("""
    <style>
        .card-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.5rem;
            padding-top: 2rem;
        }
        .card-button {
            background-color: #fff;
            padding: 1.5rem 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            font-size: 1.2rem;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s ease-in-out;
            width: 100%;
            max-width: 350px;
            border: none;
        }
        .card-button:hover {
            transform: scale(1.02);
            background-color: #f0f2f6;
        }
    </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="card-container">', unsafe_allow_html=True)

        if st.button("📚 Create Study Session", key="create"):
            st.session_state.page = "create_session"
            st.rerun()

        if st.button("🗳️ Vote on Session", key="vote"):
            st.session_state.page = "vote_session"
            st.rerun()

        if st.button("🗳️ Finalize Votes", key="final_vote"):
            st.session_state.page = "final_vote_session"
            st.rerun()

        if st.button("📁 View Resources", key="resources"):
            st.session_state.page = "resources"
            st.rerun()

        if st.button("📅 Calendar View", key="calendar"):
            st.session_state.page = "calendar"
            st.rerun()

        if st.button("📊 Feedback & Analytics", key="feedback"):
            st.session_state.page = "feedback"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


        # Other pages
    elif st.session_state.page == "create_session":
        st.title("📚 Create Study Session")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        # Session form
        with st.form("create_session_form"):
            session_title = st.text_input("📌 Session Topic", placeholder="e.g. Linear Algebra - Final Prep")
            session_description = st.text_area("📝 Description", placeholder="Details, materials covered, etc.")
    
            participants = st.text_area("👥 Invite Participants (comma-separated emails)",
                                 placeholder="e.g. alice@example.com, bob@university.edu")

            propose_deadline = st.date_input("📅 Deadline to Propose Time Slots",
                                     min_value=datetime.now().date() + timedelta(days=1))

            submitted = st.form_submit_button("➕ Create Session")

        # Handle form submission
        if submitted:
            if not session_title or not participants:
                st.error("Please provide at least a title and one participant.")
            else:
                participant_list = [email.strip() for email in participants.split(",") if email.strip()]
        
                # Here you'd call your MongoDB insert function (replace with your function later)
                session_data = {
                    "host_email": st.session_state.user_email,
                    "title": session_title,
                    "description": session_description,
                    "participants": participant_list,
                    "propose_deadline": str(propose_deadline),
                    "created_at": str(datetime.utcnow()),
                    "finalized": False,
                    "proposed_slots": [],
                    "confirmed_slot": None
                }

                st.success("🎉 Session created successfully!")
                insert_session(session_data)
                st.success("🎉 Session saved to database!")


    elif st.session_state.page == "vote_session":
        st.title("🗳️ Propose/Vote Time Slots for Study Session")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        
        user_email = st.session_state.user_email
        sessions = get_sessions_for_user(user_email)

        if not sessions:
            st.info("🤷 You have no invited sessions.")
            st.stop()

        session_map = {f"{s['title']} (Host: {s['host_email']})": s for s in sessions}
        selected = st.selectbox("Select a session to propose slots", list(session_map.keys()))

        session = session_map[selected]
        session_id = session["_id"]

        with st.form("propose_slots"):
            st.subheader(f"Propose time slots for: {session['title']}")
            slot_count = st.number_input("How many time slots do you want to propose?", min_value=1, max_value=5, step=1)
            proposed_slots = []

            for i in range(slot_count):
                slot = st.date_input(f"Date {i+1}", key=f"date_{i}")
                time = st.time_input(f"Time {i+1}", key=f"time_{i}")
                proposed_slots.append(datetime.combine(slot, time).isoformat())

            submitted = st.form_submit_button("Submit Time Slots")

            if submitted:
                propose_slots_to_session(ObjectId(session_id), user_email, proposed_slots)
                st.success("✅ Time slots proposed successfully.")

    elif st.session_state.page == "final_vote_session":
        st.title("🕒 Finalize Study Session Time (Host Only)")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

        user_email = st.session_state.user_email
        #sessions = get_sessions_for_user(user_email)
        sessions = get_sessions_hosted_by(user_email)

        host_sessions = [s for s in sessions if s['host_email'] == user_email]
        
        if not host_sessions:
            st.info("🤷 You are not hosting any sessions.")
            st.stop()

        session_map = {f"{s['title']} ({s['_id']})": s for s in host_sessions}
        selected = st.selectbox("Select a session to finalize", list(session_map.keys()))

        session = session_map[selected]
        session_id = session["_id"]

        # Show all proposed slots
        proposed = get_proposed_slots(ObjectId(session_id))
        flat_slots = []

        for entry in proposed:
            for slot in entry["slots"]:
                flat_slots.append(slot)

        slot_counts = Counter(flat_slots)
        st.subheader("🗳️ Slot Votes")
        for slot, count in slot_counts.items():
            st.write(f"🕐 {slot} — {count} vote(s)")

        def send_confirmation_email(session, final_slot):
            sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])

            for email in session["participants"]:
                message = Mail(
                    from_email="shubhamgupta94181@gmail.com",
                    to_emails=email,
                    subject="✅ Study Session Confirmed!",
                    html_content=f"""
                    <p>Hi {email.split('@')[0].title()},</p>
                    <p>The study session <strong>{session['title']}</strong> has been confirmed at:</p>
                    <h3>{final_slot}</h3>
                    <p>Thanks,<br>StudySync Team</p>
                """
                )
                try:
                    r = sg.send(message)
                    st.write(r.status_code)
                except Exception as e:
                    print(f"SendGrid error for {email}: {e}")

        # Determine if there's a clear majority
        most_common = slot_counts.most_common(1)
        confirmed_slot = None

        if most_common and most_common[0][1] > 1:
            confirmed_slot = most_common[0][0]
            st.success(f"✅ Majority Slot Found: {confirmed_slot}")
            if st.button("Finalize & Notify"):
                finalize_slot(ObjectId(session_id), confirmed_slot)
                st.success("Session time finalized. Sending notifications...")
                send_confirmation_email(session, confirmed_slot)
        else:
            st.warning("⚠️ No clear majority. Please select a slot manually:")
            custom_slot = st.selectbox("Pick one from proposed", list(slot_counts.keys()))
            if st.button("Finalize Custom & Notify"):
                finalize_slot(ObjectId(session_id), custom_slot)
                st.success("✅ Session time finalized by host.")
                send_confirmation_email(session, custom_slot)

    
    elif st.session_state.page == "resources":
        st.title("📁 Shared Resources")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        
        user_email = st.session_state.user_email
        sessions = get_sessions_for_user(user_email)

        if not sessions:
            st.info("No sessions found.")
            st.stop()

        session_map = {f"{s['title']} ({s['_id']})": s for s in sessions}
        selected = st.selectbox("Select a session", list(session_map.keys()))
        session = session_map[selected]
        session_id = ObjectId(session["_id"])

        st.subheader("📤 Upload Resources")

        uploaded_file = st.file_uploader("Upload a file (PDF, DOC, PPT)", type=["pdf", "docx", "pptx"])
        link = st.text_input("Or share a link (Google Docs, Notes, etc.)")

        if st.button("Share"):
            if uploaded_file:
                result = cloudinary.uploader.upload(
                    uploaded_file,
                    resource_type="raw",  # for non-image files like PDFs, DOCs
                    folder=f"study_sessions/{session_id}/"
                )
                file_url = result['secure_url']
                file_name = uploaded_file.name
                add_resource(session_id, user_email, file_url=file_url, filename=file_name)
                st.success("✅ File uploaded to Cloudinary!")
            elif link:
                add_resource(session_id, user_email, link=link)
                st.success("✅ Link shared!")
            else:
                st.warning("Please upload a file or share a link.")

        st.divider()

        st.subheader("📚 Shared Resources")
        resources = get_resources(session_id)

        if not resources:
            st.info("No resources shared yet.")
        else:
            for r in sorted(resources, key=lambda x: x["timestamp"], reverse=True):
                uploader = r["uploader"]
                time = r["timestamp"].strftime("%Y-%m-%d %H:%M")

                if "file_url" in r:
                    st.markdown(f"📄 **[{r['filename']}]({r['file_url']})** — uploaded by `{uploader}` on `{time}`")
                elif "link" in r:
                    st.markdown(f"🔗 [Link]({r['link']}) — shared by `{uploader}` on `{time}`")


    elif st.session_state.page == "calendar":
        #st.title("📅 Calendar Integration")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

        load_dotenv()

        CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        def get_flow():
            return Flow.from_client_config(
                {
                    "web": {
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "redirect_uris": [REDIRECT_URI],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )

        def save_token(token):
            with open("token.json", "w") as f:
                json.dump(token, f)

        def load_token():
            try:
                with open("credentials.pkl", "rb") as token:
                    return pickle.load(token)
            except FileNotFoundError:
                return None

        st.title("📅 Google Calendar Integration")

        creds = load_token()

        if not creds or not creds.valid:
            flow = get_flow()
            auth_url, _ = flow.authorization_url(prompt='consent')

            st.markdown(f"[🔐 Click here to authorize Google Calendar]({auth_url})")

            query_params = st.query_params

            # After redirect from Google
            if "code" in query_params:
                auth_code = query_params["code"][0]
                flow.fetch_token(code=auth_code)
                creds = flow.credentials

                # Save credentials to session and optionally to file
                st.session_state.credentials = creds
                with open("credentials.pkl", "wb") as f:
                    pickle.dump(creds, f)

                st.success("✅ Google Calendar connected successfully! Please refresh the app.")

        else:
            # Save loaded credentials to session
            st.session_state.credentials = creds

        # ----- Display upcoming events if authenticated -----

        if "credentials" in st.session_state:
            creds = st.session_state.credentials
            service = build("calendar", "v3", credentials=creds)

            now = datetime.utcnow().isoformat() + 'Z'
            later = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=later,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            st.subheader("📅 Upcoming Events This Week")

            if not events:
                st.info("No upcoming events found.")
            else:
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    st.markdown(f"**{event.get('summary', 'No Title')}**  \n🕒 {start_dt.strftime('%b %d, %Y %I:%M %p')}")
        else:
            st.warning("🔒 Please connect your Google Calendar using the link above.")

            

    elif st.session_state.page == "feedback":
        st.title("📊 Feedback & Analytics")
        if st.button("🔙 Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

        # Initialize feedback file if not exists
        FEEDBACK_FILE = "feedback.csv"
        if not os.path.exists(FEEDBACK_FILE):
            df_init = pd.DataFrame(columns=["session_id", "title", "host_email", "duration", "rating", "comment", "timestamp"])
            df_init.to_csv(FEEDBACK_FILE, index=False)

        # Fetch session details from MongoDB
        user_email = st.session_state.user_email
        sessions = get_sessions_for_user(user_email)
        host_sessions = [s for s in sessions if s['host_email'] == user_email]

        if not sessions:
            st.info("No sessions found.")
            st.stop()

        # session_map = {f"{s['title']} ({s['_id']})": s for s in sessions}
        # selected = st.selectbox("Select a session", list(session_map.keys()))
        # session = session_map[selected]
        # session_id = ObjectId(session["_id"])

        # Prepare session options for selectbox
        session_options = [(session["_id"], session["title"]) for session in sessions]  # Assuming "_id" as session_id
        session_ids, session_titles = zip(*session_options)

        # Display feedback form
        st.header("📝 Post-Session Feedback")

        session_id = st.selectbox("Select Session ID", options=session_ids, format_func=lambda x: next(
            title for id, title in zip(session_ids, session_titles) if id == x))
        selected_session = next(session for session in sessions if session["_id"] == session_id)

        # Pre-fill session details
        title = selected_session.get("title", "")
        host = selected_session.get("host_email", "")
        duration = selected_session.get("duration", 60)  # Default to 60 minutes if duration not found

        rating = st.slider("Rate the Session", 1, 5)
        comment = st.text_area("Your Comments")

        if st.button("Submit Feedback"):
            # Create new feedback entry
            new_entry = pd.DataFrame([{
                "session_id": session_id,
                "title": title,
                "host_email": host,
                "duration": duration,
                "rating": rating,
                "comment": comment,
                "timestamp": datetime.now()
            }])

            # Save feedback to CSV file
            new_entry.to_csv(FEEDBACK_FILE, mode="a", index=False, header=not os.path.exists(FEEDBACK_FILE))
            st.success("✅ Feedback submitted!")
            
            # --- Analytics Section ---
            st.header("📊 Feedback Analytics")

            # Load all feedback data
            feedback_data = pd.read_csv(FEEDBACK_FILE)

            if feedback_data.empty:
                st.info("No feedback data available yet.")
            else:
                # Calculate average ratings for each session
                session_ratings = feedback_data.groupby("session_id")["rating"].mean().reset_index()
                session_ratings = session_ratings.rename(columns={"rating": "average_rating"})

                # Merge with session details
                feedback_with_details = pd.merge(feedback_data, session_ratings, on="session_id")

                # Calculate other analytics:
                # 1. Most frequent topics
                topic_counts = feedback_with_details["title"].value_counts()

                # 2. Average session duration
                avg_duration = feedback_with_details["duration"].mean()

                # 3. Most common rating
                most_common_rating = feedback_with_details["rating"].mode()[0]

                # Show analytics
                st.subheader("Most Frequent Topics")
                st.write(topic_counts)

                st.subheader("Average Session Duration (minutes)")
                st.write(avg_duration)

                st.subheader("Most Common Rating")
                st.write(most_common_rating)

