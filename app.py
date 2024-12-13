from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)

# User authentication helpers
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

@app.route('/')
def home():
    news = News.query.all()
    articles = Article.query.all()
    return render_template('home.html', news=news, articles=articles)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/add_news', methods=['GET', 'POST'])
@login_required
def add_news():
    if not g.user.is_admin:
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        news = News(title=title, content=content)
        db.session.add(news)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_news.html')

@app.route('/add_article', methods=['GET', 'POST'])
@login_required
def add_article():
    if not g.user.is_admin:
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        article = Article(title=title, content=content)
        db.session.add(article)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_article.html')

@app.route('/add_comment/<string:content_type>/<int:content_id>', methods=['POST'])
@login_required
def add_comment(content_type, content_id):
    content = request.form['content']
    comment = Comment(content=content, user_id=g.user.id)
    if content_type == 'news':
        comment.news_id = content_id
    elif content_type == 'article':
        comment.article_id = content_id
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/reply_comment/<int:comment_id>', methods=['POST'])
@login_required
def reply_comment(comment_id):
    content = request.form['content']
    reply = Comment(content=content, user_id=g.user.id, parent_id=comment_id)
    db.session.add(reply)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/vote_comment/<int:comment_id>/<string:vote>', methods=['POST'])
@login_required
def vote_comment(comment_id, vote):
    comment = Comment.query.get(comment_id)
    if vote == 'like':
        comment.likes += 1
    elif vote == 'dislike':
        comment.dislikes += 1
    db.session.commit()
    return redirect(url_for('home'))

# Minimal HTML templates
def create_templates():
    templates = {
        'home.html': """<h1>Home</h1>
        <a href='/register'>Register</a> | <a href='/login'>Login</a> | <a href='/logout'>Logout</a>
        {% if g.user and g.user.is_admin %}
            <a href='/add_news'>Add News</a> | <a href='/add_article'>Add Article</a>
        {% endif %}
        <h2>News</h2>
        {% for item in news %}
            <h3>{{ item.title }}</h3>
            <p>{{ item.content }}</p>
        {% endfor %}
        <h2>Articles</h2>
        {% for item in articles %}
            <h3>{{ item.title }}</h3>
            <p>{{ item.content }}</p>
        {% endfor %}
        """,
        'register.html': """<h1>Register</h1>
        <form method='post'>
            Username: <input type='text' name='username'><br>
            Password: <input type='password' name='password'><br>
            <button type='submit'>Register</button>
        </form>
        """,
        'login.html': """<h1>Login</h1>
        <form method='post'>
            Username: <input type='text' name='username'><br>
            Password: <input type='password' name='password'><br>
            <button type='submit'>Login</button>
        </form>
        """,
        'add_news.html': """<h1>Add News</h1>
        <form method='post'>
            Title: <input type='text' name='title'><br>
            Content: <textarea name='content'></textarea><br>
            <button type='submit'>Add</button>
        </form>
        """,
        'add_article.html': """<h1>Add Article</h1>
        <form method='post'>
            Title: <input type='text' name='title'><br>
            Content: <textarea name='content'></textarea><br>
            <button type='submit'>Add</button>
        </form>
        """
    }
    for name, content in templates.items():
        with open(f'templates/{name}', 'w') as f:
            f.write(content)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_templates()
    app.run(debug=True)

