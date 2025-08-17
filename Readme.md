for all team qrs : http://localhost:5000/admin/generate-qrs?token=admin123

step 1 : python import_teams.py
or  
step 2 : python manage.py import-teams 


step 3 : python manage.py generate-qrs --base-url http://127.0.0.1:5000
step 4 : python app.py