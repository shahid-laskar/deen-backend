"""
Learning Router — Phase 9
=========================
GET  /learning/paths             — list available courses
GET  /learning/paths/{id}        — path details + user progress
POST /learning/lessons/{id}/complete — mark lesson done, get XP
GET  /learning/vocab             — list words to review today
POST /learning/vocab/{id}/review — submit Leitner spaced repetition review
POST /learning/seed              — seed test courses
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func

from app.core.dependencies import CurrentUser, DB, AdminUser
from app.models.learning import LearningPath, LearningModule, LessonContent, UserLearningProgress, VocabWord, UserVocab
from app.models.gamification import UserXP, XPSource

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/paths")
async def list_paths(db: DB):
    result = await db.execute(select(LearningPath).where(LearningPath.is_active == True).order_by(LearningPath.order_index))
    return result.scalars().all()


@router.get("/paths/{path_id}")
async def path_details(path_id: uuid.UUID, current_user: CurrentUser, db: DB):
    path = await db.get(LearningPath, path_id)
    if not path:
        raise HTTPException(404, "Path not found")

    # Fetch modules and lessons
    modules_res = await db.execute(select(LearningModule).where(LearningModule.path_id == path_id).order_by(LearningModule.order_index))
    modules = modules_res.scalars().all()

    # Get user progress
    progress_res = await db.execute(
        select(UserLearningProgress.lesson_id)
        .join(LessonContent, UserLearningProgress.lesson_id == LessonContent.id)
        .join(LearningModule, LessonContent.module_id == LearningModule.id)
        .where(UserLearningProgress.user_id == current_user.id, LearningModule.path_id == path_id)
    )
    completed_lesson_ids = set(progress_res.scalars().all())

    # Build response tree
    mod_list = []
    total_lessons = 0
    for m in modules:
        lessons_res = await db.execute(select(LessonContent).where(LessonContent.module_id == m.id).order_by(LessonContent.order_index))
        lessons = [{"id": str(L.id), "title": L.title, "content_type": L.content_type, "xp_reward": L.xp_reward, "completed": L.id in completed_lesson_ids} for L in lessons_res.scalars().all()]
        total_lessons += len(lessons)
        mod_list.append({"id": str(m.id), "title": m.title, "description": m.description, "lessons": lessons})

    progress_pct = round((len(completed_lesson_ids) / total_lessons) * 100) if total_lessons else 0

    return {
        "id": str(path.id), "title": path.title, "description": path.description,
        "difficulty": path.difficulty, "icon": path.icon,
        "progress_pct": progress_pct,
        "modules": mod_list
    }


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id: uuid.UUID, current_user: CurrentUser, db: DB):
    lesson = await db.get(LessonContent, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    existing = await db.execute(select(UserLearningProgress).where(UserLearningProgress.user_id == current_user.id, UserLearningProgress.lesson_id == lesson_id))
    if existing.scalar():
        return {"message": "Already completed", "xp_rewarded": 0}

    prog = UserLearningProgress(user_id=current_user.id, lesson_id=lesson_id, completed_at=datetime.now(timezone.utc))
    db.add(prog)

    # Award Gamification XP (Generic quest_complete source for now, or new source type)
    xp_event = UserXP(user_id=current_user.id, source=XPSource.QUEST_COMPLETE, amount=lesson.xp_reward, note=f"Lesson: {lesson.title}")
    db.add(xp_event)

    await db.commit()
    return {"message": "Lesson completed", "xp_rewarded": lesson.xp_reward}


@router.get("/vocab/review")
async def get_vocab_due(current_user: CurrentUser, db: DB):
    now = datetime.now(timezone.utc)
    # Find all due vocab
    result = await db.execute(
        select(UserVocab, VocabWord)
        .join(VocabWord, UserVocab.word_id == VocabWord.id)
        .where(UserVocab.user_id == current_user.id, UserVocab.next_review_at <= now)
        .order_by(UserVocab.next_review_at)
        .limit(20)
    )
    words = [{"user_vocab_id": str(uv.id), "word_id": str(w.id), "arabic": w.arabic, "translation": w.translation, "transliteration": w.transliteration, "level": uv.box_level} for uv, w in result.all()]
    return words


@router.post("/vocab/{user_vocab_id}/review")
async def review_vocab(user_vocab_id: uuid.UUID, remembered: bool, current_user: CurrentUser, db: DB):
    uv = await db.get(UserVocab, user_vocab_id)
    if not uv or uv.user_id != current_user.id:
        raise HTTPException(404, "Vocab tracking not found")

    # Spaced Repetition (Leitner) logic
    if remembered:
        uv.box_level = min(5, uv.box_level + 1)
    else:
        uv.box_level = max(0, uv.box_level - 1)

    intervals = {0: 0, 1: 1, 2: 3, 3: 7, 4: 14, 5: 30} # days
    uv.next_review_at = datetime.now(timezone.utc) + timedelta(days=intervals[uv.box_level])

    await db.commit()
    return {"box_level": uv.box_level, "next_review_at": uv.next_review_at.isoformat()}


@router.post("/seed")
async def seed_learning(db: DB, current_user: AdminUser):
    # 1. Vocab words
    words = [
        {"arabic": "اللَّهُ", "transliteration": "Allahu", "translation": "God"},
        {"arabic": "رَبِّ", "transliteration": "Rabbi", "translation": "Lord"},
        {"arabic": "رَحْمَٰنِ", "transliteration": "Rahman", "translation": "Most Merciful"},
        {"arabic": "كِتَاب", "transliteration": "Kitab", "translation": "Book"},
        {"arabic": "صَلَاة", "transliteration": "Salah", "translation": "Prayer"},
    ]
    for w in words:
        existing = await db.execute(select(VocabWord).where(VocabWord.arabic == w["arabic"]))
        if not existing.scalar():
            db.add(VocabWord(**w))

    # 2. Learning Path
    existing_path = await db.execute(select(LearningPath).where(LearningPath.title == "Essentials of Faith"))
    if not existing_path.scalar():
        path = LearningPath(title="Essentials of Faith", description="Core Islamic beliefs (Aqeedah) for beginners.", icon="🌱", difficulty="beginner")
        db.add(path)
        await db.flush()

        m1 = LearningModule(path_id=path.id, title="1. Tawheed (Oneness of Allah)", description="Understanding the core of Islam.", order_index=0)
        db.add(m1)
        await db.flush()

        l1 = LessonContent(module_id=m1.id, title="What is Tawheed?", content_type="article", content_data={"text": "Tawheed is the indivisible oneness concept of monotheism in Islam..."}, xp_reward=30, order_index=0)
        l2 = LessonContent(module_id=m1.id, title="The 3 Categories of Tawheed", content_type="article", content_data={"text": "Tawheed ar-Rububiyyah, Uluhiyyah, and Asma was-Sifaat..."}, xp_reward=40, order_index=1)
        l3 = LessonContent(module_id=m1.id, title="Knowledge Check: Tawheed", content_type="quiz", content_data={"questions": [{"Q": "What does Tawheed mean?", "A": "Oneness of God"}]}, xp_reward=50, order_index=2)
        db.add_all([l1, l2, l3])

    existing_arabic = await db.execute(select(LearningPath).where(LearningPath.title == "Madinah Arabic Grammar (Book 1)"))
    if not existing_arabic.scalar():
        ar_path = LearningPath(title="Madinah Arabic Grammar (Book 1)", description="Learn classical Arabic grammar used in the Quran and Hadith.", icon="📖", difficulty="intermediate")
        db.add(ar_path)
        await db.flush()

        arm1 = LearningModule(path_id=ar_path.id, title="Lesson 1: Demonstrative Pronouns", description="Introduction to Haa-thaa (هَذَا) and basic sentence structure.", order_index=0)
        db.add(arm1)
        await db.flush()

        arl1 = LessonContent(module_id=arm1.id, title="This is a book (هذا كتاب)", content_type="article", content_data={"text": "## Demonstrative Pronoun: Haa-thaa (هَذَا)\n\nIn Arabic, `هَذَا` means 'This is'. It is used to point to masculine, singular objects nearby.\n\n### Examples:\n- **هَذَا بَيْتٌ** (This is a house)\n- **هَذَا مَسْجِدٌ** (This is a mosque)\n- **هَذَا بَابٌ** (This is a door)\n\nNotice how the Arabic sentence does not use 'is'. The 'is' is implied. A simple nominal sentence in Arabic consists of a subject (Mubtada') and a predicate (Khabar)."}, xp_reward=40, order_index=0)
        arl2 = LessonContent(module_id=arm1.id, title="Questioning: What is this? (مَا هَذَا؟)", content_type="article", content_data={"text": "## Asking Questions\n\nTo ask 'What is this?', you say **مَا هَذَا؟** (Maa haa-thaa?).\n\n- **مَا** means 'What'\n- **هَذَا** means 'This'\n\n### Practice Dialogue:\n**A:** مَا هَذَا؟ (What is this?)\n**B:** هَذَا قَلَمٌ. (This is a pen.)"}, xp_reward=40, order_index=1)
        arl3 = LessonContent(module_id=arm1.id, title="Is this a house? (أَهَذَا بَيْتٌ؟)", content_type="article", content_data={"text": "## The Questioning Particle (أَ)\n\nBy placing an Alif with a Hamzah (أَ) in front of a sentence, it turns it into a Yes/No question.\n\n**أَهَذَا بَيْتٌ؟** (Is this a house?)\n\n### Responses:\n- **نَعَمْ** (Yes): نَعَمْ ، هَذَا بَيْتٌ.\n- **لاَ** (No): لاَ ، هَذَا مَسْجِدٌ. (No, this is a mosque.)"}, xp_reward=50, order_index=2)
        arl4 = LessonContent(module_id=arm1.id, title="Review Quiz: Lesson 1", content_type="quiz", content_data={"questions": [{"Q": "How do you say 'This is a door' in Arabic?", "A": "هَذَا بَابٌ"}, {"Q": "How do you ask 'What is this?'", "A": "مَا هَذَا؟"}]}, xp_reward=60, order_index=3)

        db.add_all([arl1, arl2, arl3, arl4])

    existing_hadith = await db.execute(select(LearningPath).where(LearningPath.title == "40 Hadith of An-Nawawi"))
    if not existing_hadith.scalar():
        h_path = LearningPath(title="40 Hadith of An-Nawawi", description="A compilation of the most important sayings and actions of the Prophet (ﷺ).", icon="💠", difficulty="beginner")
        db.add(h_path)
        await db.flush()

        hm1 = LearningModule(path_id=h_path.id, title="Module 1: Intentions and Pillars", description="Foundational hadith regarding inner and outer faith.", order_index=0)
        db.add(hm1)
        await db.flush()

        hl1 = LessonContent(module_id=hm1.id, title="Hadith 1: Actions are by Intentions", content_type="article", content_data={"text": "## Hadith 1: Actions are by Intentions\n\nOn the authority of Commander of the Faithful, Abu Hafs 'Umar bin al-Khattab (may Allah be pleased with him), who said: I heard the Messenger of Allah (ﷺ) say:\n\n> 'Actions are but by intentions and every man shall have only that which he intended. Thus he whose migration was for Allah and His Messenger, his migration was for Allah and His Messenger, and he whose migration was to achieve some worldly benefit or to take some woman in marriage, his migration was for that for which he migrated.'\n\n[Related by Bukhari & Muslim]\n\n### Key Lessons:\n1. **Sincerity (Ikhlas)**: Every action must be for the sake of Allah alone.\n2. **The Heart**: The intention is located in the heart, not spoken on the tongue.\n3. **Reward**: You are rewarded based on your motive, even if the action is small."}, xp_reward=50, order_index=0)
        hl2 = LessonContent(module_id=hm1.id, title="Hadith 2: Islam, Iman, and Ihsan", content_type="article", content_data={"text": "## Hadith 2: The Hadith of Jibril\n\nThis famous Hadith records the Angel Jibril (Gabriel) coming to the Prophet (ﷺ) to teach the companions their religion.\n\n### Three Levels of Faith:\n- **Islam**: The outward submission (5 Pillars).\n- **Iman**: The inward belief (6 Pillars of Faith).\n- **Ihsan**: Spiritual excellence—to worship Allah as if you see Him.\n\nIt also mentions the signs of the Hour."}, xp_reward=60, order_index=1)
        
        db.add_all([hl1, hl2])

    await db.commit()
    return {"message": "Learning Hub seeded successfully"}
