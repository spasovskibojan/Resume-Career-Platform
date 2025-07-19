import streamlit as st
import PyPDF2
import io
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Resume & Career Platform",
    page_icon="✨",
    layout="centered"
)

if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'coach_data' not in st.session_state:
    st.session_state.coach_data = None


def configure_api():
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("API Key (GOOGLE_API_KEY) not found. Please set it in your .env file.")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception:
        st.error("Error configuring the API.")
        return False


def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception:
            st.error("Error reading the PDF file.")
            return None
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    return None


def get_resume_analyzer_prompt(resume_text, job_description_text):
    return f"""
    You are an advanced AI recruitment assistant. Analyze the provided resume against the job description and return a JSON object.
    Your response MUST be a valid JSON object without any markdown formatting.

    The JSON structure must be:
    {{
        "match_score": <Number 0-100>,
        "analysis_summary": "<One-paragraph summary of the candidate's suitability>",
        "keywords": {{"job_keywords": [], "resume_keywords": [], "missing_keywords": []}},
        "strengths": ["<List of strengths>"],
        "areas_for_improvement": ["<List of weaknesses>"],
        "actionable_recommendations": [{{"area": "<Area>", "suggestion": "<Suggestion>"}}],
        "interview_prep": {{
            "technical_questions": ["<5 relevant technical interview questions based on the job description>"],
            "behavioral_questions": ["<5 behavioral questions based on the candidate's experience and the role's demands>"]
        }}
    }}

    **Resume Content:** --- {resume_text} ---
    **Job Description:** --- {job_description_text} ---
    """


def get_career_coach_prompt(resume_text):
    return f"""
    You are an expert AI career coach. Analyze the provided resume and suggest potential career paths.
    Your response MUST be a valid JSON object without any markdown formatting.

    The JSON structure must be:
    {{
      "candidate_profile": {{
        "summary": "<A summary of the candidate's core profile and experience level>",
        "top_skills": ["<A list of the candidate's most marketable skills>"]
      }},
      "suggested_career_paths": [
        {{
          "title": "<Suggested Job Title 1>",
          "suitability_reason": "<Why this role is a good fit>",
          "skills_to_develop": ["<Skill A>", "<Skill B>"],
          "next_steps": "<Concrete next steps, e.g., 'Take an online course in...', 'Build a project using...'>"
        }},
        {{
          "title": "<Suggested Job Title 2>",
          "suitability_reason": "<Why this role is a good fit>",
          "skills_to_develop": ["<Skill A>", "<Skill B>"],
          "next_steps": "<Concrete next steps>"
        }},
        {{
          "title": "<Suggested Job Title 3>",
          "suitability_reason": "<Why this role is a good fit>",
          "skills_to_develop": ["<Skill A>", "<Skill B>"],
          "next_steps": "<Concrete next steps>"
        }}
      ]
    }}

    **Resume Content:** --- {resume_text} ---
    """


st.title("✨ AI Resume & Career Platform")

mode = st.radio(
    "Select Mode:",
    ('Resume Analyzer', 'AI Career Coach'),
    horizontal=True
)

if configure_api():
    if mode == 'Resume Analyzer':
        if st.session_state.analysis_data is None:
            st.markdown("Upload a resume and a job description for a detailed comparative analysis.")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📄 Your Resume")
                uploaded_file = st.file_uploader("CV", type=["pdf", "txt"], label_visibility="collapsed")
            with col2:
                st.subheader("🎯 Job Description")
                job_description = st.text_area("Job Ad", height=210, label_visibility="collapsed")

            st.divider()
            analyze_button = st.button("Analyze Resume & Job Ad", type="primary", use_container_width=True)

            if analyze_button and uploaded_file and job_description.strip():
                with st.spinner('Performing comparative analysis...'):
                    resume_text = extract_text_from_file(uploaded_file)
                    if resume_text:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = get_resume_analyzer_prompt(resume_text, job_description)
                        response = model.generate_content(prompt)
                        try:
                            clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                            st.session_state.analysis_data = json.loads(clean_text)
                            st.rerun()
                        except (json.JSONDecodeError, AttributeError):
                            st.error("Error parsing the AI response. Please check the raw output.")
                            st.text_area("Raw AI Response:", value=response.text, height=300)
        else:
            analysis_data = st.session_state.analysis_data
            st.header("📊 Analysis Results")
            if st.button("⬅️ Start New Analysis"):
                st.session_state.analysis_data = None
                st.rerun()

            tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Keywords", "Recommendations", "Interview Prep"])

            with tab1:
                st.metric(label="Match Score", value=f"{analysis_data.get('match_score', 0)}%")
                st.progress(analysis_data.get('match_score', 0))
                st.info(analysis_data.get('analysis_summary', ''))
            with tab2:
                keywords = analysis_data.get('keywords', {})
                st.success(f"**Found:** {', '.join(keywords.get('resume_keywords', []))}")
                st.warning(f"**Missing:** {', '.join(keywords.get('missing_keywords', []))}")
            with tab3:
                st.markdown("##### Strengths:")
                for strength in analysis_data.get('strengths', []): st.write(f"- {strength}")
                st.markdown("##### Areas for Improvement:")
                for area in analysis_data.get('areas_for_improvement', []): st.write(f"- {area}")
            with tab4:
                st.subheader("Technical Questions")
                for i, q in enumerate(analysis_data.get('interview_prep', {}).get('technical_questions', [])):
                    st.write(f"{i + 1}. {q}")
                st.subheader("Behavioral Questions")
                for i, q in enumerate(analysis_data.get('interview_prep', {}).get('behavioral_questions', [])):
                    st.write(f"{i + 1}. {q}")

    elif mode == 'AI Career Coach':
        if st.session_state.coach_data is None:
            st.markdown("Upload your resume to get suggestions for your future career path.")
            uploaded_file = st.file_uploader("Your Resume", type=["pdf", "txt"], label_visibility="collapsed")

            st.divider()
            analyze_button = st.button("Get Career Advice", type="primary", use_container_width=True)

            if analyze_button and uploaded_file:
                with st.spinner('AI is analyzing your skills and experience...'):
                    resume_text = extract_text_from_file(uploaded_file)
                    if resume_text:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = get_career_coach_prompt(resume_text)
                        response = model.generate_content(prompt)
                        try:
                            clean_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                            st.session_state.coach_data = json.loads(clean_text)
                            st.rerun()
                        except (json.JSONDecodeError, AttributeError):
                            st.error("Error parsing the AI response. Please check the raw output.")
                            st.text_area("Raw AI Response:", value=response.text, height=300)
        else:
            analysis_data = st.session_state.coach_data
            st.header("💡 Career Suggestions")
            if st.button("⬅️ Start New Career Analysis"):
                st.session_state.coach_data = None
                st.rerun()

            profile = analysis_data.get('candidate_profile', {})
            st.info(f"**Profile Summary:** {profile.get('summary', '')}")
            st.success(f"**Top Skills:** {', '.join(profile.get('top_skills', []))}")

            st.divider()

            paths = analysis_data.get('suggested_career_paths', [])
            for path in paths:
                with st.expander(f"**Suggestion: {path.get('title')}**"):
                    st.markdown(f"**Why it's a good fit:** {path.get('suitability_reason')}")
                    st.warning(f"**Skills to Develop:** {', '.join(path.get('skills_to_develop', []))}")
                    st.success(f"**Next Steps:** {path.get('next_steps')}")