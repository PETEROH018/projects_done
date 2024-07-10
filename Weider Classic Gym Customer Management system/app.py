

import datetime
from inspect import ClosureVars
from itertools import accumulate, product
from logging import error
from re import M
from wsgiref.validate import validator
import MySQLdb
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mail import Mail,Message
from flask.globals import request
from flask.helpers import stream_with_context
from flask.signals import message_flashed
from flask_mysqldb import MySQL
from werkzeug import datastructures
from werkzeug.utils import html, secure_filename
from wtforms import Form,StringField,TextAreaField,PasswordField, form,validators
from functools import wraps
from datetime import date
from datetime import timedelta


app=Flask(__name__)

app.secret_key="123"
app.config['MYSQL_HOST']='weiderclassicgym.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER']='weiderclassicgym'
app.config['MYSQL_PASSWORD']='#Weider1234#'
app.config['MYSQL_DB']='weiderclassicgym$gym'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'weiderclassicgym@gmail.com'
app.config['MAIL_PASSWORD'] = '#weider1234#'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
mysql=MySQL(app)
class customer_login_form(Form):
    username=StringField('USERNAME',[validators.Length(min=5,max=20)])
    password=PasswordField('PASSWORD',[validators.DataRequired()])
@app.route('/',methods=['GET','POST'])
def customer_view():
    if request.method=='POST':
        customer_username=request.form['username']
        customer_password_candidate=request.form['password']
        cur=mysql.connection.cursor()
        result=cur.execute("SELECT Username,Password FROM Customers WHERE Username=%s",[customer_username])
        if result>0:
            data1=cur.fetchone()
            password=data1['Password']
            if customer_password_candidate==password:
                session['customer_username']=customer_username
                session['logged_in']=True
                return redirect(url_for('customer_dashboard'))
            else:
                error='Invalid login'
                return render_template('customer_view.html',error=error)
            cur.close()
        else:
            error="User not found"
            return render_template('customer_view.html',error=error)

    return render_template('customer_view.html')
@app.route('/customer_dashboard')
def customer_dashboard():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Workouts")
    workouts=cur.fetchall()


    return render_template('customer_dashboard.html',workouts=workouts)
@app.route('/selected_workouts/<string:name>,<string:des>')
def selected_workouts(name,des):
    session['name']=name
    session['des']=des
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Workouts")
    workouts=cur.fetchall()
    cur.execute("INSERT INTO Selected_Workouts (username,Workout_ID,Description)VALUES(%s,%s,%s)",[session['customer_username'],session['name'],session['des']])
    mysql.connection.commit()
    cur.close()
    msg='Workout selected successfuly'

    return render_template('customer_dashboard.html',workouts=workouts,msg=msg)
@app.route('/preferred_workouts')
def preferred_workouts():


    cur=mysql.connection.cursor()
    cur.execute("SELECT Workout_ID,Description FROM Selected_Workouts WHERE username=%s",[session['customer_username']])
    workouts=cur.fetchall()


    return render_template('preferred_workouts.html',workouts=workouts)
@app.route('/customer_selection')
def customer_selection():


    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Selected_Workouts")
    workouts=cur.fetchall()


    return render_template('customer_selection.html',workouts=workouts)

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
class customer_registration_form(Form):
    name=StringField("NAME",[validators.Length(min=1,max=50),validators.DataRequired()])
    phone_number=StringField("PHONE_NUMBER",[validators.Length(min=1,max=50),validators.DataRequired()])
    email=StringField("EMAIL",[validators.Length(min=1,max=30),validators.DataRequired()])
    home_address=StringField("HOME_ADDRESS",[validators.Length(min=1,max=20),validators.DataRequired()])
    username = StringField('USERNAME',[validators.Length(min=4,max =50)])
    password=PasswordField('PASSWORD',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message="PASSWORDS DO NOT MATCH!!")
    ])
    confirm=PasswordField('Confirm Password')

@app.route('/register_new_customer',methods=['GET','POST'])
def register_new_customer():
    cur=mysql.connection.cursor()
    form=customer_registration_form(request.form)
    if request.method=='POST':
       name=form.name.data
       phone_number=form.phone_number.data
       email=form.email.data
       home_address=form.home_address.data
       username=form.username.data
       password=form.password.data
       cur=mysql.connection.cursor()
       result=cur.execute("SELECT username FROM Customers WHERE username=%s",[username])
       if result>0:
            error='USERNAME ALREADY EXISTS'
            return render_template('customer_registration.html',error=error,form=form)
       cur.execute("INSERT INTO Customers (Name,Phone_number,Email,Home_address,Username,Password)VALUES(%s,%s,%s,%s,%s,%s)",(name,phone_number,email,home_address,username,password))
       mysql.connection.commit()
       flash('You have been registered successfully,you can now log in','success')
       return redirect(url_for('customer_view'))
    cur.close()
    return render_template('customer_registration.html',form=form)
class transaction_form(Form):
    txn_id=StringField("TXN_ID",[validators.Length(min=1,max=10),validators.DataRequired()])
    customer_id=StringField("CUSTOMER_ID",[validators.Length(min=1,max=15),validators.DataRequired()])
    time=StringField("TIME",[validators.Length(min=1,max=15),validators.DataRequired()])
    date=StringField("DATE",[validators.Length(min=1,max=15),validators.DataRequired()])
    amount=StringField("AMOUNT",[validators.Length(min=1,max=15),validators.DataRequired()])
@app.route('/update_customer_subscription',methods=['GET','POST'])
@is_admin_logged_in
def update_customer_subscription():
    cur=mysql.connection.cursor()
    form=transaction_form(request.form)
    if request.method=='POST':
        txn_id=form.txn_id.data
        customer_id=form.customer_id.data
        time=form.time.data
        date=form.date.data
        amount=form.amount.data
        result=cur.execute("SELECT CustomerID FROM Customers WHERE CustomerID=%s",(customer_id,))
        if result>0:
            result1=cur.execute("SELECT TXN_ID FROM Transactions WHERE TXN_ID=%s",(txn_id,))
            if result1>0:
                error="TXN ID already exists,please check and enter again"
                return render_template('customer_subscription.html',form=form,error=error)
            else:
                cur.execute("INSERT INTO Transactions(TXN_ID,Customer_ID,Time,Date,Amount)VALUES(%s,%s,%s,%s,%s)",(txn_id,customer_id,time,date,amount))
                mysql.connection.commit()
                msg="Transaction updated successfully"
                return render_template("customer_subscription.html",form=form,msg=msg)

        else:
            error="Customer does not exist,please check ID"
            return render_template('customer_subscription.html',form=form,error=error)

    cur.close()
    return render_template ('customer_subscription.html',form=form)



@app.route('/registered customers')
@is_admin_logged_in
def registered_customers():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Customers")
    result=cur.fetchall()

    return render_template ('registered_customers.html',customers=result)


@app.route('/monitor_customer_subcription',methods=['GET','POST'])
@is_admin_logged_in
def monitor_customer_subscription():

    count=0
    cur=mysql.connection.cursor()
    customers=cur.execute("SELECT * FROM Customers")
    distinct_customers=cur.execute("SELECT DISTINCT Customer_ID FROM Transactions")
    i=1

    result1=[]
    if distinct_customers != customers:
        error="Not all customers have subscribed...Please check!"
        return render_template ('subscription_left.html',error=error)
    else:

        while i<=customers:

            cur.execute("SELECT Customer_ID, DATEDIFF(CURDATE(),MAX(Date)) AS Days_spent FROM Transactions WHERE Customer_ID=%s  ",[i])
            result=cur.fetchall()
            result1.append(result[0])
            i=i+1
        return render_template ('subscription_left.html',days=result1,count=count)
@app.route('/customer_subcription/<int:id>')
@is_admin_logged_in
def customer_subscription(id):
    customerid=id
    result3=[]
    cur=mysql.connection.cursor()
    cur.execute("SELECT Email FROM Customers WHERE CustomerID=%s",[customerid])
    result2=cur.fetchall()
    result3.append(result2[0]["Email"])

    msg=Message('SUBSCRIPTION EXPIRED', sender = 'weiderclassicgym@gmail.com')
    msg.recipients=result3
    msg.body="Greetings,its appears that your gym subscription has expired,please activate"
    mail.send(msg)
    flash("Customer notified to renew subscription","success")
    return redirect(url_for("monitor_customer_subscription"))
@app.route('/subscribed_customers',methods=['GET','POST'])
@is_admin_logged_in
def subscribed_customers():
    cur=mysql.connection.cursor()
    cur.execute("SELECT Transactions.TXN_ID,Transactions.Customer_ID,Customers.Name,Customers.Phone_number,Customers.Email,Customers.Home_address,Transactions.Time,Transactions.Date,Transactions.Amount  FROM Transactions INNER JOIN Customers ON Transactions.Customer_ID=Customers.CustomerID")
    result=cur.fetchall()

    return render_template("subscribed_customers.html",subscribed=result)
class gym_equipments_form(Form):
        equipment_serial_number=StringField("EQUIPMENT_SERIAL_NUMBER",[validators.Length(min=1,max=20),validators.DataRequired()])
        name=StringField("NAME",[validators.Length(min=1,max=30),validators.DataRequired()])
        amount=StringField("AMOUNT",[validators.Length(min=1,max=20),validators.DataRequired()])
        price=StringField("PRICE",[validators.Length(min=1,max=20),validators.DataRequired()])
        workout_id=StringField("WORKOUT_ID",[validators.Length(min=1,max=20),validators.DataRequired()])
        date_purchased=StringField("DATE_PURCHASED",[validators.Length(min=1,max=20),validators.DataRequired()])
@app.route('/add_equipments',methods=['GET','POST'])
@is_admin_logged_in
def add_equipments():
    form=gym_equipments_form(request.form)
    cur=mysql.connection.cursor()
    if request.method=='POST':
        equipment_serial_number=form.equipment_serial_number.data
        name=form.name.data
        amount=form.amount.data
        price=form.price.data
        workout_id=form.workout_id.data
        date_purchased=form.date_purchased.data
        result=cur.execute("SELECT Equipment_serial_number FROM Equipments WHERE Equipment_serial_number=%s",[equipment_serial_number])
        result1=cur.execute("SELECT Workout_ID FROM Workouts WHERE Workout_ID=%s ",[workout_id])
        if result1>0:
            if result>0:
                error="The serial number entered already exists,Kindly check!!!"
                return render_template("gym_inventory.html",error=error,form=form)
            else:
                cur.execute("INSERT INTO Equipments (Equipment_serial_number,Name,Amount,Price,Workout_ID,Date_purchased)VALUES(%s,%s,%s,%s,%s,%s)",(equipment_serial_number,name,amount,price,workout_id,date_purchased))
                mysql.connection.commit()
                msg="Equipment added successfully"
                return render_template("gym_inventory.html",form=form,msg=msg)
        else:
            error="Workout selected does not exist"
            return render_template("gym_inventory.html",error=error,form=form)
    return render_template("gym_inventory.html",form=form)
class update_equipments_form(Form):
        equipment_serial_number=StringField("EQUIPMENT_SERIAL_NUMBER",[validators.Length(min=1,max=20),validators.DataRequired()])
        amount=StringField("AMOUNT",[validators.Length(min=1,max=20),validators.DataRequired()])
@app.route('/registered equipments',methods=['GET','POST'])
@is_admin_logged_in
def registered_equipments():
    form=update_equipments_form(request.form)
    cur=mysql.connection.cursor()
    cur.execute("SELECT Equipments.Equipment_serial_number,Equipments.Name,Equipments.Amount,Equipments.Price,Workouts.Workout_name,Equipments.Date_purchased  FROM Equipments INNER JOIN Workouts ON Equipments.Workout_ID=Workouts.Workout_ID ")
    result=cur.fetchall()
    if request.method=='POST':
        equipment_serial_number=form.equipment_serial_number.data
        amount=form.amount.data
        result1=cur.execute("SELECT Equipment_serial_number FROM Equipments WHERE Equipment_serial_number=%s",[equipment_serial_number])
        if result1<1:
            error="Equipment selected does not exist"
            cur.execute("SELECT Equipments.Equipment_serial_number,Equipments.Name,Equipments.Amount,Equipments.Price,Workouts.Workout_name,Equipments.Date_purchased FROM Equipments INNER JOIN Workouts ON Equipments.Workout_ID=Workouts.Workout_ID ")
            result3=cur.fetchall()
            return render_template ('registered_equipments.html',equipments=result3,form=form,error=error)
        else:
            cur.execute("UPDATE Equipments SET Amount=%s WHERE Equipment_serial_number=%s ",(amount,equipment_serial_number))
            mysql.connection.commit()
            msg="Equipment amount reset successfully"
            cur.execute("SELECT Equipments.Equipment_serial_number,Equipments.Name,Equipments.Amount,Equipments.Price,Workouts.Workout_name,Equipments.Date_purchased FROM Equipments INNER JOIN Workouts ON Equipments.Workout_ID=Workouts.Workout_ID ")
            result4=cur.fetchall()
            return render_template ('registered_equipments.html',equipments=result4,form=form,msg=msg)


    return render_template ('registered_equipments.html',equipments=result,form=form)
class trainers_registration_form(Form):
        trainer_id=StringField("TRAINER_ID",[validators.Length(min=1,max=20),validators.DataRequired()])
        trainer_name=StringField("TRAINER_NAME",[validators.Length(min=1,max=30),validators.DataRequired()])
        phone_number=StringField("PHONE_NUMBER",[validators.Length(min=1,max=50),validators.DataRequired()])
        email=StringField("EMAIL",[validators.Length(min=1,max=50),validators.DataRequired()])
        address=StringField("ADDRESS",[validators.Length(min=1,max=30),validators.DataRequired()])
@app.route('/register_trainer',methods=['GET','POST'])
@is_admin_logged_in
def register_trainer():
    form=trainers_registration_form(request.form)
    cur=mysql.connection.cursor()
    if request.method=='POST':
        trainer_id=form.trainer_id.data
        trainer_name=form.trainer_name.data
        phone_number=form.phone_number.data
        email=form.email.data
        address=form.address.data
        result=cur.execute("SELECT trainer_id FROM Trainers WHERE trainer_id=%s",[trainer_id])
        if result>0:
            error="Trainer already exists,Kindly check!!!"
            return render_template("trainers_registration.html",error=error,form=form)
        else:
            cur.execute("INSERT INTO Trainers (Trainer_ID,Trainer_name,Phone_number,Email,Address)VALUES(%s,%s,%s,%s,%s)",(trainer_id,trainer_name,phone_number,email,address))
            mysql.connection.commit()
            msg=" Trainer registered successfully"
            return render_template("trainers_registration.html",form=form,msg=msg)
    return render_template("trainers_registration.html",form=form)
class trainers_status_update_form(Form):
        trainer_id=StringField("TRAINER_ID",[validators.Length(min=1,max=20),validators.DataRequired()])
        status=StringField("STATUS",[validators.Length(min=1,max=30),validators.DataRequired()])

@app.route('/registered trainers',methods=['GET','POST'])
@is_admin_logged_in
def registered_trainers():
    form=trainers_status_update_form(request.form)
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Trainers")
    result=cur.fetchall()
    if request.method=='POST':
        trainer_id=form.trainer_id.data
        status=form.status.data
        result1=cur.execute("SELECT Trainer_ID FROM Trainers WHERE Trainer_ID=%s",[trainer_id])
        if result1<1:
            error="Trainer selected does not exist"
            cur.execute("SELECT * FROM Trainers")
            result2=cur.fetchall()
            return render_template ('registered_trainers.html',trainers=result2,error=error,form=form)
        else:
            cur.execute("UPDATE Trainers SET Status=%s WHERE Trainer_ID=%s ",(status,trainer_id))
            mysql.connection.commit()
            msg="Trainer status reset successfully"
            cur.execute("SELECT * FROM Trainers")
            result3=cur.fetchall()
            return render_template ('registered_trainers.html',trainers=result3,form=form,msg=msg)

    return render_template ('registered_trainers.html',trainers=result,form=form)
class workout_update_form(Form):
        workout_id=StringField("WORKOUT_ID",[validators.Length(min=1,max=20),validators.DataRequired()])
        workout_name=StringField("WORKOUT_NAME",[validators.Length(min=1,max=30),validators.DataRequired()])
        description=StringField("DESCRIPTION",[validators.Length(min=1,max=500),validators.DataRequired()])
@app.route('/update_workout',methods=['GET','POST'])
@is_admin_logged_in
def update_workout():
    form=workout_update_form(request.form)
    cur=mysql.connection.cursor()
    if request.method=='POST':
        workout_id=form.workout_id.data
        workout_name=form.workout_name.data
        description=form.description.data

        result=cur.execute("SELECT workout_id FROM Workouts WHERE workout_id=%s",[workout_id])
        if result>0:
            error="WorkoutID already exists,Kindly check!!!"
            return render_template("workouts.html",error=error,form=form)
        else:
            cur.execute("INSERT INTO Workouts (Workout_ID,Workout_name,Description)VALUES(%s,%s,%s)",(workout_id,workout_name,description))
            mysql.connection.commit()
            msg=" Workout updated successfully"
            return render_template("workouts.html",form=form,msg=msg)
    return render_template("workouts.html",form=form)
@app.route('/workouts_offered')
@is_admin_logged_in
def workouts_offered():
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM Workouts")
    result=cur.fetchall()
    return render_template ('workouts_offered.html',workouts=result)
class workout_routine_form(Form):

        customer_id=StringField("CUSTOMER_ID",[validators.Length(min=1,max=30),validators.DataRequired()])
        workout_id=StringField("WORKOUT_ID",[validators.Length(min=1,max=50),validators.DataRequired()])
        trainer_id=StringField("TRAINER_ID",[validators.Length(min=1,max=50),validators.DataRequired()])
        start_date=StringField("START_DATE",[validators.Length(min=1,max=30),validators.DataRequired()])
        end_date=StringField("END_DATE",[validators.Length(min=1,max=30),validators.DataRequired()])
@app.route('/update_routine',methods=['GET','POST'])
@is_admin_logged_in
def update_routine():
    form=workout_routine_form(request.form)
    cur=mysql.connection.cursor()
    if request.method=='POST':

        customer_id=form.customer_id.data
        workout_id=form.workout_id.data
        trainer_id=form.trainer_id.data
        start_date=form.start_date.data
        end_date=form.end_date.data

        result3=cur.execute("SELECT CustomerID FROM Customers WHERE CustomerID=%s",[customer_id])
        result4=cur.execute("SELECT Workout_ID FROM Workouts WHERE Workout_ID=%s",[workout_id])
        result5=cur.execute("SELECT Trainer_ID FROM Trainers WHERE Trainer_ID=%s",[trainer_id])
        if result3<1:
            error="Customer selected does not exist"
            return render_template("workout_routine.html",error=error,form=form)
        else:
            if result4<1:
                error="Workout selected does not exist"
                return render_template("workout_routine.html",error=error,form=form)
            else:
                if result5<1:
                    error="Trainer selected does not exist"
                    return render_template("workout_routine.html",error=error,form=form)
                else:
                            result6=cur.execute("SELECT Amount FROM EQUIPMENTS WHERE Workout_ID=%s",[workout_id])
                            if result6<1:
                                error="The workout selected has not been assigned any equipments,please check!! "
                                return render_template("workout_routine.html",error=error,form=form)
                            else:
                                cur.execute("SELECT MIN(Amount) FROM EQUIPMENTS WHERE Workout_ID=%s",[workout_id])
                                result1=cur.fetchall()
                                if result1[0]['MIN(Amount)']<1 :
                                    error="Gym equipments available are not enough,please check!!"
                                    return render_template("workout_routine.html",error=error,form=form)
                                else:
                                    cur.execute("SELECT Status FROM Trainers WHERE Trainer_ID=%s ",[trainer_id])
                                    result2=cur.fetchall()
                                    if result2[0]['Status']=='Free':
                                        cur.execute("UPDATE Trainers SET Status='Engaged' WHERE Trainer_ID=%s",[trainer_id])
                                        cur.execute("UPDATE Equipments SET Amount=Amount-1 WHERE Workout_ID=%s",[workout_id])
                                        cur.execute("INSERT INTO Workouts_schedule (Customer_ID,Workout_ID,Trainer_ID,Start_date,End_date)VALUES(%s,%s,%s,%s,%s)",(customer_id,workout_id,trainer_id,start_date,end_date))
                                        mysql.connection.commit()
                                        msg=" Training session updated successfully"
                                        return render_template("workout_routine.html",form=form,msg=msg)
                                    else:
                                        error="The trainer selected is engaged with another customer,kindly check again!!!!"
                                        return render_template("workout_routine.html",error=error,form=form)
    return render_template("workout_routine.html",form=form)
@app.route('/updated_workout_routine')
@is_admin_logged_in
def updated_workout_routine():
    cur=mysql.connection.cursor()
    cur.execute("SELECT Workouts_schedule.Session_ID,Workouts_schedule.Customer_ID,Customers.Name,Workouts_schedule.Trainer_ID,Trainers.Trainer_name,Workouts_schedule.Workout_ID,Workouts.Workout_name,Workouts_schedule.Start_date,Workouts_schedule.End_date FROM (((Workouts_schedule INNER JOIN Customers ON Workouts_schedule.Customer_ID=Customers.CustomerID)INNER JOIN Trainers ON Workouts_schedule.Trainer_ID=Trainers.Trainer_ID)INNER JOIN Workouts ON Workouts_schedule.Workout_ID=Workouts.Workout_ID)")
    result=cur.fetchall()
    return render_template ('updated_workouts.html',updated_workouts=result)
class financial_report_form(Form):
    start_date=StringField("START_DATE",[validators.Length(min=1,max=20),validators.DataRequired()])
    end_date=StringField("END_DATE",[validators.Length(min=1,max=20),validators.DataRequired()])
@app.route('/financial_report',methods=['GET','POST'])
@is_admin_logged_in
def financial_report():
    form=financial_report_form(request.form)
    cur=mysql.connection.cursor()
    start_date=form.start_date.data
    end_date=form.end_date.data
    cur.execute("SELECT MIN(Date) FROM Transactions")
    result1=cur.fetchall()
    cur.execute("SELECT MIN(Date_purchased) FROM Equipments")
    result2=cur.fetchall()


    if request.method=='POST':


            if start_date>end_date:
                error="The start date should not be greater than the end date"
                return render_template("gym_financial_report.html",error=error,Revenue=0,Expenditure=0,Difference=0,form=form)
            else:
                cur.execute("SELECT SUM(Amount) AS Total_Monthly_Revenue FROM Transactions WHERE Date BETWEEN %s AND %s",(start_date,end_date))
                result=cur.fetchall()
                cur.execute("SELECT SUM(Price) AS Total_Monthly_Expenditure From Equipments WHERE Date_purchased BETWEEN %s AND %s",(start_date,end_date))
                result1=cur.fetchall()
                if result[0]['Total_Monthly_Revenue']==None  and  result1[0]['Total_Monthly_Expenditure']==None:
                    return render_template("gym_financial_report.html",Revenue=0,Expenditure=0,Difference=0,form=form)
                if result[0]['Total_Monthly_Revenue']==None :

                    return render_template("gym_financial_report.html",Revenue=0,Expenditure=result1[0]['Total_Monthly_Expenditure'],Difference=result1[0]['Total_Monthly_Expenditure']*-1,form=form)
                if result1[0]['Total_Monthly_Expenditure']==None:
                    return render_template("gym_financial_report.html",Revenue=result[0]['Total_Monthly_Revenue'],Expenditure=0,Difference=result[0]['Total_Monthly_Revenue'],form=form)

                else:

                    difference=result[0]['Total_Monthly_Revenue']-result1[0]['Total_Monthly_Expenditure']
                    return render_template("gym_financial_report.html",Revenue=result[0]['Total_Monthly_Revenue'],Expenditure=result1[0]['Total_Monthly_Expenditure'],Difference=difference,form=form)

    return render_template("gym_financial_report.html",form=form)





















