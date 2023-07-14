import datetime
import logging
import os
import sqlite3

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

# Global variable for current timestamp used for logging
current_timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
mime_type = 'application/json'
db_file = 'database.db'

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
      app.logger.error(current_timestamp + ', Article ID "' + str(post_id) + '" was not found! 404 page is returned')
      return render_template('404.html'), 404
    else:
      post_title = post[2]
      app.logger.info(current_timestamp + ', Article "' + post_title + '" retrieved!')
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info(current_timestamp + ', About us page is retrieved')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.info(current_timestamp + ', Article "' + title + '" is created!')
            return redirect(url_for('index'))

    return render_template('create.html')

# Define a health check endpoint
@app.route('/healthz')
def healthcheck():
    healthy = (True, "") if os.path.isfile(db_file) else (False, "connection to the database failed")
    if healthy[0]:
        connection = get_db_connection()
        posts = connection.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='posts' ''')
        healthy = (True, "") if posts.fetchone()[0]==1 else (False, "posts table does not exist")
    
    if healthy[0]:
        return app.response_class(
            response=json.dumps({"result":"OK - healthy"}),
            status=200,
            mimetype=mime_type
        )
    else:
        return app.response_class(
            response=json.dumps({"result":"ERROR - unhealthy, reason: " + healthy[1]}),
            status=500,
            mimetype=mime_type
        )

# Define a metrics endpoint for DB connections count and posts count
@app.route('/metrics')
def metrics():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    db_count = c.execute('SELECT count(*) FROM sqlite_master').fetchone()[0]
    row_count = c.execute('SELECT count(*) FROM posts').fetchone()[0]
    response = app.response_class(
            response=json.dumps({"db_connection_count": db_count, "post_count": row_count}),
            status=200,
            mimetype=mime_type
    )

    return response

# start the application on port 3111
if __name__ == "__main__":
   logging.basicConfig(level=logging.DEBUG)
   app.run(host='0.0.0.0', port='3111')
