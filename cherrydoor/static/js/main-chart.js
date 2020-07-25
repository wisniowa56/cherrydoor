"user strict";
if (typeof socket == "undefined") {
  var socket = io.connect("/api");
}
Chart.platform.disableCSSInjection = true;
$(document).ready(() => {
  var ctx = document.getElementById("doorchart");
  var usageData = [];

  setInterval(() => socket.emit("stats"), 500);
  socket.on("stats", function (json) {
    var tmpDict = {};
    json
      .map((el) => {
        return JSON.parse(el);
      })
      .map((el) => {
        el.timestamp = new Date(el.timestamp["$date"]);
        return el;
      })
      .forEach((el) => {
        date = `${el.timestamp.getFullYear()}-${el.timestamp.getMonth()}-${el.timestamp.getDate()}`;
        !!tmpDict[date]
          ? tmpDict[date].y++
          : (tmpDict[date] = { x: new Date(date), y: 1 });
      });
    usageData = Object.values(tmpDict);
    usageData.sort((a, b) => a.x.getTime() - b.x.getTime());
    chart.data.datasets[0].data = usageData;
    chart.update();
  });
  if (ctx !== null) {
    var chart = new Chart(ctx, {
      type: "line",
      label: "ilość użyć",
      data: {
        datasets: [
          {
            backgroundColor: "transparent",
            borderColor: "rgb(82, 136, 255)",
            data: usageData,
            lineTension: 0.3,
            pointRadius: 5,
            pointBackgroundColor: "rgba(255,255,255,1)",
            pointHoverBackgroundColor: "rgba(255,255,255,1)",
            pointBorderWidth: 2,
            pointHoverRadius: 8,
            pointHoverBorderWidth: 1,
          },
        ],
      },

      // Configuration options go here
      options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: {
          display: false,
        },
        layout: {
          padding: {
            right: 10,
          },
        },
        scales: {
          xAxes: [
            {
              type: "time",
              distribution: "series",
              time: {
                unit: "day",
              },
              gridLines: {
                display: false,
              },
            },
          ],
          yAxes: [
            {
              gridLines: {
                display: true,
                color: "#eee",
                zeroLineColor: "#eee",
              },
              ticks: {
                callback: function (value) {
                  var ranges = [
                    { divider: 1e6, suffix: "M" },
                    { divider: 1e4, suffix: "k" },
                  ];
                  function formatNumber(n) {
                    for (var i = 0; i < ranges.length; i++) {
                      if (n >= ranges[i].divider) {
                        return (
                          (n / ranges[i].divider).toString() + ranges[i].suffix
                        );
                      }
                    }
                    return n;
                  }
                  return formatNumber(value);
                },
              },
            },
          ],
        },
        tooltips: {
          callbacks: {
            title: function (tooltipItem, data) {
              return data["labels"][tooltipItem[0]["index"]];
            },
            label: function (tooltipItem) {
              //return data["datasets"][0]["data"][tooltipItem["index"]]["y"];
              return tooltipItem["yLabel"];
            },
          },
          responsive: true,
          intersect: false,
          enabled: true,
          titleFontColor: "#888",
          bodyFontColor: "#555",
          titleFontSize: 12,
          bodyFontSize: 18,
          backgroundColor: "rgba(256,256,256,0.95)",
          xPadding: 20,
          yPadding: 10,
          displayColors: false,
          borderColor: "rgba(220, 220, 220, 0.9)",
          borderWidth: 2,
          caretSize: 10,
          caretPadding: 15,
        },
      },
    });
  }
});
