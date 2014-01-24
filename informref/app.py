import json
from flask import Request, Flask, render_template, request, redirect, url_for, abort
from informref import middleware
from informref import model

app = Flask(__name__)
app.wsgi_app = middleware.MethodFromParam(app.wsgi_app)
app.jinja_env.globals.update(jdumps=json.dumps)


@app.route('/')
def index():
    if 'version' in request.args:
        version = 'v' + request.args['version']
        return redirect(url_for(version))
    return render_template('index.html', args=request.args)


@app.route('/v1')
def v1():
    return render_template('v1.html', args=request.args)


@app.route('/retailer/', methods=['GET', 'POST'])
def retailer_index():
    if request.method == 'POST':
        try:
            # for our purposes empty means not present
            kw = {k: v for k, v in request.form.items() if v.strip()}
            retailer = model.create_retailer(**kw)
            return render_template('retailer.html', retailer=retailer), 201
        except model.RetailerNameInUse as exc:
            return redirect(url_for('retailer', flake=exc.other), 303)
    else:
        return render_template('retailer_index.html')



@app.route('/retailer/<int:flake>', methods=['GET', 'DELETE'])
def retailer(flake):
    if request.method == 'DELETE':
        model.delete_retailer(flake)
        return '', 204
    else:
        retailer = model.get_retailer(flake)
        if retailer.incomplete:
            abort(404)
        return render_template('retailer.html', retailer=retailer)


if __name__ == '__main__':
    app.run(debug=True)
