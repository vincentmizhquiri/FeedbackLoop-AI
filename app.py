from __future__ import annotations

import argparse

from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FeedbackLoop AI HR Chat</title>
    <style>
      :root {
        --bg: #07111f;
        --panel: #0f1b2d;
        --panel-2: #14253d;
        --accent: #2dd4bf;
        --accent-2: #fbbf24;
        --accent-3: #f87171;
        --text: #e5f3ff;
        --muted: #7fa0bf;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, Arial, sans-serif;
        background: linear-gradient(135deg, #07111f, #10233f);
        color: var(--text);
      }
      .shell {
        max-width: 1400px;
        margin: 0 auto;
        padding: 24px;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(15, 27, 45, 0.95);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 18px 24px;
        margin-bottom: 20px;
        gap: 12px;
      }
      .header h1 { margin: 0; font-size: 22px; }
      .chip-row, .header-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
      .chip, .header-btn { padding: 8px 12px; border-radius: 999px; font-weight: 700; font-size: 13px; }
      .chip.green { background: rgba(45,212,191,0.2); color: #8ff3e4; }
      .chip.yellow { background: rgba(251,191,36,0.2); color: #fde68a; }
      .chip.red { background: rgba(248,113,113,0.2); color: #fecaca; }
      .header-btn { border: 0; cursor: pointer; background: var(--accent); color: #07212d; }
      .layout { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 18px; }
      .panel {
        background: rgba(15, 27, 45, 0.95);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 18px;
      }
      .candidate-list {
        display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px;
      }
      .card {
        min-width: 260px;
        border-radius: 16px;
        padding: 14px;
        background: var(--panel-2);
        border: 1px solid rgba(255,255,255,0.08);
        cursor: pointer;
        transition: transform 150ms ease, border-color 150ms ease;
      }
      .card:hover { transform: translateY(-2px); }
      .card strong { display: block; margin-bottom: 6px; }
      .card.green { border-color: rgba(45,212,191,0.67); }
      .card.yellow { border-color: rgba(251,191,36,0.67); }
      .card.red { border-color: rgba(248,113,113,0.67); }
      .card.active { box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16); }
      .card .meta { color: var(--muted); font-size: 13px; margin-top: 6px; }
      .card .skills { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
      .pill { padding: 4px 8px; border-radius: 999px; background: rgba(255,255,255,0.08); font-size: 12px; }
      .actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
      .link-btn { background: rgba(255,255,255,0.06); color: var(--text); border: 0; padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: 12px; }
      .summary {
        margin-top: 16px; padding: 14px; border-radius: 14px;
        background: rgba(255,255,255,0.04);
        color: var(--text);
      }
      .history { margin-top: 12px; color: var(--muted); font-size: 14px; }
      .chat-box {
        min-height: 320px; display: flex; flex-direction: column; justify-content: space-between;
      }
      .messages {
        display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;
      }
      .bubble {
        padding: 12px 14px; border-radius: 12px; max-width: 90%;
        background: rgba(255,255,255,0.06);
      }
      .bubble.ai { background: rgba(45,212,191,0.16); align-self: flex-start; }
      .bubble.user { background: rgba(255,255,255,0.09); align-self: flex-end; }
      .composer { display: flex; gap: 10px; }
      .composer input {
        flex: 1; border: 0; outline: 0; border-radius: 999px; padding: 12px 14px; color: #07111f;
      }
      .composer button { border: 0; border-radius: 999px; padding: 10px 14px; cursor: pointer; font-weight: 700; background: var(--accent); color: #07212d; }
      .chat-overlay {
        position: fixed; top: 0; right: 0; width: min(430px, 100%); height: 100%; background: rgba(7,17,31,0.97); border-left: 1px solid rgba(255,255,255,0.08); transform: translateX(110%); transition: transform 180ms ease; box-shadow: -16px 0 40px rgba(0,0,0,0.35); z-index: 20; padding: 18px; display: flex; flex-direction: column; gap: 12px;
        backdrop-filter: blur(10px);
      }
      .chat-overlay.open { transform: translateX(0); }
      .chat-overlay header { display: flex; justify-content: space-between; align-items: center; }
      .selection-row { display: flex; gap: 8px; flex-wrap: wrap; }
      .selection-btn { border: 0; border-radius: 999px; padding: 8px 10px; font-weight: 700; cursor: pointer; color: var(--text); background: rgba(255,255,255,0.08); }
      .selection-btn.active.green { background: rgba(45,212,191,0.24); color: #8ff3e4; }
      .selection-btn.active.yellow { background: rgba(251,191,36,0.24); color: #fde68a; }
      .selection-btn.active.red { background: rgba(248,113,113,0.24); color: #fecaca; }
      .overlay-copy { background: rgba(255,255,255,0.04); border-radius: 14px; padding: 12px; color: var(--text); }
      .overlay-copy strong { display: block; margin-bottom: 8px; }
      @media (max-width: 900px) {
        .layout { grid-template-columns: 1fr; }
        .header { flex-direction: column; align-items: flex-start; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="header">
        <div>
          <h1>FeedbackLoop AI • Candidate Comparison</h1>
          <div style="color: var(--muted); margin-top: 6px;">Expandable HR AI chat with history-aware rationale</div>
        </div>
        <div class="header-actions">
          <button class="header-btn" id="open-chat-btn" type="button">Chat</button>
          <div class="chip-row">
            <div class="chip green">Green • Strong Hire</div>
            <div class="chip yellow">Yellow • Lean Hire</div>
            <div class="chip red">Red • Conflicted</div>
          </div>
        </div>
      </div>

      <div class="layout">
        <div class="panel">
          <h3 style="margin-top:0;">Candidate lineup</h3>
          <div class="candidate-list">
            <div class="card green">
              <strong>Priya Patel</strong>
              <div class="meta">Profile • Senior Software Engineer</div>
              <div class="meta">Age • 31</div>
              <div class="meta">Years of experience • 8</div>
              <div class="skills">
                <span class="pill">Python</span>
                <span class="pill">System Design</span>
                <span class="pill">SQL</span>
                <span class="pill">AWS</span>
              </div>
              <div class="actions">
                <button class="link-btn" type="button">Upload</button>
                <button class="link-btn" type="button">Download</button>
                <button class="link-btn" type="button">Edit</button>
              </div>
            </div>
            <div class="card yellow">
              <strong>Jordan Reyes</strong>
              <div class="meta">Profile • Backend Platform Engineer</div>
              <div class="meta">Age • 29</div>
              <div class="meta">Years of experience • 6</div>
              <div class="skills">
                <span class="pill">Go</span>
                <span class="pill">Distributed Systems</span>
                <span class="pill">Kafka</span>
                <span class="pill">CI/CD</span>
              </div>
              <div class="actions">
                <button class="link-btn" type="button">Upload</button>
                <button class="link-btn" type="button">Download</button>
                <button class="link-btn" type="button">Edit</button>
              </div>
            </div>
            <div class="card red">
              <strong>Marcus Chen</strong>
              <div class="meta">Profile • Staff Developer</div>
              <div class="meta">Age • 35</div>
              <div class="meta">Years of experience • 12</div>
              <div class="skills">
                <span class="pill">Leadership</span>
                <span class="pill">Payments</span>
                <span class="pill">Security</span>
                <span class="pill">React</span>
              </div>
              <div class="actions">
                <button class="link-btn" type="button">Upload</button>
                <button class="link-btn" type="button">Download</button>
                <button class="link-btn" type="button">Edit</button>
              </div>
            </div>
          </div>

          <div class="summary">
            <strong>LLM rationale</strong>
            <p>Priya Patel is marked as Strong Hire with a signal score of 0.91 across 4 scorecards. The strongest evidence was ledger reconciliation, on-call ownership, system design.</p>
            <p>Jordan Reyes is marked as Lean Hire with a signal score of 0.74 across 3 scorecards. Historical context: this candidate was previously seen on REQ-4201 (Software Engineer II) and reached Onsite with outcome No hire on 2024-03-01.</p>
            <p>Marcus Chen is marked as Conflicted with insufficient data because the system excluded problematic feedback.</p>
          </div>
        </div>

        <div class="panel chat-box">
          <div>
            <h3 style="margin-top:0;">HR AI chat</h3>
            <div class="messages">
              <div class="bubble ai">I can help review this applicant’s history and explain why they fit the requisition.</div>
              <div class="bubble user">Why is Priya a strong hire for this role?</div>
              <div class="bubble ai">Her experience in ledger reconciliation, on-call ownership, and system design aligns strongly with the role’s operational and architecture expectations.</div>
            </div>
          </div>
          <div class="history">
            <strong>History</strong>
            <div>REQ-4201 • Software Engineer II • Onsite • No hire • 2024-03-01</div>
          </div>
          <div class="composer">
            <input value="Ask about candidate fit, history, or hiring risk" />
            <button type="button">Ask</button>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-overlay" id="chat-overlay" aria-label="HR AI chat overlay">
      <header>
        <div>
          <strong>HR AI Chat</strong>
          <div style="color: var(--muted); font-size: 13px;">Candidate rationale and history</div>
        </div>
        <button class="link-btn" id="close-chat-btn" type="button">Close</button>
      </header>
      <div class="selection-row">
        <button class="selection-btn active green" data-label="Strong Hire" type="button">Strong Hire</button>
        <button class="selection-btn yellow" data-label="Lean Hire" type="button">Lean Hire</button>
        <button class="selection-btn red" data-label="Conflicted" type="button">Conflicted</button>
        <button class="selection-btn" data-label="Optional" type="button">Optional</button>
      </div>
      <div class="overlay-copy">
        <strong id="selection-title">Strong Hire</strong>
        <div id="selection-copy">Priya Patel shows strong matching evidence across system design, ledger reconciliation, and on-call ownership.</div>
      </div>
      <div class="messages">
        <div class="bubble ai">Ask about skills, experience, or prior requisition history.</div>
        <div class="bubble user">What makes this candidate a strong hire?</div>
        <div class="bubble ai" id="chat-response">Their profile fits the role with strong architecture depth and operational ownership.</div>
      </div>
      <div class="composer">
        <input id="chat-input" value="Ask about fit, age, years of experience, or skills" />
        <button type="button" id="send-chat-btn">Ask</button>
      </div>
    </div>

    <script>
      const openBtn = document.getElementById('open-chat-btn');
      const closeBtn = document.getElementById('close-chat-btn');
      const overlay = document.getElementById('chat-overlay');
      const selectionButtons = Array.from(document.querySelectorAll('.selection-btn'));
      const response = document.getElementById('chat-response');
      const title = document.getElementById('selection-title');
      const copy = document.getElementById('selection-copy');
      const input = document.getElementById('chat-input');
      const sendBtn = document.getElementById('send-chat-btn');
      const cards = Array.from(document.querySelectorAll('.card'));

      const rationaleMap = {
        'Strong Hire': 'Priya Patel shows strong matching evidence across system design, ledger reconciliation, and on-call ownership.',
        'Lean Hire': 'Jordan Reyes is a plausible fit with solid backend depth, though the panel still wants more evidence around ownership.',
        'Conflicted': 'Marcus Chen brings leadership and seniority, but the panel has unresolved concerns around role fit and evidence quality.',
        'Optional': 'This candidate remains a flexible option if the hiring team wants a broader bench of profiles.'
      };

      const setSelection = (label) => {
        selectionButtons.forEach((item) => item.classList.remove('active'));
        const matching = selectionButtons.find((item) => item.getAttribute('data-label') === label);
        if (matching) matching.classList.add('active');
        title.textContent = label;
        copy.textContent = rationaleMap[label] || 'The selection is still being reviewed.';
        response.textContent = label === 'Strong Hire'
          ? 'Their profile fits the role with strong architecture depth and operational ownership.'
          : label === 'Lean Hire'
          ? 'The profile is credible but would benefit from additional evidence before advancement.'
          : label === 'Conflicted'
          ? 'This profile needs deeper review due to unresolved fit questions.'
          : 'The team can keep this profile as an optional candidate for later review.';
      };

      openBtn.addEventListener('click', () => overlay.classList.add('open'));
      closeBtn.addEventListener('click', () => overlay.classList.remove('open'));

      selectionButtons.forEach((button) => {
        button.addEventListener('click', () => setSelection(button.getAttribute('data-label')));
      });

      cards.forEach((card) => {
        card.addEventListener('click', () => {
          cards.forEach((item) => item.classList.remove('active'));
          card.classList.add('active');
          const name = card.querySelector('strong').textContent;
          const label = name.includes('Jordan') ? 'Lean Hire' : name.includes('Marcus') ? 'Conflicted' : 'Strong Hire';
          setSelection(label);
          overlay.classList.add('open');
        });
      });

      const internalKnowledgeBase = {
        'Strong Hire': {
          name: 'Priya Patel',
          role: 'Senior Software Engineer',
          age: 31,
          experience: 8,
          skills: ['Python', 'System Design', 'SQL', 'AWS'],
          history: 'Prior requisition history is not available for this candidate in the current view.',
          summary: 'Strong fit for the role because the scorecards align on architecture depth and operational ownership.',
          answerMap: {
            'what is the candidate age': 'Priya Patel is 31 years old.',
            'how many years of experience': 'Priya Patel has 8 years of experience.',
            'what skills does the candidate have': 'Priya Patel has Python, System Design, SQL, and AWS.',
            'what is the hiring history': 'Prior requisition history is not available for this candidate in the current view.',
            'why is this candidate a strong hire': 'The scorecards align on architecture depth and operational ownership, which is why she is marked Strong Hire.'
          }
        },
        'Lean Hire': {
          name: 'Jordan Reyes',
          role: 'Backend Platform Engineer',
          age: 29,
          experience: 6,
          skills: ['Go', 'Distributed Systems', 'Kafka', 'CI/CD'],
          history: 'This candidate was previously seen on REQ-4201 and reached the onsite stage with a no-hire outcome.',
          summary: 'Moderate fit with strong platform depth but still needs more evidence before advancement.',
          answerMap: {
            'what is the candidate age': 'Jordan Reyes is 29 years old.',
            'how many years of experience': 'Jordan Reyes has 6 years of experience.',
            'what skills does the candidate have': 'Jordan Reyes has Go, Distributed Systems, Kafka, and CI/CD.',
            'what is the hiring history': 'This candidate was previously seen on REQ-4201 and reached the onsite stage with a no-hire outcome.',
            'why is this candidate a lean hire': 'The profile shows credible platform depth, but the panel still wants more evidence before advancement.'
          }
        },
        'Conflicted': {
          name: 'Marcus Chen',
          role: 'Staff Developer',
          age: 35,
          experience: 12,
          skills: ['Leadership', 'Payments', 'Security', 'React'],
          history: 'The panel flagged this profile for additional review because the evidence was mixed.',
          summary: 'High seniority and leadership depth, but the hiring panel remains split on role fit.',
          answerMap: {
            'what is the candidate age': 'Marcus Chen is 35 years old.',
            'how many years of experience': 'Marcus Chen has 12 years of experience.',
            'what skills does the candidate have': 'Marcus Chen has Leadership, Payments, Security, and React.',
            'what is the hiring history': 'The panel flagged this profile for additional review because the evidence was mixed.',
            'why is this candidate conflicted': 'The profile has strong seniority, but the current evidence does not fully resolve the role-fit questions.'
          }
        },
        'Optional': {
          name: 'Optional bench profile',
          role: 'Flexible talent pool option',
          age: 'N/A',
          experience: 'N/A',
          skills: ['Role-fit review needed'],
          history: 'No prior requisition history was surfaced for this option.',
          summary: 'This profile is being kept as an optional bench candidate pending deeper review.',
          answerMap: {
            'what is the candidate age': 'This optional profile does not currently have a recorded age.',
            'how many years of experience': 'This optional profile does not currently have a recorded experience level.',
            'what skills does the candidate have': 'This optional profile is pending skill validation.',
            'what is the hiring history': 'No prior requisition history was surfaced for this option.',
            'why is this candidate optional': 'The team can keep this profile as an optional candidate for later review.'
          }
        }
      };

      const answerQuestion = (question, label) => {
        const profile = internalKnowledgeBase[label] || internalKnowledgeBase['Strong Hire'];
        const normalized = question.trim().toLowerCase();
        const directAnswer = profile.answerMap[normalized];

        if (directAnswer) {
          return directAnswer;
        }

        if (normalized.includes('age')) {
          return profile.answerMap['what is the candidate age'];
        }

        if (normalized.includes('experience')) {
          return profile.answerMap['how many years of experience'];
        }

        if (normalized.includes('skill')) {
          return profile.answerMap['what skills does the candidate have'];
        }

        if (normalized.includes('history') || normalized.includes('prior') || normalized.includes('requisition')) {
          return profile.answerMap['what is the hiring history'];
        }

        if (normalized.includes('fit') || normalized.includes('hire') || normalized.includes('recommend')) {
          return profile.answerMap['why is this candidate a strong hire'] || profile.answerMap['why is this candidate a lean hire'] || profile.answerMap['why is this candidate conflicted'] || profile.answerMap['why is this candidate optional'];
        }

        return `${profile.summary}`;
      };

      const postQuestion = () => {
        const value = input.value.trim();
        if (!value) {
          response.textContent = 'Please enter a question about fit, history, skills, age, or experience.';
          return;
        }
        const selected = document.querySelector('.selection-btn.active');
        const label = selected ? selected.getAttribute('data-label') : 'Strong Hire';
        response.textContent = answerQuestion(value, label);
      };

      sendBtn.addEventListener('click', postQuestion);
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          postQuestion();
        }
      });
    </script>
  </body>
</html>
"""


@app.route("/")
def index() -> str:
    return render_template_string(HTML)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port, debug=True)
