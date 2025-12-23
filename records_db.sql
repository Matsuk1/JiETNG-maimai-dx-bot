CREATE DATABASE IF NOT EXISTS maimai_records
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE maimai_records;

CREATE TABLE IF NOT EXISTS best_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64),

    `name` VARCHAR(255),
    difficulty VARCHAR(20),
    type VARCHAR(10),
    score VARCHAR(20),
    `dx_score` VARCHAR(20),

    `score_icon` VARCHAR(10),
    `combo_icon` VARCHAR(10),
    `sync_icon` VARCHAR(10),

    INDEX(user_id)
);

CREATE TABLE IF NOT EXISTS recent_records LIKE best_records;
