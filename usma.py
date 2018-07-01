from flask import Flask, render_template, url_for
app = Flask(__name__)

@app.route("/")
def usma():
    return render_template('usma.html', name='usma')

with app.test_request_context():
    url_for("static", filename="usma.css")
