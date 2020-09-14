const UsageChart = {
	extends: VueChartJs.Line,
	//mixins: [VueChartJs.mixins.reactiveData],
	//inject: ["socket"],
	mounted() {
		this.renderChart({}, {});
	},
};

export default UsageChart;
