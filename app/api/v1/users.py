from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.db import get_session
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import ProfileUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", status_code=204)
async def update_me(
    req: ProfileUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    profile = (
        await db.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, full_name="")
        db.add(profile)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    await db.commit()
