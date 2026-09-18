# Allocate Minutes — fixed frontend wiring

## Clean filenames
index.html
landing.css
script.js
logo.png
login.html
signup.html
auth.css
auth.js
planner.html
planner.css
planner.js
plan.html
plan.js
quiz.html
quiz.js
style.css
student.csv

## Main fixes
- index(8).html -> index.html
- script(2).js -> script.js
- style(3).css -> style.css
- users.csv -> student.csv
- auth.js now fetches student.csv
- landing page loads auth.js
- Sign In routes to login.html
- dashboard loads auth.js and uses the logged-in student's name
- dashboard Adaptive Quiz button routes to quiz.html
- plan/quiz use the logged-in student's ID instead of hardcoded S001/Aarav
- plan/quiz Dashboard links route to planner.html
- plan/quiz load auth.js before their page scripts

## Important dataset requirement
For login to work directly from student.csv, it needs authentication fields compatible with:
user_id OR student_id, name, email, username, password, grade, avatar

The student.csv included in this package is the CSV that was uploaded in chat,
renamed to student.csv. Replace it with the teammate's real student.csv.
If that real file has different columns, auth.js must be mapped to that schema.
