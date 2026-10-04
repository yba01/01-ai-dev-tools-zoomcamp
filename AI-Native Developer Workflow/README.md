# 01-ai-dev-tools-zoomcamp

## Run the household chores app

From the project root, install the dependencies, create the database, and seed the demo members:

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py seed_members
./.venv/bin/python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Use the mode switch to work as the organizer or select a sample member. Demo modes are not authentication or access control.