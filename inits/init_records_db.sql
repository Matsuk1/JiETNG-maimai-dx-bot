CREATE DATABASE IF NOT EXISTS records
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE records;

CREATE TABLE IF NOT EXISTS best_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64),

    `name` VARCHAR(100),
    difficulty VARCHAR(20),
    kind VARCHAR(10),
    score VARCHAR(20),
    `dx-score` VARCHAR(20),
    `score-icon` VARCHAR(10),
    `combo-icon` VARCHAR(10),
    `dx-icon` VARCHAR(10),
    internalLevelValue DECIMAL(3,1),
    version VARCHAR(20),
    version_title VARCHAR(50),
    ra INT,
    id_in_songlist INT,
    url TEXT,

    INDEX(user_id)
);

CREATE TABLE IF NOT EXISTS recent_records LIKE best_records;
