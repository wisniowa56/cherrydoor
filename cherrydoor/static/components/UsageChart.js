const UsageChart = {
	data() {
		return {
			chartData: {},
		};
	},
	template: `
<div class="chart-container">
		<canvas id="usage-chart"></canvas>
		<h1>W trakcie prac :V</h1>
</div>
`,
	mounted() {
		this.ctx = document.getElementById("usage-chart").getContext("2d");
		/*this.chart = new Chart(this.ctx, {
			type: "line",
			responsive: true,
			maintainAspectRatio: false,
			data: {
				datasets: [
					{
						label: "Ilość wejść w danym dniu",
						data: [12, 19, 3, 5, 2, 3],
					},
				],
			},
			options: {
				scales: {
					y: {
						beginAtZero: true,
					},
					x: {
						type: "time",
						time: {
							unit: "day",
							rount: "day",
							isoWeekday: true,
						},
					},
				},
			},
		});*/
	},
};

export default UsageChart;
