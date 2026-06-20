import os
import requests
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

app = Flask(__name__)
app.secret_key = 'rpg_accountability_secret_chain'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

SOLO_ENEMIES = [
    "Goblin", "Skeleton", "Slime", "Orc", "Troll", "Kobold", "Harpy", "Imp", "Ghoul", "Zombie",
    "Bandit", "Cultist", "Sprite", "Mimic", "Spider", "Rat", "Wolf", "Bat", "Hobgoblin", "Wraith"
]

RAID_BOSSES = [
    "Dragon", "Behemoth", "Kraken", "Leviathan", "Hydra", "Lich", "Titan", "Colossus", "Balrog", "Chimera",
    "Wyrm", "Tarrasque", "Cyclops", "Sphinx", "Roc", "Wendigo", "Dullahan", "Juggernaut", "Beholder"
]

# --- THE 80-ITEM LOOT TABLE ---
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

class RaidBoss(db.Model):
    __tablename__ = 'raid_boss'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Dragon")
    max_hp = db.Column(db.Float, default=1200.0)
    current_hp = db.Column(db.Float, default=1200.0)
    world_level = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    next_spawn_date = db.Column(db.DateTime, nullable=True)

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

# --- Helpers ---
def notify_discord(message):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        try: requests.post(webhook_url, json={"content": message})
        except: pass

def calculate_90_percent_loot_orb(world_level):
    level_bonus = (world_level - 1) * 0.50
    if random.random() <= 0.90: return round(random.uniform(3.00 + level_bonus, 4.00 + level_bonus), 2)
    else:
        if random.random() > 0.5: return round(random.uniform(1.00, 2.99 + level_bonus), 2)
        return round(random.uniform(4.01 + level_bonus, 7.00 + level_bonus), 2)

def calculate_raid_boss_orb():
    return round(max(10.0, min(50.0, random.gauss(25.0, 10.0))), 2)

def roll_equipment():
    roll = random.random() * 100
    if roll <= 0.5: return ("Legendary", random.choice(LEGENDARY_ITEMS))
    elif roll <= 3.5: return ("Rare", random.choice(RARE_ITEMS))
    elif roll <= 11.5: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
    elif roll <= 26.5: return ("Common", random.choice(COMMON_ITEMS))
    return None

def roll_raid_equipment():
    # Massive boost to item tier chances when killing a Raid Boss
    roll = random.random() * 100
    if roll <= 10.0: return ("Legendary", random.choice(LEGENDARY_ITEMS))
    elif roll <= 50.0: return ("Rare", random.choice(RARE_ITEMS))
    elif roll <= 90.0: return ("Uncommon", random.choice(UNCOMMON_ITEMS))
    else: return ("Common", random.choice(COMMON_ITEMS))

def get_next_monday_midnight():
    now = datetime.now()
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    return (now + timedelta(days=days_ahead)).replace(hour=0, minute=1, second=0, microsecond=0)

def check_daily_reset(user):
    today_str = datetime.now().strftime('%Y-%m-%d')
    if user.last_active_date != today_str:
        user.bosses_killed_today = 0
        user.chores_completed = False
        user.last_active_date = today_str
        db.session.commit()

# --- Routes ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'): return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def auto_login_by_ip():
    if request.endpoint in ['static', 'manual_login', 'claim_gacha', 'spend_gold', 'use_item'] or not request.endpoint: return
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
    
    if current_user: check_daily_reset(current_user)

    if boss and not boss.is_active and boss.next_spawn_date:
        if datetime.now() >= boss.next_spawn_date:
            boss.is_active = True
            boss.world_level += 1
            boss.max_hp = round(boss.max_hp * 1.03, 1) 
            boss.current_hp = boss.max_hp
            boss.name = random.choice(RAID_BOSSES)
            boss.next_spawn_date = None
            
            for player in players:
                player.solo_monster_max = round(player.solo_monster_max * 1.03, 1)
                player.solo_monster_hp = player.solo_monster_max
            db.session.commit()

    pending_rewards = PendingReward.query.filter_by(user_id=current_user.id).all() if current_user else []
    inventory = UserInventory.query.filter_by(user_id=current_user.id).all() if current_user else []

    if inventory:
        for item in inventory:
            if item.is_active and item.expires_at and datetime.now() > item.expires_at:
                db.session.delete(item)
        db.session.commit()

    return render_template('index.html', current_user=current_user, players=players, boss=boss, pending_rewards=pending_rewards, inventory=inventory)

@app.route('/manual_login/<username>')
def manual_login(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.last_known_ip = get_client_ip()
        db.session.commit()
        session['user_id'] = user.id
    return redirect('/')

@app.route('/stage_activity', methods=['POST'])
def stage_activity():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    boss = RaidBoss.query.first()
    check_daily_reset(user)
    
    act_type = request.form.get('type')
    try: minutes = float(request.form.get('minutes', 0))
    except: minutes = 0.0

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

    base_dmg = 0
    if act_type == 'workout': base_dmg = minutes * workout_mult
    elif act_type == 'hobby': base_dmg = minutes * hobby_mult
    elif act_type == 'chore': base_dmg = minutes * chore_mult
    
    just_did_chores = False
    if 'chores' in request.form and not user.chores_completed:
        user.chores_completed = True
        just_did_chores = True
        base_dmg += 50.0
        notify_discord(f"🔥 **{user.username}** sparked an Initiative Strike! 50 Flat DMG added to their attack!")

    if base_dmg <= 0: return redirect('/')

    if minutes > 0:
        notify_discord(f"⚔️ **{user.username}** logged {minutes} mins of {act_type.title()} Time, unleashing **{base_dmg:.1f}** Damage!")

    solo_dmg = base_dmg
    raid_dmg = 0

    while solo_dmg > 0 and user.bosses_killed_today < 3:
        if solo_dmg >= user.solo_monster_hp:
            solo_dmg -= user.solo_monster_hp
            user.bosses_killed_today += 1
            
            gold_drop = calculate_90_percent_loot_orb(boss.world_level)
            item_drop_text = None
            
            loot = roll_equipment()
            if loot:
                tier, item_data = loot
                i_name, i_cat, i_mult, i_desc = item_data
                item_drop_text = f"[{tier}] {i_name}"
                db.session.add(UserInventory(user_id=user.id, item_name=i_name, category_target=i_cat, multiplier=i_mult, description=i_desc, rarity=tier))
            
            user.gold_balance += gold_drop
            db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=item_drop_text))
            notify_discord(f"💀 **{user.username}** slaughtered a {user.solo_monster_name}! ({user.bosses_killed_today}/3 Daily Cap)")

            user.solo_monster_hp = user.solo_monster_max
            user.solo_monster_name = random.choice(SOLO_ENEMIES)
        else:
            user.solo_monster_hp -= solo_dmg
            solo_dmg = 0

    if solo_dmg > 0:
        raid_dmg += solo_dmg
        if user.bosses_killed_today >= 3:
            notify_discord(f"🌊 **OVERFLOW!** {user.username} is capped on Solo Bosses! **{raid_dmg:.1f}** DMG blasts directly into the {boss.name}!")

    if boss.is_active and raid_dmg > 0:
        boss.current_hp -= raid_dmg
        if boss.current_hp <= 0:
            boss.is_active = False
            boss.next_spawn_date = get_next_monday_midnight()
            
            for u in User.query.all():
                raid_drop = calculate_raid_boss_orb()
                
                # RAID BOSS ITEM DROP (High Odds)
                raid_loot = roll_raid_equipment()
                r_tier, r_data = raid_loot
                r_name, r_cat, r_mult, r_desc = r_data
                db.session.add(UserInventory(user_id=u.id, item_name=r_name, category_target=r_cat, multiplier=r_mult, description=r_desc, rarity=r_tier))
                
                db.session.add(PendingReward(user_id=u.id, gold_amount=raid_drop, item_name=f"[Raid Boss Kill] [{r_tier}] {r_name}"))
                u.gold_balance += raid_drop
            
            notify_discord(f"🌋 **{boss.name.upper()} DESTROYED!** Both players received a Raid Boss Orb and guaranteed high-tier loot!")

    db.session.commit()
    return redirect('/')

@app.route('/claim_gacha', methods=['POST'])
def claim_gacha():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        rewards = PendingReward.query.filter_by(user_id=user.id).all()
        total_gold = sum(r.gold_amount for r in rewards)
        items = [r.item_name for r in rewards if r.item_name]
        
        PendingReward.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        item_str = f" and found {', '.join(items)}!" if items else "!"
        notify_discord(f"🎰 **GACHA CLAIMED!** {user.username} cracked open their orbs for **${total_gold:.2f}**{item_str}")

    return redirect('/')

@app.route('/spend_gold', methods=['POST'])
def spend_gold():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    try: amount = float(request.form.get('amount', 0))
    except ValueError: amount = 0.0
    reason = request.form.get('reason', 'a mystery reward')
    
    if amount > 0 and user.gold_balance >= amount:
        user.gold_balance -= amount
        db.session.commit()
        notify_discord(f"🎉 **CONGRATULATIONS!** {user.username} cashed out **${amount:.2f}** for: *{reason}*!")
        
    return redirect('/')

@app.route('/use_item/<int:item_id>', methods=['POST'])
def use_item(item_id):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    item = UserInventory.query.filter_by(id=item_id, user_id=user.id).first()
    
    if not item or item.is_active: return redirect('/')
    
    effect = item.category_target
    val = item.multiplier
    
    if effect.startswith('buff'):
        item.is_active = True
        item.expires_at = datetime.now() + timedelta(days=1)
        notify_discord(f"✨ **{user.username}** activated {item.item_name} for the next 24 Hours!")
        
    elif effect == 'gold':
        user.gold_balance += val
        notify_discord(f"💰 **{user.username}** opened {item.item_name} and gained ${val:.2f}!")
        db.session.delete(item)
        
    elif effect == 'damage_solo':
        user.solo_monster_hp -= val
        notify_discord(f"💣 **{user.username}** used {item.item_name}, dealing {val} DMG to their solo boss!")
        if user.solo_monster_hp <= 0:
            boss_lvl = RaidBoss.query.first().world_level
            gold_drop = calculate_90_percent_loot_orb(boss_lvl)
            user.gold_balance += gold_drop
            db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name="[Explosive Kill]"))
            user.solo_monster_hp = user.solo_monster_max
            user.solo_monster_name = random.choice(SOLO_ENEMIES)
            user.bosses_killed_today += 1
        db.session.delete(item)
        
    elif effect == 'damage_raid':
        boss = RaidBoss.query.first()
        if boss.is_active:
            boss.current_hp -= val
            notify_discord(f"☄️ **{user.username}** unleashed {item.item_name}, blasting the Raid Boss for {val} DMG!")
            if boss.current_hp <= 0:
                boss.is_active = False
                boss.next_spawn_date = get_next_monday_midnight()
                for u in User.query.all():
                    raid_drop = calculate_raid_boss_orb()
                    
                    raid_loot = roll_raid_equipment()
                    r_tier, r_data = raid_loot
                    r_name, r_cat, r_mult, r_desc = r_data
                    db.session.add(UserInventory(user_id=u.id, item_name=r_name, category_target=r_cat, multiplier=r_mult, description=r_desc, rarity=r_tier))
                    
                    db.session.add(PendingReward(user_id=u.id, gold_amount=raid_drop, item_name=f"[Raid Boss Kill] [{r_tier}] {r_name}"))
                    u.gold_balance += raid_drop
                notify_discord(f"🌋 **RAID BOSS ANNIHILATED BY ITEM!** Both players received a Raid Boss Orb and guaranteed high-tier loot!")
        db.session.delete(item)
        
    elif effect == 'chore_pass':
        user.chores_completed = True
        notify_discord(f"🧹 **{user.username}** used {item.item_name}! Chores magically completed for today.")
        db.session.delete(item)

    db.session.commit()
    return redirect('/')

def initialize_database():
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
        if not User.query.first():
            db.session.add(User(username='Alaina', solo_monster_name=random.choice(SOLO_ENEMIES)))
            db.session.add(User(username='Matthew', solo_monster_name=random.choice(SOLO_ENEMIES)))
            db.session.add(RaidBoss(name=random.choice(RAID_BOSSES)))
            db.session.commit()

initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)