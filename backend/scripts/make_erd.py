"""Write docs/diagrams/erd_current.mmd from the SQLAlchemy models (so the ERD can never drift from the code).
Render with:  mmdc -i docs/diagrams/erd_current.mmd -o docs/diagrams/erd_current.png -s 2 -b white
"""
import pathlib
import sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.database import Base
import app.models  # noqa: F401
import app.assist.models  # noqa: F401

def short(t):
    s = str(t).split("(")[0].lower()
    return {"varchar": "string", "double_precision": "float", "timestamp": "datetime"}.get(s, s) or "text"

lines = ["erDiagram"]
rels = []
for name, t in sorted(Base.metadata.tables.items()):
    lines.append(f"  {name} {{")
    fks = {c.name for c in t.columns if c.foreign_keys}
    for c in t.columns:
        key = " PK" if c.primary_key else (" FK" if c.name in fks else "")
        lines.append(f"    {short(c.type)} {c.name}{key}")
    lines.append("  }")
    for c in t.columns:
        for fk in c.foreign_keys:
            if c.name == "user_id" and fk.column.table.name == "users":
                continue  # every student-owned table points at users; stated in the figure caption to keep the picture readable
            rels.append(f"  {fk.column.table.name} ||--o{{ {name} : \"{c.name}\"")
lines += sorted(set(rels))
out = pathlib.Path(__file__).resolve().parents[2] / "docs" / "diagrams" / "erd_current.mmd"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(len(Base.metadata.tables), "tables,", len(set(rels)), "relationships ->", out)
