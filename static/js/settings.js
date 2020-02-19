"user strict";
if (typeof socket == "undefined") {
  var socket = io.connect("/api");
}
moment.locale("pl");
function fillHtml(id) {
  return `
  <div id="breakTime${id}">
<div class="row breakTimeInput input-group" id="breakTimeInput${id}">
    <label class="control-label col" for="breakTimeInputFrom">Od</label>
    <label class="control-label col" for="breakTimeInputTo">Do</label>
    <div class="col-1"></div><div class="w-100"></div>
    <div id="breakTimeInputFrom${id}" class="input-group date breakTimeInputFrom col" data-target-input="nearest">
        <input type="text" class="form-control datetimepicker-input breakTimeInput" placeholder="00:00:00" data-toggle="datetimepicker" data-target="#breakTimeInputFrom${id}"></input>
        <div class="input-group-append d-none d-sm-flex" data-target="#breakTimeInputFrom${id}" data-toggle="datetimepicker">
            <span class="input-group-text"><i class="far fa-clock"></i></span>
        </div>
    </div>
    <div id="breakTimeInputTo${id}" class="input-group date breakTimeInputTo col" data-target-input="nearest">
        <input type="text" class="form-control datetimepicker-input breakTimeInput" placeholder="00:00:00" data-toggle="datetimepicker" data-target="#breakTimeInputTo${id}"></input>
        <div class="input-group-append d-none d-sm-flex" data-target="#breakTimeInputTo${id}" data-toggle="datetimepicker">
            <span class="input-group-text"><i class="far fa-clock"></i></span>
        </div>
    </div>
    <div class="col-1"><button class="btn btn-danger btn-sm deleteBreakTime" data-target="#breakTime${id}"><i class="material-icons">delete</i></button></div>
</div><hr></div>`;
}
const addDeletion = () => {
  $(".deleteBreakTime").click(e => {
    e.preventDefault();
    $(e.delegateTarget.attributes["data-target"].value).remove();
  });
};
var timeId = 0;
socket.on("break_times", json => {
  if (!json.length) {
    $("#breakTimesContainer").html("");
    return;
  }
  var break_times = [
    ...JSON.parse(json).map(break_time => {
      return [new Date(break_time[0]), new Date(break_time[1])];
    })
  ];
  var breakTimesContainer = $("#breakTimesContainer");
  breakTimesContainer.html("");

  break_times.forEach(break_time => {
    breakTimesContainer.append(fillHtml(++timeId));
    let datePickerFrom = $(`#breakTimeInputFrom${timeId}`);
    let datePickerTo = $(`#breakTimeInputTo${timeId}`);
    datePickerFrom.datetimepicker({
      format: "LT",
      defaultDate: break_time[0]
    });
    datePickerTo.datetimepicker({
      format: "LT",
      defaultDate: break_time[1]
    });
    datePickerFrom.on("change.datetimepicker", e => {
      datePickerTo.datetimepicker("minDate", e.date);
    });
  });
  addDeletion();
});

$(document).ready(() => {
  $.fn.datetimepicker.Constructor.Default = $.extend(
    {},
    $.fn.datetimepicker.Constructor.Default,
    {
      icons: {
        time: "far fa-clock",
        date: "far fa-calendar",
        up: "fas fa-sort-up",
        down: "fas fa-sort-down",
        previous: "far fa-chevron-left",
        next: "far fa-chevron-right",
        today: "far fa-calendar-check-o",
        clear: "far fa-trash",
        close: "far fa-times"
      }
    }
  );
  $("#settingsModal").on("show.bs.modal", () => {
    socket.emit("break_times");
  });
  $("#addBreak").click(() => {
    var breakTimesContainer = $("#breakTimesContainer");
    breakTimesContainer.append(fillHtml(++timeId));
    let datePickerFrom = $(`#breakTimeInputFrom${timeId}`);
    let datePickerTo = $(`#breakTimeInputTo${timeId}`);
    datePickerFrom.datetimepicker({
      format: "LT"
    });
    datePickerTo.datetimepicker({
      format: "LT"
    });
    datePickerFrom.on("change.datetimepicker", e => {
      datePickerTo.datetimepicker("minDate", e.date);
    });
    addDeletion();
  });
  $("#submitSettings").click(() => {
    var breakTimes = [];
    $(".breakTimeInputFrom").each((i, el) => {
      if (!!$(el).datetimepicker("date")) {
        breakTimes[i] = [$(el).datetimepicker("date")];
      }
    });
    $(".breakTimeInputTo").each((i, el) => {
      if (!!breakTimes[i] && !!$(el).datetimepicker("date")) {
        breakTimes[i].push($(el).datetimepicker("date"));
      }
    });
    if (!breakTimes.length) {
      breakTimes = [[null, null]];
    }
    socket.emit("break_times", breakTimes);
  });
});
