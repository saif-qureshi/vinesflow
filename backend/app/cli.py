from __future__ import annotations

from datetime import UTC

import typer
from sqlalchemy import func, select

import app.db.base  # noqa: F401  (register all mappers)
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import RefreshSession
from app.modules.orgs.models import Membership, Organization
from app.modules.orgs.service import OrgService
from app.modules.rbac.models import Role
from app.modules.rbac.service import RbacService
from app.modules.users.models import User

app = typer.Typer(no_args_is_help=True, help="Vineflow backend management CLI")
users_app = typer.Typer(no_args_is_help=True, help="Manage users")
orgs_app = typer.Typer(no_args_is_help=True, help="Manage organizations")
roles_app = typer.Typer(no_args_is_help=True, help="Inspect roles")
db_app = typer.Typer(no_args_is_help=True, help="Database tasks")
fbr_app = typer.Typer(no_args_is_help=True, help="FBR digital invoicing")
accounting_app = typer.Typer(no_args_is_help=True, help="Accounting / Books")
app.add_typer(users_app, name="users")
app.add_typer(orgs_app, name="orgs")
app.add_typer(roles_app, name="roles")
app.add_typer(db_app, name="db")
app.add_typer(fbr_app, name="fbr")
app.add_typer(accounting_app, name="accounting")


def _get_user(db, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        typer.secho(f"User not found: {email}", fg=typer.colors.RED)
        raise typer.Exit(1)
    return user


def _get_org(db, ref: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == ref))
    if org is None and ref.isdigit():
        org = db.get(Organization, int(ref))
    if org is None:
        typer.secho(f"Org not found: {ref}", fg=typer.colors.RED)
        raise typer.Exit(1)
    return org


@users_app.command("create")
def users_create(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    full_name: str = typer.Option(None),
    org: str = typer.Option(None, help="Name of an org to create with this user as owner"),
    superuser: bool = typer.Option(False, help="Grant platform superuser"),
):
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.email == email.lower())):
            typer.secho("Email already exists", fg=typer.colors.RED)
            raise typer.Exit(1)
        user = User(
            email=email.lower(),
            full_name=full_name,
            hashed_password=hash_password(password),
            is_superuser=superuser,
        )
        db.add(user)
        db.flush()
        if org:
            created = OrgService(db).create_org_with_owner(owner=user, name=org)
            typer.echo(f"  org: {created.name} (slug={created.slug})")
        db.commit()
        typer.secho(f"Created user {user.email} (id={user.id}, superuser={superuser})", fg=typer.colors.GREEN)
    finally:
        db.close()


@users_app.command("list")
def users_list():
    db = SessionLocal()
    try:
        for u in db.scalars(select(User).order_by(User.id)).all():
            orgs = db.scalar(select(func.count()).select_from(Membership).where(Membership.user_id == u.id))
            flag = " [superuser]" if u.is_superuser else ""
            typer.echo(f"  {u.id:>3}  {u.email:28} orgs={orgs} active={u.is_active}{flag}")
    finally:
        db.close()


@users_app.command("set-password")
def users_set_password(
    email: str,
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
):
    db = SessionLocal()
    try:
        user = _get_user(db, email)
        user.hashed_password = hash_password(password)
        db.commit()
        typer.secho(f"Password updated for {user.email}", fg=typer.colors.GREEN)
    finally:
        db.close()


@users_app.command("set-superuser")
def users_set_superuser(email: str, enable: bool = typer.Option(True)):
    db = SessionLocal()
    try:
        user = _get_user(db, email)
        user.is_superuser = enable
        db.commit()
        typer.secho(f"{user.email} superuser={enable}", fg=typer.colors.GREEN)
    finally:
        db.close()


@orgs_app.command("create")
def orgs_create(name: str, owner_email: str):
    db = SessionLocal()
    try:
        owner = _get_user(db, owner_email)
        org = OrgService(db).create_org_with_owner(owner=owner, name=name)
        db.commit()
        typer.secho(f"Created org {org.name} (slug={org.slug}) owned by {owner.email}", fg=typer.colors.GREEN)
    finally:
        db.close()


@orgs_app.command("list")
def orgs_list():
    db = SessionLocal()
    try:
        for o in db.scalars(select(Organization).order_by(Organization.id)).all():
            members = db.scalar(select(func.count()).select_from(Membership).where(Membership.org_id == o.id))
            typer.echo(f"  {o.id:>3}  {o.name:28} slug={o.slug:20} members={members}")
    finally:
        db.close()


@orgs_app.command("add-member")
def orgs_add_member(org: str, email: str, role_slug: str = typer.Option("member")):
    db = SessionLocal()
    try:
        organization = _get_org(db, org)
        user = _get_user(db, email)
        role = db.scalar(
            select(Role).where(Role.org_id == organization.id, Role.slug == role_slug)
        )
        if role is None:
            typer.secho(f"Role '{role_slug}' not found in org", fg=typer.colors.RED)
            raise typer.Exit(1)
        if db.scalar(
            select(Membership).where(
                Membership.org_id == organization.id, Membership.user_id == user.id
            )
        ):
            typer.secho("Already a member", fg=typer.colors.YELLOW)
            raise typer.Exit(1)
        db.add(Membership(user_id=user.id, org_id=organization.id, role_id=role.id))
        db.commit()
        typer.secho(f"Added {user.email} to {organization.name} as {role_slug}", fg=typer.colors.GREEN)
    finally:
        db.close()


@roles_app.command("list")
def roles_list(org: str):
    db = SessionLocal()
    try:
        organization = _get_org(db, org)
        for r in db.scalars(
            select(Role).where(Role.org_id == organization.id).order_by(Role.id)
        ).all():
            kind = "system" if r.is_system else "custom"
            typer.echo(f"  {r.id:>3}  {r.slug:16} {kind:7} perms={len(r.permissions)}")
    finally:
        db.close()


@roles_app.command("grant")
def roles_grant(org: str, role_slug: str, permission_codes: list[str]):
    db = SessionLocal()
    try:
        organization = _get_org(db, org)
        role = db.scalar(
            select(Role).where(Role.org_id == organization.id, Role.slug == role_slug)
        )
        if role is None:
            typer.secho("Role not found", fg=typer.colors.RED)
            raise typer.Exit(1)
        existing = {p.code for p in role.permissions}
        for perm in RbacService(db).resolve_permissions(list(permission_codes)):
            if perm.code not in existing:
                role.permissions.append(perm)
        db.commit()
        typer.secho(f"Granted {permission_codes} to {role_slug}", fg=typer.colors.GREEN)
    finally:
        db.close()


@fbr_app.command("sync")
def fbr_sync(
    environment: str = typer.Option("production", help="sandbox or production"),
    token: str = typer.Option(None, help="Bearer token (defaults to FBR_REFERENCE_TOKEN)"),
):
    from app.core.config import settings
    from app.core.crypto import decrypt_secret
    from app.modules.fbr.client import FbrClient
    from app.modules.fbr.enums import FbrEnvironment
    from app.modules.fbr.sync import FbrReferenceSyncService
    from app.modules.orgs.models import Organization

    resolved = token or settings.FBR_REFERENCE_TOKEN
    db = SessionLocal()
    try:
        if not resolved:
            org = db.scalar(
                select(Organization).where(Organization.fbr_enabled.is_(True))
            )
            if org is not None:
                resolved = decrypt_secret(
                    org.fbr_production_token if environment == "production" else org.fbr_sandbox_token
                )
        if not resolved:
            typer.secho(
                "No token. Set FBR_REFERENCE_TOKEN, pass --token, or enable FBR on an org.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        client = FbrClient(resolved, FbrEnvironment(environment))
        typer.echo(f"Syncing FBR reference data ({environment})…")
        counts = FbrReferenceSyncService(db, client).sync_all(log=lambda m: typer.echo(f"  {m}"))
        total = sum(counts.values())
        typer.secho(f"Done. {total} rows across {len(counts)} reference types.", fg=typer.colors.GREEN)
    finally:
        db.close()


@fbr_app.command("sync-mappings")
def fbr_sync_mappings(
    environment: str = typer.Option("production", help="sandbox or production"),
    token: str = typer.Option(None, help="Bearer token (defaults to FBR_REFERENCE_TOKEN)"),
    hs_limit: int = typer.Option(None, help="Limit HS codes fetched (for testing)"),
    workers: int = typer.Option(6, help="Concurrent HS_UOM fetchers"),
    skip_hs: bool = typer.Option(False, help="Only sync SRO item serials, skip HS→UoM"),
):
    from app.core.config import settings
    from app.core.crypto import decrypt_secret
    from app.modules.fbr.client import FbrClient
    from app.modules.fbr.enums import FbrEnvironment
    from app.modules.fbr.sync import FbrReferenceSyncService
    from app.modules.orgs.models import Organization

    resolved = token or settings.FBR_REFERENCE_TOKEN
    db = SessionLocal()
    try:
        if not resolved:
            org = db.scalar(select(Organization).where(Organization.fbr_enabled.is_(True)))
            if org is not None:
                resolved = decrypt_secret(
                    org.fbr_production_token if environment == "production" else org.fbr_sandbox_token
                )
        if not resolved:
            typer.secho(
                "No token. Set FBR_REFERENCE_TOKEN, pass --token, or enable FBR on an org.",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        client = FbrClient(resolved, FbrEnvironment(environment))
        svc = FbrReferenceSyncService(db, client)
        typer.echo("Syncing SRO item serials…")
        svc.sync_sro_items(log=lambda m: typer.echo(f"  {m}"))
        if not skip_hs:
            typer.echo("Syncing HS → UoM mappings (resumable)…")
            svc.sync_hs_uom(log=lambda m: typer.echo(f"  {m}"), limit=hs_limit, workers=workers)
        typer.secho("Mappings sync complete.", fg=typer.colors.GREEN)
    finally:
        db.close()


@fbr_app.command("summary")
def fbr_summary():
    from sqlalchemy import func

    from app.modules.fbr.models import FbrReferenceData

    db = SessionLocal()
    try:
        rows = db.execute(
            select(FbrReferenceData.type, func.count()).group_by(FbrReferenceData.type)
        ).all()
        if not rows:
            typer.echo("No FBR reference data cached. Run: vineflow fbr sync")
            return
        for ref_type, count in sorted(rows):
            typer.echo(f"  {ref_type:16} {count}")
    finally:
        db.close()


@accounting_app.command("init")
def accounting_init(org: str = typer.Option("all", help="org slug/id, or 'all'")):
    """Seed the chart of accounts + fiscal calendar for existing orgs (idempotent)."""
    from app.modules.accounting.setup import AccountingSetupService

    db = SessionLocal()
    try:
        targets = (
            db.scalars(select(Organization)).all() if org == "all" else [_get_org(db, org)]
        )
        for organization in targets:
            AccountingSetupService(db).ensure_setup(
                organization.id, organization.fiscal_year_start_month
            )
        db.commit()
        typer.secho(f"Accounting setup ensured for {len(targets)} org(s)", fg=typer.colors.GREEN)
    finally:
        db.close()


@db_app.command("seed")
def db_seed():
    db = SessionLocal()
    try:
        RbacService(db).seed_permissions()
        db.commit()
        typer.secho("Permission catalog seeded", fg=typer.colors.GREEN)
    finally:
        db.close()


@db_app.command("upgrade")
def db_upgrade():
    from alembic.config import Config

    from alembic import command

    command.upgrade(Config("alembic.ini"), "head")


@db_app.command("prune-sessions")
def db_prune_sessions():
    from datetime import datetime

    from sqlalchemy import delete, or_

    db = SessionLocal()
    try:
        result = db.execute(
            delete(RefreshSession).where(
                or_(
                    RefreshSession.expires_at < datetime.now(UTC),
                    RefreshSession.revoked_at.is_not(None),
                )
            )
        )
        db.commit()
        typer.secho(f"Pruned {result.rowcount} expired/revoked sessions", fg=typer.colors.GREEN)
    finally:
        db.close()


if __name__ == "__main__":
    app()
