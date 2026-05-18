import secrets
import string

from django.contrib.auth.models import User

from accounts.models import SocialAccount


def _random_username(prefix: str) -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"{prefix}_{suffix}"


def get_or_create_user_from_social(
    provider: str,
    provider_user_id: str,
    email: str | None,
    display_name: str | None,
    avatar_url: str = "",
    extra_data: dict | None = None,
) -> tuple[User, SocialAccount, bool]:
    extra_data = extra_data or {}
    account = (
        SocialAccount.objects.select_related("user")
        .filter(provider=provider, provider_user_id=provider_user_id)
        .first()
    )
    if account:
        updated = False
        if email and account.email != email:
            account.email = email
            updated = True
        if display_name and account.display_name != display_name:
            account.display_name = display_name
            updated = True
        if avatar_url and account.avatar_url != avatar_url:
            account.avatar_url = avatar_url
            updated = True
        if extra_data:
            account.extra_data = {**account.extra_data, **extra_data}
            updated = True
        if updated:
            account.save()
        return account.user, account, False

    user = None
    is_new = False
    if email:
        user = User.objects.filter(email__iexact=email).first()

    if not user:
        username_base = (email or display_name or provider_user_id).split("@")[0]
        username_base = "".join(c for c in username_base if c.isalnum() or c in "._-")[:20] or provider
        username = _random_username(username_base)
        user = User.objects.create_user(
            username=username,
            email=email or "",
            first_name=(display_name or "").split()[0][:30] if display_name else "",
            last_name=" ".join((display_name or "").split()[1:])[:150] if display_name else "",
        )
        is_new = True

    account = SocialAccount.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email or "",
        display_name=display_name or "",
        avatar_url=avatar_url,
        extra_data=extra_data,
    )
    return user, account, is_new


def get_or_create_user_from_otp(
    identifier: str,
    username: str | None = None,
    purpose: str = "login",
) -> tuple[User, bool]:
    identifier = identifier.strip().lower()
    is_email = "@" in identifier

    if is_email:
        user = User.objects.filter(email__iexact=identifier).first()
    else:
        user = User.objects.filter(username=identifier).first()

    if user:
        return user, False

    if purpose == "login":
        raise ValueError("No account found for this identifier. Use purpose=signup to register.")

    if is_email:
        base = identifier.split("@")[0]
        uname = username or _random_username(base[:20] or "user")
        user = User.objects.create_user(username=uname, email=identifier)
    else:
        uname = username or identifier
        if User.objects.filter(username=uname).exists():
            uname = _random_username(uname[:20])
        user = User.objects.create_user(username=uname)
    return user, True
