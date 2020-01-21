"user strict";
$(".modal-link").click(e => {
  $("#" + e.target.attributes["data-modal"].value).modal("show");
  $("#" + e.target.attributes["data-modal"].value).submit(e => {
    if (!e.target.attributes["class"].value.includes("modal-form")) {
      return;
    }
    e.preventDefault();
    $.ajax({
      url: e.target.attributes["data-url"].value,
      type: e.target.attributes["data-type"].value,
      data: $(e.target).serialize()
    });
    $(".modal.show").modal("hide");
  });
});
