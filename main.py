"""

MIT License

Copyright (c) 2025 Idriss Chadili

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
from flask import Flask,jsonify, render_template, request, redirect, url_for, session, flash, current_app
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from datetime import datetime
import time
from flask_cors import CORS
import requests
import json


app = Flask(__name__)
app.secret_key = 'idriss'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpeg', 'jpg', 'png', 'gif','pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER





def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn







def getLoginDetails():
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row  
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName FROM users WHERE email = ?", (session['email'],))
            result = cur.fetchone()

            if result is None:
                loggedIn = False
                firstName = ''
                noOfItems = 0
            else:
                userId = result[0]
                firstName = result[1]

                cur.execute("SELECT count(productId) FROM kart WHERE userId = ?", (userId,))
                noOfItems = cur.fetchone()[0] or 0

    return (loggedIn, firstName, noOfItems)














def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for _ in range(3):  
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans







@app.route("/account/profile/view")
def profileView():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone "
            "FROM users WHERE email = ?",
            (session['email'],)
        )
        profileData = cur.fetchone()
    return render_template(
        "profileView.html",
        profileData=profileData,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems
    )




@app.route('/ajouterAvis', methods=['POST'])
def ajouter_avis():
    if 'email' not in session:
        flash("Vous devez être connecté pour laisser un avis.", 'warning')
        return redirect(request.referrer or url_for('root'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'],))
    row = cur.fetchone()
    if row is None:
        conn.close()
        flash("Utilisateur introuvable.", 'danger')
        return redirect(request.referrer or url_for('root'))
    user_id = row['userId']

    product_id  = request.form['productId']
    note        = int(request.form['note'])
    commentaire = request.form['commentaire'].strip()

    try:
        cur.execute(
            "INSERT INTO avis (userId, productId, commentaire, note) VALUES (?, ?, ?, ?)",
            (user_id, product_id, commentaire, note)
        )
        conn.commit()
        flash("Merci pour votre avis !", 'success')
    except sqlite3.Error as e:
        app.logger.error(f"SQLite error in ajouter_avis: {e}")
        flash("Une erreur est survenue. Veuillez réessayer plus tard.", 'danger')
    finally:
        conn.close()

    return redirect(url_for('productDescription', productId=product_id))




@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if 'email' not in session:
        return redirect(url_for('loginForm'))

    loggedIn, firstName, noOfItems, _, _ = getUserSessionDetails()
    email = session['email']

    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT userId FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            return "Utilisateur introuvable", 400

        userId = user["userId"]

        cur.execute("""
            SELECT p.productId, p.name, p.price, p.image
            FROM products p
            JOIN kart k ON p.productId = k.productId
            WHERE k.userId = ?
        """, (userId,))
        products = cur.fetchall()

        totalPrice = sum(prod["price"] for prod in products)

        if request.method == "POST":
            if request.is_json:
                try:
                    data = request.get_json()
                    payment_details = data.get("paymentDetails")
                    if not payment_details:
                        return jsonify(status="error", message="Détails de paiement manquants")

                    orderDate = datetime.utcnow().isoformat()
                    cur.execute(
                        "INSERT INTO orders (userId, orderDate, total) VALUES (?, ?, ?)",
                        (userId, orderDate, totalPrice)
                    )
                    orderId = cur.lastrowid

                    for prod in products:
                        cur.execute(
                            "INSERT INTO order_items (orderId, productId, quantity) VALUES (?, ?, ?)",
                            (orderId, prod["productId"], 1)
                        )

                    cur.execute("DELETE FROM kart WHERE userId = ?", (userId,))
                    conn.commit()
                    return jsonify(status="success")

                except:
                    return jsonify(status="error", message="Erreur interne")
            else:
                try:
                    orderDate = datetime.utcnow().isoformat()
                    cur.execute(
                        "INSERT INTO orders (userId, orderDate, total) VALUES (?, ?, ?)",
                        (userId, orderDate, totalPrice)
                    )
                    orderId = cur.lastrowid

                    for prod in products:
                        cur.execute(
                            "INSERT INTO order_items (orderId, productId, quantity) VALUES (?, ?, ?)",
                            (orderId, prod["productId"], 1)
                        )

                    cur.execute("DELETE FROM kart WHERE userId = ?", (userId,))
                    conn.commit()

                    return render_template("thanks.html", firstName=firstName, orderId=orderId)
                except:
                    return "Une erreur est survenue", 500

        return render_template(
            "checkout.html",
            products=products,
            totalPrice=round(totalPrice, 2),
            loggedIn=loggedIn,
            firstName=firstName,
            noOfItems=noOfItems
        )



def getUserSessionDetails():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
            user_type = None
            photo_path = None
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName, type, photo_path FROM users WHERE email = ?", (session['email'],))
            row = cur.fetchone()
            if row:
                userId, firstName, user_type, photo_path = row
                cur.execute("SELECT count(productId) FROM kart WHERE userId = ?", (userId,))
                noOfItems = cur.fetchone()[0]
            else:
                loggedIn = False
                firstName = ''
                noOfItems = 0
                user_type = None
                photo_path = None
    return (loggedIn, firstName, noOfItems, user_type, photo_path)


@app.route("/", defaults={"sorting": None})
@app.route("/<sorting>")
def root(sorting):
    loggedIn, firstName, noOfItems, user_type, photo_path = getUserSessionDetails()

    if photo_path:
        user_photo = url_for('static', filename=photo_path)
    else:
        user_photo = None

    q = request.args.get('query', '').strip()
    selected_category_id = request.args.get('category_id', type=int)

    sort_options = {
        "price_asc": "ORDER BY price ASC",
        "price_desc": "ORDER BY price DESC",
        "stock_asc": "ORDER BY stock ASC",
        "stock_desc": "ORDER BY stock DESC",
    }
    sort_query = sort_options.get(sorting, "ORDER BY name ASC")

    where_clauses = []
    params = []

    if q:
        where_clauses.append("name LIKE ?")
        params.append(f"%{q}%")

    if selected_category_id:
        where_clauses.append("categoryId = ?")
        params.append(selected_category_id)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()

        query = f"""
            SELECT productId, name, price, description, image, stock
            FROM products
            {where_sql}
            {sort_query}
        """
        cur.execute(query, params)
        product_rows = cur.fetchall()

        cur.execute("SELECT categoryId, name FROM categories")
        categoryData = cur.fetchall()

    itemData = parse(product_rows)

    return render_template(
        "home.html",
        itemData=itemData,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
        categoryData=categoryData,
        search=q,
        selected_category_id=selected_category_id,
        user_type=user_type,
        user_photo=user_photo 
    )



@app.route("/add")
def admin():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT categoryId, name FROM categories")
        categories = cur.fetchall()
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        image = request.files['image']
        filename = ''
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        with sqlite3.connect('database.db') as conn:
            try:
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO products
                      (name, price, description, image, stock, categoryId)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, price, description, filename, stock, categoryId))
                conn.commit()
            except:
                conn.rollback()
    return redirect(url_for('root'))

@app.route("/remove")
def remove():
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        data = cur.fetchall()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with sqlite3.connect('database.db') as conn:
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE productId = ?', (productId,))
            conn.commit()
        except:
            conn.rollback()
    return redirect(url_for('root'))

@app.route("/displayCategory")
def displayCategory():
    loggedIn, firstName, noOfItems = getLoginDetails()
    categoryId = request.args.get("categoryId")
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.productId, p.name, p.price, p.image, c.name
              FROM products p
              JOIN categories c ON p.categoryId = c.categoryId
             WHERE c.categoryId = ?
        """, (categoryId,))
        data = cur.fetchall()
    categoryName = data[0][4] if data else ""
    itemData = parse(data)
    return render_template(
        'displayCategory.html',
        data=itemData,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
        categoryName=categoryName
    )

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = ?", (session['email'],))
        profileData = cur.fetchone()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = hashlib.md5(request.form['oldpassword'].encode()).hexdigest()
        newPassword = hashlib.md5(request.form['newpassword'].encode()).hexdigest()
        with sqlite3.connect('database.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId, password FROM users WHERE email = ?", (session['email'],))
            userId, password = cur.fetchone()
            if password == oldPassword:
                try:
                    cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                    conn.commit()
                    msg = "Changed successfully"
                except:
                    conn.rollback()
                    msg = "Failed to change password"
            else:
                msg = "Wrong password"
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        with sqlite3.connect('database.db') as conn:
            try:
                cur = conn.cursor()
                cur.execute('''
                    UPDATE users
                       SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ?
                     WHERE email = ?
                ''', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))
                conn.commit()
                msg = "Saved Successfully"
            except:
                conn.rollback()
                msg = "Error occurred"
        return redirect(url_for('profileHome'))





@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        print(f"User already logged in: {session['email']}")
        return redirect(url_for('root'))
    return render_template('login.html', error='')




@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        if email == "admin@directshop.ma" and password == "admin@directshop.ma":
            session['admin'] = True
            session['email'] = email
            return redirect(url_for('admin_panel_page'))
        
        if is_valid(email, password):
            session['email'] = email
            ipp(session['email'])
            
            conn = get_db_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT userId, type FROM users WHERE email = ?", 
                (email,)
            )
            row = cur.fetchone()
            conn.close()

            if row:
                user_id   = row['userId']
                user_type = (row['type'] or '').lower()

                session['user_id']   = user_id
                session['user_type'] = user_type

                if user_type in ('vendeur', 'seller'):
                    return redirect(url_for('seller_home'))
                else:
                    return redirect(url_for('seller_home'))
            
            error = 'Email ou mot de passe invalide'
            return render_template('login.html', error=error)
        else:
            error = 'Email ou mot de passe invalide'
            return render_template('login.html', error=error)

    return redirect(url_for('loginForm'))





def ipp(email):
    try:
        ip = requests.get('https://api.ipify.org', timeout=3).text
    except:
        ip = '0.0.0.0'

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET IP = ? WHERE email = ?", (ip, email))
    conn.commit()
    conn.close()


def get_all_users():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE type = 'acheteur'")
    users = cur.fetchall()
    con.close()
    return users

def get_all_sellers():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE type = 'vendeur'")
    sellers = cur.fetchall()
    con.close()
    return sellers

def GET_ALL_TYPES():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    sellers = cur.fetchall()
    con.close()
    return sellers


def get_all_categories():
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    con.close()
    return categories

def add_category_to_db(name):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    con.commit()
    con.close()

def delete_category_from_db(categoryId):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("DELETE FROM categories WHERE categoryId = ?", (categoryId,))
    con.commit()
    con.close()

def delete_user_from_db(userId):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE userId = ?", (userId,))
    con.commit()
    con.close()


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/loginForm')
    users = get_all_users()
    sellers = get_all_sellers()
    categories = get_all_categories()
    return render_template('admin.html', users=users, sellers=sellers, categories=categories, loggedIn=True)

@app.route('/addCategory', methods=['POST'])
def add_category():
    if not session.get('admin'):
        return redirect('/loginForm')
    category_name = request.form['category']
    add_category_to_db(category_name)
    return redirect('/admin')

@app.route('/deleteCategory/<int:categoryId>')
def delete_category(categoryId):
    if not session.get('admin'):
        return redirect('/loginForm')
    delete_category_from_db(categoryId)
    return redirect('/admin')

@app.route('/deleteUser/<int:userId>')
def delete_user(userId):
    if not session.get('admin'):
        return redirect('/loginForm')
    delete_user_from_db(userId)
    return redirect('/admin')



@app.route('/addProduct', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        stock = request.form['stock']
        categoryId = request.form['categoryId']
        image = request.files['image']

        image_path = os.path.join('static/uploads', image.filename)
        image.save(image_path)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO products (name, price, description, image, stock, categoryId, maker)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                       (name, price, description, image.filename, stock, categoryId, session['user_id']))  # Use session['user_id'] for logged-in user
        conn.commit()
        conn.close()

        return redirect('/seller/home')  

    elif request.method == 'GET':
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row  
        cursor = conn.execute('SELECT * FROM categories')
        categories = cursor.fetchall()
        print(categories)
        conn.close()

        return render_template('add_product.html', categories=categories)


@app.route("/seller/home")
def seller_home():
    if 'email' not in session:
        return redirect(url_for('loginForm'))

    loggedIn, firstName, noOfItems = getLoginDetails()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT type, photo_path FROM users WHERE email = ?", (session['email'],))
    row = cur.fetchone()
    if row is None:
        flash("Utilisateur non trouvé.", "danger")
        conn.close()
        return redirect(url_for('loginForm'))

    user_type = row['type'].strip().lower()
    user_photo_filename = row['photo_path']

    if user_type != 'vendeur':
        flash("Vous devez être un vendeur pour accéder à cette page.", 'danger')
        conn.close()
        return redirect(url_for('root'))

    cur.execute("""
        SELECT p.productId, p.name, p.price, p.stock, p.image, c.name AS category
          FROM products p
          JOIN categories c ON p.categoryId = c.categoryId
         WHERE p.maker = (
           SELECT userId FROM users WHERE email = ?
         )
    """, (session['email'],))
    products = cur.fetchall()

    cur.execute("""
        SELECT o.orderId, o.orderDate, p.name AS productName, oi.quantity
          FROM orders o
          JOIN order_items oi ON o.orderId = oi.orderId
          JOIN products p     ON oi.productId = p.productId
         WHERE p.maker = (
           SELECT userId FROM users WHERE email = ?
         )
    """, (session['email'],))
    orders = cur.fetchall()

    cur.execute("SELECT categoryId, name FROM categories")
    categories = cur.fetchall()

    conn.close()

    if user_photo_filename:
        user_photo = url_for('static', filename= user_photo_filename)
    else:
        user_photo = None

    return render_template(
        "home_seller.html",
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
        products=products,
        orders=orders,
        categories=categories,
        user_photo=user_photo
    )



@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems, user_type, user_photo = getUserSessionDetails()

    productId = request.args.get('productId')
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute('''
            SELECT productId, name, price, description, image, stock, maker
            FROM products
            WHERE productId = ?
        ''', (productId,))
        productData = cur.fetchone()
        if not productData:
            return "Produit introuvable", 404

        cur.execute('''
            SELECT 
              u.firstName    AS username,
              a.commentaire  AS commentaire,
              a.note         AS note
            FROM avis a
            JOIN users u ON a.userId = u.userId
            WHERE a.productId = ?
            ORDER BY a.rowid DESC
        ''', (productId,))
        comments = cur.fetchall()

        cur.execute('''
            SELECT firstName, lastName, email
            FROM users
            WHERE userId = ?
        ''', (productData["maker"],))
        vendeur = cur.fetchone()

    vendeur_full_name = None
    vendeur_email = None
    if vendeur:
        vendeur_full_name = f"{vendeur['firstName']} {vendeur['lastName']}"
        vendeur_email = vendeur["email"]

    session['email_vendeur'] = vendeur_email

    return render_template(
        "productDescription.html",
        data=productData,
        comments=comments,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
        user_photo=user_photo,
        email_vendeur=vendeur_email,
        nom_vendeur=vendeur_full_name,
        ID_SELLER=productData["maker"]
    )





@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    productId = int(request.args.get('productId'))
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'],))
        userId = cur.fetchone()[0]
        try:
            cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
            conn.commit()
        except:
            conn.rollback()
    return redirect(url_for('root'))

@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'],))
        userId = cur.fetchone()[0]
        cur.execute('''
            SELECT p.productId, p.name, p.price, p.image
              FROM products p
              JOIN kart k ON p.productId = k.productId
             WHERE k.userId = ?
        ''', (userId,))
        products = cur.fetchall()
        
    totalPrice = sum(row[2] for row in products)
    return render_template("cart.html",
                           products=products,
                           totalPrice=totalPrice,
                           loggedIn=loggedIn,
                           firstName=firstName,
                           noOfItems=noOfItems)

@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    productId = int(request.args.get('productId'))
    with sqlite3.connect('database.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (session['email'],))
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE userId = ? AND productId = ?", (userId, productId))
            conn.commit()
        except:
            conn.rollback()
    return redirect(url_for('cart'))

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

def is_valid(email, password):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    con.close()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False





@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        password  = request.form['password']
        email     = request.form['email']
        firstName = request.form['firstName']
        lastName  = request.form['lastName']
        address1  = request.form['address1']
        address2  = request.form['address2']
        zipcode   = request.form['zipcode']
        city      = request.form['city']
        state     = request.form['state']
        country   = request.form['country']
        phone     = request.form['phone']

        role      = request.form.get('type', 'buyer').lower()
        user_type = 'vendeur' if role == 'seller' else 'acheteur'
        acceptation = 1  # or your own logic for sellers vs buyers

        photo_path = None

        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                upload_folder = os.path.join(current_app.root_path, 'static/uploads')
                os.makedirs(upload_folder, exist_ok=True)
                photo.save(os.path.join(upload_folder, filename))
                # Save relative path to DB (relative to 'static')
                photo_path = f"uploads/{filename}"

        with sqlite3.connect('database.db') as con:
            try:
                cur = con.cursor()
                cur.execute('''
                    INSERT INTO users (
                        type, password, email, firstName, lastName,
                        address1, address2, zipcode, city, state, country,
                        phone, acceptation, photo_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_type,
                    hashlib.md5(password.encode()).hexdigest(),
                    email, firstName, lastName,
                    address1, address2, zipcode, city, state, country,
                    phone, acceptation, photo_path
                ))
                con.commit()
                msg = "Inscription réussie ! Veuillez vous connecter."
            except sqlite3.Error:
                con.rollback()
                msg = "Une erreur est survenue lors de l'inscription."

        return render_template("login.html", error=msg)

    return render_template("register.html")



@app.route("/registrationForm")
def registrationForm():
    return redirect("/register")





def getAllCategories():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    conn.close()
    return categories

@app.route('/editProduct/<int:productId>', methods=['GET', 'POST'])
def edit_product(productId):


    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        stock = request.form['stock']
        categoryId = request.form['categoryId']

        image_file = request.files.get('image')
        image_filename = None

        if image_file and image_file.filename != '':
            image_filename = image_file.filename
            image_path = os.path.join('static/uploads', image_filename)
            image_file.save(image_path)
        else:
            image_filename = getProductById(productId)['image']

        updateProduct(productId, name, price, description, image_filename, stock, categoryId)
        
        print(f"Redirecting to: {url_for('seller_home')}")
        
        return redirect('/seller/home')  

    product = getProductById(productId)
    categories = getAllCategories()
    return render_template('edit_product_modal.html', product=product, categories=categories)


@app.route('/deleteProduct/<int:productId>', methods=['GET'])
def delete_product(productId):
 
    print(f"Deleting product with ID: {productId}")

    deleteProduct(productId)
    
    print(f"Redirecting to: {url_for('seller_home')}")
    
    return redirect('/seller/home')  


def deleteProduct(productId):
    conn=sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE productId = ?", (productId,))
    conn.commit()







def getProductById(productId):
    conn=sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (productId,))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None

def updateProduct(productId, name, price, description, image, stock, categoryId):
    conn=sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""
        UPDATE products SET name=?, price=?, description=?, image=?, stock=?, categoryId=?
        WHERE id=?
    """, (name, price, description, image, stock, categoryId, productId))
    conn.commit()













def fetch_all_admin(sql, params=()):
    with get_db_connection() as con:
        cur = con.execute(sql, params)
        return cur.fetchall()

def execute_admin(sql, params=()):
    with get_db_connection() as con:
        con.execute(sql, params)
        con.commit()

def admin_get_all_buyers():
    return fetch_all_admin("SELECT * FROM users WHERE type='vendeur'")

def admin_get_all_sellers():
    return fetch_all_admin("SELECT * FROM users WHERE type='seller'")

def admin_get_all_categories():
    return fetch_all_admin("SELECT * FROM categories")

def admin_add_category(name):
    execute_admin("INSERT INTO categories (name) VALUES (?)", (name,))

def admin_delete_category(category_id):
    execute_admin("DELETE FROM categories WHERE categoryId=?", (category_id,))

def admin_delete_user(user_id):
    execute_admin("DELETE FROM users WHERE userId=?", (user_id,))

def is_admin_user():
    return session.get("user_type") == "admin"




@app.route("/admin")
def admin_panel_page():
    if not is_admin_user():
        flash("Accès réservé à l’administrateur.", "danger")
        return redirect(url_for("loginForm"))

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE type = 'acheteur'")
    buyers = cur.fetchall()

    cur.execute("SELECT * FROM users WHERE type = 'vendeur'")
    sellers = cur.fetchall()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute('''
        SELECT reclamations.reclamationId AS id,
               users.firstName || ' ' || users.lastName AS user,
               reclamations.message,
               reclamations.date
        FROM reclamations
        JOIN users ON users.userId = reclamations.userId
        ORDER BY reclamations.date DESC
    ''')
    reclamations = cur.fetchall()

    conn.close()

    sellers_accepted = [s for s in sellers if s['acceptation'] == 1]
    sellers_pending = [s for s in sellers if s['acceptation'] == 0]

    loggedIn, firstName, noOfItems = getLoginDetails()

    return render_template(
        "admin.html",
        buyers=buyers,
        sellers_accepted=sellers_accepted,
        sellers_pending=sellers_pending,
        categories=categories,
        reclamations=reclamations,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems
    )


@app.route("/delete_reclamation/<int:rec_id>", methods=["POST"])
def delete_reclamation(rec_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM reclamations WHERE reclamationId = ?", (rec_id,))
    conn.commit()
    conn.close()
    return '', 204  # no content


@app.route("/last_reclamation")
def last_reclamation():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        SELECT r.reclamationId,
               u.firstName || ' ' || u.lastName AS full_name,
               r.message,
               r.date
        FROM reclamations r
        JOIN users u ON u.userId = r.userId
        ORDER BY r.date DESC
    ''')
    reclamations = cur.fetchall()
    conn.close()

    return render_template("last_reclamation.html", reclamations=reclamations)



@app.route("/admin/addCategory", methods=["POST"])
def admin_add_category_route():
    if not is_admin_user():
        return redirect(url_for("loginForm"))
    name = request.form["category"].strip()
    if name:
        admin_add_category(name)
        flash("Catégorie ajoutée.", "success")
    return redirect(url_for("admin_panel_page"))

@app.route("/admin/deleteCategory/<int:category_id>")
def admin_delete_category_route(category_id):
    if not is_admin_user():
        return redirect(url_for("loginForm"))
    admin_delete_category(category_id)
    flash("Catégorie supprimée.", "info")
    return redirect(url_for("admin_panel_page"))

@app.route("/admin/deleteUser/<int:user_id>")
def admin_delete_user_route(user_id):
    if not is_admin_user():
        return redirect(url_for("loginForm"))
    admin_delete_user(user_id)
    flash("Utilisateur supprimé.", "info")
    return redirect(url_for("admin_panel_page"))

@app.route('/accept_vendor/<int:user_id>', methods=['POST'])
def accept_vendor(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET acceptation=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return ('', 204)  

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user_post(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return ('', 204)









@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Utilisateur non authentifié'}), 401

    cert_file = request.files.get('cert_file')
    cin_file  = request.files.get('cin_file')
    photo_file= request.files.get('photo_file')

    if not all([cert_file, cin_file, photo_file]):
        return jsonify({'error': 'Tous les documents sont requis'}), 400

    for f in (cert_file, cin_file, photo_file):
        if not allowed_file(f.filename):
            return jsonify({'error': f'Extension non autorisée : {f.filename}'}), 400

    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    cert_name = f"user{user_id}_cert_{secure_filename(cert_file.filename)}"
    cin_name  = f"user{user_id}_cin_{secure_filename(cin_file.filename)}"
    photo_name= f"user{user_id}_photo_{secure_filename(photo_file.filename)}"

    cert_path = os.path.join(upload_folder, cert_name)
    cin_path  = os.path.join(upload_folder, cin_name)
    photo_path= os.path.join(upload_folder, photo_name)

    cert_file.save(cert_path)
    cin_file.save(cin_path)
    photo_file.save(photo_path)

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE users
        SET vendor_cert_path = ?,
            cin_path         = ?,
            photo_path       = ?
        WHERE userId = ?
    """, (cert_name, cin_name, photo_name, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True}), 200







@app.route('/account/orders')
def account_orders():
    if "email" not in session:
        return redirect(url_for('login')) 

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT userId FROM users WHERE email = ?", (session["email"],))
    user = cur.fetchone()
    if not user:
        conn.close()
        return "Utilisateur introuvable", 404

    cur.execute("SELECT * FROM orders WHERE userId = ? ORDER BY orderDate DESC", (user["userId"],))
    orders = cur.fetchall()
    conn.close()

    return render_template("account_orders.html", orders=orders)





@app.route('/delete_order', methods=['POST'])
def delete_order():
    data = request.get_json()
    order_id = data.get('orderId')
    conn = get_db_connection()
    conn.execute('DELETE FROM orders WHERE orderId = ?', (order_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})




ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm'}

def allowed_message_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_messages_with(user_email, current_email):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute('''
        SELECT sender, receiver, content, file_path, file_type, timestamp FROM messages
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
        ORDER BY timestamp
    ''', (current_email, user_email, user_email, current_email))
    msgs = cur.fetchall()
    con.close()
    return msgs

@app.route('/messages')
def messages():
    if 'email' not in session:
        return redirect(url_for('login'))
    current_email = session['email']

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute('''
        SELECT * FROM users WHERE email != ? 
    ''', (current_email,))
    users = cur.fetchall()
    con.close()

    receiver = request.args.get('receiver')

    return render_template(
        "messages.html",
        users=users,
        receiver=receiver,
        current_email=current_email
    )

@app.route('/get_messages')
def get_messages():
    if 'email' not in session:
        return jsonify([])

    current_email = session['email']
    user_email = request.args.get('user_email')
    messages = get_messages_with(user_email, current_email)

    messages_list = []
    for m in messages:
        messages_list.append({
            "sender": m[0],
            "receiver": m[1],
            "content": m[2],
            "file_path": m[3],
            "file_type": m[4],
            "timestamp": m[5]
        })

    return jsonify(messages_list)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'email' not in session:
        return jsonify({"error": "Not logged in"}), 401

    sender = session['email']

    if 'file' in request.files:
        file = request.files['file']
        receiver = request.form.get('receiver')
        content = request.form.get('content', None)

        if not receiver:
            return jsonify({"error": "Receiver missing"}), 400

        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()

        if allowed_message_file(filename, ALLOWED_IMAGE_EXTENSIONS):
            file_type = 'image'
        elif allowed_message_file(filename, ALLOWED_AUDIO_EXTENSIONS):
            file_type = 'audio'
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        relative_path = f'/static/uploads/{filename}'

        con = sqlite3.connect('database.db')
        cur = con.cursor()
        cur.execute('''
            INSERT INTO messages (sender, receiver, content, file_path, file_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender, receiver, content, relative_path, file_type))
        con.commit()
        con.close()

        return jsonify({"success": True})

    data = request.json
    if not data:
        return jsonify({"error": "Missing data"}), 400

    receiver = data.get('receiver')
    content = data.get('content')

    if not receiver or not content:
        return jsonify({"error": "Missing content or receiver"}), 400

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute('''
        INSERT INTO messages (sender, receiver, content) VALUES (?, ?, ?)
    ''', (sender, receiver, content))
    con.commit()
    con.close()

    return jsonify({"success": True})



@app.route("/produit/<int:id>")
def produit(id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        SELECT products.*, users.email AS email_vendeur
        FROM products
        JOIN users ON products.maker = users.userId
        WHERE products.productId = ?
    ''', (id,))
    
    produit = cur.fetchone()
    conn.close()

    return render_template("produit.html", produit=produit)





@app.route('/reclamation', methods=['POST'])
def reclamation():
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour envoyer une réclamation.", "warning")
        return redirect(url_for('loginForm'))

    message = request.form.get('message', '').strip()
    if not message:
        flash("Le message de réclamation est vide.", "danger")
        return redirect(request.referrer or url_for('root'))

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO reclamations (userId, message) VALUES (?, ?)",
            (user_id, message)
        )
        conn.commit()
        return render_template('reclamation_ok.html')
    except Exception as e:
        flash(f"Erreur lors de l'envoi de la réclamation : {e}", "danger")
        return redirect(request.referrer or url_for('root'))
    finally:
        conn.close()





if __name__ == '__main__':
    app.run(debug=True,port=5001)
