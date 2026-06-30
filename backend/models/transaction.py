from datetime import datetime, timezone
import uuid
from .database import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    id                  = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    txn_ref             = db.Column(db.String(50),  unique=True, nullable=False, index=True)
    user_id             = db.Column(db.String(36),  db.ForeignKey("users.id"), nullable=True, index=True)
    user_label          = db.Column(db.String(100), nullable=True)
    amount              = db.Column(db.Float,       nullable=False)
    currency            = db.Column(db.String(3),   default="MAD")
    country             = db.Column(db.String(2),   nullable=False)
    merchant            = db.Column(db.String(255), nullable=False)
    merchant_category   = db.Column(db.String(100), nullable=True)
    card_last4          = db.Column(db.String(4),   nullable=True)
    ip_address          = db.Column(db.String(45),  nullable=True)
    device_fingerprint  = db.Column(db.String(255), nullable=True)
    status              = db.Column(db.String(20),  nullable=False, default="pending", index=True)
    risk_score          = db.Column(db.Float,  default=0.0)
    confidence          = db.Column(db.Float,  default=0.0)
    risk_level          = db.Column(db.String(20), default="low")
    checks_json         = db.Column(db.Text,  nullable=True)
    explanation         = db.Column(db.Text,  nullable=True)
    latitude            = db.Column(db.Float, nullable=True)
    longitude           = db.Column(db.Float, nullable=True)
    created_at          = db.Column(db.DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc), index=True)
    processed_at        = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        import json
        return {
            "id":               self.id,
            "txn_ref":          self.txn_ref,
            "user_id":          self.user_id,
            "user_label":       self.user_label,
            "amount":           self.amount,
            "currency":         self.currency,
            "country":          self.country,
            "merchant":         self.merchant,
            "merchant_category":self.merchant_category,
            "card_last4":       self.card_last4,
            "ip_address":       self.ip_address,
            "status":           self.status,
            "risk_score":       round(self.risk_score, 2),
            "confidence":       round(self.confidence, 3),
            "risk_level":       self.risk_level,
            "checks":           json.loads(self.checks_json) if self.checks_json else [],
            "explanation":      self.explanation,
            "latitude":         self.latitude,
            "longitude":        self.longitude,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id            = db.Column(db.String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36),   db.ForeignKey("users.id"), nullable=True, index=True)
    action        = db.Column(db.String(100),  nullable=False, index=True)
    resource_type = db.Column(db.String(100),  nullable=True)
    resource_id   = db.Column(db.String(255),  nullable=True)
    details       = db.Column(db.Text,         nullable=True)
    ip_address    = db.Column(db.String(45),   nullable=True)
    user_agent    = db.Column(db.String(500),  nullable=True)
    severity      = db.Column(db.String(20),   default="info")
    created_at    = db.Column(db.DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc), index=True)

    # eager-load user via join when needed
    user = db.relationship("User", foreign_keys=[user_id], lazy="joined")

    def to_dict(self):
        return {
            "id":            self.id,
            "user_id":       self.user_id,
            "user":          {"username": self.user.username, "full_name": self.user.full_name}
                             if self.user else None,
            "action":        self.action,
            "resource_type": self.resource_type,
            "resource_id":   self.resource_id,
            "details":       self.details,
            "ip_address":    self.ip_address,
            "severity":      self.severity,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id         = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = db.Column(db.String(36),  db.ForeignKey("users.id"), nullable=False, index=True)
    type       = db.Column(db.String(50),  nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    data_json  = db.Column(db.Text,        nullable=True)
    is_read    = db.Column(db.Boolean,     default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "type":       self.type,
            "title":      self.title,
            "message":    self.message,
            "data":       json.loads(self.data_json) if self.data_json else None,
            "is_read":    self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
