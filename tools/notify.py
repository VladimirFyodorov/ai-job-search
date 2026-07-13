"""Notification utility functions for hunter-v2 skills.

Each function accepts an optional ``sender`` callable that receives the
formatted message string.  When ``sender`` is ``None`` the call is a no-op,
which makes the functions safe to call from contexts where no transport is
available (tests, dry-run, etc.).

No top-level imports of Claude Code runtime symbols are used here.
"""


def notify_start(skill_name: str, sender=None) -> None:
    """Send a start notification before skill work begins.

    Args:
        skill_name: Name of the skill being invoked (e.g. ``"scrape"``).
        sender: Callable that accepts a single string argument.  Pass ``None``
            to suppress output.
    """
    if sender is not None:
        sender(f"⚡ Начинаю /{skill_name}...")


def notify_progress(message: str, sender=None) -> None:
    """Forward a progress message to the sender unchanged.

    Args:
        message: Arbitrary progress string (may include emoji).
        sender: Callable that accepts a single string argument.
    """
    if sender is not None:
        sender(message)


def notify_done(skill_name: str, summary: str, sender=None) -> None:
    """Send a completion notification with a result summary.

    Args:
        skill_name: Name of the skill that finished.
        summary: Human-readable result summary (e.g. ``"5 вакансий"``).
        sender: Callable that accepts a single string argument.
    """
    if sender is not None:
        sender(f"✅ /{skill_name} готово: {summary}")


def notify_error(
    skill_name: str,
    user_msg_ru: str,
    admin_msg_en: str = None,
    sender=None,
    admin_sender=None,
) -> None:
    """Send an error notification.

    The user-facing message is sent in Russian via ``sender``.  An optional
    English diagnostic message is sent to ``admin_sender`` only when both
    ``admin_sender`` and ``admin_msg_en`` are provided.

    Args:
        skill_name: Name of the skill that failed.
        user_msg_ru: Russian error description for the end-user.
        admin_msg_en: English diagnostic string for admin channel (optional).
        sender: Callable for the user-facing message.
        admin_sender: Callable for the admin-facing message.
    """
    if sender is not None:
        sender(f"❌ /{skill_name}: {user_msg_ru}")
    if admin_sender is not None and admin_msg_en is not None:
        admin_sender(admin_msg_en)
