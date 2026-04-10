import streamlit as st

st.title("📊 My Trading App")

if st.button("🔄 Refresh"):
    st.rerun()

    st.write("App is working ✅")