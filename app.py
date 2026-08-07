import os
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for
import pymysql

app = Flask(__name__)
app.secret_key = "hotel_secret_key"

# ===========================
# DATABASE CONNECTION
# ===========================

connection = pymysql.connect(
    host="localhost",
    user="root",
    password="",      # Change if your MySQL has a password
    database="hotel_billing",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True
)


# ===========================
# LOGIN
# ===========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:

            session["user"] = user["fullname"]

            return redirect(url_for("dashboard"))

        else:

            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")


# ===========================
# DASHBOARD
# ===========================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    # Total Food Items
    cursor.execute("""
        SELECT COUNT(*) AS total_food
        FROM food_items
    """)
    total_food = cursor.fetchone()["total_food"]

    # Today's Bills
    cursor.execute("""
        SELECT COUNT(*) AS total_bills
        FROM bills
        WHERE bill_date = CURDATE()
    """)
    total_bills = cursor.fetchone()["total_bills"]

    # Today's Sales
    cursor.execute("""
        SELECT COALESCE(SUM(total),0) AS sales
        FROM bills
        WHERE bill_date = CURDATE()
    """)
    row = cursor.fetchone()
    today_sales = float(row["sales"] or 0)

    # Today's Expense
    cursor.execute("""
        SELECT COALESCE(SUM(amount),0) AS expense
        FROM expenses
        WHERE expense_date = CURDATE()
    """)
    row = cursor.fetchone()
    today_expense = float(row["expense"] or 0)

    # Today's Profit
    today_profit = today_sales - today_expense

    cursor.close()

    return render_template(
        "dashboard.html",
        user=session["user"],
        total_food=total_food,
        total_bills=total_bills,
        today_sales=today_sales,
        today_profit=today_profit
    )

# ===========================
# FOOD MANAGEMENT
# ===========================

@app.route("/food")
def food():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM food_items
        ORDER BY category, food_name
    """)

    foods = cursor.fetchall()

    cursor.close()

    return render_template("food.html", foods=foods)


# ===========================
# ADD FOOD
# ===========================

@app.route("/add_food", methods=["POST"])
def add_food():

    if "user" not in session:
        return redirect("/")

    category = request.form["category"]
    food_name = request.form["food_name"]
    price = request.form["price"]

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO food_items(category,food_name,price)
        VALUES(%s,%s,%s)
    """, (category, food_name, price))

    cursor.close()

    return redirect("/food")

# ===========================
# DELETE FOOD
# ===========================
@app.route("/delete_food/<int:id>")
def delete_food(id):
    cursor = connection.cursor()
    # Check whether the food item is used in any bill
    cursor.execute(
        "SELECT COUNT(*) AS total FROM bill_items WHERE food_id=%s",
        (id,)
    )
    used = cursor.fetchone()["total"]
    if used > 0:
        cursor.close()
        return "Cannot delete. Food item already exists in previous bills."
    cursor.execute(
        "DELETE FROM food_items WHERE id=%s",
        (id,)
    )
    connection.commit()
    cursor.close()
    return redirect("/food")
# ===========================
# BREAKFAST BILLING
# ===========================

@app.route("/breakfast")
def breakfast():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM food_items
        WHERE category='Breakfast'
        ORDER BY food_name
    """)

    foods = cursor.fetchall()

    cursor.close()

    return render_template(
        "breakfast.html",
        foods=foods
    )


# ===========================
# GENERATE BILL
# ===========================

@app.route("/generate_bill", methods=["POST"])
def generate_bill():

    if "user" not in session:
        return redirect("/")

    bill_data = request.form["bill_data"]
    payment_mode = request.form["payment_mode"]
    category = request.form["category"]

    items = json.loads(bill_data)

    cursor = connection.cursor()

    total = 0

    for item in items:
        total += float(item["price"]) * int(item["quantity"])

    # Get the last bill number
    cursor.execute("""
    SELECT bill_no
    FROM bills
    ORDER BY id DESC
    LIMIT 1
    """)

    last_bill = cursor.fetchone()

    if last_bill:

        last_number = int(last_bill["bill_no"].replace("HAV", ""))

        new_number = last_number + 1

    else:

        new_number = 1

    bill_no = f"HAV{new_number:03d}"

    cursor.execute("""
        INSERT INTO bills
        (bill_no,total,payment_mode,bill_date,bill_time)
        VALUES(%s,%s,%s,CURDATE(),CURTIME())
    """,(bill_no,total,payment_mode))

    bill_id = cursor.lastrowid

    for item in items:

        subtotal = float(item["price"]) * int(item["quantity"])

        cursor.execute("""
            INSERT INTO bill_items
            (bill_id,food_id,quantity,price,subtotal)
            VALUES(%s,%s,%s,%s,%s)
        """,
        (
            bill_id,
            item["food_id"],
            item["quantity"],
            item["price"],
            subtotal
        ))

    cursor.close()

    return redirect(url_for(
    "invoice",
    bill_id=bill_id,
    category=category
))
@app.route("/invoice/<int:bill_id>/<category>")
def invoice(bill_id, category):

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM bills WHERE id=%s",
        (bill_id,)
    )

    bill = cursor.fetchone()

    cursor.execute("""
        SELECT
            bill_items.quantity,
            bill_items.price,
            bill_items.subtotal,
            food_items.food_name
        FROM bill_items
        INNER JOIN food_items
        ON bill_items.food_id = food_items.id
        WHERE bill_items.bill_id=%s
    """, (bill_id,))

    items = cursor.fetchall()

    cursor.close()

    return render_template(
    "invoice.html",
    bill=bill,
    items=items,
    category=category
)
    
# ===========================
# LUNCH
# ===========================

@app.route("/lunch")
def lunch():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM food_items
        WHERE category='Lunch'
        ORDER BY food_name
    """)

    foods = cursor.fetchall()

    cursor.close()

    return render_template(
        "lunch.html",
        foods=foods
    )


# ===========================
# DINNER
# ===========================

@app.route("/dinner")
def dinner():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM food_items
        WHERE category='Dinner'
        ORDER BY food_name
    """)

    foods = cursor.fetchall()

    cursor.close()

    return render_template(
        "dinner.html",
        foods=foods
    )
# ===========================
# EXPENSE PAGE
# ===========================

# ===========================
# EXPENSE PAGE
# ===========================

@app.route("/expenses")
def expenses():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY expense_date DESC, id DESC
    """)
    expenses = cursor.fetchall()

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0) AS total_expense
        FROM expenses
    """)
    total_expense = cursor.fetchone()["total_expense"]

    cursor.close()

    return render_template(
        "expenses.html",
        expenses=expenses,
        total_expense=total_expense
    )
# ===========================
# ADD EXPENSE
# ===========================

@app.route("/add_expense", methods=["POST"])
def add_expense():

    if "user" not in session:
        return redirect("/")

    expense_name = request.form["expense_name"]
    amount = request.form["amount"]

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO expenses
        (
            expense_name,
            amount,
            expense_date,
            created_by
        )
        VALUES
        (
            %s,
            %s,
            CURDATE(),
            %s
        )
    """, (
        expense_name,
        amount,
        session["user"]
    ))

    cursor.close()

    return redirect("/expenses")
@app.route("/delete_expense/<int:id>")
def delete_expense(id):

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM expenses WHERE id=%s",
        (id,)
    )

    cursor.close()

    return redirect("/expenses")


# ===========================
# REPORT PAGE
# ===========================

@app.route("/reports")
def reports():

    if "user" not in session:
        return redirect("/")

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    cursor = connection.cursor()

    if from_date and to_date:

        cursor.execute("""
            SELECT *
            FROM bills
            WHERE bill_date BETWEEN %s AND %s
            ORDER BY bill_date DESC, id DESC
        """, (from_date, to_date))

        bills = cursor.fetchall()

        cursor.execute("""
            SELECT
            COUNT(*) AS total_bills,
            IFNULL(SUM(total),0) AS total_sales
            FROM bills
            WHERE bill_date BETWEEN %s AND %s
        """, (from_date, to_date))

        bill_data = cursor.fetchone()

        cursor.execute("""
            SELECT
            IFNULL(SUM(amount),0) AS total_expense
            FROM expenses
            WHERE expense_date BETWEEN %s AND %s
        """, (from_date, to_date))

        expense_data = cursor.fetchone()

    else:

        cursor.execute("""
            SELECT *
            FROM bills
            WHERE bill_date = CURDATE()
            ORDER BY id DESC
        """)

        bills = cursor.fetchall()

        cursor.execute("""
            SELECT
            COUNT(*) AS total_bills,
            IFNULL(SUM(total),0) AS total_sales
            FROM bills
            WHERE bill_date = CURDATE()
        """)

        bill_data = cursor.fetchone()

        cursor.execute("""
            SELECT
            IFNULL(SUM(amount),0) AS total_expense
            FROM expenses
            WHERE expense_date = CURDATE()
        """)

        expense_data = cursor.fetchone()

    total_bills = bill_data["total_bills"]
    total_sales = bill_data["total_sales"]
    total_expense = expense_data["total_expense"]
    total_profit = total_sales - total_expense

    cursor.close()

    return render_template(
        "reports.html",
        bills=bills,
        from_date=from_date,
        to_date=to_date,
        total_bills=total_bills,
        total_sales=total_sales,
        total_expense=total_expense,
        total_profit=total_profit
    )
@app.route("/bill_history")
def bill_history():

    if "user" not in session:
        return redirect("/")

    search = request.args.get("search", "")
    date = request.args.get("date", "")

    cursor = connection.cursor()

    sql = "SELECT * FROM bills WHERE 1=1"
    values = []

    if search:
        sql += " AND bill_no LIKE %s"
        values.append("%" + search + "%")

    if date:
        sql += " AND bill_date=%s"
        values.append(date)

    sql += " ORDER BY id DESC"

    cursor.execute(sql, values)

    bills = cursor.fetchall()

    cursor.close()

    return render_template(
        "bill_history.html",
        bills=bills,
        search=search,
        date=date
    )    
# ===========================
# CLOSE COUNTER
# ===========================

@app.route("/close_counter")
def close_counter():

    if "user" not in session:
        return redirect("/")

    cursor = connection.cursor()

    # Today's total bills
    cursor.execute("""
        SELECT COUNT(*) AS total_bills
        FROM bills
        WHERE bill_date = CURDATE()
    """)
    total_bills = cursor.fetchone()["total_bills"]

    # Today's sales
    cursor.execute("""
        SELECT IFNULL(SUM(total),0) AS total_sales
        FROM bills
        WHERE bill_date = CURDATE()
    """)
    total_sales = cursor.fetchone()["total_sales"]

    # Today's expenses
    cursor.execute("""
        SELECT IFNULL(SUM(amount),0) AS total_expense
        FROM expenses
        WHERE expense_date = CURDATE()
    """)
    total_expense = cursor.fetchone()["total_expense"]

    total_profit = total_sales - total_expense

    cursor.close()

    return render_template(
        "close_counter.html",
        total_bills=total_bills,
        total_sales=total_sales,
        total_expense=total_expense,
        total_profit=total_profit
    )
# ===========================
# BACKUP DATABASE
# ===========================

@app.route("/backup_database")
def backup_database():

    if "user" not in session:
        return redirect("/")

    # Backup folder inside HotelBillingSystem
    backup_folder = os.path.join(
        app.root_path,
        "backups"
    )

    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    filename = datetime.now().strftime(
        "hotel_backup_%Y%m%d_%H%M%S.sql"
    )

    backup_path = os.path.join(
        backup_folder,
        filename
    )

    # XAMPP mysqldump path
    mysqldump_path = r"C:\xampp\mysql\bin\mysqldump.exe"

    command = [
        mysqldump_path,
        "-u",
        "root",
        "--single-transaction",
        "--routines",
        "--events",
        "--triggers",
        "hotel_billing"
    ]

    try:

        # Run mysqldump and capture its output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check whether mysqldump worked
        if result.returncode != 0:

            return f"""
            <html>
            <body style="font-family:Arial;padding:30px">

                <h2 style="color:red;">
                    ❌ Backup Failed
                </h2>

                <p>
                    MySQL returned an error:
                </p>

                <pre>{result.stderr}</pre>

                <a href="/database">
                    ← Back to Database
                </a>

            </body>
            </html>
            """

        # Make sure something was actually exported
        if not result.stdout.strip():

            return """
            <html>
            <body style="font-family:Arial;padding:30px">

                <h2 style="color:red;">
                    ❌ Backup Failed
                </h2>

                <p>
                    mysqldump completed but produced an empty backup.
                </p>

                <p>
                    Please check whether the hotel_billing database
                    contains tables/data.
                </p>

                <a href="/database">
                    ← Back to Database
                </a>

            </body>
            </html>
            """

        # Write the actual SQL backup
        with open(
            backup_path,
            "w",
            encoding="utf-8"
        ) as outfile:

            outfile.write(result.stdout)

        return redirect("/database")

    except FileNotFoundError:

        return """
        <html>
        <body style="font-family:Arial;padding:30px">

            <h2 style="color:red;">
                ❌ mysqldump.exe Not Found
            </h2>

            <p>
                Make sure XAMPP is installed at:
            </p>

            <pre>C:\\xampp\\mysql\\bin\\mysqldump.exe</pre>

            <a href="/database">
                ← Back to Database
            </a>

        </body>
        </html>
        """
# ===========================
# RESTORE DATABASE
# ===========================

@app.route("/restore_database", methods=["POST"])
def restore_database():

    if "user" not in session:
        return redirect("/")

    filename = request.form["filename"]

    filepath = os.path.join(
        "backups",
        filename
    )

    # XAMPP MySQL executable
    mysql_path = r"C:\xampp\mysql\bin\mysql.exe"

    command = [
        mysql_path,
        "-u",
        "root",
        "hotel_billing"
    ]

    try:

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as infile:

            result = subprocess.run(
                command,
                stdin=infile,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:

            return f"""
            <h3>Restore Failed</h3>
            <p>{result.stderr}</p>
            <a href="/database">← Back to Database</a>
            """

    except FileNotFoundError:

        return """
        <h3>Restore Failed</h3>
        <p>MySQL executable was not found.</p>
        <p>Please check the XAMPP installation path.</p>
        <a href="/database">← Back to Database</a>
        """

    return redirect("/database")
# ===========================
# DATABASE
# ===========================

@app.route("/database")
def database():

    if "user" not in session:
        return redirect("/")

    folder = "backups"

    if not os.path.exists(folder):
        os.makedirs(folder)

    files = sorted(
        os.listdir(folder),
        reverse=True
    )

    return render_template(
        "database.html",
        files=files
    )


# ===========================
# DELETE BACKUP
# ===========================

@app.route("/delete_backup", methods=["POST"])
def delete_backup():

    if "user" not in session:
        return redirect("/")

    filename = request.form["filename"]

    backup_folder = "backups"

    filepath = os.path.join(backup_folder, filename)

    if os.path.exists(filepath) and os.path.isfile(filepath):
        os.remove(filepath)

    return redirect("/database")

# ===========================
# LOGOUT
# ===========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ===========================
# RUN APPLICATION
# ===========================

if __name__ == "__main__":
    app.run(debug=True)