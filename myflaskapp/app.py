from flask import Flask, render_template , flash , redirect , url_for , session ,request, logging
#from flask_mysqldb import MySQL
from wtforms import Form, StringField , TextAreaField ,IntegerField, PasswordField, validators
from passlib.hash import sha256_crypt
import pymysql.cursors
from functools import wraps
import logging
import datetime

app = Flask(__name__)

#Config Mysql
#app.config['MYSQL_HOST'] = 'localhost'
#app.config['MYSQL_USER'] = 'root'
#app.config['MYSQL_PASSWORD'] = 'root'
#app.config['MYSQL_DB'] = 'flix'
#app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


connection = pymysql.connect(host='localhost',
                             user='root',
                             password='12345678',
                             db='tnvdb',
                             cursorclass=pymysql.cursors.DictCursor)

#initialize mysql
#mysql = MySQL(app)




@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


class RegisterForm(Form):
    email = StringField('Email', [validators.Length(min=6 , max = 50)])
    typeid = IntegerField('TypeId')
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passswords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register' , methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method =='POST' and form.validate():
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        typeid = form.typeid.data

        #Create Cursor
        #cur = mysql.connection.cursor()
        cur = connection.cursor()

        cur.execute("INSERT INTO USER(email,passw) VALUES(%s,%s)", (email, password))

        #Commit to DB
        connection.commit()

        #close connection
        cur.close()

        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method =="POST":
        #Get Form Fields
        email = request.form['email']
        password_candidate = request.form['password']

        #create a cursor 
        cur = connection.cursor()

        #Get use by username 
        result = cur.execute("SELECT * FROM USER WHERE email = %s" , [email])

        if result > 0:
            #get stored hash
            data = cur.fetchone()
            password = data['passw']
            print(password)
            #password = sha256_crypt.encrypt(str(password))

            #Compare the passwords 
            if sha256_crypt.verify(password_candidate,password):
                #Passed
                session['logged_in'] = True
                session['email'] = email

                flash("You are now logged in", 'success')
                return redirect(url_for('dashboard'))
            else:
                error = "Invalid password"
                return render_template('login.html',error=error)
            #Close connection    
            cur.close()
        else:
            error = "Username not found"
            return render_template('login.html',error=error)
    return render_template('login.html')

#Check if use is logged in 
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash("Unauthorizaed please log in ", 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


#Dashboard
@app.route('/dashboard', methods=["GET", "POST"])
@is_logged_in
def dashboard():
    colors = ['Daily', 'Monthly', 'Yearly']
    cur = connection.cursor()
    cur1 = connection.cursor()
    cur2 = connection.cursor()
    cur3 = connection.cursor()
    email = session['email']
    cur2.execute('select user_id from user where email = %s',email)
    result2 = cur2.fetchone()
    result2d = result2['user_id']
    #print(result2d)

    dude = []
    result = cur.execute('select video_id from video');
    res = []
    if result > 0:
        data = cur.fetchall()
        for i in data:
            print('i',i)
            cur1.execute('select video_id from vd_subscription where user_id = %s',result2d)
            result1 = cur1.fetchall()
            print('result1',result1)
            if i not in result1:
                res.append(i)
        print('res',res)
        for k in res:
            cur3.execute('select * from video where video_id = %s',k['video_id'])
            result3 = cur3.fetchall()
            dude.append(result3[0])
        print('dude',dude)
        cur.close()
        cur1.close()
        cur2.close()

    else:
        logging.info("Error in video fetch")

    return render_template('dashboard.html', dude=dude, colors=colors)

@app.route('/subscribe_video',methods=["GET","POST"])
def subscribe():
    if request.method =="POST":
        email = session['email']
        start_date = datetime.datetime.now()
        video_id = int(request.form['ButtonSelect'])
        option = request.form.get('OptionSelect')
        print("option",option)
        if option == 'Monthly':
            coeff = 0.9
        elif option == "Yearly":
            coeff = 0.85
        elif option == 'Daily':
            coeff = 1
        #print(type(video_id))
        cur = connection.cursor()
        cur1 = connection.cursor()
        cur2 = connection.cursor()

        cur1.execute('select user_id from user where email = %s',email)
        result = cur1.fetchone()
        resultd = result['user_id']
        #print(result)
        
        #resultd = int(result[0]['user_id'])
        #print(resultd)
        cur2.execute('select price_day from video where video_id = %s',video_id)
        result_price = cur2.fetchone()
        result_pricef = int(result_price['price_day']*coeff)
        #print("hi",result_price)
        
        #print("video_id",video_id)
        #print("start_date",start_date)
        #print("resultd",resultd)
        #print("result_pricef",result_pricef)
        cur.execute("insert into vd_subscription(video_id,user_id,start_date,price) values(%s,%s,%s,%s)",(video_id, resultd ,start_date, result_pricef))
        connection.commit()
        flash("You have subscribed successfully","success")


        cur.close()
        cur1.close()
        cur2.close()
    return render_template('home.html')



@app.route('/user_history')
@is_logged_in
def user_history():
    user_email = session['email']
    print(user_email)
    cur = connection.cursor()
    cur1 = connection.cursor()
    cur2 = connection.cursor()
    cur2.execute('select disc_factor from type where type_id = (select type_id from user where email = %s)',user_email)
    result2 = cur2.fetchone()
    result2d = result2['disc_factor']
    cur.execute('select user_id from user where email = %s',user_email)
    result1 = cur.fetchone()
    print(result1['user_id'])
    cur1.execute('select * from Vd_subscription where user_id = %s',result1['user_id'])
    result = cur1.fetchall()
    print(result)
    sum = 0
    for i in result:
        sum += int(i['price'])
    print("sum is ",sum)
    cur.close()
    cur1.close()

    return render_template('history.html', result=result,user_email=user_email,sum=sum*result2d)

@app.route('/mylibrary',methods=['GET', 'POST'])
@is_logged_in
def mylibrary():
    email = session['email']

    cur = connection.cursor()

    cur.execute('select user_id from user where email = %s',email)
    result = cur.fetchone()
    resultd = result['user_id']
    cur1 = connection.cursor()
    cur1.execute('select video_id from vd_subscription where user_id = %s',resultd)
    result1 = cur1.fetchall()
    print(result1)
    cur2 = connection.cursor()
    res = []
    picnames = []
    for i in result1:
        cur2.execute('select * from video where video_id = %s',i['video_id'])
        res.append(cur2.fetchone())
    print(res)
    cur2.close()
    cur.close()
    cur1.close()
    return render_template('mylibrary.html',result1=result1,res=res)

@app.route('/planview')
@is_logged_in
def planview():

    email = session['email']
    cur = connection.cursor()

    cur.execute('select type_id from user where email = %s',email)
    result = cur.fetchone()
    print(result)
    return render_template('planview.html',result=result)

@app.route('/changeplan',methods=["GET","POST"])
@is_logged_in
def changeplan():
    email = session['email']
    cur = connection.cursor()
    result = cur.execute('UPDATE User SET type_id = %s WHERE email = %s',('2',email))
    if result > 0:
        connection.commit()
        flash("Congrats you are now a premium user!","success")
    cur.close()
    return render_template('dashboard.html')

@app.route('/checkpacks')
@is_logged_in
def checkpacks():
    cur = connection.cursor()
    email = session['email']
    cur.connection('')
    cur.close()
    return render_template('checkpacks.html')

@app.route('/subscribe_pack')
@is_logged_in
def subscribe_pack():
    if request.method =="POST":
        pack_id = request.form['ButtonSelect']
        return render_template('home.html')





if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)