$(function() {
  $('#reset-filters').click(function(){
    $('#id_name').attr('value', '');
  });

  $('div.list-categories').on('click', '.eye', function(e){
    var btn = $(this);

    if (!btn.data('children')) {
      return false;
    }

    if (!btn.data('loaded')) {
      $.ajax({
        url: categoryURLs.list, // from bima_back/categories/category.html
        data: {"parent": btn.data("categoryid")},
        method: 'GET'
      }).done(function(data) {
        var html = '';
        for (var i = 0; i < data.results.length; i++) {
          html += categoryHTML(data.results[i]);
        }

        insertCategories(btn, html);

        if (!btn.data('isroot')) {
          $('#subcategories-' + btn.data('categoryid')).collapse('toggle');
        }

        btn.data('loaded', true);
      });
    } else {
      if (!btn.data('isroot')) {
        $('#subcategories-' + btn.data('categoryid')).collapse('toggle');
      }
    }
  });
});

function categoryHTML(category) {
  var html = '<li>' + category.name +
    '<span class="pull-right">\
      <button type="button"\
          class="btn btn-transparent btn-sm eye"\
          style="background: transparent; margin-top: -8px;"\
          data-children="' + category.extra_info.children + '"\
          data-categoryid="' + category.id + '">\
        <span>' + category.extra_info.children + '</span>&nbsp;<i class="fa fa-eye"></i>\
      </button>\
    </span>';

  if (category.permissions.write) {
    html += '<a href="' + categoryURLs.delete + '/' + category.id + '" class="pull-right"><i class="fa fa-trash"></i></a>\
      <a href="' + categoryURLs.edit + '/' + category.id + '" class="pull-right"><i class="fa fa-pencil"></i></a>';
  }

  html += '<a href="' + categoryURLs.photos + '?categories=' + category.id + '&btn_advanced=" class="pull-right" target="_blank">\
        <i class="fa fa-search"></i>\
      </a>\
    </li>';

  return html;
}

function insertCategories(categoryButton, categoriesHTML) {
  if (!categoriesHTML) {
    return;
  }

  var html = '<ul id="subcategories-' + categoryButton.data('categoryid') + '">' + categoriesHTML + '</ul>';

  if (categoryButton.data('isroot')) {
    categoryButton.closest('.panel-heading').next(".panel-body").html(html);
  } else {
    categoryButton.closest('li').append(html);
  }
}
