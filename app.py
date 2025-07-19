import os
from datetime import date, datetime
from typing import Optional

import pymysql
from flask import Flask, jsonify, request
from pydantic import BaseModel, EmailStr, Field, ValidationError

###############################################################################
# Database configuration – copy your Aiven creds here or set env‑vars
###############################################################################
DB_OPTS = dict(
    host=os.getenv("MYSQL_HOST", "mysql-499fde8-readyfitgym-1ce8.c.aivencloud.com"),
    port=int(os.getenv("MYSQL_PORT", 28734)),
    user=os.getenv("MYSQL_USER", "avnadmin"),
    password=os.getenv("MYSQL_PASSWORD", "AVNS_mePxM_vVe-qTy3gflAf"),
    db=os.getenv("MYSQL_DB", "defaultdb"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=10,
    read_timeout=10,
    write_timeout=10,
    autocommit=True,         # commit after every statement
)

###############################################################################
# Pydantic model that matches your JSON
###############################################################################
class Member(BaseModel):
    name: str
    dob: date
    age: int = Field(..., ge=0)
    date_of_joining: date
    height: float = Field(..., ge=0)
    weight: float = Field(..., ge=0)
    occupation: str
    address: str
    email: EmailStr
    phone: str
    alternate_phone: Optional[str]
    looking_for: str
    membership_mode: str
    end_of_membership: date
    physical_problems: str
    physicalDescription: Optional[str]
    fractures: str
    fractureDescription: Optional[str]
    agreed_to_terms: bool
    photo: Optional[str]  # base64-encoded image string
    submitted_at: datetime

###############################################################################
# Helpers
###############################################################################
def get_conn():
    """Open a new DB connection (pymysql has built‑in pooling)."""
    return pymysql.connect(**DB_OPTS)

def ensure_table_exists():
    """Run once at startup to create the members table."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS memberss (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name               VARCHAR(255),
        dob                DATE,
        age                INT,
        date_of_joining    DATE,
        height             FLOAT,
        weight             FLOAT,
        occupation         VARCHAR(100),
        address            VARCHAR(255),
        email              VARCHAR(255),
        phone              VARCHAR(50),
        alternate_phone    VARCHAR(50),
        looking_for        VARCHAR(100),
        membership_mode    VARCHAR(50),
        end_of_membership  DATE,
        physical_problems  VARCHAR(3),
        physicalDescription VARCHAR(255),
        fractures           VARCHAR(3),
        fractureDescription VARCHAR(255),
        agreed_to_terms    BOOLEAN,
        photo              LONGTEXT,
        submitted_at       DATETIME
    )  ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(create_sql)

###############################################################################
# Flask app
###############################################################################
# {"error":"(1054, \"Unknown column 'photo' in 'field list'\")"}
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This enables CORS for all origins and all routes

ensure_table_exists()


@app.route("/members", methods=["POST"])
def add_member():
    try:
        data = request.get_json(force=True)
        member = Member(**data)          # validate
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    insert_sql = """
    INSERT INTO memberss
        (name, dob, age, date_of_joining, height, weight, occupation, address,
         email, phone, alternate_phone, looking_for, membership_mode,
         end_of_membership, physical_problems, physicalDescription,
         fractures, fractureDescription, agreed_to_terms, photo, submitted_at)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s,
         %s, %s, %s,
         %s, %s, %s, %s, %s)
    """
    values = (
        member.name,
        member.dob,
        member.age,
        member.date_of_joining,
        member.height,
        member.weight,
        member.occupation,
        member.address,
        member.email,
        member.phone,
        member.alternate_phone,
        member.looking_for,
        member.membership_mode,
        member.end_of_membership,
        member.physical_problems,
        member.physicalDescription,
        member.fractures,
        member.fractureDescription,
        member.agreed_to_terms,
        member.photo,
        member.submitted_at,
    )

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(insert_sql, values)
            member_id = cur.lastrowid
        return jsonify({"id": member_id}), 201
    except pymysql.err.IntegrityError as ie:
        # duplicate email or other constraint violation
        return jsonify({"error": str(ie)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/members/<int:member_id>", methods=["GET"])
def get_member(member_id):
    select_sql = "SELECT * FROM memberss WHERE id = %s"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(select_sql, (member_id,))
        row = cur.fetchone()

    if not row:
        return jsonify({"error": "Member not found"}), 404

    # Convert date/datetime objects to ISO strings for JSON
    for k, v in row.items():
        if isinstance(v, (date, datetime)):
            row[k] = v.isoformat()
    return jsonify(row)

@app.route("/list", methods=["GET"])
def get_all_members():
    select_sql = "SELECT * FROM memberss"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(select_sql)
        rows = cur.fetchall()

    # Convert date/datetime objects to ISO strings for JSON
    for row in rows:
        for k, v in row.items():
            if isinstance(v, (date, datetime)):
                row[k] = v.isoformat()
    return jsonify(rows)

if __name__ == "__main__":
    # app.run(debug=True, port=5000)/
     app.run(host="0.0.0.0", port=5000) 
