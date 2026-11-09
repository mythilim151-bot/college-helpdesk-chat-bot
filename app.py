# =============================================================================
# COLLEGE HELPDESK CHATBOT (Google Colab / Standalone Python)
# Continuous Assessment 3 (CA3) Implementation
# =============================================================================
import base64
import re

import streamlit as st


class CollegeHelpdeskChatbot:
    def __init__(self):
        self.state = {
            "last_intent": None,
            "awaiting_slot": None,
            "slots": {"course": None, "semester": None, "department": None,
                      "date": None, "query_type": None},
        }

        # ---------- Knowledge base: courses ----------
        self.kb_courses = {
            "cse": {"name": "B.Tech CSE", "duration": "4 Years", "fees_per_year": "₹1,25,000",
                    "eligibility": "10+2 PCM (60%)", "seats": 180},
            "ece": {"name": "B.Tech ECE", "duration": "4 Years", "fees_per_year": "₹1,15,000",
                    "eligibility": "10+2 PCM (60%)", "seats": 120},
            "me":  {"name": "B.Tech ME", "duration": "4 Years", "fees_per_year": "₹95,000",
                    "eligibility": "10+2 PCM (55%)", "seats": 60},
            "bca": {"name": "BCA", "duration": "3 Years", "fees_per_year": "₹75,000",
                    "eligibility": "10+2 Math/CS (50%)", "seats": 90},
            "mba": {"name": "MBA", "duration": "2 Years", "fees_per_year": "₹1,40,000",
                    "eligibility": "Graduation + CAT/MAT", "seats": 120},
        }

        # ---------- Knowledge base: timetables ----------
        self.kb_timetables = {
            "cse": "CSE Schedule: Classes run Mon-Fri, 9:00 AM - 4:30 PM. Lab sessions on Wed & Fri afternoon.",
            "ece": "ECE Schedule: Classes run Mon-Fri, 9:00 AM - 4:15 PM. Hardware Labs on Tue & Thu morning.",
            "me":  "ME Schedule: Classes run Mon-Fri, 8:30 AM - 4:00 PM. Workshop practice on Mon & Wed.",
            "bca": "BCA Schedule: Classes run Mon-Fri, 9:30 AM - 3:30 PM. Programming practicals daily 2:00 PM.",
            "mba": "MBA Schedule: Classes run Mon-Sat, 9:00 AM - 5:00 PM. Case study seminars on alternate Sat.",
        }

    # ------------------------------------------------------------------
    def reset_context(self):
        self.state = {
            "last_intent": None,
            "awaiting_slot": None,
            "slots": {k: None for k in self.state["slots"]},
        }

    # ------------------------------------------------------------------
    def extract_entities(self, text):
        entities = {}
        t = text.lower()

        # Remove phrases where "me" is a pronoun, not "Mechanical"
        t_clean = re.sub(r"\b(tell|show|give|help|let|send)\s+me\b", " ", t)

        # Course / Department
        patterns = [
            ("cse", r"\b(cse|computer science|comp sci)\b"),
            ("ece", r"\b(ece|electronics)\b"),
            ("me",  r"\b(me|mech|mechanical)\b"),
            ("bca", r"\b(bca)\b"),
            ("mba", r"\b(mba|management)\b"),
        ]
        for code, pat in patterns:
            if re.search(pat, t_clean):
                entities["course"] = code
                entities["department"] = code.upper()
                break

        # Semester  ("sem 5", "semester 5", "5th sem")
        sem = re.search(r"(?:sem|semester)\s*([1-8])|\b([1-8])(?:st|nd|rd|th)?\s*sem", t)
        if sem:
            entities["semester"] = sem.group(1) or sem.group(2)

        # Query type
        if any(w in t for w in ["how to apply", "how can i apply", "procedure", "process", "steps"]):
            entities["query_type"] = "procedure"
        elif any(w in t for w in ["fee", "cost", "how much", "tuition", "scholarship", "salary", "package"]):
            entities["query_type"] = "financial"
        elif any(w in t for w in ["rule", "timing", "borrow", "guideline"]):
            entities["query_type"] = "guideline"

        return entities

    # ------------------------------------------------------------------
    def identify_intent(self, text):
        t = text.lower()

        if re.search(r"\b(bye|goodbye|exit|quit|thanks|thank you)\b", t):
            return "GOODBYE"
        if self.state["awaiting_slot"]:
            return "CONTEXT_REPLY"
        if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", t):
            return "GREETING"
        if any(k in t for k in ["placement", "package", "recruiter", "job", "salary"]):
            return "PLACEMENT"
        if any(k in t for k in ["fee", "fees", "tuition", "cost"]):
            return "FEES"
        if any(k in t for k in ["timetable", "schedule", "routine", "class timing"]):
            return "TIMETABLE"
        if any(k in t for k in ["exam", "examination", "hall ticket", "admit card"]):
            return "EXAM"
        if any(k in t for k in ["library", "books", "borrow", "reading room"]):
            return "LIBRARY"
        if any(k in t for k in ["admission", "apply", "eligibility"]):
            return "ADMISSION"
        if any(k in t for k in ["course", "courses", "branch", "degree", "program"]):
            return "COURSE"
        return "UNKNOWN"

    # ------------------------------------------------------------------
    def respond(self, text):
        text = text.strip()
        entities = self.extract_entities(text)
        for k, v in entities.items():
            if v:
                self.state["slots"][k] = v

        intent = self.identify_intent(text)
        # If we were waiting for an answer but the user asked something else, drop the
        # pending question instead of getting stuck asking for it again.
        if intent == "CONTEXT_REPLY" and not entities.get("course"):
            pending = self.state["awaiting_slot"]
            self.state["awaiting_slot"] = None
            other = self.identify_intent(text)
            if other == "UNKNOWN":
                self.state["awaiting_slot"] = pending
            else:
                intent = other

        self.state["last_intent"] = intent

        # ----- Multi-turn: waiting for a missing slot -----
        if intent == "CONTEXT_REPLY":
            awaiting = self.state["awaiting_slot"]

            if awaiting == "tt_department":
                dept = entities.get("department")
                if dept:
                    self.state["awaiting_slot"] = None
                    return f"📅 Timetable for {dept}:\n{self.kb_timetables[dept.lower()]}"
                return "Please enter CSE, ECE, ME, BCA, or MBA:"

            if awaiting == "fee_course":
                crs = entities.get("course")
                if crs:
                    self.state["awaiting_slot"] = None
                    c = self.kb_courses[crs]
                    return (f"💰 Fees for {c['name']}:\n• Annual: {c['fees_per_year']}"
                            f"\n• Installments: 2 per year\n• Merit Scholarship available.")
                return "Please specify CSE, ECE, ME, BCA, or MBA:"

        # ----- Single-turn intents -----
        if intent == "GREETING":
            return ("👋 Hello! College Helpdesk at your service. Ask about Admissions, "
                    "Courses, Fees, Exams, Timetables, Library, and Placements!")

        if intent == "GOODBYE":
            self.reset_context()
            return "🎓 Thank you for visiting the Helpdesk. Have a great day!"

        if intent == "TIMETABLE":
            dept = entities.get("department")
            if not dept:
                self.state["awaiting_slot"] = "tt_department"
                return "For which department do you need the timetable? (CSE, ECE, ME, BCA, MBA)"
            return f"📅 Timetable for {dept}:\n{self.kb_timetables[dept.lower()]}"

        if intent == "FEES":
            crs = entities.get("course")
            if not crs:
                self.state["awaiting_slot"] = "fee_course"
                return "Which course's fee structure would you like to know? (CSE, ECE, ME, BCA, MBA)"
            c = self.kb_courses[crs]
            return (f"💰 Fees for {c['name']}:\n• Tuition: {c['fees_per_year']}"
                    f"\n• Exam: ₹2,000/sem\n• Hostel: ₹65,000/yr")

        if intent == "ADMISSION":
            crs = entities.get("course")
            if crs:
                c = self.kb_courses[crs]
                return (f"📝 Admission for {c['name']}:\n• Eligibility: {c['eligibility']}"
                        f"\n• Seats: {c['seats']}\n• Apply at admissions.college.edu")
            return ("📝 Admissions 2026-27 are open! Phase 1 closes June 30. "
                    "Mention a branch (e.g., 'Admission for ME') for details.")

        if intent == "COURSE":
            crs = entities.get("course")
            if crs:
                c = self.kb_courses[crs]
                return (f"🎓 {c['name']}:\n• Duration: {c['duration']}"
                        f"\n• Fee: {c['fees_per_year']}\n• Eligibility: {c['eligibility']}")
            return "🎓 Programs: B.Tech (CSE, ECE, ME), BCA, MBA. Mention a program for details."

        if intent == "EXAM":
            sem = entities.get("semester") or self.state["slots"].get("semester") or "Upcoming"
            return (f"📝 Exam Notice ({sem} Sem):\n• Mid-terms: Oct 15, 2026"
                    f"\n• End-sem practicals: Nov 20, 2026"
                    f"\n• Hall tickets: 7 days prior (Min 75% attendance required).")

        if intent == "LIBRARY":
            return ("📚 Library Info:\n• Timings: Mon-Sat 8 AM - 8 PM\n• Quota: 4 books for 14 days"
                    "\n• Overdue fine: ₹5/day\n• Digital portal active.")

        if intent == "PLACEMENT":
            return ("🚀 Placement Cell (2025-26):\n• Placement: 92%\n• Highest: ₹44.5 LPA"
                    "\n• Avg: ₹7.2 LPA\n• Top Recruiters: TCS, Infosys, Amazon, Cisco, Wipro.")

        return ("I didn't quite catch that. Please ask about Admissions, Courses, Fees, "
                "Exams, Timetables, Library, or Placements.")


# =============================================================================
#                              STREAMLIT UI
# =============================================================================
st.set_page_config(page_title="College Helpdesk", page_icon="🎓", layout="wide")

WELCOME = ("👋 Hello! College Helpdesk at your service. Ask about Admissions, "
           "Courses, Fees, Exams, Timetables, Library, and Placements!")

SAMPLE_PROMPTS = [
    "Tell me about CSE course",
    "What are the fees?",
    "Show me the timetable",
    "Admission for MBA",
    "Exam notice for sem 5",
    "Library rules",
    "Placement details",
    "Hello",
]

PAGES = ["🏠 Home", "💬 Chat", "⚡ Quick Services", "🔬 NLP Playground"]
DEPTS = ["cse", "ece", "me", "bca", "mba"]


# ---------- Images: SVGs generated in code, so no image files are needed ----------
def svg_img(svg, radius=14):
    b64 = base64.b64encode(svg.encode("utf-8")).decode()
    return (f'<img src="data:image/svg+xml;base64,{b64}" '
            f'style="width:100%;border-radius:{radius}px;" />')


def hero_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 230">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#4a148c"/><stop offset="1" stop-color="#2196f3"/></linearGradient></defs>
<rect width="900" height="230" fill="url(#g)"/>
<g fill="#ffffff" opacity="0.92" transform="translate(630,40)">
<polygon points="120,0 240,50 120,100 0,50"/>
<path d="M50 78 L50 125 Q120 160 190 125 L190 78 L120 108 Z"/>
<rect x="222" y="55" width="6" height="70"/><circle cx="225" cy="132" r="9"/></g>
<text x="50" y="105" font-family="sans-serif" font-size="46" font-weight="bold" fill="#fff">College Helpdesk</text>
<text x="50" y="145" font-family="sans-serif" font-size="20" fill="#ede7f6">Admissions, fees, exams, timetables, library and placements</text>
<rect x="50" y="165" width="370" height="34" rx="17" fill="#ffffff" opacity="0.2"/>
<text x="68" y="188" font-family="sans-serif" font-size="16" fill="#fff">Rule-based NLP  |  Slot-filling dialog</text>
</svg>"""


def feature_svg(emoji, title, sub, c1, c2):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 170">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<rect width="300" height="170" fill="url(#g)"/>
<circle cx="250" cy="40" r="70" fill="#fff" opacity="0.12"/>
<text x="24" y="85" font-size="52">{emoji}</text>
<text x="24" y="124" font-family="sans-serif" font-size="22" font-weight="bold" fill="#fff">{title}</text>
<text x="24" y="148" font-family="sans-serif" font-size="13" fill="#fff" opacity="0.9">{sub}</text>
</svg>"""


def flow_svg():
    boxes = [
        (20, "1  You type", "any college question", "#e3f2fd", "#1565c0"),
        (330, "2  NLP analysis", "intent + entities + slots", "#fff3e0", "#e65100"),
        (640, "3  Smart reply", "answer or follow-up", "#e8f5e9", "#2e7d32"),
    ]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200">',
             '<rect width="900" height="200" fill="#f7f9fc"/>']
    for x, t, s, bg, fg in boxes:
        parts.append(f'<rect x="{x}" y="40" width="240" height="120" rx="16" fill="{bg}" stroke="{fg}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 20}" y="90" font-family="sans-serif" font-size="24" font-weight="bold" fill="{fg}">{t}</text>')
        parts.append(f'<text x="{x + 20}" y="124" font-family="sans-serif" font-size="16" fill="#444">{s}</text>')
    for x in (268, 578):
        parts.append(f'<polygon points="{x},85 {x + 40},100 {x},115" fill="#90a4ae"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------- Session state ----------
def reset_chat():
    if "bot" not in st.session_state:
        st.session_state.bot = CollegeHelpdeskChatbot()
    st.session_state.bot.reset_context()
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
    st.session_state.last_analysis = None


def init_session():
    if "bot" not in st.session_state or "messages" not in st.session_state:
        st.session_state.bot = CollegeHelpdeskChatbot()
        reset_chat()


def money(text):
    """'₹1,25,000' -> 125000"""
    return int(re.sub(r"\D", "", text))


def send_message(user_text):
    bot = st.session_state.bot
    entities = bot.extract_entities(user_text)      # read-only analysis
    reply = bot.respond(user_text)                  # updates the dialog state
    name = st.session_state.get("user_name", "").strip()
    if name and bot.state["last_intent"] == "GREETING":
        reply = reply.replace("Hello!", f"Hello {name}!", 1)
    analysis = {"intent": bot.state["last_intent"], "entities": entities,
                "slots": {k: v for k, v in bot.state["slots"].items() if v},
                "awaiting": bot.state["awaiting_slot"]}
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.messages.append({"role": "assistant", "content": reply, "meta": analysis})
    st.session_state.last_analysis = analysis


def show_analysis(a):
    c1, c2, c3 = st.columns(3)
    c1.metric("Intent", a["intent"])
    c2.metric("Entities found", len(a["entities"]))
    c3.metric("Waiting for", a.get("awaiting") or "nothing")
    if a["entities"]:
        st.markdown("**Entities in this message**")
        st.json(a["entities"])
    else:
        st.caption("No entities found in this message.")
    if a.get("slots"):
        st.markdown("**Remembered slots (conversation memory)**")
        st.json(a["slots"])


# ---------- Pages ----------
def page_home():
    bot = st.session_state.bot
    st.markdown(svg_img(hero_svg(), 18), unsafe_allow_html=True)
    st.write("")
    n_user = sum(1 for m in st.session_state.messages if m["role"] == "user")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Programs offered", len(bot.kb_courses))
    m2.metric("Total seats", sum(c["seats"] for c in bot.kb_courses.values()))
    m3.metric("Placement rate", "92%")
    m4.metric("Messages you sent", n_user)

    st.subheader("What can this helpdesk do?")
    cards = [
        ("📝", "Admissions", "Eligibility, seats, how to apply", "#4a148c", "#8e24aa"),
        ("🎓", "Courses", "B.Tech, BCA, MBA details", "#0d47a1", "#42a5f5"),
        ("💰", "Fees", "Tuition, exam and hostel fees", "#1b5e20", "#66bb6a"),
        ("🗓️", "Exams", "Dates, hall tickets, attendance", "#b71c1c", "#ef5350"),
        ("📅", "Timetable", "Department-wise schedules", "#e65100", "#ffa726"),
        ("📚", "Library", "Timings, quota, fines", "#004d40", "#26a69a"),
        ("🚀", "Placements", "Packages and recruiters", "#311b92", "#7e57c2"),
    ]
    for row in (cards[:4], cards[4:]):
        cols = st.columns(4)
        for col, (e, t, s, c1, c2) in zip(cols, row):
            col.markdown(svg_img(feature_svg(e, t, s, c1, c2)), unsafe_allow_html=True)
        st.write("")

    st.subheader("How it works")
    st.markdown(svg_img(flow_svg()), unsafe_allow_html=True)
    st.info("Use the sidebar to open the **Chat**, try the **Quick Services** input boxes "
            "(fee calculator, eligibility checker), or explore the **NLP Playground**.")


def page_chat():
    st.subheader("💬 Chat with the helpdesk")

    cols = st.columns(4)
    for i, p in enumerate(SAMPLE_PROMPTS):
        if cols[i % 4].button(p, key=f"sample_{i}", use_container_width=True):
            st.session_state.queued = p

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"].replace("\n", "  \n"))
            if m.get("meta"):
                with st.expander("🔍 NLP analysis of the previous message"):
                    show_analysis(m["meta"])

    awaiting = st.session_state.bot.state["awaiting_slot"]
    if awaiting:
        st.info(f"The bot is waiting for your answer: **{awaiting}** "
                "(or just ask about something else).")

    user_input = st.chat_input("Ask about admissions, fees, exams, timetable...")
    if "queued" in st.session_state:
        user_input = st.session_state.pop("queued")
    if user_input:
        send_message(user_input)
        st.rerun()


def tab_course_explorer(bot):
    code = st.selectbox("Choose a program", DEPTS, format_func=lambda c: bot.kb_courses[c]["name"],
                        key="explore_course")
    c = bot.kb_courses[code]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Duration", c["duration"])
    k2.metric("Fees / year", c["fees_per_year"])
    k3.metric("Seats", c["seats"])
    k4.metric("Eligibility", c["eligibility"])
    st.success(bot.kb_timetables[code])


def tab_fee_calculator(bot):
    c1, c2 = st.columns(2)
    code = c1.selectbox("Program", DEPTS, format_func=lambda c: bot.kb_courses[c]["name"], key="fee_course_pick")
    hostel = c2.checkbox("I need the hostel (Rs 65,000 / year)", value=False)
    course = bot.kb_courses[code]
    default_years = int(course["duration"].split()[0])
    years = st.slider("Years to calculate", 1, default_years, default_years)

    tuition = money(course["fees_per_year"]) * years
    exam = 2000 * 2 * years          # Rs 2,000 per semester, 2 semesters per year
    hostel_fee = 65000 * years if hostel else 0
    total = tuition + exam + hostel_fee

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tuition", f"Rs {tuition:,}")
    k2.metric("Exam fees", f"Rs {exam:,}")
    k3.metric("Hostel", f"Rs {hostel_fee:,}")
    k4.metric("Total", f"Rs {total:,}")

    import pandas as pd
    st.bar_chart(pd.DataFrame({"Rs": [tuition, exam, hostel_fee]},
                              index=["Tuition", "Exam", "Hostel"]))
    st.caption("Based on the helpdesk's sample fee data. Installments: 2 per year. Merit scholarship available.")


def tab_eligibility(bot):
    code = st.selectbox("Program you want", DEPTS, format_func=lambda c: bot.kb_courses[c]["name"],
                        key="elig_course")
    c = bot.kb_courses[code]
    st.write(f"**Requirement:** {c['eligibility']}")
    if code == "mba":
        grad = st.checkbox("I have completed graduation")
        score = st.checkbox("I have a valid CAT / MAT score")
        if st.button("Check eligibility", key="elig_btn_mba"):
            if grad and score:
                st.success("You meet the eligibility criteria for MBA.")
            else:
                st.error("MBA needs graduation plus a valid CAT/MAT score.")
    else:
        need = int(re.search(r"\((\d+)%\)", c["eligibility"]).group(1))
        pct = st.number_input("Your 10+2 percentage", min_value=0.0, max_value=100.0, value=60.0, step=0.5)
        if st.button("Check eligibility", key="elig_btn"):
            if pct >= need:
                st.success(f"Eligible. You meet the {need}% requirement. Apply at admissions.college.edu")
            else:
                st.error(f"Not eligible yet. {need}% is required, you entered {pct}%.")


def tab_placements():
    k1, k2, k3 = st.columns(3)
    k1.metric("Placement rate", "92%")
    k2.metric("Highest package", "Rs 44.5 LPA")
    k3.metric("Average package", "Rs 7.2 LPA")
    st.write("**Top recruiters:** TCS, Infosys, Amazon, Cisco, Wipro")
    import pandas as pd
    st.bar_chart(pd.DataFrame({"LPA": [7.2, 44.5]}, index=["Average", "Highest"]))


def tab_library():
    k1, k2, k3 = st.columns(3)
    k1.metric("Timings", "8 AM - 8 PM")
    k2.metric("Book quota", "4 books / 14 days")
    k3.metric("Overdue fine", "Rs 5 / day")
    st.caption("Open Mon-Sat. Digital portal is active.")


def page_quick():
    bot = st.session_state.bot
    st.subheader("⚡ Quick Services")
    st.caption("Use the input boxes instead of typing. All data is sample data.")
    tabs = st.tabs(["🎓 Course Explorer", "💰 Fee Calculator", "✅ Eligibility Checker",
                    "🚀 Placements", "📚 Library"])
    with tabs[0]:
        tab_course_explorer(bot)
    with tabs[1]:
        tab_fee_calculator(bot)
    with tabs[2]:
        tab_eligibility(bot)
    with tabs[3]:
        tab_placements()
    with tabs[4]:
        tab_library()


def page_playground():
    st.subheader("🔬 NLP Playground")
    st.caption("Type any sentence and see the entities and intent the bot would detect, live "
               "(this does not change the chat memory).")
    text = st.text_input("Your sentence", value="what is the fee for 5th sem mechanical", key="playground_text")
    if text.strip():
        probe = CollegeHelpdeskChatbot()    # fresh bot so the chat state is untouched
        entities = probe.extract_entities(text)
        intent = probe.identify_intent(text)
        show_analysis({"intent": intent, "entities": entities, "slots": {}, "awaiting": None})


# ---------- Sidebar + routing ----------
init_session()

with st.sidebar:
    st.title("🎓 College Helpdesk")
    page = st.radio("Go to", PAGES, key="page")
    st.text_input("Your name (optional)", key="user_name", placeholder="e.g. Pallavi")
    st.divider()
    if st.button("🔄 Reset conversation", use_container_width=True):
        reset_chat()
        st.rerun()
    la = st.session_state.last_analysis
    if la:
        st.markdown("**Last message analysis**")
        st.write(f"Intent: `{la['intent']}`")
        st.write(f"Entities: `{la['entities'] or 'none'}`")
    st.caption("Sample data only.")

if page == PAGES[0]:
    page_home()
elif page == PAGES[1]:
    page_chat()
elif page == PAGES[2]:
    page_quick()
else:
    page_playground()
