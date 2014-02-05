function elemWithAttr(tag, attrs, child0) {
	var elem = document.createElement(tag)
	for (attr in attrs){
		elem.setAttribute(attr, attrs[attr])
	}
	for (var i=2; i < arguments.length; i++) {
		if (typeof arguments[i] === 'undefined') {
		}
		else if (typeof arguments[i] === 'string') {
			elem.innerHTML += arguments[i]
		}
		else {
			elem.appendChild(arguments[i])
		}
	}
	return elem
}


function addBootstrapToHead(head) {
	var head = document.querySelector('head')
	head.appendChild(elemWithAttr('meta', {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}))
        head.appendChild(elemWithAttr('link', {"rel": "stylesheet", "href": "http://netdna.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css"}))
}

function wrapValue(value) {
	var panel = elemWithAttr('div', {'class': 'panel panel-default'})
	var panel_heading = elemWithAttr('div', {'class': 'panel-heading'})
	var panel_body = elemWithAttr('div', {'class': 'panel-body'})
	var h3 = elemWithAttr('h3', {}, 
	    elemWithAttr('span', {'class': 'glyphicon glyphicon-tag'}), 
	    ' ',
	    value.id
	)
	panel_heading.appendChild(h3)
	panel_body.appendChild(annotate(value))
	panel.appendChild(panel_heading)
	panel.appendChild(panel_body)

	return panel
}

function wrapAnchor(anchor) {
	var panel = elemWithAttr('div', {'class': 'panel panel-default'})
	var panel_heading = elemWithAttr('div', {'class': 'panel-heading'})
	var panel_body = elemWithAttr('div', {'class': 'panel-body'})
	var h3 = elemWithAttr('h3')


	h3.appendChild(elemWithAttr('span', {'class': 'glyphicon glyphicon-link'}))
	h3.appendChild(document.createTextNode(' '))
	h3.appendChild(annotate(anchor))
	panel_heading.appendChild(h3)
	panel.appendChild(panel_heading)

	return panel
}

function wrapForm(form) {
	var panel = elemWithAttr('div', {'class': 'panel panel-default'})
	var panel_heading = elemWithAttr('div', {'class': 'panel-heading'})
	var panel_body = elemWithAttr('div', {'class': 'panel-body'})
	var h3 = elemWithAttr('h3')

	h3.appendChild(elemWithAttr('span', {'class': 'glyphicon glyphicon-transfer'}))
	h3.innerHTML = h3.innerHTML + ' ' + form.id

	panel_heading.appendChild(h3)
	panel_body.appendChild(annotate(form))
	panel.appendChild(panel_heading)
	panel.appendChild(panel_body)

	return panel
}

function annotateAnchor(anchor, suggestion) {
	console.log("SUGGESTION", suggestion)
	if (!anchor.innerHTML) {
		if (suggestion) {
			anchor.innerHTML = suggestion
		}
		else if (anchor.id)	{
			anchor.innerHTML = anchor.id
		}
		else if (anchor.href) {
			anchor.innerHTML = anchor.href
		}
		else {
			anchor.innerHTML = "empty"
		}
	}
	return anchor
}


function annotateForm(form, suggestion) {
	var button_text ;
	if (form.id) {
		button_text = form.id
	}
	else if (suggestion) {
		button_text = suggestion
	}
	else if (form.action) {
		button_text = form.action
	}
	else {
		button_text = 'submit'
	}
        var inputs = form.getElementsByTagName('input')
	for (i=0; i<inputs.length; i++) {
		var input = inputs[i]
		form.insertBefore(elemWithAttr('label', {'for': input.name}, input.name), input)
	}
	form.appendChild(elemWithAttr('button', {'type': 'submit'}, button_text))
	return form
}

function annotateDD(dd, name) {
	console.log('annotateDD', dd, dd.childNodes[0])
	annotate(dd.childNodes[0], name)
	for (var j=0; j<dd.childNodes.length; j++) {
		console.log('DD?', dd.childNodes[j])
		annotate(dd.childNodes[j])
	}
	return dd
}

function annotateDL(dl) {
	var dt ;
	console.log('annotateDL', dl)
	for (var i=0; i<dl.childNodes.length; i++) {
		if (dl.childNodes[i].tagName === 'DT') {
			dt = dl.childNodes[i]
		}
		else if (dl.childNodes[i].tagName === 'DD') {
			annotateDD(dl.childNodes[i], dt.innerHTML)
		}
	}
	return dl
}

function annotateList(list) {
	for (var i=0; i<list.childNodes.length; i++) {
		var child = list.childNodes[i]
		if (child.tagName === 'LI') {
			for (var j=0; j<child.childNodes.length; j++) {
				console.log('LIST?', child.childNodes[j])
				annotate(child.childNodes[j])
			}
		}
	}
	return list
}


var annotators = {
	"FORM": annotateForm,
	"A": annotateAnchor,
	"DL": annotateDL,
	"OL": annotateList,
	"UL": annotateList
}


var wrappers = {
	"FORM": wrapForm,
	"A": wrapAnchor
}


function wrap(elem) {
	var f = wrappers[elem.tagName]
	if (typeof f === 'function') {
		return f(elem)
	}
	return wrapValue(elem)
}

function annotate(elem) {
	var f = annotators[elem.tagName]
	console.log('annotate', elem)
	if (typeof f === 'function') {
		return f.apply(undefined, arguments)
	}
	return elem
}

function getMetaValue(selector) {
	var meta = document.querySelector(selector)
	if (meta) {
		return meta.getAttribute('value')
	}
}


document.addEventListener('DOMContentLoaded', function() {
	addBootstrapToHead()
	var container = elemWithAttr('div', {"class": "container"})
	var http_method = getMetaValue('meta[name="http-method"]')
	var http_status = getMetaValue('meta[name="http-status"]')

	container.appendChild(
		elemWithAttr('div', {'class': 'page-header'},
			elemWithAttr('h2', {}, http_method, ' ', document.documentURI, ' ', http_status)
		)
	)

        var contents = document.querySelectorAll('body > *')
	for (var i=0; i<contents.length; i++){
		if (contents[i].getAttribute('id')) {
			container.appendChild(wrap(contents[i]))
		}
		else {
	            container.appendChild(contents[i])
	        }
	}
        document.querySelector('body').appendChild(container)
})
