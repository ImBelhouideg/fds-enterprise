"""
FDS — Database seeder with realistic demo data
"""
import random, json, uuid
from datetime import datetime, timedelta, timezone

MERCHANTS = [
    "Amazon","Jumia","Fnac","Cdiscount","Marjane","Carrefour",
    "Apple Store","Netflix","Airbnb","Booking.com","PayPal","Binance",
    "Zara","H&M","Decathlon","Total Energie","Orange","BMCE Bank",
]
COUNTRIES   = ["MA","FR","US","GB","DE","ES","IT","CA","RU","CN","NG","BR"]
ALLOWED     = {"MA","FR","US","GB","DE","ES","IT","CA"}
WEIGHTS     = [30, 20, 15, 10, 8, 5, 5, 4, 1, 1, 1, 0]
MERCH_CATS  = {
    "Amazon":"e-commerce","Jumia":"e-commerce","Fnac":"electronics",
    "Cdiscount":"e-commerce","Marjane":"retail","Carrefour":"retail",
    "Apple Store":"electronics","Netflix":"subscription","Airbnb":"travel",
    "Booking.com":"travel","PayPal":"financial","Binance":"crypto",
    "Zara":"fashion","H&M":"fashion","Decathlon":"sport",
    "Total Energie":"energy","Orange":"telecom","BMCE Bank":"banking",
}
COUNTRY_COORDS = {
    "MA":(31.79,-7.09),"FR":(46.22,2.21),"US":(37.09,-95.71),
    "GB":(55.37,-3.43),"DE":(51.16,10.45),"ES":(40.46,-3.74),
    "IT":(41.87,12.56),"CA":(56.13,-106.34),"RU":(61.52,105.31),
    "CN":(35.86,104.19),"NG":(9.08,8.67),"BR":(-14.23,-51.92),
}


def seed_demo_data(db, User, Transaction, AuditLog, bcrypt):
    from flask import current_app as app

    # ── Demo users ────────────────────────────────────────────
    users_cfg = [
        dict(email="admin@fds.io",   username="admin",    password="Admin@123",
             role="admin",   first="Alice", last="Admin",   verified=True),
        dict(email="analyst@fds.io", username="analyst1", password="Analyst@123",
             role="analyst", first="Bob",   last="Analyst", verified=True),
        dict(email="manager@fds.io", username="manager1", password="Manager@123",
             role="manager", first="Carol", last="Manager", verified=True),
        dict(email="user@fds.io",    username="user1",    password="User@1234",
             role="user",    first="David", last="User",    verified=True),
    ]

    created_users = []
    for uc in users_cfg:
        if User.query.filter_by(email=uc["email"]).first():
            continue
        u = User(
            id=str(uuid.uuid4()),
            email=uc["email"], username=uc["username"],
            role=uc["role"], first_name=uc["first"], last_name=uc["last"],
            is_verified=uc["verified"], is_active=True,
            login_count=random.randint(5, 80),
            last_login=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={uc['username']}",
        )
        u.set_password(uc["password"])
        db.session.add(u)
        created_users.append(u)

    if created_users:
        db.session.commit()
        app.logger.info(f"Seeded {len(created_users)} users")

    # ── Demo transactions ─────────────────────────────────────
    if Transaction.query.count() >= 50:
        return

    all_users = User.query.all()
    if not all_users:
        return

    now = datetime.now(timezone.utc)
    txns = []

    for i in range(250):
        user    = random.choice(all_users)
        country = random.choices(COUNTRIES, weights=WEIGHTS, k=1)[0]
        amount  = round(random.uniform(20, 9000), 2)
        merchant= random.choice(MERCHANTS)

        # Fraud logic
        is_fraud = (
            country not in ALLOWED
            or amount > 5500
            or random.random() < 0.07
        )
        risk_score = round(random.uniform(60, 97), 2) if is_fraud else round(random.uniform(1, 38), 2)
        risk_level = (
            "critical" if risk_score >= 70
            else "high" if risk_score >= 45
            else "medium" if risk_score >= 20
            else "low"
        )
        lat, lon = COUNTRY_COORDS.get(country, (0, 0))
        lat += random.uniform(-3, 3)
        lon += random.uniform(-3, 3)

        checks = [
            {"check":"Limite de montant",        "icon":"💰","passed": amount < 5000,          "detail":f"Montant: {amount:.2f} MAD"},
            {"check":"Vérification de localisation","icon":"🌍","passed": country in ALLOWED, "detail":f"Pays: {country}"},
            {"check":"Fréquence des transactions","icon":"⚡","passed": True,                  "detail":"Dans les limites"},
            {"check":"Détection de doublons",     "icon":"🔁","passed": True,                  "detail":"Aucun doublon"},
        ]

        t = Transaction(
            id=str(uuid.uuid4()),
            txn_ref=f"TXN{str(i+1).zfill(6)}",
            user_id=user.id,
            user_label=user.username,
            amount=amount, currency="MAD",
            country=country, merchant=merchant,
            merchant_category=MERCH_CATS.get(merchant, "other"),
            card_last4=str(random.randint(1000, 9999)),
            ip_address=f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            status="blocked" if is_fraud else "approved",
            risk_score=risk_score,
            confidence=round(random.uniform(0.70, 0.99), 3),
            risk_level=risk_level,
            checks_json=json.dumps(checks),
            explanation=f"Score de risque: {risk_score:.0f}/100. {'Fraude probable.' if is_fraud else 'Transaction normale.'}",
            latitude=round(lat, 4),
            longitude=round(lon, 4),
            created_at=now - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            ),
        )
        txns.append(t)

    db.session.bulk_save_objects(txns)
    db.session.commit()
    app.logger.info(f"Seeded {len(txns)} transactions")
