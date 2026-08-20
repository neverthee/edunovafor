import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from werkzeug.utils import secure_filename

from backend.extensions import db
from backend.models.material import Material


GAME_HTML_FILENAME_PREFIX = "lesson-game"
SORTABLE_VENDOR_PATH = os.path.join(os.path.dirname(__file__), "vendor", "Sortable.min.js")


def build_output_path(upload_root: str, course_id: int, topic: str) -> str:
    materials_dir = os.path.join(upload_root, "materials", str(course_id))
    os.makedirs(materials_dir, exist_ok=True)
    base_name = secure_filename(topic) or GAME_HTML_FILENAME_PREFIX
    filename = f"{base_name}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.html"
    return os.path.join(materials_dir, filename)


def render_game_html(game_pack: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    html = _build_game_html(game_pack)
    with open(output_path, "w", encoding="utf-8") as file_obj:
        file_obj.write(html)

    stages = game_pack.get("stages") if isinstance(game_pack.get("stages"), list) else []
    question_count = sum(
        len(stage.get("questions", []))
        for stage in stages
        if isinstance(stage, dict) and isinstance(stage.get("questions"), list)
    )
    return {
        "stage_count": len([stage for stage in stages if isinstance(stage, dict)]),
        "question_count": question_count,
    }


def persist_generated_material(
    course_id: int,
    course_name: str,
    topic: str,
    output_path: str,
    stats: Dict[str, Any],
) -> Material:
    file_hash = _calculate_file_hash(output_path)
    existing = Material.query.filter_by(course_id=course_id, file_hash=file_hash).first()
    if existing and existing.file_path:
        existing_abs_path = _material_upload_to_abs_path(existing.file_path)
        if existing_abs_path and os.path.exists(existing_abs_path):
            if os.path.abspath(existing_abs_path) != os.path.abspath(output_path) and os.path.exists(output_path):
                os.remove(output_path)
            return existing

    filename = os.path.basename(output_path)
    relative_upload_path = f"/uploads/materials/{course_id}/{filename}"
    content = (
        f"Generated lesson game HTML | course={course_name} | topic={topic} | "
        f"stages={int(stats.get('stage_count') or 0)} | questions={int(stats.get('question_count') or 0)}"
    )

    if existing:
        existing.title = filename
        existing.material_type = "HTML"
        existing.file_path = relative_upload_path
        existing.content = content
        db.session.commit()
        return existing

    material = Material(
        title=filename,
        material_type="HTML",
        file_path=relative_upload_path,
        file_hash=file_hash,
        content=content,
        course_id=course_id,
    )
    db.session.add(material)
    db.session.commit()
    return material


def _calculate_file_hash(file_path: str) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with open(file_path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(4096), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def _material_upload_to_abs_path(file_path: str) -> Optional[str]:
    if not isinstance(file_path, str) or not file_path:
        return None
    project_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_backend_dir, file_path.lstrip("/"))


def _escape_html(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _load_sortable_vendor_script() -> str:
    try:
        with open(SORTABLE_VENDOR_PATH, "r", encoding="utf-8") as file_obj:
            return file_obj.read().replace("</script>", "<\\/script>")
    except Exception:
        return ""


def _build_game_html(game_pack: Dict[str, Any]) -> str:
    meta = game_pack.get("meta") if isinstance(game_pack.get("meta"), dict) else {}
    theme = game_pack.get("theme_config") if isinstance(game_pack.get("theme_config"), dict) else {}
    root_title = _escape_html(str(meta.get("title") or "课堂闯关小游戏").strip() or "课堂闯关小游戏")
    data_json = json.dumps(game_pack, ensure_ascii=False)
    theme_name = _escape_html(str(theme.get("name") or "clean").strip() or "clean")
    sortable_vendor_script = _load_sortable_vendor_script()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>{root_title}</title>
  <style>
    :root {{
      --bg: #f4f4f5;
      --surface: #ffffff;
      --primary: #09090b;
      --primary-hover: #27272a;
      --primary-soft: #f4f4f5;
      --accent: #4f46e5;
      --accent-soft: #e0e7ff;
      --success: #10b981;
      --success-soft: #d1fae5;
      --danger: #ef4444;
      --danger-soft: #fee2e2;
      --text-main: #09090b;
      --text-muted: #71717a;
      --border: #e4e4e7;
      --radius-lg: 24px;
      --radius-md: 16px;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
      --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
      --font: 'Inter', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
    body {{
      margin: 0;
      font-family: var(--font);
      background-color: var(--bg);
      color: var(--text-main);
      line-height: 1.6;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    body.ordering-drag-active,
    body.ordering-drag-active * {{
      user-select: none !important;
      -webkit-user-select: none !important;
      -moz-user-select: none !important;
      -ms-user-select: none !important;
      -webkit-touch-callout: none !important;
      cursor: grabbing !important;
    }}
    .container {{
      width: 100%;
      max-width: 760px;
      margin: 0 auto;
    }}
    
    .hero {{
      text-align: center;
      margin-bottom: 24px;
    }}
    .hero h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin: 0 0 4px;
      color: var(--text-muted);
    }}
    .hero p {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin: 0;
    }}
    
    .panel {{
      background: var(--surface);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      padding: 40px;
      border: 1px solid rgba(228, 228, 231, 0.5);
      position: relative;
    }}
    
    .hud {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .hud-stats {{
      display: flex;
      gap: 20px;
    }}
    .hud-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .hud-label {{
      font-size: 0.85rem;
      color: var(--text-muted);
      font-weight: 500;
    }}
    .hud-value {{
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-main);
      font-variant-numeric: tabular-nums;
    }}
    
    .progress-container {{
      height: 4px;
      background: var(--border);
      border-radius: 999px;
      margin-bottom: 40px;
      overflow: hidden;
    }}
    .progress-bar {{
      height: 100%;
      background: var(--primary);
      width: 0%;
      border-radius: 999px;
      transition: width 0.4s ease-out;
    }}

    .question-stem {{
      margin-bottom: 32px;
    }}
    .question-text {{
      font-size: 1.35rem;
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.5;
      margin-bottom: 16px;
    }}
    .question-tip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
    }}

    /* Matching Game */
    .matching-toolbar {{
      display: flex;
      justify-content: flex-end;
      margin-bottom: 12px;
    }}
    .matching-container {{
      display: flex;
      justify-content: space-between;
      position: relative;
      gap: 60px;
      margin: 16px 0 32px;
      user-select: none;
    }}
    .matching-column {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
      z-index: 2;
    }}
    .matching-item {{
      background: var(--surface);
      border: 1.5px solid var(--border);
      border-radius: var(--radius-md);
      padding: 16px;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      text-align: center;
      font-weight: 500;
      min-height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      color: var(--text-main);
    }}
    .matching-item:hover {{
      border-color: var(--accent);
      transform: translateY(-1px);
    }}
    .matching-item.selected {{
      border-color: var(--accent);
      background: var(--accent-soft);
    }}
    .matching-item.snap-target {{
      border-color: var(--accent);
      background: rgba(79, 70, 229, 0.05);
    }}
    .matching-item.matched {{
      border-color: var(--success);
      color: var(--success);
      background: var(--success-soft);
      cursor: default;
      transform: none;
    }}
    .matching-svg {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
    }}
    .matching-svg line {{
      transition: all 0.15s ease;
    }}
    
    /* Ordering Game */
    .ordering-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      user-select: none;
      -webkit-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;
    }}
    .ordering-item {{
      background: var(--surface);
      border: 1.5px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px 18px;
      display: flex;
      align-items: center;
      gap: 14px;
      cursor: grab;
      transition: all 0.2s ease;
      font-weight: 500;
      font-size: 1rem;
      user-select: none;
      -webkit-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;
      -webkit-touch-callout: none;
    }}
    .ordering-item:active {{ cursor: grabbing; }}
    .ordering-item:hover {{
      border-color: var(--accent);
    }}
    .ordering-item.selected {{
      border-color: var(--accent);
      background: var(--accent-soft);
    }}
    .ordering-item.dragging {{
      opacity: 0.9;
      background: var(--surface);
      border-color: var(--accent);
      box-shadow: var(--shadow-lg);
      transform: scale(1.01);
    }}
    .ordering-item.sortable-ghost {{
      opacity: 0.2;
      background: var(--accent-soft);
    }}
    .ordering-item.sortable-chosen {{
      border-color: var(--accent);
    }}
    .ordering-handle {{
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .ordering-handle span {{
      display: block;
      width: 14px;
      height: 2px;
      border-radius: 999px;
      background: currentColor;
    }}
    .ordering-mobile-controls {{
      margin-left: auto;
      display: flex;
      gap: 6px;
    }}
    @media (min-width: 769px) {{
      .ordering-mobile-controls {{ display: none; }}
    }}
    
    /* Error Spotting */
    .error-spotting-text {{
      font-size: 1.1rem;
      line-height: 1.8;
      padding: 20px;
      background: var(--bg);
      border-radius: var(--radius-md);
      margin-bottom: 24px;
      border: 1px solid var(--border);
      color: var(--text-main);
    }}
    .error-status {{
      margin-bottom: 12px;
      font-size: 0.9rem;
      color: var(--text-muted);
    }}
    .error-chip {{
      display: inline-flex;
      align-items: center;
      padding: 0 6px;
      margin: 0 2px;
      border-radius: 6px;
      border: 1px dashed var(--danger);
      background: var(--danger-soft);
      color: var(--danger);
      cursor: pointer;
      transition: all 0.2s ease;
      font-weight: 500;
    }}
    .error-chip:hover {{
      background: #fecaca;
    }}
    .error-chip.active {{
      background: var(--accent-soft);
      border: 1px solid var(--accent);
      color: var(--accent);
    }}
    .correction-input-group {{
      margin-top: 12px;
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      background: var(--bg);
      padding: 12px;
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
      animation: fadeIn 0.3s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}
    .correction-input {{
      flex: 1;
      padding: 10px 14px;
      border: 1.5px solid var(--border);
      border-radius: 8px;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.2s;
    }}
    .correction-input:focus {{
      border-color: var(--accent);
    }}

    /* Buttons */
    .actions {{
      margin-top: 40px;
      display: flex;
      justify-content: center;
    }}
    .btn {{
      padding: 12px 32px;
      border-radius: 99px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    .btn-primary {{
      background: var(--primary);
      color: white;
    }}
    .btn-primary:hover:not(:disabled) {{
      background: var(--primary-hover);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    .btn-secondary {{
      background: var(--surface);
      color: var(--text-main);
      border: 1px solid var(--border);
    }}
    .btn-secondary:hover:not(:disabled) {{
      background: var(--bg);
    }}
    .btn:disabled {{
      opacity: 0.3;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }}
    
    /* Feedback Box */
    .feedback-overlay {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 20px;
    }}
    .feedback-card {{
      background: var(--surface);
      border-radius: var(--radius-lg);
      padding: 40px;
      max-width: 360px;
      width: 100%;
      text-align: center;
      box-shadow: var(--shadow-lg);
      animation: popIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    @keyframes popIn {{
      0% {{ transform: scale(0.9); opacity: 0; }}
      100% {{ transform: scale(1); opacity: 1; }}
    }}
    .feedback-icon {{
      font-size: 3rem;
      margin-bottom: 16px;
    }}
    .feedback-title {{
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .feedback-msg {{
      color: var(--text-muted);
      margin-bottom: 24px;
      font-size: 0.95rem;
    }}
    
    .hidden {{ display: none !important; }}
    
    @media (max-width: 600px) {{
      .matching-container {{ flex-direction: column; gap: 24px; }}
      .matching-svg {{ display: none; }}
      .matching-item.selected::after {{
        content: "↓";
        position: absolute;
        bottom: -18px;
        color: var(--accent);
      }}
      .panel {{ padding: 24px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1 id="gameTitle">课堂小游戏</h1>
      <p id="gameTopic"></p>
    </header>

    <main class="panel">
      <!-- Start Screen -->
      <div id="startScreen">
        <div style="text-align: center; padding: 40px 0;">
          <div style="font-size: 3.5rem; margin-bottom: 16px;">🚀</div>
          <h2 style="font-size: 1.75rem; margin-bottom: 12px; font-weight: 700;">准备好挑战了吗？</h2>
          <p style="color: var(--text-muted); margin-bottom: 40px;">专注思考，轻松通关</p>
          <button class="btn btn-primary" id="startBtn" style="padding: 14px 40px;">开启闯关</button>
        </div>
      </div>

      <!-- Play Screen -->
      <div id="playScreen" class="hidden">
        <div class="hud">
          <div class="hud-item">
            <span class="hud-label">关卡</span>
            <span class="hud-value" id="levelValue">1 / 3</span>
          </div>
          <div class="hud-stats">
            <div class="hud-item">
              <span class="hud-label">得分</span>
              <span class="hud-value" id="scoreValue">0</span>
            </div>
            <div class="hud-item">
              <span class="hud-label" style="color: var(--accent);">连击</span>
              <span class="hud-value" style="color: var(--accent);" id="comboValue">0</span>
            </div>
          </div>
        </div>

        <div class="progress-container">
          <div class="progress-bar" id="progressBar"></div>
        </div>

        <div id="questionArea">
          <div class="question-stem" id="questionStem"></div>
          <div id="questionContent"></div>
          
          <div class="actions">
            <button class="btn btn-primary" id="submitBtn">提交答案</button>
          </div>
        </div>
      </div>

      <!-- Final Screen -->
      <div id="finalScreen" class="hidden">
        <div style="text-align: center; padding: 40px 0;">
          <div id="finalIcon" style="font-size: 4rem; margin-bottom: 20px;">🏆</div>
          <h2 style="font-size: 2rem; margin-bottom: 8px; font-weight: 700;">闯关圆满完成！</h2>
          <p style="color: var(--text-muted); margin-bottom: 32px;">感谢你的参与与专注</p>
          
          <div style="display: flex; justify-content: center; gap: 24px; margin-bottom: 40px;">
            <div style="background: var(--bg); padding: 24px; border-radius: var(--radius-md); flex: 1; max-width: 160px;">
              <div class="hud-label" style="margin-bottom: 8px;">最终得分</div>
              <div style="font-size: 2rem; font-weight: 800; color: var(--text-main);" id="finalScore">0</div>
            </div>
            <div style="background: var(--bg); padding: 24px; border-radius: var(--radius-md); flex: 1; max-width: 160px;">
              <div class="hud-label" style="margin-bottom: 8px;">正确率</div>
              <div style="font-size: 2rem; font-weight: 800; color: var(--success);" id="finalAccuracy">0%</div>
            </div>
          </div>
          
          <button class="btn btn-secondary" onclick="location.reload()" style="padding: 12px 32px;">重新开始</button>
        </div>
      </div>
    </main>
  </div>

  <!-- Feedback Overlay -->
  <div class="feedback-overlay" id="feedbackOverlay">
    <div class="feedback-card">
      <div class="feedback-icon" id="feedbackIcon">✨</div>
      <div class="feedback-title" id="feedbackTitle">太棒了！</div>
      <div class="feedback-msg" id="feedbackMsg">回答完全正确。</div>
      <button class="btn btn-primary" id="nextBtn" style="width: 100%;">继续</button>
    </div>
  </div>

  <script>{sortable_vendor_script}</script>
  <script>
    const GAME_DATA = {data_json};
    
    const state = {{
      currentStage: 0,
      currentQuestion: 0,
      score: 0,
      combo: 0,
      correctCount: 0,
      totalQuestions: 0,
      userAnswer: null,
      cleanupCurrentQuestion: null,
      draggedIdx: null
    }};

    // DOM Elements
    const dom = {{
      startScreen: document.getElementById('startScreen'),
      playScreen: document.getElementById('playScreen'),
      finalScreen: document.getElementById('finalScreen'),
      gameTitle: document.getElementById('gameTitle'),
      gameTopic: document.getElementById('gameTopic'),
      scoreValue: document.getElementById('scoreValue'),
      levelValue: document.getElementById('levelValue'),
      comboValue: document.getElementById('comboValue'),
      progressBar: document.getElementById('progressBar'),
      questionStem: document.getElementById('questionStem'),
      questionContent: document.getElementById('questionContent'),
      submitBtn: document.getElementById('submitBtn'),
      feedbackOverlay: document.getElementById('feedbackOverlay'),
      feedbackIcon: document.getElementById('feedbackIcon'),
      feedbackTitle: document.getElementById('feedbackTitle'),
      feedbackMsg: document.getElementById('feedbackMsg'),
      nextBtn: document.getElementById('nextBtn'),
      finalScore: document.getElementById('finalScore'),
      finalAccuracy: document.getElementById('finalAccuracy')
    }};

    function escapeHtml(value) {{
      return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}

    function clearTextSelection() {{
      try {{
        if (window.getSelection) {{
          const selection = window.getSelection();
          if (selection && typeof selection.removeAllRanges === 'function') {{
            selection.removeAllRanges();
          }}
        }}
      }} catch (error) {{
        console.warn('clear selection failed', error);
      }}

      try {{
        if (document.selection && typeof document.selection.empty === 'function') {{
          document.selection.empty();
        }}
      }} catch (error) {{
        console.warn('legacy clear selection failed', error);
      }}
    }}

    function setOrderingDragActive(active) {{
      document.body.classList.toggle('ordering-drag-active', Boolean(active));
      if (active) {{
        clearTextSelection();
      }}
    }}

    function init() {{
      dom.gameTitle.textContent = GAME_DATA.meta?.title || '课堂小游戏';
      dom.gameTopic.textContent = GAME_DATA.meta?.topic || '';
      
      state.totalQuestions = (GAME_DATA.stages || []).reduce((acc, s) => acc + (s.questions?.length || 0), 0);
      
      document.getElementById('startBtn').onclick = startPlay;
      dom.submitBtn.onclick = submitAnswer;
      dom.nextBtn.onclick = nextQuestion;
    }}

    function startPlay() {{
      dom.startScreen.classList.add('hidden');
      dom.playScreen.classList.remove('hidden');
      loadQuestion();
    }}

    function getCurrentQuestion() {{
      return GAME_DATA.stages[state.currentStage].questions[state.currentQuestion];
    }}

    function cleanupCurrentQuestion() {{
      if (typeof state.cleanupCurrentQuestion === 'function') {{
        try {{
          state.cleanupCurrentQuestion();
        }} catch (error) {{
          console.warn('cleanup failed', error);
        }}
      }}
      state.cleanupCurrentQuestion = null;
    }}

    function loadQuestion() {{
      const q = getCurrentQuestion();
      cleanupCurrentQuestion();
      
      // Simplify stem: put interaction tip with stem, remove review ref and example
      const tip = q.interaction_tip || '请根据题意完成操作';
      dom.questionStem.innerHTML = `
        <div class="question-text">${{escapeHtml(q.stem)}}</div>
        <div class="question-tip">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          ${{escapeHtml(tip)}}
        </div>
      `;
      
      dom.questionContent.innerHTML = '';
      state.userAnswer = null;
      dom.submitBtn.disabled = true;
      
      updateHUD();

      switch(q.type) {{
        case 'multiple_choice': renderMultipleChoice(q); break;
        case 'fill_in_blank': renderFillInBlank(q); break;
        case 'matching': renderMatching(q); break;
        case 'ordering': renderOrdering(q); break;
        case 'error_spotting': renderErrorSpotting(q); break;
      }}
    }}

    function updateHUD() {{
      dom.scoreValue.textContent = state.score;
      dom.levelValue.textContent = `${{state.currentStage + 1}} / ${{GAME_DATA.stages.length}}`;
      dom.comboValue.textContent = state.combo;
      
      const totalAnswered = GAME_DATA.stages.slice(0, state.currentStage).reduce((acc, s) => acc + s.questions.length, 0) + state.currentQuestion;
      const progress = state.totalQuestions > 0 ? (totalAnswered / state.totalQuestions) * 100 : 0;
      dom.progressBar.style.width = `${{progress}}%`;
    }}

    // Renderers
    function renderMultipleChoice(q) {{
      const list = document.createElement('div');
      list.className = 'ordering-list';
      q.options.forEach((opt, i) => {{
        const char = String.fromCharCode(65 + i);
        const item = document.createElement('div');
        item.className = 'ordering-item';
        item.style.cursor = 'pointer';
        item.innerHTML = `<span style="font-weight:700; color:var(--text-muted); width: 24px;">${{char}}</span> <span>${{escapeHtml(opt)}}</span>`;
        item.onclick = () => {{
          document.querySelectorAll('.ordering-item').forEach(el => el.classList.remove('selected'));
          item.classList.add('selected');
          state.userAnswer = char;
          dom.submitBtn.disabled = false;
        }};
        list.appendChild(item);
      }});
      dom.questionContent.appendChild(list);
    }}

    function renderFillInBlank(q) {{
      const input = document.createElement('input');
      input.className = 'correction-input';
      input.style.width = '100%';
      input.style.padding = '14px 16px';
      input.style.fontSize = '1.05rem';
      input.placeholder = '在此输入答案...';
      input.oninput = (e) => {{
        state.userAnswer = e.target.value.trim();
        dom.submitBtn.disabled = !state.userAnswer;
      }};
      dom.questionContent.appendChild(input);
    }}

    function renderMatching(q) {{
      const wrapper = document.createElement('div');
      const toolbar = document.createElement('div');
      toolbar.className = 'matching-toolbar';
      const undoBtn = document.createElement('button');
      undoBtn.type = 'button';
      undoBtn.className = 'btn btn-secondary';
      undoBtn.style.padding = '6px 12px';
      undoBtn.style.fontSize = '0.85rem';
      undoBtn.textContent = '撤销连线';
      toolbar.appendChild(undoBtn);
      wrapper.appendChild(toolbar);

      const container = document.createElement('div');
      container.className = 'matching-container';

      const svgNS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.classList.add('matching-svg');
      container.appendChild(svg);

      const leftCol = document.createElement('div');
      leftCol.className = 'matching-column';
      const rightCol = document.createElement('div');
      rightCol.className = 'matching-column';

      const pairs = Array.isArray(q.pairs) ? q.pairs : [];
      const lefts = pairs.map(pair => pair.left);
      const rights = pairs.map(pair => pair.right).sort(() => Math.random() - 0.5);
      state.userAnswer = {{}};

      let activeLeftIdx = null;
      let pointerPos = null;
      let snappedRightIdx = null;
      const history = [];

      function updateSubmitState() {{
        dom.submitBtn.disabled = Object.keys(state.userAnswer).length !== pairs.length;
        undoBtn.disabled = history.length === 0;
      }}

      function getRightOwner(rightIdx) {{
        return Object.entries(state.userAnswer).find(([, value]) => Number(value) === Number(rightIdx));
      }}

      function getAnchor(element, side) {{
        const rect = element.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        return {{
          x: side === 'left' ? rect.right - containerRect.left : rect.left - containerRect.left,
          y: rect.top - containerRect.top + rect.height / 2,
        }};
      }}

      function clearSnapTargets() {{
        rightCol.querySelectorAll('.matching-item').forEach(item => item.classList.remove('snap-target'));
      }}

      function updateItemStates() {{
        const usedRights = new Set(Object.values(state.userAnswer).map(value => Number(value)));
        leftCol.querySelectorAll('.matching-item').forEach((item, index) => {{
          item.classList.toggle('selected', activeLeftIdx === index);
          item.classList.toggle('matched', state.userAnswer[index] !== undefined);
        }});
        rightCol.querySelectorAll('.matching-item').forEach((item, index) => {{
          item.classList.toggle('matched', usedRights.has(index));
        }});
      }}

      function drawLines() {{
        const rect = container.getBoundingClientRect();
        svg.setAttribute('viewBox', `0 0 ${{rect.width}} ${{rect.height}}`);
        svg.setAttribute('width', String(rect.width));
        svg.setAttribute('height', String(rect.height));
        svg.innerHTML = '';

        Object.entries(state.userAnswer).forEach(([leftIdx, rightIdx]) => {{
          const leftEl = leftCol.children[leftIdx];
          const rightEl = rightCol.children[rightIdx];
          if (!leftEl || !rightEl) return;
          const from = getAnchor(leftEl, 'left');
          const to = getAnchor(rightEl, 'right');
          const line = document.createElementNS(svgNS, 'line');
          line.setAttribute('x1', String(from.x));
          line.setAttribute('y1', String(from.y));
          line.setAttribute('x2', String(to.x));
          line.setAttribute('y2', String(to.y));
          line.setAttribute('stroke', 'var(--success)');
          line.setAttribute('stroke-width', '3');
          line.setAttribute('stroke-linecap', 'round');
          svg.appendChild(line);
        }});

        if (activeLeftIdx !== null) {{
          const leftEl = leftCol.children[activeLeftIdx];
          if (leftEl && pointerPos) {{
            const from = getAnchor(leftEl, 'left');
            const targetEl = snappedRightIdx !== null ? rightCol.children[snappedRightIdx] : null;
            const to = targetEl ? getAnchor(targetEl, 'right') : pointerPos;
            const preview = document.createElementNS(svgNS, 'line');
            preview.setAttribute('x1', String(from.x));
            preview.setAttribute('y1', String(from.y));
            preview.setAttribute('x2', String(to.x));
            preview.setAttribute('y2', String(to.y));
            preview.setAttribute('stroke', 'var(--accent)');
            preview.setAttribute('stroke-width', '3');
            preview.setAttribute('stroke-linecap', 'round');
            preview.setAttribute('stroke-dasharray', '6 6');
            svg.appendChild(preview);
          }}
        }}
      }}

      function connectPair(leftIdx, rightIdx) {{
        const owner = getRightOwner(rightIdx);
        if (owner && Number(owner[0]) !== Number(leftIdx)) return;
        const prevRight = state.userAnswer[leftIdx];
        state.userAnswer[leftIdx] = rightIdx;
        history.push({{ leftIdx, prevRight, nextRight: rightIdx }});
        activeLeftIdx = null;
        snappedRightIdx = null;
        pointerPos = null;
        clearSnapTargets();
        updateItemStates();
        drawLines();
        updateSubmitState();
      }}

      function activateLeft(leftIdx, clientX, clientY) {{
        activeLeftIdx = leftIdx;
        snappedRightIdx = null;
        if (state.userAnswer[leftIdx] !== undefined) {{
          delete state.userAnswer[leftIdx];
        }}
        if (typeof clientX === 'number' && typeof clientY === 'number') {{
          const rect = container.getBoundingClientRect();
          pointerPos = {{ x: clientX - rect.left, y: clientY - rect.top }};
        }}
        clearSnapTargets();
        updateItemStates();
        drawLines();
        updateSubmitState();
      }}

      function updatePointer(clientX, clientY) {{
        if (activeLeftIdx === null) return;
        const rect = container.getBoundingClientRect();
        pointerPos = {{ x: clientX - rect.left, y: clientY - rect.top }};
        clearSnapTargets();
        snappedRightIdx = null;
        const element = document.elementFromPoint(clientX, clientY);
        const target = element && element.closest ? element.closest('.matching-item[data-side="right"]') : null;
        if (target) {{
          const rightIdx = Number(target.dataset.index);
          const owner = getRightOwner(rightIdx);
          if (!owner || Number(owner[0]) === Number(activeLeftIdx)) {{
            snappedRightIdx = rightIdx;
            target.classList.add('snap-target');
          }}
        }}
        drawLines();
      }}

      function finishPointer() {{
        if (activeLeftIdx === null) return;
        if (snappedRightIdx !== null) {{
          connectPair(activeLeftIdx, snappedRightIdx);
        }} else {{
          pointerPos = null;
          snappedRightIdx = null;
          clearSnapTargets();
          updateItemStates();
          drawLines();
          updateSubmitState();
        }}
      }}

      undoBtn.onclick = () => {{
        const last = history.pop();
        if (!last) return;
        if (last.prevRight === undefined) {{
          delete state.userAnswer[last.leftIdx];
        }} else {{
          state.userAnswer[last.leftIdx] = last.prevRight;
        }}
        activeLeftIdx = null;
        snappedRightIdx = null;
        pointerPos = null;
        clearSnapTargets();
        updateItemStates();
        drawLines();
        updateSubmitState();
      }};

      lefts.forEach((text, index) => {{
        const item = document.createElement('div');
        item.className = 'matching-item';
        item.dataset.side = 'left';
        item.dataset.index = String(index);
        item.textContent = text;
        item.addEventListener('pointerdown', event => {{
          event.preventDefault();
          activateLeft(index, event.clientX, event.clientY);
        }});
        leftCol.appendChild(item);
      }});

      rights.forEach((text, index) => {{
        const item = document.createElement('div');
        item.className = 'matching-item';
        item.dataset.side = 'right';
        item.dataset.index = String(index);
        item.textContent = text;
        item.addEventListener('click', () => {{
          if (activeLeftIdx !== null) {{
            connectPair(activeLeftIdx, index);
          }}
        }});
        rightCol.appendChild(item);
      }});

      container.appendChild(leftCol);
      container.appendChild(rightCol);
      wrapper.appendChild(container);
      dom.questionContent.appendChild(wrapper);

      const onPointerMove = event => updatePointer(event.clientX, event.clientY);
      const onPointerUp = () => finishPointer();
      const onResize = () => drawLines();

      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
      window.addEventListener('resize', onResize);

      updateItemStates();
      updateSubmitState();
      requestAnimationFrame(drawLines);
      state.cleanupCurrentQuestion = () => {{
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onPointerUp);
        window.removeEventListener('resize', onResize);
      }};
    }}

    function renderOrdering(q) {{
      const list = document.createElement('div');
      list.className = 'ordering-list';
      list.addEventListener('selectstart', event => event.preventDefault());

      let items = Array.isArray(q.items) ? [...q.items] : [];
      state.userAnswer = [...items];

      function syncUserAnswer() {{
        state.userAnswer = Array.from(list.children)
          .map(item => item.dataset.value || '')
          .filter(Boolean);
        dom.submitBtn.disabled = state.userAnswer.length < 2;
      }}

      function createItem(text) {{
        const item = document.createElement('div');
        item.className = 'ordering-item';
        item.dataset.value = text;
        item.innerHTML = `
          <div class="ordering-handle" aria-hidden="true"><span></span><span></span><span></span></div>
          <span style="flex: 1;">${{escapeHtml(text)}}</span>
          <div class="ordering-mobile-controls">
            <button type="button" class="btn btn-secondary move-up" style="padding:4px 10px; font-size:0.85rem;">↑</button>
            <button type="button" class="btn btn-secondary move-down" style="padding:4px 10px; font-size:0.85rem;">↓</button>
          </div>
        `;
        item.querySelector('.move-up').addEventListener('click', () => moveItem(item, -1));
        item.querySelector('.move-down').addEventListener('click', () => moveItem(item, 1));
        return item;
      }}

      function moveItem(item, delta) {{
        const sibling = delta < 0 ? item.previousElementSibling : item.nextElementSibling;
        if (!sibling) return;
        if (delta < 0) {{
          list.insertBefore(item, sibling);
        }} else {{
          list.insertBefore(sibling, item);
        }}
        syncUserAnswer();
      }}

      items.forEach(text => list.appendChild(createItem(text)));
      dom.questionContent.appendChild(list);

      let sortable = null;
      if (typeof Sortable !== 'undefined') {{
        sortable = Sortable.create(list, {{
          animation: 200,
          easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
          ghostClass: 'sortable-ghost',
          chosenClass: 'sortable-chosen',
          dragClass: 'dragging',
          fallbackClass: 'sortable-fallback',
          forceFallback: true,
          onChoose() {{
            clearTextSelection();
          }},
          onStart() {{
            setOrderingDragActive(true);
          }},
          onEnd() {{
            setOrderingDragActive(false);
            clearTextSelection();
            syncUserAnswer();
          }}
        }});
      }}

      syncUserAnswer();
      state.cleanupCurrentQuestion = () => {{
        setOrderingDragActive(false);
        if (sortable && typeof sortable.destroy === 'function') {{
          sortable.destroy();
        }}
      }};
    }}

    function renderErrorSpotting(q) {{
      const container = document.createElement('div');
      const answers = Array.isArray(q.answer) ? [...q.answer].sort((a, b) => Number(a.start || 0) - Number(b.start || 0)) : [];
      state.userAnswer = [];

      const status = document.createElement('div');
      status.className = 'error-status';
      container.appendChild(status);

      const textDiv = document.createElement('div');
      textDiv.className = 'error-spotting-text';
      container.appendChild(textDiv);

      const correctionArea = document.createElement('div');
      correctionArea.id = 'correctionArea';

      function updateStatus() {{
        const completed = state.userAnswer.filter(item => String(item.correction || '').trim()).length;
        status.innerHTML = `已处理 <strong style="color:var(--text-main);">${{completed}}</strong> / ${{answers.length}} 处错误。点击红色片段进行修改。`;
        dom.submitBtn.disabled = !(answers.length > 0 && completed === answers.length);
      }}

      function setActiveChip(index) {{
        textDiv.querySelectorAll('.error-chip').forEach(chip => chip.classList.toggle('active', Number(chip.dataset.index) === index));
      }}

      function getOrCreateEntry(index) {{
        let entry = state.userAnswer.find(item => item.index === index);
        if (!entry) {{
          const answer = answers[index];
          entry = {{
            index,
            wrongText: answer ? answer.wrong : '',
            correction: '',
          }};
          state.userAnswer.push(entry);
        }}
        return entry;
      }}

      function removeEntry(index) {{
        state.userAnswer = state.userAnswer.filter(item => item.index !== index);
        const group = correctionArea.querySelector(`[data-correction-index="${{index}}"]`);
        if (group) group.remove();
        setActiveChip(-1);
        updateStatus();
      }}

      function focusCorrection(index) {{
        const answer = answers[index];
        if (!answer) return;
        const entry = getOrCreateEntry(index);
        let group = correctionArea.querySelector(`[data-correction-index="${{index}}"]`);
        if (!group) {{
          group = document.createElement('div');
          group.className = 'correction-input-group';
          group.dataset.correctionIndex = String(index);
          group.innerHTML = `
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-weight:600; color:var(--danger); max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${{escapeHtml(answer.wrong)}}">${{escapeHtml(answer.wrong)}}</span>
              <span style="color:var(--text-muted);">→</span>
            </div>
            <input type="text" class="correction-input" placeholder="输入修正内容...">
            <button type="button" class="btn btn-secondary remove-correction" style="padding:8px 12px; font-size:0.85rem;">撤销</button>
          `;
          const input = group.querySelector('input');
          input.value = entry.correction || '';
          input.addEventListener('input', event => {{
            entry.correction = event.target.value;
            updateStatus();
          }});
          group.querySelector('.remove-correction').addEventListener('click', () => removeEntry(index));
          correctionArea.appendChild(group);
        }}
        setActiveChip(index);
        const input = group.querySelector('input');
        input.focus();
        updateStatus();
      }}

      let cursor = 0;
      answers.forEach((answer, index) => {{
        const start = Number(answer.start);
        const end = Number(answer.end);
        if (start > cursor) {{
          textDiv.appendChild(document.createTextNode(String(q.text || '').slice(cursor, start)));
        }}
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'error-chip';
        chip.dataset.index = String(index);
        chip.textContent = String(q.text || '').slice(start, end);
        chip.addEventListener('click', () => focusCorrection(index));
        textDiv.appendChild(chip);
        cursor = end;
      }});
      const fullText = String(q.text || '');
      if (cursor < fullText.length) {{
        textDiv.appendChild(document.createTextNode(fullText.slice(cursor)));
      }}

      container.appendChild(correctionArea);
      dom.questionContent.appendChild(container);
      updateStatus();
    }}

    // Logic
    function submitAnswer() {{
      const q = getCurrentQuestion();
      let isCorrect = false;

      function normalizeCorrectionText(value) {{
        return String(value || '')
          .toLowerCase()
          .replace(/[\\s\\u3000]/g, '')
          .replace(/[，。；：、！？,.!?:;"'“”‘’()（）【】\\[\\]{{}}<>《》]/g, '');
      }}
      
      if (q.type === 'multiple_choice' || q.type === 'fill_in_blank') {{
        const correctAns = Array.isArray(q.answer) ? q.answer : [q.answer];
        isCorrect = correctAns.some(a => String(a).toLowerCase() === String(state.userAnswer).toLowerCase());
      }} else if (q.type === 'matching') {{
        isCorrect = true;
        const pairs = q.pairs || [];
        const lefts = Array.from(document.querySelectorAll('.matching-column:first-child .matching-item')).map(el => el.textContent);
        const rights = Array.from(document.querySelectorAll('.matching-column:last-child .matching-item')).map(el => el.textContent);
        
        Object.entries(state.userAnswer).forEach(([lIdx, rIdx]) => {{
          const lTxt = lefts[lIdx];
          const rTxt = rights[rIdx];
          const pair = pairs.find(p => p.left === lTxt);
          if (!pair || pair.right !== rTxt) isCorrect = false;
        }});
      }} else if (q.type === 'ordering') {{
        isCorrect = JSON.stringify(state.userAnswer) === JSON.stringify(q.answer);
      }} else if (q.type === 'error_spotting') {{
        const expected = q.answer || [];
        const userMatches = state.userAnswer;
        
        isCorrect = userMatches.length === expected.length && 
                    expected.every((exp, index) => userMatches.some(um => 
                      Number(um.index) === index &&
                      um.wrongText === exp.wrong && 
                      (() => {{
                        const userNormalized = normalizeCorrectionText(um.correction);
                        const acceptableAnswers = Array.isArray(exp.acceptable_answers) && exp.acceptable_answers.length
                          ? exp.acceptable_answers
                          : [exp.correct];
                        return acceptableAnswers.some(answer => {{
                          const expectedNormalized = normalizeCorrectionText(answer);
                          return expectedNormalized &&
                            userNormalized &&
                            (
                              userNormalized === expectedNormalized ||
                              userNormalized.includes(expectedNormalized) ||
                              expectedNormalized.includes(userNormalized)
                            );
                        }});
                      }})()
                    ));
      }}

      if (isCorrect) {{
        state.score += q.score || 10;
        state.combo++;
        state.correctCount++;
        showFeedback(true, q.correct_feedback);
      }} else {{
        state.combo = 0;
        showFeedback(false, q.wrong_feedback);
      }}
    }}

    function showFeedback(correct, msg) {{
      dom.feedbackOverlay.style.display = 'flex';
      dom.feedbackIcon.textContent = correct ? '✨' : '💡';
      dom.feedbackTitle.textContent = correct ? '太棒了！' : '再接再厉！';
      dom.feedbackTitle.style.color = correct ? 'var(--success)' : 'var(--text-main)';
      dom.feedbackMsg.textContent = msg || (correct ? '回答完全正确，继续保持！' : '回答有误，没关系，再试一次。');
    }}

    function nextQuestion() {{
      dom.feedbackOverlay.style.display = 'none';
      state.currentQuestion++;
      
      if (state.currentQuestion >= GAME_DATA.stages[state.currentStage].questions.length) {{
        state.currentStage++;
        state.currentQuestion = 0;
      }}
      
      if (state.currentStage >= GAME_DATA.stages.length) {{
        finishGame();
      }} else {{
        loadQuestion();
      }}
    }}

    function finishGame() {{
      cleanupCurrentQuestion();
      dom.playScreen.classList.add('hidden');
      dom.finalScreen.classList.remove('hidden');
      dom.finalScore.textContent = state.score;
      
      const accuracy = state.totalQuestions > 0 ? (state.correctCount / state.totalQuestions) : 0;
      dom.finalAccuracy.textContent = Math.round(accuracy * 100) + '%';
      
      if (accuracy > 0.8) {{
        dom.finalIcon.textContent = '🏆';
      }} else if (accuracy > 0.5) {{
        dom.finalIcon.textContent = '👍';
      }} else {{
        dom.finalIcon.textContent = '💪';
      }}
    }}

    init();
  </script>
</body>
</html>
"""
