"user strict";
if (typeof socket == "undefined") {
  var socket = io.connect("/api");
}
const actions = {
  closeModal: () => $(".modal.show").modal("hide"),
  emitUsers: setTimeout(() => {
    socket.emit("users");
  }, 100)
};
$(".modal-link").click(e => {
  $("#" + e.target.attributes["data-modal"].value).modal("show");
  $("#" + e.target.attributes["data-modal"].value).submit(e => {
    e.preventDefault();
    $.ajax({
      url: e.target.attributes["data-url"].value,
      type: e.target.attributes["data-type"].value,
      data: $(e.target).serialize(),
      complete: actions[e.target.attributes["data-action"].value]
    });
  });
});
