# 🛡️ FDS Enterprise — Fraud Detection Platform v3.0

<div align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/python-3.12-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/flask-3.0-green?style=flat-square" />
  <img src="https://img.shields.io/badge/docker-ready-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
</div>

<br />

> Plateforme SaaS de détection de fraude de niveau entreprise — comparable à **Stripe Radar**, **Feedzai** et **Sift**. Développée avec Flask, PostgreSQL, Redis, SocketIO et une interface SPA premium.

---

## ✨ Fonctionnalités

| Catégorie | Fonctionnalités |
|-----------|----------------|
| 🔐 **Auth** | JWT, Refresh Token, 2FA TOTP, RBAC, verrouillage compte, audit connexions |
| 🛡️ **Détection IA** | Score 0-100, SHAP, 6 signaux, niveau de confiance, explications en langage naturel |
| ⚡ **Temps réel** | WebSockets, notifications live, streaming transactions |
| 📊 **Dashboard** | KPI animés, charts interactifs, heatmap pays, distribution risques |
| 👥 **Admin** | RBAC (admin/manager/analyst/user), gestion utilisateurs, audit complet |
| 📡 **Monitoring** | CPU/RAM/Disk, Prometheus métriques, Grafana dashboards |
| 🔔 **Notifications** | Centre en temps réel, email, push |
| 📤 **Export** | CSV, filtres avancés, pagination |

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    Nginx    │────▶│  Flask API   │────▶│ PostgreSQL  │
│  :80/:443   │     │   :5000      │     │   :5432     │
└─────────────┘     │  SocketIO    │     └─────────────┘
                    │  Gunicorn    │     ┌─────────────┐
┌─────────────┐     └──────────────┘────▶│    Redis    │
│ Prometheus  │◀──────────────────┐      │   :6379     │
│   :9090     │    /metrics       │      └─────────────┘
└──────┬──────┘                   │
       │                          │
┌──────▼──────┐                   │
│   Grafana   │                   │
│   :3000     │                   │
└─────────────┘                   │
                    SPA (index.html)
                    api.js + pages.js
```

## 🚀 Démarrage rapide

### Prérequis
- Docker 24+ et Docker Compose v2
- 4 Go RAM minimum

### Installation

```bash
# 1. Cloner et configurer
git clone https://github.com/your-org/fds-enterprise
cd fds-enterprise
cp .env.example .env
# Editer .env avec vos valeurs

# 2. Démarrer
docker compose up --build

# 3. Accéder
# Application  : http://localhost
# Grafana      : http://localhost:3000
# Prometheus   : http://localhost:9090
# API docs     : http://localhost/api/
```

### Comptes de démonstration

| Email | Mot de passe | Rôle |
|-------|-------------|------|
| admin@fds.io | Admin@123 | Admin |
| analyst@fds.io | Analyst@123 | Analyst |
| manager@fds.io | Manager@123 | Manager |
| user@fds.io | User@1234 | User |

## 📡 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Inscription |
| POST | `/api/auth/login` | Connexion |
| POST | `/api/auth/logout` | Déconnexion |
| POST | `/api/auth/refresh` | Renouveler token |
| GET  | `/api/auth/me` | Profil courant |
| PUT  | `/api/auth/me` | Modifier profil |
| POST | `/api/auth/change-password` | Changer mot de passe |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transactions/analyze` | Analyser une transaction |
| GET  | `/api/transactions/` | Liste paginée |
| GET  | `/api/transactions/stats` | Statistiques globales |
| GET  | `/api/transactions/map` | Données cartographiques |
| GET  | `/api/transactions/export` | Export CSV |

### Users (admin/manager)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/users/` | Liste utilisateurs |
| POST   | `/api/users/` | Créer utilisateur |
| PUT    | `/api/users/<id>` | Modifier |
| DELETE | `/api/users/<id>` | Supprimer |
| POST   | `/api/users/<id>/toggle-block` | Bloquer/Débloquer |
| POST   | `/api/users/<id>/change-role` | Changer rôle |

### System
| Endpoint | Description |
|----------|-------------|
| GET `/health` | État des services |
| GET `/metrics` | Métriques Prometheus |
| GET `/api/monitoring/system` | Métriques système |

## 🔒 Sécurité

- **JWT** avec expiration 1h + Refresh Token 30j
- **RBAC** à 4 niveaux (admin, manager, analyst, user)
- **Rate Limiting** par IP sur auth (10 req/min) et analyse (30 req/min)
- **bcrypt** (12 rounds) pour hashage des mots de passe
- **Verrouillage** compte après 5 tentatives
- **Headers** sécurisés (X-Frame-Options, XSS-Protection, nosniff)
- **URL encoding** des mots de passe PostgreSQL/Redis
- **CORS** configurable par variable d'environnement

## 📦 Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, Flask 3.0, Gunicorn + Gevent |
| BDD | PostgreSQL 16, SQLAlchemy 2.0 |
| Cache | Redis 7 |
| Temps réel | Flask-SocketIO 5.x |
| Auth | Flask-JWT-Extended, Flask-Bcrypt |
| Monitoring | Prometheus, Grafana |
| Reverse Proxy | Nginx 1.25 |
| Frontend | Vanilla JS ES6+, Chart.js 4.4, IBM Plex Mono |
| Conteneurs | Docker, Docker Compose v2 |

## 🧪 Variables d'environnement

```env
# App
SECRET_KEY=           # Minimum 32 caractères
JWT_SECRET_KEY=       # Minimum 32 caractères
FLASK_ENV=production

# PostgreSQL (éviter @ ! # dans les mots de passe)
POSTGRES_DB=fds_db
POSTGRES_USER=fds_user
POSTGRES_PASSWORD=StrongPass2024

# Redis
REDIS_PASSWORD=StrongRedisPass2024

# Fraude
ALLOWED_COUNTRIES=MA,FR,US,GB,DE,ES,IT,CA
MAX_TXN_IN_WINDOW=5
AMOUNT_MULTIPLIER=2.0
```

## 📄 Licence

MIT License — © 2024 FDS Enterprise Team
