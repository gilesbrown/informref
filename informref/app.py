from flask import Flask, render_template, request, redirect, url_for
from informref import middleware
from informref import model
from informref.elements import Value, Link, Form, Input, Select, inform_jinja_functions

app = Flask(__name__)
app.wsgi_app = middleware.MethodFromParam(app.wsgi_app)
app.jinja_env.globals.update(inform_jinja_functions)


def render(attributes=[], messages=[], warnings=[], errors=[], status_code=200):
    kw = dict(
        request=request,
        status_code=status_code,
        errors=errors,
        messages=messages,
        attributes=attributes,
    )
    return render_template('inform.html', **kw), status_code


@app.route('/')
def home():

    if 'version' in request.args:
        vnum = 'v{0}'.format(request.args['version'].strip())
        return redirect(url_for(vnum))

    versions = [('1', '1'), ('latest', '1')]
    elems = [
        Form('select_version', Select('version', versions, selected=-1)),
    ]
    return render(elems)


@app.route('/v1')
def v1():
    return render([Link('retailer_index', url_for('retailer_index'))])


@app.route('/retailer/')
def retailer_index():
    attributes = [
        Form('create', Input('name'), action=url_for('retailer_create'), method='POST'),
        Form('find', Input('name'), action=url_for('retailer_find')),
        Form('create_or_find', Input('name'), action=url_for('retailer_create_or_find'), method='POST'),
    ]
    return render(attributes)


@app.route('/retailer/create', methods=['POST'])
def retailer_create():
    kwargs = {k: v for k, v in request.form.items() if v.strip()}
    try:
        retailer = model.create_retailer(**kwargs)
        attributes = [Link('created', url_for('retailer', flake=retailer.flake))]
        return render(attributes=attributes, status_code=201)
    except model.RetailerNameInUse:
        errors=["Name '%s' is already in use" % request.form['name']]
        return render(errors=errors, status_code=409)


@app.route('/retailer/create_or_find', methods=['POST'])
def retailer_create_or_find():
    kwargs = {k: v for k, v in request.form.items() if v.strip()}
    try:
        retailer = model.create_retailer(**kwargs)
        attributes = [Link('created', url_for('retailer', flake=retailer.flake))]
        return render(attributes=attributes, status_code=201)
    except model.RetailerNameInUse as exc:
        return redirect(url_for('retailer', flake=exc.other), 303)


@app.route('/retailer/find', methods=['GET'])
def retailer_find():
    kwargs = {k: v for k, (v,) in dict(request.args).items() if v.strip()}
    retailer = model.find_retailer_by_name(**kwargs)
    if retailer is None:
        errors = ["No such retailer"]
        return render(errors=errors, status_code=404)
    return redirect(url_for('retailer', flake=retailer.flake), 302)


@app.route('/retailer/<int:flake>', methods=['GET', 'DELETE'])
def retailer(flake):

    retailer = model.get_retailer(flake)
    if not retailer:
        return render(errors=['No such retailer'], status_code=404)

    if request.method == 'DELETE':
        model.delete_retailer(flake)
        return render(messages=["Deleted '%s'" % request.url], status_code=200)
    else:
        delete = Form(
            'delete',
            action=url_for('retailer', flake=flake),
            method="DELETE",
        )
        return render(attributes=[Value('name', retailer.name), delete], status_code=200)


if __name__ == '__main__':
    app.run(debug=True)
