"""
The built-in sample Learning Pack. It was written by hand for MindSync (about databases), NOT produced by an AI, and the page says so.
It lets anyone try quizzes, flashcards and revision without any account setup or AI provider.
"""
SAMPLE_TITLE = "Sample pack: Introduction to databases"
SAMPLE_NOTE = "This sample was written by hand for MindSync. It is not made by AI. Upload your own notes to build a pack from your material once AI is switched on."

LESSONS = [
    {"title": "What a database is", "summary": "A database stores organised data so that many people and programs can find, add, change and protect it reliably.",
     "key_points": ["A database is organised data kept for later use; a spreadsheet on one laptop is the smallest example.",
                    "A database management system (DBMS), such as PostgreSQL, is the software that stores the data and answers requests.",
                    "A relational database keeps data in tables made of rows (records) and columns (fields).",
                    "A good DBMS keeps data correct when many users change it at the same time."]},
    {"title": "Keys and relationships", "summary": "Keys identify rows and link tables together, which avoids repeating the same facts in many places.",
     "key_points": ["A primary key uniquely identifies each row in a table, for example a student number.",
                    "A foreign key is a column that holds the primary key of another table, creating a link between the two.",
                    "One student can enrol on many courses and one course has many students: this is a many-to-many relationship, usually stored in a third table.",
                    "Splitting data into linked tables to remove repetition is called normalisation."]},
    {"title": "Asking questions with SQL", "summary": "SQL is the standard language for reading and changing data in a relational database.",
     "key_points": ["SELECT reads rows; WHERE keeps only the rows that match a condition.",
                    "INSERT adds rows, UPDATE changes rows and DELETE removes rows.",
                    "JOIN combines rows from two tables using matching key values.",
                    "A transaction groups changes so that either all of them are saved or none of them are (commit or rollback)."]},
]

QUESTIONS = [
    {"difficulty": "easy", "lesson": 0, "question": "What does a DBMS do?", "options": ["It draws charts from spreadsheets", "It stores data and answers requests for it", "It makes websites look attractive", "It sends emails to users"],
     "answer_index": 1, "explanation": "A database management system is the software that stores the data and handles requests such as reading and changing it."},
    {"difficulty": "easy", "lesson": 0, "question": "In a relational database, what is a row?", "options": ["One record in a table", "A column heading", "A password", "A whole database"],
     "answer_index": 0, "explanation": "Tables are made of rows (records) and columns (fields). One row holds the facts about one thing."},
    {"difficulty": "easy", "lesson": 1, "question": "What is a primary key?", "options": ["A password for the database", "A column that uniquely identifies each row", "The first column in every table", "A copy of another table"],
     "answer_index": 1, "explanation": "A primary key value is different for every row, so it can be used to find exactly one row."},
    {"difficulty": "easy", "lesson": 2, "question": "Which SQL word reads data from a table?", "options": ["INSERT", "DELETE", "SELECT", "UPDATE"],
     "answer_index": 2, "explanation": "SELECT reads rows. INSERT, UPDATE and DELETE change the data."},
    {"difficulty": "medium", "lesson": 1, "question": "A column in the Enrolment table holds a student number taken from the Student table. What is this column?", "options": ["A primary key of Enrolment", "A foreign key", "An index", "A transaction"],
     "answer_index": 1, "explanation": "A column that holds the primary key of another table is a foreign key. It links the two tables."},
    {"difficulty": "medium", "lesson": 1, "question": "Students can join many courses and each course has many students. How is this usually stored?", "options": ["In a third table that links students and courses", "By repeating course names in the Student table", "In one very wide column", "It cannot be stored in a relational database"],
     "answer_index": 0, "explanation": "A many-to-many relationship is stored in a linking table that holds one row for each student and course pair."},
    {"difficulty": "medium", "lesson": 2, "question": "Which statement keeps only the students older than 20?", "options": ["SELECT * FROM students JOIN age > 20", "SELECT * FROM students WHERE age > 20", "DELETE * FROM students WHERE age > 20", "UPDATE students SET age > 20"],
     "answer_index": 1, "explanation": "WHERE filters the rows that SELECT returns. The other statements either change data or are not valid SQL."},
    {"difficulty": "hard", "lesson": 2, "question": "A transfer subtracts money from account A and adds it to account B. The server crashes after the first step. Which feature prevents money from disappearing?", "options": ["An index on account A", "Normalisation", "A transaction that is rolled back if it did not finish", "A longer primary key"],
     "answer_index": 2, "explanation": "A transaction makes both steps succeed together or not at all. After the crash the half-finished transaction is rolled back."},
    {"difficulty": "hard", "lesson": 1, "question": "A table repeats the lecturer's address on every course row. What problem does this cause, and what is the usual fix?", "options": ["It is too fast; add a primary key", "The address can become inconsistent when changed; move lecturers to their own table and link with a foreign key", "It uses too few columns; add more columns", "Nothing, this is the recommended design"],
     "answer_index": 1, "explanation": "Repeated facts must be edited in many rows, so some are forgotten. Normalisation stores the address once and links to it."},
    {"difficulty": "hard", "lesson": 0, "question": "Why can a shared spreadsheet on a laptop be a poor choice compared with a DBMS for a busy student website?", "options": ["Spreadsheets cannot store text", "A DBMS handles many users changing data at the same time and keeps it correct", "A DBMS never needs backups", "Spreadsheets cannot have columns"],
     "answer_index": 1, "explanation": "A DBMS is designed for many simultaneous users and for keeping data consistent. Backups are still needed."},
]

CARDS = [
    ("Database", "Organised data stored so that it can be found, added, changed and protected."),
    ("DBMS", "Database management system: the software that stores the data and answers requests, for example PostgreSQL."),
    ("Row (record)", "One entry in a table that holds the facts about one thing."),
    ("Column (field)", "One kind of fact stored for every row, such as name or date of birth."),
    ("Primary key", "A column (or columns) whose value is different in every row, used to identify exactly one row."),
    ("Foreign key", "A column that holds the primary key of another table and so links the two tables."),
    ("Normalisation", "Splitting data into linked tables so that each fact is stored once."),
    ("SELECT ... WHERE", "Reads rows from a table and keeps only the rows that match the condition."),
    ("JOIN", "Combines rows from two tables where their key values match."),
    ("Transaction", "A group of changes that are saved together (commit) or all cancelled (rollback)."),
]


def sample_payload() -> dict:
    """The sample in the same shape the AI result is validated into, so one saving routine serves both."""
    return {"title": SAMPLE_TITLE, "lessons": LESSONS, "questions": QUESTIONS,
            "cards": [{"front": f, "back": b, "lesson": None} for f, b in CARDS]}
