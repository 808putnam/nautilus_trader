-- Schema
CREATE SCHEMA IF NOT EXISTS nautilus;

CREATE TABLE IF NOT EXISTS nautilus."currency_pair" (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS nautilus."equity" (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS nautilus."crypto_future" (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS nautilus."crypto_perpetual"(
    id SERIAL PRIMARY KEY
);