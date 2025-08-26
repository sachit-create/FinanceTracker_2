from flask import Flask , render_template

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)

