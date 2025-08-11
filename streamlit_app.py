import streamlit as st
import random
from dataclasses import dataclass
from typing import Dict, List, Optional
import base64
import html
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
try:
    from streamlit_image_coordinates import streamlit_image_coordinates
except Exception:
    streamlit_image_coordinates = None
import numpy as np

# Configure page
st.set_page_config(
    page_title="⚔️ Conquest of the Realm",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@dataclass
class Territory:
    id: str
    name: str
    x: int  # X coordinate on map
    y: int  # Y coordinate on map
    radius: int  # Territory radius
    owner: int  # 0=neutral, 1=player1, 2=player2
    units: int
    is_hq: bool = False

@dataclass
class Player:
    name: str
    nobles: int
    color: str
    hq_territory: str

class GameState:
    def __init__(self):
        self.current_player = 1
        self.phase = 'setup'  # setup, movement, reinforcement
        self.selected_territory = None
        self.turn_count = 1
        self.game_log = []
        
        # Initialize players
        self.players = {
            1: Player("Red Kingdom", 10, "#FF6B6B", "hq1"),
            2: Player("Blue Kingdom", 10, "#4ECDC4", "hq2")
        }
        # Initialize territories based on your map image
        self.territories = {
            "hq1": Territory("hq1", "Red HQ", 60, 300, 30, 1, 30, True),
            "hq2": Territory("hq2", "Blue HQ", 740, 100, 30, 2, 30, True),
            "t1": Territory("t1", "Northern Village", 250, 180, 25, 0, 2),
            "t2": Territory("t2", "Central Plains", 380, 220, 25, 0, 2),
            "t3": Territory("t3", "Eastern Outpost", 520, 280, 25, 0, 3),
            "t4": Territory("t4", "Mountain Pass", 400, 150, 25, 0, 2),
            "t5": Territory("t5", "River Crossing", 280, 320, 25, 0, 2),
            "t6": Territory("t6", "Forest Grove", 500, 400, 25, 0, 1),
            "t7": Territory("t7", "Hill Fort", 600, 200, 25, 0, 2),
        }
        # Territory adjacency
        self.adjacency = {
            "hq1": ["t1", "t5"],
            "hq2": ["t7", "t4"],
            "t1": ["hq1", "t2", "t4"],
            "t2": ["t1", "t3", "t5"],
            "t3": ["t2", "t6", "t7"],
            "t4": ["hq2", "t1", "t7"],
            "t5": ["hq1", "t2", "t6"],
            "t6": ["t3", "t5"],
            "t7": ["hq2", "t3", "t4"],
        }
    
    def add_log(self, message: str):
        """Add message to game log"""
        self.game_log.append(message)

def init_game_state():
    """Initialize game state in session state"""
    if 'game' not in st.session_state:
        st.session_state.game = GameState()
        st.session_state.game.add_log("🏰 Welcome to Conquest of the Realm!")
    # Movement and attack toggles (persist across reruns)
    if 'show_move' not in st.session_state:
        st.session_state.show_move = False
    if 'show_attack' not in st.session_state:
        st.session_state.show_attack = False

def inject_theme_css():
        """Inject global CSS to improve look & feel."""
        st.markdown(
                """
                <style>
                :root {
                    --friendly: #FF6B6B;
                    --enemy: #4ECDC4;
                    --neutral: #FFD700;
                    --ink: #222222;
                    --panel: rgba(255,255,255,0.04);
                    --accent: #F7B267;
                }
                /* Make headers tighter and bolder */
                .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { letter-spacing: .3px; }
                /* Buttons */
                .stButton>button {
                    border-radius: 10px;
                    border: 1px solid rgba(255,255,255,0.15);
                    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(0,0,0,.06));
                    transition: all .15s ease;
                }
                .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(0,0,0,.15); }
                /* Sidebar cards */
                section[data-testid="stSidebar"] .element-container div:has(> div > h1),
                section[data-testid="stSidebar"] .stMarkdown { background: var(--panel); padding: 8px 12px; border-radius: 10px; }
                /* Log container monospace, compact */
                .game-log { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 0.9rem; }
                .badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:.8rem; background:#333; color:#fff; }
                .badge.friendly { background: var(--friendly); }
                .badge.enemy { background: var(--enemy); }
                .badge.neutral { background: var(--neutral); color:#222; }
                .phase-banner { padding: 10px 14px; border-radius: 12px; background: linear-gradient(90deg, rgba(247,178,103,.25), rgba(255,255,255,.03)); border:1px solid rgba(255,255,255,.12); }
                </style>
                """,
                unsafe_allow_html=True,
        )

BASE_WIDTH = 800
BASE_HEIGHT = 400

def create_map_with_overlays(game_state: GameState, map_width=720, map_height=360):
    """Create the game map with territory overlays and return positions for hit-testing"""
    try:
        img = Image.open("GameMapV3.png").convert("RGB")
        img = img.resize((map_width, map_height), Image.BICUBIC)
    except FileNotFoundError:
        img = Image.new('RGB', (map_width, map_height), color='white')
        draw_temp = ImageDraw.Draw(img)
        draw_temp.ellipse([50, 50, 750, 350], fill='#87CEEB', outline='#4682B4', width=3)
        draw_temp.ellipse([20, 250, 120, 350], fill='#FFB6C1', outline='#FF69B4', width=2)
        draw_temp.ellipse([700, 50, 800, 150], fill='#90EE90', outline='#32CD32', width=2)
        st.warning("⚠️ GameMapV3.png not found! Using fallback map.")
    draw = ImageDraw.Draw(img)
    try:
        font_units = ImageFont.truetype("arial.ttf", 18)
        font_label = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        try:
            font_units = ImageFont.truetype("DejaVuSans.ttf", 18)
            font_label = ImageFont.truetype("DejaVuSans.ttf", 12)
        except Exception:
            font_units = ImageFont.load_default()
            font_label = ImageFont.load_default()
    sx = map_width / BASE_WIDTH
    sy = map_height / BASE_HEIGHT
    render_positions = {}
    for territory in game_state.territories.values():
        if territory.owner == 1:
            color = game_state.players[1].color
        elif territory.owner == 2:
            color = game_state.players[2].color
        else:
            color = '#FFD700'
        cx = int(round(territory.x * sx))
        cy = int(round(territory.y * sy))
        r0 = int(round(territory.radius * (sx + sy) / 2))
        margin = 2
        max_r = min(r0, cx - margin, map_width - margin - cx, cy - margin, map_height - margin - cy)
        r = max(6, max_r) if max_r > 0 else 6
        left = cx - r
        top = cy - r
        right = cx + r
        bottom = cy + r
        overlay_color = color
        if territory.owner == 0:
            overlay_color = '#FFD700'
        draw.ellipse([left, top, right, bottom], fill=overlay_color, outline='#2A2A2A', width=4)
        if territory.id == game_state.selected_territory:
            halo_pad = 8
            draw.ellipse([left-halo_pad, top-halo_pad, right+halo_pad, bottom+halo_pad], outline='#FFFFFF', width=2)
            draw.ellipse([left-halo_pad-4, top-halo_pad-4, right+halo_pad+4, bottom+halo_pad+4], outline='#F7B267', width=2)
        text_color = 'white' if territory.owner != 0 else 'black'
        draw.text((cx, cy - 5), str(territory.units), fill=text_color, anchor="mm", font=font_units, stroke_width=2, stroke_fill="#000000")
        draw.text((cx, cy + 10), territory.id.upper(), fill='#111111', anchor="mm", font=font_label, stroke_width=2, stroke_fill="#FFFFFF")
        render_positions[territory.id] = {"cx": cx, "cy": cy, "r": r}
    return img, render_positions

def add_log(message: str):
    """Add message to game log"""
    st.session_state.game.game_log.append(message)

def setup_phase():
    """Handle game setup"""
    st.header("🏰 Commissioner's Bonus Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        p1_name = st.text_input("Player 1 Name", value="Red Kingdom")
        
    with col2:
        p2_name = st.text_input("Player 2 Name", value="Blue Kingdom")
    
    st.markdown("---")
    st.markdown("**To determine who goes first, each player must state when they last spent money in real life.**")
    st.markdown("*The person who spent money most recently gets the Commissioner's Bonus and goes first!*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"{p1_name} Goes First", use_container_width=True):
            start_game(p1_name, p2_name, 1)
            
    with col2:
        if st.button(f"{p2_name} Goes First", use_container_width=True):
            start_game(p1_name, p2_name, 2)

def start_game(p1_name: str, p2_name: str, first_player: int):
    """Start the game with chosen player order"""
    game = st.session_state.game
    game.players[1].name = p1_name
    game.players[2].name = p2_name
    game.current_player = first_player
    game.phase = 'movement'
    
    add_log(f"🎯 {game.players[first_player].name} wins the Commissioner's Bonus!")
    add_log("⚔️ Game begins! Movement phase started.")
    # Reset movement and attack UI
    st.session_state.show_move = False
    st.session_state.show_attack = False
    st.rerun()

def movement_phase():
    """Handle movement phase"""
    game = st.session_state.game
    
    st.header(f"⚔️ {game.players[game.current_player].name}'s Turn - Movement Phase")
    badge_class = 'friendly' if game.current_player == 1 else 'enemy'
    st.markdown(
        f"<div class='phase-banner'><strong>Phase:</strong> {game.phase.title()} • "
        f"<span class='badge {badge_class}'>Player {game.current_player}</span></div>",
        unsafe_allow_html=True,
    )
    
    # We now select via clicking on the map (set in main); show a small summary if selected
    if game.selected_territory:
        selected_territory = game.territories[game.selected_territory]
        st.info(f"📍 Selected: {selected_territory.name} ({game.selected_territory.upper()}) • {selected_territory.units} units")
    
    # Show actions immediately for selected node
    if game.selected_territory:
        selected = game.territories[game.selected_territory]
        if selected.owner == game.current_player and selected.units > 1:
            cols = st.columns(2)
            with cols[0]:
                show_movement_options(game.selected_territory)
            with cols[1]:
                show_attack_options(game.selected_territory)
        else:
            st.info("Select one of your territories with at least 2 units to act.")
    
    # Always allow ending the turn
    if st.button("🔄 End Turn"):
        end_movement_phase()

def show_movement_options(from_territory_id: str):
    """Show movement options for selected territory"""
    game = st.session_state.game
    source = game.territories[from_territory_id]
    
    # Get adjacent territories
    adjacent = game.adjacency.get(from_territory_id, [])
    valid_moves = []
    
    for tid in adjacent:
        target = game.territories[tid]
        # Allow moves or attacks to any adjacent territory
        valid_moves.append((tid, target))
    
    if not valid_moves:
        st.warning("No valid territories to move to!")
        # Hide movement options when no moves available
        st.session_state.show_move = False
        return
    
    st.subheader(f"🚶 Move units from {source.name}")
    
    # Select destination
    move_options = {}
    for tid, territory in valid_moves:
        if territory.owner == game.current_player:
            status = "Friendly"
        elif territory.owner == 0:
            status = "Neutral"
        else:
            status = "Hostile"
        label = f"{territory.name} ({territory.id.upper()}) - {status} ({territory.units} units)"
        move_options[label] = tid
    
    if move_options:
        dest_label = st.selectbox(
            "Choose destination:",
            list(move_options.keys()),
            key="destination_select"
        )
        
        destination_id = move_options[dest_label]
        
        # Select number of units to move
        max_units = source.units - 1  # Must leave at least 1 unit
        if max_units > 1:
            units_to_move = st.slider(
                "Number of units to move:",
                min_value=1,
                max_value=max_units,
                value=min(3, max_units),
                key="units_slider"
            )
            if st.button(f"✅ Move {units_to_move} units"):
                move_units(from_territory_id, destination_id, units_to_move)
        elif max_units == 1:
            # Only one unit can move
            if st.button("✅ Move 1 unit"):
                move_units(from_territory_id, destination_id, 1)

def show_attack_options(from_territory_id: str):
    """Show attack options for selected territory (neutral or hostile)"""
    game = st.session_state.game
    source = game.territories[from_territory_id]
    # Get adjacent territories
    adjacent = game.adjacency.get(from_territory_id, [])
    attack_targets = []
    for tid in adjacent:
        target = game.territories[tid]
        if target.owner != game.current_player:
            attack_targets.append((tid, target))
    if not attack_targets:
        st.warning("No adjacent territories to attack!")
        st.session_state.show_attack = False
        return
    st.subheader(f"🗡️ Attack from {source.name}")
    options = {}
    for tid, territory in attack_targets:
        status = "Neutral" if territory.owner == 0 else "Hostile"
        label = f"{territory.name} ({territory.id.upper()}) - {status} ({territory.units} units)"
        options[label] = tid
    # Select target
    selected_label = st.selectbox(
        "Choose target:",
        list(options.keys()),
        key="attack_select"
    )
    destination_id = options[selected_label]
    # Choose number of units to attack with
    max_units = source.units - 1  # leave one behind
    if max_units > 1:
        units_to_attack = st.slider(
            "Units to attack with:",
            min_value=1,
            max_value=max_units,
            value=min(3, max_units),
            key="attack_units_slider"
        )
        if st.button(f"⚔️ Attack {units_to_attack} units"):
            move_units(from_territory_id, destination_id, units_to_attack)
    elif max_units == 1:
        if st.button("⚔️ Attack with 1 unit"):
            move_units(from_territory_id, destination_id, 1)

def move_units(from_id: str, to_id: str, num_units: int):
    """Move units between territories"""
    game = st.session_state.game
    source = game.territories[from_id]
    destination = game.territories[to_id]
    
    if destination.owner == 0:
        # Moving to neutral territory = attack
        add_log(f"⚔️ {game.players[game.current_player].name} attacks {destination.name} with {num_units} units!")
        combat_result = resolve_neutral_combat(num_units, destination.units)
        
        if combat_result['success']:
            # Conquer territory
            destination.owner = game.current_player
            destination.units = combat_result['surviving_attackers']
            source.units -= num_units
            add_log(f"🏰 {destination.name} conquered! {destination.units} units garrison.")
            # Continue from new territory
            game.selected_territory = destination.id
            st.session_state.show_move = True
        else:
            # Attack failed
            source.units -= combat_result['units_lost']
            add_log(f"💔 Attack on {destination.name} failed! Lost {combat_result['units_lost']} units.")
            # If still movable, stay on same source
            if source.units > 1:
                st.session_state.show_move = True
            
    elif destination.owner == game.current_player:
        # Moving to own territory = reinforcement
        destination.units += num_units
        source.units -= num_units
        add_log(f"🚶 Moved {num_units} units from {source.name} to {destination.name}")
        # Update selection to the destination for QoL and highlight
        game.selected_territory = destination.id
        st.session_state.show_move = True
    
    else:
        # Attack enemy territory
        add_log(f"⚔️ {game.players[game.current_player].name} attacks {destination.name} with {num_units} units!")
        combat_result = resolve_pvp_combat(num_units, destination.units)
        
        if combat_result['success']:
            # Victory! Move surviving units to conquer territory
            surviving_units = combat_result['surviving_attackers']
            destination.units = surviving_units
            destination.owner = game.current_player
            source.units -= num_units
            add_log(f"🏰 Conquered {destination.name} with {surviving_units} units!")
            
            # If any units left, allow continued movement
            if surviving_units > 1:
                game.selected_territory = destination.id
                st.session_state.show_move = True
        else:
            # Defeat, units are lost
            source.units -= combat_result['units_lost']
            add_log(f"💔 Attack on {destination.name} failed! Lost {combat_result['units_lost']} units.")
            # If still movable, stay on same source
            if source.units > 1:
                st.session_state.show_move = True
    
    st.rerun()

def resolve_neutral_combat(attacking_units: int, defending_units: int):
    """Resolve combat against neutral territory"""
    defeated_defenders = 0
    units_lost = 0
    
    for i in range(attacking_units):
        roll = random.randint(1, 6)
        add_log(f"🎲 Unit {i+1} rolls {roll}")
        
        if roll >= 3:  # Success
            defeated_defenders += 1
            add_log(f"✅ Unit succeeds!")
            
            if defeated_defenders >= defending_units:
                # Territory conquered!
                surviving_attackers = attacking_units - i
                return {
                    'success': True,
                    'surviving_attackers': surviving_attackers,
                    'units_lost': i
                }
        else:
            # Unit dies
            units_lost += 1
            add_log(f"💀 Unit dies in combat!")
    
    # Attack failed
    return {
        'success': False,
        'surviving_attackers': 0,
        'units_lost': units_lost
    }

def resolve_pvp_combat(attacking_units: int, defending_units: int):
    """Resolve player vs player combat"""
    # Simplified combat resolution: higher total wins
    attack_roll = sum(random.randint(1, 6) for _ in range(attacking_units))
    defense_roll = sum(random.randint(1, 6) for _ in range(defending_units))
    
    add_log(f"⚔️ Combat: {attacking_units}v{defending_units} - Rolls: {attack_roll} vs {defense_roll}")
    
    if attack_roll > defense_roll:
        # Attackers win
        units_lost = defending_units  # All defenders are lost
        surviving_attackers = attacking_units - units_lost  # Assume equal loss
        add_log(f"✅ Attack successful! Defenders lose all {units_lost} units.")
        return {
            'success': True,
            'surviving_attackers': surviving_attackers,
            'units_lost': units_lost
        }
    else:
        # Defenders win or tie
        units_lost = attacking_units  # All attackers are lost
        add_log(f"💔 Attack failed! {units_lost} attackers lost.")
        return {
            'success': False,
            'surviving_attackers': 0,
            'units_lost': units_lost
        }

def attack_neutral_territory(from_territory_id: str):
    """Attack a neutral territory (legacy function, now handled by move_units)"""
    # Deprecated path; attack is handled in show_attack_options + move_units
    st.info("Use the Attack panel to choose a target.")

def end_movement_phase():
    """End movement phase and move to reinforcement"""
    game = st.session_state.game
    game.phase = 'reinforcement'
    add_log(f"🔄 {game.players[game.current_player].name} ends movement phase")
    add_log("🎲 Time to roll for reinforcements!")
    st.rerun()

def reinforcement_phase():
    """Handle reinforcement phase"""
    game = st.session_state.game
    
    st.header(f"🎲 {game.players[game.current_player].name}'s Reinforcement Phase")
    
    if st.button("🎯 Roll for Reinforcements"):
        roll = random.randint(1, 6)
        add_log(f"🎲 Reinforcement roll: {roll}")
        
        if roll == 6:
            hq_id = game.players[game.current_player].hq_territory
            game.territories[hq_id].units += 2
            add_log(f"🎉 Rolled a 6! +2 units added to {game.territories[hq_id].name}")
        else:
            add_log("😐 No reinforcements this turn")
        
        # End turn
        game.current_player = 1 if game.current_player == 2 else 2
        game.phase = 'movement'
        game.turn_count += 1
        add_log(f"🆕 {game.players[game.current_player].name}'s turn begins!")
        st.rerun()

def display_game_info():
    """Display current game information in sidebar"""
    game = st.session_state.game
    
    with st.sidebar:
        st.header("🏰 Game Status")
        
        # Player info with colored badges
        for player_id, player in game.players.items():
            st.subheader(f"{player.name}")
            total_units = sum(t.units for t in game.territories.values() if t.owner == player_id)
            territories_owned = len([t for t in game.territories.values() if t.owner == player_id])
            color_class = 'friendly' if player_id == 1 else 'enemy'
            st.markdown(f"<span class='badge {color_class}'>Units: {total_units}</span> &nbsp; <span class='badge {color_class}'>Territories: {territories_owned}</span>", unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Game log
        st.subheader("📜 Game Log")
        log_container = st.container()
        with log_container:
            # Show last 12 messages in descending order (latest first)
            safe_lines = [html.escape(m) for m in list(reversed(game.game_log[-12:]))]
            st.markdown("<div class='game-log'>" + "<br>".join(safe_lines) + "</div>", unsafe_allow_html=True)

def main():
    """Main game function"""
    init_game_state()
    inject_theme_css()
    
    st.title("⚔️ Conquest of the Realm")
    
    game = st.session_state.game
    
    # Display game map smaller and clickable if extension is available
    map_img, positions = create_map_with_overlays(game)
    coords = None
    if streamlit_image_coordinates:
        coords = streamlit_image_coordinates(map_img, key="map_click")
    else:
        st.image(map_img, caption="Realm Map", use_container_width=True)
    # If clicked, find nearest territory within its radius and select it
    if coords and isinstance(coords, dict) and "x" in coords and "y" in coords:
        x = coords["x"]
        y = coords["y"]
        for tid, p in positions.items():
            dx = x - p["cx"]
            dy = y - p["cy"]
            if dx*dx + dy*dy <= p["r"]*p["r"]:
                game.selected_territory = tid
                break
    
    # Display game information
    display_game_info()
    
    # Handle game phases
    if game.phase == 'setup':
        setup_phase()
    elif game.phase == 'movement':
        movement_phase()
    elif game.phase == 'reinforcement':
        reinforcement_phase()
    
    # Debug info (remove in production)
    with st.expander("🔧 Debug Info"):
        st.write("Current Phase:", game.phase)
        st.write("Current Player:", game.current_player)
        st.write("Selected Territory:", game.selected_territory)
        st.write("Turn Count:", game.turn_count)

if __name__ == "__main__":
    main()