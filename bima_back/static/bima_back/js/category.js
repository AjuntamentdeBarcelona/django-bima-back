$(function() {
  $('#reset-filters').click(function(){
    $('#id_name').attr('value', '')
  })

  $('div.list-categories').on('click', '.eye', function(e){
    const btn = $(this)
    if (btn.data('children') === "0") {
      return false
    }
    if (!btn.data('loaded')) {
      $.ajax({
        url: categoryURLs.list, // from bima_back/categories/category.html
        data: {"parent": btn.data("categoryid")},
        method: 'GET',
      }).done(function(data) {
        console.debug(data)  // TODO: delete me
        let html = ''
        for (let category of data.results) {
          html += categoryHTML(category)
        }
        insertCategories(btn, html)
        btn.data('loaded', true)
      })
    }
  })
})

function categoryHTML(category) {
  let html = `<li>${category.name}`

  if (category.extra_info.children) {
    html += `
      <span class="pull-right">
        <button type="button"
            class="btn btn-transparent btn-sm eye"
            style="background: transparent; margin-top: -10px;"
            data-widget="collapse"
            data-children="${category.extra_info.children}"
            data-categoryid="${category.id}">
          <span>${category.extra_info.children}</span>&nbsp;<i class="fa fa-eye"></i>
        </button>
      </span>`
  }

  if (category.permissions.write) {
    html += `
    <a href="${categoryURLs.delete}/${category.id}" class="pull-right"><i class="fa fa-trash"></i></a>
    <a href="${categoryURLs.edit}/${category.id}" class="pull-right"><i class="fa fa-pencil"></i></a>`
  }

  html += `
    <a href="${categoryURLs.photos}?categories=${category.id}&btn_advanced=" class="pull-right" target="_blank">
      <i class="fa fa-search"></i>
    </a>
  </li>`

  return html
}

function insertCategories(categoryButton, categoriesHTML) {
  if (!categoriesHTML) {
    return
  }
  const html = `<ul>${categoriesHTML}</ul>`
  categoryButton.closest('div.panel-heading').next(".panel-body").html(html)
}
