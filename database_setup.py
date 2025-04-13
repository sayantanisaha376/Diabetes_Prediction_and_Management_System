import sqlite3
import csv

def create_database_from_csv(csv_file_path):
    conn = sqlite3.connect('csv_database.db')
    cur = conn.cursor()
    
    # Create a table based on the CSV file structure
    cur.execute('''CREATE TABLE IF NOT EXISTS diabetes_data (
        Pregnancies INTEGER,
        Glucose REAL,
        BloodPressure REAL,
        SkinThickness REAL,
        Insulin REAL,
        BMI REAL,
        DiabetesPedigreeFunction REAL,
        Age INTEGER,
        Outcome INTEGER
    )''')
    
    # Read data from CSV file and insert into the database
    with open(csv_file_path, 'r') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # Skip header row
        for row in csv_reader:
            cur.execute('''INSERT INTO diabetes_data 
                (Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', row)
    
    conn.commit()
    conn.close()
    print("Database created and data inserted successfully!")

if __name__ == "__main__":
    # Replace 'diabetes.csv' with the path to your uploaded CSV file
    create_database_from_csv('diabetes.csv')