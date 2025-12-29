
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

import sqlite3

conn = sqlite3.connect('database.db')
conn.execute("PRAGMA foreign_keys = ON;")
cur = conn.cursor()







cur.execute('''
            
CREATE TABLE IF NOT EXISTS users (
    userId INTEGER PRIMARY KEY,
    type TEXT CHECK(type IN ('acheteur', 'vendeur')),
    password TEXT,
    email TEXT UNIQUE,
    firstName TEXT,
    lastName TEXT,
    address1 TEXT,
    address2 TEXT,
    zipcode TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    phone TEXT,
    avatar TEXT,
    IP TEXT,
    acceptation INTEGER CHECK(acceptation IN (0,1)) DEFAULT 1,
    vendor_cert_path TEXT,
    cin_path TEXT,
    photo_path TEXT
);
''')

cur.execute("DROP TRIGGER IF EXISTS trg_users_acceptation_after;")
cur.execute('''
CREATE TRIGGER trg_users_acceptation_after
AFTER INSERT ON users
WHEN NEW.type = 'vendeur'
BEGIN
    UPDATE users
       SET acceptation = 0
     WHERE userId = NEW.userId;
END;
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS categories (
    categoryId INTEGER PRIMARY KEY,
    name TEXT
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS products (
    productId INTEGER PRIMARY KEY,
    name TEXT,
    price REAL,
    description TEXT,
    image TEXT,
    stock INTEGER,
    categoryId INTEGER,
    maker INTEGER,
    FOREIGN KEY(categoryId) REFERENCES categories(categoryId),
    FOREIGN KEY(maker) REFERENCES users(userId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS kart (
    userId INTEGER,
    productId INTEGER,
    FOREIGN KEY(userId) REFERENCES users(userId),
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS orders (
    orderId INTEGER PRIMARY KEY,
    userId INTEGER,
    orderDate TEXT,
    total REAL,
    FOREIGN KEY(userId) REFERENCES users(userId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    orderId INTEGER,
    productId INTEGER,
    quantity INTEGER,
    FOREIGN KEY(orderId) REFERENCES orders(orderId),
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS avis (
    avisId INTEGER PRIMARY KEY,
    userId INTEGER,
    productId INTEGER,
    commentaire TEXT,
    note INTEGER CHECK(note BETWEEN 1 AND 5),
    date TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(userId) REFERENCES users(userId),
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS rating_sellers (
    ratingSellerId INTEGER PRIMARY KEY,
    sellerId INTEGER,
    raterId INTEGER,
    commentaire TEXT,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    date TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(sellerId) REFERENCES users(userId),
    FOREIGN KEY(raterId) REFERENCES users(userId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS product_media (
    mediaId INTEGER PRIMARY KEY,
    productId INTEGER,
    url TEXT,
    mediaType TEXT CHECK(mediaType IN ('image','video')),
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS product_types (
    productId INTEGER PRIMARY KEY,
    type TEXT CHECK(type IN ('digital','physical')),
    livraisonType TEXT CHECK(livraisonType IN ('gratuite','payante')),
    fraisLivraison REAL DEFAULT 0,
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS produits_details (
    detailId INTEGER PRIMARY KEY,
    productId INTEGER,
    cle TEXT,
    valeur TEXT,
    FOREIGN KEY(productId) REFERENCES products(productId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS category_attributes (
    attrId INTEGER PRIMARY KEY,
    categoryId INTEGER,
    cle TEXT,
    FOREIGN KEY(categoryId) REFERENCES categories(categoryId)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS product_category_attributes (
    productId INTEGER,
    attrId INTEGER,
    valeur TEXT,
    FOREIGN KEY(productId) REFERENCES products(productId),
    FOREIGN KEY(attrId) REFERENCES category_attributes(attrId)
);
''')



cur.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    content TEXT,
    file_path TEXT,
    file_type TEXT CHECK(file_type IN ('image', 'audio')),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

''')




cur.execute('''
            
            CREATE TABLE IF NOT EXISTS reclamations (
    reclamationId INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER NOT NULL,
    message TEXT NOT NULL,
    date TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(userId) REFERENCES users(userId)
);

            ''')

conn.commit()
conn.close()

