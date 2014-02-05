from flask import Flask, render_template, request, redirect, url_for
from jinja2 import evalcontextfilter, Markup, escape
from informref import middleware
from informref import model, redisobjects
from informref.elements import Value, Link, Form, Input, Select, inform_jinja_functions

app = Flask(__name__)
app.wsgi_app = middleware.MethodFromParam(app.wsgi_app)
app.jinja_env.globals.update(inform_jinja_functions)

@evalcontextfilter
def inform_value(eval_ctx, value):

    if isinstance(value, Value):
        id = value.id
        value = value.value
    else:
        id = None

    module = eval_ctx.environment.get_template('inform.html').module
    if hasattr(value, '__iter__'):
        if hasattr(value, 'items'):
            return module.inform_dl(value, id)
        else:
            return module.inform_ol(value, id)
    elif isinstance(value, Link):
        return module.inform_link(value, id)
    else:
        result = escape(value)
    if eval_ctx.autoescape:
        result = Markup(result)
    return result
app.jinja_env.filters['inform_value'] = inform_value



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
    attr = [
        Form('create_retailer', Input('name'), action=url_for('retailer_create'), method='POST'),
        Form('find_retailer', Input('name'), action=url_for('retailer_find')),
        Form('create_or_find_retailer', Input('name'), action=url_for('retailer_create_or_find'), method='POST'),
        Link(url_for('retailer_index'), 'retailer_index'),
    ]
    return render(attr)


@app.route('/retailer/')
def retailer_index():
    retailers = []
    for retailer in model.retailer_index():
        retailer_dict = retailer.dictify()
        retailer_dict['url'] = Link(url_for('retailer', id=retailer.id))
        retailers.append(retailer_dict)
    print "SORT:", retailers
    attributes = [
        Value('retailers', retailers),
    ]
    return render(attributes)


@app.route('/retailer/create', methods=['POST'])
def retailer_create():
    print "HEY:", request.form.items()
    kwargs = {k: v for k, v in request.form.items() if v.strip()}
    try:
        retailer = model.create_retailer(**kwargs)
        attributes = [Link(url_for('retailer', id=retailer.id), 'created')]
        return render(attributes=attributes, status_code=201)
    except redisobjects.NotNullable:
        errors=["Missing required field"]
        return render(errors=errors, status_code=400)
    except redisobjects.NotUnique:
        errors=["Name '%s' is already in use" % request.form['name']]
        return render(errors=errors, status_code=409)


@app.route('/retailer/create_or_find', methods=['POST'])
def retailer_create_or_find():
    kwargs = {k: v for k, v in request.form.items() if v.strip()}
    try:
        retailer = model.create_retailer(**kwargs)
        attributes = [Link(url_for('retailer', id=retailer.id), 'created')]
        return render(attributes=attributes, status_code=201)
    except redisobjects.NotUnique as exc:
        return redirect(url_for('retailer', id=exc.other), 303)


@app.route('/retailer/find', methods=['GET'])
def retailer_find():
    kwargs = {k: v for k, (v,) in dict(request.args).items() if v.strip()}
    retailer = model.find_retailer_by_name(**kwargs)
    if retailer is None:
        errors = ["No such retailer"]
        return render(errors=errors, status_code=404)
    return redirect(url_for('retailer', id=retailer.id), 302)


@app.route('/retailer/<int:id>', methods=['GET', 'DELETE'])
def retailer(id):

    retailer = model.get_retailer(id)
    if not retailer:
        return render(errors=['No such retailer'], status_code=404)

    if request.method == 'DELETE':
        model.delete_retailer(id)
        return render(messages=["Deleted '%s'" % request.url], status_code=200)
    else:
        delete = Form(
            'delete',
            action=url_for('retailer', id=id),
            method="DELETE",
        )
        return render(attributes=[Value('name', retailer.name), delete], status_code=200)


if __name__ == '__main__':
    app.run(debug=True)
