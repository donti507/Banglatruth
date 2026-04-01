import streamlit as st
from utils.language import detect_language, get_language_name
from utils.fact_check import analyse_claim

st.set_page_config(
    page_title="BanglaTruth",
    page_icon="🔍",
    layout="wide"
)

if "history" not in st.session_state:
    st.session_state.history = []

st.sidebar.title("BanglaTruth 🔍")
st.sidebar.divider()
page = st.sidebar.radio("Navigate", ["Check Claim", "Dashboard"])

if page == "Check Claim":

    st.title("BanglaTruth 🔍")
    st.caption("Bangladesh's AI-powered fact-checking platform | বাংলাদেশের তথ্য যাচাই প্ল্যাটফর্ম")
    st.divider()

    claim = st.text_area(
        label="Paste your claim here | এখানে দাবিটি লিখুন",
        placeholder="e.g. The government announced a 20% salary cut for all public servants...",
        height=150
    )

    st.divider()
    st.markdown("### ⚙️ Analysis Settings")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Model**")
        selected_model = st.selectbox(
            "Choose model",
            ["Both", "Llama 3.3", "Llama 3.1"],
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**Analysis Mode**")
        analysis_mode = st.radio(
            "Mode",
            ["Quick", "Deep"],
            horizontal=True,
            label_visibility="collapsed"
        )
        if analysis_mode == "Deep":
            st.caption("⚠️ Deep mode argues both sides before verdict. Slower but more accurate.")

    with col3:
        st.markdown("**Source Search Engine**")
        search_engine = st.radio(
            "Engine",
            ["DuckDuckGo", "Google"],
            horizontal=True,
            label_visibility="collapsed"
        )
        if search_engine == "Google":
            st.caption("✅ Google search — more accurate results")
        else:
            st.caption("🦆 DuckDuckGo — free, no limits")

    st.divider()

    if st.button("Check Claim →"):
        if claim.strip() == "":
            st.warning("Please enter a claim first.")
        else:
            lang_code = detect_language(claim)
            lang_name = get_language_name(lang_code)

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Language Detected", value=lang_name)
            with col2:
                st.metric(label="Language Code", value=lang_code)

            st.divider()

            deep = analysis_mode == "Deep"
            engine = search_engine.lower().replace(" ", "")
            model_choice = "both" if selected_model == "Both" else selected_model

            spinner_text = "Deep analysis in progress — arguing both sides..." if deep else "Analysing claim..."

            with st.spinner(spinner_text):
                result = analyse_claim(
                    claim,
                    lang_code,
                    deep=deep,
                    search_engine=engine,
                    selected_model=model_choice
                )

            final_verdict = result["final_verdict"]
            avg_confidence = result["avg_confidence"]
            individual = result["individual"]
            image_url = result.get("image_url")

            st.session_state.history.append({
                "claim": claim,
                "lang": lang_name,
                "verdict": final_verdict,
                "confidence": avg_confidence,
                "mode": analysis_mode,
                "engine": search_engine,
                "individual": individual
            })

            if final_verdict in ["TRUE", "সত্য"]:
                color = "green"
                icon = "✅"
            elif final_verdict in ["FALSE", "মিথ্যা"]:
                color = "red"
                icon = "❌"
            elif final_verdict in ["MISLEADING", "বিভ্রান্তিকর"]:
                color = "orange"
                icon = "⚠️"
            elif final_verdict == "CONTESTED":
                color = "orange"
                icon = "⚖️"
            else:
                color = "gray"
                icon = "❓"

            # related image
            if image_url:
                st.markdown("### 🖼️ Related Image")
                st.image(image_url, use_column_width=True)
                st.divider()

            st.markdown("## Final Verdict | চূড়ান্ত রায়")

            if color == "green":
                st.success(f"## {icon} {final_verdict}")
            elif color == "red":
                st.error(f"## {icon} {final_verdict}")
            elif color == "orange":
                st.warning(f"## {icon} {final_verdict}")
            else:
                st.info(f"## {icon} {final_verdict}")

            st.markdown("### 📊 Average Confidence | গড় আস্থা")
            st.progress(avg_confidence / 100)
            st.markdown(f"**{avg_confidence}%**")

            st.divider()

            st.markdown("## 🧑‍⚖️ Jury Results | জুরির রায়")

            cols = st.columns(len(individual))

            for i, model_result in enumerate(individual):
                with cols[i]:
                    st.markdown(f"### {model_result['model_name']}")

                    v = model_result["verdict"]
                    if v in ["TRUE", "সত্য"]:
                        st.success(f"**{v}**")
                    elif v in ["FALSE", "মিথ্যা"]:
                        st.error(f"**{v}**")
                    elif v in ["MISLEADING", "বিভ্রান্তিকর"]:
                        st.warning(f"**{v}**")
                    else:
                        st.info(f"**{v}**")

                    st.progress(int(model_result["confidence"]) / 100)
                    st.caption(f"Confidence: {model_result['confidence']}%")

                    if deep:
                        if model_result.get("for_arguments"):
                            st.markdown("**✅ Arguments For:**")
                            st.write(model_result["for_arguments"])
                        if model_result.get("against_arguments"):
                            st.markdown("**❌ Arguments Against:**")
                            st.write(model_result["against_arguments"])

                    st.markdown("**📋 Explanation:**")
                    st.write(model_result["explanation"])

                    st.markdown("**🔗 Source:**")
                    if not model_result["source"] or model_result["source"] == "null":
                        st.caption("⚠️ No specific source identified. Verdict based on model training knowledge.")
                    elif model_result.get("source_link"):
                        st.write(model_result["source"])
                        st.markdown(f"[🔗 View Source]({model_result['source_link']})")
                    else:
                        st.write(model_result["source"])
                        st.caption(f"⚠️ '{model_result['source']}' identified but no direct link found. Try searching manually.")

elif page == "Dashboard":

    st.title("📊 Dashboard")
    st.caption("All past fact-checks | সকল যাচাইকৃত দাবি")
    st.divider()

    if len(st.session_state.history) == 0:
        st.info("No claims checked yet. Go to Check Claim and analyse something first.")
    else:
        total = len(st.session_state.history)
        false_count = sum(1 for h in st.session_state.history if h["verdict"] in ["FALSE", "মিথ্যা"])
        true_count = sum(1 for h in st.session_state.history if h["verdict"] in ["TRUE", "সত্য"])
        misleading_count = sum(1 for h in st.session_state.history if h["verdict"] in ["MISLEADING", "বিভ্রান্তিকর"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Checked", total)
        with col2:
            st.metric("❌ False", false_count)
        with col3:
            st.metric("✅ True", true_count)
        with col4:
            st.metric("⚠️ Misleading", misleading_count)

        st.divider()

        filter_option = st.selectbox(
            "Filter by verdict",
            ["All", "TRUE", "FALSE", "MISLEADING", "UNVERIFIED", "CONTESTED"]
        )

        st.divider()

        filtered = st.session_state.history
        if filter_option != "All":
            filtered = [h for h in st.session_state.history if h["verdict"] == filter_option]

        for i, item in enumerate(reversed(filtered)):
            with st.expander(f"{item['verdict']} — {item['claim'][:80]}..."):
                st.markdown(f"**Language:** {item['lang']}")
                st.markdown(f"**Verdict:** {item['verdict']}")
                st.markdown(f"**Confidence:** {item['confidence']}%")
                st.markdown(f"**Mode:** {item.get('mode', 'Quick')}")
                st.markdown(f"**Search Engine:** {item.get('engine', 'DuckDuckGo')}")
                st.progress(item['confidence'] / 100)