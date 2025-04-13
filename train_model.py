import numpy as np
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def train_model():
    # Load dataset from the uploaded CSV file
    df = pd.read_csv('diabetes.csv')  # Make sure 'diabetes.csv' is your uploaded file name

    # Selecting relevant features and target variable
    X = df[['Age', 'BMI', 'Glucose', 'Insulin']]
    y = df['Outcome']  # 0: No Diabetes, 1: Diabetes

    # Splitting data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Model Accuracy: {accuracy * 100:.2f}%')

    # Save trained model
    with open('diabetes_model.pkl', 'wb') as model_file:
        pickle.dump(model, model_file)

    print("Model trained and saved successfully!")

if __name__ == "__main__":
    train_model()