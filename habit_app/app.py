import os
import requests
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'rpg_accountability_secret_chain'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    gold_balance = db.Column(db.Float, default=0.0)
    last_known_ip = db.Column(db.String(100), nullable=True)
    
    # Solo Boss Progression Tracking
    solo_monster_hp = db.Column(db.Float, default=300.0)
    solo_monster_max = db.Column(db.Float, default=300.0)
    solo_monster_name = db.Column(db.String(100), default="Slime")

class RaidBoss(db.Model):
    __tablename__ = 'raid_boss'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="The Doomscroll Behemoth")
    max_hp = db.Column(db.Float, default=1500.0)
    current_hp = db.Column(db.Float, default=1500.0)

class DailyQueue(db.Model):
    __tablename__ = 'daily_queue'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    cardio_mins = db.Column(db.Float, default=0.0)
    hobby_mins = db.Column(db.Float, default=0.0)
    screen_mins = db.Column(db.Float, default=0.0)
    chores_completed = db.Column(db.Boolean, default=False)

class UserInventory(db.Model):
    __tablename__ = 'user_inventory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    category_target = db.Column(db.String(50), nullable=False)
    multiplier = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=False)
    activated_at = db.Column(db.DateTime, nullable=True)
    duration_days = db.Column(db.Integer, default=7)

    @property
    def is_expired(self):
        if not self.is_active or not self.activated_at:
            return False
        return datetime.utcnow() > (self.activated_at + timedelta(days=self.duration_days))

# --- Helpers ---
def notify_discord(message):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        try: requests.post(webhook_url, json={"content": message})
        except: pass

def calculate_90_percent_loot_orb():
    roll = random.random()
    if roll <= 0.90:
        # 90% chance for average drop range ($3.00 - $4.00)
        return round(random.uniform(3.00, 4.00), 2)
    else:
        # 10% chance to drop wild outliers ($1.00 - $2.99 OR $4.01 - $7.00)
        if random.random() > 0.5:
            return round(random.uniform(1.00, 2.99), 2)
        return round(random.uniform(4.01, 7.00), 2)

# --- Core Process Engine (Runs calculations simulated for 11:59 PM) ---
def process_end_of_day_strikes(user_id):
    user = User.query.get(user_id)
    queue = DailyQueue.query.filter_by(user_id=user_id).first()
    if not queue: return 0.0

    # Base damage compilation (Multiplier choices removed)
    base_dmg = queue.cardio_mins + (queue.hobby_mins * 1.5) + (queue.screen_mins * 2.0)

    # Apply 1.5x Chore Multiplier if completed
    if queue.chores_completed:
        base_dmg *= 1.5

    # Hit Solo Boss
    user.solo_monster_hp -= base_dmg
    if user.solo_monster_hp <= 0:
        gold_drop = calculate_90_percent_loot_orb()
        user.gold_balance += gold_drop
        
        # Check rare chance (15%) for an item gear piece
        item_note = ""
        if random.random() <= 0.15:
            new_item = UserInventory(user_id=user.id, item_name="Master Brush", category_target="hobby", multiplier=1.5)
            db.session.add(new_item)
            item_note = " and discovered an Equipment Orb: [Master Brush]!"

        notify_discord(f"💀 **SOLO MONSTER DEFEATED!** {user.username} destroyed {user.solo_monster_name} and burst open an orb dropping **${gold_drop:.2f}**{item_note}!")
        
        # Spawn next harder enemy
        user.solo_monster_max += 150
        user.solo_monster_hp = user.solo_monster_max
        user.solo_monster_name = random.choice(["Orc Raider", "Mountain Troll", "Shadow Specter"])

    # Hit Shared Raid Boss
    boss = RaidBoss.query.first()
    boss.current_hp = max(0.0, boss.current_hp - base_dmg)
    if boss.current_hp <= 0:
        boss.current_hp = boss.max_hp
        notify_discord(f"🏆 **RAID BOSS SLAYED!** Global rewards have been dropped into the channels!")

    # Clear queue storage for tomorrow
    queue.cardio_mins = 0
    queue.hobby_mins = 0
    queue.screen_mins = 0
    queue.chores_completed = False
    db.session.commit()
    
    return base_dmg

# --- Routes ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def auto_login_by_ip():
    if request.endpoint in ['static', 'manual_login'] or not request.endpoint: return
    if 'user_id' not in session:
        try:
            matched_user = User.query.filter_by(last_known_ip=get_client_ip()).first()
            if matched_user: session['user_id'] = matched_user.id
        except: pass

@app.route('/')
def index():
    current_user = User.query.get(session['user_id']) if 'user_id' in session else None
    players = User.query.all()
    boss = RaidBoss.query.first()
    inventory = UserInventory.query.filter_by(user_id=session['user_id']).all() if current_user else []
    
    user_queue = None
    if current_user:
        user_queue = DailyQueue.query.filter_by(user_id=current_user.id).first()
        if not user_queue:
            user_queue = DailyQueue(user_id=current_user.id)
            db.session.add(user_queue)
            db.session.commit()

    return render_template('index.html', current_user=current_user, players=players, boss=boss, inventory=inventory, queue=user_queue)

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
    queue = DailyQueue.query.filter_by(user_id=session['user_id']).first()
    
    act_type = request.form.get('type')
    minutes = float(request.form.get('minutes', 0))
    
    if act_type == 'cardio': queue.cardio_mins += minutes
    elif act_type == 'hobby': queue.hobby_mins += minutes
    elif act_type == 'screen_time': queue.screen_mins += minutes
    
    queue.chores_completed = 'chores' in request.form
    db.session.commit()
    return redirect('/')

@app.route('/trigger_midnight_calculation')
def trigger_midnight_calculation():
    if 'user_id' not in session: return redirect('/')
    dmg = process_end_of_day_strikes(session['user_id'])
    return redirect('/')

def initialize_database():
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
        if not User.query.first():
            db.session.add(User(username='Alaina'))
            db.session.add(User(username='Matthew'))
            db.session.add(RaidBoss())
            db.session.commit()

initialize_database()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)