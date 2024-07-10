import datetime
from inspect import ClosureVars
from itertools import accumulate, product
from logging import error
from re import M
import MySQLdb
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask.globals import request
from flask.helpers import stream_with_context
from flask.signals import message_flashed
from flask_mysqldb import MySQL
from werkzeug import datastructures
from werkzeug.utils import html, secure_filename
from wtforms import Form,StringField,TextAreaField,PasswordField, form,validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import date
from datetime import timedelta

app=Flask(__name__)
app.secret_key="123"
app.config['MYSQL_HOST']='pmathenge.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER']='pmathenge'
app.config['MYSQL_PASSWORD']='#Whocares123'
app.config['MYSQL_DB']='pmathenge$default'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql=MySQL(app)

class Register_form(Form):
    name=StringField('NAME',[validators.Length(min=1,max =50)])
    username = StringField('USERNAME',[validators.Length(min=4,max =50)])
    password=PasswordField('PASSWORD',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message="PASSWORDS DO NOT MATCH!!")
    ])
    confirm=PasswordField('Confirm Password')
@app.route('/')
def home():
    return render_template('home.html')
@app.route('/register',methods=['GET','POST'])
def register ():
    form=Register_form(request.form)
    if request.method=='POST' and form.validate():
        name =form.name.data
        username=form.username.data
        password=sha256_crypt.encrypt(form.password.data)


        cur=mysql.connection.cursor()
        result=cur.execute("SELECT username FROM customer WHERE username=%s",[username])
        if result>0:
            error='USERNAME ALREADY EXISTS'
            return render_template('register.html',error=error,form=form)
        cur.execute("INSERT INTO customer(customer_name,username,password)VALUES(%s,%s,%s)",(name,username,password))
        mysql.connection.commit()
        cur.close()

        flash('You are registered','success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
@app.route('/login',methods=['GET','POST'])
def login ():
    if request.method=='POST':
        username=request.form['username']
        password_candidate=request.form['password']

        cur=mysql.connection.cursor()
        result=cur.execute("SELECT USERNAME,PASSWORD FROM customer WHERE username=%s",[username])
        if result>0:
            data=cur.fetchone()
            password = data['PASSWORD']

            if sha256_crypt.verify(password_candidate,password):
                session['username']=username
                session['logged_in']=True
                flash("You are now logged in",'success')
                return redirect(url_for('product'))
            else:
                error='Invalid login'
                return render_template('login.html',error=error)
            cur.close()
        else:
            error="Username not found"
            return render_template('login.html',error=error)

    return render_template("login.html")
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized Please login", 'danger')
            return redirect(url_for('login'))
    return wrap
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out' , 'success')
    return redirect(url_for('login'))
@app.route('/product')
@is_logged_in
def product():
    cur=mysql.connection.cursor()
    cur.execute("SELECT customer_id FROM customer WHERE username=%s",[session['username']])
    result=cur.fetchone()
    Items_in_cart=cur.execute("SELECT (product_id) FROM Cart where customer_id=%s",[result['customer_id']])
    result=cur.execute("SELECT * FROM Inventory")
    mysql.connection.commit()
    products=cur.fetchall()
    if result>0:
        return render_template('products.html',products=products,Items_in_cart=Items_in_cart)
    else:
        error='No Products to display'
        return render_template('products.html',error=error,Items_in_cart=Items_in_cart)
    cur.close()
@app.route('/add_to_cart/<int:id>,<string:name>,<int:price>')
@is_logged_in
def add_to_cart(id,name,price):
    session['id']=id
    session['name']=name
    session['price']=price
    cur=mysql.connection.cursor()
    cur.execute("SELECT amount FROM Inventory WHERE product_id=%s",[id])
    result=cur.fetchone()
    if result['amount']>0:
        cur.execute("SELECT * FROM Inventory")
        mysql.connection.commit()
        products=cur.fetchall()
        cur.execute("SELECT customer_id,customer_name FROM customer WHERE username=%s",[session['username']])
        result1=cur.fetchone()
        cur.execute("INSERT INTO Cart (customer_id,product_id,product_name,product_price)VALUES(%s,%s,%s,%s)",[result1['customer_id'],session['id'],session['name'],session['price']])
        mysql.connection.commit()
        cur.close()
        msg='Product added to cart successfully'
        return render_template('products.html',msg=msg,products=products)
    else:
        error='This product is out of stock'
        return render_template('product_outofstock.html',error=error)
@app.route('/purchase_product/<int:id1>,<string:name1>')
@is_logged_in
def purchase_product(id1,name1):
    session['id1']=id1
    session['name1']=name1
    cur=mysql.connection.cursor()
    cur.execute("SELECT acc_no FROM customer  WHERE username=%s",[session['username']])
    result=cur.fetchone()
    if result['acc_no']==0:
        flash("Acccount number not registered,please register first to continue with transaction","danger")
        return redirect(url_for('transaction'))
    else:
        flash("Looks like your have a registered account,update if need be","success")
        return redirect(url_for('transaction'))

@app.route('/authorise_transaction')
@is_logged_in
def authorise_transaction():
    cur=mysql.connection.cursor()
    cur.execute("SELECT acc_no,customer_name from customer WHERE username=%s",[session['username']])
    result=cur.fetchone()
    if result['acc_no']==0:
        flash("Please add an account number to complete purchase",'danger')
        return redirect(url_for('transaction'))
    flash('Transaction complete,delivery will be done as follows:','success')
    cur.execute("SELECT customer_id,customer_name FROM customer WHERE username=%s",[session['username']])
    result1=cur.fetchone()
    cur.execute("UPDATE Inventory SET amount=amount-1,units_sold=units_sold+1 WHERE product_id=%s",[session['id1']])
    cur.execute("UPDATE customer SET units_bought=units_bought+1 WHERE username=%s",[session['username']])
    cur.execute("DELETE FROM Cart WHERE product_id=%s",[session['id']])
    mysql.connection.commit()
    cur.execute("INSERT INTO Sales (customer_id,customer_name,product_id,product_name)VALUES(%s,%s,%s,%s)",[result1['customer_id'],result1['customer_name'],session['id1'],session['name1']])
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('delivery_details'))
class transaction_form(Form):
    acc_no=StringField('ACCOUNT_NUMBER',[validators.Length(min=5,max=20),validators.DataRequired()])
@app.route('/transaction',methods=['GET','POST'])
@is_logged_in
def transaction():
    cur=mysql.connection.cursor()
    cur.execute("SELECT customer_category FROM customer WHERE username=%s",[session['username']])
    result=cur.fetchone()
    if result['customer_category']=='infrequent':
        form=transaction_form(request.form)
        if request.method=='POST':
            account_number=form.acc_no.data
            cur.execute("UPDATE customer SET acc_no=%s WHERE username=%s",[[account_number],session['username']])
            mysql.connection.commit()
            msg="Account number updated successfully"
            return render_template('transaction.html',txn=form,msg=msg)
        cur.execute("SELECT unit_price FROM Inventory WHERE product_id=%s",[session['id1']])
        price=cur.fetchone()

        return render_template('transaction.html',price=price['unit_price'],txn=form)
    else:
        cur.execute("SELECT customer_id,customer_name FROM customer WHERE username=%s",[session['username']])
        result1=cur.fetchone()
        cur.execute("UPDATE Inventory SET amount=amount-1,units_sold=units_sold+1 WHERE product_id=%s",[session['id1']])
        cur.execute("UPDATE customer SET units_bought=units_bought+1 WHERE username=%s",[session['username']])
        mysql.connection.commit()
        cur.execute("INSERT INTO Sales (customer_id,customer_name,product_id,product_name)VALUES(%s,%s,%s,%s)",[result1['customer_id'],result1['customer_name'],session['id1'],session['name1']])
        mysql.connection.commit()
        cur.execute("DELETE FROM Cart WHERE product_id=%s",[session['id1']])
        mysql.connection.commit()
        flash('The delivery will be done as follows','success')
        return redirect(url_for('delivery_details'))
@app.route('/items_in_cart')
@is_logged_in
def items_in_cart():
    cur=mysql.connection.cursor()
    cur.execute("SELECT customer_id FROM customer WHERE username=%s",[session['username']])
    result=cur.fetchone()
    cur.execute("SELECT product_id,product_name,product_price from Cart WHERE customer_id=%s",[result['customer_id']])
    result2=cur.fetchall()
    Items_in_cart=cur.execute("SELECT (product_id) FROM Cart where customer_id=%s",[result['customer_id']])
    cur.execute("SELECT SUM(product_price) AS 'cart_totals' FROM Cart WHERE customer_id=%s",[result['customer_id']])
    result3=cur.fetchone()


    return render_template('cart.html',products=result2,Items_in_cart=Items_in_cart,result3=result3['cart_totals'])
@app.route('/remove_from cart/<int:id>')
@is_logged_in
def remove_from_cart(id):
     cur=mysql.connection.cursor()
     cur.execute("DELETE FROM Cart WHERE product_id=%s",[id])
     mysql.connection.commit()
     return redirect(url_for('items_in_cart'))
@app.route('/delivery_details')
@is_logged_in
def delivery_details():
    today=datetime.date.today()
    date_ordered=today
    e_t_a=date_ordered+timedelta(days=1)
    cur=mysql.connection.cursor()
    cur.execute("SELECT customer_id FROM customer WHERE username=%s",[session['username']])
    result=cur.fetchone()
    cur.execute('INSERT INTO Delivery (Date_ordered,E_T_A,product_id,customer_id)VALUES(%s,%s,%s,%s)',[[date_ordered],[e_t_a],session['id1'],result['customer_id']])
    cur.execute('UPDATE Delivery SET vehicle_registration=vehicle_registration+1')
    mysql.connection.commit()
    cur.execute("SELECT * FROM Delivery WHERE customer_id=%s",[result['customer_id']])
    details=cur.fetchall()
    cur.close()
    return render_template('delivery_details.html',Delivery_details=details)


class admin_login_form(Form):
    username=StringField('ADMIN_USERNAME',[validators.Length(min=5,max=20)])
    password=PasswordField('ADMIN_PASSWORD',[validators.DataRequired()])
@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        admin_username=request.form['username']
        password_candidate=request.form['password']
        cur=mysql.connection.cursor()
        result=cur.execute("SELECT username,password FROM Admin WHERE username=%s",[admin_username])
        if result>0:
            data=cur.fetchone()
            password = data['password']
            if password_candidate==password:
                session['username']=admin_username
                session['logged_in']=True
                flash("LOGGED IN,    PLEASE SELECT YOUR DEPARTMENT",'success')
                return redirect(url_for('admin_dashboard'))
            else:
                error='Invalid login'
                return render_template('admin_login.html',error=error)
            cur.close()
        else:
            error="ADMIN not found"
            return render_template('admin_login.html',error=error)
    return render_template('admin_login.html')
def is_admin_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized Please login", 'danger')
            return redirect(url_for('admin_login'))
    return wrap
@app.route('/admin_dashboard')
@is_admin_logged_in
def admin_dashboard():
    return render_template('admin_dashboard.html')
@app.route('/admin_logout')
@is_admin_logged_in
def admin_logout():
    session.clear()
    flash('You are now logged out' , 'success')
    return redirect(url_for('admin_login'))
@app.route('/customer_service')
@is_admin_logged_in
def customer_service():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Inventory")
    result=cur.fetchall()
    cur.execute("SELECT * FROM Delivery")
    result1=cur.fetchall()
    cur.close()
    return render_template('customer_service_view.html',result=result,result1=result1)

class phone_orders_form(Form):
    customer_id=StringField("CUSTOMER_ID",[validators.Length(min=0,max=10)])
    product_id=StringField("PRODUCT_ID",[validators.Length(min=0,max=10)])
    acc_no=StringField("ACCOUNT_NUMBER",[validators.Length(min=5,max=20),validators.DataRequired()])
class customer_status_form(Form):
    customer_id2=StringField("CUSTOMER_ID",[validators.Length(min=0,max=10),validators.DataRequired()])
    customer_category=StringField("CUSTOMER_CATEGORY",[validators.Length(min=0,max=20)])
    acc_no=StringField("ACCOUNT_NUMBER",[validators.Length(min=0,max=20)])
@app.route('/call_center',methods=['GET','POST'])
@is_admin_logged_in
def call_center():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM customer")
    result=cur.fetchall()
    form=phone_orders_form(request.form)

    if request.method=='POST':
        customer_id=form.customer_id.data
        product_id=form.product_id.data
        acc_no=form.acc_no.data

        result2=cur.execute("SELECT product_id,product_name FROM Inventory WHERE product_id=%s",(product_id,))
        result3=cur.fetchone()
        if result2>0:
            cur.execute("INSERT INTO Delivery (customer_id,product_id) VALUES (%s,%s)",(customer_id,product_id))
            cur.execute("UPDATE customer SET acc_no=%s WHERE customer_id=%s",(acc_no,customer_id))
            cur.execute("SELECT amount FROM Inventory WHERE product_id=%s",(product_id,))
            result1=cur.fetchone()
            if result1['amount']>0:
                cur.execute("UPDATE Inventory SET amount=amount-1,units_sold=units_sold+1 WHERE product_id=%s",(product_id,))
                cur.execute("UPDATE customer SET units_bought=units_bought+1 WHERE customer_id=%s",(customer_id,))
                cur.execute('UPDATE Delivery SET vehicle_registration=vehicle_registration+1')
                cur.execute("SELECT customer_id,customer_name FROM customer WHERE customer_id=%s",(customer_id,))
                records=cur.fetchone()
                cur.execute("INSERT INTO Sales (customer_id,customer_name,product_id,product_name)VALUES(%s,%s,%s,%s)",[records['customer_id'],records['customer_name'],product_id,result3['product_name']])
                mysql.connection.commit()
                cur.close()
                msg="Order placed successfully"
                return render_template('call_center_view.html',form=form,result=result,msg=msg)


            else:
                error='This product is out of stock'
                return render_template('call_center_view.html',form=form,result=result,error=error)
        else:
            error="The product selected does not exist"
            return render_template('call_center_view.html',form=form,result=result,error=error)
    return render_template('call_center_view.html',form=form,result=result)
@app.route('/customer_update',methods=['GET','POST'])
@is_admin_logged_in
def customer_update():
     form2=customer_status_form(request.form)
     if request.method=='POST':
        cur=mysql.connection.cursor()
        customer_id2=form2.customer_id2.data
        customer_category=form2.customer_category.data
        acc_no=form2.acc_no.data

        cur.execute("UPDATE customer SET customer_category=%s WHERE customer_id=%s",(customer_category,customer_id2))
        cur.execute("UPDATE customer SET acc_no=%s WHERE customer_id=%s",(acc_no,customer_id2))
        mysql.connection.commit()
        cur.close()
        msg="Customer status updated successfully"
        return render_template('customer_status.html',form2=form2,msg=msg)

     return render_template('customer_status.html',form2=form2)

class inventory_update_form(Form):
    product_name=StringField("PRODUCT_NAME",[validators.Length(min=1,max=100),validators.DataRequired()])
    unit_price=StringField("UNIT_PRICE",[validators.Length(min=1,max=20),validators.DataRequired()])
    amount=StringField("AMOUNT",[validators.Length(min=1,max=10),validators.DataRequired()])
    manufacturer_id=StringField("Manufacturer_id",[validators.Length(min=1,max=15),validators.DataRequired()])
@app.route('/stocking_clerk',methods=['GET','POST'])
@is_admin_logged_in
def stocking_clerk():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Manufacturer")
    result=cur.fetchall()
    form=inventory_update_form(request.form)
    if request.method=='POST':
        product_name=form.product_name.data
        unit_price=form.unit_price.data
        amount=form.amount.data
        manufacturer_id=form.manufacturer_id.data
        result1=cur.execute("SELECT manufacturer_id FROM Manufacturer WHERE manufacturer_id=%s",(manufacturer_id,))

        if result1>0:
            cur.execute("INSERT INTO Inventory (product_name,unit_price,amount,manufacturer_id)VALUES(%s,%s,%s,%s)",(product_name,unit_price,amount,manufacturer_id))
            mysql.connection.commit()
            msg="Product added successfully"
            return render_template('stocking_clerk.html',form=form,result=result,msg=msg)


        else:
            error="Please check the manufacturer again"
            return render_template('stocking_clerk.html',form=form,result=result,error=error)
    cur.close()
    return render_template('stocking_clerk.html',form=form,result=result)
@app.route('/update_inventory',methods=['GET','POST'])
@is_admin_logged_in
def update_inventory():
    form=inventory_update_form(request.form)
    if request.method=='POST':
        product_name=form.product_name.data
        unit_price=form.unit_price.data
        amount=form.amount.data
        cur=mysql.connection.cursor()
        result=cur.execute("SELECT product_name FROM Inventory WHERE product_name=%s ",(product_name,))
        if result>0:
            cur.execute("UPDATE Inventory SET product_name=%s,unit_price=%s,amount=%s WHERE product_name=%s",(product_name,unit_price,amount,product_name))
            mysql.connection.commit()
            msg="Product update successfull!!"
            return render_template('update_inventory.html',form=form,msg=msg)
        else:
            error="The product does not exist, please enter the correct product name"
            return render_template('update_inventory.html',error=error,form=form)
    return render_template('update_inventory.html',form=form)
@app.route('/marketing')
@is_admin_logged_in
def marketing():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Sales")
    result=cur.fetchall()
    cur.close()
    return render_template('marketing.html',result=result)






















