from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user, get_user_roles, require_roles
from ..database import get_db
from ..models import Role, User, UserRole

router = APIRouter(tags=["rbac"])

PERMISSIONS_BY_ROLE = {
    "admin": [
        "assign_roles",
        "delete_users",
        "view_analytics",
        "chat_access",
    ],
    "editor": [
        "edit_content",
        "chat_access",
    ],
    "viewer": [
        "view_content",
        "chat_access",
    ],
}


@router.post("/roles/assign/", response_model=schemas.RoleAssignResponse)
def assign_role(
    data: schemas.RoleAssignRequest,
    _: User = Depends(require_roles("Admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    normalized = data.role.strip().capitalize()
    role = db.query(Role).filter(Role.name == normalized).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    db.query(UserRole).filter(UserRole.user_id == user.id).delete()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return schemas.RoleAssignResponse(message="Role assigned successfully", user_id=user.id, role=role.name)


@router.get("/users/permissions/", response_model=schemas.UserPermissionsResponse)
def user_permissions(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roles = get_user_roles(current.id, db)
    permissions: set[str] = set()
    for role in roles:
        permissions.update(PERMISSIONS_BY_ROLE.get(role.lower(), []))
    return schemas.UserPermissionsResponse(
        user_id=current.id,
        username=current.username,
        roles=roles,
        permissions=sorted(permissions),
    )


@router.delete("/users/{user_id}/", response_model=schemas.DeleteUserResponse)
def delete_user(
    user_id: int,
    current: User = Depends(require_roles("Admin")),
    db: Session = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot delete self")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return schemas.DeleteUserResponse(message="User deleted successfully", deleted_user_id=user_id)
