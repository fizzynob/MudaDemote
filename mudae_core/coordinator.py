"""Thread-safe cross-account claim and $rt reservations."""

from collections import OrderedDict
import datetime
import threading
import time


class GlobalIntervalCoordinator:
    """Reserve process-wide command slots across clients and event loops."""

    def __init__(self):
        self._lock = threading.RLock()
        self._next_slots = {}

    def reserve(self, key, interval_seconds, now_monotonic=None):
        """Return the wait for this reservation and advance the key's next slot."""
        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        interval = max(0.0, float(interval_seconds))
        with self._lock:
            slot = max(now, self._next_slots.get(key, now))
            self._next_slots[key] = slot + interval
            return max(0.0, slot - now)

    def estimated_wait(self, key, now_monotonic=None):
        """Return the current queue delay without reserving a command slot."""
        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        with self._lock:
            return max(0.0, self._next_slots.get(key, now) - now)


class ClaimCoordinator:
    """Coordinates message reservations under one lock to prevent deadlocks."""

    def __init__(self, completed_limit=2000):
        self._lock = threading.RLock()
        self._claims = set()
        self._restores = set()
        self._completed = OrderedDict()
        self._completed_limit = max(1, int(completed_limit))

    def is_reserved(self, message_id):
        with self._lock:
            return (
                message_id in self._claims
                or message_id in self._restores
                or message_id in self._completed
            )

    def filter_available(self, items, id_getter=lambda item: item[0].id):
        with self._lock:
            return [
                item for item in items
                if id_getter(item) not in self._claims
                and id_getter(item) not in self._restores
                and id_getter(item) not in self._completed
            ]

    def reserve_claim(self, message_id, allow_reserved_restore=False):
        with self._lock:
            if message_id in self._claims or message_id in self._completed:
                return False
            if message_id in self._restores and not allow_reserved_restore:
                return False
            self._claims.add(message_id)
            if allow_reserved_restore:
                self._restores.discard(message_id)
            return True

    def reserve_restore(self, message_id):
        with self._lock:
            if (
                message_id in self._claims
                or message_id in self._restores
                or message_id in self._completed
            ):
                return False
            self._restores.add(message_id)
            return True

    def transition_restore_to_claim(self, message_id):
        with self._lock:
            if message_id in self._claims or message_id in self._completed:
                return False
            self._restores.discard(message_id)
            self._claims.add(message_id)
            return True

    def release_claim(self, message_id):
        with self._lock:
            self._claims.discard(message_id)

    def release_restore(self, message_id):
        with self._lock:
            self._restores.discard(message_id)

    def release_all(self, message_id):
        with self._lock:
            self._claims.discard(message_id)
            self._restores.discard(message_id)

    def mark_completed(self, message_id):
        """Keep a bounded terminal record so late clients cannot retry a resolved roll."""
        if message_id is None:
            return
        with self._lock:
            self._claims.discard(message_id)
            self._restores.discard(message_id)
            self._completed.pop(message_id, None)
            self._completed[message_id] = None
            while len(self._completed) > self._completed_limit:
                self._completed.popitem(last=False)

    def completed_snapshot(self):
        with self._lock:
            return frozenset(self._completed)

    def snapshot(self):
        with self._lock:
            return frozenset(self._claims), frozenset(self._restores)


class MainAccountCooldownTracker:
    """Thread-safe tracker for the target Main Account's claim cooldown state.

    Populated both directly by any locally running Main Account instance and
    passively by observing Mudae's replies ($tu, marriage confirmations, claim
    cooldown rejections) in shared Discord channels.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._states = {}  # main_user_id (str) -> dict

    @staticmethod
    def _normalize_id(main_user_id):
        text = str(main_user_id or "").strip()
        return text if text.isdigit() and int(text) > 0 else ""

    @staticmethod
    def _ensure_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)

    def update_status(
        self,
        main_user_id,
        *,
        claim_available,
        cooldown_until_utc=None,
        source="tu",
        observed_at_utc=None,
    ):
        uid = self._normalize_id(main_user_id)
        if not uid:
            return
        now = self._ensure_utc(observed_at_utc) or datetime.datetime.now(datetime.timezone.utc)
        until = self._ensure_utc(cooldown_until_utc)
        if claim_available:
            until = None
        with self._lock:
            self._states[uid] = {
                "known": True,
                "claim_available": bool(claim_available),
                "cooldown_until_utc": until,
                "source": str(source or "tu"),
                "updated_at_utc": now,
            }

    def mark_claimed(
        self,
        main_user_id,
        *,
        claim_interval_minutes=180,
        cooldown_until_utc=None,
        source="claim",
        observed_at_utc=None,
    ):
        uid = self._normalize_id(main_user_id)
        if not uid:
            return
        now = self._ensure_utc(observed_at_utc) or datetime.datetime.now(datetime.timezone.utc)
        until = self._ensure_utc(cooldown_until_utc)
        if until is None:
            mins = max(1, int(claim_interval_minutes or 180))
            until = now + datetime.timedelta(minutes=mins)
        with self._lock:
            self._states[uid] = {
                "known": True,
                "claim_available": False,
                "cooldown_until_utc": until,
                "source": str(source or "claim"),
                "updated_at_utc": now,
            }

    def get_status(self, main_user_id, now_utc=None):
        uid = self._normalize_id(main_user_id)
        now = self._ensure_utc(now_utc) or datetime.datetime.now(datetime.timezone.utc)
        if not uid:
            return {
                "main_user_id": "",
                "known": False,
                "claim_available": None,
                "on_cooldown": False,
                "cooldown_until_utc": None,
                "cooldown_reset_seconds": 0,
                "source": "unconfigured",
                "updated_at_utc": None,
            }
        with self._lock:
            entry = dict(self._states.get(uid) or {})
            if not entry or not entry.get("known"):
                return {
                    "main_user_id": uid,
                    "known": False,
                    "claim_available": None,
                    "on_cooldown": False,
                    "cooldown_until_utc": None,
                    "cooldown_reset_seconds": 0,
                    "source": "unknown",
                    "updated_at_utc": None,
                }
            until = entry.get("cooldown_until_utc")
            claim_available = entry.get("claim_available")
            if claim_available is False and until is not None and now >= until:
                claim_available = True
                until = None
                entry["claim_available"] = True
                entry["cooldown_until_utc"] = None
                entry["source"] = "reset-elapsed"
                self._states[uid] = entry

            reset_secs = (
                max(0, int((until - now).total_seconds()))
                if (claim_available is False and until is not None and until > now)
                else 0
            )
            return {
                "main_user_id": uid,
                "known": True,
                "claim_available": bool(claim_available),
                "on_cooldown": claim_available is False,
                "cooldown_until_utc": until,
                "cooldown_reset_seconds": reset_secs,
                "source": entry.get("source") or "tu",
                "updated_at_utc": entry.get("updated_at_utc"),
            }

    def is_claim_allowed(self, main_user_id, *, unknown_policy="hold", now_utc=None):
        """Return (allowed, reason) for an alt gated on main account cooldown."""
        status = self.get_status(main_user_id, now_utc=now_utc)
        if not status["main_user_id"]:
            return True, "no main account id configured"
        if not status["known"]:
            if str(unknown_policy or "hold").strip().lower() == "allow":
                return True, "main claim state unknown (policy=allow)"
            return False, "main account claim status not yet confirmed (holding claims)"
        if status["on_cooldown"]:
            return True, f"main account {status['main_user_id']} is on claim cooldown"
        return False, f"main account {status['main_user_id']} still has claim available"

    def clear(self):
        with self._lock:
            self._states.clear()
