# Face-Recognition-Python

### STEPS

PART 1 : MONGO DB SETUP
1. Create MongoDB cLuster with name "Face-Recognition".
2. Create a database with name "Face-Recognition" under the cluster.
3. Add collections "Admin", "Civilian", "Criminal", "Police", "Record" to the database.
4. Refer Screenshot 1.

PART 2 : BACKEND SETUP
1. Get into requirements directory, install CMake and add to path.
2. pip install <DLIB FILE NAME CORRESPONDING TO PYTHON VERSION FROM REQUIREMENTS DIRECTORY>
3. pip install -r requirements.txt

PART 3 : RUN APPLICATION
1. python app.py
2. Open localhost:80 in a browser.
3. Get into localhost:80/addCivilian and add a civilian data. Civilian ID of this first civilian is "C1".
4. Civilian will be added to database. Refer Screenshot 2.
5. Manually add a record to the "Admin" collection in the database with the details shown in Screenshot 3.
6. Now, Admin Login username is "A1" and password is "admin".
7. Create new police account with civilian ID as "C1" and some password.
8. Now, use the Police ID "P1" as username and password as chosen to login to first police account.
9. From the police account, new civilians can be added.

### Tech Stack Used : Python Flask framework, MongoDB, HTML, CSS, JavaScript
