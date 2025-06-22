CREATE DATABASE IF NOT EXISTS updated_society_maintenance;
USE updated_society_maintenance;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    wing VARCHAR(10),
    role VARCHAR(10) NOT NULL,
    email VARCHAR(100)
);

CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    month VARCHAR(7),
    amount DECIMAL(10,2),
    status VARCHAR(10),
    due_date VARCHAR(10),
    maintenance DECIMAL(10,2),
    water DECIMAL(10,2),
    security DECIMAL(10,2),
    sinking_fund DECIMAL(10,2),
    FOREIGN KEY(user_id) REFERENCES users(id)
);