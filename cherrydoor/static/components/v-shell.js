const vShell = {
	template: `
<div @click="$refs.cmd.focus();">
	<div ref="terminal" id="container">
		<div v-if="banner" id="banner">
			<p>
				<img v-if="banner.img" :align="banner.img.align ? banner.img.align : 'left'" :src="banner.img.link ? banner.img.link : '@/logo.png'" :width="banner.img.width ? banner.img.width : '100px'" :height="banner.img.height ? banner.img.height : '100px'">
			</p>
			<h2 v-if="banner.header" style="letter-spacing: 4px">{{banner.header}}</h2>
			<p v-if="banner.subHeader">{{banner.subHeader}}</p>
			<p v-if="banner.helpHeader">{{banner.helpHeader}}</p>
			<p></p>
		</div>
		<output ref="output"></output>
		<div id="input-line" class="input-line">
			<div class="prompt">
				<div v-if="banner.emoji.first &amp;&amp; showemoji">({{banner.emoji.first}})</div>
				<div v-if="banner.emoji.second &amp;&amp; !showemoji">({{banner.emoji.second}})</div>
				<div>{{banner.sign ? banner.sign : '&gt;&gt;'}}</div>
			</div>

			<input v-model="value" ref="cmd" @keydown.enter="cmd_enter($event)" @keydown.up="history_up()" @keydown.down="history_down()" @keydown.tab="cmd_tab($event)" class="cmdline" autofocus="">
		</div>
	</div>
</div>
`,
	props: {
		shell_input: {
			required: false,
		},
		banner: {
			type: Object,
			required: false,
			default: () => {
				return {
					header: "Vue Shell",
					subHeader: "Shell is power just enjoy 🔥",
					helpHeader: 'Enter "help" for more information.',
					emoji: {
						first: "🔅",
						second: "🔆",
						time: 750,
					},
					sign: "VueShell $",
					img: {
						align: "left",
						link: `@/logo.png`,
						width: 100,
						height: 100,
					},
				};
			},
		},
		commands: {
			type: Array,
		},
	},
	data() {
		return {
			showemoji: true,
			value: "",
			history_: [],
			histpos_: 0,
			histtemp_: 0,
		};
	},
	computed: {
		allcommands() {
			var tab = [
				{
					name: "help",
					desc: "Show all the commands that are available",
				},
				{
					name: "clear",
					desc: "Clear the terminal of all output",
				},
			];

			if (this.commands) {
				this.commands.forEach(({ name, desc }) => {
					tab.push({
						name,
						desc,
					});
				});
			}

			return tab;
		},
	},
	watch: {
		shell_input(val) {
			this.output(val, false);
			this.$parent.send_to_terminal = "";
		},
	},
	methods: {
		history_up() {
			if (this.history_.length) {
				if (this.history_[this.histpos_]) {
					this.history_[this.histpos_] = this.value;
				} else {
					this.histtemp_ = this.value;
				}
			}
			// up 38
			this.histpos_--;
			if (this.histpos_ < 0) {
				this.histpos_ = 0;
			}
			this.value = this.history_[this.histpos_]
				? this.history_[this.histpos_]
				: this.histtemp_;
		},
		history_down() {
			if (this.history_.length) {
				if (this.history_[this.histpos_]) {
					this.history_[this.histpos_] = this.value;
				} else {
					this.histtemp_ = this.value;
				}
			}
			this.histpos_++;
			if (this.histpos_ > this.history_.length) {
				this.histpos_ = this.history_.length;
			}
			this.value = this.history_[this.histpos_]
				? this.history_[this.histpos_]
				: this.histtemp_;
		},
		cmd_tab(e) {
			e.preventDefault();
		},
		cmd_enter() {
			if (this.value) {
				this.history_[this.history_.length] = this.value;
				this.histpos_ = this.history_.length;
			}

			//   Duplicate current input and append to output section.
			var line = this.$refs.cmd.parentNode.cloneNode(true);
			line.removeAttribute("id");
			line.classList.add("line");
			var input = line.querySelector("input.cmdline");
			input.autofocus = false;
			input.readOnly = true;
			this.$refs.output.appendChild(line);

			if (this.value && this.value.trim()) {
				var args = this.value.split(" ").filter(function (val) {
					return val;
				});
				var cmd = args[0].toLowerCase();
				args = args.splice(1); // Remove cmd from arg list.
			}

			if (cmd == "clear") {
				this.$refs.output.innerHTML = "";
				this.value = "";
			} else if (cmd == "help") {
				var commandsList = this.allcommands.map(({ name, desc }) => {
					if (desc) {
						return `${name}: ${desc}`;
					}

					return name;
				});

				this.output(
					'<div class="ls-files">' + commandsList.join("<br>") + "</div>"
				);
			} else {
				if (this.commands) {
					this.commands.forEach((a) => {
						if (cmd == a.name) {
							this.output(a.get());
							return;
						}
					});
				}
				if (this.value.trim() != "") {
					this.$emit("shell_output", this.value);
				}
				this.value = "";
			}

			// Clear/setup line for next input.
		},
		output(html, clear = true) {
			this.$refs.output.insertAdjacentHTML(
				"beforeEnd",
				"<pre>" + html + "</pre>"
			);
			if (clear) this.value = "";
		},
	},
	mounted() {
		if (
			this.banner.emoji.first &&
			this.banner.emoji.second &&
			this.banner.emoji.time
		) {
			setInterval(() => {
				this.showemoji = !this.showemoji;
			}, this.banner.emoji.time);
		}
	},
};
export default vShell;
