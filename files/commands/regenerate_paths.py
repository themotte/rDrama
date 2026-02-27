from sqlalchemy.orm import Session

from files.__main__ import app, db_session


def regenerate_comment_paths(db: Session):
    """
    Regenerate the ltree path column for all comments by walking
    the comment tree level-by-level using the existing level column.

    This is idempotent and can be re-run to fix data issues without
    re-running migrations.
    """
    print("Regenerating comment paths...")

    # Set path for root comments (level=1): path = id
    result = db.execute(
        "UPDATE comments SET path = id::text::ltree WHERE level = 1"
    )
    print(f"Updated {result.rowcount} root comments")

    # Get max level for comments on posts (parent_submission IS NOT NULL)
    max_level_row = db.execute(
        "SELECT MAX(level) FROM comments WHERE parent_submission IS NOT NULL"
    ).fetchone()
    max_level = max_level_row[0] if max_level_row and max_level_row[0] else 1

    # Update each level by joining with the parent to build the path
    for level in range(2, max_level + 1):
        result = db.execute(
            """
            UPDATE comments c
            SET path = p.path || c.id::text
            FROM comments p
            WHERE c.parent_comment_id = p.id AND c.level = :level
            """,
            {"level": level},
        )
        print(f"Updated {result.rowcount} comments at level {level}")

    # Handle DM/notification comments (parent_submission IS NULL) that may still be null
    result = db.execute(
        "UPDATE comments SET path = id::text::ltree WHERE path IS NULL"
    )
    if result.rowcount:
        print(f"Updated {result.rowcount} DM/notification comments with null paths")

    db.commit()
    print("Done regenerating comment paths.")


@app.cli.command("regenerate-comment-paths")
def regenerate_comment_paths_cmd():
    """Regenerate the ltree path column for all comments (idempotent)."""
    regenerate_comment_paths(db_session())
