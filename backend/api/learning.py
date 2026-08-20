from flask import Blueprint, request, jsonify, current_app, make_response, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, decode_token
import base64
from io import BytesIO
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from backend.models.user import User, db
from backend.models.course import Course, course_students
from backend.models.learning import LearningRecord, ChatHistory, KnowledgeBaseQueue
from backend.models.material import Material
from backend.models.assessment import Assessment, StudentAnswer, AssessmentSubmission
from backend.models.classroom import TeacherClass, teacher_class_students, assessment_publish_classes
from backend.models.student_quiz import StudentAIQuiz
import hashlib
import requests
import openai
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from dotenv import load_dotenv
import time
import uuid
import threading
import functools
from backend.api.rag_ai import (
    cleanup_stale_material_and_queue_records,
    get_api_config,
    purge_knowledge_assets_for_material,
    purge_knowledge_assets_for_queue_item,
)
from backend.api.auth import build_cors_preflight_response
from backend.config.model_routing import get_model_candidates
from backend.rag.chapter_generation_from_material import (
    apply_generated_chapters,
    load_course_chapters,
    normalize_generated_chapters,
    preview_generate_chapters_from_material,
)
from backend.rag.parsers.docx_parser import extract_lines_from_parse_result, parse_docx
from backend.rag.parsers.pdf_parser import parse_pdf
from backend.rag.parsers.ppt_parser import parse_ppt
from sqlalchemy import func, desc, and_, or_

learning_bp = Blueprint('learning', __name__)
OFFICE_PREVIEW_EXTENSIONS = {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}
COURSE_ANALYTICS_KEYWORD_CACHE = {}
DEMO_STUDENT_ANALYTICS_SNAPSHOT = {
    'overallProgress': 68,
    'weeklyLearningTime': 7.5,
    'previousWeekTime': 5.2,
    'completedCourses': 3,
    'inProgressCourses': 2,
    'notStartedCourses': 1,
    'trendData': {
        'week': [
            {'label': '周一', 'value': 25},
            {'label': '周二', 'value': 18},
            {'label': '周三', 'value': 30},
            {'label': '周四', 'value': 22},
            {'label': '周五', 'value': 15},
            {'label': '周六', 'value': 10},
            {'label': '周日', 'value': 5},
        ],
        'month': [
            {'label': '第1周', 'value': 20},
            {'label': '第2周', 'value': 25},
            {'label': '第3周', 'value': 18},
            {'label': '第4周', 'value': 30},
        ],
        'year': [
            {'label': '1月', 'value': 15},
            {'label': '2月', 'value': 20},
            {'label': '3月', 'value': 25},
            {'label': '4月', 'value': 18},
            {'label': '5月', 'value': 30},
            {'label': '6月', 'value': 22},
        ],
    },
    'knowledgePoints': [
        {'label': '编程基础', 'value': 85},
        {'label': '数据结构', 'value': 65},
        {'label': '算法设计', 'value': 70},
        {'label': '数据库', 'value': 90},
        {'label': '网络原理', 'value': 60},
        {'label': '软件工程', 'value': 75},
    ],
    'courseDetails': [
        {'progress': 100, 'learningTime': 18.5, 'lastActivity': '2026-04-27', 'score': 92},
        {'progress': 82, 'learningTime': 14.0, 'lastActivity': '2026-04-26', 'score': 88},
        {'progress': 68, 'learningTime': 10.5, 'lastActivity': '2026-04-25', 'score': 84},
        {'progress': 41, 'learningTime': 6.0, 'lastActivity': '2026-04-24', 'score': 79},
        {'progress': 0, 'learningTime': 0.0, 'lastActivity': '未学习', 'score': 0},
        {'progress': 100, 'learningTime': 20.0, 'lastActivity': '2026-04-23', 'score': 95},
    ],
}
DEMO_STUDENT_AI_ANALYSIS = {
    'strengths': [
        '在数据结构与算法课程中表现稳定，整体完成度保持在较高水平',
        '学习节奏连续，近期学习趋势保持活跃',
        '编程基础相关知识点掌握较扎实，核心内容理解较好',
    ],
    'improvements': [
        '网络原理相关知识点仍有提升空间，建议优先补强薄弱章节',
        '部分课程仍处于进行中，建议尽快完成阶段性学习任务',
        '建议增加综合练习和阶段复盘，提升知识迁移能力',
    ],
    'suggestions': [
        '优先复习网络原理中的协议栈、分层模型与典型应用场景',
        '为每门进行中的课程设置固定学习时段，保持进度连续推进',
        '结合课程练习或小项目，把理论知识转化为可操作成果',
        '每周安排一次错题和重点知识回顾，巩固已掌握内容',
    ],
}

def format_file_size(file_size):
    if file_size < 1024:
        return f"{file_size}B"
    if file_size < 1024 * 1024:
        return f"{file_size / 1024:.1f}KB"
    return f"{file_size / (1024 * 1024):.1f}MB"

def _round_hours(total_seconds):
    return round((total_seconds or 0) / 3600, 1)

def _safe_date_label(raw_date):
    if not raw_date:
        return '未学习'
    if isinstance(raw_date, datetime):
        return raw_date.strftime('%Y-%m-%d')
    return str(raw_date)

def _parse_activity_detail_json(activity_detail):
    if not activity_detail:
        return {}
    if isinstance(activity_detail, dict):
        return activity_detail
    if not isinstance(activity_detail, str):
        return {}

    stripped = activity_detail.strip()
    if not stripped:
        return {}
    if stripped.startswith('{') or stripped.startswith('['):
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}

def _build_material_view_key(record):
    detail = _parse_activity_detail_json(record.activity_detail)
    for key in ('material_id', 'id'):
        if detail.get(key):
            return f"id:{detail[key]}"
    for key in ('file_path', 'path', 'title', 'name'):
        if detail.get(key):
            return f"{key}:{detail[key]}"
    if record.activity_detail:
        return str(record.activity_detail)
    return None

def _get_knowledge_labels_for_course(course):
    category = str(getattr(course, 'category', '') or '').lower()
    if '计算机' in category or '编程' in category:
        return ['编程基础', '数据结构', '算法设计', '数据库', '网络原理', '软件工程']
    if '数学' in category:
        return ['微积分', '线性代数', '概率论', '离散数学', '统计学', '优化理论']
    if '物理' in category:
        return ['力学', '热学', '光学', '电磁学', '量子力学', '热力学']
    if '语言' in category:
        return ['语法结构', '词汇运用', '阅读理解', '写作技巧', '口语表达', '学术写作']
    return ['基础理论', '实践应用', '分析能力', '解决问题', '创新思维', '专业素养']

def _build_course_knowledge_points(course, progress, learning_time, score):
    if progress <= 0 and learning_time <= 0 and score <= 0:
        return []

    labels = _get_knowledge_labels_for_course(course)
    baseline = max(progress, score, min(100, int(round(learning_time * 8))))
    time_bonus = min(10, int(round(learning_time)))
    knowledge_points = []

    for index, label in enumerate(labels[:6]):
        seed = sum(ord(char) for char in f'{course.id}:{label}') % 9
        value = int(round(baseline * (0.75 + index * 0.03) + time_bonus + seed - 10))
        knowledge_points.append({
            'label': label,
            'value': max(35, min(100, value)),
        })

    return knowledge_points

def _aggregate_knowledge_points(knowledge_points_by_course):
    aggregated = {}
    order = []

    for points in knowledge_points_by_course.values():
        for point in points:
            label = point.get('label')
            value = point.get('value')
            if not label:
                continue
            if label not in aggregated:
                aggregated[label] = []
                order.append(label)
            aggregated[label].append(value)

    result = []
    for label in order[:6]:
        values = aggregated.get(label) or []
        if not values:
            continue
        result.append({
            'label': label,
            'value': int(round(sum(values) / len(values))),
        })

    return result

def _build_week_trend(today, duration_by_date):
    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        trend.append({
            'label': '今天' if offset == 0 else ('昨天' if offset == 1 else day.strftime('%m-%d')),
            'value': _round_hours(duration_by_date.get(day, 0)),
        })
    return trend

def _build_month_trend(today, duration_by_date):
    current_week_start = today - timedelta(days=today.weekday())
    weeks = []

    for offset in range(3, -1, -1):
        week_start = current_week_start - timedelta(days=offset * 7)
        week_end = week_start + timedelta(days=6)
        total_seconds = 0
        current_day = week_start
        while current_day <= week_end:
            total_seconds += duration_by_date.get(current_day, 0)
            current_day += timedelta(days=1)
        weeks.append({
            'label': f'第{4 - offset}周',
            'value': _round_hours(total_seconds),
        })

    return weeks

def _shift_month(year, month, delta):
    month_index = month - 1 + delta
    target_year = year + month_index // 12
    target_month = month_index % 12 + 1
    return target_year, target_month

def _build_year_trend(today, duration_by_date):
    trend = []

    for offset in range(5, -1, -1):
        year, month = _shift_month(today.year, today.month, -offset)
        total_seconds = 0
        for record_date, duration in duration_by_date.items():
            if record_date.year == year and record_date.month == month:
                total_seconds += duration
        trend.append({
            'label': f'{month}月',
            'value': _round_hours(total_seconds),
        })

    return trend

def _apply_demo_student_snapshot(student, analytics_payload):
    if not student or student.username != 'student':
        return analytics_payload

    payload = dict(analytics_payload)
    payload['overallProgress'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['overallProgress']
    payload['weeklyLearningTime'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['weeklyLearningTime']
    payload['previousWeekTime'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['previousWeekTime']
    payload['completedCourses'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['completedCourses']
    payload['inProgressCourses'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['inProgressCourses']
    payload['notStartedCourses'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['notStartedCourses']
    payload['trendData'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['trendData']
    payload['knowledgePoints'] = DEMO_STUDENT_ANALYTICS_SNAPSHOT['knowledgePoints']
    payload['knowledgePointsByCourse'] = {
        str(item.get('id') if isinstance(item, dict) else index): DEMO_STUDENT_ANALYTICS_SNAPSHOT['knowledgePoints']
        for index, item in enumerate(payload.get('courseDetails') or [], start=1)
    }

    demo_details = DEMO_STUDENT_ANALYTICS_SNAPSHOT['courseDetails']
    course_details = payload.get('courseDetails') or []
    if course_details:
        payload['courseDetails'] = [
            {
                **course_detail,
                'progress': demo_details[index % len(demo_details)]['progress'],
                'learningTime': demo_details[index % len(demo_details)]['learningTime'],
                'lastActivity': demo_details[index % len(demo_details)]['lastActivity'],
                'score': demo_details[index % len(demo_details)]['score'],
            }
            for index, course_detail in enumerate(course_details)
        ]
    else:
        payload['courseDetails'] = [
            {
                'id': index + 1,
                'name': f'演示课程 {index + 1}',
                'category': '演示数据',
                'progress': detail['progress'],
                'learningTime': detail['learningTime'],
                'lastActivity': detail['lastActivity'],
                'score': detail['score'],
            }
            for index, detail in enumerate(demo_details[:4])
        ]

    payload['knowledgePointsByCourse'] = {
        str(course_detail['id']): DEMO_STUDENT_ANALYTICS_SNAPSHOT['knowledgePoints']
        for course_detail in payload['courseDetails']
    }
    return payload

def _is_meaningful_student_analytics(analytics_payload):
    if not analytics_payload:
        return False
    if analytics_payload.get('overallProgress', 0) > 0:
        return True
    if analytics_payload.get('weeklyLearningTime', 0) > 0:
        return True
    if analytics_payload.get('previousWeekTime', 0) > 0:
        return True
    for course_detail in analytics_payload.get('courseDetails') or []:
        if (
            course_detail.get('progress', 0) > 0 or
            course_detail.get('learningTime', 0) > 0 or
            course_detail.get('score', 0) > 0
        ):
            return True
    return False

def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        normalized = str(item or '').strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result

def _build_student_ai_analysis(student, analytics_payload, course_id=None):
    timestamp = datetime.now().isoformat()

    if student and student.username == 'student':
        return {
            **DEMO_STUDENT_AI_ANALYSIS,
            'timestamp': timestamp,
        }

    if not _is_meaningful_student_analytics(analytics_payload):
        return {
            'strengths': [],
            'improvements': [],
            'suggestions': [],
            'timestamp': timestamp,
        }

    course_details = analytics_payload.get('courseDetails') or []
    knowledge_points_by_course = analytics_payload.get('knowledgePointsByCourse') or {}
    knowledge_points = analytics_payload.get('knowledgePoints') or []
    selected_course = None
    if course_id is not None:
        selected_course = next(
            (course_detail for course_detail in course_details if int(course_detail.get('id', 0)) == int(course_id)),
            None
        )

    relevant_courses = [selected_course] if selected_course else course_details
    relevant_courses = [course for course in relevant_courses if course]

    strengths = []
    improvements = []
    suggestions = []

    best_course = max(relevant_courses or course_details, key=lambda item: (
        item.get('progress', 0),
        item.get('score', 0),
        item.get('learningTime', 0),
    ), default=None)
    weakest_course = min(relevant_courses or course_details, key=lambda item: (
        item.get('progress', 0),
        item.get('learningTime', 0),
        item.get('score', 0),
    ), default=None)

    if best_course and best_course.get('progress', 0) >= 70:
        strengths.append(f"《{best_course['name']}》学习进展稳定，当前进度达到{best_course['progress']}%")
    if analytics_payload.get('overallProgress', 0) >= 60:
        strengths.append(f"整体学习进度达到{analytics_payload['overallProgress']}%，已形成较好的推进节奏")
    if analytics_payload.get('weeklyLearningTime', 0) >= 5:
        strengths.append(f"本周累计学习 {analytics_payload['weeklyLearningTime']} 小时，学习投入较为充足")
    if best_course and best_course.get('score', 0) >= 80:
        strengths.append(f"《{best_course['name']}》相关测验表现较好，平均成绩保持在 {best_course['score']} 分左右")

    weakest_knowledge_point = min(
        knowledge_points,
        key=lambda item: item.get('value', 0),
        default=None
    )
    strongest_knowledge_point = max(
        knowledge_points,
        key=lambda item: item.get('value', 0),
        default=None
    )

    if strongest_knowledge_point and strongest_knowledge_point.get('value', 0) >= 75:
        strengths.append(f"{strongest_knowledge_point['label']} 相关知识点掌握较好，当前掌握度为 {strongest_knowledge_point['value']}%")

    if analytics_payload.get('notStartedCourses', 0) > 0:
        improvements.append(f"仍有 {analytics_payload['notStartedCourses']} 门课程尚未开始，建议尽快建立学习起点")
    if weakest_course and weakest_course.get('progress', 0) < 50:
        improvements.append(f"《{weakest_course['name']}》当前进度仅 {weakest_course['progress']}%，需要优先补强")
    if analytics_payload.get('weeklyLearningTime', 0) < 2:
        improvements.append('本周有效学习时长偏少，建议增加固定学习时段')
    if weakest_knowledge_point and weakest_knowledge_point.get('value', 0) < 60:
        improvements.append(f"{weakest_knowledge_point['label']} 掌握度偏弱，建议集中复习相关内容")

    if weakest_knowledge_point:
        suggestions.append(f"优先复习 {weakest_knowledge_point['label']} 的核心概念，并结合课程材料完成针对性练习")
    if weakest_course:
        suggestions.append(f"先推进《{weakest_course['name']}》的近期学习任务，逐步把课程进度提升到 60% 以上")
    if analytics_payload.get('weeklyLearningTime', 0) < 5:
        suggestions.append('建议为本周剩余时间安排固定学习计划，避免学习节奏中断')
    if best_course:
        suggestions.append(f"延续《{best_course['name']}》中的学习方法，把高效做法复用到其它课程")

    if selected_course:
        course_points = knowledge_points_by_course.get(str(selected_course.get('id'))) or []
        low_course_point = min(course_points, key=lambda item: item.get('value', 0), default=None)
        high_course_point = max(course_points, key=lambda item: item.get('value', 0), default=None)
        if high_course_point and high_course_point.get('value', 0) >= 75:
            strengths.insert(0, f"《{selected_course['name']}》中的 {high_course_point['label']} 掌握较好")
        if low_course_point and low_course_point.get('value', 0) < 60:
            improvements.insert(0, f"《{selected_course['name']}》中的 {low_course_point['label']} 仍需重点提升")
            suggestions.insert(0, f"建议围绕《{selected_course['name']}》的 {low_course_point['label']} 制定专项复习计划")

    return {
        'strengths': _dedupe_keep_order(strengths)[:4],
        'improvements': _dedupe_keep_order(improvements)[:4],
        'suggestions': _dedupe_keep_order(suggestions)[:5],
        'timestamp': timestamp,
    }

def _build_student_analytics_payload(student):
    student_id = student.id
    learning_records = LearningRecord.query.filter_by(student_id=student_id).order_by(
        LearningRecord.timestamp.asc()
    ).all()

    course_map = {
        course.id: course
        for course in (student.courses_enrolled or [])
    }
    record_course_ids = sorted({
        int(record.course_id)
        for record in learning_records
        if record.course_id
    })
    if record_course_ids:
        for course in Course.query.filter(Course.id.in_(record_course_ids)).all():
            course_map[course.id] = course

    student_courses = list(course_map.values())
    course_ids = [course.id for course in student_courses]

    course_records = {}
    duration_by_date = {}
    for record in learning_records:
        course_records.setdefault(record.course_id, []).append(record)
        if record.timestamp:
            record_date = record.timestamp.date()
            duration_by_date[record_date] = duration_by_date.get(record_date, 0) + int(record.duration or 0)

    material_count_map = {}
    assessment_count_map = {}
    if course_ids:
        material_count_map = {
            int(course_id): int(total or 0)
            for course_id, total in db.session.query(
                Material.course_id,
                func.count(Material.id)
            ).filter(Material.course_id.in_(course_ids)).group_by(Material.course_id).all()
        }
        assessment_count_map = {
            int(course_id): int(total or 0)
            for course_id, total in db.session.query(
                Assessment.course_id,
                func.count(Assessment.id)
            ).filter(Assessment.course_id.in_(course_ids)).group_by(Assessment.course_id).all()
        }

    submissions = []
    if course_ids:
        submissions = db.session.query(AssessmentSubmission).join(
            Assessment, Assessment.id == AssessmentSubmission.assessment_id
        ).filter(
            AssessmentSubmission.student_id == student_id,
            Assessment.course_id.in_(course_ids)
        ).all()

    submission_stats = {}
    for submission in submissions:
        course_id = getattr(submission.assessment, 'course_id', None)
        if not course_id:
            continue
        stat = submission_stats.setdefault(course_id, {'count': 0, 'scores': []})
        stat['count'] += 1
        if submission.score is not None:
            stat['scores'].append(float(submission.score))

    completed_courses = 0
    in_progress_courses = 0
    not_started_courses = 0
    course_progress = {}
    course_details = []
    knowledge_points_by_course = {}

    for course in student_courses:
        records = course_records.get(course.id, [])
        submission_stat = submission_stats.get(course.id, {'count': 0, 'scores': []})
        viewed_materials = {
            material_key
            for material_key in (
                _build_material_view_key(record)
                for record in records
                if record.activity_type == 'view_material'
            )
            if material_key
        }
        materials_count = max(1, material_count_map.get(course.id, 0))
        material_ratio = min(1.0, len(viewed_materials) / materials_count) if materials_count else 0
        assessments_count = assessment_count_map.get(course.id, 0)
        submission_ratio = min(1.0, submission_stat['count'] / max(1, assessments_count)) if assessments_count else 0
        active_records_count = len([
            record for record in records
            if record.activity_type not in ('enrolled', 'unenrolled')
        ])
        has_any_activity = bool(active_records_count or submission_stat['count'])

        progress = int(round(material_ratio * 70 + submission_ratio * 30))
        if has_any_activity and progress == 0:
            progress = min(20, 5 * max(1, active_records_count or submission_stat['count']))
        if assessments_count > 0 and submission_stat['count'] >= assessments_count and material_ratio >= 1:
            progress = 100
        progress = max(0, min(100, progress))
        course_progress[course.id] = progress

        if progress >= 100:
            completed_courses += 1
        elif progress > 0:
            in_progress_courses += 1
        else:
            not_started_courses += 1

        total_course_seconds = sum(int(record.duration or 0) for record in records)
        learning_time_hours = _round_hours(total_course_seconds)
        meaningful_records = [
            record for record in records
            if record.activity_type not in ('enrolled', 'unenrolled')
        ]
        last_activity = meaningful_records[-1].timestamp if meaningful_records else None
        score_values = submission_stat['scores']
        score = int(round(sum(score_values) / len(score_values))) if score_values else 0

        course_details.append({
            'id': course.id,
            'name': course.name,
            'category': course.category or '未分类',
            'progress': progress,
            'learningTime': learning_time_hours,
            'lastActivity': _safe_date_label(last_activity),
            'score': score,
        })

        knowledge_points_by_course[str(course.id)] = _build_course_knowledge_points(
            course,
            progress,
            learning_time_hours,
            score,
        )

    course_details.sort(key=lambda item: (
        item['lastActivity'] == '未学习',
        item['lastActivity'],
        item['name'],
    ))

    overall_progress = int(round(
        sum(course_progress.values()) / len(course_progress)
    )) if course_progress else 0

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)

    weekly_seconds = sum(
        duration for date_value, duration in duration_by_date.items()
        if week_start <= date_value <= today
    )
    previous_week_seconds = sum(
        duration for date_value, duration in duration_by_date.items()
        if last_week_start <= date_value < week_start
    )

    return {
        'overallProgress': overall_progress,
        'weeklyLearningTime': _round_hours(weekly_seconds),
        'previousWeekTime': _round_hours(previous_week_seconds),
        'completedCourses': completed_courses,
        'inProgressCourses': in_progress_courses,
        'notStartedCourses': not_started_courses,
        'trendData': {
            'week': _build_week_trend(today, duration_by_date),
            'month': _build_month_trend(today, duration_by_date),
            'year': _build_year_trend(today, duration_by_date),
        },
        'courseDetails': course_details,
        'knowledgePoints': _aggregate_knowledge_points(knowledge_points_by_course),
        'knowledgePointsByCourse': knowledge_points_by_course,
    }

def get_absolute_material_path(relative_path):
    if not relative_path:
        return None
    return os.path.join(current_app.root_path, relative_path.lstrip('/'))

def calculate_file_hash(file_path):
    """计算文件的SHA256哈希值"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_material_extension(material):
    candidate = material.file_path or material.title or ''
    return os.path.splitext(candidate)[1].lower()

def supports_generated_preview_by_extension(file_extension):
    return file_extension.lower() in OFFICE_PREVIEW_EXTENSIONS

def material_supports_generated_preview(material):
    return supports_generated_preview_by_extension(get_material_extension(material))

def resolve_windows_shortcut_path(candidate_path):
    normalized = str(candidate_path or '').strip().strip('"')
    if os.name != 'nt' or not normalized.lower().endswith('.lnk') or not os.path.exists(normalized):
        return normalized

    try:
        result = subprocess.run(
            [
                'powershell',
                '-NoProfile',
                '-Command',
                '$shell = New-Object -ComObject WScript.Shell; '
                '$shortcut = $shell.CreateShortcut($args[0]); '
                '[Console]::Out.Write($shortcut.TargetPath)',
                normalized,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        resolved = (result.stdout or '').strip().strip('"')
        if resolved:
            return resolved
    except Exception:
        current_app.logger.exception('解析 LibreOffice 快捷方式失败: %s', normalized)

    return normalized

def get_preview_converter_command():
    configured_path = (os.getenv('SOFFICE_PATH') or current_app.config.get('SOFFICE_PATH') or '').strip()
    candidates = [configured_path] if configured_path else []

    for command_name in ('soffice', 'libreoffice'):
        resolved = shutil.which(command_name)
        if resolved:
            candidates.append(resolved)

    for env_name in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        root = os.environ.get(env_name)
        if not root:
            continue
        candidates.append(os.path.join(root, 'LibreOffice', 'program', 'soffice.exe'))

    for candidate in candidates:
        if not candidate:
            continue
        candidate = resolve_windows_shortcut_path(candidate)
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None

def generate_office_preview(source_file_path, course_id, file_hash):
    converter_command = get_preview_converter_command()
    if not converter_command:
        raise RuntimeError('未找到 LibreOffice/soffice，请安装 LibreOffice 或配置 SOFFICE_PATH')

    preview_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'materials', str(course_id), 'previews')
    os.makedirs(preview_folder, exist_ok=True)

    preview_filename = f'{file_hash}.pdf' if file_hash else f'{uuid.uuid4().hex}.pdf'
    preview_relative_path = f'/uploads/materials/{course_id}/previews/{preview_filename}'
    preview_output_path = os.path.join(preview_folder, preview_filename)

    if os.path.exists(preview_output_path):
        return preview_relative_path

    command = [
        converter_command,
        '--headless',
        '--convert-to',
        'pdf',
        '--outdir',
        preview_folder,
        source_file_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        stdout = (result.stdout or '').strip()
        raise RuntimeError(stderr or stdout or 'Office 文件转换失败')

    generated_preview_path = os.path.join(
        preview_folder,
        f"{os.path.splitext(os.path.basename(source_file_path))[0]}.pdf"
    )

    if os.path.exists(generated_preview_path) and os.path.abspath(generated_preview_path) != os.path.abspath(preview_output_path):
        if os.path.exists(preview_output_path):
            os.remove(preview_output_path)
        os.replace(generated_preview_path, preview_output_path)

    if not os.path.exists(preview_output_path):
        raise RuntimeError('Office 文件转换完成，但未生成 PDF 预览文件')

    return preview_relative_path

def ensure_material_preview(material, allow_retry=False):
    changed = False

    if not material_supports_generated_preview(material):
        if material.preview_status != 'not_applicable':
            material.preview_status = 'not_applicable'
            changed = True
        if material.preview_error:
            material.preview_error = None
            changed = True
        return changed

    source_file_path = get_absolute_material_path(material.file_path)
    if not source_file_path or not os.path.exists(source_file_path):
        if material.preview_status != 'failed' or material.preview_error != '源文件不存在':
            material.preview_status = 'failed'
            material.preview_error = '源文件不存在'
            changed = True
        return changed

    preview_file_path = get_absolute_material_path(material.preview_file_path)
    if material.preview_file_path and preview_file_path and os.path.exists(preview_file_path):
        if material.preview_status != 'ready':
            material.preview_status = 'ready'
            changed = True
        if material.preview_error:
            material.preview_error = None
            changed = True
        return changed

    if material.preview_status == 'failed' and material.preview_error and not allow_retry:
        preview_error = str(material.preview_error or '').strip()
        missing_soffice = 'LibreOffice/soffice' in preview_error
        if not missing_soffice or not get_preview_converter_command():
            return changed

    try:
        preview_relative_path = generate_office_preview(source_file_path, material.course_id, material.file_hash)
        if material.preview_file_path != preview_relative_path:
            material.preview_file_path = preview_relative_path
            changed = True
        if material.preview_status != 'ready':
            material.preview_status = 'ready'
            changed = True
        if material.preview_error:
            material.preview_error = None
            changed = True
    except Exception as exc:
        error_message = str(exc)
        current_app.logger.exception('生成课件预览失败: %s', source_file_path)
        if material.preview_status != 'failed':
            material.preview_status = 'failed'
            changed = True
        if material.preview_error != error_message:
            material.preview_error = error_message
            changed = True

    return changed

def build_material_dict(material):
    material_dict = material.to_dict()

    if material.file_path:
        file_path = get_absolute_material_path(material.file_path)
        if file_path and os.path.exists(file_path):
            material_dict['size'] = format_file_size(os.path.getsize(file_path))
        else:
            material_dict['size'] = '文件不存在'
    else:
        material_dict['size'] = '未知'

    return material_dict

def validate_material_chapter_source(course_id, material_id, source_type):
    course = Course.query.get(course_id)
    if not course:
        return None, None, (jsonify({'status': 'error', 'message': '课程不存在'}), 404)

    material = Material.query.get(material_id)
    if not material:
        return course, None, (jsonify({'status': 'error', 'message': '课件资源不存在'}), 404)

    if int(material.course_id) != int(course_id):
        return course, material, (jsonify({'status': 'error', 'message': '课件资源不属于当前课程'}), 403)

    if source_type not in {'pdf', 'ppt'}:
        return course, material, (jsonify({'status': 'error', 'message': 'source_type 仅支持 pdf 或 ppt'}), 400)

    extension = get_material_extension(material)
    if source_type == 'pdf' and extension != '.pdf':
        return course, material, (jsonify({'status': 'error', 'message': 'PDF 模式仅支持 .pdf 文件'}), 400)
    if source_type == 'ppt' and extension not in {'.ppt', '.pptx'}:
        return course, material, (jsonify({'status': 'error', 'message': 'PPT 模式仅支持 .ppt 或 .pptx 文件'}), 400)

    absolute_path = get_absolute_material_path(material.file_path)
    if not absolute_path or not os.path.exists(absolute_path):
        return course, material, (jsonify({'status': 'error', 'message': '课件源文件不存在'}), 400)

    return course, material, None

# 检查是否为教师或管理员的辅助函数
def teacher_or_admin_required():
    claims = get_jwt()
    role = claims.get('role')
    if role not in ['teacher', 'admin']:
        return jsonify({"error": "需要教师或管理员权限"}), 403
    return None

# 通用错误处理装饰器
def api_error_handler(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"API异常: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            
            # 创建错误响应
            response = jsonify({
                'status': 'error',
                'message': f'服务器处理请求时出错: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            })
            
            # 添加CORS头
            origin = request.headers.get('Origin', '')
            allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
            
            if origin in allowed_origins:
                response.headers.add('Access-Control-Allow-Origin', origin)
            else:
                response.headers.add('Access-Control-Allow-Origin', '*')
                
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'POST,GET,PUT,DELETE,OPTIONS')
            response.headers.add('Content-Type', 'application/json')
            
            return response, 500
    return decorated_function


def get_current_user_from_request():
    cached_user = getattr(request, '_cached_current_user', None)
    if cached_user is not None:
        return cached_user

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        request._cached_current_user = None
        return None

    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        request._cached_current_user = None
        return None

    try:
        decoded_token = decode_token(token)
        user_id = decoded_token.get('sub')
        user = User.query.get(int(user_id)) if user_id is not None else None
    except Exception as exc:
        current_app.logger.warning(f'解析当前用户失败: {exc}')
        user = None

    request._cached_current_user = user
    return user


def is_teacher_or_admin(user):
    return bool(user and user.role in ['teacher', 'admin'])


def ensure_course_read_access(course, current_user):
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if current_user:
        if current_user.role == 'admin':
            return None
        if current_user.role == 'teacher':
            if course.teacher_id != current_user.id:
                return jsonify({'error': '无权访问该课程'}), 403
            return None
        if current_user.role == 'student':
            if course.is_public or current_user in (course.students or []):
                return None
            return jsonify({'error': 'Course not found'}), 404

    if course.is_public:
        return None

    return jsonify({'error': '未登录，无法访问该课程'}), 401


def ensure_course_manage_access(course, current_user):
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    if not current_user:
        return jsonify({'error': '未登录，无法操作该课程'}), 401
    if current_user.role == 'admin':
        return None
    if current_user.role != 'teacher' or course.teacher_id != current_user.id:
        return jsonify({'error': '无权操作该课程'}), 403
    return None


def ensure_course_upload_access(course, current_user):
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    if not current_user:
        return jsonify({'error': '未登录，无法上传课程资料'}), 401
    if current_user.role == 'admin':
        return None
    if current_user.role == 'teacher':
        if course.teacher_id != current_user.id:
            return jsonify({'error': '无权上传该课程资料'}), 403
        return None
    if current_user.role == 'student':
        if any(student.id == current_user.id for student in (course.students or [])):
            return None
        return jsonify({'error': '仅已加入该课程的学生可上传资料'}), 403
    return jsonify({'error': '无权上传该课程资料'}), 403


def ensure_material_read_access(material, current_user):
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    return ensure_course_read_access(material.course, current_user)


def ensure_material_manage_access(material, current_user):
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    return ensure_course_manage_access(material.course, current_user)


def ensure_assessment_manage_access(assessment, current_user):
    if not assessment:
        return jsonify({'error': 'Assessment not found'}), 404
    return ensure_course_manage_access(assessment.course, current_user)


def is_recently_created(created_at, updated_at, threshold_seconds=5):
    if not created_at or not updated_at:
        return False
    return abs((updated_at - created_at).total_seconds()) <= threshold_seconds


def build_dashboard_activity(timestamp, title, description, activity_type):
    if not timestamp:
        return None

    return {
        'title': title,
        'description': description,
        'type': activity_type,
        'timestamp': timestamp.isoformat(),
        '_sort_at': timestamp,
    }


def assessment_visible_to_student(assessment_id, student_id):
    return db.session.query(TeacherClass.id).join(
        assessment_publish_classes,
        TeacherClass.id == assessment_publish_classes.c.class_id,
    ).join(
        teacher_class_students,
        TeacherClass.id == teacher_class_students.c.class_id,
    ).filter(
        assessment_publish_classes.c.assessment_id == assessment_id,
        teacher_class_students.c.student_id == student_id,
    ).first() is not None


@learning_bp.route('/teacher-dashboard/summary', methods=['GET'])
@api_error_handler
def get_teacher_dashboard_summary():
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '需要教师或管理员权限'}), 403

    is_admin = current_user.role == 'admin'
    activities = []

    course_query = Course.query
    if not is_admin:
        course_query = course_query.filter(Course.teacher_id == current_user.id)

    recent_courses = course_query.order_by(Course.updated_at.desc(), Course.created_at.desc()).limit(5).all()
    for course in recent_courses:
        created = is_recently_created(course.created_at, course.updated_at)
        activities.append(build_dashboard_activity(
            course.updated_at or course.created_at,
            '课程创建' if created else '课程更新',
            f'课程《{course.name}》已创建' if created else f'课程《{course.name}》内容已更新',
            'course',
        ))

    material_query = Material.query.join(Course, Material.course_id == Course.id)
    if not is_admin:
        material_query = material_query.filter(Course.teacher_id == current_user.id)

    recent_materials = material_query.order_by(Material.updated_at.desc(), Material.created_at.desc()).limit(5).all()
    for material in recent_materials:
        created = is_recently_created(material.created_at, material.updated_at)
        course_name = material.course.name if material.course else '课程'
        activities.append(build_dashboard_activity(
            material.updated_at or material.created_at,
            '课件上传' if created else '课件更新',
            f'《{course_name}》的课件《{material.title}》已上传' if created else f'《{course_name}》的课件《{material.title}》已更新',
            'material',
        ))

    assessment_query = Assessment.query.join(Course, Assessment.course_id == Course.id)
    if not is_admin:
        assessment_query = assessment_query.filter(Course.teacher_id == current_user.id)

    recent_assessments = assessment_query.order_by(Assessment.updated_at.desc(), Assessment.created_at.desc()).limit(5).all()
    for assessment in recent_assessments:
        created = is_recently_created(assessment.created_at, assessment.updated_at)
        course_name = assessment.course.name if assessment.course else '课程'
        activities.append(build_dashboard_activity(
            assessment.updated_at or assessment.created_at,
            '评估创建' if created else '评估更新',
            f'《{course_name}》新增评估《{assessment.title}》' if created else f'评估《{assessment.title}》已更新',
            'assessment',
        ))

    teacher_class_query = TeacherClass.query
    if not is_admin:
        teacher_class_query = teacher_class_query.filter(TeacherClass.teacher_id == current_user.id)

    recent_classes = teacher_class_query.order_by(TeacherClass.updated_at.desc(), TeacherClass.created_at.desc()).limit(5).all()
    for teacher_class in recent_classes:
        created = is_recently_created(teacher_class.created_at, teacher_class.updated_at)
        activities.append(build_dashboard_activity(
            teacher_class.updated_at or teacher_class.created_at,
            '班级创建' if created else '班级更新',
            f'班级《{teacher_class.name}》已创建' if created else f'班级《{teacher_class.name}》成员信息已更新',
            'class',
        ))

    submission_query = StudentAnswer.query.join(
        Assessment, StudentAnswer.assessment_id == Assessment.id
    ).join(
        Course, Assessment.course_id == Course.id
    )
    if not is_admin:
        submission_query = submission_query.filter(Course.teacher_id == current_user.id)

    recent_submissions = submission_query.order_by(StudentAnswer.submitted_at.desc()).limit(5).all()
    for submission in recent_submissions:
        student_name = None
        if submission.student:
            student_name = submission.student.full_name or submission.student.username
        student_name = student_name or f'学生{submission.student_id}'
        assessment_title = submission.assessment.title if submission.assessment else '评估'
        activities.append(build_dashboard_activity(
            submission.submitted_at,
            '学生提交',
            f'{student_name} 提交了《{assessment_title}》',
            'submission',
        ))

    queue_query = KnowledgeBaseQueue.query.join(Course, KnowledgeBaseQueue.course_id == Course.id)
    if not is_admin:
        queue_query = queue_query.filter(Course.teacher_id == current_user.id)

    notification_count = queue_query.filter(
        KnowledgeBaseQueue.status.in_(['pending', 'processing', 'failed'])
    ).count()

    recent_activities = [item for item in activities if item]
    recent_activities.sort(key=lambda item: item['_sort_at'], reverse=True)
    recent_activities = recent_activities[:5]

    for item in recent_activities:
        item.pop('_sort_at', None)

    return jsonify({
        'overview': {
            'last_login_at': current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            'notification_count': notification_count,
        },
        'recent_activities': recent_activities,
    })


def apply_assessment_visibility_filter(query, current_user):
    if not current_user:
        return query.filter(Assessment.id == -1)

    if current_user.role == 'teacher':
        return query.join(Course, Assessment.course_id == Course.id).filter(Course.teacher_id == current_user.id)

    if current_user.role == 'student':
        query = query.join(
            assessment_publish_classes,
            Assessment.id == assessment_publish_classes.c.assessment_id,
        ).join(
            TeacherClass,
            TeacherClass.id == assessment_publish_classes.c.class_id,
        ).join(
            teacher_class_students,
            TeacherClass.id == teacher_class_students.c.class_id,
        ).filter(
            teacher_class_students.c.student_id == current_user.id,
            Assessment.is_published.is_(True),
        ).distinct()

    return query


def ensure_teacher_class_access(teacher_class, current_user):
    if not current_user:
        return jsonify({'error': '未登录，无法访问班级数据'}), 401

    if current_user.role == 'admin':
        return None

    if teacher_class.teacher_id != current_user.id:
        return jsonify({'error': '无权操作该班级'}), 403

    return None


def ensure_assessment_publish_access(assessment, current_user):
    if not current_user:
        return jsonify({'error': '未登录，无法管理发布范围'}), 401

    if current_user.role == 'admin':
        return None

    course_teacher_id = assessment.course.teacher_id if assessment.course else None
    if current_user.role != 'teacher' or course_teacher_id != current_user.id:
        return jsonify({'error': '无权管理该评估的发布范围'}), 403

    return None


def extract_text_from_docx(file_storage):
    parse_result = _parse_uploaded_docx(file_storage)
    return str(parse_result.get('raw_text') or '').strip() if parse_result else ''


def normalize_import_text(text):
    return re.sub(r'\s+', ' ', (text or '').replace('\xa0', ' ')).strip()


def iter_docx_blocks(document):
    for child in document.element.body.iterchildren():
        if child.tag.endswith('}p'):
            paragraph = Paragraph(child, document)
            paragraph_text = '\n'.join(
                normalize_import_text(run_line)
                for run_line in paragraph.text.splitlines()
                if normalize_import_text(run_line)
            ).strip()
            if paragraph_text:
                yield paragraph_text
        elif child.tag.endswith('}tbl'):
            table = Table(child, document)
            for row in table.rows:
                row_parts = []
                for cell in row.cells:
                    cell_text = '\n'.join(
                        normalize_import_text(paragraph.text)
                        for paragraph in cell.paragraphs
                        if normalize_import_text(paragraph.text)
                    ).strip()
                    if cell_text:
                        row_parts.append(cell_text)
                if row_parts:
                    yield ' '.join(row_parts)


def extract_docx_lines(file_storage):
    parse_result = _parse_uploaded_docx(file_storage)
    if not parse_result:
        return []
    return extract_lines_from_parse_result(parse_result)


def _parse_uploaded_docx(file_storage):
    file_bytes = file_storage.read()
    if not file_bytes:
        return None

    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    api_key, api_base, _ = get_api_config()
    temp_path = ''
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        parse_result = parse_docx(
            temp_path,
            upload_root=current_app.config.get('UPLOAD_FOLDER'),
            owner_id='docx_import',
            api_key=api_key,
            api_base=api_base,
            parse_mode='docx_import',
        )
        return parse_result
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def detect_question_section_type(text):
    normalized_text = normalize_import_text(text)
    if not normalized_text:
        return None

    if re.fullmatch(r'(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?(单项选择题|单选题)', normalized_text):
        return 'multiple_choice'
    if re.fullmatch(r'(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?(多项选择题|多选题)', normalized_text):
        return 'multiple_answer'
    if re.fullmatch(r'(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?(选择题)', normalized_text):
        return 'multiple_choice'
    if re.fullmatch(r'(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?(填空题)', normalized_text):
        return 'fill_blank'
    if re.fullmatch(r'(?:[一二三四五六七八九十0-9]+[、.．]?\s*)?(简答题|解答题|问答题|论述题|主观题)', normalized_text):
        return 'short_answer'
    return None


def is_question_instruction_line(text):
    normalized_text = normalize_import_text(text)
    if not normalized_text:
        return False

    instruction_patterns = [
        r'^每小题.*分',
        r'^本题.*分',
        r'^共.*分$',
        r'^请将答案',
        r'^请在.*作答',
        r'^说明[:：]?',
        r'^要求[:：]?',
    ]
    return any(re.match(pattern, normalized_text) for pattern in instruction_patterns)


def extract_option_segments(text):
    option_pattern = re.compile(r'(?<![A-Za-z0-9])([A-H])[\.．、\)）:：]\s*')
    matches = list(option_pattern.finditer(text))
    if not matches:
        return None, []

    stem = normalize_import_text(text[:matches[0].start()])
    options = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        option_text = normalize_import_text(text[start:end].strip(' ;；'))
        if option_text:
            options.append(option_text)

    return stem, options


def count_fill_blank_placeholders(text):
    if not text:
        return 1

    patterns = [
        r'_{2,}',
        r'（\s*）',
        r'\(\s*\)',
        r'【\s*】',
        r'\[\s*\]',
    ]
    placeholder_count = sum(len(re.findall(pattern, text)) for pattern in patterns)
    return max(placeholder_count, 1)


def infer_question_type(text, section_type=None):
    if section_type in {'multiple_choice', 'multiple_answer', 'fill_blank', 'short_answer'}:
        return section_type

    _, options = extract_option_segments(text)
    if len(options) >= 2:
        return 'multiple_choice'

    if count_fill_blank_placeholders(text) > 1 or re.search(r'_{2,}|（\s*）|\(\s*\)|【\s*】|\[\s*\]', text or ''):
        return 'fill_blank'

    return 'short_answer'


def build_import_question(question_type, content):
    question = {
        'type': question_type,
        'content': normalize_import_text(content),
        'score': 10,
        'reference_answer': '',
        'explanation': '',
    }

    if question_type in {'multiple_choice', 'multiple_answer'}:
        question['options'] = []
    elif question_type == 'fill_blank':
        blank_count = count_fill_blank_placeholders(content)
        question['blank_count'] = blank_count

    return question


def finalize_import_question(question):
    if not question:
        return None

    question['content'] = normalize_import_text(question.get('content', ''))
    question['explanation'] = normalize_import_text(question.get('explanation', ''))
    if not question['content'] and not question.get('options'):
        return None

    question_type = question.get('type') or infer_question_type(question.get('content', ''))
    question['type'] = question_type

    if question_type in {'multiple_choice', 'multiple_answer'}:
        options = [
            normalize_import_text(option)
            for option in (question.get('options') or [])
            if normalize_import_text(option)
        ]
        if len(options) < 2:
            question.pop('options', None)
            question['type'] = 'short_answer'
            question['reference_answer'] = ''
        else:
            question['options'] = options
            if question['type'] == 'multiple_answer':
                question['answers'] = [False] * len(options)
            else:
                question['answer'] = None
            question['reference_answer'] = ''
    elif question_type == 'fill_blank':
        question['blank_count'] = count_fill_blank_placeholders(question['content'])
        question['reference_answer'] = ''
    else:
        question.pop('options', None)
        question['reference_answer'] = ''

    return question


def parse_questions_from_docx_lines(lines):
    questions = []
    current_section_type = None
    current_question = None
    question_start_pattern = re.compile(r'^\s*(?:第\s*)?(\d+)\s*[、.．]\s*(.+)$|^\s*[（(](\d+)[)）]\s*(.+)$')

    def commit_question():
        nonlocal current_question
        finalized = finalize_import_question(current_question)
        if finalized:
            questions.append(finalized)
        current_question = None

    for raw_line in lines:
        line = normalize_import_text(raw_line)
        if not line:
            continue

        section_type = detect_question_section_type(line)
        if section_type:
            commit_question()
            current_section_type = section_type
            continue

        if current_question is None and is_question_instruction_line(line):
            continue

        question_match = question_start_pattern.match(line)
        if question_match:
            commit_question()
            content = question_match.group(2) or question_match.group(4) or ''
            question_type = infer_question_type(content, current_section_type)
            current_question = build_import_question(question_type, content)

            stem, options = extract_option_segments(content)
            if question_type in {'multiple_choice', 'multiple_answer'} and options:
                current_question['content'] = stem or current_question['content']
                current_question['options'].extend(options)
            continue

        if current_question is None:
            current_question = build_import_question(infer_question_type(line, current_section_type), line)
            stem, options = extract_option_segments(line)
            if current_question['type'] in {'multiple_choice', 'multiple_answer'} and options:
                current_question['content'] = stem or current_question['content']
                current_question['options'].extend(options)
            continue

        if current_question['type'] in {'multiple_choice', 'multiple_answer'}:
            stem, options = extract_option_segments(line)
            if options:
                if stem and not current_question.get('content'):
                    current_question['content'] = stem
                elif stem:
                    current_question['content'] = normalize_import_text(f"{current_question['content']} {stem}")
                current_question['options'].extend(options)
            elif re.match(r'^[A-H][\.．、\)）:：]\s*', line):
                option_text = normalize_import_text(re.sub(r'^[A-H][\.．、\)）:：]\s*', '', line))
                if option_text:
                    current_question['options'].append(option_text)
            elif current_question.get('options'):
                current_question['options'][-1] = normalize_import_text(f"{current_question['options'][-1]} {line}")
            else:
                current_question['content'] = normalize_import_text(f"{current_question['content']} {line}")
        else:
            current_question['content'] = normalize_import_text(f"{current_question['content']} {line}")

    commit_question()

    if questions:
        return questions

    full_text = '\n'.join(lines).strip()
    if not full_text:
        return []

    return [finalize_import_question(build_import_question('short_answer', full_text))]


def extract_json_object_from_text(text):
    if not text:
        return None

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', stripped)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def extract_json_array_from_text(text):
    if not text:
        return None

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r'\[[\s\S]*\]', stripped)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _normalize_course_keyword(value):
    text = normalize_import_text(str(value or ''))
    text = re.sub(r'[，。；：、“”"\'（）()【】\[\]{}<>《》]', '', text)
    text = re.sub(r'\s+', '', text)
    return text[:10]


def build_course_keyword_fallback(course_name, course_description=''):
    normalized_name = normalize_import_text(course_name)
    normalized_desc = normalize_import_text(course_description)
    combined = f'{normalized_name} {normalized_desc}'.lower()

    subject_mapping = [
        (('化学',), ['物质结构', '化学键', '分子性质', '反应规律', '实验分析', '综合应用']),
        (('数学',), ['基础概念', '公式运用', '推理论证', '解题方法', '运算能力', '综合提升']),
        (('物理',), ['核心概念', '运动规律', '受力分析', '公式建模', '实验探究', '综合应用']),
        (('生物',), ['基础概念', '结构功能', '生命过程', '实验探究', '图表分析', '综合应用']),
        (('语文',), ['字词积累', '文本理解', '写作表达', '文学鉴赏', '思辨能力', '综合素养']),
        (('英语',), ['词汇语法', '阅读理解', '听说表达', '写作能力', '语篇分析', '综合运用']),
        (('历史',), ['时序理解', '史实掌握', '因果分析', '材料解读', '比较归纳', '综合论述']),
        (('地理',), ['区域认知', '空间分析', '图表判读', '人地关系', '综合思维', '实践应用']),
        (('政治', '思想政治', '道德与法治'), ['概念理解', '观点辨析', '时政联系', '材料分析', '规范表达', '综合应用']),
        (('计算机', '编程', '软件', '算法', '人工智能'), ['基础语法', '数据结构', '算法思维', '程序设计', '调试实践', '综合应用']),
    ]

    for keywords, fallback in subject_mapping:
        if any(keyword in combined for keyword in keywords):
            return fallback

    generic = ['课程基础', '核心概念', '重点原理', '方法应用', '实践能力', '综合提升']
    course_tokens = []
    for part in re.split(r'[\s/、,，\-]+', normalized_name):
        token = _normalize_course_keyword(part)
        if token and token not in course_tokens and len(token) >= 2:
            course_tokens.append(token)

    merged = course_tokens + generic
    deduped = []
    for item in merged:
        normalized = _normalize_course_keyword(item)
        if normalized and normalized not in deduped:
            deduped.append(normalized)
        if len(deduped) >= 6:
            break

    while len(deduped) < 6:
        deduped.append(generic[len(deduped)])

    return deduped[:6]


def generate_course_radar_keywords(course_name, course_description=''):
    normalized_name = normalize_import_text(course_name)
    normalized_desc = normalize_import_text(course_description)
    cache_key = f'{normalized_name}||{normalized_desc}'
    cached_keywords = COURSE_ANALYTICS_KEYWORD_CACHE.get(cache_key)
    if cached_keywords:
        return list(cached_keywords)

    fallback_keywords = build_course_keyword_fallback(normalized_name, normalized_desc)

    try:
        api_key, api_base, preferred_model = get_api_config()
        if not api_key:
            return fallback_keywords

        model_candidates = get_model_candidates('text', preferred=preferred_model)
        prompt = f"""
你是一名教学分析助手。请根据课程名称提取最适合用于“学情分析雷达图”的 6 个知识维度关键词。

课程名称：{normalized_name}
课程描述：{normalized_desc or '无'}

要求：
1. 必须输出 6 个中文关键词。
2. 每个关键词 2 到 8 个字，避免“知识点一”“内容二”这类空泛表达。
3. 关键词要贴合课程主题，适合作为学生掌握情况维度。
4. 六个词尽量覆盖基础、核心概念、方法、应用等不同层面。
5. 不要重复，不要带序号，不要解释。
6. 只返回 JSON，对象格式如下：
{{"keywords":["词1","词2","词3","词4","词5","词6"]}}
""".strip()

        payload = {
            'messages': [
                {'role': 'system', 'content': '你擅长提炼课程知识维度，输出必须严格为 JSON。'},
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.2,
            'max_tokens': 300,
            'stream': False,
        }

        response_json, used_model = post_chat_completion_with_model_fallback(
            api_key=api_key,
            api_base=api_base,
            payload=payload,
            model_candidates=model_candidates,
            timeout=60,
        )
        content = extract_message_content(response_json)
        parsed = extract_json_object_from_text(content) or {}
        keywords = parsed.get('keywords')
        if not isinstance(keywords, list):
            keywords = extract_json_array_from_text(content)

        normalized_keywords = []
        for item in keywords or []:
            normalized = _normalize_course_keyword(item)
            if normalized and normalized not in normalized_keywords:
                normalized_keywords.append(normalized)
            if len(normalized_keywords) >= 6:
                break

        if len(normalized_keywords) < 6:
            for item in fallback_keywords:
                normalized = _normalize_course_keyword(item)
                if normalized and normalized not in normalized_keywords:
                    normalized_keywords.append(normalized)
                if len(normalized_keywords) >= 6:
                    break

        final_keywords = normalized_keywords[:6]
        COURSE_ANALYTICS_KEYWORD_CACHE[cache_key] = final_keywords
        current_app.logger.info('课程学情分析关键词生成成功: course=%s model=%s keywords=%s', normalized_name, used_model, final_keywords)
        return final_keywords
    except Exception as exc:
        current_app.logger.warning('课程学情分析关键词生成失败，使用兜底词: course=%s error=%s', normalized_name, exc)
        COURSE_ANALYTICS_KEYWORD_CACHE[cache_key] = fallback_keywords
        return fallback_keywords


def normalize_ai_question_type(value):
    normalized_value = normalize_import_text(str(value or '')).lower()
    type_mapping = {
        'multiple_choice': 'multiple_choice',
        'single_choice': 'multiple_choice',
        'choice': 'multiple_choice',
        '单选': 'multiple_choice',
        '单选题': 'multiple_choice',
        '选择题': 'multiple_choice',
        'multiple_answer': 'multiple_answer',
        'multiple_answers': 'multiple_answer',
        'multiple_select': 'multiple_answer',
        '多选': 'multiple_answer',
        '多选题': 'multiple_answer',
        'fill_blank': 'fill_blank',
        'fill_in_blank': 'fill_blank',
        'blank': 'fill_blank',
        '填空': 'fill_blank',
        '填空题': 'fill_blank',
        'short_answer': 'short_answer',
        'essay': 'short_answer',
        'subjective': 'short_answer',
        'qa': 'short_answer',
        '简答': 'short_answer',
        '简答题': 'short_answer',
        '解答': 'short_answer',
        '解答题': 'short_answer',
        '问答题': 'short_answer',
        '论述题': 'short_answer',
    }
    return type_mapping.get(normalized_value, '')


def sanitize_ai_import_questions(raw_questions):
    if not isinstance(raw_questions, list):
        return []

    normalized_questions = []
    for raw_question in raw_questions:
        if not isinstance(raw_question, dict):
            continue

        question_type = normalize_ai_question_type(raw_question.get('type'))
        content = normalize_import_text(raw_question.get('content') or raw_question.get('stem') or '')
        if not content:
            continue

        if not question_type:
            question_type = infer_question_type(content)

        question = build_import_question(question_type, content)
        question['explanation'] = normalize_import_text(
            raw_question.get('explanation') or
            raw_question.get('analysis') or
            raw_question.get('solution') or
            ''
        )

        if question_type in {'multiple_choice', 'multiple_answer'}:
            options = raw_question.get('options')
            if isinstance(options, list):
                question['options'] = [
                    normalize_import_text(option)
                    for option in options
                    if normalize_import_text(option)
                ]

        finalized = finalize_import_question(question)
        if finalized:
            normalized_questions.append(finalized)

    return normalized_questions


def sanitize_ignored_texts(raw_items):
    if not isinstance(raw_items, list):
        return []

    normalized_items = []
    seen_items = set()
    for item in raw_items:
        text = normalize_import_text(item)
        if not text or text in seen_items:
            continue
        seen_items.add(text)
        normalized_items.append(text)
    return normalized_items


def build_image_data_url(file_bytes, mime_type):
    encoded = base64.b64encode(file_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"


AI_ASSESSMENT_MODEL_TIMEOUT_SECONDS = 600
AI_ASSESSMENT_STALE_SECONDS = 720
AI_ASSESSMENT_HEARTBEAT_INTERVAL_SECONDS = 10


def post_chat_completion(api_key, api_base, payload, timeout=180):
    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def post_chat_completion_with_model_fallback(api_key, api_base, payload, model_candidates, timeout=180):
    errors = []
    for model_name in model_candidates:
        try:
            request_payload = dict(payload)
            request_payload['model'] = model_name
            return post_chat_completion(api_key, api_base, request_payload, timeout=timeout), model_name
        except requests.RequestException as exc:
            errors.append(f'{model_name}: {exc}')
            continue

    raise RuntimeError('all candidate models failed: ' + ' | '.join(errors))


def write_json_atomic(file_path, data):
    temp_path = f"{file_path}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)
    os.replace(temp_path, file_path)


def read_ai_assessment_state(file_path):
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file_obj:
            data = json.load(file_obj)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def update_ai_assessment_state(file_path, **updates):
    state = read_ai_assessment_state(file_path)
    now_iso = datetime.now().isoformat()
    state.update(updates)
    state['updated_at'] = now_iso
    state['heartbeat_at'] = now_iso
    write_json_atomic(file_path, state)
    return state


def _coerce_positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _clean_reference_text(value, limit=800):
    text = str(value or '').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '...'


def _build_chapter_outline_text(chapter):
    if not isinstance(chapter, dict):
        return ''

    sections = chapter.get('sections') if isinstance(chapter.get('sections'), list) else []
    lines = []
    for index, section in enumerate(sections[:12], start=1):
        if not isinstance(section, dict):
            continue
        section_title = str(section.get('title') or '').strip() or f'小节{index}'
        section_content = _clean_reference_text(section.get('content') or '', 180)
        if section_content:
            lines.append(f'{index}. {section_title}：{section_content}')
        else:
            lines.append(f'{index}. {section_title}')
    return '\n'.join(lines)


def _resolve_chapter_page_range(chapters, chapter_index):
    if not isinstance(chapters, list) or chapter_index < 0 or chapter_index >= len(chapters):
        return None, None

    current_chapter = chapters[chapter_index] if isinstance(chapters[chapter_index], dict) else {}
    start_page = _coerce_positive_int(current_chapter.get('start_page') or current_chapter.get('page'))
    next_start_page = None

    for next_chapter in chapters[chapter_index + 1:]:
        if not isinstance(next_chapter, dict):
            continue
        candidate = _coerce_positive_int(next_chapter.get('start_page') or next_chapter.get('page'))
        if candidate and (start_page is None or candidate > start_page):
            next_start_page = candidate
            break

    end_page = next_start_page - 1 if next_start_page and start_page and next_start_page > start_page else None
    return start_page, end_page


def _parse_material_for_assessment_reference(material, api_key=None, api_base=None):
    if not material:
        return None

    extension = get_material_extension(material)
    material_path = get_absolute_material_path(material.file_path)
    if not material_path or not os.path.exists(material_path):
        return None

    common_kwargs = {
        'upload_root': current_app.config['UPLOAD_FOLDER'],
        'owner_id': material.course_id,
        'file_hash': getattr(material, 'file_hash', None),
        'api_key': api_key,
        'api_base': api_base,
    }

    if extension == '.pdf':
        parsed = parse_pdf(material_path, parse_mode='assessment_reference_pdf', **common_kwargs)
        pages = parsed.get('structure', {}).get('pages') or []
        return {
            'kind': 'pdf',
            'unit_label': '页',
            'unit_count': int(parsed.get('assets', {}).get('page_count') or len(pages)),
            'material': material,
            'parsed': parsed,
        }

    if extension in {'.ppt', '.pptx'}:
        parsed = parse_ppt(material_path, parse_mode='assessment_reference_ppt', **common_kwargs)
        slides = parsed.get('structure', {}).get('slides') or []
        return {
            'kind': 'ppt',
            'unit_label': '页/幻灯片',
            'unit_count': int(parsed.get('assets', {}).get('slide_count') or len(slides)),
            'material': material,
            'parsed': parsed,
        }

    return None


def _select_material_for_chapter_reference(course_id, chapter, start_page, end_page, api_key=None, api_base=None):
    preferred_material_id = _coerce_positive_int(chapter.get('source_material_id') or chapter.get('material_id'))
    preferred_source_type = str(chapter.get('source_type') or '').strip().lower()

    if preferred_material_id:
        preferred_material = Material.query.get(preferred_material_id)
        if preferred_material and int(preferred_material.course_id) == int(course_id):
            try:
                parsed = _parse_material_for_assessment_reference(preferred_material, api_key=api_key, api_base=api_base)
                if parsed:
                    return parsed
            except Exception as exc:
                current_app.logger.warning('按章节来源课件读取参考内容失败: material_id=%s error=%s', preferred_material_id, exc)

    materials = Material.query.filter_by(course_id=course_id).order_by(Material.id.asc()).all()
    candidate_entries = []
    target_end = end_page or start_page or 1

    for material in materials:
        extension = get_material_extension(material)
        if extension not in {'.pdf', '.ppt', '.pptx'}:
            continue
        if preferred_source_type == 'pdf' and extension != '.pdf':
            continue
        if preferred_source_type == 'ppt' and extension not in {'.ppt', '.pptx'}:
            continue

        try:
            parsed = _parse_material_for_assessment_reference(material, api_key=api_key, api_base=api_base)
        except Exception as exc:
            current_app.logger.warning('读取课件参考内容失败: material_id=%s error=%s', material.id, exc)
            continue

        if not parsed:
            continue

        unit_count = parsed.get('unit_count') or 0
        score = 0
        if start_page and unit_count < start_page:
            score += 10000 + (start_page - unit_count)
        elif target_end and unit_count >= target_end:
            score += max(0, unit_count - target_end)
        elif target_end:
            score += 5000 + abs(unit_count - target_end)

        candidate_entries.append((score, material.id, parsed))

    if not candidate_entries:
        return None

    candidate_entries.sort(key=lambda item: (item[0], item[1]))
    return candidate_entries[0][2]


def _build_material_reference_excerpt(parsed_material, start_page, end_page, max_units=12, max_chars=7000):
    if not parsed_material:
        return ''

    kind = parsed_material.get('kind')
    parsed = parsed_material.get('parsed') or {}
    unit_count = parsed_material.get('unit_count') or 0
    start = start_page or 1
    if unit_count and start > unit_count:
        return ''

    if end_page and end_page >= start:
        effective_end = min(end_page, start + max_units - 1)
    else:
        effective_end = min(unit_count or start, start + max_units - 1)

    if kind == 'pdf':
        items = parsed.get('structure', {}).get('pages') or []
        unit_key = 'page_number'
        unit_label = '第{number}页'

        def get_item_text(item):
            return item.get('text') or item.get('ocr_text') or ''
    else:
        items = parsed.get('structure', {}).get('slides') or []
        unit_key = 'slide_index'
        unit_label = '第{number}页/幻灯片'

        def get_item_text(item):
            return (
                item.get('speaker_notes_weighted_text')
                or item.get('text')
                or item.get('ocr_text')
                or item.get('notes')
                or ''
            )

    excerpts = []
    current_length = 0
    for item in items:
        try:
            number = int(item.get(unit_key) or 0)
        except (TypeError, ValueError):
            continue
        if number < start or number > effective_end:
            continue

        snippet = _clean_reference_text(get_item_text(item), 900)
        if not snippet:
            continue

        block = f'[{unit_label.format(number=number)}]\n{snippet}'
        projected = current_length + len(block) + 2
        if excerpts and projected > max_chars:
            break
        excerpts.append(block)
        current_length = projected

    return '\n\n'.join(excerpts).strip()


def build_chapter_reference_context(course_id, chapter_id, fallback_title='', api_key=None, api_base=None, status_callback=None):
    normalized_course_id = _coerce_positive_int(course_id)
    if not normalized_course_id:
        return {}

    chapters = load_course_chapters(current_app.config['UPLOAD_FOLDER'], normalized_course_id)
    if not chapters:
        return {}

    chapter = None
    chapter_index = None
    normalized_chapter_id = _coerce_positive_int(chapter_id)
    if normalized_chapter_id:
        candidate_index = normalized_chapter_id - 1
        if 0 <= candidate_index < len(chapters):
            chapter = chapters[candidate_index]
            chapter_index = candidate_index

    if chapter is None and fallback_title:
        normalized_title = str(fallback_title).strip()
        for index, item in enumerate(chapters):
            if str(item.get('title') or '').strip() == normalized_title:
                chapter = item
                chapter_index = index
                break

    if chapter is None or chapter_index is None:
        return {}

    chapter_title = str(chapter.get('title') or fallback_title or '').strip()
    chapter_outline = _build_chapter_outline_text(chapter)
    start_page, end_page = _resolve_chapter_page_range(chapters, chapter_index)
    reference_context = {
        'chapter_title': chapter_title,
        'chapter_outline': chapter_outline,
        'start_page': start_page,
        'end_page': end_page,
    }

    if not start_page:
        return reference_context

    if callable(status_callback):
        status_callback('collecting_reference', '正在读取章节对应的课件页内容...', 24)

    selected_material = _select_material_for_chapter_reference(
        normalized_course_id,
        chapter,
        start_page,
        end_page,
        api_key=api_key,
        api_base=api_base,
    )
    if not selected_material:
        reference_context['reference_note'] = '未找到可用于按页提取内容的 PDF/PPT 课件资源。'
        return reference_context

    reference_excerpt = _build_material_reference_excerpt(selected_material, start_page, end_page)
    material = selected_material.get('material')
    material_title = getattr(material, 'title', '') if material else ''
    unit_label = selected_material.get('unit_label') or '页'

    reference_context.update({
        'material_title': material_title,
        'material_type': selected_material.get('kind'),
        'page_range_label': f'{start_page}-{end_page}{unit_label}' if end_page and end_page >= start_page else f'{start_page}{unit_label}',
        'reference_excerpt': reference_excerpt,
    })
    if not reference_excerpt:
        reference_context['reference_note'] = '已定位到章节页码，但未提取到足够的课件文本。'
    return reference_context


def extract_message_content(response_json):
    choices = response_json.get('choices') or []
    if not choices:
        return ''

    content = choices[0].get('message', {}).get('content', '')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(str(item.get('text') or ''))
        return ''.join(parts)
    return str(content or '')


def parse_questions_from_image_with_ai(file_bytes, mime_type):
    api_key, api_base, _ = get_api_config()
    if not api_key:
        raise ValueError('未配置 AI 模型，无法进行图片识别')

    image_data_url = build_image_data_url(file_bytes, mime_type)
    prompt = """
你是一名试卷图片解析助手。请先识别图片中的文字，再按题目结构进行语义拆分。

请严格返回一个 JSON 对象，不要输出 Markdown，不要解释。格式如下：
{
  "ocr_text": "按阅读顺序整理后的完整文字",
  "questions": [
    {
      "type": "multiple_choice | multiple_answer | fill_blank | short_answer",
      "content": "仅保留题干，不要带题号、分值、姓名班级等无关信息",
      "options": ["选项A", "选项B"],
      "analysis": "题目解析或解题说明，没有就填空字符串"
    }
  ],
  "ignored_texts": ["页眉页脚、考试说明、姓名班级考号、分值提示等无用信息"]
}

规则：
1. 必须按图片中的顺序输出题目。
2. 单选题用 multiple_choice，多选题用 multiple_answer，填空题用 fill_blank，简答/解答/论述/问答题用 short_answer。
3. 如果图片里有“解析”“答案”“解：”“参考答案”等内容，尽量放进对应题目的 analysis。
4. 不要把题号、密封线、姓名、班级、总分、页码、考试说明、每题分值等内容放进题干。
5. 如果一张图里有多道题，必须拆成多道。
6. 如果没有把握属于题目正文，就放到 ignored_texts。
7. 只输出 JSON。
""".strip()

    payload = {
        'messages': [
            {'role': 'system', 'content': '你擅长 OCR 与试卷结构化解析。'},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': image_data_url}},
                ],
            },
        ],
        'temperature': 0.1,
        'max_tokens': 3000,
        'stream': False,
    }

    response_json, used_model = post_chat_completion_with_model_fallback(
        api_key=api_key,
        api_base=api_base,
        payload=payload,
        model_candidates=get_model_candidates('ocr'),
    )
    content = extract_message_content(response_json)
    parsed_payload = extract_json_object_from_text(content) or {}
    questions = sanitize_ai_import_questions(parsed_payload.get('questions'))
    ignored_texts = sanitize_ignored_texts(parsed_payload.get('ignored_texts'))
    ocr_text = normalize_import_text(parsed_payload.get('ocr_text') or '')

    if not questions:
        raise ValueError('AI 未能从图片中识别出可用题目')

    return {
        'questions': questions,
        'ignored_texts': ignored_texts,
        'ocr_text': ocr_text,
        'model': used_model,
    }


def should_use_ai_result(ai_questions, heuristic_questions, source_text):
    if not ai_questions:
        return False

    heuristic_count = len(heuristic_questions or [])
    ai_count = len(ai_questions)
    source_length = len(source_text or '')

    if heuristic_count <= 1:
        return True

    if ai_count >= heuristic_count:
        return True

    if ai_count >= 2 and source_length < 2000:
        return True

    return False


def parse_questions_from_docx_with_ai(source_text, heuristic_questions):
    api_key, api_base, model_name = get_api_config()
    if not api_key:
        return {
            'questions': heuristic_questions,
            'mode': 'rule',
            'message': '未配置 AI 模型，已使用规则解析'
        }

    try:
        client = openai.OpenAI(api_key=api_key, base_url=api_base) if api_base else openai.OpenAI(api_key=api_key)
        prompt = f"""
你是试卷结构化助手。请从用户上传的试卷文本中识别每一道题，并判断题型。

要求：
1. 只返回 JSON，不要 Markdown，不要解释。
2. 输出格式必须是：
{{
  "questions": [
    {{
      "type": "multiple_choice | multiple_answer | fill_blank | short_answer",
      "content": "题干全文",
      "options": ["选项A", "选项B"]
    }}
  ]
}}
3. 必须按原试卷顺序输出所有题目。
4. 如果是单选题，type 用 multiple_choice；如果是多选题，type 用 multiple_answer。
5. 如果是填空题，type 用 fill_blank，不要输出 options。
6. 如果是简答/解答/论述/问答题，type 用 short_answer，不要输出 options。
7. 不要把“每小题几分”“共几分”“说明”等提示语单独当成题目。
8. 如果一行里包含完整选择题和多个选项，请拆出题干和 options。
9. 如果规则预解析有错误，请你纠正；如果预解析漏题，请你补上。

规则预解析结果：
{json.dumps(heuristic_questions, ensure_ascii=False)}

原始试卷文本：
{source_text[:15000]}
""".strip()

        response = client.chat.completions.create(
            model=model_name or 'gpt-4o-mini',
            messages=[
                {"role": "system", "content": "你擅长把试卷文档解析为结构化题目 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=4000,
        )
        content = response.choices[0].message.content if response.choices else ''
        parsed_payload = extract_json_object_from_text(content)
        ai_questions = sanitize_ai_import_questions((parsed_payload or {}).get('questions'))

        if should_use_ai_result(ai_questions, heuristic_questions, source_text):
            return {
                'questions': ai_questions,
                'mode': 'ai',
                'message': '已使用 AI 语义解析试卷结构'
            }

        return {
            'questions': heuristic_questions,
            'mode': 'rule',
            'message': 'AI 结果不稳定，已回退到规则解析'
        }
    except Exception as exc:
        current_app.logger.warning(f'AI 解析 Word 题目失败，已回退规则解析: {exc}')
        return {
            'questions': heuristic_questions,
            'mode': 'rule',
            'message': 'AI 解析失败，已回退到规则解析'
        }

# 应用错误处理装饰器到关键API端点
@learning_bp.route('/assessments/ai-generate', methods=['POST', 'OPTIONS'])
@api_error_handler
def generate_ai_assessment():
    """使用AI自动生成评估内容"""
    # 调试信息：记录完整请求详情
    current_app.logger.info(f"收到请求: {request.method} {request.path} (完整URL: {request.url})")
    current_app.logger.info(f"请求头: {request.headers}")
    
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        current_app.logger.info("处理OPTIONS请求")
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Content-Type', 'application/json')
        return response
        
    data = request.json
    current_app.logger.info(f"收到AI自动生成评估请求: {data}")
    
    # 验证必要数据
    required_fields = ['course_name', 'course_description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # 获取课程信息
    course_name = data['course_name']
    course_description = data['course_description']
    extra_info = data.get('extra_info', '')
    assessment_type = data.get('assessment_type', 'quiz')
    difficulty = data.get('difficulty', 'medium')
    course_id = data.get('course_id')
    chapter_id = data.get('chapter_id')
    chapter_title = str(data.get('chapter_title') or '').strip()
    
    # 创建唯一的请求ID (使用时间戳+课程ID)
    request_id = f"{int(time.time())}_{course_id}_{str(uuid.uuid4())[:8]}"
    
    # 创建保存目录
    ai_assessments_dir = os.path.join(current_app.root_path, 'uploads', 'ai_assessments')
    os.makedirs(ai_assessments_dir, exist_ok=True)
    
    # 构建文件路径
    file_path = os.path.join(ai_assessments_dir, f"assessment_{request_id}.json")
    
    # 保存请求信息
    request_data = {
        'status': 'processing',
        'request_id': request_id,
        'course_name': course_name,
        'course_description': course_description,
        'extra_info': extra_info,
        'assessment_type': assessment_type,
        'difficulty': difficulty,
        'course_id': course_id,
        'chapter_id': chapter_id,
        'chapter_title': chapter_title,
        'timestamp': datetime.now().isoformat(),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'heartbeat_at': datetime.now().isoformat(),
        'progress_stage': 'queued',
        'progress_message': '请求已创建，等待后台任务启动...',
        'progress_percent': 5,
    }
    
    # 先保存请求信息
    write_json_atomic(file_path, request_data)
    
    current_app.logger.info(f"请求信息已保存到: {file_path}")
    
    # 在后台线程中处理AI生成，避免长时间阻塞
    # 获取当前的应用实例，以便在线程中使用
    app = current_app._get_current_object()
    
    def generate_in_background():
        # 在线程中使用应用上下文
        with app.app_context():
            heartbeat_stop = threading.Event()

            def heartbeat_worker():
                while not heartbeat_stop.wait(AI_ASSESSMENT_HEARTBEAT_INTERVAL_SECONDS):
                    try:
                        update_ai_assessment_state(file_path)
                    except Exception as heartbeat_error:
                        app.logger.warning(
                            '刷新 AI 评估生成心跳失败: request_id=%s error=%s',
                            request_id,
                            heartbeat_error,
                        )

            heartbeat_thread = threading.Thread(
                target=heartbeat_worker,
                daemon=True,
                name=f'ai-assessment-heartbeat-{request_id}',
            )

            def stop_heartbeat():
                heartbeat_stop.set()
                if heartbeat_thread.is_alive():
                    heartbeat_thread.join(timeout=1)

            try:
                update_ai_assessment_state(
                    file_path,
                    status='processing',
                    progress_stage='starting',
                    progress_message='后台任务已启动，准备模型资源中...',
                    progress_percent=10,
                    started_at=datetime.now().isoformat(),
                )
                heartbeat_thread.start()

                def status_callback(stage, message, percent):
                    update_ai_assessment_state(
                        file_path,
                        status='processing',
                        progress_stage=stage,
                        progress_message=message,
                        progress_percent=percent,
                    )

                # 调用AI生成评估
                generated_assessment = generate_assessment_with_ai(
                    course_name, 
                    course_description, 
                    extra_info, 
                    assessment_type, 
                    difficulty,
                    course_id=course_id,
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    status_callback=status_callback,
                )
                
                # 添加课程ID（如果提供）
                if course_id:
                    generated_assessment['course_id'] = course_id
                
                # 添加请求ID用于跟踪
                generated_assessment['request_id'] = request_id

                stop_heartbeat()
                
                # 保存生成的评估
                result_data = {
                    'status': 'success',
                    'request_id': request_id,
                    'assessment': generated_assessment,
                    'timestamp': datetime.now().isoformat(),
                    'progress_stage': 'completed',
                    'progress_message': '评估生成完成',
                    'progress_percent': 100,
                    'completed_at': datetime.now().isoformat(),
                }
                
                write_json_atomic(file_path, result_data)
                
                app.logger.info(f"生成的评估已保存到: {file_path}")
                
            except Exception as e:
                stop_heartbeat()

                # 保存错误信息
                error_data = {
                    'status': 'error',
                    'request_id': request_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'progress_stage': 'failed',
                    'progress_message': '评估生成失败',
                    'progress_percent': 100,
                    'completed_at': datetime.now().isoformat(),
                }
                
                write_json_atomic(file_path, error_data)
                
                app.logger.error(f"生成评估失败: {str(e)}")
    
    # 启动后台线程
    thread = threading.Thread(target=generate_in_background)
    thread.daemon = False
    thread.start()
    
    # 立即返回请求ID，让前端可以用它来后续查询结果
    response_data = {
        'status': 'processing',
        'message': '正在生成评估，请稍后查询结果',
        'request_id': request_id
    }
    
    response = jsonify(response_data)
    
    # 添加CORS头
    origin = request.headers.get('Origin', '')
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
        
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,GET,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Content-Type', 'application/json')
    
    # 调试输出
    current_app.logger.info(f"返回响应: {response_data}")
    
    return response

@learning_bp.route('/record', methods=['POST'])
def record_learning_activity():
    """记录学习活动"""
    data = request.json
    
    # 验证必要数据
    required_fields = ['student_id', 'course_id', 'activity_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    learning_record = LearningRecord(
        student_id=data['student_id'],
        course_id=data['course_id'],
        activity_type=data['activity_type'],
        activity_detail=json.dumps(data.get('activity_detail', {})),
        duration=data.get('duration')
    )
    
    db.session.add(learning_record)
    db.session.commit()
    
    return jsonify({'success': True, 'record_id': learning_record.id}), 201

@learning_bp.route('/history/<int:student_id>', methods=['GET'])
def get_learning_history(student_id):
    """获取学生的学习历史记录"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    records = LearningRecord.query.filter_by(student_id=student_id)\
        .order_by(LearningRecord.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'records': [record.to_dict() for record in records.items],
        'total': records.total,
        'pages': records.pages,
        'page': page
    }), 200

# 添加OPTIONS请求处理
@learning_bp.route('/courses', methods=['OPTIONS'])
def courses_options():
    return build_cors_preflight_response('GET,POST,OPTIONS')

# 获取课程列表
@learning_bp.route('/courses', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_courses():
    """获取课程列表"""
    current_user = get_current_user_from_request()

    # 获取查询参数
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 构建查询
    query = Course.query

    if current_user:
        if current_user.role == 'student':
            query = query.filter(
                or_(
                    Course.is_public.is_(True),
                    Course.students.any(User.id == current_user.id)
                )
            )
        elif current_user.role == 'teacher':
            query = query.filter(Course.teacher_id == current_user.id)
    else:
        query = query.filter(Course.is_public.is_(True))
    
    # 应用过滤条件
    if category:
        query = query.filter_by(category=category)
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(Course.name.ilike(search_term) | Course.description.ilike(search_term))

    query = query.order_by(Course.updated_at.desc(), Course.created_at.desc())
    
    # 执行分页查询
    courses_pagination = query.paginate(page=page, per_page=per_page)
    
    # 准备响应数据
    enrolled_course_ids = set()
    if current_user and current_user.role == 'student':
        enrolled_course_ids = {
            int(course.id)
            for course in (current_user.courses_enrolled or [])
        }

    courses_data = []
    for course in courses_pagination.items:
        course_dict = course.to_dict()
        # 添加额外信息
        course_dict['material_count'] = Material.query.filter_by(course_id=course.id).count()
        course_dict['is_enrolled'] = course.id in enrolled_course_ids
        courses_data.append(course_dict)
    
    return jsonify({
        'courses': courses_data,
        'total': courses_pagination.total,
        'pages': courses_pagination.pages,
        'current_page': page
    })

# 获取课程详情
@learning_bp.route('/courses/<int:course_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_course(course_id):
    """获取课程详情"""
    current_user = get_current_user_from_request()

    # 查找课程
    course = Course.query.get(course_id)
    access_error = ensure_course_read_access(course, current_user)
    if access_error:
        return access_error
    
    # 获取课程详情
    course_data = course.to_dict()
    
    # 添加额外信息
    course_data['material_count'] = Material.query.filter_by(course_id=course.id).count()
    course_data['teacher_name'] = User.query.get(course.teacher_id).full_name if course.teacher_id else None
    course_data['is_enrolled'] = bool(
        current_user and
        current_user.role == 'student' and
        course in (current_user.courses_enrolled or [])
    )
    
    return jsonify(course_data)

@learning_bp.route('/enroll/<int:course_id>', methods=['POST'])
def enroll_course(course_id):
    """学生加入公开课程"""
    current_user = get_current_user_from_request()
    if not current_user or current_user.role != 'student':
        return jsonify({'error': 'Only students can enroll courses'}), 403

    course = Course.query.get(course_id)
    if not course or not course.is_public:
        return jsonify({'error': 'Course not found'}), 404

    if current_user in (course.students or []):
        return jsonify({
            'message': 'Already enrolled in course',
            'course': course.to_dict()
        }), 200

    course.students.append(current_user)
    db.session.add(LearningRecord(
        student_id=current_user.id,
        course_id=course.id,
        activity_type='enrolled',
        activity_detail='Student enrolled from course catalog'
    ))
    db.session.commit()

    course_data = course.to_dict()
    course_data['is_enrolled'] = True
    return jsonify({
        'message': 'Enrolled in course successfully',
        'course': course_data
    }), 201

@learning_bp.route('/unenroll/<int:course_id>', methods=['POST'])
def unenroll_course(course_id):
    """学生退出已加入课程"""
    current_user = get_current_user_from_request()
    if not current_user or current_user.role != 'student':
        return jsonify({'error': 'Only students can unenroll courses'}), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if current_user not in (course.students or []):
        return jsonify({'error': 'Student not enrolled in this course'}), 404

    course.students.remove(current_user)
    db.session.add(LearningRecord(
        student_id=current_user.id,
        course_id=course.id,
        activity_type='unenrolled',
        activity_detail='Student unenrolled from course catalog'
    ))
    db.session.commit()

    course_data = course.to_dict()
    course_data['is_enrolled'] = False
    return jsonify({
        'message': 'Unenrolled from course successfully',
        'course': course_data
    })

# 创建课程
@learning_bp.route('/courses', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
def create_course():
    """创建新课程"""
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '需要教师或管理员权限'}), 403

    # 检查是否有表单数据（包含文件上传）或JSON数据
    if request.content_type and 'multipart/form-data' in request.content_type:
        # 处理表单数据和文件上传
        if 'data' not in request.form:
            return jsonify({'error': 'Missing course data'}), 400
        
        try:
            # 解析JSON字符串
            data = json.loads(request.form['data'])
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # 处理封面图片
        cover_image_path = None
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # 创建课程封面目录
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'courses', 'covers')
                os.makedirs(upload_folder, exist_ok=True)
                
                # 保存文件
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # 设置相对路径
                cover_image_path = f'/uploads/courses/covers/{filename}'
    else:
        # 处理JSON数据
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        cover_image_path = None
    
    # 验证必要字段
    if 'name' not in data:
        return jsonify({'error': 'Course name is required'}), 400
    
    teacher_id = current_user.id
    if current_user.role == 'admin' and data.get('teacher_id') not in (None, '', 'null'):
        try:
            requested_teacher_id = int(data.get('teacher_id'))
        except (TypeError, ValueError):
            return jsonify({'error': 'teacher_id 必须是整数'}), 400
        requested_teacher = User.query.get(requested_teacher_id)
        if not requested_teacher or requested_teacher.role != 'teacher':
            return jsonify({'error': 'teacher_id 对应的教师不存在'}), 400
        teacher_id = requested_teacher_id
    
    # 创建新课程
    new_course = Course(
        name=data['name'],
        description=data.get('description', ''),
        category=data.get('category', ''),
        difficulty=data.get('difficulty', 'beginner'),
        is_public=data.get('is_public', True),
        cover_image=cover_image_path,
        teacher_id=teacher_id
    )
    
    db.session.add(new_course)
    db.session.commit()
    
    return jsonify(new_course.to_dict()), 201

# 更新课程
@learning_bp.route('/courses/<int:course_id>', methods=['PUT'])
# @jwt_required()  # 暂时禁用JWT认证要求
def update_course(course_id):
    """更新课程信息"""
    current_user = get_current_user_from_request()
    # 查找课程
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    # 检查是否有表单数据（包含文件上传）或JSON数据
    if request.content_type and 'multipart/form-data' in request.content_type:
        # 处理表单数据和文件上传
        if 'data' not in request.form:
            return jsonify({'error': 'Missing course data'}), 400
        
        try:
            # 解析JSON字符串
            data = json.loads(request.form['data'])
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # 处理封面图片
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # 创建课程封面目录
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'courses', 'covers')
                os.makedirs(upload_folder, exist_ok=True)
                
                # 保存文件
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # 设置相对路径
                course.cover_image = f'/uploads/courses/covers/{filename}'
    else:
        # 处理JSON数据
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
    
    # 更新课程信息
    if 'name' in data:
        course.name = data['name']
    
    if 'description' in data:
        course.description = data['description']
    
    if 'category' in data:
        course.category = data['category']
    
    if 'difficulty' in data:
        course.difficulty = data['difficulty']
    
    if 'is_public' in data:
        course.is_public = data['is_public']
    
    # 保存更改
    db.session.commit()
    
    return jsonify(course.to_dict())

# 删除课程
@learning_bp.route('/courses/<int:course_id>', methods=['DELETE'])
# @jwt_required()  # 暂时禁用JWT认证要求
def delete_course(course_id):
    """删除课程"""
    current_user = get_current_user_from_request()
    # 查找课程
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    course_data = course.to_dict()

    try:
        kb_roots = []
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(current_app.root_path)))
        normalized_course_id = str(course_id)
        for candidate in [
            os.path.join(project_root, 'uploads', 'knowledge_base', normalized_course_id),
            os.path.join(project_root, 'backend', 'uploads', 'knowledge_base', normalized_course_id),
        ]:
            if os.path.isdir(candidate):
                kb_roots.append(candidate)

        processed_material_ids = set()
        processed_queue_ids = set()

        # 清理课件资源、知识库索引与相关缓存
        materials = Material.query.filter_by(course_id=course_id).all()
        for material in materials:
            if material.id in processed_material_ids:
                continue
            cleanup_summary = purge_knowledge_assets_for_material(material)
            processed_material_ids.update(cleanup_summary.get('deleted_material_ids', []))
            processed_queue_ids.update(cleanup_summary.get('deleted_queue_ids', []))

        for queue_item in KnowledgeBaseQueue.query.filter_by(course_id=course_id).all():
            if queue_item.id in processed_queue_ids:
                continue
            cleanup_summary = purge_knowledge_assets_for_queue_item(queue_item)
            processed_queue_ids.update(cleanup_summary.get('deleted_queue_ids', []))

        # 清理关联业务数据
        LearningRecord.query.filter_by(course_id=course_id).delete(synchronize_session=False)
        ChatHistory.query.filter_by(course_id=course_id).delete(synchronize_session=False)
        StudentAIQuiz.query.filter_by(course_id=course_id).delete(synchronize_session=False)
        course.students.clear()

        assessments = Assessment.query.filter_by(course_id=course_id).all()
        assessment_ids = [assessment.id for assessment in assessments]
        if assessment_ids:
            AssessmentSubmission.query.filter(
                AssessmentSubmission.assessment_id.in_(assessment_ids)
            ).delete(synchronize_session=False)
            StudentAnswer.query.filter(
                StudentAnswer.assessment_id.in_(assessment_ids)
            ).delete(synchronize_session=False)
            db.session.execute(
                assessment_publish_classes.delete().where(
                    assessment_publish_classes.c.assessment_id.in_(assessment_ids)
                )
            )
        for assessment in assessments:
            db.session.delete(assessment)

        # 清理课程封面
        cover_path = get_absolute_material_path(course.cover_image)
        if cover_path and os.path.exists(cover_path) and os.path.isfile(cover_path):
            try:
                os.remove(cover_path)
            except Exception as exc:
                current_app.logger.warning(f"删除课程封面失败: {cover_path}, error={str(exc)}")

        # 清理课程目录下的上传资源和章节文件
        material_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'materials', str(course_id))
        chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters', str(course_id))

        if os.path.isdir(material_folder):
            try:
                shutil.rmtree(material_folder)
            except Exception as exc:
                current_app.logger.warning(f"删除课程资源目录失败: {material_folder}, error={str(exc)}")

        if os.path.isdir(chapters_folder):
            try:
                shutil.rmtree(chapters_folder)
            except Exception as exc:
                current_app.logger.warning(f"删除课程章节目录失败: {chapters_folder}, error={str(exc)}")

        for kb_root in kb_roots:
            try:
                shutil.rmtree(kb_root)
            except Exception as exc:
                current_app.logger.warning(f"删除课程知识库目录失败: {kb_root}, error={str(exc)}")

        db.session.delete(course)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"删除课程失败: course_id={course_id}")
        return jsonify({
            'status': 'error',
            'message': f'删除课程失败: {str(e)}'
        }), 500
    
    return jsonify({'message': 'Course deleted successfully', 'course': course_data})

@learning_bp.route('/my-courses', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_my_courses():
    current_user = get_current_user_from_request()

    if not current_user:
        return jsonify({'error': '未登录，无法获取课程列表'}), 401

    if current_user.role == 'student':
        my_courses = db.session.query(Course).join(
            Course.students
        ).filter(
            User.id == current_user.id
        ).order_by(
            Course.updated_at.desc(),
            Course.created_at.desc()
        ).all()
    elif current_user.role == 'admin':
        my_courses = Course.query.order_by(
            Course.updated_at.desc(),
            Course.created_at.desc()
        ).all()
    else:
        my_courses = Course.query.filter_by(teacher_id=current_user.id).order_by(
            Course.updated_at.desc(),
            Course.created_at.desc()
        ).all()

    return jsonify({
        'courses': [course.to_dict() for course in my_courses],
        'total': len(my_courses)
    })

# 获取课程的所有课件
@learning_bp.route('/courses/<int:course_id>/materials', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_course_materials(course_id):
    """获取课程的所有课件资源"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_read_access(course, current_user)
    if access_error:
        return access_error

    cleanup_stale_material_and_queue_records(course_id=course_id)

    # 获取课程的所有课件
    materials = Material.query.filter_by(course_id=course_id).all()
    has_changes = False
    for material in materials:
        if ensure_material_preview(material):
            has_changes = True
    if has_changes:
        db.session.commit()
    
    return jsonify({
        'materials': [build_material_dict(material) for material in materials],
        'total': len(materials)
    })

# 上传课件
@learning_bp.route('/courses/<int:course_id>/materials', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
def upload_material(course_id):
    """上传课件资源"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_upload_access(course, current_user)
    if access_error:
        return access_error
    
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # 如果用户没有选择文件，浏览器也会提交一个没有文件名的空部分
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # 获取文件信息
    original_filename = file.filename
    
    # 创建上传目录
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'materials', str(course_id))
    os.makedirs(upload_folder, exist_ok=True)
    
    # 保存文件，使用原始文件名
    file_path = os.path.join(upload_folder, original_filename)
    file.save(file_path)
    
    file_hash = calculate_file_hash(file_path)
    
    # 检查是否已存在相同哈希值的文件
    existing_material = Material.query.filter_by(
        file_hash=file_hash, 
        course_id=course_id
    ).first()
    
    if existing_material:
        if ensure_material_preview(existing_material, allow_retry=True):
            db.session.commit()

        # 删除刚上传的重复文件
        try:
            os.remove(file_path)
        except:
            pass
        
        # 返回已存在的文件信息
        material_dict = build_material_dict(existing_material)
        
        return jsonify({
            'status': 'duplicate',
            'message': f'文件 "{original_filename}" 已存在，避免重复上传',
            'material': material_dict
        }), 200
    
    # 获取文件大小
    file_size = os.path.getsize(file_path)
    size_str = format_file_size(file_size)
    
    # 根据文件扩展名确定文件类型
    _, file_ext = os.path.splitext(original_filename)
    file_extension = file_ext.lower()
    
    # 文件扩展名映射到类型
    extension_to_type = {
        '.pdf': 'PDF',
        '.doc': 'Word', '.docx': 'Word',
        '.ppt': 'PowerPoint', '.pptx': 'PowerPoint',
        '.xls': 'Excel', '.xlsx': 'Excel',
        '.jpg': 'Image', '.jpeg': 'Image', '.png': 'Image', 
        '.gif': 'Image', '.bmp': 'Image', '.webp': 'Image',
        '.mp4': 'Video', '.avi': 'Video', '.mov': 'Video',
        '.wmv': 'Video', '.flv': 'Video', '.mkv': 'Video',
        '.webm': 'Video', '.m4v': 'Video', '.3gp': 'Video',
        '.zip': 'Archive', '.rar': 'Archive', '.7z': 'Archive',
        '.txt': 'Text', 
        '.md': 'Markdown', '.markdown': 'Markdown',
        '.json': 'Text', '.xml': 'Text', '.csv': 'Text',
        '.html': 'Text', '.css': 'Text', '.js': 'Text'
    }
    
    # 获取文件类型
    material_type = extension_to_type.get(file_extension, 'Other')
    
    # 如果类型是Other，使用文件扩展名作为类型（不带点）
    if material_type == 'Other' and file_extension:
        material_type = file_extension[1:].upper()

    preview_file_path = None
    preview_status = 'not_applicable'
    preview_error = None

    if supports_generated_preview_by_extension(file_extension):
        preview_status = 'pending'
        try:
            preview_file_path = generate_office_preview(file_path, course_id, file_hash)
            preview_status = 'ready'
        except Exception as exc:
            preview_status = 'failed'
            preview_error = str(exc)
            current_app.logger.exception('上传后生成课件预览失败: %s', file_path)
    
    # 创建新的Material对象
    new_material = Material(
        title=original_filename,
        material_type=material_type,
        file_path=f'/uploads/materials/{course_id}/{original_filename}',
        preview_file_path=preview_file_path,
        preview_status=preview_status,
        preview_error=preview_error,
        file_hash=file_hash,  # 添加文件哈希值
        content=f'Original filename: {original_filename}',
        course_id=course_id
    )
    
    # 添加到数据库
    db.session.add(new_material)
    db.session.commit()
    
    # 返回创建的材料
    material_dict = build_material_dict(new_material)
    material_dict['size'] = size_str  # 添加文件大小信息
    
    return jsonify({
        'status': 'success',
        'message': f'文件 "{original_filename}" 上传成功',
        'material': material_dict
    }), 201

# 获取单个课件详情
@learning_bp.route('/materials/<int:material_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_material(material_id):
    """获取单个课件详情"""
    current_user = get_current_user_from_request()
    # 查找材料
    material = Material.query.get(material_id)
    access_error = ensure_material_read_access(material, current_user)
    if access_error:
        return access_error
    
    if ensure_material_preview(material):
        db.session.commit()

    # 返回材料详情
    material_dict = build_material_dict(material)
    
    return jsonify(material_dict)

# 更新课件
@learning_bp.route('/materials/<int:material_id>', methods=['PUT'])
# @jwt_required()  # 暂时禁用JWT认证要求
def update_material(material_id):
    """更新课件信息"""
    current_user = get_current_user_from_request()
    # 查找材料
    material = Material.query.get(material_id)
    access_error = ensure_material_manage_access(material, current_user)
    if access_error:
        return access_error
    
    # 获取请求数据
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # 更新材料信息
    if 'title' in data:
        material.title = data['title']
    if 'description' in data:
        material.description = data['description']
    if 'content' in data:
        material.content = data['content']
    
    # 保存更改
    db.session.commit()
    
    ensure_material_preview(material)
    db.session.commit()
    
    # 返回更新后的材料信息
    material_dict = build_material_dict(material)
    
    return jsonify(material_dict)

# 下载课件
@learning_bp.route('/materials/<int:material_id>/download', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def download_material(material_id):
    """下载课件资源"""
    current_user = get_current_user_from_request()
    # 查找材料
    material = Material.query.get(material_id)
    access_error = ensure_material_read_access(material, current_user)
    if access_error:
        return access_error
    
    # 获取文件路径
    file_path = os.path.join(current_app.root_path, material.file_path.lstrip('/'))
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # 获取原始文件名
    original_filename = None
    if material.content and material.content.startswith('Original filename:'):
        original_filename = material.content.replace('Original filename:', '').strip()
    
    # 如果没有原始文件名，使用路径中的文件名
    download_name = original_filename or os.path.basename(file_path)
    
    # 发送文件 - 确保以二进制模式发送
    try:
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name=download_name,
            mimetype='application/octet-stream'  # 使用通用的二进制MIME类型
        )
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

# 删除课件
@learning_bp.route('/materials/<int:material_id>', methods=['DELETE'])
# @jwt_required()  # 暂时禁用JWT认证要求
def delete_material(material_id):
    """删除课件资源"""
    current_user = get_current_user_from_request()
    # 查找材料
    material = Material.query.get(material_id)
    access_error = ensure_material_manage_access(material, current_user)
    if access_error:
        return access_error
    
    material_dict = build_material_dict(material)
    try:
        cleanup_summary = purge_knowledge_assets_for_material(material)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("删除材料失败: material_id=%s", material_id)
        return jsonify({'error': 'Failed to delete material'}), 500
    
    return jsonify({
        'message': 'Material deleted successfully',
        'material': material_dict,
        'cleanup': cleanup_summary,
    })

# 获取课程的所有学生
@learning_bp.route('/courses/<int:course_id>/students', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_course_students(course_id):
    """获取课程的所有学生"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    # 获取查询参数
    search = request.args.get('search', '')
    
    # 获取课程的所有学生
    students = course.students
    
    # 如果有搜索参数，过滤学生
    if search:
        search = search.lower()
        filtered_students = []
        for student in students:
            if search in student.username.lower() or search in student.email.lower() or (student.full_name and search in student.full_name.lower()):
                filtered_students.append(student)
        students = filtered_students
    
    # 准备响应数据
    students_data = []
    for student in students:
        # 获取学生的学习记录
        learning_records = LearningRecord.query.filter_by(
            student_id=student.id, 
            course_id=course_id
        ).order_by(LearningRecord.timestamp.desc()).first()
        
        # 计算学生进度（这里简化为随机值，实际应用中应该基于完成的材料和评估）
        progress = 0
        if learning_records:
            # 这里可以实现更复杂的进度计算逻辑
            progress = 50  # 示例值
        
        # 获取最后活动时间
        last_activity = None
        if learning_records:
            last_activity = learning_records.timestamp.strftime('%Y-%m-%d %H:%M')
        
        # 构建学生数据
        student_data = {
            'id': student.id,
            'name': student.full_name or student.username,
            'email': student.email,
            'progress': progress,
            'last_activity': last_activity or '未活动'
        }
        students_data.append(student_data)
    
    return jsonify({
        'students': students_data,
        'total': len(students_data)
    })

# 获取可添加到课程的学生
@learning_bp.route('/courses/<int:course_id>/available-students', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_available_students(course_id):
    """获取可添加到课程的学生"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    # 获取当前课程的所有学生ID
    current_student_ids = [student.id for student in course.students]
    
    # 获取所有学生角色的用户，但不包括已在课程中的学生
    available_students = User.query.filter(
        User.role == 'student',
        ~User.id.in_(current_student_ids) if current_student_ids else True
    ).all()
    
    # 准备响应数据
    students_data = []
    for student in available_students:
        student_data = {
            'id': student.id,
            'name': student.full_name or student.username,
            'email': student.email,
            'role': student.role
        }
        students_data.append(student_data)
    
    return jsonify({
        'students': students_data,
        'total': len(students_data)
    })

# 添加学生到课程
@learning_bp.route('/courses/<int:course_id>/students', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
def add_students_to_course(course_id):
    """添加学生到课程"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    # 获取请求数据
    data = request.json
    if not data or 'student_ids' not in data:
        return jsonify({'error': 'Missing student_ids'}), 400
    
    student_ids = data['student_ids']
    if not isinstance(student_ids, list):
        return jsonify({'error': 'student_ids must be a list'}), 400
    
    # 获取当前课程的学生ID
    current_student_ids = [student.id for student in course.students]
    
    # 添加新学生
    added_students = []
    for student_id in student_ids:
        if student_id not in current_student_ids:
            student = User.query.get(student_id)
            if student and student.role == 'student':
                course.students.append(student)
                
                # 记录学习活动
                record = LearningRecord(
                    student_id=student.id,
                    course_id=course.id,
                    activity_type='enrolled',
                    activity_detail='Enrolled to course'
                )
                db.session.add(record)
                
                # 构建学生数据
                student_data = {
                    'id': student.id,
                    'name': student.full_name or student.username,
                    'email': student.email,
                    'progress': 0,
                    'last_activity': datetime.utcnow().strftime('%Y-%m-%d %H:%M')
                }
                added_students.append(student_data)
    
    # 保存更改
    db.session.commit()
    
    return jsonify({
        'message': f'Added {len(added_students)} students to the course',
        'students': added_students
    }), 201

# 从课程中移除学生
@learning_bp.route('/courses/<int:course_id>/students/<int:student_id>', methods=['DELETE'])
# @jwt_required()  # 暂时禁用JWT认证要求
def remove_student_from_course(course_id, student_id):
    """从课程中移除学生"""
    current_user = get_current_user_from_request()
    # 检查课程是否存在
    course = Course.query.get(course_id)
    access_error = ensure_course_manage_access(course, current_user)
    if access_error:
        return access_error
    
    # 查找学生
    student = User.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # 检查学生是否在课程中
    if student not in course.students:
        return jsonify({'error': 'Student not enrolled in this course'}), 404
    
    # 构建学生数据（用于返回）
    student_data = {
        'id': student.id,
        'name': student.full_name or student.username,
        'email': student.email
    }
    
    # 从课程中移除学生
    course.students.remove(student)
    
    # 记录学习活动
    record = LearningRecord(
        student_id=student.id,
        course_id=course.id,
        activity_type='unenrolled',
        activity_detail='Removed from course'
    )
    db.session.add(record)
    
    # 保存更改
    db.session.commit()
    
    return jsonify({
        'message': 'Student removed from course successfully',
        'student': student_data
    })


@learning_bp.route('/teacher-classes', methods=['GET'])
@api_error_handler
def get_teacher_classes():
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '需要教师或管理员权限'}), 403

    query = TeacherClass.query.order_by(TeacherClass.updated_at.desc(), TeacherClass.created_at.desc())
    if current_user.role != 'admin':
        query = query.filter_by(teacher_id=current_user.id)

    teacher_classes = query.all()
    return jsonify({
        'classes': [teacher_class.to_dict() for teacher_class in teacher_classes],
        'total': len(teacher_classes)
    })


@learning_bp.route('/teacher-classes/<int:class_id>/available-students', methods=['GET'])
@api_error_handler
def get_teacher_class_available_students(class_id):
    teacher_class = TeacherClass.query.get(class_id)
    if not teacher_class:
        return jsonify({'error': '班级不存在'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_teacher_class_access(teacher_class, current_user)
    if access_error:
        return access_error

    search = str(request.args.get('search') or '').strip().lower()
    current_student_ids = {student.id for student in teacher_class.students}

    query = User.query.filter(User.role == 'student').order_by(User.created_at.desc(), User.id.desc())
    students = query.all()

    if search:
        filtered_students = []
        for student in students:
            if (
                search in str(student.username or '').lower()
                or search in str(student.email or '').lower()
                or search in str(student.full_name or '').lower()
            ):
                filtered_students.append(student)
        students = filtered_students

    students_data = []
    for student in students:
        students_data.append({
            'id': student.id,
            'username': student.username,
            'email': student.email,
            'full_name': student.full_name,
            'role': student.role,
            'created_at': student.created_at.isoformat() if student.created_at else None,
            'already_in_class': student.id in current_student_ids,
        })

    return jsonify({
        'students': students_data,
        'total': len(students_data),
    })


@learning_bp.route('/teacher-classes', methods=['POST'])
@api_error_handler
def create_teacher_class():
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '需要教师或管理员权限'}), 403

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '班级名称不能为空'}), 400

    teacher_class = TeacherClass(
        name=name,
        description=(data.get('description') or '').strip() or None,
        teacher_id=current_user.id,
    )

    student_ids = [int(student_id) for student_id in (data.get('student_ids') or [])]
    if student_ids:
        students = User.query.filter(User.id.in_(student_ids), User.role == 'student').all()
        teacher_class.students = students

    db.session.add(teacher_class)
    db.session.commit()

    return jsonify({
        'message': '班级创建成功',
        'class': teacher_class.to_dict()
    }), 201


@learning_bp.route('/teacher-classes/<int:class_id>', methods=['PUT'])
@api_error_handler
def update_teacher_class(class_id):
    teacher_class = TeacherClass.query.get(class_id)
    if not teacher_class:
        return jsonify({'error': '班级不存在'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_teacher_class_access(teacher_class, current_user)
    if access_error:
        return access_error

    data = request.get_json() or {}

    if 'name' in data:
        next_name = str(data.get('name') or '').strip()
        if not next_name:
            return jsonify({'error': '班级名称不能为空'}), 400
        teacher_class.name = next_name

    if 'description' in data:
        teacher_class.description = str(data.get('description') or '').strip() or None

    if 'student_ids' in data:
        normalized_student_ids = [int(student_id) for student_id in (data.get('student_ids') or [])]
        students = User.query.filter(User.id.in_(normalized_student_ids), User.role == 'student').all() if normalized_student_ids else []
        teacher_class.students = students

    db.session.commit()

    return jsonify({
        'message': '班级更新成功',
        'class': teacher_class.to_dict()
    })


@learning_bp.route('/teacher-classes/<int:class_id>', methods=['DELETE'])
@api_error_handler
def delete_teacher_class(class_id):
    teacher_class = TeacherClass.query.get(class_id)
    if not teacher_class:
        return jsonify({'error': '班级不存在'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_teacher_class_access(teacher_class, current_user)
    if access_error:
        return access_error

    db.session.delete(teacher_class)
    db.session.commit()

    return jsonify({'message': '班级删除成功'})


@learning_bp.route('/teacher-classes/<int:class_id>/students', methods=['POST'])
@api_error_handler
def add_students_to_teacher_class(class_id):
    teacher_class = TeacherClass.query.get(class_id)
    if not teacher_class:
        return jsonify({'error': '班级不存在'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_teacher_class_access(teacher_class, current_user)
    if access_error:
        return access_error

    data = request.get_json() or {}
    student_ids = data.get('student_ids') or []
    if not isinstance(student_ids, list) or not student_ids:
        return jsonify({'error': 'student_ids 不能为空'}), 400

    normalized_student_ids = [int(student_id) for student_id in student_ids]
    students = User.query.filter(User.id.in_(normalized_student_ids), User.role == 'student').all()
    existing_ids = {student.id for student in teacher_class.students}
    for student in students:
        if student.id not in existing_ids:
            teacher_class.students.append(student)

    db.session.commit()

    return jsonify({
        'message': '学生已加入班级',
        'class': teacher_class.to_dict()
    })


@learning_bp.route('/teacher-classes/<int:class_id>/students/<int:student_id>', methods=['DELETE'])
@api_error_handler
def remove_student_from_teacher_class(class_id, student_id):
    teacher_class = TeacherClass.query.get(class_id)
    if not teacher_class:
        return jsonify({'error': '班级不存在'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_teacher_class_access(teacher_class, current_user)
    if access_error:
        return access_error

    student = next((item for item in teacher_class.students if item.id == student_id), None)
    if not student:
        return jsonify({'error': '该学生不在班级中'}), 404

    teacher_class.students.remove(student)
    db.session.commit()

    return jsonify({
        'message': '学生已移出班级',
        'class': teacher_class.to_dict()
    })

# ============ 评估相关API ============

@learning_bp.route('/assessments', methods=['GET', 'OPTIONS'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def get_assessments():
    """获取评估列表"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
        
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        course_id = request.args.get('course_id', type=int)
        search = (request.args.get('search') or '').strip()
        current_user = get_current_user_from_request()
        
        # 构建查询
        query = apply_assessment_visibility_filter(Assessment.query, current_user)
        
        # 如果指定了课程ID，筛选该课程的评估
        if course_id:
            query = query.filter_by(course_id=course_id)

        if search:
            query = query.filter(Assessment.title.ilike(f'%{search}%'))
            
        # 按创建时间降序排序
        query = query.order_by(Assessment.created_at.desc())
        
        # 分页
        try:
            assessments_pagination = query.paginate(page=page, per_page=per_page)
        except Exception as e:
            current_app.logger.error(f"分页查询失败: {str(e)}")
            # 尝试不使用created_by字段进行查询
            assessments = query.all()
            total = len(assessments)
            start = (page - 1) * per_page
            end = start + per_page
            assessments = assessments[start:end]
            
            # 创建自定义分页结果
            result = {
                'items': [a.to_dict() for a in assessments],
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page  # 向上取整
            }
        else:
            # 使用标准分页结果
            result = {
                'items': [a.to_dict() for a in assessments_pagination.items],
                'page': assessments_pagination.page,
                'per_page': assessments_pagination.per_page,
                'total': assessments_pagination.total,
                'pages': assessments_pagination.pages
            }
        
        # 创建响应
        response = jsonify({
            'status': 'success',
            'assessments': result['items'],
            'pagination': {
                'page': result['page'],
                'per_page': result['per_page'],
                'total': result['total'],
                'pages': result['pages']
            }
        })
        
        # 添加CORS头
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
        
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
            
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"获取评估列表失败: {str(e)}")
        
        # 创建错误响应
        response = jsonify({
            'status': 'error',
            'message': f'获取评估列表失败: {str(e)}'
        })
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        
        return response, 500

@learning_bp.route('/assessments/<int:assessment_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_assessment(assessment_id):
    """获取单个评估详情"""
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'error': 'Assessment not found'}), 404

    current_user = get_current_user_from_request()
    if current_user and current_user.role == 'teacher':
        access_error = ensure_assessment_manage_access(assessment, current_user)
        if access_error:
            return access_error
    elif current_user and current_user.role == 'student':
        if not assessment.is_published or not assessment_visible_to_student(assessment.id, current_user.id):
            return jsonify({'error': 'Assessment not found'}), 404
    elif not current_user:
        return jsonify({'error': '未登录，无法访问评估'}), 401
    
    return jsonify(assessment.to_dict())


@learning_bp.route('/assessments/<int:assessment_id>/publication', methods=['GET'])
@api_error_handler
def get_assessment_publication(assessment_id):
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'error': 'Assessment not found'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_assessment_publish_access(assessment, current_user)
    if access_error:
        return access_error

    available_classes_query = TeacherClass.query.order_by(TeacherClass.name.asc())
    if current_user.role != 'admin':
        available_classes_query = available_classes_query.filter_by(teacher_id=current_user.id)

    available_classes = available_classes_query.all()

    return jsonify({
        'assessment_id': assessment.id,
        'published_class_ids': [teacher_class.id for teacher_class in assessment.published_classes],
        'published_classes': [
            {
                'id': teacher_class.id,
                'name': teacher_class.name,
                'student_count': len(teacher_class.students),
            }
            for teacher_class in assessment.published_classes
        ],
        'available_classes': [teacher_class.to_dict(include_students=False) for teacher_class in available_classes],
    })


@learning_bp.route('/assessments/<int:assessment_id>/publication', methods=['PUT'])
@api_error_handler
def update_assessment_publication(assessment_id):
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'error': 'Assessment not found'}), 404

    current_user = get_current_user_from_request()
    access_error = ensure_assessment_publish_access(assessment, current_user)
    if access_error:
        return access_error

    data = request.get_json() or {}
    action = data.get('action')
    if action not in ['publish', 'unpublish']:
        return jsonify({'error': 'action 必须是 publish 或 unpublish'}), 400

    raw_class_ids = data.get('class_ids') or []
    if not isinstance(raw_class_ids, list) or not raw_class_ids:
        return jsonify({'error': '请选择至少一个班级'}), 400

    normalized_class_ids = [int(class_id) for class_id in raw_class_ids]
    available_classes_query = TeacherClass.query.filter(TeacherClass.id.in_(normalized_class_ids))
    if current_user.role != 'admin':
        available_classes_query = available_classes_query.filter_by(teacher_id=current_user.id)
    target_classes = available_classes_query.all()

    if not target_classes:
        return jsonify({'error': '未找到可操作的班级'}), 404

    existing_class_ids = {teacher_class.id for teacher_class in assessment.published_classes}
    if action == 'publish':
        for teacher_class in target_classes:
            if teacher_class.id not in existing_class_ids:
                assessment.published_classes.append(teacher_class)
        message = '发布成功'
    else:
        target_class_ids = {teacher_class.id for teacher_class in target_classes}
        assessment.published_classes = [
            teacher_class for teacher_class in assessment.published_classes
            if teacher_class.id not in target_class_ids
        ]
        message = '已取消发布'

    assessment.is_published = len(assessment.published_classes) > 0
    db.session.commit()

    return jsonify({
        'message': message,
        'assessment': assessment.to_dict()
    })


@learning_bp.route('/assessments/import-word-question', methods=['POST'])
@api_error_handler
def import_word_question():
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '只有教师或管理员可以导入 Word 题目'}), 403

    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'error': '请上传 Word 文件'}), 400

    original_filename = str(uploaded_file.filename or '').strip()
    extension = os.path.splitext(original_filename)[1].lower()
    if extension != '.docx':
        return jsonify({'error': '当前仅支持导入 .docx 文件'}), 400

    extracted_lines = extract_docx_lines(uploaded_file)
    if not extracted_lines:
        return jsonify({'error': 'Word 中未识别到可用文字'}), 400

    heuristic_questions = parse_questions_from_docx_lines(extracted_lines)
    source_text = '\n'.join(extracted_lines)
    ai_parse_result = parse_questions_from_docx_with_ai(source_text, heuristic_questions)
    parsed_questions = ai_parse_result.get('questions') or heuristic_questions
    if not parsed_questions:
        return jsonify({'error': '暂时无法从该 Word 中识别题目'}), 400

    return jsonify({
        'message': 'Word 题目导入成功',
        'question_count': len(parsed_questions),
        'questions': parsed_questions,
        'parse_mode': ai_parse_result.get('mode', 'rule'),
        'parse_message': ai_parse_result.get('message', ''),
    })


@learning_bp.route('/assessments/import-image-question', methods=['POST'])
@api_error_handler
def import_image_question():
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '只有教师或管理员可以导入图片题目'}), 403

    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'error': '请上传题目图片'}), 400

    original_filename = str(uploaded_file.filename or '').strip()
    extension = os.path.splitext(original_filename)[1].lower()
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
    if extension not in allowed_extensions:
        return jsonify({'error': '图片格式不支持，请上传 png/jpg/jpeg/webp/bmp/gif'}), 400

    file_bytes = uploaded_file.read()
    if not file_bytes:
        return jsonify({'error': '上传的图片为空'}), 400

    mime_type = uploaded_file.mimetype or mimetypes.guess_type(original_filename)[0] or 'image/png'
    parsed_result = parse_questions_from_image_with_ai(file_bytes, mime_type)

    return jsonify({
        'message': '图片题目识别成功',
        'question_count': len(parsed_result['questions']),
        'questions': parsed_result['questions'],
        'ignored_texts': parsed_result['ignored_texts'],
        'ocr_text': parsed_result['ocr_text'],
        'parse_mode': 'ai_ocr',
        'parse_message': f"已使用 OCR 模型 {parsed_result['model']} 识别并拆题",
    })

@learning_bp.route('/assessments', methods=['OPTIONS'])
def assessments_options():
    """处理评估接口的OPTIONS请求"""
    response = make_response()
    origin = request.headers.get('Origin', '')
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
        
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

@learning_bp.route('/assessments', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def create_assessment():
    """创建新的评估"""
    current_user = get_current_user_from_request()
    if not is_teacher_or_admin(current_user):
        return jsonify({'error': '需要教师或管理员权限'}), 403

    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
        
    try:
        data = request.json
        current_app.logger.info(f"接收到创建评估请求: {data}")
        
        # 验证必要字段
        required_fields = ['title', 'course_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        course = Course.query.get(data['course_id'])
        access_error = ensure_course_manage_access(course, current_user)
        if access_error:
            return access_error
        
        # 处理日期字段
        start_date = None
        if data.get('start_date'):
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except:
                start_date = None
                
        due_date = None
        if data.get('due_date'):
            try:
                due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            except:
                due_date = None
        
        # 确保questions字段不为NULL
        questions_json = '[]'
        if 'questions' in data and data['questions']:
            questions_json = json.dumps(data['questions'])
        
        # 创建评估对象
        assessment = Assessment(
            title=data['title'],
            description=data.get('description', ''),
            course_id=data['course_id'],
            total_score=data.get('total_score', 100),
            duration=data.get('duration'),
            start_date=start_date,
            due_date=due_date,
            max_attempts=data.get('max_attempts'),
            is_published=data.get('is_published', False),
            is_active=data.get('is_active', True),
            questions=questions_json,  # 直接设置questions字段
            created_by=current_user.id
        )
        
        # 保存评估
        db.session.add(assessment)
        db.session.commit()
        
        # 创建响应
        response = jsonify({
            'status': 'success',
            'message': '评估创建成功',
            'assessment_id': assessment.id,
            'assessment': assessment.to_dict()
        })
        
        # 添加CORS头
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
        
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
            
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"创建评估失败: {str(e)}")
        db.session.rollback()
        
        # 创建错误响应
        response = jsonify({
            'status': 'error',
            'message': f'创建评估失败: {str(e)}'
        })
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        
        return response, 500

@learning_bp.route('/assessments/<int:assessment_id>', methods=['PUT', 'OPTIONS'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def update_assessment(assessment_id):
    """更新评估"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response
        
    try:
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            return jsonify({'error': 'Assessment not found'}), 404

        current_user = get_current_user_from_request()
        access_error = ensure_assessment_manage_access(assessment, current_user)
        if access_error:
            return access_error
        
        data = request.json
        current_app.logger.info(f"接收到更新评估请求: {assessment_id}, 数据: {data}")
        
        # 处理日期字段
        if 'start_date' in data:
            try:
                assessment.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')) if data['start_date'] else None
            except:
                pass
                
        if 'due_date' in data:
            try:
                assessment.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data['due_date'] else None
            except:
                pass
        
        # 更新基本信息
        assessment.title = data.get('title', assessment.title)
        assessment.description = data.get('description', assessment.description)
        assessment.total_score = data.get('total_score', assessment.total_score)
        assessment.duration = data.get('duration', assessment.duration)
        assessment.max_attempts = data.get('max_attempts', assessment.max_attempts)
        assessment.is_published = data.get('is_published', assessment.is_published)
        assessment.is_active = data.get('is_active', assessment.is_active)
        
        # 更新题目
        if 'questions' in data and data['questions'] is not None:
            # 将题目列表转换为JSON字符串
            assessment.questions = json.dumps(data['questions'])
        
        db.session.commit()
        
        # 创建响应
        response = jsonify({
            'status': 'success',
            'message': '评估更新成功',
            'assessment_id': assessment.id,
            'assessment': assessment.to_dict()
        })
        
        # 添加CORS头
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
        
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
            
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"更新评估失败: {str(e)}")
        db.session.rollback()
        
        # 创建错误响应
        response = jsonify({
            'status': 'error',
            'message': f'更新评估失败: {str(e)}'
        })
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        
        return response, 500

@learning_bp.route('/assessments/<int:assessment_id>', methods=['OPTIONS'])
def assessment_options(assessment_id):
    """处理评估相关的OPTIONS请求"""
    response = make_response()
    origin = request.headers.get('Origin', '')
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
        
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@learning_bp.route('/assessments/<int:assessment_id>', methods=['DELETE'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def delete_assessment(assessment_id):
    """删除评估"""
    assessment = Assessment.query.get(assessment_id)
    current_user = get_current_user_from_request()
    access_error = ensure_assessment_manage_access(assessment, current_user)
    if access_error:
        return access_error
    
    assessment_data = assessment.to_dict()
    db.session.delete(assessment)
    db.session.commit()
    
    response = jsonify({'message': 'Assessment deleted successfully', 'assessment': assessment_data})
    
    # 添加CORS头
    origin = request.headers.get('Origin', '')
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
        
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    
    return response

@learning_bp.route('/assessments/<int:assessment_id>/submit', methods=['POST', 'OPTIONS'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def submit_assessment(assessment_id):
    """提交评估答案"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
        
    try:
        data = request.json
        current_app.logger.info(f"收到评估提交请求: assessment_id={assessment_id}, data={data}")
        
        # 详细记录请求数据结构
        current_app.logger.info(f"请求数据类型: {type(data)}")
        if 'answers' in data:
            current_app.logger.info(f"answers类型: {type(data['answers'])}")
            current_app.logger.info(f"answers内容: {data['answers']}")
        else:
            current_app.logger.info("请求中没有answers字段")
        
        current_user = get_current_user_from_request()
        student_id = current_user.id if current_user and current_user.role == 'student' else data.get('student_id', 1)
        current_app.logger.info(f"学生ID: {student_id}")
        
        # 验证评估是否存在
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            current_app.logger.error(f"评估不存在: assessment_id={assessment_id}")
            response = jsonify({'error': 'Assessment not found'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404

        if current_user and current_user.role == 'student':
            if not assessment.is_published or not assessment_visible_to_student(assessment.id, current_user.id):
                response = jsonify({'error': 'Assessment not found'})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 404
        
        # 验证截止日期
        if assessment.due_date and datetime.utcnow() > assessment.due_date:
            current_app.logger.warning(f"评估截止日期已过: assessment_id={assessment_id}")
            response = jsonify({'error': 'Assessment submission deadline has passed'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # 验证尝试次数
        existing_attempts = StudentAnswer.query.filter_by(
            student_id=student_id,
            assessment_id=assessment_id
        ).count()
        
        # 检查评估的最大尝试次数设置
        max_attempts = assessment.max_attempts or 3
        if existing_attempts >= max_attempts:
            current_app.logger.warning(f"超过最大尝试次数: student_id={student_id}, assessment_id={assessment_id}")
            response = jsonify({'error': 'Maximum number of attempts reached'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # 创建学生答案记录
        answers_json = json.dumps(data.get('answers', {}))
        current_app.logger.info(f"答案JSON长度: {len(answers_json)}")
        
        # 确保answers是有效的JSON格式
        try:
            # 尝试解析answers，确保它是有效的JSON
            answers_data = data.get('answers', {})
            if isinstance(answers_data, list):
                # 如果是列表，直接使用
                processed_answers = answers_data
            elif isinstance(answers_data, dict):
                # 如果是字典，转换为列表
                processed_answers = list(answers_data.values())
            else:
                # 其他情况，尝试转换为JSON字符串
                processed_answers = answers_data
                
            # 重新序列化为JSON字符串
            answers_json = json.dumps(processed_answers)
            current_app.logger.info(f"处理后的答案JSON: {answers_json[:100]}...")
        except Exception as e:
            current_app.logger.error(f"处理答案数据时出错: {str(e)}")
            return jsonify({'error': 'Invalid answers format'}), 400
        
        student_answer = StudentAnswer(
            student_id=student_id,
            assessment_id=assessment_id,
            answers=answers_json,
            submitted_at=datetime.utcnow()
        )
        
        # 自动评分逻辑
        score = 0
        assessment_data = assessment.get_questions()
        student_answers = data.get('answers', [])
        
        current_app.logger.info(f"题目数据类型: {type(assessment_data)}")
        current_app.logger.info(f"学生答案类型: {type(student_answers)}")
        
        # 确保student_answers是列表
        if isinstance(student_answers, dict):
            student_answers = list(student_answers.values())
        
        # 确保assessment_data是一个字典，包含sections字段
        if isinstance(assessment_data, dict) and 'sections' in assessment_data:
            sections = assessment_data['sections']
        else:
            # 如果不是新格式，将问题列表转换为单个section
            sections = [{
                'questions': assessment_data if isinstance(assessment_data, list) else [],
                'score_per_question': assessment.total_score / len(assessment_data) if isinstance(assessment_data, list) and len(assessment_data) > 0 else 0
            }]

        question_index = 0
        question_scores = []  # 存储每道题的得分
        question_feedback = []  # 存储每道题的反馈
        
        for section in sections:
            for question in section['questions']:
                if question_index >= len(student_answers):
                    question_scores.append(0)
                    question_feedback.append('')
                    question_index += 1
                    continue

                user_answer = student_answers[question_index]
                is_correct = False
                question_score = 0

                # 客观题自动评分
                if question['type'] in ['multiple_choice', 'true_false', 'multiple_select', 'fill_in_blank']:
                    if question['type'] == 'multiple_choice':
                        # 检查选项是否匹配（考虑字母和数字格式）
                        if isinstance(user_answer, str) and len(user_answer) == 1:
                            correct_index = int(question['answer'])
                            user_index = ord(user_answer) - ord('A')
                            is_correct = correct_index == user_index
                        else:
                            is_correct = str(user_answer) == str(question['answer'])

                    elif question['type'] == 'multiple_select':
                        # 多选题比较（转换为集合进行比较）
                        if isinstance(user_answer, list) and isinstance(question['answer'], list):
                            user_set = set(str(x) for x in user_answer)
                            correct_set = set(str(x) for x in question['answer'])
                            is_correct = user_set == correct_set

                    elif question['type'] == 'fill_in_blank':
                        # 填空题比较（考虑多个空的情况）
                        if isinstance(question['answer'], list):
                            if isinstance(user_answer, list) and len(user_answer) == len(question['answer']):
                                is_correct = all(
                                    str(u).lower().strip() == str(c).lower().strip()
                                    for u, c in zip(user_answer, question['answer'])
                                )
                        else:
                            # 单个答案的情况
                            if isinstance(user_answer, list):
                                user_answer = user_answer[0] if user_answer else ''
                            is_correct = str(user_answer).lower().strip() == str(question['answer']).lower().strip()

                    elif question['type'] == 'true_false':
                        # 判断题比较
                        is_correct = str(user_answer).lower() == str(question['answer']).lower()

                    # 如果正确，加分
                    if is_correct:
                        question_score = section['score_per_question']
                        score += question_score
                
                # 主观题需要人工评分，暂时不给分
                else:
                    question_score = 0
                
                # 记录每道题的得分和反馈
                question_scores.append(question_score)
                question_feedback.append('')
                question_index += 1

        # 设置总分和题目得分
        student_answer.score = score
        student_answer.question_scores = json.dumps(question_scores)
        student_answer.question_feedback = json.dumps(question_feedback)
        
        current_app.logger.info(f"保存学生答案: student_id={student_id}, assessment_id={assessment_id}, score={score}")
        
        # 保存到数据库
        db.session.add(student_answer)
        db.session.commit()
        
        current_app.logger.info(f"学生答案保存成功: submission_id={student_answer.id}")
        
        response = jsonify({
            'status': 'success',
            'message': 'Assessment submitted successfully',
            'submission_id': student_answer.id,
            'submitted_at': student_answer.submitted_at.isoformat(),
            'score': student_answer.score,
            'total_score': assessment.total_score,
            'question_scores': question_scores
        })
    except Exception as e:
        current_app.logger.error(f"提交评估失败: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        
        db.session.rollback()
        
        response = jsonify({
            'status': 'error',
            'message': f'Failed to submit assessment: {str(e)}'
        })
    
    # 添加CORS头
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    
    return response

@learning_bp.route('/submissions/<int:submission_id>/grade', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
def grade_submission(submission_id):
    """评分提交"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        # 获取评分数据
        score = data.get('score')
        feedback = data.get('feedback')
        question_scores = data.get('question_scores')
        question_feedback = data.get('question_feedback')
        grader_id = data.get('grader_id')
        
        # 查找提交记录
        submission = StudentAnswer.query.get(submission_id)
        if not submission:
            return jsonify({'error': '找不到提交记录'}), 404
        
        # 更新评分信息
        submission.score = score
        submission.feedback = feedback
        submission.question_scores = json.dumps(question_scores) if isinstance(question_scores, list) else question_scores
        submission.question_feedback = json.dumps(question_feedback) if isinstance(question_feedback, list) else question_feedback
        submission.grader_id = grader_id
        submission.graded_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '评分已保存',
            'submission_id': submission_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'评分失败: {str(e)}'}), 500

@learning_bp.route('/submissions/<int:submission_id>/ai-grade-question', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def ai_grade_question(submission_id):
    """使用AI评分单个题目"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        question_index = data.get('question_index')
        question_data = data.get('question_data')
        
        if question_index is None or not question_data:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 查找提交记录
        submission = StudentAnswer.query.get(submission_id)
        if not submission:
            return jsonify({'error': '找不到提交记录'}), 404
            
        # 获取题目和学生答案
        question = question_data.get('question')
        student_answer = question_data.get('student_answer')
        max_score = question_data.get('max_score', 10)  # 默认10分
        
        # 构建AI评分提示
        prompt = f"""
        你是一位专业的教育评分助手，请根据以下信息为学生的答案打分：
        
        题目：{question.get('stem', '')}
        题型：{question.get('section_type', '简答题')}
        满分：{max_score}分
        
        参考答案：{question.get('reference_answer') or question.get('answer') or '未提供参考答案'}
        
        学生答案：{student_answer}
        
        请根据学生答案与参考答案的匹配度、准确性、完整性和表达清晰度进行评分。
        分数应为整数或0.5的倍数，最高分为{max_score}分。
        
        请以JSON格式返回评分结果，格式如下：
        {{
          "score": 分数值(数字),
          "feedback": "评语"
        }}
        
        只返回JSON格式，不要有其他解释。
        """
        
        # 调用AI API进行评分
        api_key, api_base, model_name = get_api_config()
        
        if not api_key:
            return jsonify({'error': 'API密钥未配置'}), 500
        
        # 设置API客户端
        if api_base:
            client = openai.OpenAI(api_key=api_key, base_url=api_base)
        else:
            client = openai.OpenAI(api_key=api_key)
        
        # 调用AI API
        response = client.chat.completions.create(
            model=model_name or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位专业的教育评分助手，根据题目和参考答案为学生答案打分。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # 提取AI响应
        ai_response = response.choices[0].message.content.strip()
        
        # 解析JSON响应
        try:
            # 使用正则表达式找到JSON部分
            json_match = re.search(r'({[\s\S]*})', ai_response)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # 尝试直接解析整个响应
                result = json.loads(ai_response)
                
            # 确保分数在有效范围内
            score = result.get('score', 0)
            if score < 0:
                score = 0
            elif score > max_score:
                score = max_score
                
            # 四舍五入到最接近的0.5
            score = round(score * 2) / 2
            
            return jsonify({
                'status': 'success',
                'score': score,
                'feedback': result.get('feedback', '')
            })
            
        except (json.JSONDecodeError, ValueError) as e:
            current_app.logger.error(f"AI响应解析错误: {str(e)}, 响应: {ai_response}")
            return jsonify({
                'error': '无法解析AI响应',
                'raw_response': ai_response
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"AI评分错误: {str(e)}")
        return jsonify({'error': f'AI评分失败: {str(e)}'}), 500

@learning_bp.route('/submissions/<int:submission_id>/ai-grade-all', methods=['POST'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def ai_grade_all_subjective(submission_id):
    """使用AI评分所有主观题"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        questions_data = data.get('questions_data')
        
        if not questions_data or not isinstance(questions_data, list):
            return jsonify({'error': '缺少必要参数或格式错误'}), 400
        
        # 查找提交记录
        submission = StudentAnswer.query.get(submission_id)
        if not submission:
            return jsonify({'error': '找不到提交记录'}), 404
            
        # 获取当前的分数和反馈
        try:
            current_scores = json.loads(submission.question_scores) if submission.question_scores else []
            current_feedback = json.loads(submission.question_feedback) if submission.question_feedback else []
        except:
            current_scores = []
            current_feedback = []
            
        # 确保分数和反馈数组足够长
        while len(current_scores) < len(questions_data):
            current_scores.append(0)
        while len(current_feedback) < len(questions_data):
            current_feedback.append("")
            
        # 获取API配置
        api_key, api_base, model_name = get_api_config()
        
        if not api_key:
            return jsonify({'error': 'API密钥未配置'}), 500
        
        # 设置API客户端
        if api_base:
            client = openai.OpenAI(api_key=api_key, base_url=api_base)
        else:
            client = openai.OpenAI(api_key=api_key)
            
        # 对每个主观题进行评分
        for question_data in questions_data:
            index = question_data.get('index')
            question = question_data.get('question')
            student_answer = question_data.get('student_answer')
            max_score = question_data.get('max_score', 10)
            
            # 构建AI评分提示
            prompt = f"""
            你是一位专业的教育评分助手，请根据以下信息为学生的答案打分：
            
            题目：{question.get('stem', '')}
            题型：{question.get('section_type', '简答题')}
            满分：{max_score}分
            
            参考答案：{question.get('reference_answer') or question.get('answer') or '未提供参考答案'}
            
            学生答案：{student_answer}
            
            请根据学生答案与参考答案的匹配度、准确性、完整性和表达清晰度进行评分。
            分数应为整数或0.5的倍数，最高分为{max_score}分。
            
            请以JSON格式返回评分结果，格式如下：
            {{
              "score": 分数值(数字),
              "feedback": "评语"
            }}
            
            只返回JSON格式，不要有其他解释。
            """
            
            # 调用AI API
            response = client.chat.completions.create(
                model=model_name or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一位专业的教育评分助手，根据题目和参考答案为学生答案打分。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 提取AI响应
            ai_response = response.choices[0].message.content.strip()
            
            # 解析JSON响应
            try:
                # 使用正则表达式找到JSON部分
                json_match = re.search(r'({[\s\S]*})', ai_response)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                else:
                    # 尝试直接解析整个响应
                    result = json.loads(ai_response)
                    
                # 确保分数在有效范围内
                score = result.get('score', 0)
                if score < 0:
                    score = 0
                elif score > max_score:
                    score = max_score
                    
                # 四舍五入到最接近的0.5
                score = round(score * 2) / 2
                
                # 更新分数和反馈
                current_scores[index] = score
                current_feedback[index] = result.get('feedback', '')
                
            except (json.JSONDecodeError, ValueError) as e:
                current_app.logger.error(f"AI响应解析错误: {str(e)}, 响应: {ai_response}")
                # 跳过这个问题，继续处理下一个
                continue
                
        # 计算总分
        total_score = sum(filter(None, current_scores))
        # 四舍五入到最接近的0.5
        total_score = round(total_score * 2) / 2
                
        return jsonify({
            'status': 'success',
            'question_scores': current_scores,
            'question_feedback': current_feedback,
            'total_score': total_score
        })
            
    except Exception as e:
        current_app.logger.error(f"AI批量评分错误: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'AI批量评分失败: {str(e)}'}), 500

@learning_bp.route('/submissions/<int:submission_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_submission(submission_id):
    """获取单个提交记录"""
    # 验证提交是否存在
    submission = StudentAnswer.query.get(submission_id)
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    # 获取学生信息
    student = User.query.get(submission.student_id)
    student_name = student.full_name if student else f"Student {submission.student_id}"
    
    # 获取评估信息
    assessment = Assessment.query.get(submission.assessment_id)
    
    # 准备响应数据
    submission_data = submission.to_dict()
    submission_data['student_name'] = student_name
    
    # 如果有评估信息，添加到响应中
    if assessment:
        submission_data['assessment'] = {
            'id': assessment.id,
            'title': assessment.title,
            'description': assessment.description,
            'total_score': assessment.total_score,
            'questions': assessment.get_questions()
        }
    
    return jsonify(submission_data)

@learning_bp.route('/courses/<int:course_id>/assessments', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_course_assessments(course_id):
    """获取课程的所有评估"""
    # 检查课程是否存在
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    current_user = get_current_user_from_request()
    assessments = apply_assessment_visibility_filter(
        Assessment.query.filter_by(course_id=course_id),
        current_user
    ).all()
    
    # 准备响应数据
    assessments_data = []
    for assessment in assessments:
        assessment_dict = assessment.to_dict()
        # 添加提交次数信息
        assessment_dict['submission_count'] = StudentAnswer.query.filter_by(assessment_id=assessment.id).count()
        assessments_data.append(assessment_dict)
    
    return jsonify({
        'assessments': assessments_data,
        'total': len(assessments_data)
    })

# 删除课程章节
@learning_bp.route('/courses/<int:course_id>/chapters', methods=['DELETE'])
def delete_course_chapters(course_id):
    """删除课程章节"""
    current_app.logger.info(f"删除课程章节: 课程ID = {course_id}")
    
    # 查找课程
    course = Course.query.get(course_id)
    if not course:
        current_app.logger.error(f"课程不存在: ID = {course_id}")
        return jsonify({'error': 'Course not found'}), 404
    
    # 获取force参数
    force = request.args.get('force', 'false').lower() == 'true'
    
    # 章节文件路径
    chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters')
    course_chapters_folder = os.path.join(chapters_folder, str(course_id))
    chapters_file_path = os.path.join(course_chapters_folder, 'chapters.json')
    current_app.logger.info(f"章节文件路径: {chapters_file_path}")
    
    # 如果章节文件存在，则删除
    if os.path.exists(chapters_file_path):
        try:
            # 删除文件
            os.remove(chapters_file_path)
            current_app.logger.info(f"成功删除章节文件: {chapters_file_path}")
            return jsonify({
                'status': 'success',
                'message': 'Chapters deleted successfully'
            })
        except Exception as e:
            current_app.logger.error(f"删除章节文件失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'删除章节文件失败: {str(e)}'
            }), 500
    else:
        # 如果是强制删除，则返回成功
        if force:
            current_app.logger.info(f"章节文件不存在，但强制参数为true，返回成功")
            return jsonify({
                'status': 'success',
                'message': 'Chapters file does not exist, nothing to delete'
            })
        else:
            current_app.logger.warning(f"章节文件不存在: {chapters_file_path}")
            return jsonify({
                'status': 'warning',
                'message': 'Chapters file does not exist'
            }), 404

# 修改生成章节函数，使其能使用课程名称和描述作为输入
@learning_bp.route('/courses/<int:course_id>/generate-chapters', methods=['OPTIONS', 'POST'])
def generate_course_chapters(course_id):
    """使用AI生成课程章节"""
    current_app.logger.info(f"收到课程章节生成请求: 课程ID = {course_id}, 方法 = {request.method}")
    
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Cache-Control')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        current_app.logger.info("处理OPTIONS请求")
        return response
    
    # 查找课程
    course = Course.query.get(course_id)
    if not course:
        current_app.logger.error(f"课程不存在: ID = {course_id}")
        return jsonify({'error': 'Course not found'}), 404
    
    # 获取请求数据
    data = request.json or {}
    course_name = data.get('course_name') or course.name
    description = data.get('description') or course.description or ''
    
    current_app.logger.info(f"课程名称: {course_name}, 描述长度: {len(description)}")
    
    # 检查章节文件夹是否存在，不存在则创建
    chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters')
    os.makedirs(chapters_folder, exist_ok=True)
    current_app.logger.info(f"章节文件夹路径: {chapters_folder}")
    
    # 检查课程章节文件夹是否存在，不存在则创建
    course_chapters_folder = os.path.join(chapters_folder, str(course_id))
    os.makedirs(course_chapters_folder, exist_ok=True)
    current_app.logger.info(f"课程章节文件夹路径: {course_chapters_folder}")
    
    # 章节文件路径
    chapters_file_path = os.path.join(course_chapters_folder, 'chapters.json')
    current_app.logger.info(f"章节文件路径: {chapters_file_path}")
    
    try:
        current_app.logger.info(f"开始生成章节数据")
        
        # 根据课程名称和描述进行定制
        course_type = "通用"
        
        # 简单的关键词匹配，用于确定课程类型
        if any(keyword in course_name.lower() or (description and keyword in description.lower()) for keyword in ["python", "编程", "程序", "代码", "开发"]):
            course_type = "编程"
        elif any(keyword in course_name.lower() or (description and keyword in description.lower()) for keyword in ["math", "数学", "物理", "chemistry", "化学"]):
            course_type = "理科"
        elif any(keyword in course_name.lower() or (description and keyword in description.lower()) for keyword in ["历史", "文学", "哲学", "艺术", "音乐"]):
            course_type = "文科"
        elif any(keyword in course_name.lower() or (description and keyword in description.lower()) for keyword in ["人工智能", "机器学习", "神经网络", "深度学习", "ai"]):
            course_type = "人工智能"
        
        current_app.logger.info(f"检测到课程类型: {course_type}")
        
        # 根据课程类型选择不同的章节模板
        if course_type == "编程":
            # 编程类课程章节
            chapters_data = [
                {
                    "title": f"第一章：{course_name}基础入门",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "1.1 开发环境搭建",
                            "duration": 30,
                            "content": "学习如何配置开发环境，安装所需工具和库"
                        },
                        {
                            "title": "1.2 基本语法讲解",
                            "duration": 30,
                            "content": "详细讲解编程语言的基础语法和结构"
                        },
                        {
                            "title": "1.3 第一个程序实例",
                            "duration": 30,
                            "content": "编写并运行第一个简单程序，了解基本工作流程"
                        }
                    ]
                },
                {
                    "title": "第二章：数据类型与结构",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "2.1 基本数据类型",
                            "duration": 40,
                            "content": "学习语言中的基本数据类型及其操作方法"
                        },
                        {
                            "title": "2.2 复合数据结构",
                            "duration": 40,
                            "content": "掌握数组、列表、字典等复合数据结构的使用"
                        },
                        {
                            "title": "2.3 数据操作实践",
                            "duration": 40,
                            "content": "通过实例练习各种数据类型和结构的操作"
                        }
                    ]
                },
                {
                    "title": "第三章：流程控制",
                    "duration": 100,
                    "sections": [
                        {
                            "title": "3.1 条件语句",
                            "duration": 30,
                            "content": "学习if-else等条件语句的语法和应用场景"
                        },
                        {
                            "title": "3.2 循环结构",
                            "duration": 40,
                            "content": "掌握for、while等循环结构的使用方法"
                        },
                        {
                            "title": "3.3 控制流实例",
                            "duration": 30,
                            "content": "通过实际案例练习流程控制语句的应用"
                        }
                    ]
                },
                {
                    "title": "第四章：函数编程",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "4.1 函数定义与调用",
                            "duration": 30,
                            "content": "学习如何定义和调用函数，理解参数传递机制"
                        },
                        {
                            "title": "4.2 函数高级特性",
                            "duration": 40,
                            "content": "探讨匿名函数、闭包、装饰器等高级函数特性"
                        },
                        {
                            "title": "4.3 模块化与包管理",
                            "duration": 50,
                            "content": "了解如何组织代码为模块，以及使用包管理工具"
                        }
                    ]
                },
                {
                    "title": "第五章：面向对象编程",
                    "duration": 150,
                    "sections": [
                        {
                            "title": "5.1 类与对象基础",
                            "duration": 50,
                            "content": "理解面向对象的核心概念，学习类的定义和实例化"
                        },
                        {
                            "title": "5.2 继承与多态",
                            "duration": 50,
                            "content": "掌握继承、多态等面向对象高级特性"
                        },
                        {
                            "title": "5.3 设计模式入门",
                            "duration": 50,
                            "content": "了解常见设计模式及其在面向对象编程中的应用"
                        }
                    ]
                },
                {
                    "title": "第六章：文件与异常处理",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "6.1 文件读写操作",
                            "duration": 30,
                            "content": "学习如何进行文件的读写、创建和删除等基本操作"
                        },
                        {
                            "title": "6.2 异常处理机制",
                            "duration": 30,
                            "content": "掌握try-except异常处理语法和最佳实践"
                        },
                        {
                            "title": "6.3 日志记录技术",
                            "duration": 30,
                            "content": "了解如何使用日志模块记录程序运行状态"
                        }
                    ]
                },
                {
                    "title": "第七章：数据库交互",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "7.1 数据库基础",
                            "duration": 40,
                            "content": "了解关系型数据库和NoSQL数据库的基本概念"
                        },
                        {
                            "title": "7.2 SQL语句与ORM",
                            "duration": 40,
                            "content": "学习基本SQL语句和使用ORM框架简化数据库操作"
                        },
                        {
                            "title": "7.3 数据库应用开发",
                            "duration": 40,
                            "content": "实践数据库在实际应用中的集成和使用"
                        }
                    ]
                },
                {
                    "title": "第八章：项目实战",
                    "duration": 180,
                    "sections": [
                        {
                            "title": "8.1 需求分析与设计",
                            "duration": 60,
                            "content": "学习如何分析项目需求并进行系统设计"
                        },
                        {
                            "title": "8.2 项目开发实践",
                            "duration": 60,
                            "content": "按照设计文档实现项目功能，应用所学知识"
                        },
                        {
                            "title": "8.3 测试与部署",
                            "duration": 60,
                            "content": "掌握基本的测试方法和项目部署技术"
                        }
                    ]
                }
            ]
        elif course_type == "人工智能":
            # 人工智能课程章节
            chapters_data = [
                {
                    "title": "第一章：人工智能基础",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "1.1 人工智能概述与历史",
                            "duration": 30,
                            "content": "介绍人工智能的发展历程、关键里程碑和基本概念"
                        },
                        {
                            "title": "1.2 机器学习基础理论",
                            "duration": 30,
                            "content": "讲解机器学习的核心原理、类型和常见算法"
                        },
                        {
                            "title": "1.3 神经网络入门",
                            "duration": 30,
                            "content": "介绍神经网络的基本结构、工作原理和应用场景"
                        }
                    ]
                },
                {
                    "title": "第二章：数学基础",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "2.1 线性代数基础",
                            "duration": 40,
                            "content": "回顾AI所需的向量、矩阵运算和特征分解等知识"
                        },
                        {
                            "title": "2.2 概率与统计",
                            "duration": 40,
                            "content": "学习概率论、贝叶斯理论和假设检验等统计知识"
                        },
                        {
                            "title": "2.3 最优化方法",
                            "duration": 40,
                            "content": "了解梯度下降、牛顿法等常用优化算法"
                        }
                    ]
                },
                {
                    "title": "第三章：监督学习",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "3.1 线性回归与逻辑回归",
                            "duration": 40,
                            "content": "详细讲解回归模型的原理和实现方法"
                        },
                        {
                            "title": "3.2 决策树与随机森林",
                            "duration": 40,
                            "content": "学习基于树的模型及其集成方法"
                        },
                        {
                            "title": "3.3 支持向量机",
                            "duration": 40,
                            "content": "掌握SVM的数学原理和核技巧"
                        }
                    ]
                },
                {
                    "title": "第四章：深度学习基础",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "4.1 前馈神经网络",
                            "duration": 40,
                            "content": "学习多层感知器的结构、前向传播和反向传播算法"
                        },
                        {
                            "title": "4.2 深度网络训练技巧",
                            "duration": 40,
                            "content": "掌握正则化、批量归一化等提升模型性能的方法"
                        },
                        {
                            "title": "4.3 深度学习框架入门",
                            "duration": 40,
                            "content": "了解主流深度学习框架的基本使用方法"
                        }
                    ]
                },
                {
                    "title": "第五章：计算机视觉",
                    "duration": 150,
                    "sections": [
                        {
                            "title": "5.1 卷积神经网络(CNN)",
                            "duration": 50,
                            "content": "深入学习CNN的结构、原理和视觉应用"
                        },
                        {
                            "title": "5.2 图像分类与检测",
                            "duration": 50,
                            "content": "掌握目标检测、图像分类等基本视觉任务"
                        },
                        {
                            "title": "5.3 图像生成与风格迁移",
                            "duration": 50,
                            "content": "探索GAN和风格迁移等高级视觉生成技术"
                        }
                    ]
                },
                {
                    "title": "第六章：自然语言处理",
                    "duration": 150,
                    "sections": [
                        {
                            "title": "6.1 循环神经网络与LSTM",
                            "duration": 50,
                            "content": "学习RNN、LSTM等序列建模的基本网络结构"
                        },
                        {
                            "title": "6.2 注意力机制与Transformer",
                            "duration": 50,
                            "content": "深入研究Transformer架构及其工作原理"
                        },
                        {
                            "title": "6.3 大型语言模型",
                            "duration": 50,
                            "content": "了解BERT、GPT等预训练语言模型的特点"
                        }
                    ]
                },
                {
                    "title": "第七章：强化学习",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "7.1 马尔可夫决策过程",
                            "duration": 40,
                            "content": "了解强化学习的数学基础和理论框架"
                        },
                        {
                            "title": "7.2 基于价值的方法",
                            "duration": 40,
                            "content": "学习Q-learning、DQN等基于价值的强化学习算法"
                        },
                        {
                            "title": "7.3 策略梯度与Actor-Critic",
                            "duration": 40,
                            "content": "掌握基于策略的强化学习方法及其应用"
                        }
                    ]
                },
                {
                    "title": "第八章：AI伦理与实践",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "8.1 AI系统部署与优化",
                            "duration": 30,
                            "content": "学习将AI模型部署到生产环境并进行优化"
                        },
                        {
                            "title": "8.2 AI伦理与公平性",
                            "duration": 30,
                            "content": "探讨AI应用中的伦理问题、偏见与公平性"
                        },
                        {
                            "title": "8.3 AI前沿与未来展望",
                            "duration": 30,
                            "content": "了解AI领域最新研究进展和未来发展方向"
                        }
                    ]
                }
            ]
        else:
            # 通用课程章节
            chapters_data = [
                {
                    "title": f"第一章：{course_name}概述",
                    "duration": 60,
                    "sections": [
                        {
                            "title": "1.1 课程导引与学习目标",
                            "duration": 20,
                            "content": "介绍课程的总体框架、学习目标和预期收获"
                        },
                        {
                            "title": "1.2 核心概念预览",
                            "duration": 20,
                            "content": "概述课程中将要学习的关键概念和重要理论"
                        },
                        {
                            "title": "1.3 学习方法与资源",
                            "duration": 20,
                            "content": "分享有效的学习策略、方法和推荐的学习资源"
                        }
                    ]
                },
                {
                    "title": "第二章：学科基础知识",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "2.1 基本概念与术语",
                            "duration": 40,
                            "content": "系统介绍学科中的基础概念和专业术语"
                        },
                        {
                            "title": "2.2 理论框架与模型",
                            "duration": 40,
                            "content": "讲解该领域的主要理论框架和分析模型"
                        },
                        {
                            "title": "2.3 发展历史与脉络",
                            "duration": 40,
                            "content": "回顾学科的历史发展脉络和重要里程碑"
                        }
                    ]
                },
                {
                    "title": "第三章：核心原理讲解",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "3.1 基本原则与规律",
                            "duration": 40,
                            "content": "详细讲解学科中的基本原则和核心规律"
                        },
                        {
                            "title": "3.2 方法论与工作流程",
                            "duration": 40,
                            "content": "介绍该领域常用的研究方法和标准流程"
                        },
                        {
                            "title": "3.3 案例分析与应用",
                            "duration": 40,
                            "content": "通过案例分析加深对核心原理的理解"
                        }
                    ]
                },
                {
                    "title": "第四章：技术与工具应用",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "4.1 常用工具介绍",
                            "duration": 30,
                            "content": "介绍本领域常用的专业工具和技术平台"
                        },
                        {
                            "title": "4.2 技术操作实践",
                            "duration": 30,
                            "content": "通过实践学习各种技术的具体操作方法"
                        },
                        {
                            "title": "4.3 数据收集与分析",
                            "duration": 30,
                            "content": "学习相关数据的收集、处理和分析方法"
                        }
                    ]
                },
                {
                    "title": "第五章：专业技能培养",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "5.1 专业能力训练",
                            "duration": 40,
                            "content": "系统训练本领域所需的核心专业能力"
                        },
                        {
                            "title": "5.2 问题解决策略",
                            "duration": 40,
                            "content": "学习解决本领域典型问题的方法和策略"
                        },
                        {
                            "title": "5.3 实践项目指导",
                            "duration": 40,
                            "content": "通过实际项目练习应用所学知识和技能"
                        }
                    ]
                },
                {
                    "title": "第六章：行业应用与实践",
                    "duration": 120,
                    "sections": [
                        {
                            "title": "6.1 行业现状分析",
                            "duration": 40,
                            "content": "分析本学科在各行业中的应用现状和特点"
                        },
                        {
                            "title": "6.2 实际案例研究",
                            "duration": 40,
                            "content": "研究行业中的典型成功案例和失败教训"
                        },
                        {
                            "title": "6.3 创新应用探索",
                            "duration": 40,
                            "content": "探讨本学科知识在新兴领域的创新应用"
                        }
                    ]
                },
                {
                    "title": "第七章：前沿研究与发展",
                    "duration": 90,
                    "sections": [
                        {
                            "title": "7.1 学术前沿综述",
                            "duration": 30,
                            "content": "综述本领域当前的学术研究前沿和热点问题"
                        },
                        {
                            "title": "7.2 新技术与新方法",
                            "duration": 30,
                            "content": "介绍领域内新兴的技术手段和研究方法"
                        },
                        {
                            "title": "7.3 跨学科融合趋势",
                            "duration": 30,
                            "content": "探讨本学科与其他学科的交叉融合趋势"
                        }
                    ]
                },
                {
                    "title": "第八章：课程总结与展望",
                    "duration": 60,
                    "sections": [
                        {
                            "title": "8.1 知识体系回顾",
                            "duration": 20,
                            "content": "系统回顾课程所学的全部知识体系"
                        },
                        {
                            "title": "8.2 实践应用指导",
                            "duration": 20,
                            "content": "指导学生如何将所学知识应用到实际工作中"
                        },
                        {
                            "title": "8.3 未来学习路径",
                            "duration": 20,
                            "content": "建议进一步学习的方向和资源获取渠道"
                        }
                    ]
                }
            ]
        
        # 保存到文件
        current_app.logger.info(f"保存章节数据到文件")
        chapters_data = normalize_generated_chapters(chapters_data)

        with open(chapters_file_path, 'w', encoding='utf-8') as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=2)
        
        current_app.logger.info(f"章节生成成功，返回数据")
        return jsonify({
            'status': 'success',
            'message': 'Chapters generated successfully',
            'chapters': chapters_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Generate chapters error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'生成章节失败: {str(e)}'
        }), 500

@learning_bp.route('/courses/<int:course_id>/chapters/generate-from-material/preview', methods=['POST'])
def preview_generate_chapters_from_material_api(course_id):
    """预览根据课件资源生成的章节结果。"""
    data = request.json or {}
    material_id = data.get('material_id')
    source_type = str(data.get('source_type') or '').strip().lower()

    if material_id is None:
        return jsonify({'status': 'error', 'message': 'material_id 不能为空'}), 400

    try:
        material_id = int(material_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'material_id 必须为整数'}), 400

    course, material, error_response = validate_material_chapter_source(course_id, material_id, source_type)
    if error_response:
        return error_response

    try:
        existing_chapters = load_course_chapters(current_app.config['UPLOAD_FOLDER'], course_id)
        preview_result = preview_generate_chapters_from_material(
            course_name=course.name or material.title,
            course_id=course_id,
            source_type=source_type,
            material_title=material.title,
            material_path=get_absolute_material_path(material.file_path),
            upload_root=current_app.config['UPLOAD_FOLDER'],
            existing_chapters=existing_chapters,
        )
        generated_chapters = preview_result.get('generated_chapters')
        if isinstance(generated_chapters, list):
            preview_result['generated_chapters'] = [
                {
                    **chapter,
                    'source_material_id': material.id,
                    'source_material_title': material.title,
                    'source_type': source_type,
                }
                for chapter in generated_chapters
                if isinstance(chapter, dict)
            ]
        return jsonify(preview_result)
    except Exception as e:
        current_app.logger.exception('课件资源生成章节预览失败: course_id=%s material_id=%s', course_id, material_id)
        return jsonify({
            'status': 'error',
            'message': f'生成预览失败: {str(e)}'
        }), 500

@learning_bp.route('/courses/<int:course_id>/chapters/generate-from-material/apply', methods=['POST'])
def apply_generate_chapters_from_material_api(course_id):
    """应用根据课件资源生成的章节结果。"""
    data = request.json or {}
    material_id = data.get('material_id')
    source_type = str(data.get('source_type') or '').strip().lower()
    apply_mode = str(data.get('apply_mode') or '').strip()
    generated_chapters = data.get('generated_chapters')
    target_chapter_index = data.get('target_chapter_index')

    if material_id is None:
        return jsonify({'status': 'error', 'message': 'material_id 不能为空'}), 400
    if not isinstance(generated_chapters, list):
        return jsonify({'status': 'error', 'message': 'generated_chapters 必须为数组'}), 400

    try:
        material_id = int(material_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'material_id 必须为整数'}), 400

    if target_chapter_index is not None and target_chapter_index != '':
        try:
            target_chapter_index = int(target_chapter_index)
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'target_chapter_index 必须为整数'}), 400
    else:
        target_chapter_index = None

    _, _, error_response = validate_material_chapter_source(course_id, material_id, source_type)
    if error_response:
        return error_response

    try:
        updated_chapters = apply_generated_chapters(
            course_id=course_id,
            upload_root=current_app.config['UPLOAD_FOLDER'],
            source_type=source_type,
            apply_mode=apply_mode,
            generated_chapters=normalize_generated_chapters(generated_chapters),
            target_chapter_index=target_chapter_index,
        )
        return jsonify({
            'status': 'success',
            'message': '章节已更新',
            'chapters': updated_chapters,
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.exception('应用课件资源生成章节失败: course_id=%s material_id=%s', course_id, material_id)
        return jsonify({
            'status': 'error',
            'message': f'应用章节失败: {str(e)}'
        }), 500

# 获取课程章节
@learning_bp.route('/courses/<int:course_id>/chapters', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_course_chapters(course_id):
    """获取课程章节"""
    current_app.logger.info(f"获取课程章节: 课程ID = {course_id}")
    
    # 查找课程
    course = Course.query.get(course_id)
    if not course:
        current_app.logger.error(f"课程不存在: ID = {course_id}")
        return jsonify({'error': 'Course not found'}), 404
    
    # 章节文件路径
    chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters')
    course_chapters_folder = os.path.join(chapters_folder, str(course_id))
    chapters_file_path = os.path.join(course_chapters_folder, 'chapters.json')
    current_app.logger.info(f"章节文件路径: {chapters_file_path}")
    
    # 如果章节文件不存在，则返回空列表
    if not os.path.exists(chapters_file_path):
        current_app.logger.info(f"章节文件不存在，返回空列表")
        return jsonify({
            'status': 'success',
            'chapters': []
        })
    
    # 读取章节文件
    try:
        current_app.logger.info(f"读取章节文件")
        with open(chapters_file_path, 'r', encoding='utf-8') as f:
            chapters_data = normalize_generated_chapters(json.load(f))
        
        current_app.logger.info(f"返回章节数据: {len(chapters_data)} 个章节")
        return jsonify({
            'status': 'success',
            'chapters': chapters_data
        })
    except Exception as e:
        current_app.logger.error(f"Get chapters error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取章节失败: {str(e)}'
        }), 500

# 保存课程章节
@learning_bp.route('/courses/<int:course_id>/chapters', methods=['POST'])
def save_course_chapters(course_id):
    """保存课程章节"""
    current_app.logger.info(f"保存课程章节: 课程ID = {course_id}")
    
    # 查找课程
    course = Course.query.get(course_id)
    if not course:
        current_app.logger.error(f"课程不存在: ID = {course_id}")
        return jsonify({'error': 'Course not found'}), 404
    
    # 获取请求数据
    data = request.json
    if not data or 'chapters' not in data:
        current_app.logger.error(f"请求数据无效，缺少chapters字段")
        return jsonify({'error': 'Invalid request data'}), 400
    
    # 验证章节数据
    chapters = data['chapters']
    if not isinstance(chapters, list):
        current_app.logger.error(f"章节数据不是有效的列表")
        return jsonify({'error': 'Chapters must be a list'}), 400
    chapters = normalize_generated_chapters(chapters)
    
    # 检查章节文件夹是否存在，不存在则创建
    chapters_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chapters')
    os.makedirs(chapters_folder, exist_ok=True)
    
    # 检查课程章节文件夹是否存在，不存在则创建
    course_chapters_folder = os.path.join(chapters_folder, str(course_id))
    os.makedirs(course_chapters_folder, exist_ok=True)
    
    # 章节文件路径
    chapters_file_path = os.path.join(course_chapters_folder, 'chapters.json')
    
    try:
        # 保存章节到文件
        with open(chapters_file_path, 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        
        current_app.logger.info(f"章节保存成功: 课程ID = {course_id}, 章节数量 = {len(chapters)}")
        return jsonify({
            'status': 'success',
            'message': 'Chapters saved successfully'
        })
    except Exception as e:
        current_app.logger.error(f"保存章节失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'保存章节失败: {str(e)}'
        }), 500

# 测试API端点
@learning_bp.route('/test-api', methods=['GET', 'POST', 'OPTIONS'])
def test_api():
    """测试API端点"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
    
    return jsonify({
        'status': 'success',
        'message': 'API测试成功',
        'method': request.method
    })

def generate_assessment_with_ai(
    course_name,
    course_description,
    extra_info='',
    assessment_type='quiz',
    difficulty='medium',
    course_id=None,
    chapter_id=None,
    chapter_title='',
    status_callback=None,
):
    """使用AI生成评估内容"""
    load_dotenv()

    api_key, api_base, preferred_model = get_api_config()
    model_candidates = get_model_candidates('text', preferred=preferred_model)

    if not api_key:
        raise ValueError("API密钥未配置，请在环境变量中设置LLM_API_KEY或OPENAI_API_KEY")

    current_app.logger.info(f"使用模型候选 {model_candidates} 生成评估内容")

    chapter_context = {}
    if course_id and chapter_id:
        try:
            chapter_context = build_chapter_reference_context(
                course_id=course_id,
                chapter_id=chapter_id,
                fallback_title=chapter_title,
                api_key=api_key,
                api_base=api_base,
                status_callback=status_callback,
            )
        except Exception as exc:
            current_app.logger.warning('构建章节参考上下文失败: course_id=%s chapter_id=%s error=%s', course_id, chapter_id, exc)
            chapter_context = {}

    question_count = 10
    if assessment_type == "quiz":
        question_count = 10
    elif assessment_type == "exam":
        question_count = 20
    elif assessment_type == "homework":
        question_count = 8

    if callable(status_callback):
        status_callback('preparing_prompt', '正在整理课程信息、章节与出题要求...', 32)

    chapter_prompt_lines = []
    effective_chapter_title = str(chapter_context.get('chapter_title') or chapter_title or '').strip()
    if effective_chapter_title:
        chapter_prompt_lines.append(f'选定章节: {effective_chapter_title}')

    chapter_outline = str(chapter_context.get('chapter_outline') or '').strip()
    if chapter_outline:
        chapter_prompt_lines.append('章节结构摘要:')
        chapter_prompt_lines.append(chapter_outline)

    page_range_label = str(chapter_context.get('page_range_label') or '').strip()
    material_title = str(chapter_context.get('material_title') or '').strip()
    reference_excerpt = str(chapter_context.get('reference_excerpt') or '').strip()
    reference_note = str(chapter_context.get('reference_note') or '').strip()

    if reference_excerpt:
        chapter_prompt_lines.append(
            f'课件参考来源: {material_title or "未命名课件"}'
            + (f'，对应范围: {page_range_label}' if page_range_label else '')
        )
        chapter_prompt_lines.append('以下内容是从课件对应页码自动提取的文本，请优先依据这些内容生成题目：')
        chapter_prompt_lines.append(reference_excerpt)
    elif reference_note:
        chapter_prompt_lines.append(f'课件参考说明: {reference_note}')

    chapter_prompt_block = '\n'.join(chapter_prompt_lines).strip()
    chapter_prompt_section = f"章节与课件参考:\n{chapter_prompt_block}" if chapter_prompt_block else ''

    prompt = f"""
    请根据以下课程信息生成一个完整的{assessment_type}（{question_count}题左右）：
    
    课程名称: {course_name}
    课程描述: {course_description}
    难度级别: {difficulty}
    额外要求: {extra_info}
    {chapter_prompt_section}
    
    请按照以下JSON格式返回评估内容，确保格式正确：
    {{
      "title": "评估标题",
      "description": "评估描述",
      "type": "{assessment_type}",
      "total_score": 100,
      "sections": [
        {{
          "type": "multiple_choice",
          "description": "选择题部分",
          "score_per_question": 分数,
          "questions": [
            {{
              "id": 1,
              "stem": "题干内容",
              "type": "multiple_choice",
              "score": 分数,
              "difficulty": "{difficulty}",
              "options": ["A. 选项内容", "B. 选项内容", "C. 选项内容", "D. 选项内容"],
              "answer": "C",
              "explanation": "答案解析"
            }}
            // 更多题目...
          ]
        }},
        // 可以有多个sections，如multiple_choice, fill_in_blank, short_answer等
      ]
    }}
    
    注意：
    1. 请确保生成的题目与课程内容相关，并具有适当的难度级别
    2. 选择题的选项应该使用A、B、C、D等标注，答案也要用对应的字母
    3. 每种题型的分值合理分配，总分为100分
    4. 务必确保JSON格式正确，可以直接被解析
    5. 对于选择题，answer是选项的字母（如"A"、"B"等）
    6. 对于填空题，answer可以是字符串或字符串数组（多个空）
    7. 对于简答题和论述题，提供reference_answer参考答案
    8. 根据课程内容生成真实、准确、有教育意义的题目
    9. 如果提供了章节与课件参考，请优先围绕该章节内容出题，不要脱离参考材料随意扩展
    10. 题目表述、答案和解析应尽量引用课程/章节中的真实知识点，避免编造与课程无关的事实
    
    请只返回JSON格式的评估内容，不要添加任何额外的解释或说明。
    """

    payload = {
        'messages': [
            {
                "role": "system",
                "content": "你是一个专业的教育内容创建者，擅长根据课程信息生成高质量的测验和考试题目。请稳定输出可解析 JSON。"
            },
            {"role": "user", "content": prompt}
        ],
        'temperature': 0.4,
        'max_tokens': 3200,
        'stream': False,
    }

    current_app.logger.info("发送AI请求生成评估内容")

    try:
        if callable(status_callback):
            status_callback('calling_model', '正在调用模型生成题目...', 42)

        response_json, used_model = post_chat_completion_with_model_fallback(
            api_key=api_key,
            api_base=api_base,
            payload=payload,
            model_candidates=model_candidates,
            timeout=AI_ASSESSMENT_MODEL_TIMEOUT_SECONDS,
        )

        if callable(status_callback):
            status_callback('parsing_result', f'模型已返回结果，正在解析内容（{used_model}）...', 82)

        ai_response = extract_message_content(response_json).strip()
        current_app.logger.info(f"AI响应内容长度: {len(ai_response)}")

        try:
            assessment_data = extract_json_object_from_text(ai_response)
            if not assessment_data:
                assessment_data = json.loads(ai_response)

            if not isinstance(assessment_data, dict):
                raise ValueError('AI 返回内容不是有效的评估对象')

            assessment_data.setdefault('type', assessment_type)
            assessment_data.setdefault('description', f'{course_name}自动生成评估')
            assessment_data['_generated_model'] = used_model
            current_app.logger.info("成功解析AI生成的评估JSON")
            return assessment_data
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON解析错误: {str(e)}")
            raise ValueError(f"无法解析AI生成的内容为有效JSON: {str(e)}")

    except Exception as e:
        current_app.logger.error(f"调用AI服务失败: {str(e)}")
        raise Exception(f"调用AI服务失败: {str(e)}")

@learning_bp.route('/assessments/ai-generate/<request_id>', methods=['GET', 'OPTIONS'])
@api_error_handler
def get_ai_assessment_status(request_id):
    """获取AI生成评估的状态和结果"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    current_app.logger.info(f"查询AI生成评估状态: request_id={request_id}")
    
    # 查找对应的文件
    ai_assessments_dir = os.path.join(current_app.root_path, 'uploads', 'ai_assessments')
    file_path = os.path.join(ai_assessments_dir, f"assessment_{request_id}.json")
    
    if not os.path.exists(file_path):
        current_app.logger.error(f"找不到评估文件: {file_path}")
        response = jsonify({
            'status': 'error',
            'message': '找不到指定的评估请求',
            'request_id': request_id
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 判断是否已完成
        if 'assessment' in data:
            current_app.logger.info(f"评估已生成完成: request_id={request_id}")
            response = jsonify(data)
        elif 'error' in data:
            current_app.logger.info(f"评估生成失败: request_id={request_id}")
            response = jsonify(data)
        else:
            start_time = datetime.fromisoformat(data.get('created_at') or data.get('timestamp', datetime.now().isoformat()))
            current_time = datetime.now()
            elapsed_seconds = (current_time - start_time).total_seconds()

            heartbeat_raw = data.get('heartbeat_at') or data.get('updated_at') or data.get('timestamp')
            heartbeat_time = datetime.fromisoformat(heartbeat_raw) if heartbeat_raw else start_time
            stale_seconds = (current_time - heartbeat_time).total_seconds()

            if stale_seconds > AI_ASSESSMENT_STALE_SECONDS:
                current_app.logger.error(
                    f"评估生成任务疑似卡死: request_id={request_id}, stale={stale_seconds:.1f}秒"
                )
                response = jsonify({
                    'status': 'error',
                    'message': '评估生成任务超时或已中断，请重试',
                    'error': '后台任务长时间未更新状态，可能已超时或被中断',
                    'elapsed_seconds': int(elapsed_seconds),
                    'request_id': request_id
                })
            else:
                progress_info = data.get('progress_message') or '评估正在生成中，请稍后再查询'
                progress_percent = int(data.get('progress_percent') or 0)

                current_app.logger.info(
                    f"评估正在生成中: request_id={request_id}, elapsed={elapsed_seconds:.1f}秒, stage={data.get('progress_stage')}"
                )
                response = jsonify({
                    'status': 'processing',
                    'message': '评估正在生成中，请稍后再查询',
                    'progress': progress_info,
                    'progress_percent': progress_percent,
                    'progress_stage': data.get('progress_stage') or 'processing',
                    'elapsed_seconds': int(elapsed_seconds),
                    'request_id': request_id
                })
            
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Content-Type', 'application/json')
        return response
    
    except Exception as e:
        current_app.logger.error(f"读取评估文件失败: {str(e)}")
        response = jsonify({
            'status': 'error',
            'message': f'读取评估状态失败: {str(e)}',
            'request_id': request_id
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@learning_bp.route('/assessments/ai-file/<request_id>', methods=['GET', 'OPTIONS'])
@api_error_handler
def get_ai_assessment_file(request_id):
    """直接获取AI生成评估文件的内容"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    current_app.logger.info(f"直接请求AI评估文件内容: request_id={request_id}")
    
    # 查找对应的文件
    ai_assessments_dir = os.path.join(current_app.root_path, 'uploads', 'ai_assessments')
    file_path = os.path.join(ai_assessments_dir, f"assessment_{request_id}.json")
    
    if not os.path.exists(file_path):
        current_app.logger.error(f"找不到评估文件: {file_path}")
        response = jsonify({
            'status': 'error',
            'message': '找不到指定的评估文件',
            'request_id': request_id
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 直接返回文件内容，无论处理状态如何
        current_app.logger.info(f"成功读取评估文件: request_id={request_id}")
        response = jsonify(data)
        
        # 添加CORS头
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Content-Type', 'application/json')
        return response
    
    except Exception as e:
        current_app.logger.error(f"读取评估文件失败: {str(e)}")
        response = jsonify({
            'status': 'error',
            'message': f'读取评估文件失败: {str(e)}',
            'request_id': request_id
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@learning_bp.route('/assessments/<int:assessment_id>/submissions', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_assessment_submissions(assessment_id):
    """获取评估的所有提交"""
    current_app.logger.info(f"获取评估提交: assessment_id={assessment_id}, args={request.args}")
    
    # 验证评估是否存在
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        current_app.logger.error(f"评估不存在: assessment_id={assessment_id}")
        return jsonify({'error': 'Assessment not found'}), 404
    
    # 获取查询参数
    student_id = request.args.get('student_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    graded = request.args.get('graded')
    
    current_app.logger.info(f"查询参数: student_id={student_id}, page={page}, per_page={per_page}, graded={graded}")
    
    # 构建查询
    query = StudentAnswer.query.filter_by(assessment_id=assessment_id)
    
    if student_id:
        current_app.logger.info(f"按学生ID过滤: student_id={student_id}")
        query = query.filter_by(student_id=student_id)
    
    # 根据评分状态过滤
    if graded == 'true':
        current_app.logger.info("只查询已评分的提交")
        query = query.filter(StudentAnswer.graded_at != None)
    elif graded == 'false':
        current_app.logger.info("只查询未评分的提交")
        query = query.filter(StudentAnswer.graded_at == None)
    
    try:
        # 执行分页查询
        submissions_pagination = query.paginate(page=page, per_page=per_page)
        
        current_app.logger.info(f"找到 {submissions_pagination.total} 条提交记录")
        
        # 准备响应数据
        submissions_data = []
        for submission in submissions_pagination.items:
            submission_dict = submission.to_dict()
            
            # 添加学生信息
            student = User.query.get(submission.student_id)
            if student:
                submission_dict['student_name'] = student.full_name
                submission_dict['student_username'] = student.username
                current_app.logger.info(f"添加学生信息: student_id={submission.student_id}, name={student.full_name}")
            
            submissions_data.append(submission_dict)
        
        response_data = {
            'submissions': submissions_data,
            'total': submissions_pagination.total,
            'pages': submissions_pagination.pages,
            'current_page': page
        }
        
        current_app.logger.info(f"返回 {len(submissions_data)} 条提交记录")
        
        # 添加CORS头
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        
        return response
    except Exception as e:
        current_app.logger.error(f"获取评估提交失败: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        
        # 添加CORS头
        response = jsonify({
            'error': f'Failed to get submissions: {str(e)}',
            'submissions': []
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        
        return response, 500

@learning_bp.route('/students/<int:student_id>/submissions', methods=['GET', 'OPTIONS'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_student_submissions(student_id):
    """获取学生的所有提交"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
        
    # 记录请求信息
    current_app.logger.info(f"获取学生提交记录: student_id={student_id}, args={request.args}")
    
    # 验证学生是否存在
    student = User.query.get(student_id)
    if not student:
        current_app.logger.warning(f"学生不存在: student_id={student_id}")
        response = jsonify({'error': 'Student not found'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404
    
    # 获取查询参数
    assessment_id = request.args.get('assessment_id', type=int)
    course_id = request.args.get('course_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    graded = request.args.get('graded')
    
    current_app.logger.info(f"查询参数: assessment_id={assessment_id}, course_id={course_id}, page={page}, per_page={per_page}, graded={graded}")
    
    # 构建查询
    query = StudentAnswer.query.filter_by(student_id=student_id)
    
    if assessment_id:
        current_app.logger.info(f"按评估ID过滤: assessment_id={assessment_id}")
        query = query.filter_by(assessment_id=assessment_id)
    
    if course_id:
        # 需要联表查询
        current_app.logger.info(f"按课程ID过滤: course_id={course_id}")
        query = query.join(Assessment).filter(Assessment.course_id == course_id)
    
    # 根据评分状态过滤
    if graded == 'true':
        current_app.logger.info("只查询已评分的提交")
        query = query.filter(StudentAnswer.graded_at != None)
    elif graded == 'false':
        current_app.logger.info("只查询未评分的提交")
        query = query.filter(StudentAnswer.graded_at == None)
    
    # 按提交时间降序排序
    query = query.order_by(StudentAnswer.submitted_at.desc())
    
    try:
        # 执行分页查询
        submissions_pagination = query.paginate(page=page, per_page=per_page)
        
        current_app.logger.info(f"找到 {submissions_pagination.total} 条提交记录")
        
        # 准备响应数据
        submissions_data = []
        for submission in submissions_pagination.items:
            submission_dict = submission.to_dict()
            
            # 添加评估信息
            assessment = Assessment.query.get(submission.assessment_id)
            if assessment:
                submission_dict['assessment_title'] = assessment.title
                submission_dict['assessment_total_score'] = assessment.total_score
            
            submissions_data.append(submission_dict)
        
        response = jsonify({
            'submissions': submissions_data,
            'total': submissions_pagination.total,
            'pages': submissions_pagination.pages,
            'current_page': page
        })
    except Exception as e:
        current_app.logger.error(f"获取学生提交记录失败: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        response = jsonify({
            'error': f'Failed to get submissions: {str(e)}',
            'submissions': []
        })
    
    # 添加CORS头
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

@learning_bp.route('/assessments/<int:assessment_id>/submission-count', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_assessment_submission_count(assessment_id):
    """获取评估的提交数量"""
    # 验证评估是否存在
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'error': 'Assessment not found'}), 404
    
    # 计算提交数量
    count = StudentAnswer.query.filter_by(assessment_id=assessment_id).count()
    
    # 获取已评分和未评分的数量
    graded_count = StudentAnswer.query.filter_by(assessment_id=assessment_id).filter(StudentAnswer.graded_at != None).count()
    ungraded_count = count - graded_count
    
    # 返回数量信息
    response = jsonify({
        'count': count,
        'graded_count': graded_count,
        'ungraded_count': ungraded_count,
        'assessment_id': assessment_id
    })
    
    # 添加CORS头
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    return response

@learning_bp.route('/analytics/student/<int:student_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
def get_student_analytics(student_id):
    """获取单个学生的学习分析数据"""
    try:
        student = User.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        response_payload = _apply_demo_student_snapshot(student, _build_student_analytics_payload(student))
        return jsonify(response_payload)
    except Exception as e:
        current_app.logger.error(f"获取学生学习分析数据失败: {str(e)}")
        return jsonify({'error': f'获取学习分析数据失败: {str(e)}'}), 500

@learning_bp.route('/ai/learning-analysis', methods=['POST'])
def get_student_ai_learning_analysis():
    """基于学生学习分析结果生成动态学习建议"""
    try:
        data = request.get_json() or {}
        student_id = data.get('studentId')
        course_id = data.get('courseId')

        if not student_id:
            return jsonify({'error': 'studentId is required'}), 400

        student = User.query.get(int(student_id))
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        analytics_payload = _apply_demo_student_snapshot(student, _build_student_analytics_payload(student))
        analysis_payload = _build_student_ai_analysis(student, analytics_payload, course_id=course_id)
        return jsonify(analysis_payload)
    except Exception as e:
        current_app.logger.error(f"生成AI学习建议失败: {str(e)}")
        return jsonify({'error': f'生成学习建议失败: {str(e)}'}), 500

@learning_bp.route('/analytics/course/<int:course_id>', methods=['GET'])
# @jwt_required()  # 暂时禁用JWT认证要求
@api_error_handler
def get_course_analytics(course_id):
    """获取课程的整体学习分析数据"""
    try:
        current_app.logger.info(f"获取课程学情分析数据: 课程ID = {course_id}")
        
        # 检查课程是否存在
        course = Course.query.get(course_id)
        if not course:
            current_app.logger.error(f"课程不存在: ID = {course_id}")
            return jsonify({'error': 'Course not found'}), 404
            
        # 课程学情统计需要同时覆盖:
        # 1. 课程直接关联的学生
        # 2. 已发布评估所覆盖班级中的学生
        published_assessments = Assessment.query.filter_by(
            course_id=course_id,
            is_published=True
        ).all()
        published_assessment_ids = [assessment.id for assessment in published_assessments]

        student_map = {}

        for student in (course.students if hasattr(course, 'students') else []):
            student_map[student.id] = student

        published_class_ids = {
            teacher_class.id
            for assessment in published_assessments
            for teacher_class in assessment.published_classes
        }
        if published_class_ids:
            published_classes = TeacherClass.query.filter(TeacherClass.id.in_(published_class_ids)).all()
            for teacher_class in published_classes:
                for student in teacher_class.students:
                    student_map[student.id] = student

        students = list(student_map.values())
        current_app.logger.info(
            "课程学生数量: direct=%s published_class=%s merged=%s",
            len(course.students if hasattr(course, 'students') else []),
            len(published_class_ids),
            len(students),
        )

        # 学生完成情况统计
        total_students = len(students)
        completed_students = 0
        in_progress_students = 0
        not_started_students = 0
        
        # 学生进度数据
        student_progress = []

        student_published_assessment_ids = {}
        if published_assessment_ids and students:
            published_visibility_rows = db.session.query(
                assessment_publish_classes.c.assessment_id,
                teacher_class_students.c.student_id,
            ).join(
                teacher_class_students,
                teacher_class_students.c.class_id == assessment_publish_classes.c.class_id,
            ).filter(
                assessment_publish_classes.c.assessment_id.in_(published_assessment_ids),
                teacher_class_students.c.student_id.in_([student.id for student in students]),
            ).all()

            for assessment_id, student_id in published_visibility_rows:
                student_published_assessment_ids.setdefault(student_id, set()).add(assessment_id)
        
        for student in students:
            try:
                visible_assessment_ids = student_published_assessment_ids.get(student.id, set())

                if visible_assessment_ids:
                    submitted_assessment_ids = {
                        assessment_id
                        for (assessment_id,) in db.session.query(StudentAnswer.assessment_id).filter(
                            StudentAnswer.student_id == student.id,
                            StudentAnswer.assessment_id.in_(list(visible_assessment_ids))
                        ).distinct().all()
                    }
                    visible_count = len(visible_assessment_ids)
                    submitted_count = len(submitted_assessment_ids)
                    progress = int((submitted_count / visible_count) * 100) if visible_count else 0

                    if submitted_count == 0:
                        not_started_students += 1
                    elif submitted_count >= visible_count:
                        completed_students += 1
                    else:
                        in_progress_students += 1
                else:
                    # 没有已发布评估时，回退到课程学习记录口径
                    records = LearningRecord.query.filter_by(
                        student_id=student.id,
                        course_id=course_id
                    ).all()

                    if not records:
                        not_started_students += 1
                        progress = 0
                    else:
                        materials_count = db.session.query(Material).filter_by(course_id=course_id).count()
                        if materials_count == 0:
                            materials_count = 1

                        viewed_materials = len(set([r.activity_detail for r in records if r.activity_type == 'view_material']))
                        progress = min(100, int((viewed_materials / materials_count) * 100))

                        if progress == 100:
                            completed_students += 1
                        else:
                            in_progress_students += 1
                
                # 计算学习时间
                learning_time = db.session.query(func.sum(LearningRecord.duration)).filter(
                    LearningRecord.student_id == student.id,
                    LearningRecord.course_id == course_id
                ).scalar() or 0
                
                # 转换为小时
                learning_time = round(learning_time / 3600, 1)
                
                student_progress.append({
                    "id": student.id,
                    "name": student.full_name if hasattr(student, 'full_name') else f"学生{student.id}",
                    "progress": progress,
                    "learningTime": learning_time
                })
            except Exception as e:
                current_app.logger.error(f"处理学生数据时出错: 学生ID = {student.id}, 错误 = {str(e)}")
                # 继续处理下一个学生
        
        # 按进度排序
        student_progress.sort(key=lambda x: x["progress"], reverse=True)
        
        # 获取评估数据
        assessment_data = []
        try:
            # 直接查询数据库获取评估数据
            current_app.logger.info("使用直接查询获取评估数据")
            assessments = Assessment.query.filter_by(course_id=course_id).all()
            current_app.logger.info(f"课程评估数量: {len(assessments)}")
            
            for assessment in assessments:
                try:
                    # 提交数量按已提交学生数去重，避免一人多题/多次记录导致放大
                    submissions_count = db.session.query(StudentAnswer.student_id).filter_by(
                        assessment_id=assessment.id
                    ).distinct().count()
                    
                    # 获取平均分 - 使用StudentAnswer而不是AssessmentSubmission
                    avg_score_result = db.session.query(func.avg(StudentAnswer.score)).filter(
                        StudentAnswer.assessment_id == assessment.id,
                        StudentAnswer.score != None
                    ).scalar()
                    
                    avg_score = 0
                    if avg_score_result is not None:
                        avg_score = round(float(avg_score_result), 1)
                    
                    assessment_data.append({
                        "id": assessment.id,
                        "title": assessment.title,
                        "submissionsCount": submissions_count,
                        "averageScore": avg_score
                    })
                    current_app.logger.info(f"添加评估: ID={assessment.id}, 标题={assessment.title}, 提交数={submissions_count}, 平均分={avg_score}")
                except Exception as e:
                    current_app.logger.error(f"处理评估数据时出错: 评估ID = {assessment.id}, 错误 = {str(e)}")
                    # 继续处理下一个评估
        except Exception as e:
            current_app.logger.error(f"获取评估列表时出错: {str(e)}")
        
        # 知识点掌握情况：维度标签由大模型根据课程名称动态提取，数值先沿用当前展示策略
        knowledge_labels = generate_course_radar_keywords(course.name, getattr(course, 'description', '') or '')
        default_scores = [78, 62, 68, 85, 55, 70]
        knowledge_points = [
            {"label": label, "value": default_scores[index % len(default_scores)]}
            for index, label in enumerate(knowledge_labels[:6])
        ]
        
        response_data = {
            "totalStudents": total_students,
            "completedStudents": completed_students,
            "inProgressStudents": in_progress_students,
            "notStartedStudents": not_started_students,
            "studentProgress": student_progress,
            "assessments": assessment_data,
            "knowledgePoints": knowledge_points
        }
        
        current_app.logger.info(f"成功获取课程学情分析数据: 课程ID = {course_id}, 评估数量: {len(assessment_data)}")
        return jsonify(response_data)
    except Exception as e:
        current_app.logger.error(f"获取课程学习分析数据失败: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'获取学习分析数据失败: {str(e)}'}), 500

