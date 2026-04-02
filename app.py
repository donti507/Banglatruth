from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from utils.language import detect_language, get_language_name
from utils.fact_check import analyse_claim, search_image, find_similar_claim, extract_claim_from_url, get_evidence_map
from utils.source_credibility import check_source_credibility


st.set_page_config(
    page_title="BanglaTruth",
    page_icon="🔍",
    layout="wide"
)

if "history" not in st.session_state:
    st.session_state.history = []

if "confidence_log" not in st.session_state:
    st.session_state.confidence_log = {}

st.sidebar.title("BanglaTruth 🔍")
st.sidebar.divider()
page = st.sidebar.radio("Navigate", ["Check Claim", "Dashboard", "Trending"])

if page == "Check Claim":

    st.title("BanglaTruth 🔍")
    st.caption("Bangladesh's AI-powered fact-checking platform | বাংলাদেশের তথ্য যাচাই প্ল্যাটফর্ম")
    st.divider()

    input_type = st.radio(
        "Input type",
        ["Paste Claim", "Paste URL"],
        horizontal=True
    )

    if input_type == "Paste URL":
        url_input = st.text_input(
            "Paste a news article or social media URL",
            placeholder="https://www.prothomalo.com/..."
        )
        if st.button("Extract Claim from URL"):
            if url_input.strip() == "":
                st.warning("Please enter a URL first.")
            else:
                with st.spinner("Extracting claim from URL..."):
                    extracted = extract_claim_from_url(url_input)
                if extracted:
                    st.success("Claim extracted successfully.")
                    st.session_state.extracted_claim = extracted
                else:
                    st.error(
                        "Could not extract text from this URL. "
                        "This may be a paywalled site, Facebook post, or login-required page. "
                        "Try pasting the claim text directly instead."
                    )
        claim = st.text_area(
            "Extracted claim (you can edit this)",
            value=st.session_state.get("extracted_claim", ""),
            height=150
        )
    else:
        claim = st.text_area(
            label="Paste your claim here | এখানে দাবিটি লিখুন",
            placeholder="e.g. The government announced a 20% salary cut for all public servants...",
            height=150
        )

    st.divider()
    st.markdown("### ⚙️ Analysis Settings")

    col1, col2, col3, col4 = st.columns(4)

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
            st.caption("⚠️ Slower but more accurate.")

    with col3:
        st.markdown("**Reporter Mode**")
        reporter_mode = st.toggle("Reporter Mode 📰")
        if reporter_mode:
            st.caption("🔍 Journalist-level deep analysis.")

    with col4:
        st.markdown("**Source Search Engine**")
        search_engine = st.radio(
            "Engine",
            ["DuckDuckGo", "Google"],
            horizontal=True,
            label_visibility="collapsed"
        )

    st.divider()

    if st.button("Check Claim →"):
        if claim.strip() == "":
            st.warning("Please enter a claim first.")
        else:
            similar = find_similar_claim(claim, st.session_state.history)
            if similar:
                st.warning("⚠️ Similar claim was already checked.")
                with st.expander("See previous result"):
                    st.markdown(f"**Previous Claim:** {similar['claim']}")
                    st.markdown(f"**Verdict:** {similar['verdict']}")
                    st.markdown(f"**Confidence:** {similar['confidence']}%")
                    st.markdown(f"**Language:** {similar['lang']}")
                st.divider()
                if not st.session_state.get("force_recheck"):
                    if st.button("Re-check anyway →"):
                        st.session_state.force_recheck = True
                        st.rerun()
                    st.stop()

            st.session_state.force_recheck = False

            lang_code = detect_language(claim)
            lang_name = get_language_name(lang_code)

            deep = analysis_mode == "Deep"
            engine = search_engine.lower().replace(" ", "")
            model_choice = "both" if selected_model == "Both" else selected_model
            spinner_text = "Deep analysis in progress..." if deep else "Analysing claim..."

            with st.spinner(spinner_text):
                with ThreadPoolExecutor() as executor:
                    image_future = executor.submit(search_image, claim)
                    analysis_future = executor.submit(
                        analyse_claim,
                        claim, lang_code,
                        deep=deep,
                        search_engine=engine,
                        selected_model=model_choice,
                        reporter=reporter_mode
                    )
                    images = image_future.result()
                    result = analysis_future.result()

            if images:
                st.markdown("### 🖼️ Related Images")
                img_cols = st.columns(3)
                for idx, img in enumerate(images):
                    with img_cols[idx]:
                        st.image(img, width=200)
                st.divider()
            else:
                st.caption("🖼️ No relevant images found.")
                st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Language Detected", value=lang_name)
            with col2:
                st.metric(label="Language Code", value=lang_code)

            st.divider()

            final_verdict = result["final_verdict"]
            avg_confidence = result["avg_confidence"]
            individual = result["individual"]

            st.session_state.history.append({
                "claim": claim,
                "lang": lang_name,
                "verdict": final_verdict,
                "confidence": avg_confidence,
                "mode": analysis_mode,
                "engine": search_engine,
                "individual": individual
            })

            claim_key = claim[:50]
            if claim_key not in st.session_state.confidence_log:
                st.session_state.confidence_log[claim_key] = []
            st.session_state.confidence_log[claim_key].append(avg_confidence)

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

            log = st.session_state.confidence_log.get(claim_key, [])
            if len(log) > 1:
                st.divider()
                st.markdown("### 📈 Confidence Timeline")
                st.line_chart(log)
                st.caption(f"This claim has been checked {len(log)} times.")

            st.divider()
            st.markdown("## 🗺️ Evidence Map")

            with st.spinner("Building evidence map..."):
                evidence = get_evidence_map(claim, lang_code)

            if evidence:
                col_for, col_against, col_neutral = st.columns(3)

                with col_for:
                    st.markdown("### ✅ Supporting")
                    points = evidence.get("supporting", [])
                    if points:
                        for point in points:
                            st.success(point)
                    else:
                        st.caption("No supporting evidence found.")

                with col_against:
                    st.markdown("### ❌ Contradicting")
                    points = evidence.get("contradicting", [])
                    if points:
                        for point in points:
                            st.error(point)
                    else:
                        st.caption("No contradicting evidence found.")

                with col_neutral:
                    st.markdown("### 🔍 Context")
                    points = evidence.get("neutral", [])
                    if points:
                        for point in points:
                            st.info(point)
                    else:
                        st.caption("No context found.")

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

                    if reporter_mode:
                        if model_result.get("follow_up_questions"):
                            st.markdown("**🔍 Follow-up Questions:**")
                            for q in model_result["follow_up_questions"]:
                                st.markdown(f"- {q}")
                        if model_result.get("what_to_investigate"):
                            st.markdown("**🔎 What to Investigate:**")
                            st.write(model_result["what_to_investigate"])
                        if model_result.get("red_flags"):
                            st.markdown("**🚩 Red Flags:**")
                            st.write(model_result["red_flags"])

                    st.markdown("**🔗 Source:**")
                    if not model_result["source"] or model_result["source"] == "null":
                        st.caption("⚠️ No specific source identified. Verdict based on model training knowledge.")
                    elif model_result.get("source_link"):
                        st.write(model_result["source"])
                        st.markdown(f"[🔗 View Source]({model_result['source_link']})")
                    else:
                        st.write(model_result["source"])
                        st.caption(f"⚠️ '{model_result['source']}' identified but no direct link found.")

                    cred = check_source_credibility(model_result.get("source", ""))
                    if cred:
                        st.markdown("**📊 Source Credibility:**")
                        score = cred["score"]
                        cred_label = cred["label"]
                        st.progress(score / 100)
                        if cred_label == "Reliable":
                            st.success(f"**{cred_label}** — {cred['type']} | Bias: {cred['bias']} | Score: {score}/100")
                        elif cred_label == "Mixed":
                            st.warning(f"**{cred_label}** — {cred['type']} | Bias: {cred['bias']} | Score: {score}/100")
                        else:
                            st.error(f"**{cred_label}** — {cred['type']} | Bias: {cred['bias']} | Score: {score}/100")


elif page == "Dashboard":

    st.title("📊 Dashboard")
    st.caption("All past fact-checks | সকল যাচাইকৃত দাবি")
    st.divider()

    if len(st.session_state.history) == 0:
        st.info("No claims checked yet.")
    else:
        total = len(st.session_state.history)
        false_count = sum(1 for h in st.session_state.history if h["verdict"] in ["FALSE", "মিথ্যা"])
        true_count = sum(1 for h in st.session_state.history if h["verdict"] in ["TRUE", "সত্য"])
        misleading_count = sum(1 for h in st.session_state.history if h["verdict"] in ["MISLEADING", "বিভ্রান্তিকর"])
        unverified_count = sum(1 for h in st.session_state.history if h["verdict"] in ["UNVERIFIED", "অযাচাইকৃত"])

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Checked", total)
        with col2:
            st.metric("❌ False", false_count)
        with col3:
            st.metric("✅ True", true_count)
        with col4:
            st.metric("⚠️ Misleading", misleading_count)
        with col5:
            st.metric("❓ Unverified", unverified_count)

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
                st.markdown(f"**Engine:** {item.get('engine', 'DuckDuckGo')}")
                st.progress(item['confidence'] / 100)

elif page == "Trending":

    st.title("🔥 Trending")
    st.caption("Most checked claim types this session")
    st.divider()

    if len(st.session_state.history) == 0:
        st.info("No claims checked yet. Start checking claims to see trends.")
    else:
        verdict_counts = {}
        lang_counts = {}

        for item in st.session_state.history:
            v = item["verdict"]
            verdict_counts[v] = verdict_counts.get(v, 0) + 1
            l = item["lang"]
            lang_counts[l] = lang_counts.get(l, 0) + 1

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Verdicts Distribution")
            st.bar_chart(verdict_counts)

        with col2:
            st.markdown("### Languages Distribution")
            st.bar_chart(lang_counts)

        st.divider()
        st.markdown("### Confidence Timeline — All Claims")

        if st.session_state.confidence_log:
            for claim_key, log in st.session_state.confidence_log.items():
                if len(log) > 1:
                    st.markdown(f"**{claim_key}...**")
                    st.line_chart(log)