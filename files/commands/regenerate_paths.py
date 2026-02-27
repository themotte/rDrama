from sqlalchemy.orm import Session

from files.__main__ import app, db_session


def regenerate_comment_paths(db: Session):
    """
    Regenerate the ltree path column for all comments by walking the tree
    using parent_comment_id (not level, which may be wrong).

    This is idempotent and can be re-run to fix data issues without
    re-running migrations.
    """
    print("Regenerating comment paths...")

    # Set path for root comments (no parent comment)
    result = db.execute(
        "UPDATE comments SET path = id::text::ltree WHERE parent_comment_id IS NULL"
    )
    print(f"Updated {result.rowcount} root comments")

    # Iteratively set path for children by joining with parent.
    # Each pass handles one more level of depth. We loop until no rows change.
    iteration = 0
    while True:
        result = db.execute("""
            UPDATE comments c
            SET path = p.path || c.id::text
            FROM comments p
            WHERE c.parent_comment_id = p.id
              AND (c.path IS NULL OR c.path IS DISTINCT FROM p.path || c.id::text)
              AND p.path IS NOT NULL
        """)
        iteration += 1
        print(f"  Pass {iteration}: updated {result.rowcount} child comments")
        if result.rowcount == 0:
            break

    db.commit()
    print("Done regenerating comment paths.")


def regenerate_comment_levels(db: Session):
    """
    Regenerate the level column for all comments from the path column.

    Requires path to be correct first — run regenerate_comment_paths() if unsure.
    level = nlevel(path) in ltree, i.e. the number of segments in the path.
    """
    print("Regenerating comment levels from path...")
    result = db.execute("UPDATE comments SET level = nlevel(path)")
    print(f"Updated {result.rowcount} comments")
    db.commit()
    print("Done regenerating comment levels.")


@app.cli.command("regenerate-comment-paths")
def regenerate_comment_paths_cmd():
    """Regenerate the ltree path column for all comments (idempotent)."""
    regenerate_comment_paths(db_session())


@app.cli.command("regenerate-comment-levels")
def regenerate_comment_levels_cmd():
    """Regenerate the level column from the ltree path column (idempotent).

    Run regenerate-comment-paths first if path may also be wrong.
    """
    regenerate_comment_levels(db_session())
