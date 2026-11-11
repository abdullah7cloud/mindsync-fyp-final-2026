"""
Account and privacy routes (GDPR-style rights, simplified).

  GET    /account/export    - download EVERYTHING we store about you as JSON ("right of access / portability")
  DELETE /account/wellbeing - erase only your wellbeing-check history
  POST   /account/password  - change the password (needs the current one)
  POST   /account/email     - closed (410): the e-mail is changed in My Profile with a code sent to the new address (see app/profile28)
  DELETE /account           - permanently erase the account and all its data ("right to erasure")

Why these exist: the app stores personal data (e-mail, tasks, energy and wellbeing answers), so a student
must be able to see it and remove it. Deletion asks for the password again so a stolen login token alone
cannot wipe an account, and wrong passwords count towards the same lock-out as the login form.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.assist import models as AM
from app.models import (EnergyCheckin, PasswordResetToken, RecommendationFeedback, SessionLog, Task, TaskOutcome, User,
                        UserSkill, WellbeingCheck)
from app.notifier import build_password_changed_email, deliver_quietly
from app.ratelimit import limiter_key, login_limiter
from app.schemas import ChangeEmail, ChangePassword, DeleteAccount
from app.studio import models as SM
from app.simple import models as XM
from app.profile28 import models as P28
from app.security import hash_password_async, verify_password_async

router = APIRouter(prefix="/account", tags=["account"])


def _iso(value):
    return value.isoformat() if value is not None else None


@router.get("/export")
async def export_my_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Everything stored about the logged-in user. The password hash is deliberately NOT included."""
    tasks = (await db.scalars(select(Task).where(Task.owner_id == user.id).order_by(Task.deadline))).all()
    energy = (await db.scalars(select(EnergyCheckin).where(EnergyCheckin.user_id == user.id)
                               .order_by(EnergyCheckin.created_at))).all()
    wellbeing = (await db.scalars(select(WellbeingCheck).where(WellbeingCheck.user_id == user.id)
                                  .order_by(WellbeingCheck.created_at))).all()
    feedback = (await db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)
                                 .order_by(RecommendationFeedback.created_at))).all()
    skills = (await db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()
    outcomes = (await db.scalars(select(TaskOutcome).where(TaskOutcome.user_id == user.id).order_by(TaskOutcome.created_at))).all()
    sessions = (await db.scalars(select(SessionLog).where(SessionLog.user_id == user.id).order_by(SessionLog.created_at))).all()
    settings_row = await db.get(AM.UserSettings, user.id)
    profile_row = await db.get(AM.UserProfile, user.id)
    metas = (await db.scalars(select(AM.TaskMeta).where(AM.TaskMeta.user_id == user.id))).all()
    plans = (await db.scalars(select(AM.StudyPlan).where(AM.StudyPlan.user_id == user.id).order_by(AM.StudyPlan.created_at))).all()
    plan_sessions = (await db.scalars(select(AM.PlanSession).where(AM.PlanSession.user_id == user.id).order_by(AM.PlanSession.day))).all()
    task_sessions = (await db.scalars(select(AM.TaskSession).where(AM.TaskSession.user_id == user.id).order_by(AM.TaskSession.created_at))).all()
    usage = (await db.scalars(select(AM.AiUsage).where(AM.AiUsage.user_id == user.id).order_by(AM.AiUsage.created_at))).all()
    reminders = (await db.scalars(select(AM.ReminderLog).where(AM.ReminderLog.user_id == user.id).order_by(AM.ReminderLog.created_at))).all()
    reviews = (await db.scalars(select(AM.WeeklyReview).where(AM.WeeklyReview.user_id == user.id).order_by(AM.WeeklyReview.week_start))).all()
    events = (await db.scalars(select(AM.PlanEvent).where(AM.PlanEvent.user_id == user.id).order_by(AM.PlanEvent.created_at))).all()
    notes = (await db.scalars(select(AM.Notification).where(AM.Notification.user_id == user.id).order_by(AM.Notification.created_at))).all()
    packs = (await db.scalars(select(SM.LearningPack).where(SM.LearningPack.user_id == user.id).order_by(SM.LearningPack.created_at))).all()
    pack_qs = (await db.scalars(select(SM.PackQuestion).where(SM.PackQuestion.user_id == user.id).order_by(SM.PackQuestion.position))).all()
    pack_cs = (await db.scalars(select(SM.PackCard).where(SM.PackCard.user_id == user.id).order_by(SM.PackCard.position))).all()
    attempts = (await db.scalars(select(SM.QuizAttempt).where(SM.QuizAttempt.user_id == user.id).order_by(SM.QuizAttempt.created_at))).all()
    s_plans = (await db.scalars(select(XM.SPlan).where(XM.SPlan.user_id == user.id).order_by(XM.SPlan.created_at))).all()
    s_tasks = (await db.scalars(select(XM.STask).where(XM.STask.user_id == user.id).order_by(XM.STask.due_date))).all()
    s_notes = (await db.scalars(select(XM.SNote).where(XM.SNote.user_id == user.id).order_by(XM.SNote.created_at))).all()
    s_docs = (await db.execute(select(XM.SDocument.name, XM.SDocument.size, XM.SDocument.created_at).where(XM.SDocument.user_id == user.id))).all()
    p28 = await db.get(P28.Preferences, user.id)
    has_pic = await db.get(P28.ProfilePicture, user.id) is not None
    return {
        "profile_and_settings": {"email_reminders": bool(p28.remind_enabled) if p28 else False, "reminder_percent": p28.remind_percent if p28 else 30,
                                 "timezone": p28.timezone if p28 else "UTC", "has_profile_picture": has_pic, "note": "the picture itself is not included in this export"},
        "study_plans": [{"subject": p.subject, "topic": p.topic, "notes": p.goal, "target_date": p.target_date.isoformat(), "mood": p.mood, "stress": p.stress,
                         "roadmap": p.roadmap, "made_by": p.source, "created_at": _iso(p.created_at),
                         "tasks": [{"title": t.title, "details": t.details, "date": t.due_date.isoformat(), "start_time": t.start_time, "minutes": t.minutes,
                                    "done": t.done, "done_at": _iso(t.done_at)} for t in s_tasks if t.plan_id == p.id]} for p in s_plans],
        "notebook_notes": [{"title": n.title, "text": n.body, "created_at": _iso(n.created_at), "updated_at": _iso(n.updated_at)} for n in s_notes],
        "notebook_documents": [{"name": d.name, "size_bytes": d.size, "uploaded_at": _iso(d.created_at), "note": "the file itself is not included in this export"} for d in s_docs],
        "roadmap_history": [{"kind": e.kind, "detail": e.detail, "created_at": _iso(e.created_at)} for e in events],
        "roadmap_blocks": [{"day": s.day.isoformat(), "title": s.title or s.label, "subject": s.subject, "planned_minutes": s.minutes,
                            "studied_minutes": s.actual_minutes, "status": s.status, "felt": s.felt, "completed_at": _iso(s.completed_at),
                            "originally_on": s.original_day.isoformat() if s.original_day else None, "added_by_me": s.manual} for s in plan_sessions],
        "in_app_reminders": [{"kind": n.kind, "title": n.title, "text": n.body, "due_on": n.due_on.isoformat() if n.due_on else None,
                              "read": n.read_at is not None, "created_at": _iso(n.created_at)} for n in notes],
        "learning_packs": [{"title": p.title, "source": p.source, "source_name": p.source_name, "status": p.status, "lessons": p.lessons,
                            "made_by": p.provider, "created_at": _iso(p.created_at),
                            "questions": [{"question": q.question, "options": q.options, "answer_index": q.answer_index, "explanation": q.explanation,
                                           "difficulty": q.difficulty} for q in pack_qs if q.pack_id == p.id],
                            "flashcards": [{"front": c.front, "back": c.back, "box": c.box, "due_on": c.due_on.isoformat() if c.due_on else None,
                                            "reviews": c.reviews} for c in pack_cs if c.pack_id == p.id],
                            "quiz_attempts": [{"difficulty": a.difficulty, "correct": a.correct, "total": a.total, "created_at": _iso(a.created_at)}
                                              for a in attempts if a.pack_id == p.id]} for p in packs],
        "settings": settings_row.data if settings_row else {},
        "profile": profile_row.data if profile_row else {},
        "planning_details": [{"task_id": str(m.task_id), "kind": m.kind, "intrinsic_difficulty": m.intrinsic_difficulty,
                              "difficulty_for_you": m.personal_difficulty, "estimate_minutes": [m.est_low, m.est_likely, m.est_high],
                              "minutes_worked": m.done_minutes, "steps": m.stages, "source": m.source, "priority": m.priority} for m in metas],
        "plans": [{"created_at": _iso(p.created_at), "status": p.status, "reason": p.reason, "summary": p.summary} for p in plans],
        "planned_sessions": [{"day": s.day.isoformat(), "task_id": str(s.task_id) if s.task_id else None, "minutes": s.minutes, "label": s.label,
                              "status": s.status} for s in plan_sessions],
        "session_feedback": [{"task_id": str(s.task_id) if s.task_id else None, "kind": s.kind, "planned_minutes": s.planned_minutes,
                              "actual_minutes": s.actual_minutes, "completed": s.completed, "focus": s.focus, "felt_difficulty": s.felt_difficulty,
                              "energy_after": s.energy_after, "length_feel": s.length_feel, "created_at": _iso(s.created_at)} for s in task_sessions],
        "ai_usage": [{"purpose": u.purpose, "provider": u.provider, "model": u.model, "tokens": u.input_tokens + u.output_tokens,
                      "cost_usd": u.cost_usd, "outcome": u.outcome, "created_at": _iso(u.created_at)} for u in usage],
        "reminder_log": [{"kind": r.kind, "status": r.status, "detail": r.detail, "created_at": _iso(r.created_at)} for r in reminders],
        "weekly_reviews": [{"week_start": r.week_start.isoformat(), "text": r.text, "source": r.source} for r in reviews],
        "account": {"email": user.email, "display_name": user.display_name, "email_alerts": user.email_alerts,
                    "created_at": _iso(user.created_at)},
        "tasks": [{"title": t.title, "description": t.description, "category": t.category,
                   "difficulty": t.difficulty, "deadline": _iso(t.deadline), "status": t.status.value,
                   "created_at": _iso(t.created_at), "completed_at": _iso(t.completed_at)} for t in tasks],
        "energy_checkins": [{"energy_level": e.energy_level, "created_at": _iso(e.created_at)} for e in energy],
        "wellbeing_checks": [{"risk_label": w.risk_label, "probabilities": w.probabilities, "answers": w.answers,
                              "model_version": w.model_version, "created_at": _iso(w.created_at)} for w in wellbeing],
        "recommendation_feedback": [{"helpful": f.helpful, "energy_level": f.energy_level,
                                     "difficulty": f.difficulty, "hours_left": f.hours_left,
                                     "burnout_mode": f.burnout_mode, "created_at": _iso(f.created_at)}
                                    for f in feedback],
        "skill_ratings": [{"kind": s.kind, "level": s.level} for s in skills],
        "task_outcomes": [{"kind": o.kind, "estimated_minutes": o.raw_minutes, "actual_minutes": o.actual_minutes,
                           "felt_difficulty": o.felt, "created_at": _iso(o.created_at)} for o in outcomes],
        "study_sessions": [{"kind": s.kind, "minutes": s.minutes, "completed": s.completed, "focus": s.focus,
                            "created_at": _iso(s.created_at)} for s in sessions],
    }


@router.delete("/wellbeing", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wellbeing_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    """Remove all wellbeing results and daily mood check-ins (also ends any Burnout Mode that was triggered by one)."""
    await db.execute(delete(WellbeingCheck).where(WellbeingCheck.user_id == user.id))
    prow = await db.get(AM.UserProfile, user.id)          # the optional daily mood / stress check-ins are wellbeing history too
    if prow is not None and (prow.data or {}).get("mood_log"):
        prow.data = {**prow.data, "mood_log": []}
    await db.commit()


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: ChangePassword, request: Request, background: BackgroundTasks,
                          user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    """Change the password while logged in. The current password is asked for again (a stolen login token alone is not enough)."""
    key = limiter_key(user.email, request.client.host if request.client else None)
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many wrong passwords. Try again later.",
                            headers={"Retry-After": str(wait)})
    if not await verify_password_async(payload.current_password, user.password_hash):
        login_limiter.record_failure(key)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your current password is not correct.")
    if payload.new_password == payload.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please choose a password that is different from the current one.")
    user.password_hash = await hash_password_async(payload.new_password)
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))   # old reset links die too
    await db.commit()
    login_limiter.reset(key)
    background.add_task(deliver_quietly, build_password_changed_email(user), "password changed")


@router.post("/email")
async def change_email(payload: ChangeEmail, user: User = Depends(get_current_user)) -> dict:
    """Retired in Update 28: changing the sign-in e-mail now needs a code that is e-mailed to the NEW address (POST /my/email/start and /my/email/confirm).
    The old password-only route is closed on purpose, so a stolen login plus password cannot move an account to an address the owner does not control."""
    raise HTTPException(status.HTTP_410_GONE, "Changing your e-mail now needs a confirmation code. Please use My Profile in MindSync.")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(payload: DeleteAccount, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> None:
    key = limiter_key(user.email, request.client.host if request.client else None)
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many wrong passwords. Try again later.",
                            headers={"Retry-After": str(wait)})
    if not await verify_password_async(payload.password, user.password_hash):
        login_limiter.record_failure(key)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password is not correct.")
    uid = user.id
    # Explicit deletes (children first) so this works on every database, even where ON DELETE CASCADE is off.
    for model, column in ((XM.STask, XM.STask.user_id), (XM.SPlan, XM.SPlan.user_id), (XM.SNote, XM.SNote.user_id), (XM.SDocument, XM.SDocument.user_id),
                          (SM.QuizAttempt, SM.QuizAttempt.user_id), (SM.PackQuestion, SM.PackQuestion.user_id), (SM.PackCard, SM.PackCard.user_id),
                          (SM.LearningPack, SM.LearningPack.user_id), (AM.PlanEvent, AM.PlanEvent.user_id), (AM.Notification, AM.Notification.user_id),
                          (AM.PlanSession, AM.PlanSession.user_id), (AM.StudyPlan, AM.StudyPlan.user_id), (AM.TaskSession, AM.TaskSession.user_id),
                          (AM.TaskMeta, AM.TaskMeta.user_id), (AM.UserSettings, AM.UserSettings.user_id), (AM.UserProfile, AM.UserProfile.user_id),
                          (AM.AiUsage, AM.AiUsage.user_id), (AM.ReminderLog, AM.ReminderLog.user_id), (AM.WeeklyReview, AM.WeeklyReview.user_id),
                          (PasswordResetToken, PasswordResetToken.user_id), (Task, Task.owner_id),
                          (P28.ProfilePicture, P28.ProfilePicture.user_id), (P28.Preferences, P28.Preferences.user_id), (P28.EmailChange, P28.EmailChange.user_id),
                          (P28.TaskReminder, P28.TaskReminder.user_id),
                          (EnergyCheckin, EnergyCheckin.user_id),
                          (WellbeingCheck, WellbeingCheck.user_id),
                          (RecommendationFeedback, RecommendationFeedback.user_id),
                          (TaskOutcome, TaskOutcome.user_id), (SessionLog, SessionLog.user_id), (UserSkill, UserSkill.user_id)):
        await db.execute(delete(model).where(column == uid))
    await db.execute(delete(User).where(User.id == uid))
    await db.commit()
    login_limiter.reset(key)
