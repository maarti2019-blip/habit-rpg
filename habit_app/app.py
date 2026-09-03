import os
import requests
import random
import holidays
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

WEEKLY_QUESTS = {
    # --- COMMON (Fast, easy week. $5 + Common Loot) ---
    1: {"title": "The Scout's Warmup", "type": "workout", "target": 60.0, "gold": 5.0, "tier": "Common", "desc": "Complete 60 minutes of light physical movement, walking, or stretching."},
    2: {"title": "Novice's Curiosity", "type": "hobby", "target": 60.0, "gold": 5.0, "tier": "Common", "desc": "Dedicate 60 minutes to practicing a skill, reading, or learning something new."},
    3: {"title": "Camp Cleanup", "type": "chore", "target": 60.0, "gold": 5.0, "tier": "Common", "desc": "Spend 60 minutes tidying up your immediate living spaces."},
    4: {"title": "Morning Patrol", "type": "workout", "target": 75.0, "gold": 5.0, "tier": "Common", "desc": "Log 75 minutes of steady active recovery or general fitness."},
    5: {"title": "The Tinkerer's Hour", "type": "hobby", "target": 75.0, "gold": 5.0, "tier": "Common", "desc": "Spend 75 minutes working on a personal project or creative outlet."},
    6: {"title": "Hearth & Home", "type": "chore", "target": 75.0, "gold": 5.0, "tier": "Common", "desc": "Complete 75 minutes of basic daily chores and household upkeep."},
    
    # --- UNCOMMON (Steady effort. $10 + Uncommon Loot) ---
    7: {"title": "Foot-Soldier's March", "type": "workout", "target": 120.0, "gold": 10.0, "tier": "Uncommon", "desc": "Log 120 minutes of steady-state cardio or endurance training."},
    8: {"title": "The Craftsman's Focus", "type": "hobby", "target": 120.0, "gold": 10.0, "tier": "Uncommon", "desc": "Dedicate 120 minutes to active project building or skill refinement."},
    9: {"title": "Quartermaster's Run", "type": "chore", "target": 120.0, "gold": 10.0, "tier": "Uncommon", "desc": "Spend 120 minutes running errands or managing household supplies."},
    10: {"title": "Warrior's Conditioning", "type": "workout", "target": 150.0, "gold": 10.0, "tier": "Uncommon", "desc": "Complete 150 minutes of general strength training and lifting."},
    11: {"title": "The Scholar's Study", "type": "hobby", "target": 150.0, "gold": 10.0, "tier": "Uncommon", "desc": "Spend 150 minutes in focused study, reading, or dedicated creative practice."},
    12: {"title": "Armory Organization", "type": "chore", "target": 150.0, "gold": 10.0, "tier": "Uncommon", "desc": "Spend 150 minutes organizing, decluttering, or tackling laundry."},
    13: {"title": "Amazonian Physique", "type": "workout", "target": 180.0, "gold": 10.0, "tier": "Uncommon", "desc": "Log 180 minutes focusing on building THAT BUTT and legs."},
    14: {"title": "The Artisan's Grind", "type": "hobby", "target": 180.0, "gold": 10.0, "tier": "Uncommon", "desc": "Spend 180 minutes making tangible progress on a core hobby."},
    
    # --- RARE (Heavy grind. $20 + Rare Loot) ---
    15: {"title": "The Iron Crucible", "type": "workout", "target": 240.0, "gold": 20.0, "tier": "Rare", "desc": "Endure 240 minutes of intense, heavy physical training."},
    16: {"title": "The Architect's Vision", "type": "hobby", "target": 240.0, "gold": 20.0, "tier": "Rare", "desc": "Dedicate 240 minutes to designing, creating, or building a complex project."},
    17: {"title": "The Quartermaster's Batch", "type": "chore", "target": 240.0, "gold": 20.0, "tier": "Rare", "desc": "Complete 240 minutes of large-scale meal prep and deep cleaning."},
    18: {"title": "Gladiator's Split", "type": "workout", "target": 300.0, "gold": 20.0, "tier": "Rare", "desc": "Log 300 minutes of strict, high-volume workout routines."},
    19: {"title": "Masterpiece Creation", "type": "hobby", "target": 300.0, "gold": 20.0, "tier": "Rare", "desc": "Spend 300 minutes pushing a major personal project toward completion."},
    20: {"title": "Castle Restoration", "type": "chore", "target": 300.0, "gold": 20.0, "tier": "Rare", "desc": "Log 300 minutes deep-cleaning multiple rooms and tackling neglected tasks."},
    
    # --- LEGENDARY (Insane commitment. $40 + Legendary Loot) ---
    21: {"title": "Ascension to Godhood", "type": "workout", "target": 450.0, "gold": 40.0, "tier": "Legendary", "desc": "A monumental 450 minutes of physical training. Only for the elite."},
    22: {"title": "The Magnum Opus", "type": "hobby", "target": 450.0, "gold": 40.0, "tier": "Legendary", "desc": "Dedicate 450 minutes to an overarching, legendary personal pursuit."},
    23: {"title": "Domain Purification", "type": "chore", "target": 450.0, "gold": 40.0, "tier": "Legendary", "desc": "Spend 450 minutes overhauling your entire living space from top to bottom."},
    24: {"title": "Titan's Awakening", "type": "workout", "target": 600.0, "gold": 40.0, "tier": "Legendary", "desc": "Log an unbelievable 600 minutes of exercise this week."},
    25: {"title": "Archmage's Dedication", "type": "hobby", "target": 600.0, "gold": 40.0, "tier": "Legendary", "desc": "Spend 600 minutes deeply immersed in mastering your chosen hobby."},
    26: {"title": "Grand Estate Overhaul", "type": "chore", "target": 600.0, "gold": 40.0, "tier": "Legendary", "desc": "Complete 600 minutes of massive household repair, cleaning, and organization."}
}
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
    ("Colosseum Champion", "Your first 3 Solo Boss kills of the day grant a massive 5x Gold Multiplier!"),
    ("Amnesia Fog", "All exact enemy health values are hidden behind dark fog! ??? / ??? HP"),
    ("The Early Bird Wormhole", "Logging any activity before 10:00 AM grants a 1.5x global multiplier for the day!"),
    ("The Shadow Clone", "A dark shadow copy takes over! Defeat it by letting your partner deal 70% of the damage!"),
    ("Broken Seal", "Active inventory item buffs have their remaining durations expanded to a flat 72 hours!"),
    ("Gambler’s Fallacy", "Logging exactly 7 minutes of any action rewards a guaranteed equipment item box!")
]

def is_event_active(est_now):
    """
    Returns True if:
    - It is Saturday or Sunday.
    - It is a US Federal Holiday.
    - It is the day BEFORE a weekend or holiday AND it is past 5:00 PM (17:00).
    - It is Friday AND Thursday was a holiday (bridges 4-day weekends).
    """
    # Fix 1: Remove the years= limitation so New Year's Eve doesn't break
    us_holidays = holidays.US() 
    
    # 1. Is today a weekend? (5 = Saturday, 6 = Sunday)
    if est_now.weekday() in [5, 6]:
        return True
        
    # 2. Is today a Federal Holiday?
    if est_now.date() in us_holidays:
        return True
        
    # 3. Fix 2: Bridge the "Friday Gap" 
    # If yesterday was a Thursday holiday, keep event active all day Friday
    yesterday = est_now.date() - timedelta(days=1)
    if est_now.weekday() == 4 and yesterday in us_holidays:
        return True
        
    # 4. Is tomorrow a weekend or holiday?
    tomorrow = est_now.date() + timedelta(days=1)
    is_tomorrow_off = (tomorrow.weekday() == 5 or tomorrow in us_holidays)
    
    # 5. Turn on at 5 PM the day before
    if is_tomorrow_off and est_now.hour >= 17:
        return True
        
    return False

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
    ("Mithril Blade", "damage_solo", 250.0, "Instantly deal 250 DMG to your Solo Boss."),
    ("Gold Ingot", "gold", 10.00, "Instantly adds $10.00 to your Vault."),
    ("Berserker's Axe", "buff_workout", 1.50, "Multiplies Workout DMG by 1.50x for 24h."),
    ("Master Brush", "buff_hobby", 1.50, "Multiplies Hobby DMG by 1.50x for 24h."),
    ("Maid's Bell", "chore_pass", 0, "Instantly forces your Chores box to Complete."),
    ("Dragon's Breath", "damage_raid", 350.0, "Instantly deal 350 DMG to the Raid Boss."),
    ("Platinum Crown", "gold", 14.00, "Instantly adds $14.00 to your Vault."),
    ("Arcane Staff", "buff_global", 1.35, "Multiplies ALL DMG by 1.35x for 24h."),
    ("Valkyrie Wings", "buff_workout", 1.60, "Multiplies Workout DMG by 1.60x for 24h."),
    ("Timepiece", "buff_chore", 1.60, "Multiplies Chore Time DMG by 1.60x for 24h."),
    ("Grimoire", "buff_hobby", 1.60, "Multiplies Hobby DMG by 1.60x for 24h."),
    ("Meteor Scroll", "damage_raid", 400.0, "Instantly deal 400 DMG to the Raid Boss."),
    ("Royal Signet", "gold", 15.00, "Instantly adds $15.00 to your Vault."),
    ("Shadow Bow", "damage_solo", 300.0, "Instantly deal 300 DMG to your Solo Boss."),
    ("Knight's Armor", "buff_global", 1.40, "Multiplies ALL DMG by 1.40x for 24h."),
    ("Crystal Ball", "buff_hobby", 1.55, "Multiplies Hobby DMG by 1.55x for 24h."),
    ("Titan's Belt", "buff_workout", 1.55, "Multiplies Workout DMG by 1.55x for 24h."),
    ("Feather Duster", "buff_chore", 1.55, "Multiplies Chore Time DMG by 1.55x for 24h."),
    ("Treasure Map", "gold", 12.00, "Instantly adds $12.00 to your Vault."),
    ("Lightning Bolt", "damage_solo", 350.0, "Instantly deal 350 DMG to your Solo Boss.")
]

# --- BRAND NEW EPIC TIER (Purple) ---
EPIC_ITEMS = [
    ("Obsidian Greatsword", "damage_solo", 600.0, "Instantly deal 600 DMG to your Solo Boss."),
    ("Gilded Vault Chest", "gold", 25.00, "Instantly adds $25.00 to your Vault."),
    ("War-God's Pauldrons", "buff_workout", 2.20, "Multiplies Workout DMG by 2.20x for 24h."),
    ("Tome of Greater Intellect", "buff_hobby", 2.20, "Multiplies Hobby DMG by 2.20x for 24h."),
    ("Broom of Cleansing", "buff_chore", 2.20, "Multiplies Chore Time DMG by 2.20x for 24h."),
    ("Storm Hammer", "damage_raid", 800.0, "Instantly blast the Raid Boss for 800 DMG."),
    ("Astral Signet", "buff_global", 1.85, "Multiplies ALL DMG by 1.85x for 24h."),
    ("King's Ransom", "gold", 35.00, "Instantly adds $35.00 to your Vault."),
    ("Nova Grenade", "damage_raid", 1000.0, "Instantly deal 1,000 DMG to the Raid Boss."),
    ("Sunfire Aegis", "buff_global", 2.00, "Multiplies ALL DMG by 2.00x for 24h."),
    ("Soul-Stealer Scythe", "damage_solo", 750.0, "Instantly deal 750 DMG to your Solo Boss."),
    ("Ruby Dragon Egg", "gold", 30.00, "Instantly adds $30.00 to your Vault.")
]

# --- HEAVILY BUFFED LEGENDARY TIER (Gold) ---
LEGENDARY_ITEMS = [
    ("Excalibur", "damage_solo", 3000.0, "Instantly obliterate your Solo Boss for 3,000 DMG."),
    ("Dragon's Hoard", "gold", 100.00, "Instantly adds $100.00 to your Vault."),
    ("Aegis of the Titan", "buff_workout", 4.00, "Multiplies Workout DMG by 4.00x for 24h."),
    ("Crown of the Scholar", "buff_hobby", 4.00, "Multiplies Hobby DMG by 4.00x for 24h."),
    ("Chrono-Watch", "buff_chore", 4.00, "Multiplies Chore Time DMG by 4.00x for 24h."),
    ("Hero's Elixir", "damage_raid", 3500.0, "Instantly blast the Raid Boss for 3,500 DMG."),
    ("Archon's Halo", "buff_global", 3.50, "Multiplies ALL DMG by 3.50x for 24h."),
    ("Philosopher's Stone", "gold", 75.00, "Instantly adds $75.00 to your Vault."),
    ("Orb of Annihilation", "damage_raid", 5000.0, "Instantly deal 5,000 DMG to the Raid Boss."),
    ("Divine Rapier", "damage_solo", 2500.0, "Instantly deal 2,500 DMG to your Solo Boss."),
    ("God-King's Treasure", "gold", 90.00, "Instantly adds $90.00 to your Vault."),
    ("Infinity Catalyst", "buff_global", 4.50, "Multiplies ALL DMG by 4.50x for 24h.")
]

# --- ULTRA-RARE MYTHIC TIER (Rainbow - 0.001% Drop) ---
# Format: Name, category, total_charges, description
MYTHIC_ITEMS = [
    ("Sugar Patron's Beacon", "mythic_care_package", 5.0, "5 Uses: Air-drops $50.00 and a guaranteed Legendary item to your partner."),
    ("Titan's Blood Flask", "mythic_limit_break", 3.0, "3 Uses: Drink before an activity to apply a 50x DMG and gold multiplier to that session."),
    ("Chrono-Crystal", "mythic_time_skip", 4.0, "4 Uses: Instantly fulfills your active Weekly Contract for $40.00 and Legendary loot.")
]

# --- Models ---
class User(db.Model):
    __tablename__ = 'users'
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
    current_streak = db.Column(db.Integer, default=0)
    has_killed_today = db.Column(db.Boolean, default=False)
    active_quest_id = db.Column(db.Integer, nullable=True)
    quest_progress = db.Column(db.Float, default=0.0)
    quest_completed = db.Column(db.Boolean, default=False)
    offered_quest_1 = db.Column(db.Integer, nullable=True)
    offered_quest_2 = db.Column(db.Integer, nullable=True)
    offered_quest_3 = db.Column(db.Integer, nullable=True)
    theme_base = db.Column(db.String(50), default='base-obsidian')
    theme_accent = db.Column(db.String(50), default='accent-blue')
    theme_font = db.Column(db.String(50), default='font-standard')
    theme_size = db.Column(db.String(50), default='size-md')
    theme_bg = db.Column(db.String(50), default='bg-solid')
    
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

    raid_dmg_contributed = db.Column(db.Float, default=0.0)

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

class RaidSpoils(db.Model):
    __tablename__ = 'raid_spoils'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    winner_id = db.Column(db.Integer)
    loser_id = db.Column(db.Integer)
    winner_picks_left = db.Column(db.Integer, default=2)
    
    c1_gold = db.Column(db.Float)
    c1_tier = db.Column(db.String(50))
    c1_item = db.Column(db.String(100))
    c1_claimed_by = db.Column(db.Integer, nullable=True)

    c2_gold = db.Column(db.Float)
    c2_tier = db.Column(db.String(50))
    c2_item = db.Column(db.String(100))
    c2_claimed_by = db.Column(db.Integer, nullable=True)

    c3_gold = db.Column(db.Float)
    c3_tier = db.Column(db.String(50))
    c3_item = db.Column(db.String(100))
    c3_claimed_by = db.Column(db.Integer, nullable=True)

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

class GuildHall(db.Model):
    __tablename__ = 'guild_hall'
    id = db.Column(db.Integer, primary_key=True)
    workout_lvl = db.Column(db.Integer, default=1)
    workout_donated = db.Column(db.Float, default=0.0)
    chore_lvl = db.Column(db.Integer, default=1)
    chore_donated = db.Column(db.Float, default=0.0)
    hobby_lvl = db.Column(db.Integer, default=1)
    hobby_donated = db.Column(db.Float, default=0.0)
    gold_lvl = db.Column(db.Integer, default=1)
    gold_donated = db.Column(db.Float, default=0.0)
    luck_lvl = db.Column(db.Integer, default=1)
    luck_donated = db.Column(db.Float, default=0.0)

class DailyShopItem(db.Model):
    __tablename__ = 'daily_shop_item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    multiplier = db.Column(db.Float)
    desc = db.Column(db.String(255))
    rarity = db.Column(db.String(50))
    price = db.Column(db.Float)
    is_sold = db.Column(db.Boolean, default=False)
    date_seeded = db.Column(db.String(20)) # Tracks the day it was generated

class BountyBoard(db.Model):
    __tablename__ = 'bounty_board'
    id = db.Column(db.Integer, primary_key=True)
    poster_id = db.Column(db.Integer, nullable=False)
    poster_name = db.Column(db.String(50), nullable=False)
    task_desc = db.Column(db.String(255), nullable=False)
    gold_reward = db.Column(db.Float, default=0.0)
    item_reward = db.Column(db.String(50), default='None')
    is_active = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=lambda: get_est_now().replace(tzinfo=None))

class TradeOffer(db.Model):
    __tablename__ = 'trade_offer'
    id = db.Column(db.Integer, primary_key=True)
    poster_id = db.Column(db.Integer, nullable=False)
    poster_name = db.Column(db.String(50), nullable=False)
    offered_item_ids = db.Column(db.String(255), nullable=False) # Stores multiple item IDs
    offered_item_names = db.Column(db.String(500), nullable=False) # Stores the formatted list for the HTML
    requested_return = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: get_est_now().replace(tzinfo=None))
    
class TransactionHistory(db.Model):
    __tablename__ = 'transaction_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: get_est_now().replace(tzinfo=None))
    
class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    activity_type = db.Column(db.String(50), nullable=False) # workout, hobby, chore
    minutes = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True) # General notes
    
    # Workout Specifics
    workout_details = db.Column(db.Text, nullable=True) # Sets, weights, routines
    difficulty = db.Column(db.String(50), nullable=True) # RPE or 1-10 scale
    morning_feeling = db.Column(db.String(255), nullable=True) # Recovery notes
    
    timestamp = db.Column(db.DateTime, default=lambda: get_est_now().replace(tzinfo=None))

# --- Discord Notification Helper ---
def notify_discord(message):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        try: requests.post(webhook_url, json={"content": message})
        except: pass

def get_guild_stats():
    g = GuildHall.query.first()
    if not g: return None
    
    # Exponential Math Algorithms
    return {
        "workout_lvl": g.workout_lvl,
        "workout_donated": g.workout_donated,
        "workout_target": 50.0 * (1.5 ** (g.workout_lvl - 1)),
        "workout_cur": 3.5 + ((g.workout_lvl - 1) * 0.1),
        
        "chore_lvl": g.chore_lvl,
        "chore_donated": g.chore_donated,
        "chore_target": 100.0 * (1.5 ** (g.chore_lvl - 1)),
        "chore_cur": 5.0 + ((g.chore_lvl - 1) * 0.1),
        
        "hobby_lvl": g.hobby_lvl,
        "hobby_donated": g.hobby_donated,
        "hobby_target": 150.0 * (1.5 ** (g.hobby_lvl - 1)),
        "hobby_cur": 7.0 + ((g.hobby_lvl - 1) * 0.1),
        
        "gold_lvl": g.gold_lvl,
        "gold_donated": g.gold_donated,
        "gold_target": 250.0 * (1.6 ** (g.gold_lvl - 1)),
        "gold_cur": (g.gold_lvl - 1) * 5.0, # 5% increments
        
        "luck_lvl": g.luck_lvl,
        "luck_donated": g.luck_donated,
        "luck_target": 500.0 * (1.7 ** (g.luck_lvl - 1)),
        "luck_cur": (g.luck_lvl - 1) * 2.0, # 2% increments
    }

def refresh_daily_shop():
    today_str = get_est_now().strftime('%Y-%m-%d')
    existing = DailyShopItem.query.first()
    if existing and existing.date_seeded == today_str: return 
        
    DailyShopItem.query.delete()
    
    shop_common = [i for i in COMMON_ITEMS if i[1] != 'gold']
    shop_uncommon = [i for i in UNCOMMON_ITEMS if i[1] != 'gold']
    shop_rare = [i for i in RARE_ITEMS if i[1] != 'gold']
    shop_epic = [i for i in EPIC_ITEMS if i[1] != 'gold']
    shop_legendary = [i for i in LEGENDARY_ITEMS if i[1] != 'gold']
    
    for _ in range(4):
        roll = random.random() * 100
        if roll <= 8.0:  
            rarity = "Legendary"
            item_data = random.choice(shop_legendary)
            price = round(random.uniform(95.0, 150.0), 2)
        elif roll <= 22.0:
            rarity = "Epic"
            item_data = random.choice(shop_epic)
            price = round(random.uniform(45.0, 75.0), 2)
        elif roll <= 45.0: 
            rarity = "Rare"
            item_data = random.choice(shop_rare)
            price = round(random.uniform(20.0, 35.0), 2)
        elif roll <= 75.0: 
            rarity = "Uncommon"
            item_data = random.choice(shop_uncommon)
            price = round(random.uniform(8.0, 16.0), 2)
        else: 
            rarity = "Common"
            item_data = random.choice(shop_common)
            price = round(random.uniform(2.0, 6.0), 2)
            
        db.session.add(DailyShopItem(
            name=item_data[0], category=item_data[1], multiplier=item_data[2],
            desc=item_data[3], rarity=rarity, price=price, date_seeded=today_str
        ))
    db.session.commit()
    
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
    if not state:
        return

    # Use your new helper function to determine if an event should be active
    est_now = get_est_now()
    event_should_be_active = is_event_active(est_now)

    # If it's time for an event but we don't have one, roll for it
    if event_should_be_active and not state.active_event:
        evt = random.choice(ALL_EVENTS)
        state.active_event, state.event_description = evt
        db.session.commit()
    
    # If the time is up but an event is still active, clear it
    elif not event_should_be_active and state.active_event:
        state.active_event = None
        state.event_description = None
        db.session.commit()

def calculate_90_percent_loot_orb(world_level, event_name=None):
    if event_name == "The Cursed Vault": return round(random.uniform(0.50, 2.00), 2)
    
    # Calculate the 3% compounding multiplier (same math as boss HP)
    multiplier = 1.03 ** (world_level - 1)
    
    # Apply the multiplier to both the floor and the ceiling of the base drops
    if random.random() <= 0.95:
        base_amt = random.uniform(3.00 * multiplier, 4.00 * multiplier)
    else:
        base_amt = random.uniform(2.00 * multiplier, 7.00 * multiplier)
        
    return round(base_amt, 2)

def calculate_raid_boss_orb():
    return round(max(10.0, min(50.0, random.gauss(25.0, 10.0))), 2)

def roll_equipment(event_name=None):
    guild_stats = get_guild_stats()
    luck_bonus = guild_stats['luck_cur'] if guild_stats else 0.0
    
    roll = random.random() * 100.0

    # 1 in 100,000 (0.001%)
    mythic_chance = 0.01 if event_name == "The Cursed Vault" else 0.001
    if roll <= mythic_chance:
        return ("Mythic", random.choice(MYTHIC_ITEMS))

    if event_name == "The Cursed Vault":
        if roll <= (5.0 + luck_bonus): return ("Legendary", random.choice(LEGENDARY_ITEMS))
        elif roll <= (15.0 + luck_bonus): return ("Epic", random.choice(EPIC_ITEMS))
        elif roll <= (30.0 + luck_bonus): return ("Rare", random.choice(RARE_ITEMS))
        elif roll <= (50.0 + luck_bonus): return ("Uncommon", random.choice(UNCOMMON_ITEMS))
        else: return ("Common", random.choice(COMMON_ITEMS))
    else:
        if roll <= (0.8 + (luck_bonus * 0.5)): return ("Legendary", random.choice(LEGENDARY_ITEMS))
        elif roll <= (3.5 + luck_bonus): return ("Epic", random.choice(EPIC_ITEMS))
        elif roll <= (11.5 + luck_bonus): return ("Rare", random.choice(RARE_ITEMS))
        elif roll <= (26.5 + luck_bonus): return ("Uncommon", random.choice(UNCOMMON_ITEMS))
        elif roll <= (50.0 + luck_bonus): return ("Common", random.choice(COMMON_ITEMS))
    return None

def get_item_data_by_name(target_name):
    for loot_pool in [COMMON_ITEMS, UNCOMMON_ITEMS, RARE_ITEMS, EPIC_ITEMS, LEGENDARY_ITEMS, MYTHIC_ITEMS]:
        for item in loot_pool:
            if item[0] == target_name:
                return item[1], item[2], item[3]
    return "unknown", 1.0, "A mysterious artifact."

def roll_raid_equipment():
    roll = random.random() * 100
    if roll <= 10.0: return ("Legendary", random.choice(LEGENDARY_ITEMS))
    elif roll <= 30.0: return ("Epic", random.choice(EPIC_ITEMS))
    elif roll <= 70.0: return ("Rare", random.choice(RARE_ITEMS))
    elif roll <= 90.0: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
    else: return ("Common", random.choice(COMMON_ITEMS))

def get_next_monday_midnight():
    now = get_est_now()
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    target = (now + timedelta(days=days_ahead)).replace(hour=0, minute=1, second=0, microsecond=0)
    # Strip the timezone so Postgres saves the literal 00:01 time
    return target.replace(tzinfo=None)

def check_resets(user):
    now = get_est_now()
    today_str = now.strftime('%Y-%m-%d')
    current_iso_week = now.isocalendar()[1]
    
    if user.current_week is None: user.current_week = current_iso_week
    
    if user.last_active_date != today_str:
        # STREAK BREAKER: If they didn't get a kill yesterday, reset the streak to 0.
        if not user.has_killed_today and user.last_active_date is not None:
            user.current_streak = 0
            
        user.has_killed_today = False
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
        user.active_quest_id = None
        user.quest_progress = 0.0
        user.quest_completed = False
        
        quest_keys = list(WEEKLY_QUESTS.keys())
        choices = random.sample(quest_keys, 3)
        user.offered_quest_1 = choices[0]
        user.offered_quest_2 = choices[1]
        user.offered_quest_3 = choices[2]
        
    db.session.commit()

def handle_boss_death(current_event):
    boss = RaidBoss.query.first()
    boss.is_active = False
    
    users = User.query.all()
    
    # --- 1. THE REGULAR ORB & LOOT (For Everyone) ---
    for u in users:
        raid_drop = calculate_raid_boss_orb()
        raid_loot = ("Legendary", random.choice(LEGENDARY_ITEMS)) if current_event == "Raid Boss Enrage" else roll_raid_equipment()
        r_tier, r_data = raid_loot
        r_name, r_cat, r_mult, r_desc = r_data
        
        db.session.add(UserInventory(user_id=u.id, item_name=r_name, category_target=r_cat, multiplier=r_mult, description=r_desc, rarity=r_tier))
        db.session.add(PendingReward(user_id=u.id, gold_amount=raid_drop, item_name=f"[Raid Boss Kill] [{r_tier}] {r_name}"))
        u.gold_balance += raid_drop
        u.wk_gold += raid_drop

    # --- 2. THE NEW SPOILS OF WAR BONUS (Damage Based) ---
    sorted_users = sorted(users, key=lambda u: u.raid_dmg_contributed, reverse=True)
    winner = sorted_users[0] if len(sorted_users) > 0 else None
    loser = sorted_users[1] if len(sorted_users) > 1 else winner

    # Roll 3 items. Force one to be at least Rare.
    loot1 = roll_raid_equipment()
    loot2 = roll_raid_equipment()
    loot3 = random.choice([
        ("Rare", random.choice(RARE_ITEMS)), 
        ("Legendary", random.choice(LEGENDARY_ITEMS))
    ])
    
    # Shuffle so the guaranteed good item isn't always choice #3
    choices = [loot1, loot2, loot3]
    random.shuffle(choices)
    golds = [round(random.uniform(15.0, 30.0), 2) for _ in range(3)]
    
    # Create the Spoils entry
    if winner and loser:
        spoils = RaidSpoils(
            winner_id=winner.id, loser_id=loser.id,
            c1_tier=choices[0][0], c1_item=choices[0][1][0], c1_gold=golds[0],
            c2_tier=choices[1][0], c2_item=choices[1][1][0], c2_gold=golds[1],
            c3_tier=choices[2][0], c3_item=choices[2][1][0], c3_gold=golds[2]
        )
        db.session.add(spoils)

    # Reset damage trackers for the next boss
    for u in users:
        u.raid_dmg_contributed = 0.0

    notify_discord(f"🌋 **{boss.name.upper()} DESTROYED!** Both players received a Raid Boss Orb! {winner.username} dealt the most damage and gets first pick of the Bonus Loot Chests!")
    db.session.commit()
# -----------------------------------

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
    # Force the database connection to reset if it's currently stuck in an error state
    try:
        db.session.rollback()
    except Exception:
        pass

    # Now that the transaction is clean, proceed with your queries
    user_id = session.get('user_id')
    current_user = User.query.get(user_id) if user_id else None
    boss = RaidBoss.query.first()
    players = User.query.all()
    server_state = ServerState.query.first()
    
    if not server_state:
        server_state = ServerState()
        db.session.add(server_state)
        db.session.commit()
        
    manage_world_events()
    if current_user: check_resets(current_user)

    est_now = get_est_now()
    event_active_now = is_event_active(est_now)
    
   # --- WEEKLY RAID BOSS RESET LOGIC ---
    if boss:
        # Failsafe for older DBs to ensure the timer works
        if boss.next_spawn_date is None:
            # Strip the timezone here too
            boss.next_spawn_date = (get_est_now() - timedelta(days=1)).replace(tzinfo=None)
            db.session.commit()
            
        spawn_time = boss.next_spawn_date
        if spawn_time.tzinfo is None:
            spawn_time = spawn_time.replace(tzinfo=ZoneInfo("America/New_York"))

# If it's time for the Monday reset (or past due)
        if get_est_now() >= spawn_time:
            was_defeated = (boss.current_hp <= 0 or not boss.is_active)
            
            # 1. Roll the new boss name exactly ONCE
            new_boss_name = random.choice(RAID_BOSSES)
            
            if was_defeated:
                boss.world_level += 1
                boss.max_hp = round(boss.max_hp * 1.03, 1)
                
                # Apply 3% boost to all players' solo monsters
                for player in players:
                    player.solo_monster_max = round(player.solo_monster_max * 1.03, 1)
                    if player.solo_monster_hp > player.solo_monster_max:
                        player.solo_monster_hp = player.solo_monster_max
                        
                # 2. Pass the saved variable to the webhook
                notify_discord(f"🔄 **NEW WEEK!** You defeated the previous boss. The world grows stronger! A new **{new_boss_name}** (Lvl {boss.world_level}) has arrived!")
            else:
                # 2. Pass the saved variable to the webhook
                notify_discord(f"🔄 **NEW WEEK!** The previous boss fled before you could defeat it! The World Level remains at {boss.world_level}. A new **{new_boss_name}** has appeared!")
            
            # 3. Save that exact same name to the database and reset the timer
            boss.name = new_boss_name
            boss.current_hp = boss.max_hp * 2.0 if event_active_now and server_state.active_event == "Raid Boss Enrage" else boss.max_hp
            boss.is_active = True
            boss.next_spawn_date = get_next_monday_midnight()
            db.session.commit()
            

    pending_rewards = PendingReward.query.filter_by(user_id=current_user.id).all() if current_user else []
    inventory = UserInventory.query.filter_by(user_id=current_user.id).all() if current_user else []
    
    transactions = TransactionHistory.query.filter_by(user_id=current_user.id).order_by(TransactionHistory.timestamp.desc()).limit(15).all() if current_user else []

    activity_logs = ActivityLog.query.filter_by(user_id=current_user.id).order_by(ActivityLog.timestamp.desc()).limit(20).all() if current_user else []

    if inventory:
        for item in inventory:
            if item.is_active and item.expires_at and get_est_now() > item.expires_at.replace(tzinfo=ZoneInfo("America/New_York")):
                db.session.delete(item)
        db.session.commit()

    solo_img = get_monster_image(current_user.solo_monster_name) if current_user else None
    raid_img = get_monster_image(boss.name) if boss else None

    if current_user and current_user.has_pet and current_user.pet_xp >= 100:
        # Loop handles multiple level-ups if an item pushes XP past 200, 300, etc.
        while current_user.pet_xp >= 100:
            current_user.pet_level += 1
            current_user.pet_xp -= 100
        db.session.commit()

    active_spoils = RaidSpoils.query.filter_by(is_active=True).first()

    refresh_daily_shop()
    daily_shop = DailyShopItem.query.all()
    guild_stats = get_guild_stats()

    # Calculate daily hustle minutes for the Rebate (Must be a SINGLE unbroken session of 120+)
    today_start = get_est_now().replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    alaina_user = User.query.filter_by(username='Alaina').first()
    matthew_user = User.query.filter_by(username='Matthew').first()
    
    # Use db.func.max to find their longest single logged session today
    alaina_max = db.session.query(db.func.max(ActivityLog.minutes)).filter(ActivityLog.user_id == alaina_user.id, ActivityLog.timestamp >= today_start).scalar() or 0.0 if alaina_user else 0.0
    matthew_max = db.session.query(db.func.max(ActivityLog.minutes)).filter(ActivityLog.user_id == matthew_user.id, ActivityLog.timestamp >= today_start).scalar() or 0.0 if matthew_user else 0.0
    
    alaina_hustled = alaina_max >= 120.0
    matthew_hustled = matthew_max >= 120.0
    
    active_bounties = BountyBoard.query.filter_by(is_active=True).all()
    active_trades = TradeOffer.query.order_by(TradeOffer.timestamp.desc()).all()
    
    # Recover the escrowed item details so the HTML can display them properly
    for bounty in active_bounties:
        if bounty.item_reward != 'None':
            escrow_item = UserInventory.query.get(int(bounty.item_reward))
            if escrow_item:
                bounty.display_item_name = escrow_item.item_name
                bounty.display_item_rarity = escrow_item.rarity
            else:
                bounty.display_item_name = None
    
    # Calculate how many active bounties were posted by the OTHER player
    partner_bounty_count = sum(1 for b in active_bounties if current_user and b.poster_id != current_user.id)

    # --- LIVE DROP RATE & GOLD CALCULATOR FOR UI ---
    world_mult = 1.03 ** (boss.world_level - 1) if boss else 1.0
    luck = guild_stats['luck_cur'] if guild_stats else 0.0
    gold_mult = 1.0 + (guild_stats['gold_cur'] / 100.0) if guild_stats else 1.0
    
    is_cursed = (server_state.active_event == "The Cursed Vault" and event_active_now)
    is_goblin = (server_state.active_event == "Goblin Merchant's Crash" and event_active_now)
    is_mimic = (server_state.active_event == "Treasure Mimic Infestation" and event_active_now)
    
    # 1. Calculate Solo Gold Ranges
    if is_cursed:
        solo_gold_min, solo_gold_max = 0.50 * gold_mult, 2.00 * gold_mult
    elif is_mimic:
        solo_gold_min = solo_gold_max = 10.00 * gold_mult
    else:
        solo_gold_min = 2.0 * world_mult * gold_mult
        solo_gold_max = 7.0 * world_mult * gold_mult
        if is_goblin:
            solo_gold_min *= 2.0; solo_gold_max *= 2.0
            
    # 2. Calculate Solo Drop Percentages based on active luck/events
    mythic_pct = 0.01 if is_cursed else 0.001
    leg_raw = (5.0 + luck) if is_cursed else (0.8 + (luck * 0.5))
    epic_raw = (15.0 + luck) if is_cursed else (3.5 + luck)
    rare_raw = (30.0 + luck) if is_cursed else (11.5 + luck)
    unc_raw = (50.0 + luck) if is_cursed else (26.5 + luck)
    
    drop_info = {
        'solo_gold': f"${solo_gold_min:.2f} - ${solo_gold_max:.2f}",
        'raid_gold': "$10.00 - $50.00",
        'solo_mythic': f"{mythic_pct:.3f}%",
        'solo_leg': f"{max(0, leg_raw - mythic_pct):.2f}%",
        'solo_epic': f"{max(0, epic_raw - leg_raw):.2f}%",
        'solo_rare': f"{max(0, rare_raw - epic_raw):.2f}%",
        'solo_unc': f"{max(0, unc_raw - rare_raw):.2f}%",
        'solo_com': f"{max(0, 100.0 - unc_raw):.2f}%"
    }
    
    return render_template('index.html', current_user=current_user, players=players, boss=boss, pending_rewards=pending_rewards, inventory=inventory, solo_img=solo_img, raid_img=raid_img, server_state=server_state, transactions=transactions, activity_logs=activity_logs, WEEKLY_QUESTS=WEEKLY_QUESTS, event_active_now=event_active_now, active_spoils=active_spoils, daily_shop=daily_shop, guild_stats=guild_stats, alaina_hustled=alaina_hustled, matthew_hustled=matthew_hustled, active_bounties=active_bounties, partner_bounty_count=partner_bounty_count, active_trades=active_trades, drop_info=drop_info, COMMON_ITEMS=COMMON_ITEMS, UNCOMMON_ITEMS=UNCOMMON_ITEMS, RARE_ITEMS=RARE_ITEMS, EPIC_ITEMS=EPIC_ITEMS, LEGENDARY_ITEMS=LEGENDARY_ITEMS, MYTHIC_ITEMS=MYTHIC_ITEMS)

@app.route('/select_quest/<int:q_id>', methods=['POST'])
def select_quest(q_id):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None) # Clear the dead session cookie
        return redirect('/')
    if not user.active_quest_id:
        user.active_quest_id = q_id
        db.session.commit()
    return redirect('/')
    
@app.route('/manual_login/<username>')
def manual_login(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.last_known_ip = get_client_ip()
        db.session.commit()
        session['user_id'] = user.id
    return redirect('/')

@app.route('/post_bounty', methods=['POST'])
def post_bounty():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    task_desc = request.form.get('task_desc')
    item_reward_id = request.form.get('item_reward', 'None')
    try: gold_reward = float(request.form.get('gold_reward', 0))
    except: gold_reward = 0.0
    
    if user.gold_balance >= gold_reward and task_desc:
        user.gold_balance -= gold_reward  # Hold gold in escrow
        
        # Hold item in escrow (change owner to -1 so it leaves their Vault)
        item_id_to_store = 'None'
        if item_reward_id != 'None':
            item = UserInventory.query.filter_by(id=int(item_reward_id), user_id=user.id).first()
            if item and not item.is_active:
                item.user_id = -1 
                item_id_to_store = str(item.id)
                
        new_bounty = BountyBoard(
            poster_id=user.id, poster_name=user.username,
            task_desc=task_desc, gold_reward=gold_reward, item_reward=item_id_to_store
        )
        db.session.add(new_bounty)
        db.session.add(TransactionHistory(user_id=user.id, amount=gold_reward, reason=f"Bounty Escrow: {task_desc}"))
        db.session.commit()
        
    return redirect('/')

@app.route('/interact_bounty', methods=['POST'])
def interact_bounty():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    action = request.form.get('action_type')
    bounty_id = request.form.get('bounty_id')
    bounty = BountyBoard.query.get(bounty_id)
    
    if bounty and bounty.is_active:
        if action == 'cancel' and bounty.poster_id == user.id:
            # Refund escrowed gold
            user.gold_balance += bounty.gold_reward
            
            # Refund escrowed item back to the original poster
            if bounty.item_reward != 'None':
                item = UserInventory.query.get(int(bounty.item_reward))
                if item: item.user_id = user.id
                
            bounty.is_active = False
            db.session.add(TransactionHistory(user_id=user.id, amount=bounty.gold_reward, reason=f"Bounty Refund: {bounty.task_desc}"))
            
        elif action == 'claim' and bounty.poster_id != user.id:
            # Payout gold to the fulfiller
            user.gold_balance += bounty.gold_reward
            user.wk_gold += bounty.gold_reward
            
            # Transfer escrowed item to the fulfiller
            if bounty.item_reward != 'None':
                item = UserInventory.query.get(int(bounty.item_reward))
                if item: item.user_id = user.id
                
            bounty.is_active = False
            
        db.session.commit()
    return redirect('/')

@app.route('/post_trade', methods=['POST'])
def post_trade():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    # getlist() captures ALL the checkboxes you ticked!
    offered_ids = request.form.getlist('offered_items')
    requested_return = request.form.get('requested_return')
    
    if not offered_ids or not requested_return:
        return redirect('/')
        
    offered_names = []
    valid_ids = []
    
    # Send all checked items to escrow
    for item_id in offered_ids:
        item = UserInventory.query.filter_by(id=int(item_id), user_id=user.id).first()
        if item and not item.is_active:
            item.user_id = -1 
            offered_names.append(f"[{item.rarity}] {item.item_name}")
            valid_ids.append(str(item.id))
            
    if valid_ids:
        new_trade = TradeOffer(
            poster_id=user.id,
            poster_name=user.username,
            offered_item_ids=",".join(valid_ids),
            offered_item_names="\n".join(offered_names), # Uses line breaks for the HTML
            requested_return=requested_return
        )
        db.session.add(new_trade)
        db.session.commit()
        
    return redirect('/')

@app.route('/interact_trade', methods=['POST'])
def interact_trade():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    action = request.form.get('action_type')
    trade_id = request.form.get('trade_id')
    trade = TradeOffer.query.get(trade_id)
    
    if trade:
        item_ids = trade.offered_item_ids.split(',')
        
        if action == 'cancel' and trade.poster_id == user.id:
            # Return all escrowed items back to the poster
            for i_id in item_ids:
                item = UserInventory.query.get(int(i_id))
                if item: item.user_id = user.id
            db.session.delete(trade)
            
        elif action == 'accept' and trade.poster_id != user.id:
            given_item_id = request.form.get('given_item_id')
            given_item = UserInventory.query.filter_by(id=int(given_item_id), user_id=user.id).first()
            
            if given_item and not given_item.is_active:
                # 1. Give the partner's item to the poster
                given_item.user_id = trade.poster_id
                
                # 2. Give the poster's escrowed items to the partner
                for i_id in item_ids:
                    item = UserInventory.query.get(int(i_id))
                    if item: item.user_id = user.id
                    
                db.session.delete(trade)
                
        db.session.commit()
    return redirect('/')
    
@app.route('/dismiss_report', methods=['POST'])
def dismiss_report():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.show_weekly_report = False
        db.session.commit()
    return redirect('/')

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'user_id' not in session: return {"status": "error"}, 401
    
    user = User.query.get(session['user_id'])
    data = request.json
    
    if user and data:
        # Update the database with whatever classes the body currently has
        user.theme_base = data.get('base', 'base-obsidian')
        user.theme_accent = data.get('accent', 'accent-blue')
        user.theme_font = data.get('font', 'font-standard')
        user.theme_size = data.get('size', 'size-md')
        user.theme_bg = data.get('bg', 'bg-solid')
        
        db.session.commit()
        return {"status": "success"}
    return {"status": "error"}, 400

@app.route('/stage_activity', methods=['POST'])
def stage_activity():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    boss = RaidBoss.query.first()
    state = ServerState.query.first()
    check_resets(user)
    
    est_now = get_est_now()
    current_event = state.active_event if is_event_active(est_now) else None
    
    act_type = request.form.get('type')
    if 'chores' in request.form: act_type = 'chore'
    try: minutes = float(request.form.get('minutes', 0))
    except: minutes = 0.0
    desc = request.form.get('description', '')
    w_details = request.form.get('workout_details', '')
    diff = request.form.get('difficulty', '')
    feeling = request.form.get('morning_feeling', '')
    
    if minutes > 0:
        new_log = ActivityLog(
            user_id=user.id,
            activity_type=act_type,
            minutes=minutes,
            description=desc,
            workout_details=w_details if act_type == 'workout' else None,
            difficulty=diff if act_type == 'workout' else None,
            morning_feeling=feeling if act_type == 'workout' else None
        )
        db.session.add(new_log)
                       
    if not user.has_pet and minutes > 0:
        user.egg_minutes += minutes
        if user.egg_minutes >= 100.0:
            user.has_pet = True

    guild_stats = get_guild_stats()
    workout_mult = guild_stats['workout_cur']
    hobby_mult = guild_stats['hobby_cur']
    chore_mult = guild_stats['chore_cur']
    
    active_buffs = UserInventory.query.filter_by(user_id=user.id, is_active=True).all()
    for buff in active_buffs:
        if buff.category_target == 'buff_workout': workout_mult *= buff.multiplier
        elif buff.category_target == 'buff_hobby': hobby_mult *= buff.multiplier
        elif buff.category_target == 'buff_chore': chore_mult *= buff.multiplier
        elif buff.category_target == 'buff_global': 
            workout_mult *= buff.multiplier
            hobby_mult *= buff.multiplier
            chore_mult *= buff.multiplier

    if current_event == "Frenzy of the Warrior":
        workout_mult *= 3.0
        hobby_mult *= 0.5
    elif current_event == "Scholar’s Blessing":
        hobby_mult *= 3.0
        workout_mult *= 0.5
    
    if current_event == "The Early Bird Wormhole" and get_est_now().hour < 10:
        workout_mult *= 1.5; hobby_mult *= 1.5; chore_mult *= 1.5

    pet_multiplier = 1.0 + (user.pet_level * 0.01) if user.has_pet else 1.0
    workout_mult *= pet_multiplier; hobby_mult *= pet_multiplier; chore_mult *= pet_multiplier

    base_dmg = 0
    if act_type == 'workout': base_dmg = minutes * workout_mult; user.wk_workout += minutes
    elif act_type == 'hobby': base_dmg = minutes * hobby_mult; user.wk_hobby += minutes
    elif act_type == 'chore': base_dmg = minutes * chore_mult; user.wk_chore += minutes
    # Check for Limit Break (50x)
    limit_break = UserInventory.query.filter_by(user_id=user.id, category_target="buff_limit_break").first()
    if limit_break:
        base_dmg *= 50.0
        db.session.delete(limit_break) # Consumed on strike
    
    # QUEST PROGRESSION
    if user.active_quest_id and not user.quest_completed:
        quest = WEEKLY_QUESTS.get(user.active_quest_id)
        if quest and act_type == quest["type"]:
            user.quest_progress += minutes
            if user.quest_progress >= quest["target"]:
                user.quest_completed = True
                user.gold_balance += quest["gold"]
                user.wk_gold += quest["gold"]
                
                # Grant the exact tier promised in the quest
                loot_pool = LEGENDARY_ITEMS if quest["tier"] == "Legendary" else RARE_ITEMS
                q_name, q_cat, q_mult, q_desc = random.choice(loot_pool)
                
                db.session.add(UserInventory(user_id=user.id, item_name=q_name, category_target=q_cat, multiplier=q_mult, description=q_desc, rarity=quest["tier"]))
                db.session.add(PendingReward(user_id=user.id, gold_amount=quest["gold"], item_name=f"[Contract Fulfilled!] [{quest['tier']}] {q_name}"))
                
    if 'chores' in request.form and not user.chores_completed:
        user.chores_completed = True
        base_dmg += 300.0 if current_event == "The Maid's Crusade" else 50.0

    if current_event == "Gambler’s Fallacy" and int(minutes) == 7:
        loot = roll_equipment(current_event)
        if not loot:
            loot = ("Common", random.choice(COMMON_ITEMS))
            
        tier, item_data = loot
        i_name, i_cat, i_mult, i_desc = item_data
        db.session.add(UserInventory(user_id=user.id, item_name=i_name, category_target=i_cat, multiplier=i_mult, description=i_desc, rarity=tier))
        db.session.add(PendingReward(user_id=user.id, gold_amount=0.0, item_name=f"[{tier}] {i_name} (Lucky 7s!)"))
        
        # Save the item to the database immediately so it isn't lost if damage is 0!
        db.session.commit()
        
    if base_dmg <= 0: return redirect('/')

    if current_event == "Synergy Link" and state.last_logged_activity_type == act_type and state.last_logged_user_id != user.id:
        if boss.is_active: boss.current_hp -= 500.0

    state.last_logged_activity_type = act_type
    state.last_logged_user_id = user.id

    if current_event == "Critical Strike Weekend" and random.random() <= 0.25:
        base_dmg += user.solo_monster_hp # Instantly kills the solo boss without deleting overflow damage!

    solo_dmg = base_dmg
    raid_dmg = 0
    kill_cap = 10 if current_event == "Colosseum Draft" else 3

    solo_dmg = base_dmg
    raid_dmg = 0
    kill_cap = 3 # Lock the cap to 3 permanently

    while solo_dmg > 0:
        # 1. DIVERT TO RAID BOSS IF ALIVE AND CAP IS MET
        if boss and boss.is_active and user.bosses_killed_today >= kill_cap:
            if current_event != "Titan’s Shield":
                raid_dmg += solo_dmg
            solo_dmg = 0  
            break         

        # 2. NECROMANCER FIX: Only 1 HP if they haven't hit the cap
        if current_event == "Necromancer’s Curse" and get_est_now().weekday() == 6 and user.bosses_killed_today < kill_cap:
            target_hp = 1.0
        else:
            target_hp = user.solo_monster_hp
        
        if solo_dmg >= target_hp:
            if not user.has_killed_today:
                user.has_killed_today = True
                user.current_streak += 1
                
                if user.current_streak in [3, 7, 14, 30, 60, 100]:
                    streak_gold = user.current_streak * 2.0 
                    s_name, s_cat, s_mult, s_desc = random.choice(LEGENDARY_ITEMS if user.current_streak >= 14 else RARE_ITEMS)
                    db.session.add(UserInventory(user_id=user.id, item_name=s_name, category_target=s_cat, multiplier=s_mult, description=s_desc, rarity="Legendary" if user.current_streak >= 14 else "Rare"))
                    db.session.add(PendingReward(user_id=user.id, gold_amount=streak_gold, item_name=f"[{user.current_streak}-Day Streak Chest!] {s_name}"))

            solo_dmg -= target_hp
            user.bosses_killed_today += 1
            user.wk_bosses += 1
            
            gold_drop = calculate_90_percent_loot_orb(boss.world_level, current_event)
            guild_stats = get_guild_stats()
            bonus_multiplier = 1.0 + (guild_stats['gold_cur'] / 100.0)
            gold_drop = round(gold_drop * bonus_multiplier, 2)
            
            if current_event == "Goblin Merchant's Crash": gold_drop *= 2.0
            if current_event == "Treasure Mimic Infestation": gold_drop = 10.00
            if current_event == "Colosseum Champion" and user.bosses_killed_today <= 3:
                gold_drop *= 5.0
            # -------------------------------------

            user.gold_balance += gold_drop; user.wk_gold += gold_drop
            
            if current_event != "Goblin Merchant's Crash":
                loot = roll_equipment(current_event)
                if loot:
                    tier, item_data = loot
                    i_name, i_cat, i_mult, i_desc = item_data
                    db.session.add(UserInventory(user_id=user.id, item_name=i_name, category_target=i_cat, multiplier=i_mult, description=i_desc, rarity=tier))
                    db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=f"[{tier}] {i_name}"))
                else:
                    db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))
                    
                if current_event == "Meteor Shower":
                    loot2 = roll_equipment(current_event)
                    if loot2:
                        tier2, item_data2 = loot2
                        i_name2, i_cat2, i_mult2, i_desc2 = item_data2
                        db.session.add(UserInventory(user_id=user.id, item_name=i_name2, category_target=i_cat2, multiplier=i_mult2, description=i_desc2, rarity=tier2))
                        db.session.add(PendingReward(user_id=user.id, gold_amount=0.0, item_name=f"[{tier2}] {i_name2} (Bonus!)"))
            else:
                db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))

            scaled_hp = round(300.0 * (1.03 ** (boss.world_level - 1)), 1)
            user.solo_monster_max = 50.0 if current_event == "Slime Outbreak" else scaled_hp
            user.solo_monster_hp = user.solo_monster_max
            user.solo_monster_name = "Slime" if current_event == "Slime Outbreak" else random.choice(SOLO_ENEMIES)
        else:
            user.solo_monster_hp -= solo_dmg
            solo_dmg = 0

    if solo_dmg > 0 and current_event != "Titan’s Shield":
        raid_dmg += solo_dmg

    if boss.is_active and raid_dmg > 0:
        if current_event != "The Shadow Clone":
            # 1. Cap the damage to whatever health the boss actually has left
            actual_dmg = min(raid_dmg, boss.current_hp)
            overflow = raid_dmg - actual_dmg
            
            # 2. Apply ONLY the real damage to the boss and your stats
            boss.current_hp -= actual_dmg
            user.raid_dmg_contributed += actual_dmg
            
            # 3. Dump the remaining overflow into your solo monster
            if overflow > 0:
                user.solo_monster_hp -= overflow
                
                while user.solo_monster_hp <= 0:
                    # 1. Update stats and streaks
                    user.bosses_killed_today += 1
                    user.wk_bosses += 1
                    if not user.has_killed_today:
                        user.has_killed_today = True
                        user.current_streak += 1
                    
                    # 2. Grant Gold (10.00 if Mimic event, otherwise normal calc)
                    gold_drop = 10.00 if current_event == "Treasure Mimic Infestation" else calculate_90_percent_loot_orb(boss.world_level, current_event)
                    if current_event == "Goblin Merchant's Crash": gold_drop *= 2.0
                    user.gold_balance += gold_drop
                    user.wk_gold += gold_drop
                    
                    # 3. Roll for Items (Unless Goblin Merchant event)
                    if current_event != "Goblin Merchant's Crash":
                        loot = roll_equipment(current_event)
                        if loot:
                            tier, item_data = loot
                            db.session.add(UserInventory(user_id=user.id, item_name=item_data[0], category_target=item_data[1], multiplier=item_data[2], description=item_data[3], rarity=tier))
                            db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=f"[{tier}] {item_data[0]}"))
                        else:
                            db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))
                    else:
                        db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=None))

                    # 4. Reset Solo Monster HP for the next potential loop
                    user.solo_monster_hp += user.solo_monster_max
                    
        # Boss dies mid-week. It stays dead until Monday reset.
        if boss.current_hp <= 0:
            handle_boss_death(current_event)
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

@app.route('/claim_spoil/<int:choice_num>', methods=['POST'])
def claim_spoil(choice_num):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    spoils = RaidSpoils.query.filter_by(is_active=True).first()
    
    if not spoils: return redirect('/')
    
    # Enforce Turn Order: Loser cannot pick while winner still has picks left
    if user.id == spoils.loser_id and spoils.winner_picks_left > 0:
        return redirect('/')
        
    # Map the choice to the correct database column and recover missing data
    if choice_num == 1 and spoils.c1_claimed_by is None:
        spoils.c1_claimed_by = user.id
        cat, mult, desc = get_item_data_by_name(spoils.c1_item)
        db.session.add(UserInventory(user_id=user.id, item_name=spoils.c1_item, category_target=cat, multiplier=mult, description=desc, rarity=spoils.c1_tier))
        db.session.add(PendingReward(user_id=user.id, gold_amount=spoils.c1_gold, item_name=f"[{spoils.c1_tier}] {spoils.c1_item}"))
        
        user.gold_balance += spoils.c1_gold
        user.wk_gold += spoils.c1_gold
        
    elif choice_num == 2 and spoils.c2_claimed_by is None:
        spoils.c2_claimed_by = user.id
        cat, mult, desc = get_item_data_by_name(spoils.c2_item)
        db.session.add(UserInventory(user_id=user.id, item_name=spoils.c2_item, category_target=cat, multiplier=mult, description=desc, rarity=spoils.c2_tier))
        db.session.add(PendingReward(user_id=user.id, gold_amount=spoils.c2_gold, item_name=f"[{spoils.c2_tier}] {spoils.c2_item}"))
                
        user.gold_balance += spoils.c2_gold
        user.wk_gold += spoils.c2_gold
        
    elif choice_num == 3 and spoils.c3_claimed_by is None:
        spoils.c3_claimed_by = user.id
        cat, mult, desc = get_item_data_by_name(spoils.c3_item)
        db.session.add(UserInventory(user_id=user.id, item_name=spoils.c3_item, category_target=cat, multiplier=mult, description=desc, rarity=spoils.c3_tier))
        db.session.add(PendingReward(user_id=user.id, gold_amount=spoils.c3_gold, item_name=f"[{spoils.c3_tier}] {spoils.c3_item}"))
                
        user.gold_balance += spoils.c3_gold
        user.wk_gold += spoils.c3_gold
        
    else:
        return redirect('/')

    # Deduct winner pick count
    if user.id == spoils.winner_id:
        spoils.winner_picks_left -= 1
        
    # Close event if all three chests are claimed
    if spoils.c1_claimed_by and spoils.c2_claimed_by and spoils.c3_claimed_by:
        spoils.is_active = False

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

    est_now = get_est_now()
    current_event = state.active_event if is_event_active(est_now) else None
    
    if current_event == "Alchemist’s Bazaar":
        user.gold_balance += 2.00; user.wk_gold += 2.00

    # --- MYTHIC MULTI-USE HANDLERS ---
    if item.rarity == "Mythic":
        # 1. Sugar Care Package
        if item.category_target == 'mythic_care_package':
            partner = User.query.filter(User.id != user.id).first()
            if partner:
                partner.gold_balance += 50.00
                partner.wk_gold += 50.00
                leg_choice = random.choice(LEGENDARY_ITEMS)
                db.session.add(UserInventory(user_id=partner.id, item_name=leg_choice[0], category_target=leg_choice[1], multiplier=leg_choice[2], description=leg_choice[3], rarity="Legendary"))
                db.session.add(PendingReward(user_id=partner.id, gold_amount=50.00, item_name=f"[Partner Air-Drop!] [Legendary] {leg_choice[0]}"))
                notify_discord(f"🎁 **CARE PACKAGE DELIVERED!** {user.username} activated their Mythic Beacon! {partner.username} received $50.00 and a Legendary item!")

        # 2. Limit Break Prep
        elif item.category_target == 'mythic_limit_break':
            db.session.add(UserInventory(user_id=user.id, item_name="⚡ LIMIT BREAK ACTIVE (50x)", category_target="buff_limit_break", multiplier=50.0, description="Your next activity deals 50x DMG and yields massive rewards.", rarity="Mythic", is_active=True))
            notify_discord(f"⚡ **LIMIT BREAK UNLEASHED!** {user.username} drank the Titan's Blood Flask! Their next activity will hit with 50x force!")

        # 3. Time Skip
        elif item.category_target == 'mythic_time_skip':
            if user.active_quest_id and not user.quest_completed:
                quest = WEEKLY_QUESTS.get(user.active_quest_id)
                user.quest_progress = quest["target"]
                user.quest_completed = True
                user.gold_balance += quest["gold"]
                user.wk_gold += quest["gold"]
                loot_pool = LEGENDARY_ITEMS if quest["tier"] == "Legendary" else RARE_ITEMS
                q_choice = random.choice(loot_pool)
                db.session.add(UserInventory(user_id=user.id, item_name=q_choice[0], category_target=q_choice[1], multiplier=q_choice[2], description=q_choice[3], rarity=quest["tier"]))
                db.session.add(PendingReward(user_id=user.id, gold_amount=quest["gold"], item_name=f"[Chrono-Skip Contract!] [{quest['tier']}] {q_choice[0]}"))
                notify_discord(f"⏳ **CHRONO-SKIP!** {user.username} used a Chrono-Crystal to instantly fulfill their contract!")

        # Deduct a charge from multiplier
        item.multiplier -= 1.0
        if item.multiplier <= 0:
            db.session.delete(item)
        db.session.commit()
        return redirect('/')

    # --- STANDARD ITEM HANDLERS ---
    if item.category_target.startswith('buff'):
        item.is_active = True
        duration = 72 if current_event == "Broken Seal" else 24
        item.expires_at = get_est_now() + timedelta(hours=duration)
    elif item.category_target == 'damage_raid' or current_event == "Titan’s Shield":
        boss = RaidBoss.query.first()
        if boss.is_active: 
            boss.current_hp -= item.multiplier
            user.raid_dmg_contributed += item.multiplier
            if boss.current_hp <= 0:
                handle_boss_death(current_event)
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

@app.route('/donate_guild', methods=['POST'])
def donate_guild():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    amount = float(request.form.get('amount', 0))
    u_type = request.form.get('upgrade_type')
    
    if user.gold_balance >= amount and amount > 0:
        user.gold_balance -= amount
        guild = GuildHall.query.first()
        stats = get_guild_stats()
        
        # Route to the correct attribute and check for level-ups
        if u_type == 'workout':
            guild.workout_donated += amount
            if guild.workout_donated >= stats['workout_target']:
                guild.workout_donated -= stats['workout_target']
                guild.workout_lvl += 1
        elif u_type == 'chore':
            guild.chore_donated += amount
            if guild.chore_donated >= stats['chore_target']:
                guild.chore_donated -= stats['chore_target']
                guild.chore_lvl += 1
        elif u_type == 'hobby':
            guild.hobby_donated += amount
            if guild.hobby_donated >= stats['hobby_target']:
                guild.hobby_donated -= stats['hobby_target']
                guild.hobby_lvl += 1
        elif u_type == 'gold':
            guild.gold_donated += amount
            if guild.gold_donated >= stats['gold_target']:
                guild.gold_donated -= stats['gold_target']
                guild.gold_lvl += 1
        elif u_type == 'luck':
            guild.luck_donated += amount
            if guild.luck_donated >= stats['luck_target']:
                guild.luck_donated -= stats['luck_target']
                guild.luck_lvl += 1
                
        db.session.add(TransactionHistory(user_id=user.id, amount=amount, reason=f"Guild Hall Donation: {u_type.capitalize()}"))
        db.session.commit()
        
    return redirect('/')

@app.route('/buy_shop_item', methods=['POST'])
def buy_shop_item():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    item_id = request.form.get('shop_item_id')
    
    shop_item = DailyShopItem.query.get(item_id)
    if shop_item and not shop_item.is_sold and user.gold_balance >= shop_item.price:
        user.gold_balance -= shop_item.price
        shop_item.is_sold = True
        
        db.session.add(UserInventory(
            user_id=user.id, item_name=shop_item.name, category_target=shop_item.category,
            multiplier=shop_item.multiplier, description=shop_item.desc, rarity=shop_item.rarity
        ))
        db.session.add(TransactionHistory(user_id=user.id, amount=shop_item.price, reason=f"Snivels Shop: {shop_item.name}"))
        db.session.commit()
        
    return redirect('/')
    
def initialize_database():
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
        if not ServerState.query.first():
            db.session.add(ServerState())
        if not TradeOffer.query.first(): pass
        if not GuildHall.query.first():
            db.session.add(GuildHall())
        if not User.query.first():
            db.session.add(User(username='Alaina', solo_monster_name='Slime'))
            db.session.add(User(username='Matthew', solo_monster_name='Slime'))
            db.session.add(RaidBoss(name='Dragon'))
        db.session.commit()
        
initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
