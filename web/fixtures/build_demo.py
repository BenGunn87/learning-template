"""Author the synthetic UI fixture using existing engine write operations.

Run once from the repository root: python -m web.fixtures.build_demo.
The committed demo is ready to read; the viewer never runs this generator.
Existing files are preserved by the engine's create-only operations.
"""

from pathlib import Path
import shutil
import tempfile

from scripts.learning_core import Repository
from scripts.learning_core.yaml_io import create_yaml, load_yaml
from web.data import DEMO_ROOT, PROJECT_ROOT


class DemoRepository(Repository):
    SCHEMAS = {name: PROJECT_ROOT / path for name, path in Repository.SCHEMAS.items()}


def build(root):
    root.mkdir(parents=True, exist_ok=True)
    for directory in (*Repository.REQUIRED_DIRECTORIES, "gaps", "interests", "resources/generated"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    def seed(relative, data):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        create_yaml(path, data)

    # The engine has no onboarding create command for these four documents.
    seed("learning.yaml", {"format_version": 1, "topic": {"id": "demo-data-systems", "title": "Data Systems · DEMO"}, "learning_core": {"version": "0.7.0"}, "created_at": "2026-10-01"})
    seed("config/context.yaml", {
        "format_version": 1,
        "goal": {"why": "professional-growth", "outcome": "Explore a synthetic Knowledge Map."},
        "experience": {"level": "beginner"}, "depth": "working",
        "constraints": {"default_session_minutes": 25},
        "preferences": {"languages": ["en"], "resources": ["documentation"]},
        "diagnostic": {"status": "completed", "completed_at": "2026-10-01", "areas": [{"area": "Data Systems", "level": "unknown"}]},
    })
    seed("config/settings.yaml", load_yaml(PROJECT_ROOT / "config/settings.yaml"))
    nodes = [
        ("data-systems", "Data Systems", "area", "Хранение, обработка и согласованность данных."),
        ("indexing", "Indexing", "topic", "Как индексы ускоряют чтение и влияют на запись."),
        ("transactions", "Transactions", "topic", "Границы атомарности и изоляция конкурентных операций."),
        ("query-planning", "Query Planning", "topic", "Выбор способа выполнения запроса."),
        ("btree", "B-tree", "concept", "Один Graph Node с двумя родителями: Indexing и Query Planning."),
        ("isolation", "Isolation Levels", "concept", "Какие эффекты конкурентного выполнения разрешены."),
        ("caching", "Caching", "topic", "Сохранённый Progress verified на связанной Unit."),
        ("latency", "Latency", "concept", None),
        ("loop-a", "Hierarchy Loop A", "topic", "Цикл, достижимый из обычного корня."),
        ("loop-b", "Hierarchy Loop B", "concept", "Раскрытие возвращает ссылку на уже встреченный узел."),
        ("cycle-a", "Rootless Cycle A", "topic", "Компонента без корня показывается отдельно."),
        ("cycle-b", "Rootless Cycle B", "concept", "Часть циклической компоненты без корня."),
        ("cycle-c", "Rootless Cycle C", "concept", "Замыкает цикл без корня."),
        ("cycle-leaf", "Cycle Leaf", "concept", "Потомок циклической компоненты тоже доступен."),
    ]
    relationships = [
        ("indexing", "data-systems", "part-of"), ("transactions", "data-systems", "part-of"),
        ("query-planning", "data-systems", "part-of"), ("caching", "data-systems", "part-of"),
        ("btree", "indexing", "part-of"), ("btree", "query-planning", "part-of"),
        ("isolation", "transactions", "part-of"),
        ("loop-a", "indexing", "part-of"), ("loop-b", "loop-a", "part-of"), ("loop-a", "loop-b", "part-of"),
        ("cycle-a", "cycle-b", "part-of"), ("cycle-b", "cycle-c", "part-of"), ("cycle-c", "cycle-a", "part-of"),
        ("cycle-leaf", "cycle-b", "part-of"),
        ("btree", "isolation", "prerequisite"), ("indexing", "query-planning", "related"),
    ]
    seed("map/graph.yaml", {"format_version": 1,
        "nodes": [{"id": key, "title": title, "type": kind, **({"summary": summary} if summary else {})} for key, title, kind, summary in nodes],
        "edges": [{"from": source, "to": target, "type": kind} for source, target, kind in relationships],
    })
    frontier_units = [
        ("indexing-basics", "Indexing Basics", ["indexing", "btree"]),
        ("transaction-isolation", "Choose an Isolation Level", ["transactions", "isolation"]),
        ("query-plan", "Read a Query Plan", ["query-planning"]),
        ("cache-policy", "Choose a Cache Policy", ["caching"]),
        ("cycle-navigation", "Explore a Rootless Component", ["cycle-a"]),
        ("transactions-basics", "Transaction Boundaries", ["transactions"]),
        ("cache-basics", "Caching Basics", ["caching"]),
    ]
    seed("map/frontier.yaml", {"format_version": 1, "focus": {"primary": "data-systems", "secondary": []}, "units": [
        {"id": key, "title": title, "nodes": node_ids, "goal": "Демонстрационная запланированная Unit.", "estimated_minutes": 20, "priority": "medium", "routing_reasons": [{"type": "primary-route"}]}
        for key, title, node_ids in frontier_units
    ]})
    repository = DemoRepository(root)
    unit_definitions = [
        ("indexing-basics", "Indexing Basics", ["indexing", "btree"], "Объяснить стоимость чтения и записи при использовании B-tree индекса."),
        ("transactions-basics", "Transaction Boundaries", ["transactions"], "Определить границы атомарной операции."),
        ("cache-basics", "Caching Basics", ["caching"], "Выбрать срок жизни и политику обновления кеша."),
        ("btree-cost", "Estimate B-tree Cost", ["btree"], "Сравнить индексное чтение с полным сканированием. Unit ещё без Progress."),
    ]
    for key, title, node_ids, goal in unit_definitions:
        repository.create_unit({
            "format_version": 1, "id": key, "title": title, "nodes": node_ids, "goal": goal,
            "estimated_minutes": 20, "concepts": [title],
            "study_focus": ["Механизм и ограничения.", "Применение к конкретному сценарию."],
            "practice": {"type": "scenario", "goal": goal},
            "verification": {dimension: {"enabled": True} for dimension in ("recall", "understanding", "application")},
        })

    def attempt(unit_id, node_ids, day, result, previous=None):
        _, session = repository.create_session(unit_id, 25, f"{day}T10:00:00+05:00")
        kind = "practice" if previous else "initial"
        evidence_id = f"{session['id']}-{kind}"
        evidence = {
            "format_version": 1, "id": evidence_id, "unit": unit_id, "session": session["id"],
            "type": kind, "created_at": f"{day}T10:20:00+05:00",
            "takeaways": ["Synthetic UI demonstration; not evidence about a real learner."], "observations": [],
            "practice": {"prompt": f"Synthetic {kind} scenario for {unit_id} on {day}.", "answer": "Synthetic demonstration answer."},
        }
        if previous:
            evidence.update({"target": {"dimension": "application"}, "based_on": {"evidence": previous}})
        else:
            evidence.update({"resources": [{"title": "Synthetic demo notes", "url": "https://example.com/demo", "type": "external", "format": "article", "language": "en"}],
                "recall": {"prompts": [f"Explain {unit_id}."], "answers": ["Synthetic demonstration answer."]}})
            repository.update_checkpoint(session["id"], {
                "unit": unit_id, "action": "study", "stage": "takeaways",
                "completed_steps": {"mode_selected": True, "resources_prepared": True, "study_focus_shown": True,
                    "study_completed": True, "recall_completed": True, "practice_completed": True},
                "study_mode": "external", "resources": [{**resource, "status": "completed"} for resource in evidence["resources"]],
            }, f"{day}T10:18:00+05:00", "completed")
        repository.create_evidence(evidence)
        repository.create_assessment({
            "format_version": 1, "id": f"{evidence_id}-assessment", "evidence": evidence_id, "type": kind,
            "created_at": f"{day}T10:22:00+05:00", "result": result,
            "evaluated": {dimension: {"nodes": node_ids} for dimension in (["application"] if previous else result)},
            "gaps": ["Synthetic learning gap."] if any(grade in {"failed", "hard"} for grade in result.values()) else [],
            "summary": "Synthetic assessment for UI demonstration.",
        })
        repository.rebuild_progress()
        repository.complete_session(session["id"], [evidence_id], f"{day}T10:25:00+05:00")
        return evidence_id

    result = {"recall": "good", "understanding": "good", "application": "hard"}
    first = attempt("indexing-basics", ["indexing", "btree"], "2026-10-01", result)
    attempt("indexing-basics", ["indexing", "btree"], "2026-10-02", result, first)
    attempt("transactions-basics", ["transactions"], "2026-10-03", {"recall": "failed", "understanding": "hard", "application": "good"})
    attempt("cache-basics", ["caching"], "2026-10-04", {"recall": "good", "understanding": "good", "application": "easy"})


def main():
    # Build in isolation. Publish only after engine operations have succeeded;
    # never replace differing fixture files or touch the real learning data.
    with tempfile.TemporaryDirectory(prefix="learning-web-demo-") as temporary:
        root = Path(temporary)
        build(root)
        for source in root.rglob("*"):
            if source.is_file():
                target = DEMO_ROOT / source.relative_to(root)
                if target.exists() and target.read_bytes() != source.read_bytes():
                    raise SystemExit(f"Refusing to overwrite existing fixture: {target}")
        shutil.copytree(root, DEMO_ROOT, dirs_exist_ok=True)
    print("Created synthetic demo with engine-authored Units, Evidence, Assessments, Gaps and Progress.")


if __name__ == "__main__":
    main()
