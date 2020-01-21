"user strict";
var apiSocket = io.connect("/api");

apiSocket.on("users", json => {
  var users = [];
  json.forEach(value => {
    users.push(JSON.parse(value));
  });
  var html;
  users.forEach(user => {
    html = `<a class="list-group-item user-item" id="user-${user.username}" href="#collapseUser${user.username}" data-toggle="collapse" datadata-username="${user.username} aria-expanded="false" aria-controls="collapseUser${user.username}">${user.username}</a>
        <div class="collapse" id="collapseUser${user.username}">
            <ul class="list-group" id="cardList${user.username}>
            </ul>
        </div>`;
    $("#userContainer").append(html);
    user.cards.forEach(card => {
      html = `<li class="list-group-item" id="cardItem${user.username}Id${card}"><form ${card}</li>`;
      $(`#cardList${user.username}`).append(html);
    });
  });
});
$(document).ready(() => {
  $("#manageUsersModal").on("show.bs.modal", () => {
    console.log("shown");
    apiSocket.emit("users");
  });
});
