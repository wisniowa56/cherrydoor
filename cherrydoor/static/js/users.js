"user strict";
if (typeof socket == "undefined") {
  var socket = io.connect("/api");
}
socket.on("users", (json) => {
  var users = [];
  json.forEach((value) => {
    users.push(JSON.parse(value));
  });
  var userContainer = $("#userContainer");
  userContainer.html("");
  var html;
  users.forEach((user) => {
    html = `<li class="list-group-item user-item"><div class="btn-toolbar justify-content-between">
				<div class="btn-group">
				<a class="text-primary btn" id="user-${user.username}" href="#collapseUser${user.username}" data-toggle="collapse" datadata-username="${user.username} aria-expanded="false" aria-controls="collapseUser${user.username}">${user.username}</a>
				</div>
				<div class="btn-group">
				<form class="delete-user-form form-inline pull-right" id="deleteUser${user.username}Form" data-url="/api/user" data-type="DELETE" data-action="emitUsers">
				<input type="hidden" name="username" value="${user.username}">
				<button class="btn btn-danger btn-sm delete-user-button d-flex" type="submit"><i class="material-icons">delete</i></button>
				</form>
				</div>
				</div>
				</li>
				<div class="collapse" id="collapseUser${user.username}">
						<ul class="list-group" id="cardList${user.username}">
						<li><form class="add-card-form form-inline w-100 pull-right" id="addCard${user.username}Form" data-url="/api/card" data-type="POST" data-action="emitUsers>
								<input type="hidden" name="username" value="${user.username}">
								<input class="form-control card-input" id="addCard${user.username}" type="text" placeholder="ID Karty" name="card" pattern="[0-9a-fA-F]{10}">
								<button class="btn btn-primary card-form-button d-flex" type="submit"><i class="material-icons">add_box</i></button>
						</form></li>
						</ul>
				</div>`;
    userContainer.append(html);
    var cardlist = $(`#cardList${user.username}`);
    user.cards.forEach((card) => {
      html = `<li class="list-group-item card-item" id="cardItem${card}">
			<div class="btn-toolbar justify-content-between">
				<div class="btn-group"><span class="text-primary btn d-flex">${card}</span></div>
			<div class="btn-group">
			<form class="delete-card-form form-inline pull-right" id="deleteCard${card}Form" data-url="/api/card" data-type="DELETE">
				<input type="hidden" name="username" value="${user.username}">
				<input type="hidden" name="card" value="${card}">
				<button class="btn btn-danger btn-sm delete-user-button" type="submit"><i class="material-icons">delete</i></span></button>
				</form>
			</div>
			</li>`;
      cardlist.append(html);
    });
  });
});
$(document).ready(() => {
  $("#manageUsersModal").on("show.bs.modal", () => {
    socket.emit("users");
  });
});
