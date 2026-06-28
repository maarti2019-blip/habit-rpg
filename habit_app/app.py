import os
import requests
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

app = Flask(__name__)
app.secret_key = 'rpg_accountability_secret_chain'
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Secure Cloud Database Connection ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db'))
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- TIMEZONE HELPER (Enforces US/Eastern Standard Time) ---
def get_est_now():
    return datetime.now(ZoneInfo("America/New_York"))

SOLO_ENEMIES = [
    "Goblin", "Skeleton", "Slime", "Orc", "Troll", "Kobold", "Harpy", "Imp", "Ghoul", "Zombie",
    "Bandit", "Cultist", "Sprite", "Mimic", "Spider", "Rat", "Wolf", "Bat", "Hobgoblin", "Wraith"
]

RAID_BOSSES = [
    "Dragon", "Behemoth", "Kraken", "Leviathan", "Hydra", "Lich", "Titan", "Colossus", "Balrog", "Chimera",
    "Wyrm", "Tarrasque", "Cyclops", "Sphinx", "Roc", "Wendigo", "Dullahan", "Juggernaut", "Beholder"
]

ALL_EVENTS = [
    ("Frenzy of the Warrior", "Workout DMG is 3.0x, but Hobby DMG is 0.5x!"),
    ("Scholar’s Blessing", "Hobby Time deals 3.0x damage, but Workouts deal 0.5x!"),
    ("The Maid's Crusade", "Initiative Strikes deal an absolutely massive 300 Flat DMG instead of 50!"),
    ("Critical Strike Weekend", "Every action logged has a 25% chance to instantly execute your Solo Boss!"),
    ("Synergy Link", "Matching your partner's logged activity type today triggers a bonus 500 DMG blast to the Raid Boss!"),
    ("Goblin Merchant's Crash", "Solo Bosses drop 2x Gold, but 0% Equipment Orbs drop!"),
    ("Meteor Shower", "Every Gacha Orb you crack open drops two items instead of one!"),
    ("Treasure Mimic Infestation", "Defeating a Solo Boss drops a flat $10.00 instantly into your vault!"),
    ("The Cursed Vault", "Gold drops are slashed in half, but Legendary drop rates are 10x higher!"),
    ("Alchemist’s Bazaar", "Using any inventory consumable item instantly refunds a $2.00 rebate to your vault!"),
    ("Raid Boss Enrage", "The Raid Boss spawns with double max HP, but drops guaranteed Legendary gear!"),
    ("Slime Outbreak", "All new Solo Bosses spawn as Frail Slimes with only 50 Max HP!"),
    ("Titan’s Shield", "Raid Boss ignores activity overflow damage! It can only be wounded by Consumable Items!"),
    ("Necromancer’s Curse", "Defeated Solo Bosses respawn on Sunday with exactly 1 HP!"),
    ("Colosseum Draft", "The daily Solo Boss kill limit cap is shattered from 3 up to 10!"),
    ("Amnesia Fog", "All exact enemy health values are hidden behind dark fog! ??? / ??? HP"),
    ("The Early Bird Wormhole", "Logging any activity before 10:00 AM grants a 1.5x global multiplier for the day!"),
    ("The Shadow Clone", "A dark shadow copy takes over! Defeat it by letting your partner deal 70% of the damage!"),
    ("Broken Seal", "Active inventory item buffs have their remaining durations expanded to a flat 72 hours!"),
    ("Gambler’s Fallacy", "Logging exactly 7 minutes of any action rewards a guaranteed equipment item box!")
]

# --- THE FULL 80-ITEM LOOT TABLE ---
COMMON_ITEMS = [
    ("Rusty Dagger", "damage_solo", 20.0, "Instantly deal 20 DMG to your Solo Boss."),
    ("Throwing Stone", "damage_solo", 10.0, "Instantly deal 10 DMG to your Solo Boss."),
    ("Frayed Bowstring", "buff_workout", 1.05, "Multiplies Workout DMG by 1.05x for 24h."),
    ("Tarnished Coin", "gold", 0.50, "Instantly adds $0.50 to your Vault."),
    ("Wooden Buckler", "buff_global", 1.05, "Multiplies ALL DMG by 1.05x for 24h."),
    ("Dull Hatchet", "damage_raid", 15.0, "Instantly deal 15 DMG to the Raid Boss."),
    ("Dusty Tome", "buff_hobby", 1.05, "Multiplies Hobby DMG by 1.05x for 24h."),
    ("Tin Mug", "gold", 0.75, "Instantly adds $0.75 to your Vault."),
    ("Cracked Lens", "buff_chore", 1.05, "Multiplies Chore Time DMG by 1.05x for 24h."),
    ("Pebble Memento", "gold", 0.25, "Instantly adds $0.25 to your Vault."),
    ("Old Rag", "damage_solo", 5.0, "Instantly deal 5 DMG to your Solo Boss."),
    ("Copper Ring", "gold", 1.00, "Instantly adds $1.00 to your Vault."),
    ("Faded Blueprint", "buff_hobby", 1.10, "Multiplies Hobby DMG by 1.10x for 24h."),
    ("Sturdy Stick", "damage_raid", 10.0, "Instantly deal 10 DMG to the Raid Boss."),
    ("Leather Scrap", "buff_workout", 1.10, "Multiplies Workout DMG by 1.10x for 24h."),
    ("Sooty Candle", "buff_chore", 1.10, "Multiplies Chore Time DMG by 1.10x for 24h."),
    ("Iron Nail", "damage_solo", 15.0, "Instantly deal 15 DMG to your Solo Boss."),
    ("Bone Charm", "buff_global", 1.02, "Multiplies ALL DMG by 1.02x for 24h."),
    ("Dried Herb", "gold", 0.30, "Instantly adds $0.30 to your Vault."),
    ("Novice Badge", "buff_global", 1.08, "Multiplies ALL DMG by 1.08x for 24h.")
]

UNCOMMON_ITEMS = [
    ("Steel Longsword", "damage_solo", 50.0, "Instantly deal 50 DMG to your Solo Boss."),
    ("Silver Chalice", "gold", 2.50, "Instantly adds $2.50 to your Vault."),
    ("Iron Gauntlets", "buff_workout", 1.25, "Multiplies Workout DMG by 1.25x for 24h."),
    ("Goblin Bomb", "damage_raid", 75.0, "Instantly deal 75 DMG to the Raid Boss."),
    ("Scholar's Quill", "buff_hobby", 1.25, "Multiplies Hobby DMG by 1.25x for 24h."),
    ("Sturdy Broom", "buff_chore", 1.25, "Multiplies Chore Time DMG by 1.25x for 24h."),
    ("Focus Ring", "buff_global", 1.15, "Multiplies ALL DMG by 1.15x for 24h."),
    ("Bag of Silver", "gold", 3.00, "Instantly adds $3.00 to your Vault."),
    ("Crossbow", "damage_raid", 100.0, "Instantly deal 100 DMG to the Raid Boss."),
    ("Mana Potion", "buff_hobby", 1.30, "Multiplies Hobby DMG by 1.30x for 24h."),
    ("Stamina Potion", "buff_workout", 1.30, "Multiplies Workout DMG by 1.30x for 24h."),
    ("Haste Potion", "buff_chore", 1.30, "Multiplies Chore Time DMG by 1.30x for 24h."),
    ("Spiked Mace", "damage_solo", 75.0, "Instantly deal 75 DMG to your Solo Boss."),
    ("Jade Idol", "gold", 4.00, "Instantly adds $4.00 to your Vault."),
    ("Hunter's Cloak", "buff_global", 1.18, "Multiplies ALL DMG by 1.18x for 24h."),
    ("Alchemist Fire", "damage_raid", 120.0, "Instantly deal 120 DMG to the Raid Boss."),
    ("Polished Shield", "buff_global", 1.20, "Multiplies ALL DMG by 1.20x for 24h."),
    ("Assassin's Dagger", "damage_solo", 90.0, "Instantly deal 90 DMG to your Solo Boss."),
    ("Gemstone Shard", "gold", 5.00, "Instantly adds $5.00 to your Vault."),
    ("Acolyte's Robe", "buff_hobby", 1.35, "Multiplies Hobby DMG by 1.35x for 24h.")
]

RARE_ITEMS = [
    ("Mithril Blade", "damage_solo", 200.0, "Instantly deal 200 DMG to your Solo Boss."),
    ("Gold Ingot", "gold", 10.00, "Instantly adds $10.00 to your Vault."),
    ("Berserker's Axe", "buff_workout", 1.50, "Multiplies Workout DMG by 1.50x for 24h."),
    ("Master Brush", "buff_hobby", 1.50, "Multiplies Hobby DMG by 1.50x for 24h."),
    ("Maid's Bell", "chore_pass", 0, "Instantly forces your Chores box to Complete."),
    ("Dragon's Breath", "damage_raid", 250.0, "Instantly deal 250 DMG to the Raid Boss."),
    ("Platinum Crown", "gold", 12.00, "Instantly adds $12.00 to your Vault."),
    ("Arcane Staff", "buff_global", 1.35, "Multiplies ALL DMG by 1.35x for 24h."),
    ("Valkyrie Wings", "buff_workout", 1.60, "Multiplies Workout DMG by 1.60x for 24h."),
    ("Timepiece", "buff_chore", 1.60, "Multiplies Chore Time DMG by 1.60x for 24h."),
    ("Grimoire", "buff_hobby", 1.60, "Multiplies Hobby DMG by 1.60x for 24h."),
    ("Meteor Scroll", "damage_raid", 300.0, "Instantly deal 300 DMG to the Raid Boss."),
    ("Royal Signet", "gold", 15.00, "Instantly adds $15.00 to your Vault."),
    ("Shadow Bow", "damage_solo", 250.0, "Instantly deal 250 DMG to your Solo Boss."),
    ("Knight's Armor", "buff_global", 1.40, "Multiplies ALL DMG by 1.40x for 24h."),
    ("Crystal Ball", "buff_hobby", 1.55, "Multiplies Hobby DMG by 1.55x for 24h."),
    ("Titan's Belt", "buff_workout", 1.55, "Multiplies Workout DMG by 1.55x for 24h."),
    ("Feather Duster", "buff_chore", 1.55, "Multiplies Chore Time DMG by 1.55x for 24h."),
    ("Treasure Map", "gold", 8.00, "Instantly adds $8.00 to your Vault."),
    ("Lightning Bolt", "damage_solo", 280.0, "Instantly deal 280 DMG to your Solo Boss.")
]

LEGENDARY_ITEMS = [
    ("Excalibur", "damage_solo", 1000.0, "Instantly obliterate your Solo Boss for 1,000 DMG."),
    ("Dragon's Hoard", "gold", 50.00, "Instantly adds $50.00 to your Vault."),
    ("Aegis of the Titan", "buff_workout", 2.00, "Multiplies Workout DMG by 2.00x for 24h."),
    ("Crown of the Scholar", "buff_hobby", 2.00, "Multiplies Hobby DMG by 2.00x for 24h."),
    ("Chrono-Watch", "buff_chore", 2.00, "Multiplies Chore Time DMG by 2.00x for 24h."),
    ("Hero's Elixir", "damage_raid", 1000.0, "Instantly blast the Raid Boss for 1,000 DMG."),
    ("Archon's Halo", "buff_global", 1.75, "Multiplies ALL DMG by 1.75x for 24h."),
    ("Philosopher's Stone", "gold", 30.00, "Instantly adds $30.00 to your Vault."),
    ("Orb of Annihilation", "damage_raid", 1500.0, "Instantly deal 1,500 DMG to the Raid Boss."),
    ("Divine Rapier", "damage_solo", 800.0, "Instantly deal 800 DMG to your Solo Boss."),
    ("God-King's Treasure", "gold", 40.00, "Instantly adds $40.00 to your Vault."),
    ("Omniscience Gem", "buff_hobby", 2.50, "Multiplies Hobby DMG by 2.50x for 24h."),
    ("Hercules' Bracers", "buff_workout", 2.50, "Multiplies Workout DMG by 2.50x for 24h."),
    ("Automaton Core", "buff_chore", 2.50, "Multiplies Chore Time DMG by 2.50x for 24h."),
    ("Essence of Magic", "buff_global", 2.00, "Multiplies ALL DMG by 2.00x for 24h."),
    ("Midas Touch", "gold", 25.00, "Instantly adds $25.00 to your Vault."),
    ("Supernova Scroll", "damage_raid", 2000.0, "Instantly deal 2,000 DMG to the Raid Boss."),
    ("Scythe of Death", "damage_solo", 1500.0, "Instantly deal 1,500 DMG to your Solo Boss."),
    ("Infinity Catalyst", "buff_global", 2.50, "Multiplies ALL DMG by 2.50x for 24h."),
    ("Diamond Chest", "gold", 45.00, "Instantly adds $45.00 to your Vault.")
]

# --- Models ---
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    gold_balance = db.Column(db.Float, default=0.0)
    last_known_ip = db.Column(db.String(100), nullable=True)
    solo_monster_hp = db.Column(db.Float, default=300.0)
    solo_monster_max = db.Column(db.Float, default=300.0)
    solo_monster_name = db.Column(db.String(100), default="Slime")
    bosses_killed_today = db.Column(db.Integer, default=0)
    chores_completed = db.Column(db.Boolean, default=False)
    last_active_date = db.Column(db.String(20), nullable=True)
    
    current_week = db.Column(db.Integer, nullable=True)
    wk_workout = db.Column(db.Float, default=0.0)
    wk_hobby = db.Column(db.Float, default=0.0)
    wk_chore = db.Column(db.Float, default=0.0)
    wk_bosses = db.Column(db.Integer, default=0)
    wk_gold = db.Column(db.Float, default=0.0)
    
    prev_wk_workout = db.Column(db.Float, default=0.0)
    prev_wk_hobby = db.Column(db.Float, default=0.0)
    prev_wk_chore = db.Column(db.Float, default=0.0)
    prev_wk_bosses = db.Column(db.Integer, default=0)
    prev_wk_gold = db.Column(db.Float, default=0.0)
    show_weekly_report = db.Column(db.Boolean, default=False)

    egg_minutes = db.Column(db.Float, default=0.0)
    has_pet = db.Column(db.Boolean, default=False)
    pet_level = db.Column(db.Integer, default=1)
    pet_xp = db.Column(db.Float, default=0.0)

class RaidBoss(db.Model):
    __tablename__ = 'raid_boss'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Dragon")
    max_hp = db.Column(db.Float, default=1200.0)
    current_hp = db.Column(db.Float, default=1200.0)
    world_level = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    next_spawn_date = db.Column(db.DateTime, nullable=True)

class ServerState(db.Model):
    __tablename__ = 'server_state'
    id = db.Column(db.Integer, primary_key=True)
    active_event = db.Column(db.String(100), nullable=True)
    event_description = db.Column(db.String(255), nullable=True)
    last_logged_activity_type = db.Column(db.String(50), nullable=True)
    last_logged_user_id = db.Column(db.Integer, nullable=True)

class PendingReward(db.Model):
    __tablename__ = 'pending_reward'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    gold_amount = db.Column(db.Float, default=0.0)
    item_name = db.Column(db.String(100), nullable=True)

class UserInventory(db.Model):
    __tablename__ = 'user_inventory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    category_target = db.Column(db.String(50), nullable=False)
    multiplier = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    rarity = db.Column(db.String(50), default="Common")

class TransactionHistory(db.Model):
    __tablename__ = 'transaction_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Discord Notification Helper ---
def notify_discord(message):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        try: requests.post(webhook_url, json={"content": message})
        except: pass

# --- Helpers & Core Event Interceptors ---
def get_monster_image(monster_name):
    safe_name = monster_name.lower().replace(" ", "_").replace("'", "")
    folder_path = os.path.join(app.static_folder, 'images', 'monsters')
    if not os.path.exists(folder_path): return "/static/icon-192.png"
    try:
        actual_files = os.listdir(folder_path)
        for real_file_name in actual_files:
            if real_file_name.lower().startswith(safe_name + "."):
                return f"/static/images/monsters/{real_file_name}"
    except: pass
    return "/static/icon-192.png" 

def manage_world_events():
    state = ServerState.query.first()
    if not state: return
    now = get_est_now()
    is_weekend = (now.weekday() == 4 and now.hour >= 17) or now.weekday() in [5, 6]
    
    if is_weekend and not state.active_event:
        evt = random.choice(ALL_EVENTS)
        state.active_event, state.event_description = evt
        db.session.commit()
    elif not is_weekend and state.active_event:
        state.active_event = None
        state.event_description = None
        db.session.commit()

def calculate_90_percent_loot_orb(world_level, event_name=None):
    if event_name == "The Cursed Vault": return round(random.uniform(0.50, 2.00), 2)
    level_bonus = (world_level - 1) * 0.25
    base_amt = random.uniform(3.00 + level_bonus, 4.00 + level_bonus) if random.random() <= 0.95 else random.uniform(2.00, 7.00 + level_bonus)
    return round(base_amt, 2)

def calculate_raid_boss_orb():
    return round(max(10.0, min(50.0, random.gauss(25.0, 10.0))), 2)

def roll_equipment(event_name=None):
    roll = random.random() * 100
    if event_name == "The Cursed Vault":
        if roll <= 5.0: return ("Legendary", random.choice(LEGENDARY_ITEMS))
        elif roll <= 20.0: return ("Rare", random.choice(RARE_ITEMS))
        elif roll <= 40.0: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
        else: return ("Common", random.choice(COMMON_ITEMS))
    else:
        if roll <= 0.5: return ("Legendary", random.choice(LEGENDARY_ITEMS))
        elif roll <= 3.5: return ("Rare", random.choice(RARE_ITEMS))
        elif roll <= 11.5: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
        elif roll <= 26.5: return ("Common", random.choice(COMMON_ITEMS))
    return None

def roll_raid_equipment():
    roll = random.random() * 100
    if roll <= 10.0: return ("Legendary", random.choice(LEGENDARY_ITEMS))
    elif roll <= 50.0: return ("Rare", random.choice(RARE_ITEMS))
    elif roll <= 90.0: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
    else: return ("Common", random.choice(COMMON_ITEMS))

def get_next_monday_midnight():
    now = get_est_now()
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    return (now + timedelta(days=days_ahead)).replace(hour=0, minute=1, second=0, microsecond=0)

def check_resets(user):
    now = get_est_now()
    today_str = now.strftime('%Y-%m-%d')
    current_iso_week = now.isocalendar()[1]
    
    if user.current_week is None: user.current_week = current_iso_week
    
    if user.last_active_date != today_str:
        user.bosses_killed_today = 0
        user.chores_completed = False
        user.last_active_date = today_str
        
    if user.current_week != current_iso_week:
        user.prev_wk_workout, user.prev_wk_hobby, user.prev_wk_chore = user.wk_workout, user.wk_hobby, user.wk_chore
        user.prev_wk_bosses, user.prev_wk_gold = user.wk_bosses, user.wk_gold
        
        user.wk_workout = user.wk_hobby = user.wk_chore = user.wk_gold = 0.0
        user.wk_bosses = 0
        
        user.current_week = current_iso_week
        user.show_weekly_report = True
        
    db.session.commit()

# --- Routes ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'): return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def auto_login_by_ip():
    if request.endpoint in ['static', 'manual_login', 'claim_gacha', 'spend_gold', 'use_item', 'feed_pet', 'dismiss_report'] or not request.endpoint: return
    if 'user_id' not in session:
        try:
            matched_user = User.query.filter_by(last_known_ip=get_client_ip()).first()
            if matched_user: session['user_id'] = matched_user.id
        except: pass

@app.route('/')
def index():
    current_user = User.query.get(session['user_id']) if 'user_id' in session else None
    boss = RaidBoss.query.first()
    players = User.query.all()
    server_state = ServerState.query.first()
    
    if not server_state:
        server_state = ServerState()
        db.session.add(server_state)
        db.session.commit()
        
    manage_world_events()
    if current_user: check_resets(current_user)

    # --- WEEKLY RAID BOSS RESET LOGIC ---
    if boss:
        # Failsafe for older DBs to ensure the timer works
        if boss.next_spawn_date is None:
            boss.next_spawn_date = get_est_now() - timedelta(days=1)
            db.session.commit()

        spawn_time = boss.next_spawn_date
        if spawn_time.tzinfo is None:
            spawn_time = spawn_time.replace(tzinfo=ZoneInfo("America/New_York"))

        # If it's time for the Monday reset (or past due)
        if get_est_now() >= spawn_time:
            was_defeated = (boss.current_hp <= 0 or not boss.is_active)
            
            if was_defeated:
                boss.world_level += 1
                boss.max_hp = round(boss.max_hp * 1.03, 1)
                
                # Apply 3% boost to all players' solo monsters
                for player in players:
                    player.solo_monster_max = round(player.solo_monster_max * 1.03, 1)
                    if player.solo_monster_hp > player.solo_monster_max:
                        player.solo_monster_hp = player.solo_monster_max
                        
                notify_discord(f"🔄 **NEW WEEK!** You defeated the previous boss. The world grows stronger! A new **{random.choice(RAID_BOSSES)}** (Lvl {boss.world_level}) has arrived!")
            else:
                notify_discord(f"🔄 **NEW WEEK!** The previous boss fled before you could defeat it! The World Level remains at {boss.world_level}. A new **{random.choice(RAID_BOSSES)}** has appeared!")
            
            # Spawn the new boss and reset the timer for NEXT Monday
            boss.name = random.choice(RAID_BOSSES)
            boss.current_hp = boss.max_hp
            boss.is_active = True
            boss.next_spawn_date = get_next_monday_midnight()
            db.session.commit()

    pending_rewards = PendingReward.query.filter_by(user_id=current_user.id).all() if current_user else []
    inventory = UserInventory.query.filter_by(user_id=current_user.id).all() if current_user else []
    
    transactions = TransactionHistory.query.filter_by(user_id=current_user.id).order_by(TransactionHistory.timestamp.desc()).limit(15).all() if current_user else []

    if inventory:
        for item in inventory:
            if item.is_active and item.expires_at and get_est_now() > item.expires_at.replace(tzinfo=ZoneInfo("America/New_York")):
                db.session.delete(item)
        db.session.commit()

    solo_img = get_monster_image(current_user.solo_monster_name) if current_user else None
    raid_img = get_monster_image(boss.name) if boss else None

    if current_user and current_user.has_pet and current_user.pet_xp >= 100:
        current_user.pet_level += 1
        current_user.pet_xp = 0
        db.session.commit()

    return render_template('index.html', current_user=current_user, players=players, boss=boss, pending_rewards=pending_rewards, inventory=inventory, solo_img=solo_img, raid_img=raid_img, server_state=server_state, transactions=transactions)

@app.route('/manual_login/<username>')
def manual_login(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.last_known_ip = get_client_ip()
        db.session.commit()
        session['user_id'] = user.id
    return redirect('/')

@app.route('/dismiss_report', methods=['POST'])
def dismiss_report():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.show_weekly_report = False
        db.session.commit()
    return redirect('/')

@app.route('/stage_activity', methods=['POST'])
def stage_activity():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    boss = RaidBoss.query.first()
    state = ServerState.query.first()
    check_resets(user)
    
    act_type = request.form.get('type')
    try: minutes = float(request.form.get('minutes', 0))
    except: minutes = 0.0

    if not user.has_pet and minutes > 0:
        user.egg_minutes += minutes
        if user.egg_minutes >= 100.0:
            user.has_pet = True

    workout_mult = 4.5
    hobby_mult = 7.0
    chore_mult = 5.0
    
    active_buffs = UserInventory.query.filter_by(user_id=user.id, is_active=True).all()
    for buff in active_buffs:
        if buff.category_target == 'buff_workout': workout_mult *= buff.multiplier
        elif buff.category_target == 'buff_hobby': hobby_mult *= buff.multiplier
        elif buff.category_target == 'buff_chore': chore_mult *= buff.multiplier
        elif buff.category_target == 'buff_global': 
            workout_mult *= buff.multiplier
            hobby_mult *= buff.multiplier
            chore_mult *= buff.multiplier

    if state.active_event == "Frenzy of the Warrior":
        workout_mult *= 3.0
        hobby_mult *= 0.5
    elif state.active_event == "Scholar’s Blessing":
        hobby_mult *= 3.0
        workout_mult *= 0.5
    
    if state.active_event == "The Early Bird Wormhole" and get_est_now().hour < 10:
        workout_mult *= 1.5; hobby_mult *= 1.5; chore_mult *= 1.5

    pet_multiplier = 1.0 + (user.pet_level * 0.01) if user.has_pet else 1.0
    workout_mult *= pet_multiplier; hobby_mult *= pet_multiplier; chore_mult *= pet_multiplier

    base_dmg = 0
    if act_type == 'workout': base_dmg = minutes * workout_mult; user.wk_workout += minutes
    elif act_type == 'hobby': base_dmg = minutes * hobby_mult; user.wk_hobby += minutes
    elif act_type == 'chore': base_dmg = minutes * chore_mult; user.wk_chore += minutes

    if 'chores' in request.form and not user.chores_completed:
        user.chores_completed = True
        base_dmg += 300.0 if state.active_event == "The Maid's Crusade" else 50.0

    if base_dmg <= 0: return redirect('/')

    if state.active_event == "Synergy Link" and state.last_logged_activity_type == act_type and state.last_logged_user_id != user.id:
        if boss.is_active: boss.current_hp -= 500.0

    state.last_logged_activity_type = act_type
    state.last_logged_user_id = user.id

    if state.active_event == "Critical Strike Weekend" and random.random() <= 0.25:
        base_dmg = user.solo_monster_hp

    if state.active_event == "Gambler’s Fallacy" and int(minutes) == 7:
        db.session.add(UserInventory(user_id=user.id, item_name="Gambler's Box", category_target="gold", multiplier=5.0, description="Guaranteed Box from the system!", rarity="Uncommon"))

    solo_dmg = base_dmg
    raid_dmg = 0
    kill_cap = 10 if state.active_event == "Colosseum Draft" else 3

    while solo_dmg > 0:
        target_hp = 1.0 if (state.active_event == "Necromancer’s Curse" and get_est_now().weekday() == 6) else user.solo_monster_hp
        
        if solo_dmg >= target_hp:
            solo_dmg -= target_hp
            user.bosses_killed_today += 1
            user.wk_bosses += 1
            
            gold_drop = calculate_90_percent_loot_orb(boss.world_level, state.active_event)
            if state.active_event == "Goblin Merchant's Crash": gold_drop *= 2.0
            if state.active_event == "Treasure Mimic Infestation": gold_drop = 10.00

            user.gold_balance += gold_drop; user.wk_gold += gold_drop
            
            if state.active_event != "Goblin Merchant's Crash":
                loot = roll_equipment(state.active_event)
                if loot:
                    tier, item_data = loot
                    i_name, i_cat, i_mult, i_desc = item_data
                    db.session.add(UserInventory(user_id=user.id, item_name=i_name, category_target=i_cat, multiplier=i_mult, description=i_desc, rarity=tier))
                    db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=f"[{tier}] {i_name}"))
                else:
                    db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))
                    
                if state.active_event == "Meteor Shower":
                    loot2 = roll_equipment(state.active_event)
                    if loot2:
                        tier2, item_data2 = loot2
                        i_name2, i_cat2, i_mult2, i_desc2 = item_data2
                        db.session.add(UserInventory(user_id=user.id, item_name=i_name2, category_target=i_cat2, multiplier=i_mult2, description=i_desc2, rarity=tier2))
                        db.session.add(PendingReward(user_id=user.id, gold_amount=0.0, item_name=f"[{tier2}] {i_name2} (Bonus!)"))
            else:
                db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))

            user.solo_monster_max = 50.0 if state.active_event == "Slime Outbreak" else 300.0
            user.solo_monster_hp = user.solo_monster_max
            user.solo_monster_name = "Slime" if state.active_event == "Slime Outbreak" else random.choice(SOLO_ENEMIES)
        else:
            user.solo_monster_hp -= solo_dmg
            solo_dmg = 0

    if solo_dmg > 0 and state.active_event != "Titan’s Shield":
        raid_dmg += solo_dmg

    if boss.is_active and raid_dmg > 0:
        if state.active_event == "The Shadow Clone":
            pass
        boss.current_hp -= raid_dmg
        
        # Boss dies mid-week. It stays dead until Monday reset.
        if boss.current_hp <= 0:
            boss.is_active = False
            for u in User.query.all():
                raid_drop = calculate_raid_boss_orb()
                raid_loot = roll_raid_equipment()
                r_tier, r_data = raid_loot
                r_name, r_cat, r_mult, r_desc = r_data
                db.session.add(UserInventory(user_id=u.id, item_name=r_name, category_target=r_cat, multiplier=r_mult, description=r_desc, rarity=r_tier))
                db.session.add(PendingReward(user_id=u.id, gold_amount=raid_drop, item_name=f"[Raid Boss Kill] [{r_tier}] {r_name}"))
                u.gold_balance += raid_drop
                u.wk_gold += raid_drop
            
            notify_discord(f"🌋 **{boss.name.upper()} DESTROYED!** Both players received a Raid Boss Orb and guaranteed high-tier loot! A new boss will spawn on Monday.")

    db.session.commit()
    return redirect('/')

@app.route('/feed_pet/<int:item_id>', methods=['POST'])
def feed_pet(item_id):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    item = UserInventory.query.filter_by(id=item_id, user_id=user.id).first()
    if item and user.has_pet:
        xp_gain = {"Common": 10.0, "Uncommon": 25.0, "Rare": 50.0, "Legendary": 100.0}.get(item.rarity, 10.0)
        user.pet_xp += xp_gain
        db.session.delete(item)
        db.session.commit()
    return redirect('/')

@app.route('/claim_gacha', methods=['POST'])
def claim_gacha():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        rewards = PendingReward.query.filter_by(user_id=user.id).all()
        total_gold = sum(r.gold_amount for r in rewards)
        PendingReward.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    return redirect('/')

@app.route('/spend_gold', methods=['POST'])
def spend_gold():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    try: amount = float(request.form.get('amount', 0))
    except: amount = 0.0
    
    reason = request.form.get('reason', 'Personal Reward')
    
    if amount > 0 and user.gold_balance >= amount:
        user.gold_balance -= amount
        db.session.add(TransactionHistory(user_id=user.id, amount=amount, reason=reason))
        db.session.commit()
        
        notify_discord(f"🎉 **CONGRATULATIONS!** {user.username} cashed out **${amount:.2f}** from their Vault!")
        
    return redirect('/')

@app.route('/use_item/<int:item_id>', methods=['POST'])
def use_item(item_id):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    state = ServerState.query.first()
    item = UserInventory.query.filter_by(id=item_id, user_id=user.id).first()
    if not item or item.is_active: return redirect('/')
    
    if state.active_event == "Alchemist’s Bazaar":
        user.gold_balance += 2.00; user.wk_gold += 2.00

    if item.category_target.startswith('buff'):
        item.is_active = True
        duration = 72 if state.active_event == "Broken Seal" else 24
        item.expires_at = get_est_now() + timedelta(hours=duration)
    elif item.category_target == 'damage_raid' or state.active_event == "Titan’s Shield":
        boss = RaidBoss.query.first()
        if boss.is_active: 
            boss.current_hp -= item.multiplier
            
            # Boss dies mid-week. It stays dead until Monday reset.
            if boss.current_hp <= 0:
                boss.is_active = False
                for u in User.query.all():
                    raid_drop = calculate_raid_boss_orb()
                    raid_loot = roll_raid_equipment()
                    r_tier, r_data = raid_loot
                    r_name, r_cat, r_mult, r_desc = r_data
                    db.session.add(UserInventory(user_id=u.id, item_name=r_name, category_target=r_cat, multiplier=r_mult, description=r_desc, rarity=r_tier))
                    db.session.add(PendingReward(user_id=u.id, gold_amount=raid_drop, item_name=f"[Raid Boss Kill] [{r_tier}] {r_name}"))
                    u.gold_balance += raid_drop
                    u.wk_gold += raid_drop
                notify_discord(f"🌋 **{boss.name.upper()} ANNIHILATED BY AN ITEM!** Both players received a Raid Boss Orb and guaranteed high-tier loot! A new boss will spawn on Monday.")
                
        db.session.delete(item)
    elif item.category_target == 'gold':
        user.gold_balance += item.multiplier
        user.wk_gold += item.multiplier
        db.session.delete(item)
    elif item.category_target == 'chore_pass':
        user.chores_completed = True
        db.session.delete(item)
    else:
        if item.category_target == 'damage_solo': user.solo_monster_hp -= item.multiplier
        db.session.delete(item)
        
    db.session.commit()
    return redirect('/')

def initialize_database():
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
        if not ServerState.query.first():
            db.session.add(ServerState())
        if not User.query.first():
            db.session.add(User(username='Alaina', solo_monster_name='Slime'))
            db.session.add(User(username='Matthew', solo_monster_name='Slime'))
            db.session.add(RaidBoss(name='Dragon'))
        db.session.commit()

initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
