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
		this.socket.on("serial_command", (data) => {
			if (data != null) {
				const command = `(${data.timestamp} < ${
					data.command
				} ${data.arguments.join(" ")}`;
				this.send_to_terminal = command;
			}
		});
		this.socket.emit("enter_room", { room: "serial_console" });
	},
	methods: {
		prompt(value) {
			this.socket.emit("serial_command", { command: value });
		},
	},
	template: `
<div class="card col-4 row-2">
	<v-shell @shell_output="prompt" :shell_input="send_to_terminal" :banner="banner"></v-shell>
</div>`,
};

export default SerialConsole;
