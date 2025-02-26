import streamlit as st

def calculate_final_recommendation(score):
    """Auto-calculate final recommendation based on weighted score."""
    if score >= 4.5:
        return "Strong Hire"
    elif score >= 3.5:
        return "Hire"
    elif score >= 2.5:
        return "Maybe"
    else:
        return "No Hire"

def main():
    st.title("Interview Feedback Form")
    st.markdown(
        """
        ### Please provide structured, behavior-based feedback for the candidate.
        Your ratings and examples help ensure objective, actionable insights.
        """
    )

    # Define the rubric dimensions with corresponding weights and descriptions.
    dimensions = {
        "Communication": {
            "weight": 0.2,
            "description": "Evaluate clarity, conciseness, and the ability to articulate ideas."
        },
        "Problem Solving": {
            "weight": 0.3,
            "description": "Assess analytical thinking, creativity, and approach to solving complex problems."
        },
        "Technical Skills": {
            "weight": 0.3,
            "description": "Rate technical expertise and the practical application of relevant skills."
        },
        "Cultural Fit": {
            "weight": 0.1,
            "description": "Consider alignment with company values, teamwork, and interpersonal skills."
        },
        "Adaptability": {
            "weight": 0.1,
            "description": "Evaluate the ability to adjust to new challenges and changes in the work environment."
        }
    }

    errors = []
    ratings = {}
    evidences = {}

    # Build the form with structured inputs.
    with st.form("feedback_form"):
        st.header("Candidate Evaluation")
        for dim, info in dimensions.items():
            st.subheader(f"{dim} (Weight: {int(info['weight'] * 100)}%)")
            st.write(info["description"])
            # Rating slider for the dimension.
            rating = st.slider(
                f"Rate {dim} (1 = Poor, 5 = Excellent)",
                min_value=1,
                max_value=5,
                key=f"{dim}_rating"
            )
            ratings[dim] = rating

            # Evidence text area with a placeholder prompting behavior-based examples.
            evidence = st.text_area(
                f"Provide specific evidence/examples for {dim}:",
                placeholder=(
                    "For example, 'Candidate explained project challenges by detailing how they prioritized tasks "
                    "and collaborated with team members.'"
                ),
                key=f"{dim}_evidence"
            )
            evidences[dim] = evidence

        st.markdown("---")
        # Calculate weighted score.
        weighted_score = sum(ratings[dim] * info["weight"] for dim, info in dimensions.items())
        auto_recommendation = calculate_final_recommendation(weighted_score)

        st.write("### Auto-calculated Score and Recommendation")
        st.write(f"**Weighted Score:** {weighted_score:.2f}")
        st.write(f"**Final Recommendation:** {auto_recommendation}")

        # Optional final comments.
        st.text_area(
            "Final Comments (Optional):",
            placeholder="Summarize overall impressions, key strengths, or any development areas...",
            key="final_comments"
        )

        submit_button = st.form_submit_button("Submit Feedback")

        # Intelligent validation: require evidence for each dimension.
        if submit_button:
            for dim, text in evidences.items():
                if not text.strip():
                    errors.append(f"Evidence/examples for **{dim}** are required.")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.success("Feedback submitted successfully!")
                st.markdown("### Feedback Summary")
                st.json({
                    "Ratings": ratings,
                    "Evidence": evidences,
                    "Weighted Score": f"{weighted_score:.2f}",
                    "Final Recommendation": auto_recommendation,
                    "Final Comments": st.session_state.get("final_comments", "")
                })

if __name__ == "__main__":
    main()
