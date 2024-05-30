import json
import openai
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime
import uuid
import pytz
from openai import OpenAI


load_dotenv()
ACCESS_CODE = os.getenv("ACCESS_CODE")
assistant_id = os.getenv("assistant_id")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def entry_page():
    st.title('Access Code')
    user_code = st.text_input("Enter your access code:")
    user_email = st.text_input("Enter your BYUH email:")
    if st.button("Submit"):
        if user_code == ACCESS_CODE :

            if not firebase_admin._apps:
                cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"]))
                firebase_admin.initialize_app(cred, { 'databaseURL' : 'https://chatstore-history-default-rtdb.firebaseio.com/'})

            temp_modified_email = user_email.replace('.', ',')    

            ref = db.reference('student_emails')
            student_emails = ref.get()

            if student_emails and temp_modified_email in student_emails:

                st.success("Access granted.")
                st.session_state['access_granted'] = True
                st.session_state['user_email'] = user_email
                st.rerun()
            else:
                st.error("Invalid email. Please try again.")
        else:
            st.error("invalid access code please try again")

def libraryBot_page():
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())[:8]
    session_id = st.session_state['session_id']

    if 'session_start_time' not in st.session_state:
        hawaii = pytz.timezone('Pacific/Honolulu')
        st.session_state['session_start_time'] = datetime.now(hawaii)
    session_start_time = st.session_state['session_start_time']

    user_email = st.session_state.get('user_email', '')

    # @st.cache_data()
    # def initialize_firebase():
    #     cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"]))
    #     firebase_admin.initialize_app(cred, { 'databaseURL' : 'https://chatstore-history-default-rtdb.firebaseio.com/'})

    # initialize_firebase()

    def record_output(role, output):
        reference = session_ref.child('outputs')
        output_data = {
            'role' : role,
            'content' : output,   
        }
        reference.push(output_data)

    st.sidebar.markdown("<h1 style='color: grey;'>BYUH Faculty of Math and Computing</h1>", unsafe_allow_html=True)
    st.subheader("AI Assistant: Ask Me Anything")

    if 'chat_display' not in st.session_state:
        st.session_state['chat_display'] = []

    for interaction in st.session_state['chat_display']:
        if interaction['role'] == 'user':
            st.markdown(f'<div style="border:2px solid coral; padding:10px; margin:5px; border-radius: 15px;">You: {interaction["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="border:2px solid LightBlue; padding:10px; margin:5px; border-radius: 15px;">AI: {interaction["content"]}</div>', unsafe_allow_html=True)

    res_box = st.empty()
    
    user_input = st.text_area("You", placeholder="Ask me a question here...", key="input")

    history = [{"role": "assistant", "content": "You help users with general questions and stuff."}]
    history.extend(st.session_state['chat_display'])
    history.append({"role": "user", "content": user_input})

    if user_input:
        st.markdown("_____")
        

        ref = db.reference('sessions')
        session_ref = ref.child(session_id)
        if not session_ref.get():
            session_ref.set({
            'start_time': session_start_time.strftime("%m/%d/%Y, %H:%M:%S"),
            'user_email:' : user_email,
            'outputs': []
        })

        st.session_state['chat_display'].append({"role": "user", "content": user_input})
        record_output('user', user_input)

        report = []

        stream = client.beta.threads.create_and_run(
            assistant_id = assistant_id,
            thread={
                "messages": history
            },
            stream = True
        )

        for event in stream:
            if event.data.object == "thread.message.delta":
                for content in event.data.delta.content:
                    if content.type == "text":

                        report.append(content.text.value)
                        result = "".join(report).strip()
                        res_box.markdown(f'<div style="border:2px solid lightgreen; padding:10px; margin:5px; border-radius: 15px;"><b>Current Output: </b>{result}</div>', unsafe_allow_html=True)

        st.session_state['chat_display'].append({"role": "assistant", "content": result})
        record_output('assistant', result)

if 'access_granted' not in st.session_state:
    st.session_state['access_granted'] = False

if st.session_state['access_granted'] == True:
    libraryBot_page()
else:
    entry_page()
