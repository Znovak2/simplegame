import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import random

# Title of the app
st.title("🗺️ Treasure Hunt on the Game Map")

# Load and display the map
map_img = Image.open("GameMapV1.png")
st.image(map_img, use_column_width=True, caption="Find the hidden treasure on this map!")

# Initialize game state
if "treasure_node" not in st.session_state:
    st.session_state.treasure_node = random.randint(1, 10)  # pick a random node 1–10
    st.session_state.tries = 0
    st.session_state.found = False

st.markdown("### Search for the treasure")
st.write("Pick a node number (1–10) and click **Search** to see if the treasure is there.")

node_choice = st.selectbox("Choose node", list(range(1, 11)), index=0)

if st.button("Search") and not st.session_state.found:
    st.session_state.tries += 1
    if node_choice == st.session_state.treasure_node:
        st.balloons()
        st.success(f"🎉 You found the treasure at node **{node_choice}** in **{st.session_state.tries}** tries!")
        st.session_state.found = True
    else:
        st.warning(f"No treasure at node **{node_choice}**. Try again! ({st.session_state.tries} tries so far)")

if st.session_state.found:
    if st.button("Play Again"):
        st.session_state.treasure_node = random.randint(1, 10)
        st.session_state.tries = 0
        st.session_state.found = False