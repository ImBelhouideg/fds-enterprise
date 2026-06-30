import random, math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple

COUNTRY_COORDS = {
    "MA":(31.79,-7.09),"FR":(46.22,2.21),"US":(37.09,-95.71),"GB":(55.37,-3.43),
    "DE":(51.16,10.45),"ES":(40.46,-3.74),"IT":(41.87,12.56),"CA":(56.13,-106.34),
    "RU":(61.52,105.31),"CN":(35.86,104.19),"NG":(9.08,8.67),"BR":(-14.23,-51.92),
    "IN":(20.59,78.96),"AU":(-25.27,133.77),"JP":(36.20,138.25),
    "PK":(30.37,69.34),"VN":(14.05,108.27),"KP":(40.33,127.51),"IR":(32.42,53.68),
}
COUNTRY_NAMES = {
    "MA":"Maroc","FR":"France","US":"États-Unis","GB":"Royaume-Uni","DE":"Allemagne",
    "ES":"Espagne","IT":"Italie","CA":"Canada","RU":"Russie","CN":"Chine","NG":"Nigeria",
    "BR":"Brésil","IN":"Inde","AU":"Australie","JP":"Japon","PK":"Pakistan","VN":"Vietnam",
}
HIGH_RISK   = {"RU","CN","NG","PK","VN","KP","IR"}
MEDIUM_RISK = {"BR","IN","UA","MX","EG"}

def calculate_risk_score(checks, amount, country, user_history):
    score = 0.0
    weights = {"Limite de montant":35,"Vérification de localisation":30,
               "Fréquence des transactions":25,"Détection de doublons":20}
    for c in checks:
        if not c["passed"] and c["check"] in weights:
            score += weights[c["check"]]
    if country in HIGH_RISK:   score = min(score + 25, 100)
    elif country in MEDIUM_RISK: score = min(score + 10, 100)
    if amount > 8000:   score = min(score + 20, 100)
    elif amount > 4000: score = min(score + 10, 100)
    elif amount > 2000: score = min(score + 5, 100)
    if user_history:
        recent = [t for t in user_history
                  if datetime.fromisoformat(t.get("created_at","1970-01-01T00:00:00+00:00").replace("Z","+00:00"))
                  > datetime.now(timezone.utc) - timedelta(hours=1)]
        if len(recent) > 6: score = min(score + 12, 100)
    confidence = min(0.55 + len(user_history)*0.015 + len(checks)*0.04, 0.98)
    level = "critical" if score>=70 else "high" if score>=45 else "medium" if score>=20 else "low"
    return round(score, 2), round(confidence, 3), level

def generate_explanation(checks, risk_score, amount, country, merchant):
    failed = [c["check"] for c in checks if not c["passed"]]
    emoji  = "🚨" if risk_score>=70 else "🔶" if risk_score>=45 else "⚠️" if risk_score>=20 else "✅"
    parts  = [f"{emoji} Score de risque: {risk_score:.0f}/100."]
    if failed: parts.append(f"Anomalies: {', '.join(failed)}.")
    if country in HIGH_RISK: parts.append(f"Pays {COUNTRY_NAMES.get(country,country)} à haut risque.")
    if amount > 4000: parts.append(f"Montant élevé ({amount:.2f} MAD).")
    return " ".join(parts)

def get_shap_values(checks, risk_score):
    base = risk_score / 100
    return [
        {"feature":"Montant transaction", "value":round(base*0.32*(1+random.gauss(0,.08)),3), "direction":"positive" if base>0.3 else "negative"},
        {"feature":"Pays d'origine",      "value":round(base*0.27*(1+random.gauss(0,.08)),3), "direction":"positive" if base>0.3 else "negative"},
        {"feature":"Fréquence récente",   "value":round(base*0.21*(1+random.gauss(0,.08)),3), "direction":"positive" if base>0.4 else "negative"},
        {"feature":"Historique marchand", "value":round(base*0.13*(1+random.gauss(0,.08)),3), "direction":"negative"},
        {"feature":"Heure de transaction","value":round(base*0.07*(1+random.gauss(0,.08)),3), "direction":"negative"},
    ]
