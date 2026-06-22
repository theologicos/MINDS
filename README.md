to run the system, just do this inside the vscode terminal where you placed the files:
python -m venv venv  
pip install -r requirements.txt      

if you ever need to makemigrations, just delete all files inside the migrations except for the "__init__.py"
folders:
minds
|_accounts
|  |_migrations
|_departments
|  |_migrations
|_memos
| |_migrations
|_notifications
|  |_migrations
|_settings_app
  |_migrations

then run these commands:
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser (this creates an account(staff default) to access the admin, then change the user into a superadmin to create more users inside the system)
                                   (go to http://127.0.0.1:8000/admin/ to access the database) 
pythone manage.py runserver
