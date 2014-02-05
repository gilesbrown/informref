function styleInformForm(form) {
    $(form).children(":input").each(
        function(index, elem) {
            //$(elem).wrap($('<tr />')).wrap($('<td />')) ;
            $(elem).wrap('<td />').parent().wrap('<tr />').parent().prepend(
                $('<td />').text(elem.getAttribute('name')),
                $('<td />').text(elem.getAttribute('type')),
                $('<td />').text(elem.tagName.toLowerCase()),
                $('<td />').text(elem.getAttribute('title'))
            )
        }
    ) ;
    $(form).children('tr').wrapAll($("<table><tbody /></table>")) ;
    $(form).children('table').prepend(
        $('<thead />').append(
            $('<tr />').append(
                $('<th>name</th>'),
                $('<th>type</th>'),
                $('<th>tag</th>'),
                $('<th>title</th>'),
                $('<th>value</th>')
            )
        )
    )
    $(form).before($('<h2 />', {'class': 'inform-id'}).text(form.getAttribute('id')) ;
}


function informstyle() {
    $("*[id]").each(
        function(index, elem) {
            switch(elem.tagName) {
                case "FORM": styleInformForm(elem) ; break ;
                default: alert(elem.tagName) ; break ;
            }
        }
    ) ;
}
