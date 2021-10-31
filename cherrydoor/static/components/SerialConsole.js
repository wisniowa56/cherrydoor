const SerialConsole = {
	data() {
		return {
			send_to_terminal: "",
			banner: {
				header: "Serial Console",
				subHeader: "Allows sending commands directly to the arduino",
				helpHeader:
					'Just type the string to send over serial. You can clear the console with "clear" command',
				sign: ">",
				emoji: {},
			},
		};
	},
	inject: ["user", "socket"],
	mounted() {
		const container = document.getElementById("container");
		this.socket.on("serial_command", (data) => {
			if (data != null) {
				const command = `(${data.timestamp}) < ${
					data.command
				} ${data.arguments.join(" ")}`;
				this.send_to_terminal = command;
				if (
					container.scrollHeight - container.scrollTop <
					container.clientHeight * 1.5
				) {
					setTimeout(() => {
						container.scrollTop = container.scrollHeight;
					}, 100);
				}
			}
		});
		this.socket.emit("enter_room", { room: "serial_console" });
	},
	methods: {
		prompt(value) {
			this.socket.emit("serial_command", { command: value });
			const container = document.getElementById("container");
			if (
				container.scrollHeight - container.scrollTop <
				container.clientHeight * 1.5
			) {
				setTimeout(() => {
					container.scrollTop = container.scrollHeight;
				}, 100);
			}
		},
	},
	template: `
<div class="card col-4 row-2">
	<v-shell @shell_output="prompt" :shell_input="send_to_terminal" :banner="banner"></v-shell>
</div>`,
};

export default SerialConsole;
