import os
import requests
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'rpg_accountability_secret_chain'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- RPG Loot Configuration ---
LOOT_TABLE = {
    "common":    {"min_gold": 1.00, "max_gold": 2.50, "items": [("Running Shoes", "cardio", 1.25), ("Wooden Shield", "screen_time", 1.10)]},
    "rare":      {"min_gold": 2.51, "max_gold": 4.50, "items": [("Painter's Brush", "hobby", 1.50), ("Heavy Greatsword", "all", 1.15)]},
    "epic":      {"min_gold": 4.51, "max_gold": 6.50, "items": [("Focus Cloak", "screen_time", 2.00)]},
    "legendary": {"min_gold": 6.51, "max_gold": 7.00, "items": [("The Golden Hourglass", "all", 1.30)]}
}

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    gold_balance = db.Column(db.Float, default=0.0)
    last_known_ip = db.Column(db.String(100), nullable=True)

class RaidBoss(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="The Doomscroll Behemoth")
    max_hp = db.Column(db.Float, default=1500.0)
    current_hp = db.Column(db.Float, default=1500.0)

class UserInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    category_target = db.Column(db.String(50), nullable=False) # cardio, hobby, screen_time, all
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

def get_clean_multiplier(user_id, category):
    active_items = UserInventory.query.filter_by(user_id=user_id, is_active=True).all()
    total_mod = 1.0
    for item in active_items:
        if item.is_expired:
            item.is_active = False
            db.session.commit()
            user = User.query.get(user_id)
            notify_discord(f"⏰ *{user.username}'s* [{item.item_name}] has degraded and broken after a week of intense habits!")
        elif item.category_target == category or item.category_target == "all":
            total_mod += (item.multiplier - 1.0)
    return total_mod

# --- Middleware-like IP Handler ---
def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.before_request
def auto_login_by_ip():
    if 'user_id' not in session:
        ip = get_client_ip()
        matched_user = User.query.filter_by(last_known_ip=ip).first()
        if matched_user:
            session['user_id'] = matched_user.id

# --- Routes ---
@app.route('/')
def index():
    current_user = User.query.get(session['user_id']) if 'user_id' in session else None
    players = User.query.all()
    boss = RaidBoss.query.first()
    
    inventory = []
    if current_user:
        # Trigger cleanup pass
        get_clean_multiplier(current_user.id, "all")
        inventory = UserInventory.query.filter_by(user_id=current_user.id).all()

    return render_template('index.html', current_user=current_user, players=players, boss=boss, inventory=inventory)

@app.route('/manual_login/<username>')
def manual_login(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.last_known_ip = get_client_ip()
        db.session.commit()
        session['user_id'] = user.id
    return redirect('/')

@app.route('/log_activity', methods=['POST'])
def log_activity():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    act_type = request.form.get('type')
    minutes = float(request.form.get('minutes', 0))
    
    # Base Math Engine
    if act_type == 'cardio':
        intensity = float(request.form.get('intensity', 1.0))
        base_exp = minutes * intensity
    elif act_type == 'hobby':
        base_exp = minutes * 1.5
    elif act_type == 'screen_time':
        base_exp = minutes * 2.0
    else:
        base_exp = 0

    # Process Active Boosters
    multiplier = get_clean_multiplier(user.id, act_type)
    final_damage = base_exp * multiplier

    # Apply Strike to Shared Raid Boss
    boss = RaidBoss.query.first()
    boss.current_hp = max(0.0, boss.current_hp - final_damage)
    db.session.commit()

    notify_discord(f"⚔️ **{user.username}** struck the Raid Boss for **{final_damage:.2f} Damage** using a {act_type} entry! (Multiplier: {multiplier}x)")

    # Handle Raid Boss Defeated Reward Loops
    if boss.current_hp <= 0:
        roll = random.random()
        tier = "common" if roll <= 0.60 else "rare" if roll <= 0.85 else "epic" if roll <= 0.97 else "legendary"
        tier_data = LOOT_TABLE[tier]
        
        gold_dropped = round(random.uniform(tier_data["min_gold"], tier_data["max_gold"]), 2)
        user.gold_balance += gold_dropped
        
        item_dropped = None
        if random.random() > 0.40: # 60% chance to also pull an item item
            raw_item = random.choice(tier_data["items"])
            item_dropped = UserInventory(user_id=user.id, item_name=raw_item[0], category_target=raw_item[1], multiplier=raw_item[2])
            db.session.add(item_dropped)
            
        boss.current_hp = boss.max_hp  # Revive Boss stronger or reset
        db.session.commit()

        msg = f"🏆 🎉 **RAID BOSS DEFEATED!** {user.username} landed the execution. \n" \
              f"🎁 **Loot Quality:** {tier.upper()}\n" \
              f"💰 **Gold Drop:** +${gold_dropped:.2f} to {user.username}'s personal vault!"
        if item_dropped:
            msg += f"\n📦 **Item Added:** [{item_dropped.item_name}] (+{int((item_dropped.multiplier-1)*100)}% {item_dropped.category_target} bonus for 7 days!)"
        notify_discord(msg)

    return redirect('/')

@app.route('/activate_item/<int:item_id>')
def activate_item(item_id):
    if 'user_id' not in session: return redirect('/')
    item = UserInventory.query.get(item_id)
    if item and item.user_id == session['user_id'] and not item.is_active:
        item.is_active = True
        item.activated_at = datetime.utcnow()
        db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            db.session.add(User(username='Alaina'))
            db.session.add(User(username='Matthew'))
            db.session.add(RaidBoss())
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)