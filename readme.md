
[![Build status](https://img.shields.io/github/workflow/status/TheMotte/rDrama/run_tests.py/frost)](https://github.com/TheMotte/rDrama/actions?query=workflow%3Arun_tests.py+branch%3Afrost)

This code runs https://www.themotte.org .

# Installation (Windows/Linux/MacOS)

1 - Install Docker on your machine.

[Docker installation](https://docs.docker.com/get-docker/)

2 - If hosting on localhost and/or without HTTPS, change```"SESSION_COOKIE_SECURE"``` in ```__main__.py``` to "False"

3 - Run the following commands in the terminal:

```
git clone https://github.com/themotte/rDrama/

cd rDrama

docker-compose up
```

4 - That's it! Visit `localhost` in your browser.

5 - Optional: to change the domain from "localhost" to something else and configure the site settings, as well as integrate it with the external services the website uses, please edit the variables in the `env` file and then restart the docker container.

# Run the E2E tests:

`./run_tests.py`

# Database Stuff

## What is a migration?

Prior to the fork of themotte from rDrama, there were no database migrations, and the database schema was stored in `schema.sql`. Any time a column or such was added to a model, one hoped that the author remembered to update `schema.sql` to add that column. One of the first changes we made after forking this repo was to add database migrations using Alembic.

Database migrations are instructions for how to convert an out-of-date database into an up-to-date database. This can involve changing the schema, or changing data within the database.

## Why use database migrations

Database migrations allow us to specify where data moves when there are schema changes. This is important when we're live -- if we rename the `comments.ban\_reason` column to `comments.reason\_banned` for naming consistency or whatever, and we do this by dropping the `ban\_reason` column and adding a `reason\_banned` column, we will lose all user data in that column. We don't want to do this. With migrations, we could instead specify that the operation in question should be a column rename, or, if the database engine does not support renaming columns, that we should do a three-step process of "add new column, migrate data over, drop old column".

## Database schema change workflow

As an example, let's say we want to add a column `is\_filtered` to the `comments` table.

1. Update the `Comment` model in `files/classes/comment.py`
```python
	from files.__main__ import Base
	class Comment(Base):
		__tablename__ = "comments"
		id = Column(Integer, primary_key=True)
		...
+		is_flagged = Column(Boolean, default=False, nullable=False)
```
2. Autogenerate a migration with a descriptive message. To do this, run
```sh
flask db revision --autogenerate --message="add is_flagged field to comments"
```
from the flask server within the directory the flask app is being served from, with an env var of `FLASK\_APP="files/cli:app"`. If you are running flask using `docker-compose` as described above, this looks like
```sh
docker-compose exec -T files bash -c 'cd /service/; FLASK_APP="files/cli:app" flask "$@"' . db revision --autogenerate --message="add is_flagged field to comments"
```
This will create a migration in the `migrations/versions` directory with a name like `migrations/versions/2022\_05\_23\_05\_38\_40\_9c27db0b3918\_add\_is\_flagged\_field\_to\_comments.py` and content like
```python
"""add is_flagged field to comments
Revision ID: 9c27db0b3918
Revises: 16d6335dd9a3
Create Date: 2022-05-23 05:38:40.398762+00:00
"""
from alembic import op
import sqlalchemy as sa
# revision identifiers, used by Alembic.
revision = '9c27db0b3918'
down_revision = '16d6335dd9a3'
branch_labels = None
depends_on = None
def upgrade():
    op.add_column('comments', sa.Column('is_flagged', sa.Boolean(), nullable=False))
def downgrade():
    op.drop_column('comments', 'is_flagged')
```

3. Examine the autogenerated migration to make sure that everything looks right (it adds the column you expected it to add and nothing else, all constraints are named, etc. If you see a `None` in one of the alembic operations, e.g. `op.create\_foreign\_key\_something(None, 'usernotes', 'users', ['author\_id'])`, please replace it with a descriptive string before you commit the migration).
4. Run the migration to make sure it works. You can run a migration with the command
```sh
flask db upgrade
```
which, if you're using the docker-compose, looks like
```sh
docker-compose exec -T files bash -c 'cd /service/; FLASK_APP="files/cli:app" flask "$@"' . db upgrade
```

## Running migrations someone else checked in

If another dev made schema changes, and you just merged them in, you can get your local database up to date with the changes by running
```sh
docker-compose exec -T files bash -c 'cd /service/; FLASK\_APP="files/cli:app" flask db upgrade
```
You should not have to reboot your container, though it might be a good idea to do so anyway if the changes you are merging in are nontrivial (particularly if there have been changes to `docker-compose.yml` or `Dockerfile`).

## So what's up with schema.sql, can I just change that?

No, please do not do that. Instead, please make a migration as described above.
