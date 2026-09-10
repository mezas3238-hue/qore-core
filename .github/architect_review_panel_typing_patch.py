from pathlib import Path

path = Path("src/qore/infrastructure/trader_lab/story_forensics_review_panel.py")
text = path.read_text(encoding="utf-8")
old = '''    subject_type = _text(subject.get("subject_type"), field_name="subject type")
    if subject_type == "episode":
'''
new = '''    subject_type = _text(subject.get("subject_type"), field_name="subject type")
    keys: tuple[str, ...]
    if subject_type == "episode":
'''
if text.count(old) != 1:
    raise SystemExit("expected exactly one subject descriptor typing insertion")
path.write_text(text.replace(old, new), encoding="utf-8")
