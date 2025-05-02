from flask import Flask,render_template,request,redirect, url_for
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime
import sqlite3

app=Flask(__name__)
app.config['SECRET_KEY']='your_secret_key_here'
app.config['WTF_CSRF_ENABLED']=True

DATABASE = 'database.db'

def get_db_connection():
    conn=sqlite3.connect(DATABASE)
    conn.row_factory=sqlite3.Row
    return conn
class InitializeQuantityForm(FlaskForm):
    product_id=SelectField('Product',coerce=int,validators=[DataRequired()])
    location_id=SelectField('Location',coerce=int,validators=[DataRequired()])
    qty=IntegerField('Quantity',validators=[DataRequired()])
    submit=SubmitField('Initialize')

def init_db():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, 
    name TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS locations(id INTEGER PRIMARY KEY, 
    name TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory(product_id INTEGER, 
    location_id INTEGER, 
    qty INTEGER,
    PRIMARY KEY (product_id,location_id),
    FOREIGN KEY(product_id)REFERENCES products(id),
    FOREIGN KEY(location_id)REFERENCES locations(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY AUTOINCREMENT, 
    product_id INTEGER,
    from_location INTEGER, 
    to_location INTEGER, 
    qty INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
    FOREIGN KEY(product_id)REFERENCES products(id),
    FOREIGN KEY(from_location)REFERENCES locations(id),
    FOREIGN KEY(to_location)REFERENCES locations(id))''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM products")
    products=cursor.fetchall()
    cursor.execute("SELECT * FROM locations")
    locations=cursor.fetchall()
    conn.close()
    return render_template('index.html',products=products,locations=locations)

@app.route('/addproduct',methods=['POST'])
def addproduct():
    product_id=request.form['product_id']
    name=request.form['product_name']
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("INSERT INTO products(id,name)VALUES(?,?)",(product_id,name))
    conn.commit()
    conn.close()
    return redirect(url_for('addproducts'))

@app.route('/editproduct/<int:id>',methods=['GET','POST'])
def editproduct(id):
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    if request.method=='POST':
        name=request.form['product_name']
        cursor.execute("UPDATE products SET name=? WHERE id=?",(name,id))
        conn.commit()
        conn.close()
        return redirect(url_for('addproducts'))
    cursor.execute("SELECT * FROM products WHERE id=?",(id,))
    product=cursor.fetchone()
    conn.close()
    return render_template('editproducts.html',product=product)

@app.route('/addlocation',methods=['POST'])
def add_location():
    id=request.form['location_id']
    name=request.form['location_name']
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("INSERT INTO locations(id,name)VALUES(?,?)",(id,name))
    conn.commit()
    conn.close()
    return redirect(url_for('addlocations'))

@app.route('/editlocation/<int:id>',methods=['GET','POST'])
def editlocation(id):
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    if request.method=='POST':
        name=request.form['location_name']
        cursor.execute("UPDATE locations SET name=? WHERE id=?",(name,id))
        conn.commit()
        conn.close()
        return redirect(url_for('addlocations'))
    cursor.execute("SELECT * FROM locations WHERE id=?",(id,))
    location=cursor.fetchone()
    conn.close()
    return render_template('editlocations.html',location=location)

@app.route('/addproducts',methods=['GET','POST'])
def addproducts():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM products")
    products=cursor.fetchall()
    conn.close()
    return render_template('addproducts.html',products=products)

@app.route('/addlocations',methods=['GET','POST'])
def addlocations():
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM locations")
    locations=cursor.fetchall()
    conn.close()
    return render_template('addlocations.html',locations=locations)


@app.route('/initializequantity',methods=['GET','POST'])
def initializequantity():
    form=InitializeQuantityForm()
    conn=sqlite3.connect(DATABASE)
    cursor=conn.cursor()
    cursor.execute("SELECT id,name FROM products")
    products=cursor.fetchall()
    cursor.execute("SELECT id,name FROM locations")
    locations=cursor.fetchall()
    conn.close()
    form.product_id.choices=[(p[0],p[1])for p in products]
    form.location_id.choices=[(l[0],l[1])for l in locations]

    if form.validate_on_submit():
        conn=sqlite3.connect(DATABASE)
        cursor=conn.cursor()
        cursor.execute("SELECT qty FROM inventory WHERE product_id=? AND location_id=?",(form.product_id.data,form.location_id.data))
        existing_inventory = cursor.fetchone()
        if existing_inventory:
            new_qty=existing_inventory[0]+form.qty.data
            cursor.execute("UPDATE inventory SET qty=? WHERE product_id=?AND location_id=?",(new_qty,form.product_id.data,form.location_id.data))
        else:
            cursor.execute("INSERT INTO inventory(product_id,location_id,qty)VALUES(?,?,?)",(form.product_id.data, form.location_id.data, form.qty.data))
        conn.commit()
        conn.close()
        return redirect(url_for('productquantity'))
    return render_template('initializequantity.html',form=form)


@app.route('/productquantity')
def productquantity():
    conn=sqlite3.connect(DATABASE)
    conn.row_factory=sqlite3.Row
    cursor=conn.cursor()
    cursor.execute('''SELECT products.name AS product,locations.name AS location,inventory.qty
    FROM inventory
    JOIN products ON inventory.product_id=products.id
    JOIN locations ON inventory.location_id=locations.id''')
    report=cursor.fetchall()
    conn.close()
    return render_template('productquantity.html',report=report)

@app.route('/movements',methods=['GET','POST'])
def movements():
    conn=get_db_connection()
    error_message=None
    products=conn.execute('SELECT id,name FROM products').fetchall()
    locations=conn.execute('SELECT id,name FROM locations').fetchall()

    if request.method=='POST':
        product_id=int(request.form.get('product_id'))
        from_location=request.form.get('from_location')
        to_location=request.form.get('to_location')
        qty_input=request.form.get('qty')
        try:
            qty=int(qty_input)
            if qty<=0:
                raise ValueError("Quantity must be positive")
        except:
            error_message="Quantity must be a positive integer."
        if not error_message and from_location==to_location:
            error_message="From and To locations must be different."
        if not error_message and from_location: 
            stock_check=conn.execute("""SELECT qty FROM inventory WHERE product_id=? AND location_id=?""",(product_id,from_location)).fetchone()
            if not stock_check or stock_check['qty']<qty:
                error_message="Insufficient quantity in the source location."
        if not error_message:
            if from_location:
                existing_from=conn.execute("""SELECT qty FROM inventory WHERE product_id=? AND location_id=?""",(product_id,from_location)).fetchone()
                if existing_from and existing_from['qty']>=qty:
                    conn.execute("""UPDATE inventory SET qty=qty-? WHERE product_id=? AND location_id=?""",(qty,product_id,from_location))
                else:
                    error_message=f"Insufficient stock at source location."
            if to_location:
                existing_to=conn.execute("""SELECT qty FROM inventory WHERE product_id=? AND location_id=?""",(product_id,to_location)).fetchone()
                if existing_to:
                    conn.execute("""UPDATE inventory SET qty=qty+?WHERE product_id=? AND location_id=?""",(qty,product_id,to_location))
                else:
                    conn.execute("""INSERT INTO inventory(product_id,location_id,qty)VALUES(?,?,?)""",(product_id,to_location,qty))
            conn.execute("""INSERT INTO movements (product_id, from_location, to_location, qty, timestamp)VALUES (?, ?, ?, ?, ?)""",(product_id,from_location,to_location,qty,datetime.now()))
            conn.commit()
            conn.close()
            return redirect(url_for('movements'))

    movements=conn.execute("""SELECT m.timestamp,m.product_id,fl.name AS from_name,tl.name AS to_name,m.qty AS quantity,p.name AS product_name
    FROM movements m
    JOIN products p ON m.product_id=p.id
    LEFT JOIN locations fl ON m.from_location=fl.id
    LEFT JOIN locations tl ON m.to_location=tl.id
    ORDER BY m.timestamp DESC""").fetchall()
    conn.close()
    return render_template('movements.html',products=products,locations=locations,movements=movements,error_message=error_message)

@app.route('/delete_movements',methods=['POST'])
def delete_movements():
    conn = get_db_connection()
    conn.execute("DELETE FROM movements")
    conn.commit()
    conn.close()
    return redirect(url_for('movements'))

if __name__=='__main__':
    init_db()
    app.run(debug=True)
