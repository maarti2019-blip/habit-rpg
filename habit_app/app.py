import os
import requests
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'rpg_accountability_secret_chain'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Fantasy Monster Pools ---
SOLO_ENEMIES = [
    "Goblin", "Skeleton", "Slime", "Orc", "Troll", "Kobold", "Harpy", "Imp", "Ghoul", "Zombie",
    "Bandit", "Cultist", "Sprite", "Mimic", "Spider", "Rat", "Wolf", "Bat", "Hobgoblin", "Wraith",
    "Basilisk", "Cockatrice", "Manticore", "Gargoyle", "Elemental", "Golem", "Treant", "Centaur", "Minotaur", "Naga"
]

RAID_BOSSES = [
    "Dragon", "Behemoth", "Kraken", "Leviathan", "Hydra", "Lich", "Titan", "Colossus", "Balrog", "Chimera",
    "Wyrm", "Tarrasque", "Cyclops", "Sphinx", "Roc", "Wendigo", "Dullahan", "Juggernaut", "Beholder", "Deathknight",
    "Goliath", "Ogre", "Vampire", "Necromancer", "Archdemon", "Archangel", "Ifrit", "Geryon", "Bahamut", "Fenrir"
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

class RaidBoss(db.Model):
    __tablename__ = 'raid_boss'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Dragon")
    max_hp = db.Column(db.Float, default=1200.0)  # NERFED from 3000
    current_hp = db.Column(db.Float, default=1200.0)
    world_level = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    next_spawn_date = db.Column(db.DateTime, nullable=True)

class DailyQueue(db.Model):
    __tablename__ = 'daily_queue'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    workout_mins = db.Column(db.Float, default=0.0)
    hobby_mins = db.Column(db.Float, default=0.0)
    chores_completed = db.Column(db.Boolean, default=False)

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

# --- Helpers ---
def notify_discord(message):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        try: requests.post(webhook_url, json={"content": message})
        except: pass

def calculate_90_percent_loot_orb(world_level):
    level_bonus = (world_level - 1) * 0.50
    if random.random() <= 0.90:
        return round(random.uniform(3.00 + level_bonus, 4.00 + level_bonus), 2)
    else:
        if random.random() > 0.5: return round(random.uniform(1.00, 2.99 + level_bonus), 2)
        return round(random.uniform(4.01 + level_bonus, 7.00 + level_bonus), 2)

def get_next_monday_midnight():
    now = datetime.now()
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    return (now + timedelta(days=days_ahead)).replace(hour=0, minute=1, second=0, microsecond=0)

# --- Midnight Calculation Engine ---
def process_all_end_of_day_strikes():
    queues = DailyQueue.query.all()
    boss = RaidBoss.query.first()
    
    for queue in queues:
        if queue.workout_mins == 0 and queue.hobby_mins == 0 and not queue.chores_completed:
            continue
            
        user = User.query.get(queue.user_id)
        
        base_dmg = (queue.workout_mins * 4.5) + (queue.hobby_mins * 7.0)
        if queue.chores_completed:
            base_dmg *= 1.5

        solo_dmg = base_dmg
        raid_dmg = 0
        bosses_killed = 0

        while solo_dmg > 0 and bosses_killed < 3:
            if solo_dmg >= user.solo_monster_hp:
                solo_dmg -= user.solo_monster_hp
                bosses_killed += 1
                
                gold_drop = calculate_90_percent_loot_orb(boss.world_level)
                item_drop = None
                
                if random.random() <= 0.15:
                    item_drop = "Master Brush"
                    db.session.add(UserInventory(user_id=user.id, item_name=item_drop, category_target="hobby", multiplier=1.5))
                
                user.gold_balance += gold_drop
                db.session.add(PendingReward(user_id=user.id, gold_amount=gold_drop, item_name=item_drop))
                
                notify_discord(f"💀 **{user.username}** slaughtered a {user.solo_monster_name} and queued a Gacha Orb drop!")

                user.solo_monster_max += 100 
                user.solo_monster_hp = user.solo_monster_max
                user.solo_monster_name = random.choice(SOLO_ENEMIES)
            else:
                user.solo_monster_hp -= solo_dmg
                solo_dmg = 0

        if solo_dmg > 0:
            raid_dmg += solo_dmg
            notify_discord(f"🌊 **OVERFLOW BURST!** {user.username} hit their solo cap and blasted **{raid_dmg:.1f}** remaining damage directly into the {boss.name}!")

        if boss.is_active and raid_dmg > 0:
            boss.current_hp -= raid_dmg
            if boss.current_hp <= 0:
                boss.is_active = False
                boss.next_spawn_date = get_next_monday_midnight()
                
                db.session.add(PendingReward(user_id=user.id, gold_amount=10.0, item_name="Raid Boss Bounty"))
                user.gold_balance += 10.0
                
                notify_discord(f"🌋 **{boss.name.upper()} DESTROYED!** It is dead until Monday. The server advances to **World Level {boss.world_level + 1}**!")

        queue.workout_mins = 0
        queue.hobby_mins = 0
        queue.chores_completed = False

    db.session.commit()

# --- Routes ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'): return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def auto_login_by_ip():
    if request.endpoint in ['static', 'manual_login', 'claim_gacha'] or not request.endpoint: return
    if 'user_id' not in session:
        try:
            matched_user = User.query.filter_by(last_known_ip=get_client_ip()).first()
            if matched_user: session['user_id'] = matched_user.id
        except: pass

@app.route('/')
def index():
    current_user = User.query.get(session['user_id']) if 'user_id' in session else None
    boss = RaidBoss.query.first()
    
    if boss and not boss.is_active and boss.next_spawn_date:
        if datetime.now() >= boss.next_spawn_date:
            boss.is_active = True
            boss.world_level += 1
            boss.max_hp += 150  # Much more forgiving scaling
            boss.current_hp = boss.max_hp
            boss.name = random.choice(RAID_BOSSES)
            boss.next_spawn_date = None
            db.session.commit()
            notify_discord(f"🚨 **NEW RAID BOSS SPAWN!** A massive {boss.name} has appeared for the week!")

    pending_rewards = PendingReward.query.filter_by(user_id=current_user.id).all() if current_user else []
    user_queue = DailyQueue.query.filter_by(user_id=current_user.id).first() if current_user else None
    
    if current_user and not user_queue:
        user_queue = DailyQueue(user_id=current_user.id)
        db.session.add(user_queue)
        db.session.commit()

    return render_template('index.html', current_user=current_user, players=User.query.all(), boss=boss, queue=user_queue, pending_rewards=pending_rewards)

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
    queue = DailyQueue.query.filter_by(user_id=session['user_id']).first()
    
    act_type = request.form.get('type')
    minutes = float(request.form.get('minutes', 0))
    
    if act_type == 'workout': 
        queue.workout_mins += minutes
        notify_discord(f"⚔️ {user.username} staged {minutes} mins of Workout Time.")
    elif act_type == 'hobby': 
        queue.hobby_mins += minutes
        notify_discord(f"📚 {user.username} staged {minutes} mins of Hobby Time.")
    
    if 'chores' in request.form and not queue.chores_completed: 
        queue.chores_completed = True
        notify_discord(f"🧹 {user.username} completed chores! Personal 1.5x damage buff active.")
        
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

@app.route('/trigger_midnight_calculation')
def trigger_midnight_calculation():
    process_all_end_of_day_strikes()
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